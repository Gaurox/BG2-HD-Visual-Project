#include "area_animation_clock_probe.h"

#include <algorithm>
#include <limits>

namespace iee::core {
namespace {
constexpr std::size_t kMissingIndex = std::numeric_limits<std::size_t>::max();

std::uint64_t hash_resref(const std::array<char, 8>& resref) noexcept {
  std::uint64_t hash = 1469598103934665603ull;
  for (const auto value : resref) {
    hash ^= static_cast<unsigned char>(value);
    hash *= 1099511628211ull;
  }
  return hash;
}

std::uint64_t hash_group(const std::array<char, 8>& resref, int sequence) noexcept {
  auto hash = hash_resref(resref);
  hash ^= static_cast<std::uint32_t>(sequence);
  hash *= 1099511628211ull;
  return hash;
}

std::uint64_t hash_occurrence(std::uintptr_t instance,
                              const std::array<char, 8>& resref) noexcept {
  auto hash = hash_resref(resref);
  hash ^= static_cast<std::uint64_t>(instance);
  hash *= 1099511628211ull;
  return hash;
}
}  // namespace

AreaAnimationClockProbe::AreaAnimationClockProbe(std::int64_t ticksPerSecond) noexcept {
  set_ticks_per_second(ticksPerSecond);
}

void AreaAnimationClockProbe::set_ticks_per_second(std::int64_t ticksPerSecond) noexcept {
  ticksPerSecond_ = std::max<std::int64_t>(0, ticksPerSecond);
  // 250 ms separates ordinary 15 Hz slots from pause, culling and hitch gaps.
  stallThresholdTicks_ = ticksPerSecond_ > 0 ? std::max<std::int64_t>(1, ticksPerSecond_ / 4) : 0;
}

void AreaAnimationClockProbe::begin_area(std::uint64_t generation) noexcept {
  areaGeneration_ = generation;
  groups_ = {};
  occurrences_ = {};
  droppedOccurrences_ = 0;
  droppedGroups_ = 0;
  invalidSamples_ = 0;
}

std::size_t AreaAnimationClockProbe::find_or_create_group(
    const std::array<char, 8>& resref, int sequence) noexcept {
  const auto start = static_cast<std::size_t>(hash_group(resref, sequence) % groups_.size());
  for (std::size_t probe = 0; probe < groups_.size(); ++probe) {
    const auto index = (start + probe) % groups_.size();
    auto& group = groups_[index];
    if (!group.occupied) {
      group.occupied = true;
      group.stats.resref = resref;
      group.stats.sequence = sequence;
      return index;
    }
    if (group.stats.sequence == sequence && group.stats.resref == resref) return index;
  }
  ++droppedGroups_;
  return kMissingIndex;
}

std::size_t AreaAnimationClockProbe::find_or_create_occurrence(
    const AreaAnimationClockSample& sample, std::size_t groupIndex, bool& created) noexcept {
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
      occurrence.sequence = sample.sequence;
      occurrence.slot = sample.slot;
      occurrence.groupIndex = groupIndex;
      occurrence.lastEpoch = sample.presentationEpoch;
      occurrence.slotStartTicks = sample.clockTicks;
      occurrence.lastSeenTicks = sample.clockTicks;
      occurrence.slotEpochs = 1;
      occurrence.lastWorldActive = sample.worldActive;
      ++groups_[groupIndex].stats.occurrenceStarts;
      ++groups_[groupIndex].stats.occurrenceEpochs;
      created = true;
      return index;
    }
    if (occurrence.instance == sample.instance && occurrence.resref == sample.resref) return index;
  }
  ++droppedOccurrences_;
  return kMissingIndex;
}

void AreaAnimationClockProbe::finalize_slot(OccurrenceState& occurrence,
                                             GroupAccumulator& group,
                                             std::int64_t nowTicks) noexcept {
  auto& stats = group.stats;
  ++stats.completedSlots;
  stats.slotEpochsTotal += occurrence.slotEpochs;
  if (stats.slotEpochsMinimum == 0 || occurrence.slotEpochs < stats.slotEpochsMinimum) {
    stats.slotEpochsMinimum = occurrence.slotEpochs;
  }
  stats.slotEpochsMaximum = std::max(stats.slotEpochsMaximum, occurrence.slotEpochs);

  if (nowTicks < occurrence.slotStartTicks) {
    ++stats.nonMonotonicClockSamples;
    return;
  }
  const auto duration = static_cast<std::uint64_t>(nowTicks - occurrence.slotStartTicks);
  if (stallThresholdTicks_ > 0 && duration > static_cast<std::uint64_t>(stallThresholdTicks_)) {
    ++stats.stalledSlots;
    return;
  }
  ++stats.validSlotDurations;
  stats.slotDurationTicksTotal += duration;
  if (stats.validSlotDurations == 1 || duration < stats.slotDurationTicksMinimum) {
    stats.slotDurationTicksMinimum = duration;
  }
  stats.slotDurationTicksMaximum = std::max(stats.slotDurationTicksMaximum, duration);
}

void AreaAnimationClockProbe::observe(const AreaAnimationClockSample& sample) noexcept {
  if (ticksPerSecond_ <= 0 || sample.instance == 0 || sample.sequence < 0 || sample.slot < 0 ||
      sample.clockTicks < 0) {
    ++invalidSamples_;
    return;
  }

  const auto sampleGroupIndex = find_or_create_group(sample.resref, sample.sequence);
  if (sampleGroupIndex == kMissingIndex) return;
  auto& sampleStats = groups_[sampleGroupIndex].stats;
  ++sampleStats.calls;
  if (sample.worldActive > 0)
    ++sampleStats.worldActiveCalls;
  else if (sample.worldActive == 0)
    ++sampleStats.worldInactiveCalls;
  else
    ++sampleStats.worldActiveUnknownCalls;

  bool occurrenceCreated = false;
  const auto occurrenceIndex =
      find_or_create_occurrence(sample, sampleGroupIndex, occurrenceCreated);
  if (occurrenceIndex == kMissingIndex) return;
  auto& occurrence = occurrences_[occurrenceIndex];
  if (occurrenceCreated) return;
  if (occurrence.sequence != sample.sequence) {
    auto& oldGroup = groups_[occurrence.groupIndex];
    finalize_slot(occurrence, oldGroup, sample.clockTicks);
    ++oldGroup.stats.sequenceChanges;
    occurrence.sequence = sample.sequence;
    occurrence.slot = sample.slot;
    occurrence.groupIndex = sampleGroupIndex;
    occurrence.lastEpoch = sample.presentationEpoch;
    occurrence.slotStartTicks = sample.clockTicks;
    occurrence.lastSeenTicks = sample.clockTicks;
    occurrence.slotEpochs = 1;
    occurrence.lastWorldActive = sample.worldActive;
    ++sampleStats.occurrenceStarts;
    ++sampleStats.occurrenceEpochs;
    return;
  }

  if (sample.clockTicks < occurrence.lastSeenTicks) {
    ++sampleStats.nonMonotonicClockSamples;
    occurrence.slotStartTicks = sample.clockTicks;
  } else if (stallThresholdTicks_ > 0 &&
             sample.clockTicks - occurrence.lastSeenTicks > stallThresholdTicks_) {
    ++sampleStats.longGaps;
  }

  if (sample.worldActive >= 0 && occurrence.lastWorldActive >= 0 &&
      sample.worldActive != occurrence.lastWorldActive) {
    ++sampleStats.worldActiveTransitions;
  }

  if (sample.slot != occurrence.slot) {
    finalize_slot(occurrence, groups_[occurrence.groupIndex], sample.clockTicks);
    if (sample.slot == occurrence.slot + 1)
      ++sampleStats.sequentialTransitions;
    else if (sample.slot == 0 && occurrence.slot > 0)
      ++sampleStats.wraps;
    else if (sample.slot > occurrence.slot + 1)
      ++sampleStats.skippedForwardTransitions;
    else
      ++sampleStats.backwardTransitions;

    if (sample.presentationEpoch != occurrence.lastEpoch)
      ++sampleStats.occurrenceEpochs;
    else
      ++sampleStats.sameEpochCalls;
    occurrence.slot = sample.slot;
    occurrence.slotStartTicks = sample.clockTicks;
    occurrence.slotEpochs = 1;
  } else if (sample.presentationEpoch != occurrence.lastEpoch) {
    ++sampleStats.occurrenceEpochs;
    ++occurrence.slotEpochs;
  } else {
    ++sampleStats.sameEpochCalls;
  }

  occurrence.groupIndex = sampleGroupIndex;
  occurrence.lastEpoch = sample.presentationEpoch;
  occurrence.lastSeenTicks = sample.clockTicks;
  occurrence.lastWorldActive = sample.worldActive;
}

AreaAnimationClockReport AreaAnimationClockProbe::take_report() noexcept {
  AreaAnimationClockReport report{};
  report.areaGeneration = areaGeneration_;
  report.ticksPerSecond = ticksPerSecond_;
  report.droppedOccurrences = droppedOccurrences_;
  report.droppedGroups = droppedGroups_;
  report.invalidSamples = invalidSamples_;

  for (auto& group : groups_) {
    if (!group.occupied || group.stats.calls == 0) continue;
    if (report.groupCount < report.groups.size()) {
      report.groups[report.groupCount++] = group.stats;
    }
    const auto resref = group.stats.resref;
    const auto sequence = group.stats.sequence;
    group.stats = {};
    group.stats.resref = resref;
    group.stats.sequence = sequence;
  }
  droppedOccurrences_ = 0;
  droppedGroups_ = 0;
  invalidSamples_ = 0;
  return report;
}

}  // namespace iee::core
