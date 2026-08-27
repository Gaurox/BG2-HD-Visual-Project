#include "tile_liquid.h"

#include <algorithm>
#include <cctype>
#include <initializer_list>
#include <string>

namespace iee::game {
namespace {

std::string upper_copy(std::string_view value) {
  std::string result(value);
  std::transform(result.begin(), result.end(), result.begin(), [](unsigned char character) {
    return static_cast<char>(std::toupper(character));
  });
  return result;
}

bool starts_with_any(std::string_view value,
                     std::initializer_list<std::string_view> prefixes) noexcept {
  for (const auto prefix : prefixes) {
    if (value.starts_with(prefix)) return true;
  }
  return false;
}

}  // namespace

std::string_view tile_liquid_mode_name(TileLiquidMode mode) noexcept {
  switch (mode) {
    case TileLiquidMode::Water:
      return "water";
    case TileLiquidMode::Lava:
      return "lava";
    case TileLiquidMode::Goo:
      return "goo";
    case TileLiquidMode::Sewage:
      return "sewage";
    case TileLiquidMode::Swamp:
      return "swamp";
    case TileLiquidMode::Oil:
      return "oil";
    case TileLiquidMode::None:
    default:
      return "none";
  }
}

TileLiquidMode classify_liquid_tileset(std::string_view resref) noexcept {
  if (resref.empty()) return TileLiquidMode::None;

  const auto upper = upper_copy(resref);
  if (starts_with_any(upper, {"WTLAV"})) return TileLiquidMode::Lava;
  if (starts_with_any(upper, {"WTGOO"})) return TileLiquidMode::Goo;
  if (starts_with_any(upper, {"WTSEW"})) return TileLiquidMode::Sewage;
  if (starts_with_any(upper, {"WTSW"})) return TileLiquidMode::Swamp;
  if (starts_with_any(upper, {"WTOIL"})) return TileLiquidMode::Oil;
  if (starts_with_any(upper, {"WTWAVE", "WTRIV", "WTPOOL", "WTLAK", "WTFALL", "WTURN", "YSPOOL",
                              "YSRIV", "YSWAVE"})) {
    return TileLiquidMode::Water;
  }
  return TileLiquidMode::None;
}

std::optional<std::array<float, 3>> liquid_tileset_fallback_tint(
    std::string_view resref) noexcept {
  const auto upper = upper_copy(resref);
  // Linear-light means of the installed x4 build inputs, or the extracted x1
  // stock frames for overlays deliberately kept stock. Exact resrefs prevent
  // an unknown or modded liquid from inheriting an unrelated palette.
  if (upper == "WTLAKA") {
    return std::array<float, 3>{0.067051f, 0.368126f, 0.406010f};
  }
  if (upper == "WTLAKB") {
    return std::array<float, 3>{0.067983f, 0.372867f, 0.409764f};
  }
  if (upper == "WTLAKC") {
    return std::array<float, 3>{0.066039f, 0.363237f, 0.403121f};
  }
  if (upper == "WTLAKD") {
    return std::array<float, 3>{0.067860f, 0.371557f, 0.409053f};
  }
  if (upper == "WTLAKE") {
    // Keep the visually validated AR2300 state exactly unchanged.
    return std::array<float, 3>{0.062f, 0.089f, 0.117f};
  }
  if (upper == "WTPOOL") {
    return std::array<float, 3>{0.089065f, 0.149378f, 0.234645f};
  }
  if (upper == "WTSWAM") {
    return std::array<float, 3>{0.036129f, 0.099635f, 0.094358f};
  }
  if (upper == "WTSEW") {
    return std::array<float, 3>{0.044581f, 0.059381f, 0.041765f};
  }
  if (upper == "WTOIL") {
    return std::array<float, 3>{0.019028f, 0.015909f, 0.020098f};
  }
  return std::nullopt;
}

}  // namespace iee::game
