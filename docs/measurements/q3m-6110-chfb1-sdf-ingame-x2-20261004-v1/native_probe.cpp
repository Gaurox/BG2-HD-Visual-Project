#include <algorithm>
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <windows.h>
#include <bcrypt.h>
#include "iee/creature_sprite_x2.h"
namespace iee::probe {
void record_creature_texture_trace(unsigned,int,int,int,int,int,std::string_view) noexcept {}
}
namespace cs=iee::creature_sprite_x2;
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
template<class T>void read(std::istream& s,T& value){require(bool(s.read(reinterpret_cast<char*>(&value),sizeof(value))),"truncated oracle");}
std::array<unsigned char,32> sha(std::vector<std::uint32_t>& p){
  std::array<unsigned char,32> result{};
  require(BCryptHash(BCRYPT_SHA256_ALG_HANDLE,nullptr,0,reinterpret_cast<PUCHAR>(p.data()),static_cast<ULONG>(p.size()*4),result.data(),32)>=0,"hash failed");return result;
}
std::uint32_t swap(std::uint32_t p){return(p&0xff00ff00u)|((p&255u)<<16)|((p>>16)&255u);}
int main(int argc,char** argv){try{
  require(argc==4,"usage: native_probe assets oracle sdf|plain|reject");
  const std::string mode=argv[3];const bool sdf=mode=="sdf";
  std::ifstream input(argv[2],std::ios::binary);std::array<char,8> magic{};unsigned nr{},np{};
  read(input,magic);read(input,nr);read(input,np);
  require(magic==std::array<char,8>{'I','E','E','C','S','D','1','0'}&&nr==23&&np==6,"oracle scope");
  std::vector<std::array<std::uint32_t,256>> palettes(np);for(auto& p:palettes)read(input,p);
  require(cs::prepare(argv[1]),"catalog rejected");
  unsigned frames=0,slots=0,coldMisses=0;double maxWait=0;
  for(unsigned r=0;r<nr;++r){
    std::array<char,8> name{};unsigned nf{},nc{};read(input,name);read(input,nf);read(input,nc);
    std::vector<std::vector<unsigned>> cycles(nc);cs::FrameHandle base{};bool first=true;
    for(unsigned c=0;c<nc;++c){unsigned count{};read(input,count);cycles[c].resize(count);
      for(unsigned s=0;s<count;++s){read(input,cycles[c][s]);cs::FrameHandle h{};const auto start=std::chrono::steady_clock::now();
        bool ok=cs::resolve_frame(0x6110,name,c,s,h,cs::FrameResolveMode::WaitForCharacterMetadata);
        if(mode=="reject"){require(!ok,"malformed V10 admitted");cs::release();std::cout<<"{\"rejected\":true}\n";return 0;}
        if(first){coldMisses+=!ok;maxWait=(std::max)(maxWait,std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());first=false;}
        require(ok&&h.frameIndex==cycles[c][s],"native cycle mapping differs");base=h;++slots;
      }
    }
    require(!first&&!cs::frame_requires_fixed_monster_palette(base),"Character contract changed");
    for(unsigned f=0;f<nf;++f){unsigned w{},h{};int cx{},cy{};read(input,w);read(input,h);read(input,cx);read(input,cy);base.frameIndex=f;
      for(unsigned p=0;p<np;++p){std::array<unsigned char,32> plain{},encoded{},composite{};read(input,plain);read(input,encoded);read(input,composite);
        for(unsigned e=0;e<3;++e){cs::PaletteSnapshot palette{};palette.colors=palettes[p];palette.encoding={0x1908,0x1401};
          if(e){palette.encoding={0x80e1,e==1?0x1401u:0x8367u};for(auto& colour:palette.colors)colour=swap(colour);}
          std::vector<std::uint32_t> pixels;std::uint64_t fingerprint{};
          require(cs::reconstruct_frame_pixels(base,palette,pixels,fingerprint)&&pixels.size()==std::uint64_t(w)*h*4,"plain extent");
          if(e)for(auto& colour:pixels)colour=swap(colour);
          require(sha(pixels)==plain,"Character colours changed");
          if(sdf){require(cs::reconstruct_frame_sdf_pixels(base,palette,pixels,fingerprint)&&pixels.size()==std::uint64_t(w*2+12)*(h*2+12),"SDF reconstruction failed");
            if(e)for(auto& colour:pixels)colour=swap(colour);require(sha(pixels)==encoded,"SDF colours or shadows differ");}
        }
        if(sdf){cs::CompositeLayer layer{};layer.frame=base;layer.palette.colors=palettes[p];layer.palette.encoding={0x1908,0x1401};
          std::vector<std::uint32_t> pixels;cs::CompositeBounds bounds{};
          require(cs::reconstruct_composite_sdf_pixels(&layer,1,pixels,bounds)&&sha(pixels)==composite,"Character composite differs");
          require(bounds.left==-cx&&bounds.top==-cy&&bounds.content_width()==int(w)&&bounds.content_height()==int(h),"native centres changed");}
      }++frames;
    }
  }
  require(input.peek()==std::char_traits<char>::eof()&&frames==10323&&coldMisses==0,"incomplete scope/cold resolution");cs::release();
  std::cout<<"{\"passed\":true,\"resources\":"<<nr<<",\"frames\":"<<frames<<",\"slots\":"<<slots<<",\"cold_misses\":"<<coldMisses<<",\"maximum_wait_ms\":"<<maxWait<<",\"palettes\":"<<np<<",\"encodings\":3,\"SDF\":"<<(sdf?"true":"false")<<"}\n";return 0;
}catch(const std::exception& e){cs::release();std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
