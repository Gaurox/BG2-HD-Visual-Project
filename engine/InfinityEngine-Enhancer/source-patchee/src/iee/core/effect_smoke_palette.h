#pragma once
#include "iee/core/area_animation_lighting.h"
#include <span>
namespace iee::core::effect_smoke_palette {
// SPSMPUFF's only coloured source indices are17..22, neutral RGB231..115.
// Use the palette actually realized by the native cell, including PRO ranges.
inline area_lighting::Transfer derive(const area_lighting::Palette& realized,
                                      bool bgra) noexcept {
  area_lighting::Transfer out{};
  const auto opacity=realized[22]>>24;
  constexpr std::array<unsigned,6> levels{115,140,165,189,206,231};
  for (unsigned channel=0; channel<3; ++channel) {
    std::array<unsigned,6> values{};
    for (unsigned i=0;i<6;++i) {
      const auto color=realized[22-i];
      if ((color>>24)!=opacity) return {};
      values[i]=(color>>((bgra?2-channel:channel)*8))&255;
      if (i && values[i]+1<values[i-1]) return {};
    }
    for (unsigned x=0;x<256;++x) {
      // Index1/black remains the native additive neutral. Extrapolating the
      // coloured ramp below115 would illuminate otherwise neutral pixels.
      if (x<levels[0]) {
        out.rgb[channel][x]=static_cast<std::uint8_t>((x*values[0]+levels[0]/2)/levels[0]);
        continue;
      }
      unsigned i=0;
      while(i<4 && x>levels[i+1]) ++i;
      const double y=values[i]+(double(x)-levels[i])*
          (double(values[i+1])-values[i])/(levels[i+1]-levels[i]);
      out.rgb[channel][x]=static_cast<std::uint8_t>(std::clamp(std::lround(y),0L,255L));
    }
  }
  out.valid=true;out.fingerprint=area_lighting::fingerprint(out) ^
      ((std::uint64_t(opacity)+1)*1099511628211ull);return out;
}
inline void apply(std::span<std::byte> rgba,const area_lighting::Transfer& transfer,
                  unsigned opacity=255) noexcept {
  if (!transfer.valid || rgba.size()%4) return;
  for (std::size_t i=0;i<rgba.size();i+=4) {
    const unsigned alpha=std::to_integer<unsigned>(rgba[i+3]);
    if (!alpha) continue;
    const unsigned outputAlpha=(alpha*opacity+127)/255;
    for(unsigned c=0;c<3;++c) {
      const unsigned value=std::to_integer<unsigned>(rgba[i+c]);
      const unsigned straight=std::min(255u,(value*255u+alpha/2)/alpha);
      // Identity leaves even low-alpha premultiplied bytes exactly untouched.
      if (opacity==255 && transfer.rgb[c][straight]==straight) continue;
      rgba[i+c]=static_cast<std::byte>((transfer.rgb[c][straight]*outputAlpha+127)/255);
    }
    rgba[i+3]=static_cast<std::byte>(outputAlpha);
  }
}
}
