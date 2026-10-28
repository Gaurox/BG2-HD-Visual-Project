#pragma once
#include "iee/core/area_animation_lighting.h"
#include "iee/core/effect_sharea_source_palette.h"
#include <limits>

namespace iee::core::effect_indexed_palette {
// SHAREA's six native BMP palettes change hue across RGB channels. A channel-wise
// smoke ramp cannot represent them. Interpolate palette deltas in source RGB
// space; exact native knots and identity palettes remain byte-exact. Only the
// upload copy changes, never the production frame or its cached CPU bytes.
struct Transfer {
  std::array<std::array<int,3>,256> delta{};
  std::uint64_t fingerprint{};
  unsigned opacity{255};
  bool valid{}, identity{true};
};

inline bool enabled(const std::array<char,8>& ref) noexcept {
  return ref==std::array<char,8>{'S','H','A','R','E','A','\0','\0'};
}

inline Transfer derive(const area_lighting::Palette& realized, bool bgra) noexcept {
  Transfer out{};
  out.opacity=realized[2]>>24;
  std::uint64_t hash=0x5348415245410008ull; // Distinct from smoke GPU variants.
  for(unsigned i=2;i<256;++i) {
    if((realized[i]>>24)!=out.opacity) return {};
    for(unsigned c=0;c<3;++c) {
      const int value=(realized[i]>>((bgra?2-c:c)*8))&255;
      const int base=(source[i]>>((2-c)*8))&255;
      out.delta[i][c]=value-base;
      out.identity=out.identity && value==base;
      hash=(hash^static_cast<unsigned>(value))*1099511628211ull;
    }
  }
  // Native index1/black is the additive neutral, including outside the palette.
  out.fingerprint=(hash^out.opacity)*1099511628211ull;
  out.valid=true;
  return out;
}

inline unsigned distance(unsigned a,unsigned b) noexcept {
  const int r=int(a>>16)-int(b>>16);
  const int g=int((a>>8)&255)-int((b>>8)&255);
  const int blue=int(a&255)-int(b&255);
  return static_cast<unsigned>(r*r+g*g+blue*blue);
}

struct Search {
  std::array<std::pair<unsigned,unsigned>,255> exact{};
  // Fixed memory; eight local candidates, four weighted knots per RGB sample.
  std::array<std::array<unsigned char,8>,4096> grid{};
  Search() noexcept {
    for(unsigned i=1;i<256;++i) exact[i-1]={source[i],i};
    std::sort(exact.begin(),exact.end());
    for(unsigned bin=0;bin<4096;++bin) {
      const auto rgb=(((bin>>8)*16+8)<<16) |
          ((((bin>>4)&15)*16+8)<<8) | ((bin&15)*16+8);
      std::array<std::pair<unsigned,unsigned>,255> ranked{};
      for(unsigned i=1;i<256;++i) ranked[i-1]={distance(rgb,source[i]),i};
      std::partial_sort(ranked.begin(),ranked.begin()+8,ranked.end());
      for(unsigned i=0;i<8;++i) grid[bin][i]=static_cast<unsigned char>(ranked[i].second);
    }
  }
};

inline std::array<unsigned,3> recolor(std::array<unsigned,3> rgb,
                                    const Transfer& transfer) noexcept {
  if(transfer.identity || (rgb[0]|rgb[1]|rgb[2])==0) return rgb;
  static const Search search;
  const unsigned packed=(rgb[0]<<16)|(rgb[1]<<8)|rgb[2];
  const auto found=std::lower_bound(search.exact.begin(),search.exact.end(),
                                  std::pair<unsigned,unsigned>{packed,0});
  if(found!=search.exact.end() && found->first==packed) {
    for(unsigned c=0;c<3;++c)
      rgb[c]=static_cast<unsigned>(std::clamp(int(rgb[c])+transfer.delta[found->second][c],0,255));
    return rgb;
  }
  const auto bin=((rgb[0]>>4)<<8)|((rgb[1]>>4)<<4)|(rgb[2]>>4);
  std::array<std::pair<unsigned,unsigned>,8> ranked{};
  for(unsigned j=0;j<8;++j) {
    const auto i=search.grid[bin][j];ranked[j]={distance(packed,source[i]),i};
  }
  std::partial_sort(ranked.begin(),ranked.begin()+4,ranked.end());
  std::array<double,3> delta{};double weights=0;
  for(unsigned j=0;j<4;++j) {
    const double weight=1.0/std::max(1u,ranked[j].first);
    weights+=weight;
    for(unsigned c=0;c<3;++c) delta[c]+=weight*transfer.delta[ranked[j].second][c];
  }
  for(unsigned c=0;c<3;++c)
    rgb[c]=static_cast<unsigned>(std::clamp(std::lround(rgb[c]+delta[c]/weights),0L,255L));
  return rgb;
}

inline void apply(std::span<std::byte> pixels,const Transfer& transfer) noexcept {
  if(!transfer.valid || pixels.size()%4 || (transfer.identity && transfer.opacity==255)) return;
  for(std::size_t i=0;i<pixels.size();i+=4) {
    const auto alpha=std::to_integer<unsigned>(pixels[i+3]);
    if(!alpha) continue;
    std::array<unsigned,3> rgb{};
    for(unsigned c=0;c<3;++c)
      rgb[c]=std::min(255u,(std::to_integer<unsigned>(pixels[i+c])*255u+alpha/2)/alpha);
    rgb=recolor(rgb,transfer);
    const auto outputAlpha=(alpha*transfer.opacity+127)/255;
    for(unsigned c=0;c<3;++c) pixels[i+c]=static_cast<std::byte>((rgb[c]*outputAlpha+127)/255);
    pixels[i+3]=static_cast<std::byte>(outputAlpha);
  }
}
} // namespace iee::core::effect_indexed_palette
