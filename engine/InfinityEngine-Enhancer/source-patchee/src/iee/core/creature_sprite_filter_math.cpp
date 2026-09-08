#include "creature_sprite_filter_math.h"

#include <algorithm>
#include <cmath>

namespace iee::core::creature_sprite_filter {
namespace {

[[nodiscard]] double finite_or_zero(double value) noexcept {
  return std::isfinite(value) ? value : 0.0;
}

}  // namespace

Weights catmull_rom_weights(double phase) noexcept {
  if (!std::isfinite(phase)) return {};

  const double t = std::clamp(phase, 0.0, 1.0);
  const double t2 = t * t;
  const double t3 = t2 * t;
  return {
      -0.5 * t + t2 - 0.5 * t3,
      1.0 - 2.5 * t2 + 1.5 * t3,
      0.5 * t + 2.0 * t2 - 1.5 * t3,
      -0.5 * t2 + 0.5 * t3,
  };
}

Rgba reconstruct_premultiplied(const SampleBlock& samples, double phaseX,
                                double phaseY) noexcept {
  if (!std::isfinite(phaseX) || !std::isfinite(phaseY)) return {};

  const auto weightsX = catmull_rom_weights(phaseX);
  const auto weightsY = catmull_rom_weights(phaseY);
  double alphaRaw = 0.0;
  std::array<double, 3> premultipliedRaw{};

  for (std::size_t y = 0; y < kKernelWidth; ++y) {
    for (std::size_t x = 0; x < kKernelWidth; ++x) {
      const auto& sample = samples[y * kKernelWidth + x];
      const double weight = weightsX[x] * weightsY[y];
      const double alpha = std::clamp(finite_or_zero(sample.a), 0.0, 1.0);
      alphaRaw += weight * alpha;
      if (alpha == 0.0) continue;
      premultipliedRaw[0] += weight * finite_or_zero(sample.r) * alpha;
      premultipliedRaw[1] += weight * finite_or_zero(sample.g) * alpha;
      premultipliedRaw[2] += weight * finite_or_zero(sample.b) * alpha;
    }
  }

  const double alpha = std::clamp(alphaRaw, 0.0, 1.0);
  if (alpha <= kAlphaEpsilon) return {};

  const auto unpremultiply = [alpha](double value) noexcept {
    return std::clamp(value, 0.0, alpha) / alpha;
  };
  return {
      unpremultiply(premultipliedRaw[0]),
      unpremultiply(premultipliedRaw[1]),
      unpremultiply(premultipliedRaw[2]),
      alpha,
  };
}

}  // namespace iee::core::creature_sprite_filter
