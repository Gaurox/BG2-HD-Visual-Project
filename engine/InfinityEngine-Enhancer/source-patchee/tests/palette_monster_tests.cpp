#include <array>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include <algorithm>
#include <limits>
#include <windows.h>
#include <bcrypt.h>
#include "iee/creature_sprite_x2.h"
#include "iee/core/palette_fraction.h"

namespace iee::probe {
void record_creature_texture_trace(unsigned,int,int,int,int,int,std::string_view) noexcept {}
}
namespace cs=iee::creature_sprite_x2;
namespace pf=iee::core::palette_fraction;
namespace fs=std::filesystem;
void require(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
template<class T> void read(std::istream& stream,T& value) {
  require(static_cast<bool>(stream.read(reinterpret_cast<char*>(&value),sizeof(value))),"truncated fixture");
}
std::array<char,8> resref_bytes(const std::string& s) {
  std::array<char,8> result{};require(s.size()<=8,"bad resref");std::memcpy(result.data(),s.data(),s.size());return result;
}
bool resolve(unsigned animation,const std::string& name,int slot,cs::FrameHandle& h) {
  const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
  do {
    if(cs::resolve_frame(static_cast<std::uint16_t>(animation),resref_bytes(name),0,slot,h,
          animation==0x6110 ? cs::FrameResolveMode::WaitForCharacterMetadata : cs::FrameResolveMode::NonBlocking)) return true;
    if(!cs::pending_catalog_loads()) return false;
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  } while(std::chrono::steady_clock::now()<deadline);
  throw std::runtime_error("catalog worker timeout");
}
std::uint32_t swap_rb(std::uint32_t p) { return (p&0xff00ff00u)|((p&255u)<<16)|((p>>16)&255u); }

std::array<unsigned char,32> hash_pixels(const std::vector<std::uint32_t>& pixels) {
  std::array<unsigned char,32> result{};
  require(pixels.size()<=(std::numeric_limits<ULONG>::max)()/4,"hash size overflow");
  require(BCryptHash(BCRYPT_SHA256_ALG_HANDLE,nullptr,0,
      reinterpret_cast<PUCHAR>(const_cast<std::uint32_t*>(pixels.data())),
      static_cast<ULONG>(pixels.size()*4),result.data(),static_cast<ULONG>(result.size()))>=0,"pixel SHA256 failed");
  return result;
}

void inspect_produced_pack(const fs::path& assets,const fs::path& oracle) {
  const auto start=std::chrono::steady_clock::now();
  std::ifstream input(oracle,std::ios::binary);require(static_cast<bool>(input),"pack oracle missing");
  std::array<char,8> magic{};read(input,magic);
  require(magic==std::array<char,8>{'I','E','E','Q','M','4','\0','\0'},"pack oracle magic");
  unsigned np{},nf{},profile{},animation{},nc{};
  read(input,np);read(input,nf);read(input,profile);read(input,animation);read(input,nc);
  require(np==9&&nf>0&&nf<=65535&&nc>0&&nc<=255&&pf::monster_profile(profile,2)&&
      pf::monster_owner(profile,3,static_cast<std::uint16_t>(animation)),"pack oracle contract");
  std::array<char,8> name{};read(input,name);
  const std::string resref(name.data(),std::find(name.begin(),name.end(),'\0')-name.begin());
  std::array<std::byte,32> sourceSha{};read(input,sourceSha);
  require(pf::monster_resource(profile,resref,sourceSha),"pack oracle source identity");
  std::vector<pf::Palette> palettes(np);for(auto& palette:palettes)read(input,palette);
  std::vector<std::vector<unsigned>> cycles(nc);
  for(auto& cycle:cycles) {
    unsigned count{};read(input,count);require(count<=65535,"oracle cycle size");cycle.resize(count);
    for(auto& index:cycle) {read(input,index);require(index<nf,"oracle cycle index");}
  }
  require(cs::prepare(assets)&&cs::contains_animation(static_cast<std::uint16_t>(animation)),"pack catalog prepare");
  cs::FrameHandle handle{};unsigned slots=0;bool resolvedAny=false;
  for(unsigned c=0;c<nc;++c) {
    for(unsigned s=0;s<cycles[c].size();++s) {
      // Cold Monster metadata uses the existing asynchronous resolver; wait only in this host test.
      const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
      bool ok=false;
      do {
        if(cs::resolve_frame(static_cast<std::uint16_t>(animation),name,static_cast<int>(c),static_cast<int>(s),handle)) {ok=true;break;}
        if(!cs::pending_catalog_loads()) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      } while(std::chrono::steady_clock::now()<deadline);
      require(ok&&handle.frameIndex==cycles[c][s],"produced native cycle/slot/frame identity");
      resolvedAny=true;++slots;
    }
    cs::FrameHandle invalid{};
    require(!cs::resolve_frame(static_cast<std::uint16_t>(animation),name,static_cast<int>(c),
                              static_cast<int>(cycles[c].size()),invalid),"out-of-range cycle slot accepted");
  }
  require(resolvedAny,"produced resource has no native cycle slots");
  require(cs::frame_requires_fixed_monster_palette(handle)&&
          cs::frame_accepts_fixed_monster_palette(handle,0,pf::kMonsterSourceRgb[profile-2]),"produced fixed palette routing");
  std::uint64_t decoded=0,peakResident=0,peakMetadata=0;
  for(unsigned index=0;index<nf;++index) {
    unsigned w{},h{};int cx{},cy{};read(input,w);read(input,h);read(input,cx);read(input,cy);
    require(w>0&&h>0&&static_cast<std::uint64_t>(w)*h<65535,"oracle frame geometry");
    handle.frameIndex=index; // Host-only access also covers native frames absent from cycle slots.
    for(unsigned p=0;p<np;++p) {
      std::array<unsigned char,32> expected{};read(input,expected);
      for(unsigned encoding=0;encoding<3;++encoding) {
        cs::PaletteSnapshot palette{};palette.colors=palettes[p];palette.encoding={0x1908,0x1401};
        if(encoding) {palette.encoding={0x80e1,encoding==1?0x1401u:0x8367u};for(auto& color:palette.colors)color=swap_rb(color);}
        std::vector<std::uint32_t> pixels;std::uint64_t fingerprint{};
        require(cs::reconstruct_frame_pixels(handle,palette,pixels,fingerprint)&&pixels.size()==w*h*4,
                "produced frame reconstruct/geometry");
        if(encoding)for(auto& color:pixels)color=swap_rb(color);
        require(hash_pixels(pixels)==expected,"produced scalar/native pixel SHA mismatch");
        decoded+=pixels.size();
      }
    }
    // A single-layer composition derives bounds from parsed native centres, not oracle geometry.
    cs::CompositeLayer layer{};layer.frame=handle;layer.palette.encoding={0x1908,0x1401};layer.palette.colors=palettes[0];
    std::vector<std::uint32_t> composite;cs::CompositeBounds bounds{};
    require(cs::reconstruct_composite_pixels(&layer,1,composite,bounds)&&
            bounds.left==-cx&&bounds.top==-cy&&bounds.right==static_cast<int>(w)-cx&&
            bounds.bottom==static_cast<int>(h)-cy&&composite.size()==(w+2)*(h+2)*4,"produced native centres/composition bounds");
    peakResident=std::max(peakResident,cs::resident_index_bytes());
    peakMetadata=std::max(peakMetadata,cs::resident_catalog_metadata_bytes());
  }
  require(input.peek()==EOF,"pack oracle trailing data");cs::release();
  const auto ms=std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-start).count();
  std::cout<<"{\"resref\":\""<<resref<<"\",\"profile_id\":"<<profile<<",\"frames\":"<<nf
      <<",\"cycles\":"<<nc<<",\"cycle_slots\":"<<slots<<",\"palettes\":"<<np
      <<",\"native_encodings\":3,\"decoded_pixels\":"<<decoded<<",\"native_centres_identical\":true"
      <<",\"peak_resident_I_F_bytes\":"<<peakResident<<",\"peak_metadata_bytes\":"<<peakMetadata
      <<",\"elapsed_ms\":"<<ms<<"}\n";
}

int main(int argc,char** argv) {
  try {
    if(argc==4&&std::string(argv[1])=="--pack") {inspect_produced_pack(fs::path(argv[2]),fs::path(argv[3]));return 0;}
    require(argc==2,"usage: palette_monster_tests fixtures");const fs::path root(argv[1]);
    std::ifstream cases(root/"cases.tsv");require(static_cast<bool>(cases),"missing cases");
    unsigned accepted=0,rejected=0;std::uint64_t decoded=0;
    std::string line;
    while(std::getline(cases,line)) {
      std::istringstream row(line);std::string name,status,resref;unsigned animation{};row>>name>>status>>animation>>resref;
      cs::FrameHandle h{};const bool ok=cs::prepare(root/name)&&resolve(animation,resref,0,h);
      if(ok!=(status=="ok")) throw std::runtime_error("case unexpectedly "+std::string(ok?"accepted: ":"rejected: ")+name);
      if(ok) {
        ++accepted;require(cs::frame_uses_q3m_profile(h)&&cs::frame_requires_fixed_monster_palette(h),"Monster profile routing");
        std::ifstream fixture(root/(name+".bin"),std::ios::binary);unsigned pid{},rule{},palettes{},pixels{};
        read(fixture,pid);read(fixture,rule);read(fixture,palettes);read(fixture,pixels);
        require(rule==2&&pid>=2&&pid<=7&&pixels==2028,"golden dimensions");
        auto source=pf::kMonsterSourceRgb[pid-2];
        require(cs::frame_accepts_fixed_monster_palette(h,0,source),"fixed native source palette");
        require(!cs::frame_accepts_fixed_monster_palette(h,1,source),"false-color palette accepted");
        source[3]^=1;require(!cs::frame_accepts_fixed_monster_palette(h,0,source),"changed source RGB accepted");source[3]^=1;
        source[3]|=128u<<24;require(!cs::frame_accepts_fixed_monster_palette(h,0,source),"unsupported reserved alpha accepted");
        for(unsigned p=0;p<palettes;++p) {
          cs::PaletteSnapshot palette{};palette.encoding={0x1908,0x1401};read(fixture,palette.colors);
          std::vector<std::uint32_t> expected(pixels);for(auto& color:expected) read(fixture,color);
          for(unsigned bgra=0;bgra<3;++bgra) {
            auto native=palette;auto oracle=expected;
            if(bgra) { native.encoding={0x80e1,bgra==1?0x1401u:0x8367u};for(auto& c:native.colors)c=swap_rb(c);for(auto& c:oracle)c=swap_rb(c); }
            std::vector<std::uint32_t> actual;std::uint64_t fingerprint{};
            require(cs::reconstruct_frame_pixels(h,native,actual,fingerprint)&&actual==oracle,"integer decoder golden mismatch");
            decoded+=actual.size();
          }
          if(name.find("zero")==std::string::npos) {
            palette.colors[pf::successor(3, pid)]^=1u<<24;
            std::vector<std::uint32_t> actual;std::uint64_t fingerprint{};
            require(!cs::reconstruct_frame_pixels(h,palette,actual,fingerprint)&&actual.empty(),"unequal live alpha accepted");
          }
        }
        cs::FrameHandle repeated{};require(resolve(animation,resref,1,repeated)&&h==repeated,"repeated cycle slot changed");
        require(!cs::resolve_frame(static_cast<std::uint16_t>(animation),resref_bytes(resref),1,0,repeated),"empty cycle accepted");
      } else { ++rejected; }
      cs::release();require(!cs::ensure_frame_payload_available(h),"stale handle accepted");
    }
    require(accepted==18&&rejected==10,"case count");
    require(cs::prepare(root/"mixed"),"mixed catalog prepare");
    cs::FrameHandle monster{},character{};
    require(resolve(0x7f30,"NBOHG1",0,monster)&&resolve(0x6110,"CHAR",0,character),"mixed owner catalog resolution");
    require(cs::frame_requires_fixed_monster_palette(monster)&&!cs::frame_requires_fixed_monster_palette(character),"mixed profile isolation");
    cs::PaletteSnapshot palette{};palette.encoding={0x1908,0x1401};palette.colors[4]=0x4d000000u;palette.colors[5]=0xff505050u;
    std::vector<std::uint32_t> actual;std::uint64_t fingerprint{};
    require(cs::reconstruct_frame_pixels(character,palette,actual,fingerprint)&&actual==std::vector<std::uint32_t>(16,0x4d1e1e1eu),"Character decode/primary alpha regression");
    cs::release();std::cout<<"{\"accepted\":"<<accepted<<",\"rejected\":"<<rejected<<",\"decoded_pixels\":"<<decoded<<",\"mixed_character_monster\":true}\n";
    return 0;
  } catch(const std::exception& error) {cs::release();std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}
}
