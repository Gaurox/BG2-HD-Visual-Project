#include <algorithm>
#include <array>
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
 require(argc==5,"usage assets native-oracle primary secondary");require(cs::prepare(std::filesystem::path(argv[1])),"catalog rejected");
 std::array<std::array<unsigned,256>,2> palettes{};
 for(int i=0;i<2;++i){std::ifstream p(argv[i+3],std::ios::binary);read(p,palettes[i]);}
 std::ifstream f(argv[2],std::ios::binary);std::array<char,8> magic{};unsigned nr{};read(f,magic);read(f,nr);
 require(magic==std::array<char,8>{'I','E','E','N','A','T','0','2'}&&nr==14,"oracle header");
 unsigned long long checks=0,cycles=0,paletteChecks=0,frames=0,world=0;
 for(unsigned r=0;r<nr;++r){
  unsigned aid{},nf{},nc{};std::array<char,8> ref{};read(f,aid);read(f,ref);read(f,nf);read(f,nc);require(aid==0x7314,"wrong ID");
  std::vector<std::vector<unsigned>> lookup(nc);cs::FrameHandle first{};bool found=false;
  for(auto& cycle:lookup){unsigned n{};read(f,n);cycle.resize(n);for(auto& v:cycle)read(f,v);}
  for(unsigned seq=0;seq<nc;++seq){++cycles;const auto& c=lookup[seq];int n=int(c.size());
   for(auto mode:{cs::FramePlaybackMode::Clamp,cs::FramePlaybackMode::Loop}){
    for(int slot:{0,n/2,n-1,n,n+1,2*n+1,-1,-n,-n-1,32767,-32768}){
     cs::FrameHandle h{};bool ok=cs::resolve_frame(aid,ref,seq,slot,h,cs::FrameResolveMode::WaitForMonsterMetadata,mode);
     unsigned expected=n?c[mode==cs::FramePlaybackMode::Loop?((slot%n)+n)%n:std::clamp(slot,0,n-1)]:nf;
     require(ok==(expected<nf),"native lookup status differs");if(ok){require(h.frameIndex==expected,"native frame differs");if(!found){first=h;found=true;}}++checks;
    }
   }
  }
  require(found,"no valid native frame");frames+=nf;
  if(std::string(ref.data(),8).find("INV")!=std::string::npos)continue;
  int bank=ref[5]=='1'?0:1;unsigned count=bank==0?253:252;
  for(unsigned i=0;i<nf;++i){auto h=first;h.frameIndex=i;
   require(cs::frame_accepts_fixed_monster_palette(h,0,palettes[bank],count),"actual native palette rejected");
   require(!cs::frame_accepts_fixed_monster_palette(h,0,palettes[1-bank],count),"wrong bank palette accepted");
   require(!cs::frame_accepts_fixed_monster_palette(h,0,palettes[bank],bank?253:252),"wrong native count accepted");
   require(!cs::frame_accepts_fixed_monster_palette(h,1,palettes[bank],count),"wrong kind accepted");
   auto changed=palettes[bank];changed[3]^=1;require(!cs::frame_accepts_fixed_monster_palette(h,0,changed,count),"wrong RGB accepted");
   changed=palettes[bank];changed[3]^=0x01000000;require(!cs::frame_accepts_fixed_monster_palette(h,0,changed,count),"wrong alpha accepted");
   changed=palettes[bank];for(unsigned j=count;j<256;++j)changed[j]=0x13579bdf+j;
   require(cs::frame_accepts_fixed_monster_palette(h,0,changed,256),"unused advertised tail rejected");
   for(unsigned bad:{0u,251u,254u,257u})require(!cs::frame_accepts_fixed_monster_palette(h,0,palettes[bank],bad),"wrong count accepted");
   ++world;paletteChecks+=11;
  }
 }
 cs::release();std::cout<<"{\"passed\":true,\"resources\":"<<nr<<",\"frames\":"<<frames<<",\"world_frames\":"<<world<<",\"cycles\":"<<cycles<<",\"native_playback_checks\":"<<checks<<",\"palette_guard_checks\":"<<paletteChecks<<",\"missing_or_wrong_frames\":0}\n";return 0;
}catch(const std::exception& e){cs::release();std::cerr<<e.what()<<"\n";return 1;}}
