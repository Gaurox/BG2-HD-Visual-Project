#include <algorithm>
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
  require(argc==4,"usage assets oracle short-palette");require(cs::prepare(std::filesystem::path(argv[1])),"catalog rejected");
  std::ifstream f(argv[2],std::ios::binary);std::array<char,8> magic{};unsigned resources{};read(f,magic);read(f,resources);
  require(magic==std::array<char,8>{'I','E','E','N','A','T','0','2'}&&resources==1040,"oracle header");
  std::ifstream p(argv[3],std::ios::binary);std::array<std::uint32_t,256> palette{};read(p,palette);
  unsigned long long checks=0,cycles=0,empty=0,strictRejected=0,invalid=0,coldMisses=0,paletteChecks=0,shortAccepted=0;
  auto check=[&](unsigned aid,const std::array<char,8>& ref,int seq,int slot,cs::FramePlaybackMode playback,unsigned expected,unsigned nf){
    cs::FrameHandle h{};const bool ok=cs::resolve_frame(aid,ref,seq,slot,h,cs::FrameResolveMode::WaitForMonsterMetadata,playback);
    if(expected<nf){
      if(!ok||h.frameIndex!=expected){std::cerr<<"FAIL id="<<std::hex<<aid<<" ref="<<std::string(ref.data(),8)<<std::dec<<" seq="<<seq<<" slot="<<slot<<" expected="<<expected<<" got="<<h.frameIndex<<" ok="<<ok<<"\n";throw std::runtime_error("native frame differs");}
    }else{require(!ok,"invalid native frame resolved");++invalid;}
    ++checks;
  };
  for(unsigned r=0;r<resources;++r){
    unsigned aid{},nf{},nc{};std::array<char,8> ref{};read(f,aid);read(f,ref);read(f,nf);read(f,nc);
    require(cs::animation_targets_owner(aid,3),"wrong owner");
    std::vector<std::vector<unsigned>> lookup(nc);
    for(auto& cycle:lookup){unsigned n{};read(f,n);cycle.resize(n);for(auto& index:cycle)read(f,index);}
    cs::FrameHandle cold{};
    if(!cs::resolve_frame(aid,ref,0,0,cold,cs::FrameResolveMode::NonBlocking))++coldMisses;
    for(unsigned seq=0;seq<nc;++seq){
      ++cycles;const auto& cycle=lookup[seq];const int n=int(cycle.size());
      if(!n){++empty;for(auto mode:{cs::FramePlaybackMode::Clamp,cs::FramePlaybackMode::Loop})check(aid,ref,seq,0,mode,nf,nf);continue;}
      for(auto mode:{cs::FramePlaybackMode::Clamp,cs::FramePlaybackMode::Loop}){
        for(int slot:{0,n/2,n-1,n,n+1,2*n+1,-1,-n,-n-1,32767,-32768}){
          int normalized=mode==cs::FramePlaybackMode::Loop?((slot%n)+n)%n:std::clamp(slot,0,n-1);
          check(aid,ref,seq,slot,mode,cycle[normalized],nf);
        }
      }
      cs::FrameHandle h{};
      require(!cs::resolve_frame(aid,ref,seq,n,h,cs::FrameResolveMode::WaitForMonsterMetadata),"strict overflow changed");
      require(!cs::resolve_frame(aid,ref,seq,-1,h,cs::FrameResolveMode::WaitForMonsterMetadata),"strict negative changed");strictRejected+=2;
      const auto valid=std::find_if(cycle.begin(),cycle.end(),[&](unsigned v){return v<nf;});
      if(valid!=cycle.end()){
        const int slot=int(valid-cycle.begin());require(cs::resolve_frame(aid,ref,seq,slot,h,cs::FrameResolveMode::WaitForMonsterMetadata),"valid frame missing");
        if(aid==0x7314&&std::string(ref.data(),8).find("INV")==std::string::npos){
          require(cs::frame_accepts_fixed_monster_palette(h,0,palette,252),"native 252-entry palette rejected");++shortAccepted;
          require(!cs::frame_accepts_fixed_monster_palette(h,1,palette,252),"wrong short kind accepted");
          for(unsigned count:{0u,251u,253u,257u})require(!cs::frame_accepts_fixed_monster_palette(h,0,palette,count),"wrong short count accepted");
          auto changed=palette;changed[2]^=1;require(!cs::frame_accepts_fixed_monster_palette(h,0,changed,252),"changed palette accepted");
          changed=palette;changed[251]^=0x01000000;require(!cs::frame_accepts_fixed_monster_palette(h,0,changed,252),"partial alpha accepted");
          auto tail=palette;
          for(unsigned j=252;j<256;++j)tail[j]=0x13579bdfu+j;
          require(cs::frame_accepts_fixed_monster_palette(h,0,tail,256),"unused advertised tail rejected");
          tail[2]^=1;require(!cs::frame_accepts_fixed_monster_palette(h,0,tail,256),"changed declared prefix accepted");
          paletteChecks+=9;
        }else{
          require(!cs::frame_accepts_fixed_monster_palette(h,0,palette,252),"short palette accepted for another resource");++paletteChecks;
        }
      }
    }
    const auto& zero=lookup[0];const unsigned first=zero.empty()?nf:zero[0];
    for(auto mode:{cs::FramePlaybackMode::Clamp,cs::FramePlaybackMode::Loop}){
      check(aid,ref,nc,0,mode,first,nf);check(aid,ref,-1,0,mode,first,nf);
    }
  }
  cs::FrameHandle h{};std::array<char,8> absent{'N','O','S','U','C','H'};
  require(!cs::resolve_frame(0x7314,absent,0,8,h,cs::FrameResolveMode::WaitForMonsterMetadata,cs::FramePlaybackMode::Loop),"unknown resource accepted");
  std::array<char,8> ice{'M','M','I','N','A','1'};
  require(!cs::resolve_frame(0xE070,ice,0,-1,h,cs::FrameResolveMode::WaitForMonsterMetadata,cs::FramePlaybackMode::Loop),"Icewind normalized with Monster mode");
  std::array<char,8> old{'M','L','O','F','G','1'};
  require(!cs::resolve_frame(0x7B06,old,0,-1,h,cs::FrameResolveMode::WaitForMonsterMetadata,cs::FramePlaybackMode::Loop),"Monster_old normalized with Monster mode");
  require(shortAccepted>0,"no Burning Man short palette checks");cs::release();
  std::cout<<"{\"passed\":true,\"resources\":"<<resources<<",\"cycles\":"<<cycles<<",\"empty_cycles\":"<<empty<<",\"native_playback_checks\":"<<checks<<",\"strict_out_of_range_rejected\":"<<strictRejected<<",\"invalid_lookup_checks\":"<<invalid<<",\"baseline_nonblocking_cold_misses\":"<<coldMisses<<",\"short_palette_acceptance_checks\":"<<shortAccepted<<",\"palette_guard_checks\":"<<paletteChecks<<",\"missing_or_wrong_frames\":0}\n";
  return 0;
}catch(const std::exception& e){cs::release();std::cerr<<e.what()<<"\n";return 1;}}
