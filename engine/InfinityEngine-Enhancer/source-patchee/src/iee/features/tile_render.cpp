#include "tile_render.h"

#include <cstdint>
#include <optional>

#include "iee/app_context.h"
#include "iee/bridge_transition.h"
#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/diagnostics.h"
#include "iee/game/game_types.h"
#include "iee/game/resref_runtime.h"
#include "iee/game/renderer.h"
#include "iee/game/tile_upscale.h"
#include "iee/game/tis_runtime.h"

namespace iee::features {
namespace {
std::atomic<bool> g_resetRenderStateRequest{false};

bool is_wtpool_page(const game::TileInfo& tileInfo) noexcept {
  game::CResTile tile{};
  game::CResPVR pvr{};
  game::ResrefBuffer pvrResref{};
  return core::safe_read(tileInfo.resource, tile) && tile.pvr &&
         core::safe_read(tile.pvr, pvr) &&
         game::read_runtime_resref(pvr.baseclass_0.resref, pvrResref) &&
         game::resref_view(pvrResref) == "WPOOL00";
}

void trace_wtpool_tile(TileRenderState& state, const void* vidTile, int tileIndex) {
  auto& trace = state.wtpoolTrace;
  if (!trace.trackedVidTile) {
    trace.trackedVidTile = vidTile;
    trace.lastIndex = tileIndex;
    LOG_INFO("WTPOOL trace attached to CVidTile=0x{:X}, initialIndex={}",
             reinterpret_cast<std::uintptr_t>(vidTile), tileIndex);
  }
  if (trace.trackedVidTile != vidTile) return;

  if (trace.lastIndex != tileIndex) {
    ++trace.transitions;
    trace.lastIndex = tileIndex;
  }
  ++trace.calls;
  // A call-count window avoids a per-frame log flood while still showing
  // whether this exact CVidTile advances through the expected cycle.
  if (trace.calls == 240) {
    LOG_INFO("WTPOOL trace CVidTile=0x{:X}: calls=240 transitions={} currentIndex={}",
             reinterpret_cast<std::uintptr_t>(vidTile), trace.transitions, trace.lastIndex);
    trace.calls = 0;
    trace.transitions = 0;
  }
}
}  // namespace

TileRenderState& tile_render_state() noexcept {
  static TileRenderState state;
  return state;
}

TileRenderTelemetryStats tile_render_telemetry_snapshot() noexcept {
  return tile_render_state().performance;
}

void request_tile_render_state_reset() noexcept {
  g_resetRenderStateRequest.store(true, std::memory_order_release);
}

bool render_tile(AppContext& ctx, void* vidTile, int texId, void* unused, int x, int y,
                 unsigned long flags) {
  (void)unused;

  using game::DrawMode;
  using game::ShaderTone;

  auto& state = tile_render_state();
  if (g_resetRenderStateRequest.exchange(false, std::memory_order_acquire)) {
    state.reset();
  }
  const auto textureConfigurationEpoch = game::texture_configuration_epoch();
  if (state.lastTextureConfigurationEpoch != textureConfigurationEpoch) {
    state.lastTextureConfigurationEpoch = textureConfigurationEpoch;
    state.lastTexId.store(-1, std::memory_order_relaxed);
  }

  // Try to get tile information
  game::TileInfo tileInfo;
  if (!game::get_tile_info(vidTile, *ctx.manifest, tileInfo, ctx.draw.CRes_Demand)) {
    state.lastTexId.store(-1, std::memory_order_relaxed);
    ++state.consecutiveDecodeFailures;
    if (!state.sawUpscaledTileset &&
        state.consecutiveDecodeFailures >= game::UpscaleThresholds::DETECTION_SAMPLE_COUNT) {
      if (state.consecutiveDecodeFailures == game::UpscaleThresholds::DETECTION_SAMPLE_COUNT) {
        LOG_WARN(
            "RenderTexture hook could not decode {} consecutive tile resources; delegating them "
            "to the engine renderer while continuing to observe later tilesets",
            state.consecutiveDecodeFailures);
      }
    }
    return false;
  }
  state.consecutiveDecodeFailures = 0;

  // Bounds check the tile index before accessing
  if (tileInfo.index < 0 || static_cast<std::uint32_t>(tileInfo.index) >= tileInfo.tileCount) {
    state.lastTexId.store(-1, std::memory_order_relaxed);
    return false;
  }

  const bool isWtpool =
      ctx.cfg.wtpool_page_check_enabled() && is_wtpool_page(tileInfo);
  if (isWtpool && ctx.cfg.enableWtpoolTileTrace) {
    trace_wtpool_tile(state, vidTile, tileInfo.index);
  }
  if (isWtpool && ctx.cfg.bypassWtpoolTileRenderHook) {
    state.lastTexId.store(-1, std::memory_order_relaxed);
    if (!state.wtpoolHookBypassLogged) {
      state.wtpoolHookBypassLogged = true;
      LOG_WARN("WTPOOL test: delegating WPOOL00 to the native RenderTexture path");
    }
    return false;
  }

  // BRIDGE01 is a WED tiled object. The resource index reaching this hook is
  // the engine's final primary/secondary selection, so it is a more reliable
  // lever signal than reconstructing the private CTypedPtrList layout.
  bridge::observe_rendered_tile(tileInfo.index);

  const auto& entry = tileInfo.entry;
  const int u0 = entry.u;
  const int v0 = entry.v;

  auto* tilesetState = state.find_or_add(tileInfo.tileset);
  if (!tilesetState) {
    state.lastTexId.store(-1, std::memory_order_relaxed);
    if (!state.capacityWarningLogged) {
      state.capacityWarningLogged = true;
      LOG_WARN(
          "Area exceeded the bounded {}-tileset runtime cache; delegating uncached tiles to the "
          "engine renderer",
          TileRenderState::kMaxTilesetsPerArea);
    }
    return false;
  }
  if (ctx.cfg.enablePerformanceLogging) {
    // Uses values already decoded by get_tile_info: no diagnostic snapshot or
    // extra guarded read is introduced on the tile hot path.
    state.observe_performance_sample(*tilesetState, tileInfo.entry.page, texId);
  }

  // Detect scale independently for each observed tileset. Standard resources
  // delegate to the engine without preventing a later modded overlay from
  // being classified as upscaled.
  if (!tilesetState->scaleDetected) {
    if (const auto detection = game::detect_scale(tileInfo, texId, *ctx.manifest)) {
      tilesetState->scaleFactor = detection->scaleFactor;
      tilesetState->scaleDetected = true;
      if (detection->scaleFactor > 1) state.sawUpscaledTileset = true;

      switch (detection->source) {
        case game::ScaleDetectionSource::TisHeader:
          LOG_INFO("Detected {}x tileset 0x{:X} from TIS header (tileDimension=0x{:X})",
                   detection->scaleFactor, reinterpret_cast<std::uintptr_t>(tileInfo.tileset),
                   detection->detectedTileDimension);
          break;
        case game::ScaleDetectionSource::TileTable:
          LOG_INFO("Detected {}x tileset 0x{:X} from PVR entry table (grid step=0x{:X})",
                   detection->scaleFactor, reinterpret_cast<std::uintptr_t>(tileInfo.tileset),
                   detection->detectedTileDimension);
          break;
        case game::ScaleDetectionSource::Heuristic:
          LOG_INFO("Detected {}x tileset 0x{:X} via heuristic fallback (texId={}, UV=({}, {}))",
                   detection->scaleFactor, reinterpret_cast<std::uintptr_t>(tileInfo.tileset),
                   texId, entry.u, entry.v);
          break;
      }

      if (detection->scaleFactor == 1) {
        state.lastTexId.store(-1, std::memory_order_relaxed);
        return false;
      }
    } else if (tilesetState->detectionCount < game::UpscaleThresholds::DETECTION_SAMPLE_COUNT) {
      const int sampleCount = ++tilesetState->detectionCount;
      if (sampleCount == 1) {
        if (const auto headerTileDimension =
                game::get_tis_header_tile_dimension(tileInfo, *ctx.manifest)) {
          diagnostics::log_tis_header_diagnostics(
              vidTile, tileInfo,
              "Unsupported deterministic tile metadata; sampling before disabling",
              *headerTileDimension, true);
        } else {
          diagnostics::log_tis_header_diagnostics(
              vidTile, tileInfo,
              "TIS header missing and tile table did not resolve scale; sampling "
              "before disabling",
              std::nullopt, true);
        }
      }

      if (sampleCount == game::UpscaleThresholds::DETECTION_SAMPLE_COUNT) {
        tilesetState->scaleFactor = 1;
        tilesetState->scaleDetected = true;
        LOG_INFO("Tileset 0x{:X} delegated as standard after {} inconclusive samples",
                 reinterpret_cast<std::uintptr_t>(tileInfo.tileset), sampleCount);
      }
      state.lastTexId.store(-1, std::memory_order_relaxed);
      return false;
    }
  }

  if (tilesetState->scaleFactor <= 1) {
    state.lastTexId.store(-1, std::memory_order_relaxed);
    return false;
  }

  const int scaleFactor = tilesetState->scaleFactor;
  const int du = game::TileDimensions::STANDARD_SIZE * scaleFactor;
  const int dv = game::TileDimensions::STANDARD_SIZE * scaleFactor;

  // Explicit diagnostics only: capturing the first draw of each atlas page
  // performs extra guarded reads and flushes an INFO record on the render
  // thread. It must not run in production or ordinary performance telemetry.
  if (ctx.cfg.enableTilePageDiagnostics && entry.page < state.pageDiagnosticSeen.size() &&
      !state.pageDiagnosticSeen[entry.page]) {
    state.pageDiagnosticSeen[entry.page] = true;
    game::CResTile resourceSnapshot{};
    game::CResPVR pvrSnapshot{};
    game::ResrefBuffer pvrResref{};
    const bool haveResource = core::safe_read(tileInfo.resource, resourceSnapshot);
    const bool havePvr = haveResource && resourceSnapshot.pvr &&
                         core::safe_read(resourceSnapshot.pvr, pvrSnapshot);
    const bool havePvrResref =
        havePvr && game::read_runtime_resref(pvrSnapshot.baseclass_0.resref, pvrResref);
    const auto pvrName = havePvrResref ? game::resref_view(pvrResref) : std::string_view{"?"};
    LOG_INFO(
        "TILE_PAGE_DIAG tileset=0x{:X} tile={} tablePage={} uv=({}, {}) "
        "pvr={} pvrTexture={} pvrSize={}x{} texId={} pos=({}, {}) flags=0x{:X}",
        reinterpret_cast<std::uintptr_t>(tileInfo.tileset), tileInfo.index, entry.page,
        entry.u, entry.v, pvrName,
        havePvr ? pvrSnapshot.texture : -1, havePvr ? pvrSnapshot.size.cx : -1,
        havePvr ? pvrSnapshot.size.cy : -1, texId, x, y, flags);
  }

  // Handle special texture cases
  unsigned long savedColor = 0;
  if (texId == 0) {
    if (ctx.draw.DrawDisable) ctx.draw.DrawDisable(1);
    if (ctx.draw.DrawColor) savedColor = ctx.draw.DrawColor(game::BLACK_COLOR);
  } else if (texId != -1) {
    if (ctx.draw.DrawBindTexture) ctx.draw.DrawBindTexture(texId);
  }

  // Successful tile decoding is the identity check; an arbitrary texture-ID
  // threshold can reject valid area textures. The renderer keeps a bounded
  // cache of actual GL texture names and validates recycled names.
  const int currentLastTex = state.lastTexId.load(std::memory_order_relaxed);
  const bool forceTextureFilter = ctx.cfg.forceTextureFilterEveryDraw;
  if (texId > 0 && (forceTextureFilter || texId != currentLastTex)) {
    const bool configured = game::configure_bound_texture(ctx.cfg, texId);
    if (configured) {
      state.lastTexId.store(texId, std::memory_order_relaxed);
      // Avoid a log line per tile while the diagnostic mode intentionally
      // reconfigures every draw.
      if (!forceTextureFilter) LOG_DEBUG_FAST("Enhanced tile texture {}", texId);
    } else {
      // The renderer logs and latches the first failure for this GL object.
      // Mark the consecutive source as attempted so a persistent failure does
      // not re-enter the driver on every tile draw.
      state.lastTexId.store(texId, std::memory_order_relaxed);
    }
  }

  if (ctx.draw.DrawPushState) ctx.draw.DrawPushState();

  int tone = static_cast<int>(ShaderTone::Seam);

  // Check if grey tone is specifically requested via flags
  if (flags & game::RenderFlags::GREY_TONE_MASK) {
    tone = static_cast<int>(ShaderTone::Grey);
  }

  // Check the "linear tiles" switch in TIS structure
  if (!tilesetState->linearFlagDetected) {
    tilesetState->linearTiles = game::get_tis_linear_tiles_flag(tileInfo.tileset, *ctx.manifest);
    tilesetState->linearFlagDetected = true;
  }
  if (tilesetState->linearTiles) {
    tone = static_cast<int>(ShaderTone::Seam);
  }

  if (ctx.draw.DrawColorTone) ctx.draw.DrawColorTone(tone);

  if (ctx.draw.DrawBegin) ctx.draw.DrawBegin(static_cast<int>(DrawMode::Triangles));

  // Keep the 64×64 screen quad (lighting/scissor correctness)
  const int x0 = x;
  const int y0 = y;
  const int x1 = x + game::TileDimensions::RENDER_QUAD_SIZE;
  const int y1 = y + game::TileDimensions::RENDER_QUAD_SIZE;

  // Triangle 1
  if (ctx.draw.DrawTexCoord && ctx.draw.DrawVertex) {
    ctx.draw.DrawTexCoord(u0, v0);
    ctx.draw.DrawVertex(x0, y0);
    ctx.draw.DrawTexCoord(u0, v0 + dv);
    ctx.draw.DrawVertex(x0, y1);
    ctx.draw.DrawTexCoord(u0 + du, v0);
    ctx.draw.DrawVertex(x1, y0);

    // Triangle 2
    ctx.draw.DrawTexCoord(u0 + du, v0);
    ctx.draw.DrawVertex(x1, y0);
    ctx.draw.DrawTexCoord(u0, v0 + dv);
    ctx.draw.DrawVertex(x0, y1);
    ctx.draw.DrawTexCoord(u0 + du, v0 + dv);
    ctx.draw.DrawVertex(x1, y1);
  }

  if (ctx.draw.DrawEnd) ctx.draw.DrawEnd();
  if (texId == 0 && ctx.draw.DrawColor) ctx.draw.DrawColor(savedColor);
  if (ctx.draw.DrawPopState) ctx.draw.DrawPopState();

  return true;
}
}  // namespace iee::features
