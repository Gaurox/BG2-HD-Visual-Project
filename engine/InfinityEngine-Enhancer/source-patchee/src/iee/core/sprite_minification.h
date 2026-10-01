#pragma once

#include <algorithm>
#include <cstdint>
#include <span>
#include <vector>

namespace iee::core::sprite_minification {
struct MipLayout {
  int maximumLevel{};
  std::uint64_t bytes{};
};

// Exact RGBA8 storage, including NPOT floor-halves and the last 1x1 level.
inline MipLayout mip_layout(int width, int height) noexcept {
  if (width <= 0 || height <= 0 || width > 8192 || height > 8192) return {};
  MipLayout result{};
  for (;;) {
    result.bytes += static_cast<std::uint64_t>(width) * height * 4ull;
    if (width == 1 && height == 1) return result;
    width = (std::max)(1, width / 2);
    height = (std::max)(1, height / 2);
    ++result.maximumLevel;
  }
}

// Both supported native little-endian RGBA/BGRA words store alpha in byte 3.
// Opaque bytes are exact; hidden RGB is cleared; the source cache stays straight.
inline std::uint32_t premultiply(std::uint32_t pixel) noexcept {
  const auto alpha = pixel >> 24;
  std::uint32_t result = pixel & 0xff000000u;
  for (unsigned shift = 0; shift < 24; shift += 8)
    result |= (((pixel >> shift & 255u) * alpha + 127u) / 255u) << shift;
  return result;
}

inline bool premultiply_copy(std::span<const std::uint32_t> input,
                             std::vector<std::uint32_t>& output) noexcept {
  try {
    output.resize(input.size());
    std::transform(input.begin(), input.end(), output.begin(), premultiply);
    return true;
  } catch (...) {
    output.clear();
    return false;
  }
}
}  // namespace iee::core::sprite_minification
