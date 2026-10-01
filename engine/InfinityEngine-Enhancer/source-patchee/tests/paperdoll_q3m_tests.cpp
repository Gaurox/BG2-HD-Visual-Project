#include "iee/paperdoll_q3m.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>

namespace {
std::vector<std::uint8_t> read(const char* path) {
  std::ifstream f(path,std::ios::binary);
  if(!f)throw std::runtime_error("missing fixture");
  return {std::istreambuf_iterator<char>(f),{}};
}
void expect(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
std::uint32_t word(std::span<const std::uint8_t> b,std::size_t offset) {
  expect(offset<=b.size() && b.size()-offset>=4,"truncated oracle");
  return b[offset]|(std::uint32_t(b[offset+1])<<8)|(std::uint32_t(b[offset+2])<<16)|(std::uint32_t(b[offset+3])<<24);
}
}
int main(int argc,char** argv) {
  try {
    expect(argc==3,"usage: iee_paperdoll_q3m_tests PACK ORACLE");
    const auto pack=read(argv[1]),oracle=read(argv[2]);
    iee::paperdoll_q3m::Frames frames;
    expect(iee::paperdoll_q3m::parse(pack,frames),"pilot pack rejected");
    expect(frames[0].width==66 && frames[0].height==64 && frames[0].centerX==-24 && frames[0].centerY==-16 &&
           frames[1].width==65 && frames[1].height==75 && frames[1].centerX==-25 && frames[1].centerY==0,"native placement changed");
    auto reject=[&](std::vector<std::uint8_t> bad) {
      auto copy=frames;
      expect(!iee::paperdoll_q3m::parse(bad,copy),"malformed pack accepted");
      expect(copy[0].indices.empty() && copy[1].indices.empty(),"failed parse retained previous frames");
    };
    for(const auto size : {std::size_t(0),std::size_t(31),std::size_t(80),std::size_t(648),pack.size()-1})
      reject({pack.begin(),pack.begin()+size});
    for(const auto offset : {0u,8u,12u,16u,20u,24u,28u,32u,40u,72u,76u,80u,84u,88u,89u,90u,91u,92u,
                             608u,640u,644u,645u,646u,647u}) {
      auto bad=pack;bad[offset]^=0x80;reject(std::move(bad));
    }
    const auto pixels0=frames[0].indices.size();
    auto bad=pack;bad[648+pixels0]=8;reject(bad); // invalid fraction
    bad=pack;bad[648]=1;bad[648+pixels0]=1;reject(bad); // special index cannot interpolate
    bad=pack;bad.back()=0x80;reject(bad); // cycle points outside this body
    bad=pack;bad.push_back(0);reject(bad); // trailing resource is outside scope
    expect(oracle.size()>=12 && std::equal(oracle.begin(),oracle.begin()+8,"P7ORCL01"),"oracle header differs");
    const auto count=word(oracle,8);expect(count==64,"measured session fixture differs");
    std::size_t pos=12,decodes=0;
    for(std::size_t n=0;n<count;++n) {
      iee::core::palette_fraction::Palette palette;
      for(std::size_t i=0;i<256;++i) {palette[i]=word(oracle,pos);pos+=4;}
      for(const auto& frame:frames) {
        std::vector<std::uint32_t> actual;
        expect(iee::paperdoll_q3m::decode(frame,palette,actual),"native palette decode failed");
        expect(actual.size()==frame.indices.size(),"decoded geometry differs");
        for(const auto color:actual) {expect(color==word(oracle,pos),"independent measured-palette byte oracle differs");pos+=4;}
        ++decodes;
      }
    }
    expect(pos==oracle.size(),"oracle trailing data");
    auto invalid=frames[0];invalid.width=0;
    std::vector<std::uint32_t> result{0x123};
    expect(!iee::paperdoll_q3m::decode(invalid,{},result) && result.empty(),"invalid frame produced pixels");
    int previous{};std::uint32_t crc{};bool uploaded{};
    expect(!iee::paperdoll_q3m::bind(0,0,66,64,{}, {},previous,crc,uploaded),"disabled pilot mutated native rendering");
    std::cout<<"PASS: strict native body scope, malformed/truncated rejection, "<<decodes
             <<" measured-palette BGRA byte decodes, disabled fallback\n";
    return 0;
  } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
