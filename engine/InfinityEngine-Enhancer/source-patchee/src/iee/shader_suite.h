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

// D6 resolves only catalog-owned HD creature draws. D7 owns the future
// non-HD fpSprite/fpSELECT expansion.
[[nodiscard]] CreatureFragment classify_creature_fragment(
    std::string_view fragmentShader) noexcept;
[[nodiscard]] CreatureHdDrawStyle resolve_creature_hd_draw_style(
    bool suiteEnabled, const core::shader_suite::CreatureHdProfile& profile,
    bool catalogOwned, int textureScale,
    CreatureFragment fragment) noexcept;

}  // namespace iee::shader_suite
