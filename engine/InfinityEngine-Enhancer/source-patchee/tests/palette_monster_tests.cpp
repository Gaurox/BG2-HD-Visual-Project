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

int main(int argc,char** argv) {
  try {
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
