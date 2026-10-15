#pragma once

#include <array>
#include <atomic>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <span>
#include <unordered_map>
#include <vector>

#ifdef _WIN32
#include "iee/core/process_lifetime_worker.h"
#else
#include <thread>
#endif

namespace iee::core {

// One immutable backing, independently of its native consumers and GL copies.
class EffectFrameCache {
 public:
  using Id = std::size_t;
  using Pixels = std::vector<std::byte>;
  using Lease = std::shared_ptr<const Pixels>;
  using Loader = std::function<bool(Id, std::span<std::byte>)>;
  enum class State : std::uint8_t { Absent, Queued, Reading, Ready, Failed };
  struct Limits {
    std::uint64_t bytes{768ull << 20};
    std::uint64_t inFlightBytes{32ull << 20};
    std::uint64_t headBytes{256ull << 20};
    std::size_t queued{4096}, owners{4096};
    std::uint64_t idleIntentNanoseconds{2000000000ull};
  };
  struct Stats {
    std::uint64_t budget{}, committedBytes{}, peakBytes{}, readyBytes{}, inFlightBytes{};
    std::uint64_t pinnedBytes{}, headBytes{}, requests{}, hits{}, misses{}, coalesced{};
    std::uint64_t reads{}, failures{}, cancelled{}, evictions{}, admissionFailures{}, expiredIntents{};
    std::uint64_t readNanoseconds{}, maximumReadNanoseconds{}, queueNanoseconds{};
    std::uint64_t storageOpenNanoseconds{}, storageReadNanoseconds{}, publicationNanoseconds{};
    std::uint64_t deadlineMisses{}, retiredBytes{};
    std::int64_t minimumReadyLeadNanoseconds{INT64_MAX};
    std::size_t queued{}, reading{}, ready{}, owners{};
    std::uint64_t generation{};
  };
  using Reporter = std::function<void(const Stats&)>;

  EffectFrameCache() = default;
  ~EffectFrameCache();
  EffectFrameCache(const EffectFrameCache&) = delete;
  EffectFrameCache& operator=(const EffectFrameCache&) = delete;

  // Lifecycle calls run outside render callbacks. start() never reads pixels.
  bool start(std::vector<std::uint64_t> sizes, Limits limits, Loader loader, Reporter reporter = {});
  void stop() noexcept;
  // Replaces an occurrence's complete window atomically. False means no change;
  // the caller may retry a smaller horizon. Identities are renderer serials.
  bool set_intent(std::uint64_t owner, std::span<const Id> frames,
                  std::uint8_t priority = 1, std::uint64_t phaseNanoseconds = 33333333) noexcept;
  void remove_intent(std::uint64_t owner) noexcept;
  void begin_generation() noexcept;
  void request(Id id, std::uint8_t priority = 0) noexcept;
  Lease acquire(Id id) noexcept;
  void record_storage_timing(std::uint64_t openNanoseconds, std::uint64_t readNanoseconds) noexcept;
  // Bootstrap only: bounded heads are loaded by workers, not by the caller.
  void warm(std::span<const Id> frames);
  [[nodiscard]] Stats stats() const noexcept;
  [[nodiscard]] State state(Id id) const noexcept;

 private:
  struct Entry {
    std::uint64_t bytes{}, version{}, use{}, queuedAt{}, deadline{};
    std::uint32_t pins{};
    std::uint8_t priority{4};
    bool head{};
    State state{State::Absent};
    Lease pixels;
  };
  bool enqueue_locked(Id id, std::uint8_t priority, std::uint64_t deadline = 0);
  void cancel_unneeded_locked(Id id);
  void remove_intent_locked(std::uint64_t owner);
  void expire_intents_locked(std::uint64_t now);
  void run() noexcept;
  void report() noexcept;
#ifdef _WIN32
  static unsigned __stdcall worker_entry(void* self) noexcept;
  std::array<ProcessLifetimeWorker, 2> workers_;
#else
  std::array<std::thread, 2> workers_;
#endif
  mutable std::mutex mutex_;
  std::condition_variable changed_;
  Limits limits_;
  Loader loader_;
  Reporter reporter_;
  std::atomic<std::uint64_t> lastReport_{};
  std::atomic_flag reporting_ = ATOMIC_FLAG_INIT;
  std::vector<Entry> entries_;
  std::vector<Id> pending_, resident_;
  struct RetiredLease { std::weak_ptr<const Pixels> pixels; std::uint64_t bytes{}; };
  std::vector<RetiredLease> retiredLeases_;
  struct Intent { std::vector<Id> frames; std::uint64_t touched{}; };
  std::unordered_map<std::uint64_t, Intent> intents_;
  Stats stats_;
  std::uint64_t clock_{};
  std::uint64_t lastPrune_{};
  bool stopping_{true};
};

}  // namespace iee::core
