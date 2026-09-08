#pragma once

#include <array>
#include <cstddef>

namespace iee::core::creature_sprite_filter {

inline constexpr std::size_t kKernelWidth = 4;
inline constexpr std::size_t kKernelSampleCount = kKernelWidth * kKernelWidth;
inline constexpr double kAlphaEpsilon = 1.0e-6;

struct Rgba {
  double r{};
  double g{};
  double b{};
  double a{};
};

using Weights = std::array<double, kKernelWidth>;
using SampleBlock = std::array<Rgba, kKernelSampleCount>;

[[nodiscard]] Weights catmull_rom_weights(double phase) noexcept;

// Samples are row-major and cover base-1 through base+2 on each axis. RGB is
// premultiplied before the signed Catmull-Rom accumulation. Alpha and
// premultiplied RGB are clamped only after the complete 4x4 accumulation.
[[nodiscard]] Rgba reconstruct_premultiplied(const SampleBlock& samples,
                                             double phaseX,
                                             double phaseY) noexcept;

}  // namespace iee::core::creature_sprite_filter
