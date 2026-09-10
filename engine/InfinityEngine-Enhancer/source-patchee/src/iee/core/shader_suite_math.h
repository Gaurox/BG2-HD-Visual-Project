#pragma once

#include <array>

#include "iee/core/creature_sprite_filter_math.h"
#include "iee/core/shader_suite_config.h"

namespace iee::core::shader_suite_math {

using Rgba = creature_sprite_filter::Rgba;
using SampleBlock = creature_sprite_filter::SampleBlock;
using Weights = creature_sprite_filter::Weights;
using OutlineAlphaBlock = std::array<double, 36>;

struct Rgb {
  double r{};
  double g{};
  double b{};
};

struct OutlineData {
  double distance{};
  double maximumAlpha{};
};

[[nodiscard]] double srgb_to_linear(double value) noexcept;
[[nodiscard]] double linear_to_srgb(double value) noexcept;
[[nodiscard]] Rgba to_working_space(Rgba value,
                                    shader_suite::ColorSpace colorSpace) noexcept;
[[nodiscard]] Rgba from_working_space(Rgba value,
                                      shader_suite::ColorSpace colorSpace) noexcept;
[[nodiscard]] SampleBlock to_working_space(
    const SampleBlock& samples, shader_suite::ColorSpace colorSpace) noexcept;

// Phase-aware four-tap Gaussian weights adapted from Dshaders 0.3.5, sigma
// 2.5. The four weights cover base-1 through base+2 and sum to one.
[[nodiscard]] Weights gaussian_weights(double phase,
                                       double sigma = 2.5) noexcept;
[[nodiscard]] Rgb gaussian_premultiplied_rgb(
    const SampleBlock& workingSamples, double phaseX, double phaseY,
    double sigma = 2.5) noexcept;
[[nodiscard]] Rgba apply_sharpen(Rgba color, Rgb gaussian,
                                 double sharpen) noexcept;
[[nodiscard]] OutlineData outline_data(
    const OutlineAlphaBlock& alpha, double phaseX, double phaseY,
    double outlineSize) noexcept;
[[nodiscard]] Rgba apply_outline(
    Rgba color, Rgb outlineColor, const OutlineAlphaBlock& alpha,
    double phaseX, double phaseY, double outlineSize,
    double opacity = 1.0) noexcept;

// Input is straight RGBA in the profile working space. The output is encoded
// once according to ColorSpace and clamped to finite display values.
[[nodiscard]] Rgba apply_color_adjustments(
    Rgba color, const shader_suite::CreatureHdProfile& profile) noexcept;

}  // namespace iee::core::shader_suite_math
