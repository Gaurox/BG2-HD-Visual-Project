#include "map_page_preload.h"
#include <windows.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <fstream>

#include "app_context.h"
#include "frame_hook.h"
#include "map_page_prepare.h"
#include "iee/core/logger.h"
#include "iee/core/map_page_preload_policy.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/opengl_types.h"
#include "iee/game/runtime_types_x64.h"
#include "iee/game/tis_runtime.h"
#include "iee/game/wed_runtime.h"

namespace iee::map_page_preload {
namespace {
using Clock = std::chrono::steady_clock;
struct Runtime {
  std::vector<core::MapPageBinding> bindings;
  DemandPrepared demand{};
  core::MapPagePreloadPolicy policy;
  std::uint64_t generation{}, attempts{}, submitted{}, budgetSkips{}, notReady{}, unresolved{}, reportFrame{};
  const game::CGameArea* area{};
  HGLRC context{};
  double intervalMs{-1}, totalMs{}, maximumMs{};
  std::uint64_t lastPresented{~std::uint64_t{0}};
  std::array<bool, core::kPreparePageLimit> done{};
  bool completeLogged{};
};
Runtime& runtime() { static auto* r = new Runtime; return *r; }
double elapsed(Clock::time_point start) {
  return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}
void summary(Runtime& r, const char* reason) {
  LOG_INFO("Map page B1.3: generation={}, reason={}, attempts={}, submitted={}, "
           "notReady={}, unresolved={}, budgetSkips={}, totalMs={:.3f}, maximumMs={:.3f}, "
           "estimateMs={:.3f}, perFrameSoftBudgetMs=8, cpuBudgetMiB=128",
           r.generation, reason, r.attempts, r.submitted, r.notReady, r.unresolved, r.budgetSkips,
           r.totalMs, r.maximumMs, r.policy.estimate_ms());
}

void* resolve_page(const AppContext& ctx, const core::MapPageBinding& binding,
                   game::CResPVR& pvr) {
  const auto* area = ctx.activeArea.load(std::memory_order_acquire);
  const auto wed = ctx.wed.load(std::memory_order_acquire);
  if (!area || !wed || wed->areaResrefView() != "AR0900") return nullptr;
  const auto* areaBytes = reinterpret_cast<const std::byte*>(area);
  game::CResWED* liveWed{};
  game::CRes live{};
  game::ResrefBuffer name{};
  if (!core::safe_read(areaBytes + offsetof(game::CGameArea, m_pResWED), liveWed) ||
      !liveWed || !core::safe_read(liveWed, live) ||
      !game::read_runtime_resref(live.resref, name) || game::resref_view(name) != "AR0900")
    return nullptr;
  const auto* infinity = areaBytes + offsetof(game::CGameArea, m_cInfinity);
  std::int32_t rain{};
  std::uint16_t type{};
  if (!core::safe_read(infinity + offsetof(game::CInfinity, nCurrentRainLevel), rain) ||
      !core::safe_read(infinity + offsetof(game::CInfinity, m_areaType), type) ||
      ((type & 4) && rain != 0)) return nullptr; // candidate is dry AR0900 only
  std::array<game::CInfTileSet*, 5> sets{};
  if (!core::safe_read(infinity + offsetof(game::CInfinity, pTileSets), sets)) return nullptr;
  for (std::size_t i = 0; i < sets.size() && i < wed->overlays.size(); ++i) {
    if (wed->overlays[i].tilesetResrefView() != binding.tileset || !sets[i]) continue;
    game::CInfTileSet set{};
    game::CResTileSet tis{};
    if (!core::safe_read(sets[i], set) || !set.tis[0] || !set.pResTiles ||
        binding.tileIndex >= set.nTiles || !core::safe_read(set.tis[0], tis) ||
        !tis.baseclass_0.bLoaded || tis.baseclass_0.nSize != sizeof(game::PVRZTileEntry) ||
        !tis.baseclass_0.pData || binding.tileIndex >= tis.baseclass_0.nCount ||
        !game::read_runtime_resref(tis.baseclass_0.resref, name) ||
        game::resref_view(name) != binding.tileset) return nullptr;
    game::TileInfo tileInfo{};
    tileInfo.table = static_cast<const game::PVRZTileEntry*>(tis.baseclass_0.pData);
    tileInfo.tileCount = tis.baseclass_0.nCount;
    game::PVRZTileEntry entry{};
    void* wrapper{};
    game::CResTile tile{};
    if (!game::read_tis_tile_entry(tileInfo, binding.tileIndex, entry) ||
        entry.page != binding.pageNumber ||
        !core::safe_read(set.pResTiles + binding.tileIndex, wrapper) || !wrapper ||
        !core::safe_read(wrapper, tile) || tile.tis != set.tis[0] ||
        !game::matches_tis_tile_identity(tile.tileIndex, binding.tileset,
                                          binding.tileIndex, binding.tileset) ||
        !tile.pvr || !core::safe_read(tile.pvr, pvr) ||
        !game::read_runtime_resref(pvr.baseclass_0.resref, name) ||
        game::resref_view(name) != binding.page ||
        !game::matches_pvrz_page_identity(binding.page, binding.tileset, entry.page))
      return nullptr;
    return tile.pvr;
  }
  return nullptr;
}

// Select unit zero for native upload. Restore its upload-facing GL state before the
// next engine frame; never touch texture contents, filtering, or engine slots.
class UploadState {
 public:
  bool capture() {
    auto& gl = game::gl::get_gl_functions();
    if (!gl.glGetIntegerv || !gl.glActiveTexture || !gl.glBindTexture || !gl.glPixelStorei)
      return false;
    gl.glGetIntegerv(game::gl::PIXEL_UNPACK_BUFFER_BINDING, &unpackBuffer_);
    if (unpackBuffer_ != 0) return false;
    context_ = wglGetCurrentContext();
    gl.glGetIntegerv(game::gl::ACTIVE_TEXTURE, &active_);
    if (active_ < static_cast<int>(game::gl::TEXTURE0)) return false;
    for (std::size_t i = 0; i < pixelKeys_.size(); ++i) gl.glGetIntegerv(pixelKeys_[i], &pixel_[i]);
    gl.glActiveTexture(game::gl::TEXTURE0);
    gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &binding_);
    captured_ = true;
    return true;
  }
  ~UploadState() {
    if (!captured_ || wglGetCurrentContext() != context_) return;
    auto& gl = game::gl::get_gl_functions();
    gl.glActiveTexture(game::gl::TEXTURE0);
    gl.glBindTexture(game::gl::TEXTURE_2D, static_cast<unsigned>(binding_));
    for (std::size_t i = 0; i < pixelKeys_.size(); ++i) gl.glPixelStorei(pixelKeys_[i], pixel_[i]);
    gl.glActiveTexture(static_cast<unsigned>(active_));
  }
 private:
  static constexpr std::array<unsigned, 4> pixelKeys_{game::gl::UNPACK_ALIGNMENT,
      game::gl::UNPACK_ROW_LENGTH, game::gl::UNPACK_SKIP_ROWS, game::gl::UNPACK_SKIP_PIXELS};
  std::array<int, 4> pixel_{};
  int active_{}, binding_{}, unpackBuffer_{};
  HGLRC context_{};
  bool captured_{};
};
}

bool configure(const std::filesystem::path& bindings, DemandPrepared demand) noexcept {
  auto& r = runtime();
  r = {};
  try {
    if (!demand || !map_page_prepare::enabled() || std::filesystem::file_size(bindings) > 32768)
      return false;
    std::ifstream input(bindings);
    if (!core::parse_map_page_bindings(input, r.bindings)) return false;
    r.demand = demand;
    LOG_INFO("Map page B1.3 configured: bindings={}, one ready page/frame, soft budget=8ms, "
             "target=30fps, native cache reserve=32; private preparation unchanged", r.bindings.size());
    return true;
  } catch (...) { r.demand = nullptr; return false; }
}
void on_frame_interval(double milliseconds) noexcept { runtime().intervalMs = milliseconds; }
void on_post_swap(AppContext& ctx, const void* cacheEntries) noexcept {
  auto& r = runtime();
  if (!r.demand || !cacheEntries || !map_page_prepare::enabled() || !frame::boundary_available()) return;
  try {
    const auto context = wglGetCurrentContext();
    const auto* area = ctx.activeArea.load(std::memory_order_acquire);
    const auto generation = map_page_prepare::generation();
    if (!context || !area || !(generation & 1u)) return;
    const auto frameNumber = frame::frame_count();
    if (frameNumber == r.lastPresented) return;
    r.lastPresented = frameNumber;
    if (generation != r.generation || area != r.area || context != r.context) {
      if (r.generation && r.attempts) summary(r, "plan-changed");
      r.generation = generation; r.area = area; r.context = context;
      r.policy = {}; r.done.fill(false); r.completeLogged = false;
      r.attempts = r.submitted = r.budgetSkips = r.notReady = r.unresolved = 0;
      r.reportFrame = frameNumber;
      r.totalMs = r.maximumMs = 0;
      summary(r, "plan-start");
    }
    if (r.policy.stopped() || r.completeLogged) return;
    if (frameNumber - r.reportFrame >= 120) {
      summary(r, "progress"); r.reportFrame = frameNumber;
    }
    const auto started = Clock::now();
    std::array<std::uintptr_t, 128> before{};
    if (!core::safe_read(cacheEntries, before)) return;
    const auto occupied = static_cast<std::size_t>(std::count_if(before.begin(), before.end(),
                                                               [](auto p) { return p != 0; }));
    if (!r.policy.admit(frameNumber, r.intervalMs, elapsed(started), 52, occupied)) {
      ++r.budgetSkips;
      return;
    }
    for (std::size_t i = 0; i < r.bindings.size(); ++i) {
      if (r.done[i]) continue;
      if (!r.policy.admit(frameNumber, r.intervalMs, elapsed(started), 52, occupied)) {
        ++r.budgetSkips; break;
      }
      // Metadata checks do not consume a slot or cancel a pending worker job.
      game::CResPVR native{};
      auto* resource = resolve_page(ctx, r.bindings[i], native);
      if (!resource) { ++r.unresolved; continue; }
      if (native.texture > 0) { r.done[i] = true; continue; }
      auto claim = map_page_prepare::reserve_ready(r.bindings[i].page);
      if (!claim) { ++r.notReady; continue; }
      if (!claim.current() || ctx.activeArea.load() != area || wglGetCurrentContext() != context ||
          !r.policy.admit(frameNumber, r.intervalMs, elapsed(started), claim.page()->decoded.size(), occupied)) {
        claim.defer(); ++r.budgetSkips; return;
      }
      bool consumed = false;
      const auto callStart = Clock::now();
      {
        UploadState state;
        if (!state.capture()) { claim.defer(); return; }
        consumed = r.demand(resource, claim);
      }
      const auto milliseconds = elapsed(callStart);
      ++r.attempts;
      r.totalMs += milliseconds; r.maximumMs = (std::max)(r.maximumMs, milliseconds);
      std::array<std::uintptr_t, 128> after{};
      game::CResPVR loaded{};
      const bool valid = consumed && claim.current() && wglGetCurrentContext() == context &&
          ctx.activeArea.load() == area && core::safe_read(resource, loaded) && loaded.texture > 0 &&
          core::safe_read(cacheEntries, after) && core::preserves_pvr_cache(before, after);
      r.policy.completed(frameNumber, elapsed(started), valid);
      r.done[i] = true;
      if (valid) ++r.submitted;
      if (r.policy.stopped()) summary(r, valid ? "soft-budget-overrun" : "native-validation-failed");
      break; // one monolithic native upload at most, even if it ran cheaply
    }
    if (std::all_of(r.done.begin(), r.done.begin() + r.bindings.size(), [](bool v) { return v; })) {
      r.completeLogged = true;
      summary(r, "all-bindings-resident-or-processed");
    }
  } catch (...) {
    r.policy.completed(frame::frame_count(), 0, false);
    try { summary(r, "exception"); } catch (...) {}
  }
}
void shutdown() noexcept { runtime().demand = nullptr; }
}
