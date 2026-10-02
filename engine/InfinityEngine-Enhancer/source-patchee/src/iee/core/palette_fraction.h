#pragma once

#include <array>
#include <bitset>
#include <cstdint>
#include <span>
#include "iee/core/monster_palette_profiles.h"

namespace iee::core::palette_fraction {
// V6 profile/rule namespaces. Unknown IDs fail closed in the registry reader.
inline constexpr std::uint32_t kCharacterProfile = 1;  // character-bg2ee-2.7.3.0
inline constexpr std::uint32_t kSrgb8Rule = 1;          // ramp-lerp-srgb8-v1
using Dependencies = std::array<std::uint8_t, 32>;
using Palette = std::array<std::uint32_t, 256>;

constexpr bool supported_profile(std::uint32_t profile, std::uint32_t rule) noexcept {
  return (profile == kCharacterProfile && rule == kSrgb8Rule) || monster_profile(profile, rule);
}

constexpr bool profile_owner(std::uint32_t profile, std::uint32_t rule,
                              std::uint32_t owner, std::uint16_t animation) noexcept {
  return (profile == kCharacterProfile && rule == kSrgb8Rule) ? owner == 1
      : monster_profile(profile, rule) && monster_owner(profile, owner, animation);
}

constexpr std::uint8_t successor(std::uint8_t i, std::uint32_t profile = kCharacterProfile) noexcept {
  if (profile >= 2 && profile <= 7) return kMonsterSuccessors[profile-2][i];
  if (i <= 3 || (i < 88 ? (i - 4) % 12 == 11 : (i - 88) % 8 == 7)) return i;
  return static_cast<std::uint8_t>(i + 1);
}

// On the supported little-endian native encodings color occupies the low
// three bytes (RGBA or BGRA); primary alpha occupies the high byte.
inline std::uint32_t decode(std::uint8_t i, std::uint8_t f,
                            const Palette& palette, std::uint32_t profile = kCharacterProfile) noexcept {
  const auto a = (profile != kCharacterProfile && i == 0) ? (palette[i] & 0x00ffffffu) : palette[i];
  if (f == 0) return a;  // Do not read a successor outside the dependency mask.
  const auto b = palette[successor(i, profile)];
  std::uint32_t result = a & 0xff000000u;
  for (unsigned shift = 0; shift < 24; shift += 8) {
    const auto value = (((a >> shift) & 255u) * (8u - f) +
                         ((b >> shift) & 255u) * f + 4u) >> 3;
    result |= value << shift;
  }
  return result;
}

inline bool validate(std::span<const std::uint8_t> indices,
                      std::span<const std::uint8_t> fractions,
                      const Dependencies& expected, std::uint32_t profile = kCharacterProfile,
                      std::uint32_t rule = kSrgb8Rule) noexcept {
  if (!supported_profile(profile, rule)) return false;
  if (indices.empty() || (!fractions.empty() && fractions.size() != indices.size())) return false;
  Dependencies actual{};
  for (std::size_t n = 0; n < indices.size(); ++n) {
    const auto i = indices[n];
    const auto f = fractions.empty() ? 0 : fractions[n];
    if (f > 7 || (f != 0 && successor(i, profile) == i)) return false;
    actual[i / 8] |= static_cast<std::uint8_t>(1u << (i % 8));
    if (f != 0) {
      const auto s = successor(i, profile);
      actual[s / 8] |= static_cast<std::uint8_t>(1u << (s % 8));
    }
  }
  return actual == expected;
}

// Frame-scoped scratch. Only pairs used by this frame read the palette.
// A complete palette LUT would read entries outside an exact dep_mask.
struct Lut {
  std::array<std::uint32_t, 2048> colors{};
  bool prepare(std::span<const std::uint8_t> indices,
               std::span<const std::uint8_t> fractions,
               const Palette& palette, std::uint32_t profile = kCharacterProfile,
               std::uint32_t rule = kSrgb8Rule) noexcept {
    if (!supported_profile(profile, rule)) return false;
    if (!fractions.empty() && fractions.size() != indices.size()) return false;
    std::bitset<2048> filled;
    for (std::size_t n = 0; n < indices.size(); ++n) {
      const auto i = indices[n];
      const auto f = fractions.empty() ? std::uint8_t{0} : fractions[n];
      if (f > 7 || (f != 0 && successor(i, profile) == i)) return false;
      if (profile != kCharacterProfile && f != 0 &&
          (palette[i] >> 24) != (palette[successor(i, profile)] >> 24)) return false;
      const auto pair = static_cast<std::size_t>(i) * 8 + f;
      if (!filled[pair]) {
        colors[pair] = decode(i, f, palette, profile);
        filled.set(pair);
      }
    }
    return true;
  }
  std::uint32_t pixel(std::uint8_t i, std::uint8_t f) const noexcept {
    return colors[static_cast<std::size_t>(i) * 8 + f];
  }
};
}  // namespace iee::core::palette_fraction
