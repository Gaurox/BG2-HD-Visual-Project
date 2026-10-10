#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#include <vector>
#include "iee/creature_sprite_x2.h"
namespace iee::probe {void record_creature_texture_trace(unsigned,int,int,int,int,int,std::string_view) noexcept {}}
namespace cs=iee::creature_sprite_x2;
void need(bool b,const char* why){if(!b)throw std::runtime_error(why);}
template<class T>void read(std::istream& f,T& v){need(bool(f.read(reinterpret_cast<char*>(&v),sizeof(v))),"truncated oracle");}
int main(int argc,char** argv){try{
  need(argc==3,"usage assets oracle");need(cs::prepare(std::filesystem::path(argv[1])),"catalog rejected");
  std::ifstream f(argv[2],std::ios::binary);std::array<char,8> magic{};unsigned resources{};read(f,magic);read(f,resources);
  need(magic==std::array<char,8>{'I','E','E','A','L','L','0','1'},"oracle header");
  unsigned long long checks=0,cycles=0,empty=0,invalid=0,strict=0,aliases=0,cold=0;std::set<unsigned> ids,owners;
  bool observed=false;
  for(unsigned r=0;r<resources;++r){
    unsigned aid{},owner{},nf{},nc{},na{};std::array<char,8> ref{};
    read(f,aid);read(f,owner);read(f,ref);read(f,nf);read(f,nc);read(f,na);
    std::vector<unsigned> aids(na);for(auto& id:aids){read(f,id);ids.insert(id);}owners.insert(owner);
    std::vector<std::vector<unsigned>> lookup(nc);
    for(auto& c:lookup){unsigned n{};read(f,n);c.resize(n);for(auto& i:c)read(f,i);}
    auto check=[&](unsigned id,int seq,int slot,cs::FramePlaybackMode mode,unsigned expected){
      cs::FrameHandle h{};const bool ok=cs::resolve_frame(id,ref,seq,slot,h,cs::FrameResolveMode::WaitForRegisteredMetadata,mode);
      if(expected<nf){if(!ok||h.frameIndex!=expected){std::cerr<<"FAIL id="<<std::hex<<id<<" ref="<<std::string(ref.data(),8)<<std::dec<<" seq="<<seq<<" slot="<<slot<<" expected="<<expected<<" got="<<h.frameIndex<<" ok="<<ok<<"\n";throw std::runtime_error("native frame differs");}}
      else {need(!ok,"invalid lookup resolved");++invalid;}++checks;
    };
    // First request waits for exact metadata; no polling or prior contains_resource call.
    check(aid,0,0,cs::FramePlaybackMode::Loop,lookup[0].empty()?nf:lookup[0][0]);++cold;
    for(unsigned seq=0;seq<nc;++seq){
      ++cycles;const auto& c=lookup[seq];const int n=int(c.size());
      if(!n){++empty;for(auto mode:{cs::FramePlaybackMode::Clamp,cs::FramePlaybackMode::Loop})check(aid,seq,0,mode,nf);continue;}
      // Every native cycle slot; boundary/negative/overflow slots in both playback modes.
      for(int slot=0;slot<n;++slot)check(aid,seq,slot,cs::FramePlaybackMode::Loop,c[slot]);
      for(auto mode:{cs::FramePlaybackMode::Clamp,cs::FramePlaybackMode::Loop}){
        for(int slot:{0,n-1,n,n+1,2*n+1,-1,-n,-n-1,32767,-32768}){
          int norm=mode==cs::FramePlaybackMode::Loop?((slot%n)+n)%n:std::clamp(slot,0,n-1);
          check(aid,seq,slot,mode,c[norm]);
        }
      }
      cs::FrameHandle h{};
      need(!cs::resolve_frame(aid,ref,seq,n,h,cs::FrameResolveMode::WaitForRegisteredMetadata),"default Strict overflow changed");
      need(!cs::resolve_frame(aid,ref,seq,-1,h,cs::FrameResolveMode::WaitForRegisteredMetadata),"default Strict negative changed");strict+=2;
      if(std::find(aids.begin(),aids.end(),0x6110)!=aids.end()&&ref==std::array<char,8>{'C','H','F','F','4','G','1','\0'}&&seq==15){
        need(n==12,"observed cycle differs");
        check(0x6110,15,12,cs::FramePlaybackMode::Loop,c[0]);
        check(0x6110,15,12,cs::FramePlaybackMode::Clamp,c[11]);observed=true;
      }
    }
    for(auto id:aids){
      need(cs::animation_targets_owner(id,owner),"alias owner differs");
      check(id,0,0,cs::FramePlaybackMode::Loop,lookup[0].empty()?nf:lookup[0][0]);++aliases;
    }
    for(auto mode:{cs::FramePlaybackMode::Loop,cs::FramePlaybackMode::Clamp}){
      const auto expected=lookup[0].empty()?nf:lookup[0][0];
      check(aid,nc,0,mode,expected);check(aid,-1,0,mode,expected);
    }
    if((r+1)%1000==0)std::cout<<"progress "<<r+1<<"/"<<resources<<" checks="<<checks<<std::endl;
  }
  cs::FrameHandle h{};std::array<char,8> unknown{'N','O','S','U','C','H'};
  need(!cs::resolve_frame(0x6110,unknown,0,12,h,cs::FrameResolveMode::WaitForRegisteredMetadata,cs::FramePlaybackMode::Loop),"unknown resref accepted");
  need(!cs::resolve_frame(0xFFFF,unknown,0,12,h,cs::FrameResolveMode::WaitForRegisteredMetadata,cs::FramePlaybackMode::Loop),"unknown ID accepted");
  need(observed&&ids.size()==331,"coverage incomplete");cs::release();
  std::cout<<"{\"passed\":true,\"animation_ids\":"<<ids.size()<<",\"owner_types\":"<<owners.size()<<",\"resources\":"<<resources<<",\"routes\":"<<aliases<<",\"cycles\":"<<cycles<<",\"empty_cycles\":"<<empty<<",\"playback_checks\":"<<checks<<",\"invalid_lookup_checks\":"<<invalid<<",\"strict_rejections\":"<<strict<<",\"first_cold_requests\":"<<cold<<",\"observed_6110_fixed\":true,\"missing_or_wrong_frames\":0}\n";
  return 0;
}catch(const std::exception& e){cs::release();std::cerr<<e.what()<<"\n";return 1;}}
