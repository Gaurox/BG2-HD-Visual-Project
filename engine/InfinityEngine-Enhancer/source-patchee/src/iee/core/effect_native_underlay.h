#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <span>
#include <optional>
#include <vector>

namespace iee::core::effect_native_underlay {
inline std::optional<unsigned> uniform_opacity(std::span<const std::uint32_t> palette) noexcept {
  unsigned alpha=0;
  for(std::size_t i=2;i<palette.size();++i) {
    const unsigned current=palette[i]>>24;
    if(!current) continue;
    if(alpha && current!=alpha) return {};
    alpha=current;
  }
  return alpha ? std::optional<unsigned>{alpha} : std::nullopt;
}
// BG2EE's BAM-to-FX kernel (426E43/426F66/42706E) writes realized pixels;
// it does not source-over blend the BAM into preceding FX layers. Preserve
// native prefix pixels wherever the HD layer has no support, including RGB
// with zero alpha used by additive effects. Input/output are RGBA8.
inline bool compose(std::span<const std::byte> frame, int width, int height,
                    int canvasWidth, int canvasHeight, int x, int y,
                    std::span<const std::byte> nativePrefix, unsigned opacity,
                    std::vector<std::byte>& out) noexcept {
  if (width<=0 || height<=0 || canvasWidth<=0 || canvasHeight<=0 ||
      canvasWidth>1024 || canvasHeight>1024 || x<0 || y<0 ||
      width>canvasWidth-x || height>canvasHeight-y || opacity>255 ||
      frame.size()!=std::size_t(width)*height*64 ||
      nativePrefix.size()!=std::size_t(canvasWidth)*canvasHeight*4) return false;
  try {
  out.resize(std::size_t(canvasWidth)*canvasHeight*64);
  for (int py=0;py<canvasHeight*4;++py) for (int px=0;px<canvasWidth*4;++px) {
    const auto src=(std::size_t(py/4)*canvasWidth+px/4)*4;
    const auto dst=(std::size_t(py)*canvasWidth*4+px)*4;
    std::copy_n(nativePrefix.data()+src,4,out.data()+dst);
  }
  for (int py=0;py<height*4;++py) for (int px=0;px<width*4;++px) {
    const auto src=(std::size_t(py)*width*4+px)*4;
    if (frame[src]==std::byte{} && frame[src+1]==std::byte{} &&
        frame[src+2]==std::byte{} && frame[src+3]==std::byte{}) continue;
    const auto dst=((std::size_t(py)+y*4)*canvasWidth*4+px+x*4)*4;
    std::copy_n(frame.data()+src,4,out.data()+dst);
    // Palette realization modulates alpha, not RGB, in this native write path.
    out[dst+3]=static_cast<std::byte>((std::to_integer<unsigned>(frame[src+3])*opacity+127)/255);
  }
  return true;
  } catch(...) {out.clear();return false;}
}
inline std::uint64_t fingerprint(std::span<const std::byte> prefix,unsigned opacity) noexcept {
  if(prefix.empty()) return 0;
  std::uint64_t hash=14695981039346656037ull;
  for(auto b:prefix) hash=(hash^std::to_integer<unsigned>(b))*1099511628211ull;
  return (hash^(std::uint64_t(opacity)+1))*1099511628211ull;
}
}
