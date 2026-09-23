#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "resref_runtime.h"
#include "tile_liquid.h"
#include "tis_runtime.h"

namespace iee::game {
inline constexpr std::size_t kMaxTintTileCandidatesPerOverlay = 128;

struct WedOverlayInfo {
  std::uint16_t width{};
  std::uint16_t height{};
  ResrefBuffer tilesetResref{};
  std::uint32_t tilemapOffset{};
  std::uint32_t tileIndexLookupOffset{};
  TileLiquidMode liquidMode{TileLiquidMode::None};
  std::uint32_t coverageCells{};
  // Bounded unique tile indices used only for authored liquid-tint sampling.
  // Keeping per-cell indices would permit millions of entries per overlay even
  // though the runtime consumes only a small sample.
  std::vector<std::uint16_t> tintTileCandidates{};

  [[nodiscard]] std::string_view tilesetResrefView() const noexcept;
};

struct WedAreaInfo {
  ResrefBuffer areaResref{};
  std::uint32_t overlayCount{};
  std::uint16_t baseWidth{};
  std::uint16_t baseHeight{};
  std::vector<WedOverlayInfo> overlays{};
  std::vector<std::uint8_t> baseOverlayFlags{};

  [[nodiscard]] bool empty() const noexcept { return overlays.empty(); }
  [[nodiscard]] std::string_view areaResrefView() const noexcept;
};

// Mode for an overlay the resref classifier leaves None; runs before coverage
// and tint sampling so a resolved overlay is treated like a prefixed one.
using LiquidModeResolver = TileLiquidMode (*)(const WedAreaInfo& wed,
                                              std::size_t overlayIndex) noexcept;

[[nodiscard]] bool parse_loaded_wed(const CRes& resource, WedAreaInfo& out,
                                    LiquidModeResolver resolver = nullptr) noexcept;

[[nodiscard]] std::uint8_t liquid_overlay_mask(const WedAreaInfo& wed) noexcept;
}  // namespace iee::game
