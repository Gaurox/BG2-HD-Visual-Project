#include "map_page_prepare.h"

#include <windows.h>
#include <array>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <fstream>
#include <mutex>
#include <sstream>
#include <thread>

#include "app_context.h"
#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/core/process_lifetime_worker.h"
#include "iee/game/runtime_types_x64.h"
#include "iee/game/wed_runtime.h"

namespace iee::map_page_prepare {
namespace {
// Lifetime state intentionally survives process teardown, like the worker's
// module reference. Explicit shutdown joins first. No destructor races DllMain.
struct Runtime {
  core::MapPagePrepareQueue queue;
  core::ProcessLifetimeWorker worker;
  std::atomic<bool> enabled{false}, stop{false};
  std::mutex waitMutex;
  std::condition_variable wake;
  std::vector<std::string> overlays;
  std::atomic<std::uint64_t> consumed{0}, rejected{0}, crcNs{0}, copyNs{0};
  std::uint64_t scannedGeneration{}; // render thread only
};
Runtime& runtime() { static auto* value = new Runtime; return *value; }

bool valid_name(std::string_view name) {
  if (name.empty() || name.size() > 8) return false;
  for (char c : name)
    if (!((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_')) return false;
  return true;
}

core::PvrzPreparedPage load_private(const core::PrivatePageEntry& e) {
  const auto started = std::chrono::steady_clock::now();
  core::PvrzPreparedPage result;
  // Do not follow a reparse point or accept a hardlink to native resources.
  const auto handle = CreateFileW(e.path.c_str(), GENERIC_READ, FILE_SHARE_READ,
      nullptr, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_SEQUENTIAL_SCAN, nullptr);
  if (handle == INVALID_HANDLE_VALUE) return result;
  struct Close {
    HANDLE value;
    ~Close() { if (value != INVALID_HANDLE_VALUE) CloseHandle(value); }
  } close{handle};
  BY_HANDLE_FILE_INFORMATION info{};
  if (!GetFileInformationByHandle(handle, &info) || info.nNumberOfLinks != 1 ||
      (info.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY)) ||
      info.nFileSizeHigh || info.nFileSizeLow != e.compressedBytes) return result;
  std::vector<std::byte> bytes(e.compressedBytes);
  DWORD read{};
  if (!ReadFile(handle, bytes.data(), e.compressedBytes, &read, nullptr) ||
      read != e.compressedBytes) return result;
  CloseHandle(handle);
  close.value = INVALID_HANDLE_VALUE;
  // Private handle cannot collide with override. Decode limits also constrain
  // a replaced/corrupted private file to the queue's admitted allocation.
  result = core::prepare_pvrz_bytes(bytes, {e.compressedBytes, e.decodedBytes, 4096});
  result.prepareNanoseconds = static_cast<std::uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(
          std::chrono::steady_clock::now() - started).count());
  return result;
}

unsigned __stdcall worker_entry(void*) {
  auto& r = runtime();
  auto lastLog = std::chrono::steady_clock::now();
  while (!r.stop.load()) {
    try {
      const bool worked = r.queue.work_one(load_private);
      const auto now = std::chrono::steady_clock::now();
      if (now - lastLog >= std::chrono::seconds(2)) {
        lastLog = now;
        LOG_INFO("Map page B1: generation={}, pages={}, prepared={}, hits={}, misses={}, "
                 "consumed={}, rejected={}, failures={}, reservedBytes={}, peakBytes={}, "
                 "crcMs={:.3f}, copyMs={:.3f}, renderWorkerWaits=0",
                 r.queue.generation(), r.queue.page_count(), r.queue.prepared(),
                 r.queue.hits(), r.queue.misses(), r.consumed.load(), r.rejected.load(),
                 r.queue.failures(), r.queue.reserved_bytes(), r.queue.peak_bytes(),
                 r.crcNs.load() / 1e6, r.copyNs.load() / 1e6);
      }
      if (!worked) {
        std::unique_lock lock(r.waitMutex);
        r.wake.wait_for(lock, std::chrono::milliseconds(5));
      }
    } catch (...) { r.enabled.store(false); r.queue.activate(false); }
  }
  r.queue.activate(false);
  (void)r.queue.work_one(nullptr); // retire unborrowed buffers on this worker
  return 0;
}
}

bool configure(const std::filesystem::path& directory) noexcept {
  auto& r = runtime();
  if (r.worker.active()) return false;
  try {
    // Bound all parsing before allocations. Only an explicit AR0900 candidate
    // is supported; no runtime discovery or writes to installed assets.
    const auto index = directory / "pages.index";
    if (std::filesystem::file_size(index) > 32768) return false;
    std::ifstream file(index);
    std::string magic, keyword, area;
    unsigned count{};
    if (!(file >> magic >> keyword >> area >> count) || magic != "IEE_PRIVATE_PVRZ_V1" ||
        keyword != "AREA" || area != "AR0900" || count == 0 || count > 5 ||
        !(file >> keyword) || keyword != "OVERLAYS") return false;
    std::vector<std::string> overlays(count);
    for (auto& overlay : overlays)
      if (!(file >> overlay) || (overlay != "-" && !valid_name(overlay))) return false;
    if (overlays[0] != "AR0900") return false;
    std::vector<core::PrivatePageEntry> entries;
    while (file >> keyword) {
      core::PrivatePageEntry e;
      if (keyword != "PAGE" || entries.size() >= core::kPreparePageLimit ||
          !(file >> e.resref >> e.compressedBytes >> e.decodedBytes >> e.crc32) ||
          !valid_name(e.resref)) return false;
      e.path = directory / (e.resref + ".b1pvrz");
      entries.push_back(std::move(e));
    }
    if (!file.eof() || !r.queue.configure(std::move(entries))) return false;
    r.overlays = std::move(overlays);
    r.stop.store(false);
    r.scannedGeneration = 0;
    r.consumed.store(0); r.rejected.store(0); r.crcNs.store(0); r.copyNs.store(0);
    if (!r.worker.start(worker_entry, nullptr, worker_entry)) return false;
    (void)r.worker.set_priority(THREAD_PRIORITY_BELOW_NORMAL);
    r.enabled.store(true);
    LOG_INFO("Map page B1 enabled: AR0900, {} pages, CPU budget {} MiB, private cache={}; "
             "native Demand/upload retained; no proactive GPU Demand",
             r.queue.page_count(), core::kPrepareBudgetBytes / (1024 * 1024), directory.string());
    return true;
  } catch (...) { return false; }
}
bool enabled() noexcept { return runtime().enabled.load(std::memory_order_acquire); }
void reset() noexcept {
  auto& r = runtime();
  if (r.enabled.load()) r.queue.activate(false);
}
void observe_area(const AppContext& ctx) noexcept {
  auto& r = runtime();
  if (!r.enabled.load()) return;
  const auto wed = ctx.wed.load(std::memory_order_acquire);
  bool matches = wed && wed->areaResrefView() == "AR0900" &&
                 wed->overlays.size() == r.overlays.size();
  if (matches) {
    for (std::size_t i = 0; i < r.overlays.size(); ++i) {
      const auto& overlay = wed->overlays[i];
      const auto name = overlay.width && overlay.height ? overlay.tilesetResrefView()
                                                        : std::string_view{"-"};
      if (name != r.overlays[i]) { matches = false; break; }
    }
  }
  r.queue.activate(matches);
}
void retire_resident_pages(const void* cacheEntries) noexcept {
  auto& r = runtime();
  if (!r.enabled.load() || !cacheEntries) return;
  const auto generation = r.queue.generation();
  if (!(generation & 1u) || generation == r.scannedGeneration) return;
  std::array<void*, 128> entries{};
  if (!core::safe_read(cacheEntries, entries)) return;
  r.scannedGeneration = generation;
  for (auto* resource : entries) {
    game::CResPVR native{};
    game::ResrefBuffer name{};
    if (resource && core::safe_read(resource, native) && native.texture > 0 &&
        game::read_runtime_resref(native.baseclass_0.resref, name))
      r.queue.retire_resident(game::resref_view(name));
  }
}
core::MapPagePrepareQueue::Claim begin_native_demand(void* resource) noexcept {
  if (!enabled() || !resource) return {};
  game::CResPVR native{};
  game::ResrefBuffer name{};
  if (!core::safe_read(resource, native) || native.texture > 0 ||
      !game::read_runtime_resref(native.baseclass_0.resref, name)) return {};
  return runtime().queue.try_claim(game::resref_view(name));
}
bool current(std::uint64_t generation) noexcept {
  return enabled() && (generation & 1u) && runtime().queue.generation() == generation;
}
core::MapPagePrepareQueue::Claim reserve_ready(std::string_view page) noexcept {
  return enabled() ? runtime().queue.try_reserve_ready(page) : core::MapPagePrepareQueue::Claim{};
}
std::uint64_t generation() noexcept { return runtime().queue.generation(); }
void record(bool consumed, std::uint64_t crcNanoseconds, std::uint64_t copyNanoseconds) noexcept {
  auto& r = runtime();
  (consumed ? r.consumed : r.rejected).fetch_add(1, std::memory_order_relaxed);
  r.crcNs.fetch_add(crcNanoseconds, std::memory_order_relaxed);
  r.copyNs.fetch_add(copyNanoseconds, std::memory_order_relaxed);
}
void shutdown() noexcept {
  auto& r = runtime();
  r.enabled.store(false);
  r.stop.store(true);
  r.queue.activate(false);
  r.wake.notify_all();
  const auto joined = r.worker.join();
  if (joined == core::ProcessLifetimeWorker::JoinResult::Joined ||
      joined == core::ProcessLifetimeWorker::JoinResult::NotStarted)
    (void)r.worker.release_module_reference();
}
} // namespace iee::map_page_prepare
