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
 require(argc==3,"usage assets oracle");require(cs::prepare(std::filesystem::path(argv[1])),"catalog rejected");
 std::ifstream f(argv[2],std::ios::binary);std::array<char,8> magic{};unsigned nr{};read(f,magic);read(f,nr);
 require(magic==std::array<char,8>{'I','E','E','B','A','N','K','1'}&&nr==27,"oracle header");
 unsigned long long frames=0,cycles=0,playback=0,g1=0,g1Accepted=0,g2=0,g2Accepted=0,g2G1Accepted=0;
 for(unsigned r=0;r<nr;++r){
  unsigned aid{},nf{},nc{};std::array<char,8> ref{};std::array<unsigned,256> primary{},secondary{};
  read(f,aid);read(f,ref);read(f,nf);read(f,nc);read(f,primary);read(f,secondary);
  require(aid==0x7312||aid==0x7313,"wrong ID");
  std::vector<std::vector<unsigned>> lookup(nc);cs::FrameHandle first{};bool found=false;
  for(auto& c:lookup){unsigned n{};read(f,n);c.resize(n);for(auto& v:c)read(f,v);}
  for(unsigned seq=0;seq<nc;++seq){++cycles;const auto& c=lookup[seq];int n=int(c.size());
   for(auto mode:{cs::FramePlaybackMode::Clamp,cs::FramePlaybackMode::Loop})
    for(int slot:{0,n/2,n-1,n,n+1,2*n+1,-1,-n,-n-1,32767,-32768}){
     cs::FrameHandle h{};bool ok=cs::resolve_frame(aid,ref,seq,slot,h,cs::FrameResolveMode::WaitForMonsterMetadata,mode);
     unsigned expected=n?c[mode==cs::FramePlaybackMode::Loop?((slot%n)+n)%n:std::clamp(slot,0,n-1)]:nf;
     require(ok==(expected<nf),"native lookup status differs");if(ok){require(h.frameIndex==expected,"native frame differs");if(!found){first=h;found=true;}}++playback;
    }
  }
  require(found,"no valid native frame");frames+=nf;
  if(std::string(ref.data(),8).find("INV")!=std::string::npos)continue;
  for(unsigned i=0;i<nf;++i){auto h=first;h.frameIndex=i;
   if(ref[5]=='1'){++g1;g1Accepted+=cs::frame_accepts_fixed_monster_palette(h,0,primary,256);}
   else {require(ref[5]=='2',"wrong bank");++g2;g2Accepted+=cs::frame_accepts_fixed_monster_palette(h,0,secondary,256);g2G1Accepted+=cs::frame_accepts_fixed_monster_palette(h,0,primary,256);}
  }
 }
 cs::release();require(g1==g1Accepted&&g2>0&&g2Accepted==g2&&g2G1Accepted==0,"unexpected native bank result");
 std::cout<<"{\"audit_completed\":true,\"resources\":"<<nr<<",\"frames\":"<<frames<<",\"cycles\":"<<cycles<<",\"playback_checks\":"<<playback
 <<",\"native_playback_passed\":true,\"G1_frames\":"<<g1<<",\"G1_native_palette_accepted\":"<<g1Accepted
 <<",\"G2_frames\":"<<g2<<",\"G2_native_palette_accepted\":"<<g2Accepted<<",\"G2_wrong_G1_palette_accepted\":"<<g2G1Accepted<<",\"G2_defect_confirmed\":false,\"native_palettes_correct\":true}\n";return 0;
}catch(const std::exception& e){cs::release();std::cerr<<e.what()<<"\n";return 1;}}
