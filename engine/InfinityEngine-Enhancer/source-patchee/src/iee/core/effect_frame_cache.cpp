#include "effect_frame_cache.h"

#include <algorithm>
#include <chrono>
#include <limits>
#include <utility>

namespace iee::core {
namespace {
std::uint64_t now_ns() noexcept {
  return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::steady_clock::now().time_since_epoch()).count());
}
}

EffectFrameCache::~EffectFrameCache() { stop(); }

bool EffectFrameCache::start(std::vector<std::uint64_t> sizes, Limits limits, Loader loader, Reporter reporter) {
  stop();
#ifdef _WIN32
  for (const auto& worker : workers_) if (worker.active()) return false;
#endif
  if (!loader || !limits.bytes || !limits.inFlightBytes || !limits.queued || !limits.owners ||
      limits.inFlightBytes > limits.bytes || limits.headBytes > limits.bytes ||
      limits.queued > 65536 || limits.owners > 65536 || !limits.idleIntentNanoseconds)
    return false;
  for (auto bytes : sizes)
    if (!bytes || bytes > limits.bytes || bytes > limits.inFlightBytes ||
        bytes > std::numeric_limits<std::size_t>::max()) return false;
  {
    std::lock_guard lock(mutex_);
    std::erase_if(retiredLeases_, [](const auto& e) { return e.pixels.expired(); });
    // Replacement is fail-closed while a caller still owns an old upload lease.
    // A new budget cannot silently forget physical bytes from the old pack.
    if (!retiredLeases_.empty()) return false;
    limits_ = limits;
    entries_.resize(sizes.size());
    for (Id i = 0; i < sizes.size(); ++i) entries_[i].bytes = sizes[i];
    pending_.reserve(limits.queued);
    resident_.reserve(std::min<std::size_t>(sizes.size(), 32768));
    retiredLeases_.reserve(std::min<std::size_t>(sizes.size(), 32768));
    intents_.reserve(limits.owners);
    loader_ = std::move(loader);
    reporter_ = std::move(reporter);
    lastReport_.store(now_ns());
    stats_ = {.budget = limits.bytes};
    stats_.generation = 1;
    lastPrune_ = 0;
    stopping_ = false;
  }
  try {
    for (auto& worker : workers_) {
#ifdef _WIN32
      if (!worker.start(worker_entry, this, reinterpret_cast<const void*>(&worker_entry))) {
        stop(); return false;
      }
      (void)worker.set_priority(THREAD_PRIORITY_BELOW_NORMAL);
#else
      worker = std::thread([this] { run(); });
#endif
    }
  } catch (...) { stop(); return false; }
  return true;
}

void EffectFrameCache::stop() noexcept {
  {
    std::lock_guard lock(mutex_);
    stopping_ = true;
    ++stats_.generation;
    changed_.notify_all();
  }
  for (auto& worker : workers_) {
#ifdef _WIN32
    const auto joined = worker.join(true);
    // Never release storage/module while a worker could still execute it.
    if (joined == ProcessLifetimeWorker::JoinResult::SelfJoinRejected ||
        joined == ProcessLifetimeWorker::JoinResult::WaitFailed) return;
#else
    if (worker.joinable()) worker.join();
#endif
  }
  {
    std::lock_guard lock(mutex_);
    for (const auto id : resident_) {
      const auto& e = entries_[id];
      if (e.pixels.use_count() > 1) retiredLeases_.push_back({e.pixels, e.bytes});
    }
    intents_.clear(); pending_.clear(); resident_.clear(); entries_.clear();
    loader_ = {};
    reporter_ = {};
    stats_ = {};
  }
#ifdef _WIN32
  for (auto& worker : workers_) (void)worker.release_module_reference();
#endif
}

bool EffectFrameCache::enqueue_locked(Id id, std::uint8_t priority, std::uint64_t deadline) {
  if (stopping_ || id >= entries_.size()) return false;
  auto& entry = entries_[id];
  ++stats_.requests;
  entry.use = ++clock_;
  if (!deadline) deadline = now_ns();
  if (entry.state == State::Absent || priority < entry.priority) entry.deadline = deadline;
  else entry.deadline = std::min(entry.deadline, deadline);
  entry.priority = entry.state == State::Absent ? priority : std::min(entry.priority, priority);
  if (entry.state == State::Ready || entry.state == State::Reading ||
      entry.state == State::Queued) { ++stats_.coalesced; return true; }
  if (entry.state == State::Failed) return false;
  if (pending_.size() >= limits_.queued) { ++stats_.admissionFailures; return false; }
  entry.state = State::Queued;
  entry.queuedAt = now_ns();
  pending_.push_back(id);
  changed_.notify_all();
  return true;
}

bool EffectFrameCache::set_intent(std::uint64_t owner, std::span<const Id> frames,
                                std::uint8_t priority, std::uint64_t phaseNanoseconds) noexcept {
  if (!owner || frames.size() > 128) return false;
  try {
    // Allocate the tiny window before taking the worker handoff mutex.
    std::vector<Id> unique(frames.begin(), frames.end());
    std::sort(unique.begin(), unique.end());
    unique.erase(std::unique(unique.begin(), unique.end()), unique.end());
    std::lock_guard lock(mutex_);
    if (stopping_) return false;
    auto existing = intents_.find(owner);
    if (existing == intents_.end() && intents_.size() >= limits_.owners) {
      ++stats_.admissionFailures; return false;
    }
    auto pinned = stats_.pinnedBytes;
    std::size_t newJobs = 0;
    if (existing != intents_.end()) for (Id id : existing->second.frames) {
      if (entries_[id].pins == 1) pinned -= entries_[id].bytes;
    }
    for (Id id : unique) {
      if (id >= entries_.size() || entries_[id].state == State::Failed) return false;
      const bool old = existing != intents_.end() &&
          std::binary_search(existing->second.frames.begin(), existing->second.frames.end(), id);
      const auto otherPins = entries_[id].pins - (old ? 1u : 0u);
      if (!otherPins) {
        if (entries_[id].bytes > limits_.bytes - pinned) {
          ++stats_.admissionFailures; return false;
        }
        pinned += entries_[id].bytes;
      }
      if (entries_[id].state == State::Absent) ++newJobs;
    }
    if (newJobs > limits_.queued - pending_.size()) {
      ++stats_.admissionFailures; return false;
    }
    // Install the replacement before cancellation so shared reading jobs survive.
    if (existing == intents_.end()) existing = intents_.emplace(owner, Intent{}).first;
    auto old = std::move(existing->second.frames);
    existing->second = {std::move(unique), now_ns()};
    for (Id id : existing->second.frames) ++entries_[id].pins;
    for (Id id : old) --entries_[id].pins;
    stats_.pinnedBytes = pinned;
    for (Id id : old) cancel_unneeded_locked(id);
    const auto now = now_ns();
    // Preserve timeline order for deadlines; the ownership set remains sorted.
    for (std::size_t n = 0; n < frames.size(); ++n)
      (void)enqueue_locked(frames[n], priority, now + n * std::min(phaseNanoseconds, 1000000000ull));
    changed_.notify_all();
    return true;
  } catch (...) { return false; }
}

void EffectFrameCache::cancel_unneeded_locked(Id id) {
  auto& e = entries_[id];
  if (e.pins || e.head) return;
  if (e.state == State::Queued) {
    std::erase(pending_, id); e.state = State::Absent; ++stats_.cancelled;
  } else if (e.state == State::Reading) {
    // Its reservation remains charged until this worker acknowledges retirement.
    ++e.version;
  }
}

void EffectFrameCache::remove_intent_locked(std::uint64_t owner) {
  const auto it = intents_.find(owner);
  if (it == intents_.end()) return;
  for (Id id : it->second.frames) {
    auto& e = entries_[id];
    if (--e.pins == 0) stats_.pinnedBytes -= e.bytes;
    cancel_unneeded_locked(id);
  }
  intents_.erase(it);
}

void EffectFrameCache::expire_intents_locked(std::uint64_t now) {
  if (now - lastPrune_ < 100000000ull) return;
  lastPrune_ = now;
  for (auto it = intents_.begin(); it != intents_.end();) {
    if (now - it->second.touched < limits_.idleIntentNanoseconds) { ++it; continue; }
    const auto owner = it->first;
    ++it;
    remove_intent_locked(owner);
    ++stats_.expiredIntents;
  }
}

void EffectFrameCache::remove_intent(std::uint64_t owner) noexcept {
  std::lock_guard lock(mutex_);
  remove_intent_locked(owner);
  changed_.notify_all();
}

void EffectFrameCache::begin_generation() noexcept {
  std::lock_guard lock(mutex_);
  ++stats_.generation;
  while (!intents_.empty()) remove_intent_locked(intents_.begin()->first);
  std::erase_if(pending_, [&](Id id) {
    auto& entry = entries_[id];
    if (entry.head) return false;
    entry.state = State::Absent; ++stats_.cancelled;
    return true;
  });
  changed_.notify_all();
}

void EffectFrameCache::request(Id id, std::uint8_t priority) noexcept {
  try { std::lock_guard lock(mutex_); (void)enqueue_locked(id, priority); } catch (...) {}
}

EffectFrameCache::Lease EffectFrameCache::acquire(Id id) noexcept {
  std::lock_guard lock(mutex_);
  if (stopping_ || id >= entries_.size()) return {};
  auto& e = entries_[id];
  e.use = ++clock_;
  if (e.state == State::Ready) { ++stats_.hits; return e.pixels; }
  ++stats_.misses;
  (void)enqueue_locked(id, 0);
  return {};
}

void EffectFrameCache::record_storage_timing(std::uint64_t openNanoseconds,
                                           std::uint64_t readNanoseconds) noexcept {
  std::lock_guard lock(mutex_);
  stats_.storageOpenNanoseconds += openNanoseconds;
  stats_.storageReadNanoseconds += readNanoseconds;
}

void EffectFrameCache::warm(std::span<const Id> frames) {
  std::unique_lock lock(mutex_);
  for (Id id : frames) {
    if (id >= entries_.size()) continue;
    auto& e = entries_[id];
    if (e.head || e.bytes > limits_.headBytes - stats_.headBytes) continue;
    if (!enqueue_locked(id, 4)) continue;
    e.head = true;
    stats_.headBytes += e.bytes;
  }
  changed_.wait(lock, [&] {
    if (stopping_) return true;
    for (Id id : frames) if (id < entries_.size()) {
      const auto& e = entries_[id];
      if (e.head && (e.state == State::Queued || e.state == State::Reading)) return false;
    }
    return true;
  });
}

EffectFrameCache::Stats EffectFrameCache::stats() const noexcept {
  std::lock_guard lock(mutex_);
  auto result = stats_;
  result.queued = pending_.size(); result.ready = resident_.size(); result.owners = intents_.size();
  result.retiredBytes = result.committedBytes - result.readyBytes - result.inFlightBytes;
  for (const auto& e : retiredLeases_) if (!e.pixels.expired()) {
    result.committedBytes += e.bytes; result.retiredBytes += e.bytes;
  }
  if (result.committedBytes && !result.budget) result.budget = limits_.bytes;
  return result;
}
EffectFrameCache::State EffectFrameCache::state(Id id) const noexcept {
  std::lock_guard lock(mutex_);
  return id < entries_.size() ? entries_[id].state : State::Absent;
}

#ifdef _WIN32
unsigned __stdcall EffectFrameCache::worker_entry(void* self) noexcept {
  static_cast<EffectFrameCache*>(self)->run(); return 0;
}
#endif

void EffectFrameCache::run() noexcept {
  for (;;) {
    report();
    Id id = 0;
    std::uint64_t version = 0, bytes = 0, generation = 0;
    {
      std::unique_lock lock(mutex_);
      for (;;) {
        expire_intents_locked(now_ns());
        if (!changed_.wait_for(lock, std::chrono::seconds(1), [&] { return stopping_ || !pending_.empty(); })) {
          lock.unlock(); report(); lock.lock(); continue;
        }
        if (stopping_) return;
        auto best = std::min_element(pending_.begin(), pending_.end(), [&](Id a, Id b) {
          const auto& x = entries_[a]; const auto& y = entries_[b];
          return x.priority != y.priority ? x.priority < y.priority :
              x.deadline != y.deadline ? x.deadline < y.deadline : x.queuedAt < y.queuedAt;
        });
        id = *best; bytes = entries_[id].bytes;
        if (bytes > limits_.inFlightBytes - stats_.inFlightBytes) {
          changed_.wait(lock); continue;
        }
        if (bytes > limits_.bytes - stats_.committedBytes || resident_.size() >= 32768) {
          auto victim = resident_.end();
          for (auto it = resident_.begin(); it != resident_.end(); ++it) {
            const auto& e = entries_[*it];
            if (e.pins || e.pixels.use_count() != 1) continue;
            if (victim == resident_.end() ||
                (entries_[*victim].head && !e.head) ||
                (entries_[*victim].head == e.head && e.use < entries_[*victim].use)) victim = it;
          }
          if (victim == resident_.end()) {
            // An upload lease can end without taking our mutex. Poll only workers.
            changed_.wait_for(lock, std::chrono::milliseconds(5)); continue;
          }
          auto& e = entries_[*victim];
          const auto retiredBytes = e.bytes;
          auto retired = std::move(e.pixels);
          if (e.head) { stats_.headBytes -= e.bytes; e.head = false; }
          e.state = State::Absent; e.priority = 4;
          resident_.erase(victim);
          stats_.readyBytes -= retiredBytes; ++stats_.evictions;
          lock.unlock(); retired.reset(); lock.lock();
          stats_.committedBytes -= retiredBytes;
          if (stopping_) return;
          continue;
        }
        pending_.erase(best);
        auto& e = entries_[id];
        e.state = State::Reading; version = e.version; generation = stats_.generation;
        stats_.committedBytes += bytes; stats_.inFlightBytes += bytes; ++stats_.reading;
        stats_.peakBytes = std::max(stats_.peakBytes, stats_.committedBytes);
        stats_.queueNanoseconds += now_ns() - e.queuedAt;
        break;
      }
    }
    // No cache lock, native pointers, logging or GL in this section.
    const auto started = now_ns();
    std::shared_ptr<Pixels> pixels;
    bool success = false;
    try {
      pixels = std::make_shared<Pixels>(static_cast<std::size_t>(bytes));
      success = loader_(id, *pixels);
    } catch (...) {}
    const auto loadedAt = now_ns();
    const auto elapsed = loadedAt - started;
    std::unique_lock lock(mutex_);
    auto& e = entries_[id];
    ++stats_.reads; stats_.readNanoseconds += elapsed;
    stats_.maximumReadNanoseconds = std::max(stats_.maximumReadNanoseconds, elapsed);
    const bool stale = stopping_ || version != e.version || (generation != stats_.generation && !e.head);
    if (success && !stale) {
      e.pixels = std::move(pixels); e.state = State::Ready;
      resident_.push_back(id); stats_.readyBytes += bytes;
      if (e.priority <= 1) {
        const auto readyAt = now_ns();
        const auto lead = e.deadline >= readyAt ? static_cast<std::int64_t>(e.deadline - readyAt) :
            -static_cast<std::int64_t>(readyAt - e.deadline);
        stats_.minimumReadyLeadNanoseconds = std::min(stats_.minimumReadyLeadNanoseconds, lead);
        if (lead < 0) ++stats_.deadlineMisses;
      }
    } else {
      e.state = stale ? State::Absent : State::Failed;
      if (e.head) { stats_.headBytes -= e.bytes; e.head = false; }
      if (stale) ++stats_.cancelled; else ++stats_.failures;
      // Do not free a large allocation while a render callback waits for mutex_.
      lock.unlock(); pixels.reset(); lock.lock();
      stats_.committedBytes -= bytes;
    }
    stats_.inFlightBytes -= bytes; --stats_.reading;
    stats_.publicationNanoseconds += now_ns() - loadedAt;
    if (stale && !stopping_ && e.pins) (void)enqueue_locked(id, e.priority);
    changed_.notify_all();
  }
}

void EffectFrameCache::report() noexcept {
  if (!reporter_) return;
  auto before = lastReport_.load();
  const auto now = now_ns();
  if (now - before < 5000000000ull || !lastReport_.compare_exchange_strong(before, now)) return;
  if (reporting_.test_and_set(std::memory_order_acquire)) return;
  try { reporter_(stats()); } catch (...) {}
  reporting_.clear(std::memory_order_release);
}

}  // namespace iee::core
