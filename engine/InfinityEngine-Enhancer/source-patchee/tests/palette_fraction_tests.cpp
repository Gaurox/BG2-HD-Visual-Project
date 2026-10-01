#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <vector>
#include <windows.h>
#include <bcrypt.h>

#include "iee/creature_sprite_x2.h"

// Host tests do not collect live GL telemetry (same boundary as iee_tests).
namespace iee::probe {
void record_creature_texture_trace(unsigned, int, int, int, int, int,
                                  std::string_view) noexcept {}
}

namespace cs = iee::creature_sprite_x2;
namespace fs = std::filesystem;
namespace {
std::uint64_t decoded = 0;
void require(bool ok, const std::string& label) {
  if (!ok) throw std::runtime_error(label);
}
template<class T> void read(std::istream& input, T& value) {
  require(static_cast<bool>(input.read(reinterpret_cast<char*>(&value), sizeof(value))), "truncated test fixture");
}
template<class T> void read_vector(std::istream& input, std::vector<T>& data, std::size_t n) {
  data.resize(n);
  require(static_cast<bool>(input.read(reinterpret_cast<char*>(data.data()),
                                      static_cast<std::streamsize>(n*sizeof(T)))), "truncated test vector");
}
std::array<char,8> ref(const std::string& name) {
  std::array<char,8> result{};
  require(name.size() <= result.size(), "invalid resref fixture");
  std::memcpy(result.data(),name.data(),name.size());
  return result;
}
bool resolve(std::uint16_t animation, const std::array<char,8>& name,
             int sequence, int slot, cs::FrameHandle& handle) {
  if (cs::animation_targets_character(animation)) {
    // One cold render call must resolve a valid Character resource. Retrying
    // here would hide the native/HD alternation seen with the async resolver.
    return cs::resolve_frame(animation,name,sequence,slot,handle,
                            cs::FrameResolveMode::WaitForCharacterMetadata);
  }
  const auto deadline = std::chrono::steady_clock::now()+std::chrono::seconds(5);
  do {
    if (cs::resolve_frame(animation,name,sequence,slot,handle)) return true;
    if (!cs::pending_catalog_loads()) return false;
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  } while (std::chrono::steady_clock::now()<deadline);
  throw std::runtime_error("catalog worker timeout");
}
std::uint32_t swap_rb(std::uint32_t p) {
  return (p & 0xff00ff00u) | ((p & 255u)<<16) | ((p>>16)&255u);
}
std::array<unsigned char,32> hash_pixels(const std::vector<std::uint32_t>& pixels) {
  std::array<unsigned char,32> result{};
  require(pixels.size() <= (std::numeric_limits<ULONG>::max)()/4, "hash size overflow");
  require(BCryptHash(BCRYPT_SHA256_ALG_HANDLE,nullptr,0,
                    reinterpret_cast<PUCHAR>(const_cast<std::uint32_t*>(pixels.data())),
                    static_cast<ULONG>(pixels.size()*4),result.data(),static_cast<ULONG>(result.size()))>=0,
          "BCrypt SHA256 failed");
  return result;
}
struct Golden {
  std::uint32_t palettes{}, pairs{}, neutral{};
  std::vector<std::uint8_t> i,f;
  std::vector<std::uint32_t> palette,expected;
};
Golden load_golden(const fs::path& path) {
  std::ifstream input(path,std::ios::binary);
  std::array<char,8> magic{};read(input,magic);
  require(magic==std::array<char,8>{'I','E','E','Q','3','G','1','\0'},"golden magic");
  std::uint32_t profile{},rule{};read(input,profile);read(input,rule);
  Golden g;read(input,g.palettes);read(input,g.pairs);read(input,g.neutral);
  require(profile==1 && rule==1 && g.palettes==50 && g.pairs==1824 && g.neutral==18,"golden dimensions/profile");
  read_vector(input,g.i,g.pairs);read_vector(input,g.f,g.pairs);
  read_vector(input,g.palette,static_cast<std::size_t>(g.palettes)*256);
  read_vector(input,g.expected,static_cast<std::size_t>(g.palettes)*g.pairs);
  require(input.peek()==EOF,"golden trailing bytes");
  return g;
}
void compare_golden(const Golden& g, cs::FrameHandle handle, bool fractional) {
  for (std::size_t p=0;p<g.palettes;++p) {
    for (const auto encoding : std::array<cs::NativePixelEncoding,3>{
          cs::NativePixelEncoding{0x1908,0x1401}, {0x80e1,0x1401}, {0x80e1,0x8367}}) {
      cs::PaletteSnapshot palette{};palette.encoding=encoding;
      const bool bgra=encoding.externalFormat==0x80e1;
      for (std::size_t n=0;n<256;++n) {
        const auto color=g.palette[p*256+n];palette.colors[n]=bgra ? swap_rb(color) : color;
      }
      std::vector<std::uint32_t> pixels;std::uint64_t fp{};
      require(cs::reconstruct_frame_pixels(handle,palette,pixels,fp),"native frame decode");
      require(pixels.size()==g.pairs,"native pixel count");
      for (std::size_t n=0;n<g.pairs;++n) {
        auto expected=fractional ? g.expected[p*g.pairs+n] : g.palette[p*256+g.i[n]];
        if (bgra) expected=swap_rb(expected);
        require(pixels[n]==expected,"golden byte mismatch at "+std::to_string(n));
        ++decoded;
      }
    }
  }
}

void test_cache(cs::FrameHandle handle) {
  cs::PaletteSnapshot a{};a.encoding={0x1908,0x1401};
  a.colors[4]=0x4d000000;a.colors[5]=0xff505050;
  std::vector<std::uint32_t> pixels,original;std::uint64_t fp{},oldFp{};
  require(cs::reconstruct_frame_pixels(handle,a,original,oldFp),"partial decode");
  require(original==std::vector<std::uint32_t>(16,0x4d1e1e1e),"integer interpolation/primary alpha");
  require(cs::resident_index_bytes()==32,"I+F atomic residency accounting");
  a.colors[6]=0xffffffff;
  require(cs::reconstruct_frame_pixels(handle,a,pixels,fp) && fp==oldFp && pixels==original,"unused palette dependency");
  cs::CompositeLayer layer{.frame=handle,.palette=a};
  cs::CompositeBounds bounds{};
  require(cs::reconstruct_composite_pixels(&layer,1,pixels,bounds),"CPU composite");
  const auto first=cs::composite_rebuild_count();
  a.colors[6]=0x10000000;layer.palette=a;
  require(cs::reconstruct_composite_pixels(&layer,1,pixels,bounds) && cs::composite_rebuild_count()==first,
          "unused palette mutation must hit composite cache");
  auto previous=original;
  for (unsigned pulse=1;pulse<=16;++pulse) {
    const auto color=80u+pulse*8u;
    a.colors[5]=0xff000000u | color | (color<<8) | (color<<16);
    require(cs::reconstruct_frame_pixels(handle,a,pixels,fp) && fp!=oldFp && pixels!=previous,"used successor pulse invalidation");
    previous=pixels;oldFp=fp;layer.palette=a;
    require(cs::reconstruct_composite_pixels(&layer,1,pixels,bounds) && cs::composite_rebuild_count()==first+pulse,
            "pulse must rebuild CPU composite");
  }
  auto b=a;b.colors[4]=0;  // Alpha0 with nonzero interpolated RGB still overwrites natively.
  std::array<cs::CompositeLayer,2> layers{{{handle,a},{handle,b}}};
  require(cs::reconstruct_composite_pixels(layers.data(),layers.size(),pixels,bounds),"per-layer palettes");
  require(bounds.left==3 && bounds.top==-5 && bounds.logical_width()==4 && bounds.logical_height()==4,
          "signed centres and native borders");
  std::uint64_t bfp{};std::vector<std::uint32_t> second;
  require(cs::reconstruct_frame_pixels(handle,b,second,bfp) && bfp!=oldFp && second[0]!=previous[0],"same BAM actors have independent colors/alpha");
  const int physicalWidth=bounds.logical_width()*2;
  for (int y=0;y<8;++y) for(int x=0;x<8;++x) {
    require(pixels[static_cast<std::size_t>(y)*physicalWidth+x]==
            (y>=2 && y<6 && x>=2 && x<6 ? second[0] : 0),"native overwrite/order/zero border");
  }
  const auto beforeReset=cs::composite_rebuild_count();
  cs::forget_engine_textures();
  require(cs::reconstruct_composite_pixels(layers.data(),layers.size(),pixels,bounds) &&
          cs::composite_rebuild_count()==beforeReset+1,"graphics forget/reset invalidates CPU composites");
  // Repeated actor A draws must not consume B's last palette or its cache entry.
  require(cs::reconstruct_frame_pixels(handle,a,pixels,fp) && pixels==previous && fp==oldFp,"actor palette separation");
  auto badEncoding=a;badEncoding.encoding.type=0;
  require(!cs::reconstruct_frame_pixels(handle,badEncoding,pixels,fp) && pixels.empty(),"unsupported native encoding fails closed");
}

void test_zero_cache(cs::FrameHandle handle) {
  cs::PaletteSnapshot palette{};palette.encoding={0x1908,0x1401};palette.colors[4]=0x4d102030;
  std::vector<std::uint32_t> pixels;std::uint64_t first{},next{};
  require(cs::reconstruct_frame_pixels(handle,palette,pixels,first) &&
          pixels==std::vector<std::uint32_t>(16,palette.colors[4]),"F0 must read primary directly");
  cs::CompositeLayer layer{handle,palette};cs::CompositeBounds bounds{};
  require(cs::reconstruct_composite_pixels(&layer,1,pixels,bounds),"F0 composite");
  const auto builds=cs::composite_rebuild_count();
  palette.colors[5]=0xffffffff;layer.palette=palette;
  require(cs::reconstruct_frame_pixels(handle,palette,pixels,next) && first==next &&
          pixels==std::vector<std::uint32_t>(16,palette.colors[4]),"F0 must not depend on successor");
  require(cs::reconstruct_composite_pixels(&layer,1,pixels,bounds) &&
          cs::composite_rebuild_count()==builds,"F0 successor mutation must hit cache");
}

void test_eviction(cs::FrameHandle handle) {
  constexpr std::uint64_t frameBytes=32ull*1024*1024, budget=128ull*1024*1024;
  for(unsigned n=0;n<5;++n) {
    cs::FrameHandle current{};
    require(resolve(0x6110,ref("TEST"),0,static_cast<int>(n),current),"eviction frame lookup");
    require(cs::ensure_frame_payload_available(current),"eviction I+F load");
    require(cs::resident_index_bytes()==std::min((n+1)*frameBytes,budget),"atomic I+F eviction/accounting");
  }
  require(cs::ensure_frame_payload_available(handle) && cs::resident_index_bytes()==budget,
          "oldest I+F frame must reload within budget");
  cs::PaletteSnapshot palette{};palette.encoding={0x1908,0x1401};
  palette.colors[4]=0x4d000000;palette.colors[5]=0xff505050;
  std::vector<std::uint32_t> pixels;std::uint64_t fingerprint{};
  require(cs::reconstruct_frame_pixels(handle,palette,pixels,fingerprint) && pixels.size()==16777216 &&
          std::all_of(pixels.begin(),pixels.end(),[](auto p){return p==0x4d1e1e1e;}),"reloaded I+F decode identity");
}

void test_mixed_catalog(const fs::path& root) {
  for (bool legacyFirst : {true, false}) {
    require(cs::prepare(root/"mixed-components"), "mixed catalog prepare");
    cs::FrameHandle fractional{}, legacy{}, monster{};
    if (legacyFirst) require(resolve(0x6110,ref("LEGACY"),0,0,legacy),"V5 loads before V6");
    require(resolve(0x6110,ref("TEST"),0,0,fractional),"mixed V6 resolve");
    require(resolve(0x6110,ref("LEGACY"),0,0,legacy),"mixed V5 resolve");
    require(resolve(0x7000,ref("LEGACY"),0,0,monster) && monster.resourceIndex==legacy.resourceIndex &&
            monster.animationId==0x7000 && legacy.animationId==0x6110,"V5 non-Character component and scoped handles preserved");
    require(cs::frame_uses_q3m_profile(fractional) && !cs::frame_uses_q3m_profile(legacy),"per-frame profile ownership");
    for (const auto encoding : std::array<cs::NativePixelEncoding,3>{{{0x1908,0x1401},{0x80e1,0x1401},{0x80e1,0x8367}}}) {
      cs::PaletteSnapshot a{};a.encoding=encoding;a.colors[4]=0x4d000000;a.colors[5]=0xff505050;
      auto b=a;b.colors[4]=encoding.externalFormat==0x80e1 ? swap_rb(0x80224466u) : 0x80224466u;
      std::array<cs::CompositeLayer,2> layers{{{fractional,a},{legacy,b}}};
      cs::CompositeBounds bounds{};std::vector<std::uint32_t> pixels;
      require(cs::reconstruct_composite_pixels(layers.data(),layers.size(),pixels,bounds),"mixed V5/V6 native composition");
      for (int y=0;y<8;++y) for(int x=0;x<8;++x) {
        const auto expected=x>=2 && x<6 && y>=2 && y<6 ? (y<4 ? b.colors[4] : 0x4d1e1e1eu) : 0u;
        require(pixels[static_cast<std::size_t>(y)*8+x]==expected,"mixed order, alpha, encoding, geometry and border");
      }
      const auto builds=cs::composite_rebuild_count();
      layers[0].palette.colors[6]=0xffffffff;
      require(cs::reconstruct_composite_pixels(layers.data(),2,pixels,bounds) && cs::composite_rebuild_count()==builds,"mixed unused dependency cache hit");
      layers[0].palette.colors[5]=0xff808080;
      require(cs::reconstruct_composite_pixels(layers.data(),2,pixels,bounds) && cs::composite_rebuild_count()==builds+1,"mixed Q3m successor pulse invalidates cache");
      cs::forget_engine_textures();
      require(cs::reconstruct_composite_pixels(layers.data(),2,pixels,bounds) && cs::composite_rebuild_count()==builds+2,"mixed graphics reset");
    }
    cs::release();
    require(cs::prepare(root/"mixed-shared"),"shared resref mixed prepare");
    cs::FrameHandle other{};
    if (legacyFirst) require(resolve(0x6115,ref("TEST"),0,0,other),"shared V5 first");
    require(resolve(0x6110,ref("TEST"),0,0,fractional) && resolve(0x6115,ref("TEST"),0,0,other) && fractional!=other,"same resref disjoint memberships");
    cs::PaletteSnapshot p{};p.encoding={0x1908,0x1401};p.colors[4]=0x4d000000;p.colors[5]=0xff505050;
    std::vector<std::uint32_t> pixels;std::uint64_t fingerprint{};
    require(cs::reconstruct_frame_pixels(fractional,p,pixels,fingerprint) && pixels[0]==0x4d1e1e1e,"target actor uses V6");
    require(cs::reconstruct_frame_pixels(other,p,pixels,fingerprint) && pixels[0]==0x4d000000,"other actor retains V5");
    require(cs::reconstruct_frame_pixels(fractional,p,pixels,fingerprint) && pixels[0]==0x4d1e1e1e,"mixed actor A/B/A separation");
    cs::release();
  }
  require(cs::prepare(root/"mixed-component-bad"),"bad mixed component outer catalog authenticated");
  cs::FrameHandle retained{}, invalid{};
  require(resolve(0x6110,ref("TEST"),0,0,retained),"first bad-component shard accepted provisionally");
  require(!resolve(0x6110,ref("LEGACY"),0,0,invalid),"mixed versions within component rejected");
  std::vector<std::uint32_t> pixels;std::uint64_t fingerprint{};cs::PaletteSnapshot palette{};palette.encoding={0x1908,0x1401};
  require(!cs::reconstruct_frame_pixels(retained,palette,pixels,fingerprint),"quarantine invalidates retained handle");
  cs::release();
  require(cs::prepare(root/"mixed-owner-bad"),"bad mixed owner outer catalog authenticated");
  require(!resolve(0x6110,ref("TEST"),0,0,invalid),"V6 shared with non-Character owner rejected");
  require(resolve(0x6110,ref("LEGACY"),0,0,retained),"unrelated valid V5 component survives quarantine");
  cs::release();
}

void inspect_pack(const fs::path& directory,const fs::path& oracle,bool complete=false) {
  const auto started=std::chrono::steady_clock::now();
  std::uint64_t peakResident=0,peakMetadata=0;
  std::ifstream input(oracle,std::ios::binary);
  std::array<char,8> magic{};read(input,magic);
  require(magic==std::array<char,8>{'I','E','E','Q','3','P','1','\0'},"pack oracle magic");
  std::uint32_t np{},nf{};read(input,np);read(input,nf);
  require(np==18 && nf>0 && nf<100000,"pack oracle bounds");
  std::vector<std::uint32_t> colors;read_vector(input,colors,static_cast<std::size_t>(np)*256);
  require(cs::prepare(directory),"experimental catalog prepare");
  for (std::uint32_t n=0;n<nf;++n) {
    std::array<char,8> resref{};read(input,resref);
    std::uint32_t index{},sequence{},slot{},count{};read(input,index);read(input,sequence);read(input,slot);read(input,count);
    cs::FrameHandle handle{};
    require(resolve(0x6110,resref,static_cast<int>(sequence & 0x7fffffffu),static_cast<int>(slot),handle),"experimental resource/lookup resolution");
    if (!(sequence & 0x80000000u)) require(handle.frameIndex==index,"native cycle lookup must retain frame identity");
    handle.frameIndex=index;  // Also covers native frames absent from all lookup slots.
    for(std::uint32_t p=0;p<np;++p) {
      std::array<unsigned char,32> expected{};read(input,expected);
      cs::PaletteSnapshot palette{};palette.encoding={0x1908,0x1401};
      std::copy_n(colors.data()+p*256,256,palette.colors.data());
      std::vector<std::uint32_t> pixels;std::uint64_t fingerprint{};
      require(cs::reconstruct_frame_pixels(handle,palette,pixels,fingerprint) && pixels.size()==count &&
              hash_pixels(pixels)==expected,"experimental full-frame Python/native SHA256 mismatch");
      decoded+=pixels.size();
      peakResident=std::max(peakResident,cs::resident_index_bytes());
      peakMetadata=std::max(peakMetadata,cs::resident_catalog_metadata_bytes());
    }
  }
  require(input.peek()==EOF,"pack oracle trailing bytes");
  if (complete || cs::contains_animation(0x6115)) {
    std::array<cs::CompositeLayer,4> layers{};
    const std::array<std::string,4> names{{"CHFF4G12","WQNMCG1","WQNJ8G1","WQNC2G1"}};
    for(std::size_t n=0;n<names.size();++n) {
      require(resolve(0x6110,ref(names[n]),0,0,layers[n].frame),"preserved real equipment resolves");
      layers[n].palette.encoding={0x80e1,0x8367};
      std::copy_n(colors.data(),256,layers[n].palette.colors.data());
      require(cs::frame_uses_q3m_profile(layers[n].frame)==(complete || n==0),
              "real scene uses the declared V6 body/equipment coverage");
    }
    cs::CompositeBounds bounds{};std::vector<std::uint32_t> pixels;
    require(cs::reconstruct_composite_pixels(layers.data(),4,pixels,bounds),"real four-layer mixed composition");
    if (cs::contains_animation(0x6115)) {
      cs::FrameHandle other{};
      require(resolve(0x6115,ref("CHFF4G12"),0,0,other) && !cs::frame_uses_q3m_profile(other),"shared body remains V5 for other animation");
    }
  }
  cs::release();
  const auto ms=std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count();
  std::cout<<"{\"pack_frames\":"<<nf<<",\"palettes\":"<<np<<",\"decoded_pixels\":"<<decoded
           <<",\"peak_resident_I_F_bytes\":"<<peakResident<<",\"peak_metadata_bytes\":"<<peakMetadata
           <<",\"verification_elapsed_ms\":"<<ms<<"}\n";
}
}  // namespace

int main(int argc,char** argv) {
  try {
    if(argc==4 && (std::string(argv[1])=="--pack" || std::string(argv[1])=="--pack-complete")) {
      inspect_pack(fs::path(argv[2]),fs::path(argv[3]),std::string(argv[1])=="--pack-complete");return 0;
    }
    require(argc==2,"usage: palette_fraction_tests fixtures-base OR --pack assets oracle");
    fs::path root(argv[1]);
    std::ifstream pointer(root/"ready.txt");std::string version;std::getline(pointer,version);root/=version;
    const auto golden=load_golden(root/"golden.bin");
    std::ifstream cases(root/"cases.tsv");require(static_cast<bool>(cases),"cases manifest missing");
    std::string line;unsigned accepted=0,rejected=0;
    while(std::getline(cases,line)) {
      std::istringstream row(line);std::string name,status;unsigned animation{};row>>name>>status>>animation;
      require(!name.empty() && (status=="ok" || status=="bad"),"bad case row");
      const auto directory=root/name;
      const bool prepared=cs::prepare(directory);
      cs::FrameHandle handle{};
      const bool resolved=prepared && resolve(static_cast<std::uint16_t>(animation),ref("TEST"),0,0,handle);
      require(resolved==(status=="ok"),name+" unexpectedly "+(resolved ? "accepted" : "rejected"));
      if(resolved) {
        ++accepted;
        if(name=="partial") test_cache(handle);
        else if(name=="partial-zero") test_zero_cache(handle);
        else if(name=="eviction" || name=="eviction-x2" || name=="eviction-x4-large") test_eviction(handle);
        else compare_golden(golden,handle,name=="raw" || name=="compressed");
        cs::FrameHandle repeated{};
        if(name!="eviction" && name!="eviction-x2" && name!="eviction-x4-large") require(resolve(0x6110,ref("TEST"),0,1,repeated) && repeated==handle,"repeated slot identity");
        require(!cs::resolve_frame(0x6110,ref("TEST"),1,0,repeated),"empty native cycle");
      } else {
        ++rejected;
        std::vector<std::uint32_t> invalid;std::uint64_t fp{};cs::PaletteSnapshot palette{};
        require(!cs::reconstruct_frame_pixels(handle,palette,invalid,fp) && invalid.empty(),"invalid data must expose no pixels");
      }
      cs::release();
      require(!cs::ensure_frame_payload_available(handle),"released handles must be invalid");
    }
    require(accepted==10 && rejected==37,"case coverage count");
    test_mixed_catalog(root);
    std::cout<<"{\"accepted\":"<<accepted<<",\"rejected\":"<<rejected<<",\"decoded_pixels\":"<<decoded
             <<",\"neutral_reference_decodings\":32832,\"cache_pulses\":16,\"reset\":true,\"eviction_budget_bytes\":134217728}\n";
    return 0;
  } catch(const std::exception& e) {
    cs::release();std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;
  }
}
