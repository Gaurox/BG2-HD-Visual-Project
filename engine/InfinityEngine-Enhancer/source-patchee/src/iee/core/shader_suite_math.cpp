#include "shader_suite_math.h"

#include <algorithm>
#include <cmath>

namespace iee::core::shader_suite_math {
namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kAlphaEpsilon = creature_sprite_filter::kAlphaEpsilon;

double finite_or_zero(double value) noexcept {
  return std::isfinite(value) ? value : 0.0;
}

double normal_cdf(double x, double inverseSigma) noexcept {
  const double scaled = x * inverseSigma;
  const double exponential = std::exp(scaled * scaled * -0.5);
  return std::copysign(1.0, x) * 0.56418958 *
             std::sqrt(std::max(0.0, 1.0 - exponential)) *
             (0.88622692 + exponential * (exponential * -0.042625 + 0.155)) +
         0.5;
}

double segment_distance_squared(double pointX, double pointY,
                                double firstX, double firstY,
                                double secondX, double secondY) noexcept {
  const double deltaX = secondX - firstX;
  const double deltaY = secondY - firstY;
  const double lengthSquared = deltaX * deltaX + deltaY * deltaY;
  if (lengthSquared <= kAlphaEpsilon) {
    const double offsetX = firstX - pointX;
    const double offsetY = firstY - pointY;
    return offsetX * offsetX + offsetY * offsetY;
  }
  const double position = std::clamp(
      ((pointX - firstX) * deltaX + (pointY - firstY) * deltaY) /
          lengthSquared,
      0.0, 1.0);
  const double projectionX = firstX + position * deltaX - pointX;
  const double projectionY = firstY + position * deltaY - pointY;
  return projectionX * projectionX + projectionY * projectionY;
}

double outline_alpha_at(const OutlineAlphaBlock& alpha, int x, int y) noexcept {
  return std::clamp(finite_or_zero(
                        alpha[static_cast<std::size_t>((y + 2) * 6 + x + 2)]),
                    0.0, 1.0);
}

Rgb rotate_hue(Rgb color, double degrees) noexcept {
  if (std::abs(degrees) <= 1.0e-9 ||
      std::abs(std::abs(degrees) - 360.0) <= 1.0e-9) {
    return color;
  }
  const double radians = degrees * kPi / 180.0;
  const double u = std::cos(radians);
  const double w = std::sin(radians);
  const double m00 = 0.299 + 0.701 * u + 0.168 * w;
  const double m01 = 0.587 - 0.587 * u + 0.330 * w;
  const double m02 = 0.114 - 0.114 * u - 0.497 * w;
  const double m10 = 0.299 - 0.299 * u - 0.328 * w;
  const double m11 = 0.587 + 0.413 * u + 0.035 * w;
  const double m12 = 0.114 - 0.114 * u + 0.292 * w;
  const double m20 = 0.299 - 0.300 * u + 1.250 * w;
  const double m21 = 0.587 - 0.588 * u - 1.050 * w;
  const double m22 = 0.114 + 0.886 * u - 0.203 * w;
  return {
      m00 * color.r + m01 * color.g + m02 * color.b,
      m10 * color.r + m11 * color.g + m12 * color.b,
      m20 * color.r + m21 * color.g + m22 * color.b,
  };
}

}  // namespace

double srgb_to_linear(double value) noexcept {
  const double bounded = std::clamp(finite_or_zero(value), 0.0, 1.0);
  return bounded <= 0.039285714
             ? bounded * 0.077380154
             : std::pow(bounded * 0.947867299 + 0.052132701, 2.4);
}

double linear_to_srgb(double value) noexcept {
  const double nonnegative = std::max(0.0, finite_or_zero(value));
  const double encoded = nonnegative <= 0.0030399346
                             ? nonnegative * 12.9232101808
                             : std::pow(nonnegative, 1.0 / 2.4) * 1.055 - 0.055;
  return std::clamp(encoded, 0.0, 1.0);
}

Rgba to_working_space(Rgba value,
                      shader_suite::ColorSpace colorSpace) noexcept {
  value.a = std::clamp(finite_or_zero(value.a), 0.0, 1.0);
  if (value.a <= kAlphaEpsilon) return {};
  value.r = finite_or_zero(value.r);
  value.g = finite_or_zero(value.g);
  value.b = finite_or_zero(value.b);
  if (colorSpace == shader_suite::ColorSpace::SrgbLinear) {
    value.r = srgb_to_linear(value.r);
    value.g = srgb_to_linear(value.g);
    value.b = srgb_to_linear(value.b);
  }
  return value;
}

Rgba from_working_space(Rgba value,
                        shader_suite::ColorSpace colorSpace) noexcept {
  value.a = std::clamp(finite_or_zero(value.a), 0.0, 1.0);
  if (value.a <= kAlphaEpsilon) return {};
  if (colorSpace == shader_suite::ColorSpace::SrgbLinear) {
    value.r = linear_to_srgb(value.r);
    value.g = linear_to_srgb(value.g);
    value.b = linear_to_srgb(value.b);
  } else {
    value.r = std::clamp(finite_or_zero(value.r), 0.0, 1.0);
    value.g = std::clamp(finite_or_zero(value.g), 0.0, 1.0);
    value.b = std::clamp(finite_or_zero(value.b), 0.0, 1.0);
  }
  return value;
}

SampleBlock to_working_space(const SampleBlock& samples,
                             shader_suite::ColorSpace colorSpace) noexcept {
  SampleBlock result{};
  for (std::size_t index = 0; index < samples.size(); ++index) {
    result[index] = to_working_space(samples[index], colorSpace);
  }
  return result;
}

Weights gaussian_weights(double phase, double sigma) noexcept {
  if (!std::isfinite(phase) || !std::isfinite(sigma) || sigma <= 0.0) return {};
  const double t = std::clamp(phase, 0.0, 1.0);
  const double inverseSigma = 1.0 / sigma;
  // D5 phase grows from the base texel center toward base+1, so the
  // Dshaders CDF interval is evaluated at boundary-phase.
  const std::array stops{
      normal_cdf(-t - 1.5, inverseSigma), normal_cdf(-t - 0.5, inverseSigma),
      normal_cdf(-t + 0.5, inverseSigma), normal_cdf(-t + 1.5, inverseSigma),
      normal_cdf(-t + 2.5, inverseSigma),
  };
  const double denominator = stops[4] - stops[0];
  if (!std::isfinite(denominator) || denominator <= 0.0) return {};
  return {
      (stops[1] - stops[0]) / denominator,
      (stops[2] - stops[1]) / denominator,
      (stops[3] - stops[2]) / denominator,
      (stops[4] - stops[3]) / denominator,
  };
}

Rgb gaussian_premultiplied_rgb(const SampleBlock& workingSamples,
                               double phaseX, double phaseY,
                               double sigma) noexcept {
  const auto weightsX = gaussian_weights(phaseX, sigma);
  const auto weightsY = gaussian_weights(phaseY, sigma);
  double alphaSum = 0.0;
  Rgb premultiplied{};
  for (std::size_t y = 0; y < creature_sprite_filter::kKernelWidth; ++y) {
    for (std::size_t x = 0; x < creature_sprite_filter::kKernelWidth; ++x) {
      const auto& sample = workingSamples[y * creature_sprite_filter::kKernelWidth + x];
      const double alpha = std::clamp(finite_or_zero(sample.a), 0.0, 1.0);
      const double weight = weightsX[x] * weightsY[y];
      alphaSum += weight * alpha;
      premultiplied.r += weight * alpha * finite_or_zero(sample.r);
      premultiplied.g += weight * alpha * finite_or_zero(sample.g);
      premultiplied.b += weight * alpha * finite_or_zero(sample.b);
    }
  }
  if (!std::isfinite(alphaSum) || alphaSum <= kAlphaEpsilon) return {};
  return {
      premultiplied.r / alphaSum,
      premultiplied.g / alphaSum,
      premultiplied.b / alphaSum,
  };
}

Rgba apply_sharpen(Rgba color, Rgb gaussian, double sharpen) noexcept {
  const double amount = std::isfinite(sharpen) ? std::clamp(sharpen, -1.0, 1.0) : 0.0;
  color.a = std::clamp(finite_or_zero(color.a), 0.0, 1.0);
  if (color.a <= kAlphaEpsilon) return {};
  color.r = (1.0 + amount) * finite_or_zero(color.r) - amount * finite_or_zero(gaussian.r);
  color.g = (1.0 + amount) * finite_or_zero(color.g) - amount * finite_or_zero(gaussian.g);
  color.b = (1.0 + amount) * finite_or_zero(color.b) - amount * finite_or_zero(gaussian.b);
  return color;
}

OutlineData outline_data(const OutlineAlphaBlock& alpha, double phaseX,
                         double phaseY, double outlineSize) noexcept {
  if (!std::isfinite(phaseX) || !std::isfinite(phaseY) ||
      !std::isfinite(outlineSize) || phaseX < 0.0 || phaseX > 1.0 ||
      phaseY < 0.0 || phaseY > 1.0 || outlineSize < 0.0 ||
      outlineSize > 4.0) {
    return {};
  }
  double distanceSquared = (outlineSize + 1.0) * (outlineSize + 1.0);
  double maximumAlpha = 0.0;
  for (int y = -1; y < 3; ++y) {
    for (int x = -1; x < 3; ++x) {
      const double a00 = outline_alpha_at(alpha, x, y);
      const double a01 = outline_alpha_at(alpha, x + 1, y);
      const double a10 = outline_alpha_at(alpha, x, y + 1);
      const double a11 = outline_alpha_at(alpha, x + 1, y + 1);
      const double highAlpha = std::max({a00, a01, a10, a11});
      const double lowAlpha = std::min({a00, a01, a10, a11});
      maximumAlpha = std::max(maximumAlpha, highAlpha);
      if (0.0625 < lowAlpha || highAlpha <= 0.0625) continue;

      const double lineA0 = (a00 * 3.0 + a01 + a10 - a11) * 0.25 - 0.0625;
      const double lineAX = (a01 + a11 - a00 - a10) * 0.5;
      const double lineBX = (a10 + a11 - a00 - a01) * 0.5;
      std::array<std::array<double, 2>, 2> endpoints{};
      std::size_t count = 0;
      const auto add_endpoint = [&](double first, double second) {
        if (count < endpoints.size()) endpoints[count++] = {first, second};
      };
      if (lineBX != 0.0) {
        const double y0 = -lineA0 / lineBX;
        const double y1 = -(lineA0 + lineAX) / lineBX;
        if (y0 >= 0.0 && y0 <= 1.0) add_endpoint(0.0, y0);
        if (y1 >= 0.0 && y1 <= 1.0) add_endpoint(1.0, y1);
      }
      if (lineAX != 0.0) {
        const double x0 = -lineA0 / lineAX;
        const double x1 = -(lineA0 + lineBX) / lineAX;
        if (x0 >= 0.0 && x0 <= 1.0) add_endpoint(x0, 0.0);
        if (x1 >= 0.0 && x1 <= 1.0) add_endpoint(x1, 1.0);
      }
      if (count == endpoints.size()) {
        distanceSquared = std::min(
            distanceSquared,
            segment_distance_squared(
                phaseX - static_cast<double>(x),
                phaseY - static_cast<double>(y), endpoints[0][0],
                endpoints[0][1], endpoints[1][0], endpoints[1][1]));
      }
    }
  }
  return {std::sqrt(distanceSquared), maximumAlpha};
}

Rgba apply_outline(Rgba color, Rgb outlineColor,
                   const OutlineAlphaBlock& alpha, double phaseX,
                   double phaseY, double outlineSize,
                   double opacity) noexcept {
  color.a = std::clamp(finite_or_zero(color.a), 0.0, 1.0);
  if (!std::isfinite(phaseX) || !std::isfinite(phaseY) || phaseX < 0.0 ||
      phaseX > 1.0 || phaseY < 0.0 || phaseY > 1.0 ||
      !std::isfinite(outlineSize) || outlineSize <= 0.70710678 ||
      outlineSize > 4.0) {
    return color;
  }
  const double boundedOpacity =
      std::clamp(finite_or_zero(opacity), 0.0, 1.0);
  const auto data = outline_data(alpha, phaseX, phaseY, outlineSize);
  double distanceFactor =
      std::max(0.0, 1.0 - data.distance / (outlineSize + 0.29289321));
  distanceFactor *= distanceFactor;
  const double outlineAlpha = distanceFactor *
                              (data.maximumAlpha + 3.0) * 0.25 *
                              boundedOpacity;
  const double combinedAlpha = outlineAlpha * (1.0 - color.a) + color.a;
  if (!std::isfinite(combinedAlpha) || combinedAlpha <= kAlphaEpsilon) return {};
  const auto combine = [&](double outline, double channel) {
    return (finite_or_zero(outline) * distanceFactor * outlineAlpha *
                (1.0 - color.a) +
            finite_or_zero(channel) * color.a) /
           combinedAlpha;
  };
  return {
      .r = combine(outlineColor.r, color.r),
      .g = combine(outlineColor.g, color.g),
      .b = combine(outlineColor.b, color.b),
      .a = std::clamp(combinedAlpha, 0.0, 1.0),
  };
}

Rgba apply_color_adjustments(
    Rgba color, const shader_suite::CreatureHdProfile& profile) noexcept {
  color.a = std::clamp(finite_or_zero(color.a), 0.0, 1.0);
  if (color.a <= kAlphaEpsilon || !shader_suite::valid(profile)) return {};
  Rgb rgb = rotate_hue(
      {finite_or_zero(color.r), finite_or_zero(color.g), finite_or_zero(color.b)},
      profile.hueDegrees);
  const double grey = rgb.r * 0.299 + rgb.g * 0.587 + rgb.b * 0.114;
  rgb.r = rgb.r * profile.saturation + grey * (1.0 - profile.saturation);
  rgb.g = rgb.g * profile.saturation + grey * (1.0 - profile.saturation);
  rgb.b = rgb.b * profile.saturation + grey * (1.0 - profile.saturation);
  const auto finish = [&](double channel) {
    const double contrasted =
        (channel - 0.5) * profile.contrast + 0.5 + profile.brightness;
    return std::pow(std::max(0.0, finite_or_zero(contrasted)), profile.gamma);
  };
  color.r = finish(rgb.r);
  color.g = finish(rgb.g);
  color.b = finish(rgb.b);
  return from_working_space(color, profile.colorSpace);
}

}  // namespace iee::core::shader_suite_math
