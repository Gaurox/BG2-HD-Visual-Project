#pragma once

#include <algorithm>
#include <cstdint>
#include <vector>

namespace iee::core {
// Optional inward coverage for the non-dithered BDFORCEW WED cut. R/G/B
// remain the exact native transfer; unused A holds coverage reconstructed
// continuously at x4. Never reveals any native-cleared pixel.
inline bool inward_occlusion_coverage(std::vector<std::uint8_t>& transfer,
                                     int width, int height) {
  if (width <= 0 || height <= 0 ||
      static_cast<std::uint64_t>(width) * height > 2u * 1024u * 1024u ||
      transfer.size() != static_cast<std::size_t>(width) * height * 4u) return false;
  std::vector<float> distance(static_cast<std::size_t>(width) * height, 5.0f);
  bool cleared = false;
  for (std::size_t i = 0; i < distance.size(); ++i) {
    // Retain the exact path for fixed-alpha dither or fractional transfers.
    if (transfer[i * 4 + 1] != 0 ||
        (transfer[i * 4] != 0 && transfer[i * 4] != 255)) return false;
    if (transfer[i * 4] == 0 || transfer[i * 4 + 2] != 0) {
      distance[i] = 0.0f;
      cleared = true;
    }
  }
  if (!cleared) return false;
  constexpr float diagonal = 1.41421356237f;
  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) {
      const auto i = static_cast<std::size_t>(y) * width + x;
      auto& d = distance[i];
      if (x > 0) d = std::min(d, distance[i - 1] + 1.0f);
      if (y > 0) {
        d = std::min(d, distance[i - width] + 1.0f);
        if (x > 0) d = std::min(d, distance[i - width - 1] + diagonal);
        if (x + 1 < width) d = std::min(d, distance[i - width + 1] + diagonal);
      }
    }
  }
  for (int y = height - 1; y >= 0; --y) {
    for (int x = width - 1; x >= 0; --x) {
      const auto i = static_cast<std::size_t>(y) * width + x;
      auto& d = distance[i];
      if (x + 1 < width) d = std::min(d, distance[i + 1] + 1.0f);
      if (y + 1 < height) {
        d = std::min(d, distance[i + width] + 1.0f);
        if (x > 0) d = std::min(d, distance[i + width - 1] + diagonal);
        if (x + 1 < width) d = std::min(d, distance[i + width + 1] + diagonal);
      }
    }
  }
  for (std::size_t i = 0; i < distance.size(); ++i) {
    // One zero-coverage inner logical cell guards the exact hard cut; the
    // following four logical pixels (16 x4 pixels) restore the first smooth
    // treatment. The OH8100 visual placement is adjusted after this mask.
    const float t = std::clamp((distance[i] - 1.0f) / 4.0f, 0.0f, 1.0f);
    transfer[i * 4 + 3] = static_cast<std::uint8_t>(255.0f * t * t * (3.0f - 2.0f * t) + 0.5f);
  }
  return true;
}
}  // namespace iee::core
