#pragma once

#include <algorithm>
#include <cmath>
namespace iee::core {
inline float route2_water_strength(float requested, float approved = 1.0f) noexcept {
  return std::isfinite(requested) && std::isfinite(approved) &&
                 requested >= 0.0f && requested <= 1.0f &&
                 approved >= 0.0f && approved <= 1.0f
             ? std::min(requested, approved) : 0.0f;
}
}  // namespace iee::core
