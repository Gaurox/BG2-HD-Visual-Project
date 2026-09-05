#pragma once
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>

namespace iee {
struct AppContext;
}

namespace iee::game {
struct CResTileSet;
}

namespace iee::features {
struct TilesetRenderState {
  const game::CResTileSet* tileset{};
  int scaleFactor{1};
  int detectionCount{};
  bool scaleDetected{};
  bool linearTiles{};
  bool linearFlagDetected{};
  std::array<std::uint64_t, 2> performancePagesSeen{};
};

struct TileRenderTelemetryStats {
  std::uint64_t decodedTileDraws{};
  std::uint64_t distinctTablePagesObserved{};
  std::uint64_t negativeTablePageSamples{};
  std::uint64_t tablePageAboveCapacitySamples{};
  std::uint64_t sourceTextureIdsObserved{};
  std::uint64_t sourceTextureCapacityMisses{};
};

struct WtpoolTileTraceState {
  const void* trackedVidTile{};
  int lastIndex{-1};
  std::uint32_t calls{};
  std::uint32_t transitions{};

  void reset() noexcept { *this = {}; lastIndex = -1; }
};

// Per-area tile upscale state, owned by this feature (moved out of AppContext).
struct TileRenderState {
  static constexpr std::size_t kMaxTilesetsPerArea = 16;
  static constexpr std::size_t kMaxObservedTextureIds = 256;

  std::atomic<int> lastTexId{-1};
  std::uint64_t lastTextureConfigurationEpoch{};
  std::array<TilesetRenderState, kMaxTilesetsPerArea> tilesets{};
  std::size_t tilesetCount{};
  int consecutiveDecodeFailures{};
  std::array<bool, 128> pageDiagnosticSeen{};
  std::array<int, kMaxObservedTextureIds> performanceTextureIds{};
  TileRenderTelemetryStats performance{};
  WtpoolTileTraceState wtpoolTrace{};
  bool sawUpscaledTileset{};
  bool capacityWarningLogged{};
  bool wtpoolHookBypassLogged{};

  TilesetRenderState* find_or_add(const game::CResTileSet* tileset) noexcept {
    for (std::size_t i = 0; i < tilesetCount; ++i) {
      if (tilesets[i].tileset == tileset) return &tilesets[i];
    }
    if (!tileset || tilesetCount >= tilesets.size()) return nullptr;
    auto& added = tilesets[tilesetCount++];
    added = {.tileset = tileset};
    return &added;
  }

  void observe_performance_sample(TilesetRenderState& tilesetState, int tablePage,
                                  int textureId) noexcept {
    ++performance.decodedTileDraws;
    if (tablePage < 0) {
      ++performance.negativeTablePageSamples;
    } else if (tablePage < 128) {
      const auto page = static_cast<unsigned>(tablePage);
      const auto word = page / 64;
      const auto mask = std::uint64_t{1} << (page % 64);
      if ((tilesetState.performancePagesSeen[word] & mask) == 0) {
        tilesetState.performancePagesSeen[word] |= mask;
        ++performance.distinctTablePagesObserved;
      }
    } else {
      ++performance.tablePageAboveCapacitySamples;
    }

    if (textureId <= 0) return;
    const auto value = static_cast<std::uint32_t>(textureId);
    auto slot = static_cast<std::size_t>((value * 2654435761u) &
                                         (kMaxObservedTextureIds - 1));
    for (std::size_t probe = 0; probe < performanceTextureIds.size(); ++probe) {
      auto& candidate = performanceTextureIds[slot];
      if (candidate == textureId) return;
      if (candidate == 0) {
        candidate = textureId;
        ++performance.sourceTextureIdsObserved;
        return;
      }
      slot = (slot + 1) & (kMaxObservedTextureIds - 1);
    }
    ++performance.sourceTextureCapacityMisses;
  }

  void reset() noexcept {
    lastTexId.store(-1, std::memory_order_relaxed);
    lastTextureConfigurationEpoch = 0;
    tilesets = {};
    tilesetCount = 0;
    consecutiveDecodeFailures = 0;
    pageDiagnosticSeen = {};
    performanceTextureIds = {};
    performance = {};
    wtpoolTrace.reset();
    sawUpscaledTileset = false;
    capacityWarningLogged = false;
    wtpoolHookBypassLogged = false;
  }
};

TileRenderState& tile_render_state() noexcept;
[[nodiscard]] TileRenderTelemetryStats tile_render_telemetry_snapshot() noexcept;

// LoadArea may run at a different engine boundary from rendering. Request a
// reset here; the render thread consumes it before touching non-atomic state.
void request_tile_render_state_reset() noexcept;

// Tile upscale render path. Returns true if it fully handled the draw;
// false means the caller must invoke the original RenderTexture.
// Never calls the original itself; the dispatcher remains installed for the
// area so modded overlays encountered after a standard base can still be
// classified independently.
bool render_tile(AppContext& ctx, void* vidTile, int texId, void* unused, int x, int y,
                 unsigned long flags);
}  // namespace iee::features
