#include "iee/shader_suite.h"

namespace iee::shader_suite {
namespace {

template <typename Profile>
CreatureHdDrawStyle style_from_profile(const Profile& profile,
                                       int textureScale) noexcept {
  CreatureHdDrawStyle result{};
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
  result.outlineSize = profile.outlineSize;
  result.textureScale = static_cast<float>(textureScale);
  return result;
}

}  // namespace

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
  result = style_from_profile(profile, textureScale);
  result.outlineSize = fragment == CreatureFragment::Select
                           ? profile.selectedOutlineSize
                           : profile.outlineSize;
  return result;
}

ResolvedDrawProfile resolve_draw_profile(
    bool suiteEnabled,
    const core::shader_suite::CreatureHdProfile& creatureHd,
    const core::shader_suite::SpriteProfile& fpSprite,
    const core::shader_suite::SpriteProfile& fpSelect,
    bool spriteScopeAvailable, bool catalogOwned, int textureScale,
    CreatureFragment fragment) noexcept {
  ResolvedDrawProfile result{};
  if (!suiteEnabled || fragment == CreatureFragment::Unsupported) return result;

  if (catalogOwned && creatureHd.enabled) {
    result.style = resolve_creature_hd_draw_style(
        true, creatureHd, true, textureScale, fragment);
    if (result.style.active) result.source = ProfileSource::CreatureHd;
    return result;
  }

  if (!spriteScopeAvailable ||
      (fragment != CreatureFragment::Sprite &&
       fragment != CreatureFragment::Select)) {
    return result;
  }
  const auto& profile = fragment == CreatureFragment::Sprite ? fpSprite : fpSelect;
  if (!profile.enabled || !core::shader_suite::valid(profile) ||
      (catalogOwned ? (textureScale != 2 && textureScale != 4)
                    : textureScale != 1)) {
    return result;
  }

  result.style = style_from_profile(profile, textureScale);
  result.source = fragment == CreatureFragment::Sprite
                      ? ProfileSource::FpSprite
                      : ProfileSource::FpSelect;
  // HD reconstruction remains exclusively owned by the D1 setting even
  // when CreatureHD is disabled and the shader profile supplies the style.
  result.filter = catalogOwned ? core::shader_suite::Filter::Native
                               : profile.filter;
  return result;
}

X1SamplerPlan resolve_x1_sampler_plan(
    core::shader_suite::Filter filter, bool profileActive, bool catalogOwned,
    bool minFilterNearest, bool magFilterNearest) noexcept {
  X1SamplerPlan result{};
  if (!profileActive || catalogOwned ||
      filter != core::shader_suite::Filter::CatmullRom) {
    return result;
  }
  result.catmullRomActive = true;
  result.overrideMinFilter = !minFilterNearest;
  result.overrideMagFilter = !magFilterNearest;
  return result;
}

bool should_route_x1_to_fp_sprite(
    bool suiteEnabled, const core::shader_suite::SpriteProfile& fpSprite,
    SpriteScopeOwner owner, bool hdOwned, bool replacementBound,
    int nativeTone, bool fpSpriteContractReady) noexcept {
  return suiteEnabled && fpSprite.enabled &&
         core::shader_suite::valid(fpSprite) &&
         owner != SpriteScopeOwner::None && !hdOwned && !replacementBound &&
         nativeTone == 0 && fpSpriteContractReady;
}

const char* profile_source_name(ProfileSource source) noexcept {
  switch (source) {
    case ProfileSource::None:
      return "none";
    case ProfileSource::CreatureHd:
      return "CreatureHD";
    case ProfileSource::FpSprite:
      return "fpSprite";
    case ProfileSource::FpSelect:
      return "fpSELECT";
  }
  return "none";
}

}  // namespace iee::shader_suite
