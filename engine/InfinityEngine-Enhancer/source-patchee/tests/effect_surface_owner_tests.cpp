#include "iee/core/effect_surface_owner.h"
#include "iee/core/effect_smoke_palette.h"
#include "iee/core/effect_secondary_scope.h"
#include "iee/core/effect_texture_alias.h"
#include "iee/core/effect_native_underlay.h"
#include "effect_sharea_palette_fixtures.h"
#include "iee/core/effect_indexed_palette.h"
#include <cstdlib>
static void require(bool value) { if (!value) std::abort(); }
int main() {
  // Engine COW188 shares CProjectileBAM::Render, but its image is a sprite BAM.
  const std::array<char,8> cow{'A','C','O','W','G','1'};
  require(iee::core::effect_secondary_scope::enabled(cow));
  require(iee::core::effect_texture_resref(cow,true)==cow);
  require(iee::core::effect_surface_layout(cow,67,61,false)==
          iee::core::EffectSurfaceLayout::SourcePlacement);
  {
    constexpr std::array<std::array<char,8>,3> sources{{
      {'B','G','L','R','Y','U'}, {'S','P','C','L','2','3','6','U'},
      {'S','P','G','L','Y','P','H','I'}}};
    for(unsigned i=0;i<sources.size();++i) {
      const std::array<char,8> expected{'X','3','N','0','0',char('1'+i)};
      require(iee::core::effect_texture_resref(sources[i],false)==sources[i]);
      require(iee::core::effect_texture_resref(sources[i],true)==expected);
      require(iee::core::effect_texture_resref(expected,true)==expected);
      require(iee::core::effect_secondary_scope::enabled(sources[i]));
      require(iee::core::effect_secondary_scope::enabled(expected));
    }
  }
  {
    using namespace iee::core;
    const std::array<char,8> missile{'S','P','M','A','G','M','I','S'};
    require(effect_surface_layout(missile,64,64,false)==EffectSurfaceLayout::CroppedSource);
    require(effect_frame_lookup_size(missile,64,64)==std::array<int,2>{64,78});
    require(effect_frame_lookup_size(missile,24,16)==std::array<int,2>{24,16});
    require(effect_surface_layout(missile,64,64,true)==EffectSurfaceLayout::NativeOnly);
    require(effect_surface_layout(missile,64,78,false)==EffectSurfaceLayout::SourcePlacement);
    require(effect_surface_layout({'F','I','R','E','B','A','T','\0'},64,64,false)==
        EffectSurfaceLayout::SourcePlacement);
  }
  // Native source identity must reach the corrected pack AND remain eligible
  // for the actual single-cell FX path. A corrected pack outside the whitelist
  // would silently retain the native draw instead of testing its alpha.
  const std::array<char,8> cloud{'S','P','C','L','O','U','D','K'};
  const auto corrected=iee::core::effect_texture_resref(cloud);
  require(corrected==(std::array<char,8>{'X','5','8','C','L','K','\0','\0'}));
  require(iee::core::effect_secondary_scope::enabled(corrected));
  for(const auto source : {std::array<char,8>{'S','P','C','L','O','U','D','S'},
                          std::array<char,8>{'S','P','D','F','O','G','A','\0'}}) {
    const auto target=iee::core::effect_texture_resref(source);
    require(target!=source && iee::core::effect_secondary_scope::enabled(target));
    require(iee::core::effect_texture_resref(target)==target);
  }
  const std::array<char,8> wallFog{'B','D','W','O','F','O','G','A'};
  require(iee::core::effect_texture_resref(wallFog,false)==wallFog);
  const auto normalWallFog=iee::core::effect_texture_resref(wallFog,true);
  require(normalWallFog==(std::array<char,8>{'X','5','8','W','F','O','G','\0'}));
  require(iee::core::effect_secondary_scope::enabled(normalWallFog));
  require(iee::core::effect_texture_resref(normalWallFog,true)==normalWallFog);
  const std::array<char,8> writhing{'W','R','I','T','H','I','N','G'};
  require(iee::core::effect_texture_resref(writhing,false)==writhing);
  const auto normalWrithing=iee::core::effect_texture_resref(writhing,true);
  require(normalWrithing==(std::array<char,8>{'X','2','8','W','R','T','H','\0'}));
  require(iee::core::effect_secondary_scope::enabled(normalWrithing));
  require(iee::core::effect_texture_resref(normalWrithing,true)==normalWrithing);
  const std::array<char,8> fire{'F','I','R','E','B','A','T','\0'};
  require(iee::core::effect_texture_resref(fire)==fire);
  require(iee::core::effect_secondary_scope::enabled({'S','P','S','M','P','U','F','F'}));
  require(iee::core::effect_secondary_scope::enabled({'S','P','M','A','G','M','I','S'}));
  // The real LIGHTCHA path creates all three oriented trails. Each must
  // retain the single-cell FX/mask route, not just generic texture binding.
  for (char suffix : {'1','2','3'}) {
    const std::array<char,8> trail{'S','P','C','H','L','G','T',suffix};
    require(iee::core::effect_secondary_scope::enabled(trail));
    require(iee::core::effect_texture_resref(trail)==trail);
  }
  require(!iee::core::effect_secondary_scope::enabled({'S','P','C','H','L','G','T','4'}));
  require(!iee::core::effect_secondary_scope::enabled({'G','R','N','D','G','L','O','W'}));
  {
    using namespace iee::core::effect_indexed_palette;
    require(enabled({'S','H','A','R','E','A','\0','\0'}));
    require(iee::core::effect_secondary_scope::enabled({'S','H','A','R','E','A','\0','\0'}));
    require(!enabled({'S','H','A','R','E','A','W','\0'}));
    std::array<std::uint64_t,7> hashes{};
    for(unsigned variant=0;variant<shareaPalettes.size();++variant) {
      const auto transfer=derive(shareaPalettes[variant],true);
      require(transfer.valid && transfer.opacity==255 && transfer.identity==(variant==0));
      hashes[variant]=transfer.fingerprint;
      for(unsigned previous=0;previous<variant;++previous) require(hashes[previous]!=hashes[variant]);
      for(unsigned i=1;i<256;++i) {
        std::array<unsigned,3> rgb{(source[i]>>16)&255,(source[i]>>8)&255,source[i]&255};
        const auto output=recolor(rgb,transfer);
        for(unsigned c=0;c<3;++c)
          require(output[c]==((shareaPalettes[variant][i]>>((2-c)*8))&255));
      }
      // Equivalent RGBA/BGRA realizations must choose the same GPU variant.
      auto rgba=shareaPalettes[variant];
      for(auto& value:rgba) value=(value&0xff00ff00u)|((value&255)<<16)|((value>>16)&255);
      require(derive(rgba,false).fingerprint==transfer.fingerprint);
    }
    const auto neutral=derive(shareaPalettes[0],true);
    std::array<std::byte,12> pixels{std::byte{8},std::byte{5},std::byte{2},std::byte{16},
        std::byte{71},std::byte{99},std::byte{33},std::byte{255},
        std::byte{22},std::byte{33},std::byte{44},std::byte{0}};
    const auto before=pixels;iee::core::effect_indexed_palette::apply(pixels,neutral);require(pixels==before);
    auto half=shareaPalettes[3];for(auto& value:half)value=(value&0xffffffu)|0x80000000u;
    const auto colored=derive(half,true);require(colored.valid && colored.fingerprint!=hashes[3]);
    iee::core::effect_indexed_palette::apply(pixels,colored);require(pixels[3]==std::byte{8} && pixels[7]==std::byte{128});
    for(unsigned i=8;i<12;++i)require(pixels[i]==before[i]);
    half[99]=0;require(!derive(half,true).valid); // Per-index alpha cannot use a uniform remap.
    require(recolor({0,0,0},colored)==std::array<unsigned,3>{0,0,0});
  }
  iee::core::EffectSurfaceOwner owner;
  require(!owner.pending_cell());
  owner.submit(1,2,true); require(!owner.cell(1)); // No prepared pass.
  owner.begin(1); owner.submit(1,2,true); require(owner.cell(1)==2);
  require(!owner.cell(3)); // Other surface cannot inherit a cell.
  owner.clear(); require(!owner.cell(1));
  owner.begin(1); owner.submit(1,2,false); require(!owner.cell(1));
  owner.begin(1); owner.submit(1,2,true); owner.submit(1,3,false);
  require(!owner.cell(1)); // Native overlay must not disappear.
  require(!owner.candidate_cell(1));
  owner.begin(1); owner.submit(1,2,true); owner.submit(1,2,true);
  require(!owner.cell(1)); // Two instances of the same resource remain native.
  require(owner.candidate_cell(1)==2); // Captured prefix permits the last layer.
  owner.begin(1);owner.submit(1,3,false);owner.submit(1,2,true);
  require(owner.candidate_cell(1)==2 && owner.submissions()==2);
  for(int i=0;i<7;++i) owner.submit(1,2,true);
  require(!owner.pending_candidate()); // Bounded composition, no overflow draw.
  owner.begin(1); owner.submit(3,2,true); require(!owner.pending_cell());
  owner.begin(1); owner.submit(1,2,true); owner.begin(1);
  require(!owner.cell(1)); // Next pass, including reused addresses.
  iee::core::area_lighting::Palette palette{};
  constexpr unsigned levels[]{115,140,165,189,206,231};
  for(unsigned i=0;i<6;++i) palette[22-i]=0xff000000u | (levels[i]*0x10101u);
  const auto neutral=iee::core::effect_smoke_palette::derive(palette,true);
  require(neutral.valid);
  for(unsigned i=0;i<256;++i) for(unsigned c=0;c<3;++c) require(neutral.rgb[c][i]==i);
  std::array<std::byte,16> pixels{std::byte{8},std::byte{5},std::byte{2},std::byte{16},
      std::byte{231},std::byte{231},std::byte{231},std::byte{255},
      std::byte{22},std::byte{33},std::byte{44},std::byte{0}};
  const auto original=pixels;
  iee::core::effect_smoke_palette::apply(pixels,neutral);require(pixels==original);
  for(unsigned i=0;i<6;++i) palette[22-i]=0xff000000u | (levels[i]<<16);
  const auto red=iee::core::effect_smoke_palette::derive(palette,true);
  require(red.valid && red.fingerprint!=neutral.fingerprint);
  require(red.rgb[0][0]==0 && red.rgb[1][0]==0 && red.rgb[2][0]==0);
  iee::core::effect_smoke_palette::apply(pixels,red);
  require(pixels[4]==std::byte{231} && pixels[5]==std::byte{} && pixels[6]==std::byte{});
  for(unsigned i=3;i<pixels.size();i+=4) require(pixels[i]==original[i]);
  require(pixels[8]==original[8]); // Transparent RGB preserved.
  for(unsigned i=0;i<6;++i) palette[22-i]=(palette[22-i]&0xffffffu)|0x80000000u;
  const auto half=iee::core::effect_smoke_palette::derive(palette,true);
  require(half.valid && half.fingerprint!=red.fingerprint);
  pixels=original;iee::core::effect_smoke_palette::apply(pixels,half,128);
  require(pixels[7]==std::byte{128} && pixels[3]==std::byte{8});
  palette[20]=0;require(!iee::core::effect_smoke_palette::derive(palette,true).valid);
  {
    using namespace iee::core::effect_native_underlay;
    std::array<std::uint32_t,256> colors{};colors.fill(0x7f8090a0u);
    require(uniform_opacity(colors)==127);
    colors[0]=0;colors[1]=0xff00ff00u;require(uniform_opacity(colors)==127);
    colors[24]=0x608090a0u;require(!uniform_opacity(colors));
    std::array<std::byte,24> prefix{}; // 3x2 native black/coloured lower layer.
    prefix[0]=std::byte{22};prefix[3]=std::byte{128};
    std::vector<std::byte> frame(64); // 1x1 x4; transparent holes keep native.
    frame[0]=std::byte{99};frame[3]=std::byte{255};
    frame[4]=std::byte{17}; // Zero-alpha additive RGB still replaces native.
    std::vector<std::byte> out;
    require(compose(frame,1,1,3,2,0,0,prefix,127,out));
    require(out[0]==std::byte{99} && out[3]==std::byte{127});
    require(out[4]==std::byte{17} && out[7]==std::byte{});
    require(out[8]==std::byte{22} && out[11]==std::byte{128});
    require(!compose(frame,1,1,3,2,-1,0,prefix,127,out));
    require(!compose(frame,1,1,3,2,3,0,prefix,127,out));
    const auto first=fingerprint(prefix,127);prefix[0]=std::byte{23};
    require(first!=fingerprint(prefix,127) && first!=fingerprint(prefix,255));
  }
}
