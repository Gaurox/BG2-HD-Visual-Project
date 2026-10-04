#include <algorithm>
#include <array>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>
#include <windows.h>
#include <bcrypt.h>
#include "iee/creature_sprite_x2.h"
#include "iee/game/build_manifest.h"
namespace iee::probe { void record_creature_texture_trace(unsigned,int,int,int,int,int,std::string_view) noexcept {} }
namespace cs=iee::creature_sprite_x2;
void require(bool b,const char* s){if(!b)throw std::runtime_error(s);}
template<class T> void read(std::istream& f,T& v){require(bool(f.read(reinterpret_cast<char*>(&v),sizeof(v))),"truncated composite oracle");}
bool resolve(unsigned a,const std::array<char,8>& r,unsigned c,unsigned s,cs::FrameHandle& h){
  const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
  do {if(cs::resolve_frame(static_cast<std::uint16_t>(a),r,c,s,h))return true;
      if(!cs::pending_catalog_loads())return false;
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }while(std::chrono::steady_clock::now()<deadline);return false;
}
std::array<unsigned char,32> sha(std::vector<std::uint32_t>& p){
  std::array<unsigned char,32> out{};
  require(BCryptHash(BCRYPT_SHA256_ALG_HANDLE,nullptr,0,reinterpret_cast<PUCHAR>(p.data()),static_cast<ULONG>(p.size()*4),out.data(),32)>=0,"hash failed");return out;
}
int main(int argc,char** argv){try{
  const auto manifest=iee::game::find_manifest("BG2EE 2.7.3.x");
  require(bool(manifest),"BG2EE manifest absent");
  require(manifest->get().areaAnimations.monsterQuadrantRender==0x3305a0,"native Quadrant hook differs");
  require(argc==3,"usage: composite_probe assets composite.oracle|regression");
  require(cs::prepare(std::filesystem::path(argv[1])),"catalog rejected");
  if(std::strcmp(argv[2],"regression")==0){
    unsigned missing=0;
    for(unsigned a:{0x6400u,0x6401u,0x6403u}){std::array<char,8> r={'C','S','H','D','G','1',0,0};cs::FrameHandle h{};missing+=!resolve(a,r,16,31,h);}
    cs::release();require(missing==3,"old catalog must reproduce the three missing shadow dependencies");
    std::cout<<"{\"old_catalog_missing_shadows\":3,\"passed\":true}\n";return 0;
  }
  std::ifstream f(argv[2],std::ios::binary);std::array<char,8> m{};unsigned n{};read(f,m);read(f,n);
  require(m==std::array<char,8>{'I','E','E','O','L','D','1',0}&&n>0,"oracle header");
  std::uint64_t layersTotal=0,pixelsTotal=0;unsigned cases=0;
  for(unsigned k=0;k<n;++k){unsigned count{};read(f,count);require(count==4,"native four quadrants");std::vector<cs::CompositeLayer> layers(count);
    for(auto& layer:layers){std::array<unsigned,5> metadata{};std::array<char,8> ref{};std::array<std::uint32_t,256> source{};
      read(f,metadata);read(f,ref);read(f,source);read(f,layer.palette.colors);layer.palette.encoding={0x1908,0x1401};
      require(cs::animation_targets_owner(static_cast<std::uint16_t>(metadata[0]),4),"wrong native owner");
      require(resolve(metadata[0],ref,metadata[1],metadata[2],layer.frame),"complete native layer failed to resolve");
      require(layer.frame.frameIndex==metadata[3],"native cycle selected wrong frame");
      require(cs::frame_accepts_fixed_monster_palette(layer.frame,static_cast<std::uint16_t>(metadata[4]),source),"native layer palette rejected");
      require(cs::ensure_frame_payload_available(layer.frame),"layer payload unavailable");
    }
    const auto nativeCount=layers.size();
    layers.erase(std::remove_if(layers.begin(),layers.end(),[](const auto& layer){return cs::frame_is_native_empty_quadrant(layer.frame);}),layers.end());
    require(!layers.empty(),"fully empty native case");
    std::array<int,4> expectedBounds{};std::array<unsigned char,32> expected{};read(f,expectedBounds);read(f,expected);
    std::vector<std::uint32_t> pixels;cs::CompositeBounds bounds{};
    require(cs::reconstruct_composite_pixels(layers.data(),layers.size(),pixels,bounds),"complete composite unavailable");
    require(std::array<int,4>{bounds.left,bounds.top,bounds.right,bounds.bottom}==expectedBounds,"body/shadow/equipment origin changed");
    require(sha(pixels)==expected,"complete composite pixels differ");pixelsTotal+=pixels.size();layersTotal+=nativeCount;++cases;
  }
  require(f.peek()==std::char_traits<char>::eof(),"trailing composite oracle");cs::release();
  std::cout<<"{\"native_composites\":"<<cases<<",\"resolved_layers\":"<<layersTotal<<",\"decoded_pixels\":"<<pixelsTotal<<",\"missing_layers\":0,\"passed\":true}\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";cs::release();return 1;}}
