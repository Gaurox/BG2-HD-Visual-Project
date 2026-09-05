#include "cache_budget_simulator.h"

#include <algorithm>
#include <limits>

namespace iee::core {
namespace {

void saturating_add(std::uint64_t& target, std::uint64_t value) noexcept {
  const auto maximum = (std::numeric_limits<std::uint64_t>::max)();
  target = value > maximum - target ? maximum : target + value;
}

}  // namespace

void ByteLruCacheSimulator::reset(std::size_t frameCapacity, std::uint64_t budgetBytes,
                                  std::size_t entryLimit) {
  entries_.assign(frameCapacity, {});
  stats_ = {
      .budgetBytes = budgetBytes,
      .entryLimit = static_cast<std::uint64_t>(entryLimit),
  };
  useCounter_ = 0;
}

bool ByteLruCacheSimulator::access(std::size_t frameIndex,
                                   std::uint64_t frameBytes) noexcept {
  saturating_add(stats_.requests, 1);
  if (frameIndex >= entries_.size() || frameBytes == 0) {
    saturating_add(stats_.misses, 1);
    saturating_add(stats_.uncacheableRequests, 1);
    return false;
  }

  auto& requested = entries_[frameIndex];
  if (requested.lastUse != 0) {
    saturating_add(stats_.hits, 1);
    requested.lastUse = ++useCounter_;
    return true;
  }

  saturating_add(stats_.misses, 1);
  if (stats_.entryLimit == 0 || frameBytes > stats_.budgetBytes) {
    saturating_add(stats_.uncacheableRequests, 1);
    return false;
  }

  while (stats_.residentEntries >= stats_.entryLimit ||
         stats_.residentBytes > stats_.budgetBytes - frameBytes) {
    auto victim = entries_.end();
    for (auto candidate = entries_.begin(); candidate != entries_.end(); ++candidate) {
      if (candidate->lastUse == 0) continue;
      if (victim == entries_.end() || candidate->lastUse < victim->lastUse) {
        victim = candidate;
      }
    }
    if (victim == entries_.end() || stats_.residentEntries == 0 ||
        stats_.residentBytes < victim->bytes) {
      saturating_add(stats_.uncacheableRequests, 1);
      return false;
    }
    --stats_.residentEntries;
    stats_.residentBytes -= victim->bytes;
    *victim = {};
    saturating_add(stats_.evictions, 1);
  }

  requested = {.lastUse = ++useCounter_, .bytes = frameBytes};
  ++stats_.residentEntries;
  stats_.residentBytes += frameBytes;
  stats_.peakResidentBytes =
      (std::max)(stats_.peakResidentBytes, stats_.residentBytes);
  return false;
}

void ByteLruCacheSimulator::clear_residency() noexcept {
  std::fill(entries_.begin(), entries_.end(), Entry{});
  stats_.residentEntries = 0;
  stats_.residentBytes = 0;
  useCounter_ = 0;
}

void HierarchicalCacheBudgetSimulator::reset(std::size_t frameCapacity,
                                             std::uint64_t cpuBudgetBytes,
                                             std::uint64_t gpuBudgetBytes,
                                             std::size_t gpuEntryLimit) {
  cpu_.reset(frameCapacity, cpuBudgetBytes, frameCapacity);
  gpu_.reset(frameCapacity, gpuBudgetBytes, gpuEntryLimit);
  requestedFrames_.assign(frameCapacity, 0);
  requests_ = 0;
  distinctFrames_ = 0;
  predictedFrameReadBytes_ = 0;
  predictedUploadBytes_ = 0;
}

void HierarchicalCacheBudgetSimulator::observe(std::size_t frameIndex,
                                               std::uint64_t frameBytes) noexcept {
  saturating_add(requests_, 1);
  if (frameIndex < requestedFrames_.size() && requestedFrames_[frameIndex] == 0) {
    requestedFrames_[frameIndex] = 1;
    saturating_add(distinctFrames_, 1);
  }

  if (gpu_.access(frameIndex, frameBytes)) return;
  saturating_add(predictedUploadBytes_, frameBytes);
  if (!cpu_.access(frameIndex, frameBytes)) {
    saturating_add(predictedFrameReadBytes_, frameBytes);
  }
}

void HierarchicalCacheBudgetSimulator::clear_gpu_residency() noexcept {
  gpu_.clear_residency();
}

HierarchicalCacheBudgetSimulationStats HierarchicalCacheBudgetSimulator::snapshot()
    const noexcept {
  return {
      .requests = requests_,
      .distinctFrames = distinctFrames_,
      .predictedFrameReadBytes = predictedFrameReadBytes_,
      .predictedUploadBytes = predictedUploadBytes_,
      .cpu = cpu_.stats(),
      .gpu = gpu_.stats(),
  };
}

}  // namespace iee::core
