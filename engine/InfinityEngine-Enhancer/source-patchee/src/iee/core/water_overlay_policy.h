#pragma once

#include <cmath>
#include <span>
#include <string_view>

namespace iee::core {
inline bool route2_water_layout(std::span<const std::string_view> slots) noexcept {
  if (slots.size() < 2 || slots.size() > 5 || slots[0] != "AR0900" ||
      slots[1] != "WTLAKE") return false;
  for (std::size_t i = 2; i < slots.size(); ++i) {
    if (!slots[i].empty()) return false;
  }
  return true;
}

// Deliberately narrower than the liquid classifier: this experiment owns
// AR0900 DAY's standalone WTLAKE atlas, never a base/secondary map atlas.
inline bool route2_water_identity(std::string_view wed, std::string_view base,
                                 std::string_view overlay, std::string_view page,
                                 unsigned tileCount, int width, int height) noexcept {
  return wed == "AR0900" && base == "AR0900" && overlay == "WTLAKE" &&
         page == "WLAKE00" && tileCount == 6 && width == 2048 && height == 2048;
}

inline float route2_water_strength(float requested) noexcept {
  return std::isfinite(requested) && requested >= 0.0f && requested <= 1.0f
             ? requested : 0.0f;
}
}  // namespace iee::core
