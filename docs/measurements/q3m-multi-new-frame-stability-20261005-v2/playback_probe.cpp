#include <array>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include "iee/creature_sprite_x2.h"
namespace iee::probe {void record_creature_texture_trace(unsigned,int,int,int,int,int,std::string_view) noexcept {}}
namespace cs=iee::creature_sprite_x2;
void require(bool b,const char* why){if(!b)throw std::runtime_error(why);}
template<class T>void read(std::istream& f,T& v){require(bool(f.read(reinterpret_cast<char*>(&v),sizeof(v))),"truncated oracle");}
int main(int argc,char** argv){try{
  require(argc==3,"usage assets oracle");require(cs::prepare(std::filesystem::path(argv[1])),"catalog rejected");
  std::ifstream f(argv[2],std::ios::binary);std::array<char,8> magic{};unsigned resources{};read(f,magic);read(f,resources);
  require(magic==std::array<char,8>{'I','E','E','N','A','T','0','2'}&&resources==5155,"oracle header");
  unsigned long long checks=0,cycles=0,emptyCycles=0,strictRejected=0,invalidLookups=0;
  auto check=[&](unsigned aid,const std::array<char,8>& ref,int seq,int slot,cs::FramePlaybackMode playback,unsigned expected,unsigned frameCount){
    cs::FrameHandle h{};
    const bool ok=cs::resolve_frame(aid,ref,seq,slot,h,cs::FrameResolveMode::WaitForMultiNewMetadata,playback);
    if(expected<frameCount){
      if(!ok||h.frameIndex!=expected){std::cerr<<"FAIL id="<<std::hex<<aid<<" ref="<<std::string(ref.data(),8)<<std::dec<<" seq="<<seq<<" slot="<<slot<<" playback="<<int(playback)<<" expected="<<expected<<" got="<<h.frameIndex<<" ok="<<ok<<"\n";throw std::runtime_error("native frame differs");}
    }else{require(!ok,"invalid native lookup must fail closed");++invalidLookups;}
    ++checks;
  };
  for(unsigned r=0;r<resources;++r){
    unsigned aid{},frameCount{},cycleCount{};std::array<char,8> ref{};
    read(f,aid);read(f,ref);read(f,frameCount);read(f,cycleCount);
    require(cs::animation_targets_owner(aid,5),"wrong owner");
    std::vector<std::vector<unsigned>> lookup(cycleCount);
    for(auto& cycle:lookup){unsigned n{};read(f,n);cycle.resize(n);for(auto& index:cycle)read(f,index);}
    for(unsigned seq=0;seq<cycleCount;++seq){
      ++cycles;const auto& cycle=lookup[seq];const int n=int(cycle.size());
      if(!n){++emptyCycles;for(auto mode:{cs::FramePlaybackMode::Clamp,cs::FramePlaybackMode::Loop})check(aid,ref,seq,0,mode,frameCount,frameCount);continue;}
      for(auto mode:{cs::FramePlaybackMode::Clamp,cs::FramePlaybackMode::Loop}){
        for(int slot:{0,n/2,n-1,n,n+1,2*n+1,-1,-n,-n-1}){
          // Oracle arithmetic independently confirmed against actual native x64 instructions.
          int normalized=slot;
          if(mode==cs::FramePlaybackMode::Loop) normalized=((slot%n)+n)%n;
          else normalized=slot<0?0:(slot>=n?n-1:slot);
          check(aid,ref,seq,slot,mode,cycle[normalized],frameCount);
        }
      }
      cs::FrameHandle h{};
      require(!cs::resolve_frame(aid,ref,seq,n,h,cs::FrameResolveMode::WaitForMultiNewMetadata),"strict mode changed");
      require(!cs::resolve_frame(aid,ref,seq,-1,h,cs::FrameResolveMode::WaitForMultiNewMetadata),"strict negative mode changed");
      strictRejected+=2;
    }
    const auto& zero=lookup[0];const unsigned first=zero.empty()?frameCount:zero[0];
    for(auto mode:{cs::FramePlaybackMode::Clamp,cs::FramePlaybackMode::Loop}){
      check(aid,ref,cycleCount,0,mode,first,frameCount);
      check(aid,ref,-1,0,mode,first,frameCount);
    }
  }
  cs::FrameHandle h{};std::array<char,8> absent{'N','O','S','U','C','H'};
  require(!cs::resolve_frame(0x1207,absent,0,8,h,cs::FrameResolveMode::WaitForMultiNewMetadata,cs::FramePlaybackMode::Loop),"unknown resource accepted");
  std::array<char,8> ankheg{'M','A','K','H','G','1'};
  require(!cs::resolve_frame(0x3000,ankheg,0,-1,h,cs::FrameResolveMode::WaitForMultiNewMetadata,cs::FramePlaybackMode::Loop),"other owner normalized");
  cs::release();
  std::cout<<"{\"passed\":true,\"resources\":"<<resources<<",\"cycles\":"<<cycles<<",\"empty_cycles\":"<<emptyCycles<<",\"native_playback_checks\":"<<checks<<",\"strict_out_of_range_rejected\":"<<strictRejected<<",\"invalid_lookup_checks\":"<<invalidLookups<<",\"missing_or_wrong_frames\":0}\n";
  return 0;
}catch(const std::exception& e){cs::release();std::cerr<<e.what()<<"\n";return 1;}}
