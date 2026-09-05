#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace iee::core {

// Deterministic byte-LRU model used by diagnostics. It never owns payloads and
// never performs I/O or GPU work; callers provide the exact byte size observed
// for each logical frame.
struct ByteLruSimulationStats {
  std::uint64_t budgetBytes{};
  std::uint64_t entryLimit{};
  std::uint64_t requests{};
  std::uint64_t hits{};
  std::uint64_t misses{};
  std::uint64_t evictions{};
  std::uint64_t uncacheableRequests{};
  std::uint64_t residentEntries{};
  std::uint64_t residentBytes{};
  std::uint64_t peakResidentBytes{};
};

class ByteLruCacheSimulator {
 public:
  void reset(std::size_t frameCapacity, std::uint64_t budgetBytes,
             std::size_t entryLimit);
  [[nodiscard]] bool access(std::size_t frameIndex, std::uint64_t frameBytes) noexcept;
  void clear_residency() noexcept;
  [[nodiscard]] const ByteLruSimulationStats& stats() const noexcept { return stats_; }

 private:
  struct Entry {
    std::uint64_t lastUse{};
    std::uint64_t bytes{};
  };

  std::vector<Entry> entries_;
  ByteLruSimulationStats stats_{};
  std::uint64_t useCounter_{};
};

struct HierarchicalCacheBudgetSimulationStats {
  std::uint64_t requests{};
  std::uint64_t distinctFrames{};
  std::uint64_t predictedFrameReadBytes{};
  std::uint64_t predictedUploadBytes{};
  ByteLruSimulationStats cpu{};
  ByteLruSimulationStats gpu{};
};

// Models the intended lazy hierarchy: a GPU hit needs no CPU payload; a GPU
// miss checks the independent CPU cache, and only a CPU miss predicts a file
// read. Both caches begin empty for each area.
class HierarchicalCacheBudgetSimulator {
 public:
  void reset(std::size_t frameCapacity, std::uint64_t cpuBudgetBytes,
             std::uint64_t gpuBudgetBytes, std::size_t gpuEntryLimit);
  void observe(std::size_t frameIndex, std::uint64_t frameBytes) noexcept;
  void clear_gpu_residency() noexcept;
  [[nodiscard]] HierarchicalCacheBudgetSimulationStats snapshot() const noexcept;

 private:
  ByteLruCacheSimulator cpu_;
  ByteLruCacheSimulator gpu_;
  std::vector<std::uint8_t> requestedFrames_;
  std::uint64_t requests_{};
  std::uint64_t distinctFrames_{};
  std::uint64_t predictedFrameReadBytes_{};
  std::uint64_t predictedUploadBytes_{};
};

}  // namespace iee::core
