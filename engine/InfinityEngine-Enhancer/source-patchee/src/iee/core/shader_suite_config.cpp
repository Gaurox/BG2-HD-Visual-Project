#include "shader_suite_config.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <string>

namespace iee::core::shader_suite {
namespace {

bool iequals(std::string_view left, std::string_view right) noexcept {
  if (left.size() != right.size()) return false;
  for (std::size_t index = 0; index < left.size(); ++index) {
    const auto l = static_cast<unsigned char>(left[index]);
    const auto r = static_cast<unsigned char>(right[index]);
    if (std::tolower(l) != std::tolower(r)) return false;
  }
  return true;
}

bool parse_bool(std::string_view text, bool& value) noexcept {
  if (iequals(text, "1") || iequals(text, "true") ||
      iequals(text, "yes") || iequals(text, "on")) {
    value = true;
    return true;
  }
  if (iequals(text, "0") || iequals(text, "false") ||
      iequals(text, "no") || iequals(text, "off")) {
    value = false;
    return true;
  }
  return false;
}

bool parse_float(std::string_view text, float& value) noexcept {
  try {
    const std::string owned{text};
    std::size_t parsedBytes = 0;
    const float parsed = std::stof(owned, &parsedBytes);
    if (parsedBytes != owned.size() || !std::isfinite(parsed)) return false;
    value = parsed;
    return true;
  } catch (...) {
    return false;
  }
}

ApplyResult apply_number(float& target, std::string_view value, float neutral,
                         float minimum, float maximum,
                         bool exclusiveMinimum = false) noexcept {
  float parsed = neutral;
  if (!parse_float(value, parsed) ||
      (exclusiveMinimum ? parsed <= minimum : parsed < minimum) ||
      parsed > maximum) {
    target = neutral;
    return ApplyResult::Invalid;
  }
  target = parsed;
  return ApplyResult::Applied;
}

}  // namespace

const char* color_space_name(ColorSpace value) noexcept {
  switch (value) {
    case ColorSpace::Stored:
      return "Stored";
    case ColorSpace::SrgbLinear:
      return "SRGBLinear";
  }
  return "Stored";
}

const char* outline_mode_name(OutlineMode value) noexcept {
  switch (value) {
    case OutlineMode::Native:
      return "Native";
    case OutlineMode::Dshaders:
      return "Dshaders";
  }
  return "Native";
}

ApplyResult apply_creature_hd_parameter(CreatureHdProfile& profile,
                                        std::string_view key,
                                        std::string_view value) noexcept {
  if (iequals(key, "Enabled")) {
    bool parsed = false;
    if (!parse_bool(value, parsed)) {
      profile.enabled = false;
      return ApplyResult::Invalid;
    }
    profile.enabled = parsed;
    return ApplyResult::Applied;
  }
  if (iequals(key, "ColorSpace")) {
    if (iequals(value, "Stored")) {
      profile.colorSpace = ColorSpace::Stored;
      return ApplyResult::Applied;
    }
    if (iequals(value, "SRGBLinear")) {
      profile.colorSpace = ColorSpace::SrgbLinear;
      return ApplyResult::Applied;
    }
    profile.colorSpace = ColorSpace::Stored;
    return ApplyResult::Invalid;
  }
  if (iequals(key, "Sharpen")) {
    return apply_number(profile.sharpen, value, 0.0f, -1.0f, 1.0f);
  }
  if (iequals(key, "Gamma")) {
    return apply_number(profile.gamma, value, 1.0f, 0.0f, 4.0f, true);
  }
  if (iequals(key, "Contrast")) {
    return apply_number(profile.contrast, value, 1.0f, 0.0f, 4.0f);
  }
  if (iequals(key, "Brightness")) {
    return apply_number(profile.brightness, value, 0.0f, -1.0f, 1.0f);
  }
  if (iequals(key, "Saturation")) {
    return apply_number(profile.saturation, value, 1.0f, 0.0f, 4.0f);
  }
  if (iequals(key, "HueDegrees")) {
    return apply_number(profile.hueDegrees, value, 0.0f, -360.0f, 360.0f);
  }
  if (iequals(key, "OutlineMode")) {
    if (iequals(value, "Native")) {
      profile.outlineMode = OutlineMode::Native;
      return ApplyResult::Applied;
    }
    if (iequals(value, "Dshaders")) {
      profile.outlineMode = OutlineMode::Dshaders;
      return ApplyResult::Applied;
    }
    profile.outlineMode = OutlineMode::Native;
    return ApplyResult::Invalid;
  }
  if (iequals(key, "OutlineSize")) {
    return apply_number(profile.outlineSize, value, 2.0f, 0.0f, 4.0f);
  }
  if (iequals(key, "SelectedOutlineSize")) {
    return apply_number(profile.selectedOutlineSize, value, 3.5f, 0.0f, 4.0f);
  }
  return ApplyResult::Unrecognized;
}

bool valid(const CreatureHdProfile& profile) noexcept {
  const auto finite_between = [](float value, float minimum, float maximum) {
    return std::isfinite(value) && value >= minimum && value <= maximum;
  };
  return (profile.colorSpace == ColorSpace::Stored ||
          profile.colorSpace == ColorSpace::SrgbLinear) &&
         (profile.outlineMode == OutlineMode::Native ||
          profile.outlineMode == OutlineMode::Dshaders) &&
         finite_between(profile.sharpen, -1.0f, 1.0f) &&
         finite_between(profile.gamma, 0.0f, 4.0f) && profile.gamma > 0.0f &&
         finite_between(profile.contrast, 0.0f, 4.0f) &&
         finite_between(profile.brightness, -1.0f, 1.0f) &&
         finite_between(profile.saturation, 0.0f, 4.0f) &&
         finite_between(profile.hueDegrees, -360.0f, 360.0f) &&
         finite_between(profile.outlineSize, 0.0f, 4.0f) &&
         finite_between(profile.selectedOutlineSize, 0.0f, 4.0f);
}

}  // namespace iee::core::shader_suite
