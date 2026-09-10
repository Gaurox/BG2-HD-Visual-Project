#pragma once

#include <cstdint>
#include <string_view>

#include "iee/core/shader_suite_config.h"

namespace iee::shader_suite {

enum class CreatureFragment : std::uint8_t {
  Unsupported,
  Draw,
  Sprite,
  Select,
};

struct CreatureHdDrawStyle {
  bool active{};
  float colorSpace{};
  float sharpen{};
  float gamma{1.0f};
  float contrast{1.0f};
  float brightness{};
  float saturation{1.0f};
  float hueDegrees{};
  float outlineMode{};
  float outlineSize{};
  float textureScale{1.0f};
};

enum class ProfileSource : std::uint8_t {
  None,
  CreatureHd,
  FpSprite,
  FpSelect,
};

struct ResolvedDrawProfile {
  CreatureHdDrawStyle style{};
  ProfileSource source{ProfileSource::None};
  core::shader_suite::Filter filter{core::shader_suite::Filter::Native};
};

// D6 resolver retained for the catalog-owned HD profile and its tests.
[[nodiscard]] CreatureFragment classify_creature_fragment(
    std::string_view fragmentShader) noexcept;
[[nodiscard]] CreatureHdDrawStyle resolve_creature_hd_draw_style(
    bool suiteEnabled, const core::shader_suite::CreatureHdProfile& profile,
    bool catalogOwned, int textureScale,
    CreatureFragment fragment) noexcept;
// D7 priority resolver. CreatureHD wins as one block for owned x2/x4
// textures. A per-shader Filter is always neutral for those owned textures,
// so CreatureSpriteFilter remains their exclusive reconstruction owner.
[[nodiscard]] ResolvedDrawProfile resolve_draw_profile(
    bool suiteEnabled,
    const core::shader_suite::CreatureHdProfile& creatureHd,
    const core::shader_suite::SpriteProfile& fpSprite,
    const core::shader_suite::SpriteProfile& fpSelect,
    bool spriteScopeAvailable, bool catalogOwned, int textureScale,
    CreatureFragment fragment) noexcept;
[[nodiscard]] const char* profile_source_name(ProfileSource source) noexcept;

}  // namespace iee::shader_suite
