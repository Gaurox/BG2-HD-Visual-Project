#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

namespace iee::core::area_lighting {
using Palette = std::array<std::uint32_t, 256>;

// Only these newly produced, unlit assets opt in. Historical packs stay exact.
inline bool enabled(const std::array<char, 8>& ref) noexcept {
  return ref[0] == '1' && ref[1] == '4' && ref[2] == '0' && ref[3] == '0' &&
         ref[4] == 'T' && ref[5] == '0' && ref[6] == '0' && ref[7] >= '1' && ref[7] <= '5';
}

struct Transfer {
  std::array<std::array<std::uint8_t, 256>, 3> rgb{};
  std::uint64_t fingerprint{};
  bool valid{};
};

inline std::uint64_t fingerprint(const Transfer& transfer) noexcept {
  std::uint64_t value = 14695981039346656037ull;
  for (const auto& channel : transfer.rgb) for (const auto component : channel) {
    value = (value ^ component) * 1099511628211ull;
  }
  return value;
}

// Use the live render state, not a brightness threshold or the wall clock.
inline bool tree_night_scene(std::string_view area, std::string_view liveWed) noexcept {
  return (area == "AR1400" && liveWed == "AR1400N") ||
         (area == "AR1404" && liveWed == "AR1404");
}

inline bool customize_tree_night(Transfer& transfer, const std::array<char, 8>& ref,
                                  bool nightScene) noexcept {
  const bool target = enabled(ref) && (ref[7] == '2' || ref[7] == '3' || ref[7] == '5');
  if (!transfer.valid || !nightScene || !target) return false;
  // Preserve the native time/weather transfer; attenuate its final RGB only.
  constexpr std::array<unsigned, 3> gains{60, 55, 85};
  for (unsigned c = 0; c < 3; ++c) for (auto& value : transfer.rgb[c]) {
    value = static_cast<std::uint8_t>((static_cast<unsigned>(value) * gains[c] + 50) / 100);
  }
  transfer.fingerprint = fingerprint(transfer);
  return true;
}

// Read-only transfer from source BGRA palette to this draw's realized palette.
// Native tint/add/light operations act channel-wise. Conflicting per-index
// effects are rejected rather than projected onto an unrelated RGB texture.
inline Transfer derive(const Palette& source, const Palette& realized,
                       bool realizedBgra, std::size_t entries = 256) noexcept {
  Transfer out{};
  if (entries < 16 || entries > 256) return out;
  for (unsigned channel = 0; channel < 3; ++channel) {
    std::array<unsigned, 256> counts{}, sums{};
    std::array<unsigned, 256> lows{}, highs{};
    lows.fill(255);
    const unsigned sourceShift = (2 - channel) * 8;
    const unsigned outputShift = (realizedBgra ? 2 - channel : channel) * 8;
    // Index zero is native transparency; one can be the engine's shadow entry.
    for (std::size_t i = 2; i < entries; ++i) {
      if ((realized[i] >> 24) != 255) continue;
      const unsigned x = (source[i] >> sourceShift) & 255;
      const unsigned y = (realized[i] >> outputShift) & 255;
      ++counts[x]; sums[x] += y;
      lows[x] = std::min(lows[x], y); highs[x] = std::max(highs[x], y);
    }
    std::array<unsigned, 256> knots{};
    std::array<double, 256> values{};
    unsigned n = 0;
    for (unsigned x = 0; x < 256; ++x) {
      if (!counts[x]) continue;
      if (highs[x] - lows[x] > 1) return {};
      knots[n] = x;
      values[n++] = static_cast<double>(sums[x]) / counts[x];
    }
    if (n < 8 || knots[n - 1] - knots[0] < 32) return {};
    for (unsigned i = 1; i < n; ++i) {
      if (values[i] + 1 < values[i - 1]) return {};
    }
    // Endpoint slopes use >=16 source levels to avoid rounding amplification.
    unsigned lower = 1, upper = n - 2;
    while (lower + 1 < n && knots[lower] - knots[0] < 16) ++lower;
    while (upper > 0 && knots[n - 1] - knots[upper] < 16) --upper;
    unsigned segment = 0;
    for (unsigned x = 0; x < 256; ++x) {
      unsigned a = 0, b = lower;
      if (x >= knots[n - 1]) { a = upper; b = n - 1; }
      else if (x > knots[0]) {
        while (segment + 1 < n - 1 && knots[segment + 1] < x) ++segment;
        a = segment; b = segment + 1;
      }
      const double y = values[a] + (values[b] - values[a]) *
          (static_cast<double>(x) - knots[a]) / (knots[b] - knots[a]);
      out.rgb[channel][x] = static_cast<std::uint8_t>(std::clamp(std::lround(y), 0L, 255L));
    }
    for (std::size_t i = 2; i < entries; ++i) {
      if ((realized[i] >> 24) != 255) continue;
      const unsigned x = (source[i] >> sourceShift) & 255;
      const unsigned y = (realized[i] >> outputShift) & 255;
      if (std::abs(static_cast<int>(out.rgb[channel][x]) - static_cast<int>(y)) > 1) return {};
    }
  }
  out.fingerprint = fingerprint(out);
  out.valid = true;
  return out;
}

inline void apply(std::span<std::byte> rgba, const Transfer& transfer) noexcept {
  if (!transfer.valid || rgba.size() % 4 != 0) return;
  for (std::size_t i = 0; i < rgba.size(); i += 4) {
    if (rgba[i + 3] == std::byte{}) continue;
    for (unsigned c = 0; c < 3; ++c) {
      rgba[i + c] = static_cast<std::byte>(transfer.rgb[c][std::to_integer<unsigned>(rgba[i + c])]);
    }
  }
}
}  // namespace iee::core::area_lighting
