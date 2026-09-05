#include "area_animation_timeline.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace iee::core {
namespace {
constexpr std::size_t kMissingIndex = std::numeric_limits<std::size_t>::max();

std::uint64_t hash_occurrence(std::uintptr_t instance,
                              const std::array<char, 8>& resref) noexcept {
  std::uint64_t hash = 1469598103934665603ull;
  for (const auto value : resref) {
    hash ^= static_cast<unsigned char>(value);
    hash *= 1099511628211ull;
  }
  hash ^= static_cast<std::uint64_t>(instance);
  hash *= 1099511628211ull;
  return hash;
}

bool valid_rate(std::uint32_t numerator, std::uint32_t denominator) noexcept {
  return numerator != 0 && denominator != 0;
}
}  // namespace

void AreaAnimationTimelineClock::begin_area(std::uint64_t generation) noexcept {
  areaGeneration_ = generation;
  occurrences_ = {};
  droppedOccurrences_ = 0;
}

std::size_t AreaAnimationTimelineClock::find_or_create(
    const AreaAnimationTimelineSample& sample, bool& created) noexcept {
  created = false;
  const auto start = static_cast<std::size_t>(
      hash_occurrence(sample.instance, sample.resref) % occurrences_.size());
  for (std::size_t probe = 0; probe < occurrences_.size(); ++probe) {
    const auto index = (start + probe) % occurrences_.size();
    auto& occurrence = occurrences_[index];
    if (!occurrence.occupied) {
      occurrence.occupied = true;
      occurrence.instance = sample.instance;
      occurrence.resref = sample.resref;
      created = true;
      return index;
    }
    if (occurrence.instance == sample.instance && occurrence.resref == sample.resref) return index;
  }
  ++droppedOccurrences_;
  return kMissingIndex;
}

std::uint32_t AreaAnimationTimelineClock::calculate_phase(
    const AreaAnimationTimelineSample& sample, std::int64_t slotStartTicks,
    std::int64_t effectiveTicks) noexcept {
  const long double nativeRate =
      static_cast<long double>(sample.nativeFpsNumerator) /
      static_cast<long double>(sample.nativeFpsDenominator);
  const long double targetRate =
      static_cast<long double>(sample.targetFpsNumerator) /
      static_cast<long double>(sample.targetFpsDenominator);
  const long double slotDurationTicks =
      static_cast<long double>(sample.ticksPerSecond) / nativeRate;
  long double elapsedTicks =
      static_cast<long double>(std::max<std::int64_t>(0, effectiveTicks - slotStartTicks));
  // A stale same-slot observation after culling or a hitch must hold the last
  // phase owned by that native slot, never spill into the next slot's timeline.
  elapsedTicks = std::min(elapsedTicks, std::max<long double>(0.0L, slotDurationTicks - 1.0L));
  const long double cycleSeconds =
      static_cast<long double>(sample.nativeSlot) / nativeRate +
      elapsedTicks / static_cast<long double>(sample.ticksPerSecond);
  const auto unwrapped = static_cast<std::uint64_t>(std::floor(cycleSeconds * targetRate));
  return static_cast<std::uint32_t>(unwrapped % sample.timelinePhaseCount);
}

AreaAnimationTimelineSelection AreaAnimationTimelineClock::select(
    const AreaAnimationTimelineSample& sample) noexcept {
  if (sample.instance == 0 || sample.sequence < 0 || sample.nativeSlot < 0 ||
      sample.clockTicks < 0 || sample.ticksPerSecond <= 0 || sample.worldActive < 0 ||
      !valid_rate(sample.nativeFpsNumerator, sample.nativeFpsDenominator) ||
      !valid_rate(sample.targetFpsNumerator, sample.targetFpsDenominator) ||
      sample.timelinePhaseCount == 0) {
    return {};
  }

  bool created = false;
  const auto index = find_or_create(sample, created);
  if (index == kMissingIndex) return {};
  auto& occurrence = occurrences_[index];
  const bool reset = created || occurrence.sequence != sample.sequence ||
                     occurrence.nativeSlot != sample.nativeSlot ||
                     sample.clockTicks < occurrence.lastClockTicks;
  if (reset) {
    occurrence.sequence = sample.sequence;
    occurrence.nativeSlot = sample.nativeSlot;
    occurrence.lastEpoch = sample.presentationEpoch;
    occurrence.lastClockTicks = sample.clockTicks;
    occurrence.slotStartTicks = sample.clockTicks;
    occurrence.pauseStartTicks = sample.clockTicks;
    occurrence.paused = sample.worldActive == 0;
    occurrence.lastPhase = calculate_phase(sample, occurrence.slotStartTicks, sample.clockTicks);
    return {.valid = true,
            .phase = occurrence.lastPhase,
            .occurrenceReset = true,
            .paused = occurrence.paused};
  }

  if (sample.presentationEpoch == occurrence.lastEpoch) {
    return {.valid = true,
            .phase = occurrence.lastPhase,
            .occurrenceReset = false,
            .paused = occurrence.paused};
  }

  std::int64_t effectiveTicks = sample.clockTicks;
  if (sample.worldActive == 0) {
    if (!occurrence.paused) {
      occurrence.paused = true;
      occurrence.pauseStartTicks = sample.clockTicks;
    }
    effectiveTicks = occurrence.pauseStartTicks;
  } else if (occurrence.paused) {
    occurrence.slotStartTicks += sample.clockTicks - occurrence.pauseStartTicks;
    occurrence.paused = false;
  }

  occurrence.lastPhase = calculate_phase(sample, occurrence.slotStartTicks, effectiveTicks);
  occurrence.lastEpoch = sample.presentationEpoch;
  occurrence.lastClockTicks = sample.clockTicks;
  return {.valid = true,
          .phase = occurrence.lastPhase,
          .occurrenceReset = false,
          .paused = occurrence.paused};
}

}  // namespace iee::core
