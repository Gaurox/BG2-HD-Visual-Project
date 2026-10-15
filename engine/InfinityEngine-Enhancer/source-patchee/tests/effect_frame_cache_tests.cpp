#include "iee/core/effect_frame_cache.h"
#include "iee/core/area_animation_timeline.h"

#include <atomic>
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>

using Cache = iee::core::EffectFrameCache;
using namespace std::chrono_literals;
namespace {
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
template<class F> void eventually(F predicate, const char* message) {
  const auto end = std::chrono::steady_clock::now() + 3s;
  while (!predicate()) {
    require(std::chrono::steady_clock::now() < end, message);
    std::this_thread::sleep_for(1ms);
  }
}
struct Gate {
  std::mutex mutex;
  std::condition_variable changed;
  bool open{};
  void wait() { std::unique_lock lock(mutex); changed.wait(lock, [&] { return open; }); }
  void release() { std::lock_guard lock(mutex); open = true; changed.notify_all(); }
  ~Gate() { release(); }
};
Cache::Limits limits() { return {.bytes = 256, .inFlightBytes = 128, .headBytes = 64,
                                  .queued = 32, .owners = 16}; }
void sharing_and_budget() {
  Cache cache;
  std::atomic<int> calls{};
  const auto mainThread = std::this_thread::get_id();
  require(cache.start(std::vector<std::uint64_t>(2000, 64), limits(),
      [&](Cache::Id id, std::span<std::byte> out) {
        require(std::this_thread::get_id() != mainThread, "loader ran on consumer thread");
        ++calls; std::fill(out.begin(), out.end(), static_cast<std::byte>(id % 251)); return true;
      }), "cache did not start");
  const std::array<Cache::Id, 2> first{0, 1};
  require(cache.set_intent(1, first) && cache.set_intent(2, first), "shared window rejected");
  eventually([&] { return cache.state(0) == Cache::State::Ready &&
                          cache.state(1) == Cache::State::Ready; }, "shared window not ready");
  require(calls == 2 && cache.stats().pinnedBytes == 128, "shared pixels were duplicated");
  auto lease = cache.acquire(0);
  cache.remove_intent(1); cache.remove_intent(2);
  for (Cache::Id id = 2; id < 24; ++id) {
    cache.request(id);
    eventually([&] { return cache.state(id) == Cache::State::Ready; }, "eviction did not make progress");
    require(cache.stats().committedBytes <= 256 && cache.stats().peakBytes <= 256,
            "ready/in-flight/leased bytes escaped the cap");
  }
  require(lease && (*lease)[0] == std::byte{0}, "upload lease was invalidated by eviction");
  require(cache.stats().evictions > 0 && calls < 30, "inactive library was read");
  const std::array<Cache::Id, 4> full{30, 31, 32, 33};
  require(cache.set_intent(3, full), "full byte window rejected");
  const std::array<Cache::Id, 1> extra{34};
  require(!cache.set_intent(4, extra) && cache.stats().owners == 1,
          "over-budget intent was partially installed");
  cache.remove_intent(3); lease.reset(); cache.stop();
}
void stale_and_shutdown() {
  // Destruction order guarantees release even if an assertion throws.
  Gate gate; Cache cache;
  struct ReleaseOnExit { Gate& gate; ~ReleaseOnExit() { gate.release(); } } unblock{gate};
  std::atomic<int> calls{};
  require(cache.start({64, 64}, limits(), [&](Cache::Id, std::span<std::byte> out) {
    const int call = ++calls;
    if (call == 1) gate.wait();
    std::fill(out.begin(), out.end(), static_cast<std::byte>(call)); return true;
  }), "stale cache start");
  const std::array<Cache::Id, 1> frame{0};
  require(cache.set_intent(11, frame), "first occurrence");
  eventually([&] { return calls == 1; }, "reader did not enter");
  cache.begin_generation();
  require(cache.set_intent(12, frame), "replacement occurrence");
  require(!cache.acquire(0), "unpublished pixels exposed");
  gate.release();
  eventually([&] { return cache.state(0) == Cache::State::Ready; }, "stale reload did not finish");
  auto lease = cache.acquire(0);
  require(lease && (*lease)[0] == std::byte{2} && calls == 2 && cache.stats().cancelled,
          "old generation satisfied a new occurrence");
  cache.stop();
  require((*lease)[0] == std::byte{2}, "shutdown destroyed an outstanding immutable lease");
  require(cache.stats().retiredBytes == 64 && cache.stats().committedBytes == 64,
          "shutdown forgot a retained upload lease");
  const auto loader = [](Cache::Id, std::span<std::byte>) { return true; };
  require(!cache.start({64}, limits(), loader), "replacement ignored old leased bytes");
  lease.reset();
  require(cache.start({64}, limits(), loader), "expired upload lease blocked replacement");
}
void failure_and_heads() {
  Cache cache;
  std::atomic<int> failures{};
  require(cache.start({64, 64, 64, 64}, limits(), [&](Cache::Id id, std::span<std::byte> out) {
    if (id == 1) { ++failures; return false; }
    std::fill(out.begin(), out.end(), std::byte{0x7f}); return true;
  }), "failure cache start");
  const std::array<Cache::Id, 4> heads{0, 0, 2, 3};
  cache.warm(heads);
  require(cache.stats().headBytes == 64 && cache.stats().reads == 1, "warm heads exceeded quota");
  cache.request(1);
  eventually([&] { return cache.state(1) == Cache::State::Failed; }, "disk error not quarantined");
  for (int i = 0; i < 100; ++i) cache.request(1);
  require(failures == 1 && cache.stats().failures == 1, "disk error retried every draw");
  cache.request(3);
  eventually([&] { return cache.state(3) == Cache::State::Ready; }, "one disk failure poisoned library");
}
void occurrence_retirement() {
  iee::core::AreaAnimationTimelineClock clock;
  constexpr std::array<char, 8> ref{'T','E','S','T'};
  clock.begin_area(1);
  for (std::uint64_t serial = 1; serial < 5000; ++serial) {
    const auto result = clock.select({.instance = 0x1234, .resref = ref, .sequence = 0,
      .nativeSlot = 0, .presentationEpoch = serial, .clockTicks = static_cast<std::int64_t>(serial),
      .ticksPerSecond = 1000, .worldActive = 1, .nativeFpsNumerator = 15,
      .nativeFpsDenominator = 1, .targetFpsNumerator = 30, .targetFpsDenominator = 1,
      .timelinePhaseCount = 12, .roundToPresentation = true, .occurrenceSerial = serial});
    require(result.valid && result.occurrenceReset && result.phase == 0,
            "reused pointer or >1024 lifetime occurrences lost interpolation");
    clock.forget(serial);
  }
  require(clock.dropped_occurrences() == 0, "retired occurrence leaked scheduler capacity");
}
void shutdown_in_flight() {
  Gate gate; Cache cache;
  std::jthread stopper;
  struct ReleaseOnExit { Gate& gate; ~ReleaseOnExit() { gate.release(); } } unblock{gate};
  std::atomic<bool> entered{}, stopped{};
  require(cache.start({64}, limits(), [&](Cache::Id, std::span<std::byte> out) {
    entered = true; gate.wait(); std::fill(out.begin(), out.end(), std::byte{3}); return true;
  }), "shutdown cache start");
  cache.request(0);
  eventually([&] { return entered.load(); }, "shutdown reader did not start");
  stopper = std::jthread([&] { cache.stop(); stopped = true; });
  eventually([&] { return cache.stats().generation != 1; }, "stop did not invalidate pending work");
  require(!stopped && !cache.acquire(0), "shutdown exposed a partial buffer or failed to join reader");
  gate.release();
  eventually([&] { return stopped.load(); }, "shutdown deadlocked on cache mutex");
  stopper.join();
}
void culled_window_expires() {
  Cache cache;
  auto options = limits(); options.idleIntentNanoseconds = 20000000;
  require(cache.start({64}, options, [](Cache::Id, std::span<std::byte>) { return true; }),
          "idle cache start");
  const std::array<Cache::Id, 1> frame{0};
  require(cache.set_intent(44, frame), "idle intent start");
  eventually([&] { return cache.stats().expiredIntents == 1; }, "culled owner pins did not expire");
  require(cache.stats().pinnedBytes == 0 && cache.stats().owners == 0,
          "culled window retained ownership");
  require(cache.set_intent(44, frame), "visible owner cannot renew its window");
}
}
int main() {
  try {
    sharing_and_budget(); stale_and_shutdown(); failure_and_heads(); occurrence_retirement(); shutdown_in_flight();
    culled_window_expires();
    std::cout << "bounded cache: sharing, leases, eviction, generations, failures, heads, 4999 lifetimes passed\n";
    return 0;
  } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
