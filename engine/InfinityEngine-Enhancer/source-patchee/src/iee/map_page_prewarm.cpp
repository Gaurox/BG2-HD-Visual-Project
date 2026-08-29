#include "map_page_prewarm.h"

#include <windows.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <string_view>
#include <utility>
#include <vector>

#include "app_context.h"
#include "area_state.h"
#include "frame_hook.h"
#include "iee/core/logger.h"
#include "iee/core/map_texture_telemetry.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/resref_runtime.h"
#include "iee/game/runtime_types_x64.h"
#include "iee/game/tis_runtime.h"

namespace iee::map_page_prewarm {
namespace {
constexpr std::uint32_t kNativePvrPoolEntries = 128;
constexpr std::uint32_t kNativePvrReserveEntries = 32;
constexpr std::uint32_t kHardMaximumPlannedPages =
    kNativePvrPoolEntries - kNativePvrReserveEntries;
constexpr std::uint32_t kMaximumTilesetEntries = 1'048'576;
constexpr unsigned kMaximumPlanRetries = 180;

struct PageSeed {
  std::uint32_t tileIndex{};
  std::int32_t page{};
};

struct PageCandidate {
  void* wrapper{};
  game::CResTileSet* tis{};
  game::CResPVR* pvr{};
  std::uint32_t tileIndex{};
  std::int32_t page{};
  game::ResrefBuffer tilesetResref{};
  game::ResrefBuffer pageResref{};
};

enum class PlanState : std::uint8_t { Waiting, Running, Finished, Aborted };

struct RuntimeState {
  PlanState state{PlanState::Waiting};
  const game::CGameArea* area{};
  game::CInfTileSet* infTileset{};
  game::CResTileSet* tis{};
  HGLRC context{};
  game::ResrefBuffer areaResref{};
  game::ResrefBuffer tilesetResref{};
  std::vector<PageCandidate> candidates{};
  std::size_t nextCandidate{};
  std::uint64_t areaStartFrame{};
  unsigned planRetries{};
  std::uint32_t waitingFailureMask{};
  unsigned cooldownFrames{};
  std::uint64_t discoveredPages{};
  std::uint64_t cappedPages{};
  std::uint64_t initiallyResident{};
  std::uint64_t alreadyResident{};
  std::uint64_t demandCalls{};
  std::uint64_t materializations{};
  std::uint64_t invalidCandidates{};
  std::uint64_t evictedTextureNames{};
  double totalDemandMs{};
  double maximumDemandMs{};
};

PvrDemandFn g_demand{};
std::atomic<bool> g_resetRequested{true};
RuntimeState g_state{};

void reset_state(std::uint64_t frame) {
  g_state = {};
  g_state.areaStartFrame = frame;
}

std::string_view area_name() noexcept {
  const auto name = game::resref_view(g_state.areaResref);
  return name.empty() ? std::string_view{"?"} : name;
}

void log_summary(std::string_view outcome, std::string_view reason) {
  LOG_INFO(
      "Map page prewarm {}: area={}, reason={}, discoveredPages={}, cappedPages={}, "
      "plannedPages={}, initiallyResident={}, alreadyResident={}, demandCalls={}, "
      "materializations={}, invalidCandidates={}, evictedTextureNames={}, "
      "totalDemandMs={:.2f}, maximumDemandMs={:.2f}; missing pages keep native Demand fallback",
      outcome, area_name(), reason, g_state.discoveredPages, g_state.cappedPages,
      g_state.candidates.size(), g_state.initiallyResident, g_state.alreadyResident,
      g_state.demandCalls, g_state.materializations, g_state.invalidCandidates,
      g_state.evictedTextureNames, g_state.totalDemandMs, g_state.maximumDemandMs);
}

void abort_plan(std::string_view reason) {
  if (g_state.state == PlanState::Aborted || g_state.state == PlanState::Finished) return;
  g_state.state = PlanState::Aborted;
  log_summary("aborted", reason);
}

bool same_resref(std::string_view lhs, const game::ResrefBuffer& rhs) noexcept {
  return lhs == game::resref_view(rhs);
}

bool observe_waiting_area(AppContext& ctx, std::uint64_t frame) noexcept {
  const auto wed = ctx.wed.load(std::memory_order_acquire);
  const auto* area = ctx.activeArea.load(std::memory_order_acquire);
  const auto context = wglGetCurrentContext();
  const auto noteFailure = [](std::uint32_t bit, std::string_view reason) {
    if ((g_state.waitingFailureMask & bit) != 0) return;
    g_state.waitingFailureMask |= bit;
    LOG_INFO("Map page prewarm waiting for a validated area: reason={}", reason);
  };
  if (!wed) {
    noteFailure(1u << 0, "no-published-wed");
  } else if (wed->overlays.empty()) {
    noteFailure(1u << 1, "published-wed-has-no-overlay");
  } else if (!area) {
    noteFailure(1u << 2, "no-published-active-area");
  } else if (!context) {
    noteFailure(1u << 3, "no-current-gl-context-at-callback");
  } else if (wed->areaResrefView().empty() ||
             wed->overlays[0].tilesetResrefView().empty()) {
    noteFailure(1u << 4, "published-wed-identity-empty");
  } else {
    if (g_state.area != area || g_state.context != context ||
        game::resref_view(g_state.areaResref) != wed->areaResrefView()) {
      g_state.area = area;
      g_state.context = context;
      g_state.areaResref = wed->areaResref;
      g_state.areaStartFrame = frame;
      g_state.planRetries = 0;
    }
    return true;
  }

  // Menus and asynchronous load transitions can render for much longer than
  // the retry window. They are not failed area plans and must not consume it.
  g_state.planRetries = 0;
  return false;
}

bool validate_candidate(const PageCandidate& candidate,
                        game::CResPVR& pvrSnapshot) noexcept {
  game::CResTile tile{};
  game::CResTileSet tis{};
  game::ResrefBuffer actualTileset{};
  game::ResrefBuffer actualPage{};
  if (!candidate.wrapper || !candidate.tis || !candidate.pvr ||
      !core::safe_read(candidate.wrapper, tile) || tile.tis != candidate.tis ||
      tile.pvr != candidate.pvr ||
      !core::safe_read(candidate.tis, tis) ||
      !game::read_runtime_resref(tis.baseclass_0.resref, actualTileset) ||
      !game::matches_tis_tile_identity(tile.tileIndex,
                                       game::resref_view(actualTileset),
                                       candidate.tileIndex,
                                       game::resref_view(candidate.tilesetResref)) ||
      !core::safe_read(candidate.pvr, pvrSnapshot) ||
      !game::read_runtime_resref(pvrSnapshot.baseclass_0.resref, actualPage) ||
      !game::matches_pvrz_page_identity(game::resref_view(actualPage),
                                        game::resref_view(candidate.tilesetResref),
                                        candidate.page) ||
      game::resref_view(actualPage) != game::resref_view(candidate.pageResref)) {
    return false;
  }
  return true;
}

bool current_plan_identity_matches(AppContext& ctx) noexcept {
  if (!g_state.area || !g_state.context || wglGetCurrentContext() != g_state.context ||
      ctx.activeArea.load(std::memory_order_acquire) != g_state.area) {
    return false;
  }
  const auto wed = ctx.wed.load(std::memory_order_acquire);
  return wed && wed->areaResrefView() == game::resref_view(g_state.areaResref) &&
         !wed->overlays.empty() &&
         wed->overlays[0].tilesetResrefView() == game::resref_view(g_state.tilesetResref);
}

bool build_plan(AppContext& ctx) {
  const auto wed = ctx.wed.load(std::memory_order_acquire);
  const auto* area = ctx.activeArea.load(std::memory_order_acquire);
  const auto context = wglGetCurrentContext();
  if (!wed || wed->overlays.empty() || !area || !context ||
      wed->areaResrefView().empty() || wed->overlays[0].tilesetResrefView().empty()) {
    return false;
  }

  std::array<game::CInfTileSet*, 5> tileSets{};
  const auto* tileSetsAddress = reinterpret_cast<const std::byte*>(area) +
      offsetof(game::CGameArea, m_cInfinity) + offsetof(game::CInfinity, pTileSets);
  if (!core::safe_read(tileSetsAddress, tileSets) || !tileSets[0]) return false;

  game::CInfTileSet infTileset{};
  if (!core::safe_read(tileSets[0], infTileset) || !infTileset.tis[0] ||
      !infTileset.pResTiles || infTileset.nTiles == 0 ||
      infTileset.nTiles > kMaximumTilesetEntries) {
    return false;
  }

  game::CResTileSet tis{};
  game::ResrefBuffer tisResref{};
  if (!core::safe_read(infTileset.tis[0], tis) || !tis.baseclass_0.bLoaded ||
      !tis.baseclass_0.pData || tis.baseclass_0.nSize != sizeof(game::PVRZTileEntry) ||
      tis.baseclass_0.nCount == 0 || tis.baseclass_0.nCount > kMaximumTilesetEntries ||
      !game::read_runtime_resref(tis.baseclass_0.resref, tisResref) ||
      game::resref_view(tisResref) != wed->overlays[0].tilesetResrefView()) {
    return false;
  }

  game::TileInfo tileInfo{};
  tileInfo.table = static_cast<const game::PVRZTileEntry*>(tis.baseclass_0.pData);
  tileInfo.tileCount = tis.baseclass_0.nCount;
  const auto tileCount = (std::min)(infTileset.nTiles, tis.baseclass_0.nCount);
  std::vector<PageSeed> seeds;
  seeds.reserve(kHardMaximumPlannedPages + 1);
  for (std::uint32_t tileIndex = 0; tileIndex < tileCount; ++tileIndex) {
    game::PVRZTileEntry entry{};
    if (!game::read_tis_tile_entry(tileInfo, tileIndex, entry) || entry.page < 0) continue;
    const auto duplicate = std::find_if(seeds.begin(), seeds.end(), [&](const PageSeed& seed) {
      return seed.page == entry.page;
    });
    if (duplicate == seeds.end()) seeds.push_back({tileIndex, entry.page});
  }
  if (seeds.empty()) return false;

  const auto planLimit = (std::min)(ctx.cfg.mapPagePrewarmMaxPages,
                                    kHardMaximumPlannedPages);
  RuntimeState plan{};
  plan.state = PlanState::Running;
  plan.area = area;
  plan.infTileset = tileSets[0];
  plan.tis = infTileset.tis[0];
  plan.context = context;
  plan.areaResref = wed->areaResref;
  plan.tilesetResref = tisResref;
  plan.areaStartFrame = g_state.areaStartFrame;
  plan.discoveredPages = seeds.size();
  plan.cappedPages = seeds.size() > planLimit ? seeds.size() - planLimit : 0;
  plan.candidates.reserve((std::min)(static_cast<std::size_t>(planLimit), seeds.size()));

  for (std::size_t index = 0; index < seeds.size() && index < planLimit; ++index) {
    const auto& seed = seeds[index];
    void* wrapper = nullptr;
    game::CResTile tile{};
    game::CResPVR pvr{};
    game::ResrefBuffer pageResref{};
    if (!core::safe_read(infTileset.pResTiles + seed.tileIndex, wrapper) || !wrapper ||
        !core::safe_read(wrapper, tile) || tile.tis != infTileset.tis[0] || !tile.pvr ||
        !game::matches_tis_tile_identity(tile.tileIndex, game::resref_view(tisResref),
                                         seed.tileIndex,
                                         wed->overlays[0].tilesetResrefView()) ||
        !core::safe_read(tile.pvr, pvr) ||
        !game::read_runtime_resref(pvr.baseclass_0.resref, pageResref) ||
        !game::matches_pvrz_page_identity(game::resref_view(pageResref),
                                          game::resref_view(tisResref), seed.page)) {
      ++plan.invalidCandidates;
      continue;
    }
    if (pvr.texture > 0) ++plan.initiallyResident;
    plan.candidates.push_back({wrapper, infTileset.tis[0], tile.pvr, seed.tileIndex,
                               seed.page, tisResref, pageResref});
  }

  g_state = std::move(plan);
  LOG_INFO(
      "Map page prewarm plan: area={}, tileset={}, discoveredPages={}, plannedPages={}, "
      "cappedPages={}, initiallyResident={}, invalidCandidates={}, pagesPerFrame={}, "
      "budgetMs={:.2f}, delayFrames={}, nativePoolEntries={}, reservedEntries={}",
      area_name(), game::resref_view(g_state.tilesetResref), g_state.discoveredPages,
      g_state.candidates.size(), g_state.cappedPages, g_state.initiallyResident,
      g_state.invalidCandidates, ctx.cfg.mapPagePrewarmPagesPerFrame,
      ctx.cfg.mapPagePrewarmBudgetMs, ctx.cfg.mapPagePrewarmDelayFrames,
      kNativePvrPoolEntries, kNativePvrReserveEntries);
  if (g_state.candidates.empty()) {
    g_state.state = PlanState::Aborted;
    log_summary("aborted", "no-validated-native-page-wrapper");
  }
  return true;
}

double elapsed_ms(const LARGE_INTEGER& start, const LARGE_INTEGER& end,
                  const LARGE_INTEGER& frequency) noexcept {
  if (frequency.QuadPart <= 0 || end.QuadPart < start.QuadPart) return 0.0;
  return static_cast<double>(end.QuadPart - start.QuadPart) * 1000.0 /
         static_cast<double>(frequency.QuadPart);
}
}  // namespace

void configure(PvrDemandFn demand) noexcept {
  g_demand = demand;
  g_resetRequested.store(true, std::memory_order_release);
}

void request_area_reset() noexcept {
  g_resetRequested.store(true, std::memory_order_release);
}

void on_post_swap(AppContext& ctx) noexcept {
  try {
    if (!ctx.cfg.enableMapPagePrewarm || !ctx.cfg.enablePerformanceLogging || !g_demand) return;

    const auto frame = frame::frame_count();
    if (g_resetRequested.exchange(false, std::memory_order_acq_rel)) {
      reset_state(frame);
    }

    if (g_state.state == PlanState::Waiting) {
      if (!observe_waiting_area(ctx, frame)) return;
      if (frame < g_state.areaStartFrame + ctx.cfg.mapPagePrewarmDelayFrames) return;
      if (!build_plan(ctx)) {
        if (++g_state.planRetries >= kMaximumPlanRetries) {
          g_state.state = PlanState::Aborted;
          log_summary("aborted", "area-or-page-wrappers-never-became-stable");
        }
        return;
      }
    }
    if (g_state.state != PlanState::Running) return;
    if (!current_plan_identity_matches(ctx)) {
      abort_plan("area-or-gl-context-changed");
      return;
    }
    if (g_state.cooldownFrames > 0) {
      --g_state.cooldownFrames;
      return;
    }

    LARGE_INTEGER frequency{};
    LARGE_INTEGER frameStart{};
    if (!QueryPerformanceFrequency(&frequency) || !QueryPerformanceCounter(&frameStart)) {
      abort_plan("performance-clock-unavailable");
      return;
    }

    std::uint32_t processed = 0;
    while (g_state.nextCandidate < g_state.candidates.size() &&
           processed < ctx.cfg.mapPagePrewarmPagesPerFrame) {
      const auto& candidate = g_state.candidates[g_state.nextCandidate++];
      game::CResPVR before{};
      if (!validate_candidate(candidate, before)) {
        ++g_state.invalidCandidates;
        abort_plan("native-page-wrapper-identity-changed");
        return;
      }
      if (before.texture > 0) {
        ++g_state.alreadyResident;
        ++processed;
        continue;
      }

      const auto glBefore = core::gl_texture_telemetry_snapshot();
      LARGE_INTEGER demandStart{};
      LARGE_INTEGER demandEnd{};
      QueryPerformanceCounter(&demandStart);
      (void)g_demand(candidate.pvr);
      QueryPerformanceCounter(&demandEnd);
      const auto demandMs = elapsed_ms(demandStart, demandEnd, frequency);
      ++g_state.demandCalls;
      g_state.totalDemandMs += demandMs;
      g_state.maximumDemandMs = (std::max)(g_state.maximumDemandMs, demandMs);

      game::CResPVR after{};
      if (!validate_candidate(candidate, after)) {
        ++g_state.invalidCandidates;
        abort_plan("native-page-wrapper-changed-during-demand");
        return;
      }
      if (after.texture > 0 && after.texture != before.texture) {
        ++g_state.materializations;
      }
      const auto glAfter = core::gl_texture_telemetry_snapshot();
      if (glAfter.deletedTextureNames > glBefore.deletedTextureNames) {
        g_state.evictedTextureNames +=
            glAfter.deletedTextureNames - glBefore.deletedTextureNames;
        abort_plan("native-cache-eviction-observed");
        return;
      }

      ++processed;
      LARGE_INTEGER now{};
      QueryPerformanceCounter(&now);
      const auto frameMs = elapsed_ms(frameStart, now, frequency);
      if (frameMs >= ctx.cfg.mapPagePrewarmBudgetMs) {
        const auto framesNeeded = static_cast<unsigned>(
            std::ceil(frameMs / static_cast<double>(ctx.cfg.mapPagePrewarmBudgetMs)));
        g_state.cooldownFrames = framesNeeded > 1 ? (std::min)(framesNeeded - 1, 60u) : 0;
        break;
      }
    }

    if (g_state.nextCandidate >= g_state.candidates.size()) {
      g_state.state = PlanState::Finished;
      log_summary("complete", "validated-pages-processed");
    }
  } catch (...) {
    abort_plan("unexpected-exception");
  }
}

void shutdown() noexcept {
  g_demand = nullptr;
  g_resetRequested.store(true, std::memory_order_release);
  g_state = {};
}
}  // namespace iee::map_page_prewarm
