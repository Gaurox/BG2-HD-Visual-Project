#pragma once

#include <cstdint>
#include <string_view>

namespace iee::core::shader_suite {

enum class ColorSpace : std::uint8_t {
  Stored = 0,
  SrgbLinear = 1,
};

enum class OutlineMode : std::uint8_t {
  Native = 0,
  Dshaders = 1,
};

struct CreatureHdProfile {
  bool enabled{};
  ColorSpace colorSpace{ColorSpace::Stored};
  float sharpen{};
  float gamma{1.0f};
  float contrast{1.0f};
  float brightness{};
  float saturation{1.0f};
  float hueDegrees{};
  OutlineMode outlineMode{OutlineMode::Native};
  float outlineSize{2.0f};
  float selectedOutlineSize{3.5f};
};

enum class ApplyResult : std::uint8_t {
  Unrecognized,
  Applied,
  Invalid,
};

[[nodiscard]] const char* color_space_name(ColorSpace value) noexcept;
[[nodiscard]] const char* outline_mode_name(OutlineMode value) noexcept;

// Applies one key from [ShaderSuite.CreatureHD]. Invalid recognized values
// reset only that parameter to its neutral contract value.
[[nodiscard]] ApplyResult apply_creature_hd_parameter(
    CreatureHdProfile& profile, std::string_view key,
    std::string_view value) noexcept;

[[nodiscard]] bool valid(const CreatureHdProfile& profile) noexcept;

}  // namespace iee::core::shader_suite
