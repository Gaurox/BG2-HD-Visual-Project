#include <algorithm>
#include <array>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <thread>
#include <vector>
#include <windows.h>
#include <bcrypt.h>
#include "iee/core/palette_fraction.h"
#include "iee/creature_sprite_x2.h"

namespace iee::probe {
void record_creature_texture_trace(unsigned,int,int,int,int,int,std::string_view) noexcept {}
}
namespace cs = iee::creature_sprite_x2;
namespace pf = iee::core::palette_fraction;
void require(bool ok,const char* message) { if (!ok) throw std::runtime_error(message); }
template<class T> void read(std::istream& stream,T& value) {
  require(static_cast<bool>(stream.read(reinterpret_cast<char*>(&value),sizeof(value))),"truncated V7 oracle");
}
std::array<unsigned char,32> pixel_sha(std::vector<std::uint32_t>& pixels) {
  std::array<unsigned char,32> result{};
  require(pixels.size() <= (std::numeric_limits<ULONG>::max)()/4,"pixel hash limit");
  require(BCryptHash(BCRYPT_SHA256_ALG_HANDLE,nullptr,0,reinterpret_cast<PUCHAR>(pixels.data()),
      static_cast<ULONG>(pixels.size()*4),result.data(),32) >= 0,"pixel hash failed");
  return result;
}
std::uint32_t swap_rb(std::uint32_t p) { return (p&0xff00ff00u)|((p&255u)<<16)|((p>>16)&255u); }
int main(int argc,char** argv) {
  try {
    require(argc==3 || argc==4,"usage: palette_partner_tests assets witnesses.oracle [sdf.oracle]");
    std::ifstream sdfOracle; if (argc==4) sdfOracle.open(argv[3],std::ios::binary);
    if (argc==4) { std::array<char,8> m{};read(sdfOracle,m);require(m==std::array<char,8>{'I','E','E','S','D','F','1',0},"SDF oracle header"); }
    std::ifstream oracle(argv[2],std::ios::binary); require(static_cast<bool>(oracle),"oracle missing");
    std::array<char,8> magic{}; unsigned nr{}; read(oracle,magic); read(oracle,nr);
    require(magic==std::array<char,8>{'I','E','E','Q','P','7','\0','\0'} && nr<=128,"oracle header");
    require(cs::prepare(std::filesystem::path(argv[1])),"V7 catalog rejected");
    std::vector<cs::FrameHandle> handles;std::vector<std::array<pf::Palette,6>> witnessPalettes;
    std::uint64_t frames{},slots{},pixelsTotal{};
    for (unsigned resource=0; resource<nr; ++resource) {
      unsigned animation{},owner{},nf{},nc{}; std::array<char,8> name{};
      read(oracle,animation);read(oracle,owner);read(oracle,name);read(oracle,nf);read(oracle,nc);
      require(nf>0&&nf<=4096&&nc>0&&nc<=256&&cs::animation_targets_owner(static_cast<std::uint16_t>(animation),owner),"V7 native owner routing");
      std::array<pf::Palette,6> palettes{}; for (auto& palette:palettes) read(oracle,palette);
      pf::PartnerProfile profile{}; read(oracle,profile.nativeKind); read(oracle,profile.sourcePalette);read(oracle,profile.partners);
      require(profile.valid(profile.nativeKind==0?8:9,3),"oracle profile invalid");
      std::vector<std::vector<unsigned>> cycles(nc);
      cs::FrameHandle handle{};bool resolved=false;
      for (unsigned c=0;c<nc;++c) {
        unsigned count{};read(oracle,count); require(count<=65535,"cycle limit"); cycles[c].resize(count);
        for (unsigned s=0;s<count;++s) {
          read(oracle,cycles[c][s]); cs::FrameHandle current{};
          const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);
          bool ok=false;
          do {
            ok=cs::resolve_frame(static_cast<std::uint16_t>(animation),name,static_cast<int>(c),static_cast<int>(s),current);
            if (ok||!cs::pending_catalog_loads()) break;
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
          } while (std::chrono::steady_clock::now()<deadline);
          if (cycles[c][s]>=nf) require(!ok,"native sentinel resolved to pixels");
          else { require(ok&&current.frameIndex==cycles[c][s],"V7 cycle/slot mapping differs"); handle=current;resolved=true;++slots; }
        }
      }
      require(resolved,"no native frames resolved");
      handles.push_back(handle);witnessPalettes.push_back(palettes);
      require(cs::frame_requires_fixed_monster_palette(handle)&&
          cs::frame_accepts_fixed_monster_palette(handle,static_cast<std::uint16_t>(profile.nativeKind),profile.sourcePalette),"V7 native palette contract");
      require(!cs::frame_accepts_fixed_monster_palette(handle,static_cast<std::uint16_t>(1-profile.nativeKind),profile.sourcePalette),"wrong native palette kind accepted");
      for (unsigned f=0;f<nf;++f) {
        unsigned w{},h{};int cx{},cy{};read(oracle,w);read(oracle,h);read(oracle,cx);read(oracle,cy);
        handle.frameIndex=f;
        for (unsigned p=0;p<6;++p) {
          std::array<unsigned char,32> expected{};read(oracle,expected);
          std::array<unsigned char,32> expectedSdf{};if(argc==4)read(sdfOracle,expectedSdf);
          for (unsigned encoding=0;encoding<3;++encoding) {
            cs::PaletteSnapshot palette{};palette.colors=palettes[p];palette.encoding={0x1908,0x1401};
            if (encoding) { palette.encoding={0x80e1,encoding==1?0x1401u:0x8367u};for(auto& color:palette.colors)color=swap_rb(color); }
            std::vector<std::uint32_t> pixels;std::uint64_t fingerprint{};
            require(cs::reconstruct_frame_pixels(handle,palette,pixels,fingerprint)&&pixels.size()==std::uint64_t(w)*h*4,"V7 reconstruction/extent");
            if (encoding) for(auto& color:pixels) color=swap_rb(color);
            require(pixel_sha(pixels)==expected,"Python/C++ V7 pixel bytes differ"); pixelsTotal+=pixels.size();
            if (argc==4) {
              require(cs::reconstruct_frame_sdf_pixels(handle,palette,pixels,fingerprint)&&pixels.size()==std::uint64_t(w*2+12)*(h*2+12),"SDF upload extent");
              if(encoding)for(auto& color:pixels)color=swap_rb(color);
              require(pixel_sha(pixels)==expectedSdf,"Python/C++ SDF upload bytes differ");
            }
          }
        }
        cs::CompositeLayer layer{};layer.frame=handle;layer.palette.colors=palettes[0];layer.palette.encoding={0x1908,0x1401};
        std::vector<std::uint32_t> pixels;cs::CompositeBounds bounds{};
        require(cs::reconstruct_composite_pixels(&layer,1,pixels,bounds)&&bounds.left==-cx&&bounds.top==-cy&&bounds.content_width()==static_cast<int>(w)&&bounds.content_height()==static_cast<int>(h),"native BAM center changed");
        if (argc==4) {
          std::array<unsigned char,32> expectedComposite{};read(sdfOracle,expectedComposite);
          require(cs::reconstruct_composite_sdf_pixels(&layer,1,pixels,bounds),"SDF native composition failed");
          require(pixel_sha(pixels)==expectedComposite,"SDF native composition bytes differ");
        }
        ++frames;
      }
    }
    unsigned composites=0;
    if(argc==4 && sdfOracle.peek()!=std::char_traits<char>::eof()) {
      read(sdfOracle,composites);require(composites<=128,"SDF composite count");
      for(unsigned n=0;n<composites;++n) {
        unsigned count{},palette{};read(sdfOracle,count);read(sdfOracle,palette);
        require(count>0&&count<=8&&palette<6,"SDF layers/palette");
        std::vector<cs::CompositeLayer> layers(count);
        for(auto& layer:layers) {
          unsigned ri{},fi{};read(sdfOracle,ri);read(sdfOracle,fi);require(ri<handles.size(),"SDF resource");
          layer.frame=handles[ri];layer.frame.frameIndex=fi;layer.palette.colors=witnessPalettes[ri][palette];layer.palette.encoding={0x1908,0x1401};
        }
        std::array<int,4> expectedBounds{};read(sdfOracle,expectedBounds);
        std::array<unsigned char,32> plain{},encoded{};read(sdfOracle,plain);read(sdfOracle,encoded);
        std::vector<std::uint32_t> pixels;cs::CompositeBounds bounds{};
        require(cs::reconstruct_composite_pixels(layers.data(),count,pixels,bounds)&&pixel_sha(pixels)==plain,"native layering changed");
        require(bounds.left==expectedBounds[0]&&bounds.top==expectedBounds[1]&&bounds.right==expectedBounds[2]&&bounds.bottom==expectedBounds[3],"SDF layer centers changed");
        require(cs::reconstruct_composite_sdf_pixels(layers.data(),count,pixels,bounds)&&pixel_sha(pixels)==encoded,"body/earth SDF union bytes differ");
      }
      std::cout<<"SDF composite golden cases passed: "<<composites<<"\n";
    }
    require(oracle.peek()==std::char_traits<char>::eof(),"oracle trailing bytes");
    if(argc==4)require(sdfOracle.peek()==std::char_traits<char>::eof(),"SDF oracle trailing bytes"); cs::release();
    std::cout<<"{\"resources\":"<<nr<<",\"frames\":"<<frames<<",\"native_cycle_slots\":"<<slots<<",\"decoded_pixels\":"<<pixelsTotal<<",\"palette_encodings\":3,\"K\":6,\"passed\":true}\n";
    return 0;
  } catch (const std::exception& e) { cs::release();std::cerr<<"FAIL: "<<e.what()<<"\n";return 1; }
}
