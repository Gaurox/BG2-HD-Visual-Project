#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "map_page_shadow.h"

namespace iee::core {
inline constexpr std::size_t kPreparePageLimit = 96;
inline constexpr std::size_t kPrepareBudgetBytes = 128u * 1024u * 1024u;
// Reserve inflate/allocator scratch in addition to compressed + decoded bytes.
inline constexpr std::size_t kPrepareScratchBytes = 1024u * 1024u;

struct PrivatePageEntry {
  std::string resref;
  std::filesystem::path path;
  std::uint32_t compressedBytes{}, decodedBytes{}, crc32{};
};

// Fixed slots: only the worker constructs/destroys payloads. Render borrowers
// return a slot through atomic state changes, including across generation changes.
class MapPagePrepareQueue {
 public:
  using Loader = PvrzPreparedPage (*)(const PrivatePageEntry&);
  class Claim {
   public:
    Claim() noexcept = default;
    Claim(Claim&& other) noexcept;
    Claim& operator=(Claim&& other) noexcept;
    ~Claim();
    Claim(const Claim&) = delete;
    Claim& operator=(const Claim&) = delete;
    explicit operator bool() const noexcept { return owner_ != nullptr; }
    const PvrzPreparedPage* page() const noexcept;
    std::uint64_t generation() const noexcept { return generation_; }
    bool current() const noexcept;
    // Unused speculative reservation: make it available again, without freeing.
    void defer() noexcept;
   private:
    friend class MapPagePrepareQueue;
    Claim(MapPagePrepareQueue* owner, std::size_t slot, std::uint64_t generation) noexcept;
    void release() noexcept;
    MapPagePrepareQueue* owner_{};
    std::size_t slot_{};
    std::uint64_t generation_{};
  };

  // Startup/shutdown only, with worker and all borrowers stopped.
  bool configure(std::vector<PrivatePageEntry> entries,
                 std::size_t budget = kPrepareBudgetBytes);
  // Idempotent activation; reset to false before a fresh load of the same area.
  void activate(bool active) noexcept;
  std::uint64_t generation() const noexcept { return epoch_.load(std::memory_order_acquire); }
  Claim try_claim(std::string_view page) noexcept;
  // Does not retire or count a native miss. For optional preloading only.
  Claim try_reserve_ready(std::string_view page) noexcept;
  void retire_resident(std::string_view page) noexcept;
  // Single worker only. At most one file decoded per invocation. Never on render.
  bool work_one(Loader loader);
  std::size_t reserved_bytes() const noexcept { return reserved_.load(); }
  std::size_t peak_bytes() const noexcept { return peak_.load(); }
  std::uint64_t hits() const noexcept { return hits_.load(); }
  std::uint64_t misses() const noexcept { return misses_.load(); }
  std::uint64_t prepared() const noexcept { return prepared_.load(); }
  std::uint64_t failures() const noexcept { return failures_.load(); }
  std::size_t page_count() const noexcept { return count_; }

 private:
  enum class State : std::uint8_t { Empty, Loading, Ready, Claimed, Retired };
  struct Slot {
    PrivatePageEntry entry;
    std::atomic<State> state{State::Empty};
    std::atomic<std::uint64_t> retiredThrough{0};
    std::uint64_t generation{}; // protected by state ownership
    PvrzPreparedPage page;
    std::size_t reservation{}; // worker only
  };
  void recycle(Slot& slot);
  std::array<Slot, kPreparePageLimit> slots_{};
  std::size_t count_{}, budget_{kPrepareBudgetBytes};
  // Low bit active; monotonic token prevents ABA when the same area reloads.
  std::atomic<std::uint64_t> epoch_{0};
  std::atomic<std::size_t> reserved_{0}, peak_{0};
  std::atomic<std::uint64_t> hits_{0}, misses_{0}, prepared_{0}, failures_{0};
};
} // namespace iee::core
