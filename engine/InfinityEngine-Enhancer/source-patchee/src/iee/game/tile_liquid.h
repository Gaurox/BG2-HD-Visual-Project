#pragma once

#include <array>
#include <optional>
#include <string_view>

namespace iee::game {
enum class TileLiquidMode : int {
  None = 0,
  Water = 1,
  Lava = 2,
  Goo = 3,
  Sewage = 4,
  Swamp = 5,
  Oil = 6,
};

[[nodiscard]] std::string_view tile_liquid_mode_name(TileLiquidMode mode) noexcept;

[[nodiscard]] TileLiquidMode classify_liquid_tileset(std::string_view resref) noexcept;

// Deterministic authored tint used only when a modern PVRZ page cannot be
// sampled at runtime. Presets are deliberately exact-resref and opt-in so an
// unknown river, pool, swamp, or mod asset never inherits an unrelated color.
[[nodiscard]] std::optional<std::array<float, 3>> liquid_tileset_fallback_tint(
    std::string_view resref) noexcept;
}  // namespace iee::game
