#include "map_page_prewarm.h"

#include <windows.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string_view>
#include <utility>
#include <vector>

#include "app_context.h"
#include "area_state.h"
#include "frame_hook.h"
#include "iee/core/logger.h"
#include "iee/core/map_page_shadow.h"
#include "iee/core/map_texture_telemetry.h"
#include "iee/core/pattern_scanner.h"
#include "iee/core/process_lifetime_worker.h"
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
  bool initiallyResident{};
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
  std::uint64_t shadowGeneration{};
  bool shadowDemandSummaryLogged{};
  std::optional<std::size_t> shadowScheduledCandidate{};
  std::uint64_t shadowJustInTimeSubmissions{};
  std::uint64_t shadowIdleWaitFrames{};
  std::uint64_t shadowWideViewStops{};
  bool wideViewObserved{};
  std::uint64_t consumeClaims{};
  std::uint64_t consumeConsumed{};
  std::uint64_t consumeFallbacks{};
  std::uint64_t consumeUnexpectedReturns{};
  std::uint64_t consumeResourceMismatches{};
  std::uint64_t consumeSourceMismatches{};
  std::uint64_t consumeSizeMismatches{};
  std::uint64_t consumeCrcMismatches{};
  std::uint64_t consumeMemoryRejected{};
  std::uint64_t consumeInternalErrors{};
  std::uint64_t consumeNotReached{};
  std::uint64_t consumeCrcNanoseconds{};
  std::uint64_t consumeCopyNanoseconds{};
};

PvrDemandFn g_demand{};
std::atomic<bool> g_resetRequested{true};
RuntimeState g_state{};
core::MapPageShadowQueue g_shadowQueue{};
core::ProcessLifetimeWorker g_shadowWorker{};
std::filesystem::path g_shadowResourceDirectory{};
bool g_shadowEnabled{};
bool g_consumeEnabled{};
core::MapPageConsumeGate g_consumeGate{};

std::string_view area_name() noexcept;

void log_shadow_summary(std::string_view reason) noexcept {
  if (!g_shadowEnabled) return;
  const auto stats = g_shadowQueue.snapshot();
  if (stats.submitted == 0 && stats.started == 0 && stats.unplannedDemands == 0) return;
  try {
    LOG_INFO(
        "Map page shadow summary: area={}, reason={}, generation={}, submitted={}, "
        "coalesced={}, rejected={}, started={}, prepared={}, missing={}, ioFailures={}, "
        "invalid={}, discarded={}, readyBeforeDemand={}, notReadyBeforeDemand={}, "
        "unplannedDemands={}, compressedMiB={:.2f}, decodedMiB={:.2f}, totalPrepareMs={:.2f}, "
        "maximumPrepareMs={:.2f}, totalQueueMs={:.2f}, maximumQueueMs={:.2f}, "
        "nativeFallbackWaits={}, totalFallbackWaitMs={:.2f}, maximumFallbackWaitMs={:.2f}, "
        "cancelledPending={}, cancelledCompleted={}, justInTimeSubmissions={}, "
        "idleWaitFrames={}, wideViewStops={}, "
        "pending={}, inFlight={}, fallbackWaiters={}, completed={}, completedMiB={:.2f}, "
        "peakPending={}, peakCompleted={}, "
        "peakCompletedMiB={:.2f}, consumeClaims={}, claimLimit={}, consumed={}, "
        "originalFallbacks={}, "
        "unexpectedReturn={}, resourceMismatch={}, sourceMismatch={}, sizeMismatch={}, "
        "crcMismatch={}, memoryRejected={}, internalError={}, uncompressNotReached={}, "
        "crcMs={:.2f}, copyMs={:.2f}; mode={}",
        area_name(), reason, stats.generation, stats.submitted, stats.coalesced,
        stats.queueRejected, stats.started, stats.prepared, stats.missing,
        stats.ioFailures, stats.invalid, stats.discarded, stats.readyBeforeDemand,
        stats.notReadyBeforeDemand, stats.unplannedDemands,
        static_cast<double>(stats.compressedBytes) / (1024.0 * 1024.0),
        static_cast<double>(stats.decodedBytes) / (1024.0 * 1024.0),
        static_cast<double>(stats.prepareNanoseconds) / 1'000'000.0,
        static_cast<double>(stats.maximumPrepareNanoseconds) / 1'000'000.0,
        static_cast<double>(stats.queueNanoseconds) / 1'000'000.0,
        static_cast<double>(stats.maximumQueueNanoseconds) / 1'000'000.0,
        stats.nativeFallbackWaits,
        static_cast<double>(stats.nativeFallbackWaitNanoseconds) / 1'000'000.0,
        static_cast<double>(stats.maximumNativeFallbackWaitNanoseconds) / 1'000'000.0,
        stats.cancelledPendingPages, stats.cancelledCompletedPages,
        g_state.shadowJustInTimeSubmissions, g_state.shadowIdleWaitFrames,
        g_state.shadowWideViewStops,
        stats.pendingPages, stats.inFlightPages, stats.nativeFallbackWaiters,
        stats.completedPages,
        static_cast<double>(stats.completedBytes) / (1024.0 * 1024.0),
        stats.peakPendingPages, stats.peakCompletedPages,
        static_cast<double>(stats.peakCompletedBytes) / (1024.0 * 1024.0),
        g_state.consumeClaims, core::kMapPageConsumeMaximumClaimsPerGeneration,
        g_state.consumeConsumed, g_state.consumeFallbacks,
        g_state.consumeUnexpectedReturns, g_state.consumeResourceMismatches,
        g_state.consumeSourceMismatches, g_state.consumeSizeMismatches,
        g_state.consumeCrcMismatches, g_state.consumeMemoryRejected,
        g_state.consumeInternalErrors, g_state.consumeNotReached,
        static_cast<double>(g_state.consumeCrcNanoseconds) / 1'000'000.0,
        static_cast<double>(g_state.consumeCopyNanoseconds) / 1'000'000.0,
        g_consumeEnabled ? "bounded-diagnostic-consume" : "shadow-observation-only");
  } catch (...) {
  }
}

void maybe_log_completed_shadow_summary(std::string_view reason) noexcept {
  if (g_state.shadowDemandSummaryLogged) return;

  // In single-slot consume mode, each completed claim is followed by the
  // submission of the next candidate. A momentarily empty queue therefore
  // does not mean the diagnostic is complete. Wait for the four-claim gate or
  // for the native prewarm plan to finish before publishing its summary.
  if (g_consumeEnabled && g_state.state == PlanState::Running &&
      !g_consumeGate.exhausted(g_state.shadowGeneration)) {
    return;
  }

  const auto stats = g_shadowQueue.snapshot();
  if (stats.submitted == 0 ||
      stats.readyBeforeDemand + stats.notReadyBeforeDemand < stats.submitted) {
    return;
  }
  g_state.shadowDemandSummaryLogged = true;
  log_shadow_summary(reason);
}

unsigned __stdcall shadow_worker_entry(void*) noexcept {
  try {
    core::ShadowPageJob job;
    while (g_shadowQueue.wait_take(job)) {
      core::ShadowPreparedResult result;
      result.identity = job.identity;
      result.page = core::prepare_pvrz_file(job.path);
      (void)g_shadowQueue.publish(std::move(result));
    }
  } catch (...) {
  }
  return 0;
}

void stop_shadow_worker() noexcept {
  g_consumeEnabled = false;
  g_shadowEnabled = false;
  g_shadowQueue.request_stop();
  const auto join = g_shadowWorker.join();
  if (join == core::ProcessLifetimeWorker::JoinResult::SelfJoinRejected) {
    try {
      LOG_ERROR("Map page shadow shutdown rejected a worker self-join; state retained");
    } catch (...) {
    }
    return;
  }
  if (join == core::ProcessLifetimeWorker::JoinResult::WaitFailed) {
    try {
      LOG_ERROR("Map page shadow shutdown could not join the worker; state retained");
    } catch (...) {
    }
    return;
  }
  g_shadowResourceDirectory.clear();
  (void)g_shadowWorker.release_module_reference();
}

core::ShadowPageIdentity shadow_identity(const PageCandidate& candidate) {
  return {
      .generation = g_state.shadowGeneration,
      .areaResref = std::string(area_name()),
      .tilesetResref = std::string(game::resref_view(candidate.tilesetResref)),
      .pageResref = std::string(game::resref_view(candidate.pageResref)),
      .pageNumber = candidate.page,
  };
}

bool submit_shadow_candidate(const PageCandidate& candidate) noexcept {
  try {
    auto identity = shadow_identity(candidate);
    const auto filename = identity.pageResref + ".PVRZ";
    return g_shadowQueue.submit(
        {.identity = std::move(identity),
         .path = g_shadowResourceDirectory / filename});
  } catch (...) {
    return false;
  }
}

void reset_state(std::uint64_t frame) {
  log_shadow_summary("area-generation-reset");
  const auto shadowGeneration =
      g_shadowEnabled ? g_shadowQueue.begin_generation() : std::uint64_t{};
  g_state = {};
  g_state.areaStartFrame = frame;
  g_state.shadowGeneration = shadowGeneration;
  g_consumeGate.reset(shadowGeneration);
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
  plan.shadowGeneration = g_state.shadowGeneration;
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
    const bool initiallyResident = pvr.texture > 0;
    if (initiallyResident) ++plan.initiallyResident;
    plan.candidates.push_back({wrapper, infTileset.tis[0], tile.pvr, seed.tileIndex,
                               seed.page, tisResref, pageResref, initiallyResident});
  }

  g_state = std::move(plan);
  if (g_shadowEnabled && !g_consumeEnabled) {
    for (const auto& candidate : g_state.candidates) {
      // A page already backed by a native texture will not cross the unloaded
      // Demand boundary measured by this probe. Keeping its CPU copy would also
      // consume one of the four completed slots and could starve missing pages.
      if (candidate.initiallyResident) continue;
      (void)submit_shadow_candidate(candidate);
    }
  }
  LOG_INFO(
      "Map page prewarm plan: area={}, tileset={}, discoveredPages={}, plannedPages={}, "
      "cappedPages={}, initiallyResident={}, invalidCandidates={}, pagesPerFrame={}, "
      "budgetMs={:.2f}, delayFrames={}, nativePoolEntries={}, reservedEntries={}, "
      "shadowScheduling={}",
      area_name(), game::resref_view(g_state.tilesetResref), g_state.discoveredPages,
      g_state.candidates.size(), g_state.cappedPages, g_state.initiallyResident,
      g_state.invalidCandidates, ctx.cfg.mapPagePrewarmPagesPerFrame,
      ctx.cfg.mapPagePrewarmBudgetMs, ctx.cfg.mapPagePrewarmDelayFrames,
      kNativePvrPoolEntries, kNativePvrReserveEntries,
      g_consumeEnabled ? "single-slot-just-in-time" : "probe-eager-bounded");
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

bool configure_shadow(bool enabled, bool consumeEnabled,
                      const std::filesystem::path& resourceDirectory) noexcept {
  stop_shadow_worker();
  if (!enabled) return true;
  try {
    std::error_code error;
    const auto status = std::filesystem::symlink_status(resourceDirectory, error);
    if (error || std::filesystem::is_symlink(status) ||
        !std::filesystem::is_directory(status)) {
      LOG_WARN("Map page shadow probe disabled: override resource directory is unavailable");
      return false;
    }
    g_shadowResourceDirectory = std::filesystem::weakly_canonical(resourceDirectory, error);
    if (error || g_shadowResourceDirectory.empty()) {
      LOG_WARN("Map page shadow probe disabled: override resource directory is unresolved");
      g_shadowResourceDirectory.clear();
      return false;
    }
    g_shadowQueue.restart();
    if (!g_shadowWorker.start(&shadow_worker_entry, nullptr, &shadow_worker_entry)) {
      g_shadowQueue.request_stop();
      g_shadowResourceDirectory.clear();
      LOG_WARN("Map page shadow probe disabled: worker or DLL lifetime guard could not start");
      return false;
    }
    const bool lowPriority =
        g_shadowWorker.set_priority(THREAD_PRIORITY_BELOW_NORMAL);
    g_shadowEnabled = true;
    g_consumeEnabled = consumeEnabled;
    g_resetRequested.store(true, std::memory_order_release);
    LOG_INFO(
        "Map page shadow probe prepared: resourceDirectory={}, pendingLimit={}, "
        "completedLimit={}, completedMiBLimit={:.2f}, decodedPageMiBLimit={:.2f}; "
        "worker is CPU-only; workerPriority={}, diagnosticConsume={}, consumeLimit={}, "
        "consumeScheduling={} and native Demand owns cache/upload/free",
        g_shadowResourceDirectory.string(), core::kShadowMaximumPendingPages,
        core::kShadowMaximumCompletedPages,
        static_cast<double>(core::kShadowMaximumCompletedBytes) / (1024.0 * 1024.0),
        static_cast<double>(core::kShadowMaximumDecodedBytes) / (1024.0 * 1024.0),
        lowPriority ? "below-normal" : "unchanged",
        g_consumeEnabled, core::kMapPageConsumeMaximumClaimsPerGeneration,
        g_consumeEnabled ? "single-slot-just-in-time" : "probe-eager-bounded");
    return true;
  } catch (...) {
    stop_shadow_worker();
    return false;
  }
}

void request_area_reset() noexcept {
  g_resetRequested.store(true, std::memory_order_release);
}

void notify_wide_view_expansion() noexcept {
  try {
    if (!g_shadowEnabled || g_state.shadowGeneration == 0 ||
        g_state.wideViewObserved) {
      return;
    }
    g_state.wideViewObserved = true;
    ++g_state.shadowWideViewStops;
    const auto cancelled = g_shadowQueue.cancel_remaining();
    LOG_INFO(
        "Map page off-frame preparation stopped at first wide-view expansion: "
        "area={}, generation={}, cancelledPending={}, cancelledCompleted={}, "
        "cancelledCompletedMiB={:.2f}, inFlightRetirementPending={}",
        area_name(), g_state.shadowGeneration, cancelled.pendingPages,
        cancelled.completedPages,
        static_cast<double>(cancelled.completedBytes) / (1024.0 * 1024.0),
        cancelled.inFlight);
  } catch (...) {
  }
}

void on_post_swap(AppContext& ctx) noexcept {
  try {
    const bool shadowActive = g_shadowEnabled;
    if ((!ctx.cfg.enableMapPagePrewarm && !shadowActive) ||
        !ctx.cfg.enablePerformanceLogging || !g_demand) {
      return;
    }

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
    if (!ctx.cfg.enableMapPagePrewarm) return;
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
      const auto candidateIndex = g_state.nextCandidate;
      const auto& candidate = g_state.candidates[candidateIndex];
      game::CResPVR before{};
      if (!validate_candidate(candidate, before)) {
        ++g_state.invalidCandidates;
        abort_plan("native-page-wrapper-identity-changed");
        return;
      }
      if (before.texture > 0) {
        ++g_state.nextCandidate;
        if (g_state.shadowScheduledCandidate == candidateIndex) {
          g_state.shadowScheduledCandidate.reset();
        }
        ++g_state.alreadyResident;
        ++processed;
        continue;
      }

      const bool justInTimeShadow =
          g_shadowEnabled && g_consumeEnabled && !g_state.wideViewObserved &&
          !g_consumeGate.exhausted(g_state.shadowGeneration);
      if (justInTimeShadow) {
        const auto identity = shadow_identity(candidate);
        auto readiness = g_shadowQueue.inspect(identity);
        if (readiness == core::ShadowObservationStatus::Unplanned &&
            g_state.shadowScheduledCandidate != candidateIndex) {
          if (submit_shadow_candidate(candidate)) {
            g_state.shadowScheduledCandidate = candidateIndex;
            ++g_state.shadowJustInTimeSubmissions;
            readiness = g_shadowQueue.inspect(identity);
          }
        }
        if (readiness == core::ShadowObservationStatus::NotReady) {
          ++g_state.shadowIdleWaitFrames;
          break;
        }
      }

      const auto glBefore = core::gl_texture_telemetry_snapshot();
      LARGE_INTEGER demandStart{};
      LARGE_INTEGER demandEnd{};
      QueryPerformanceCounter(&demandStart);
      (void)g_demand(candidate.pvr);
      QueryPerformanceCounter(&demandEnd);
      ++g_state.nextCandidate;
      if (g_state.shadowScheduledCandidate == candidateIndex) {
        g_state.shadowScheduledCandidate.reset();
      }
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
      maybe_log_completed_shadow_summary("all-planned-pages-observed");
    }
  } catch (...) {
    abort_plan("unexpected-exception");
  }
}

std::optional<PvrConsumeAttempt> begin_native_demand(void* pvr) noexcept {
  if (!g_shadowEnabled || !pvr || g_state.shadowGeneration == 0) return std::nullopt;
  try {
    const auto candidate = std::find_if(
        g_state.candidates.begin(), g_state.candidates.end(),
        [&](const PageCandidate& value) { return value.pvr == pvr; });
    if (candidate == g_state.candidates.end()) return std::nullopt;
    auto identity = shadow_identity(*candidate);
    std::optional<PvrConsumeAttempt> attempt;
    core::ShadowObservationStatus queueStatus = core::ShadowObservationStatus::Unplanned;
    std::uint64_t nativeFallbackWaitNanoseconds = 0;
    std::string_view action = "shadow-only";
    if (g_consumeEnabled && !g_consumeGate.exhausted(g_state.shadowGeneration)) {
      auto claim = g_shadowQueue.claim(identity);
      queueStatus = claim.status;
      nativeFallbackWaitNanoseconds = claim.nativeFallbackWaitNanoseconds;
      if (claim.status == core::ShadowObservationStatus::Ready &&
          g_consumeGate.try_claim(g_state.shadowGeneration)) {
        ++g_state.consumeClaims;
        attempt.emplace(PvrConsumeAttempt{
            .resource = pvr,
            .identity = identity,
            .page = std::move(claim.page),
            .claimOrdinal = g_consumeGate.claims(g_state.shadowGeneration),
            .claimLimit = core::kMapPageConsumeMaximumClaimsPerGeneration,
        });
        action = "prepared-claim";
      } else {
        action = claim.status == core::ShadowObservationStatus::NotReady
                     ? "native-fallback-not-ready"
                     : "native-fallback-unplanned";
      }
    } else {
      const auto observation = g_shadowQueue.observe(identity);
      queueStatus = observation.status;
      nativeFallbackWaitNanoseconds = observation.nativeFallbackWaitNanoseconds;
      action = g_consumeEnabled ? "native-fallback-claim-limit" : "shadow-observation";
    }
    if (g_consumeEnabled) {
      const auto queueStatusName = [&]() -> std::string_view {
        switch (queueStatus) {
          case core::ShadowObservationStatus::Ready:
            return "ready";
          case core::ShadowObservationStatus::NotReady:
            return "not-ready";
          case core::ShadowObservationStatus::Unplanned:
            return "unplanned";
        }
        return "unknown";
      }();
      LOG_INFO(
          "Map page off-frame decision: area={}, page={}, generation={}, queueStatus={}, "
          "action={}, claims={}/{}, fallbackWaitMs={:.2f}",
          identity.areaResref, identity.pageResref, identity.generation, queueStatusName,
          action, g_consumeGate.claims(g_state.shadowGeneration),
          core::kMapPageConsumeMaximumClaimsPerGeneration,
          static_cast<double>(nativeFallbackWaitNanoseconds) / 1'000'000.0);
    }
    if (!attempt) maybe_log_completed_shadow_summary("all-planned-pages-observed");
    return attempt;
  } catch (...) {
    return std::nullopt;
  }
}

std::optional<PvrLifecycleSnapshot> lifecycle_snapshot(void* pvr) noexcept {
  if (!g_shadowEnabled || !pvr || g_state.shadowGeneration == 0) return std::nullopt;
  try {
    const auto candidate = std::find_if(
        g_state.candidates.begin(), g_state.candidates.end(),
        [&](const PageCandidate& value) { return value.pvr == pvr; });
    if (candidate == g_state.candidates.end()) return std::nullopt;
    const auto queue = g_shadowQueue.snapshot();
    return PvrLifecycleSnapshot{
        .identity = shadow_identity(*candidate),
        .claims = g_consumeGate.claims(g_state.shadowGeneration),
        .claimLimit = core::kMapPageConsumeMaximumClaimsPerGeneration,
        .pendingPages = queue.pendingPages,
        .inFlightPages = queue.inFlightPages,
        .nativeFallbackWaits = queue.nativeFallbackWaits,
        .completedPages = queue.completedPages,
        .completedBytes = queue.completedBytes,
    };
  } catch (...) {
    return std::nullopt;
  }
}

namespace {
std::string_view consume_outcome_name(PvrConsumeOutcome outcome) noexcept {
  switch (outcome) {
    case PvrConsumeOutcome::Consumed:
      return "consumed";
    case PvrConsumeOutcome::UnexpectedReturnAddress:
      return "unexpected-return-address";
    case PvrConsumeOutcome::ResourceMismatch:
      return "resource-mismatch";
    case PvrConsumeOutcome::SourceMismatch:
      return "source-mismatch";
    case PvrConsumeOutcome::SizeMismatch:
      return "size-mismatch";
    case PvrConsumeOutcome::CrcMismatch:
      return "crc-mismatch";
    case PvrConsumeOutcome::MemoryRejected:
      return "memory-rejected";
    case PvrConsumeOutcome::InternalError:
      return "internal-error";
    case PvrConsumeOutcome::NotReached:
      return "uncompress-not-reached";
  }
  return "unknown";
}
}  // namespace

void record_consume_attempt(const PvrConsumeAttempt& attempt,
                            std::uint64_t demandNanoseconds) noexcept {
  try {
    if (attempt.outcome == PvrConsumeOutcome::Consumed) {
      ++g_state.consumeConsumed;
    } else {
      ++g_state.consumeFallbacks;
      switch (attempt.outcome) {
        case PvrConsumeOutcome::UnexpectedReturnAddress:
          ++g_state.consumeUnexpectedReturns;
          break;
        case PvrConsumeOutcome::ResourceMismatch:
          ++g_state.consumeResourceMismatches;
          break;
        case PvrConsumeOutcome::SourceMismatch:
          ++g_state.consumeSourceMismatches;
          break;
        case PvrConsumeOutcome::SizeMismatch:
          ++g_state.consumeSizeMismatches;
          break;
        case PvrConsumeOutcome::CrcMismatch:
          ++g_state.consumeCrcMismatches;
          break;
        case PvrConsumeOutcome::MemoryRejected:
          ++g_state.consumeMemoryRejected;
          break;
        case PvrConsumeOutcome::InternalError:
          ++g_state.consumeInternalErrors;
          break;
        case PvrConsumeOutcome::NotReached:
          ++g_state.consumeNotReached;
          break;
        case PvrConsumeOutcome::Consumed:
          break;
      }
    }
    g_state.consumeCrcNanoseconds += attempt.crcNanoseconds;
    g_state.consumeCopyNanoseconds += attempt.copyNanoseconds;
    LOG_INFO(
        "Map page off-frame consume: claim={}/{}, area={}, page={}, generation={}, outcome={}, "
        "compressedMiB={:.2f}, decodedMiB={:.2f}, crcMs={:.2f}, copyMs={:.2f}, "
        "nativeDemandMs={:.2f}; native cache/upload/free path retained",
        attempt.claimOrdinal, attempt.claimLimit, attempt.identity.areaResref,
        attempt.identity.pageResref,
        attempt.identity.generation, consume_outcome_name(attempt.outcome),
        static_cast<double>(attempt.page.compressedBytes) / (1024.0 * 1024.0),
        static_cast<double>(attempt.page.decodedBytes) / (1024.0 * 1024.0),
        static_cast<double>(attempt.crcNanoseconds) / 1'000'000.0,
        static_cast<double>(attempt.copyNanoseconds) / 1'000'000.0,
        static_cast<double>(demandNanoseconds) / 1'000'000.0);
    maybe_log_completed_shadow_summary("all-planned-pages-observed");
  } catch (...) {
  }
}

void shutdown() noexcept {
  log_shadow_summary("shutdown");
  stop_shadow_worker();
  g_demand = nullptr;
  g_resetRequested.store(true, std::memory_order_release);
  g_state = {};
}
}  // namespace iee::map_page_prewarm
