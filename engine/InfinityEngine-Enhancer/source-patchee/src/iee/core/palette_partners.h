#pragma once

#include <array>
#include <cstdint>

namespace iee::core::palette_fraction {
// V7: second plane stores (partner << 3) | fraction. Native palette remains live.
inline constexpr std::uint32_t kFourPartnerRule = 3;
inline constexpr std::uint32_t kFourPartnerFixedProfile = 8;
inline constexpr std::uint32_t kFourPartnerRangeProfile = 9;
struct PartnerProfile {
  std::uint32_t nativeKind{};
  std::array<std::uint32_t, 256> sourcePalette{};
  std::array<std::array<std::uint8_t, 4>, 256> partners{};

  constexpr unsigned semantic_class(unsigned i) const noexcept {
    if (nativeKind == 0) return i < 3 ? i : 3;
    if (i < 4) return i;
    return i < 88 ? 4 + (i - 4) / 12 : 11 + (i - 88) / 8;
  }
  constexpr bool valid(std::uint32_t profile, std::uint32_t rule) const noexcept {
    if (rule != kFourPartnerRule || nativeKind > 1 ||
        profile != (nativeKind == 0 ? kFourPartnerFixedProfile : kFourPartnerRangeProfile)) return false;
    for (unsigned i = 0; i < 256; ++i) {
      for (const auto j : partners[i]) {
        if (semantic_class(i) != semantic_class(j) ||
            (i < (nativeKind == 0 ? 3u : 4u) && i != j)) return false;
      }
    }
    return true;
  }
};
constexpr bool four_partner_profile(std::uint32_t profile, std::uint32_t rule) noexcept {
  return rule == kFourPartnerRule &&
      (profile == kFourPartnerFixedProfile || profile == kFourPartnerRangeProfile);
}
}  // namespace iee::core::palette_fraction
