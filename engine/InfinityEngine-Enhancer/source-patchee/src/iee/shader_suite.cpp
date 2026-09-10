#include "iee/shader_suite.h"

namespace iee::shader_suite {

CreatureFragment classify_creature_fragment(
    std::string_view fragmentShader) noexcept {
  if (fragmentShader == "fpDraw") return CreatureFragment::Draw;
  if (fragmentShader == "fpSprite") return CreatureFragment::Sprite;
  if (fragmentShader == "fpSELECT") return CreatureFragment::Select;
  return CreatureFragment::Unsupported;
}

CreatureHdDrawStyle resolve_creature_hd_draw_style(
    bool suiteEnabled, const core::shader_suite::CreatureHdProfile& profile,
    bool catalogOwned, int textureScale,
    CreatureFragment fragment) noexcept {
  CreatureHdDrawStyle result{};
  if (!suiteEnabled || !profile.enabled || !catalogOwned ||
      !core::shader_suite::valid(profile) ||
      (textureScale != 2 && textureScale != 4) ||
      fragment == CreatureFragment::Unsupported) {
    return result;
  }
  result.active = true;
  result.colorSpace = profile.colorSpace == core::shader_suite::ColorSpace::SrgbLinear
                          ? 1.0f
                          : 0.0f;
  result.sharpen = profile.sharpen;
  result.gamma = profile.gamma;
  result.contrast = profile.contrast;
  result.brightness = profile.brightness;
  result.saturation = profile.saturation;
  result.hueDegrees = profile.hueDegrees;
  result.outlineMode = profile.outlineMode == core::shader_suite::OutlineMode::Dshaders
                           ? 1.0f
                           : 0.0f;
  result.outlineSize = fragment == CreatureFragment::Select
                           ? profile.selectedOutlineSize
                           : profile.outlineSize;
  result.textureScale = static_cast<float>(textureScale);
  return result;
}

}  // namespace iee::shader_suite
