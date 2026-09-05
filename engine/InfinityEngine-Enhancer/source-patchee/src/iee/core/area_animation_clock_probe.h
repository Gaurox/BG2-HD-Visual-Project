#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace iee::core {

struct AreaAnimationClockSample {
  std::uintptr_t instance{};
  std::array<char, 8> resref{};
  int sequence{-1};
  int slot{-1};
  std::uint64_t presentationEpoch{};
  std::int64_t clockTicks{};
  // -1 means unavailable; zero and one preserve the raw CTimerWorld::m_active value.
  int worldActive{-1};
};

struct AreaAnimationClockGroupSnapshot {
  std::array<char, 8> resref{};
  int sequence{-1};
  std::uint64_t calls{};
  // Distinct presentation epochs are counted per occurrence, not globally across instances.
  std::uint64_t occurrenceEpochs{};
  std::uint64_t sameEpochCalls{};
  std::uint64_t occurrenceStarts{};
  std::uint64_t completedSlots{};
  std::uint64_t slotEpochsTotal{};
  std::uint32_t slotEpochsMinimum{};
  std::uint32_t slotEpochsMaximum{};
  std::uint64_t validSlotDurations{};
  std::uint64_t slotDurationTicksTotal{};
  std::uint64_t slotDurationTicksMinimum{};
  std::uint64_t slotDurationTicksMaximum{};
  std::uint64_t stalledSlots{};
  std::uint64_t longGaps{};
  std::uint64_t sequentialTransitions{};
  std::uint64_t skippedForwardTransitions{};
  std::uint64_t wraps{};
  std::uint64_t backwardTransitions{};
  std::uint64_t sequenceChanges{};
  std::uint64_t nonMonotonicClockSamples{};
  std::uint64_t worldActiveCalls{};
  std::uint64_t worldInactiveCalls{};
  std::uint64_t worldActiveUnknownCalls{};
  std::uint64_t worldActiveTransitions{};
};

struct AreaAnimationClockReport {
  static constexpr std::size_t kMaximumGroups = 256;

  std::uint64_t areaGeneration{};
  std::int64_t ticksPerSecond{};
  std::array<AreaAnimationClockGroupSnapshot, kMaximumGroups> groups{};
  std::size_t groupCount{};
  std::uint64_t droppedOccurrences{};
  std::uint64_t droppedGroups{};
  std::uint64_t invalidSamples{};
};

// Fixed-capacity, allocation-free accumulator for the RenderBam hot path.
// The owning runtime keeps it on the render thread and only requests an area
// generation change atomically from LoadArea.
class AreaAnimationClockProbe {
 public:
  static constexpr std::size_t kMaximumOccurrences = 1024;
  static constexpr std::size_t kMaximumGroups = AreaAnimationClockReport::kMaximumGroups;

  explicit AreaAnimationClockProbe(std::int64_t ticksPerSecond = 0) noexcept;

  void set_ticks_per_second(std::int64_t ticksPerSecond) noexcept;
  void begin_area(std::uint64_t generation) noexcept;
  void observe(const AreaAnimationClockSample& sample) noexcept;
 [[nodiscard]] AreaAnimationClockReport take_report() noexcept;

 private:
  struct GroupAccumulator {
    bool occupied{};
    AreaAnimationClockGroupSnapshot stats{};
  };

  struct OccurrenceState {
    bool occupied{};
    std::uintptr_t instance{};
    std::array<char, 8> resref{};
    int sequence{-1};
    int slot{-1};
    std::size_t groupIndex{std::numeric_limits<std::size_t>::max()};
    std::uint64_t lastEpoch{};
    std::int64_t slotStartTicks{};
    std::int64_t lastSeenTicks{};
    std::uint32_t slotEpochs{};
    int lastWorldActive{-1};
  };

  [[nodiscard]] std::size_t find_or_create_group(const std::array<char, 8>& resref,
                                                 int sequence) noexcept;
  [[nodiscard]] std::size_t find_or_create_occurrence(
      const AreaAnimationClockSample& sample, std::size_t groupIndex, bool& created) noexcept;
  void finalize_slot(OccurrenceState& occurrence, GroupAccumulator& group,
                     std::int64_t nowTicks) noexcept;

  std::int64_t ticksPerSecond_{};
  std::int64_t stallThresholdTicks_{};
  std::uint64_t areaGeneration_{};
  std::array<GroupAccumulator, kMaximumGroups> groups_{};
  std::array<OccurrenceState, kMaximumOccurrences> occurrences_{};
  std::uint64_t droppedOccurrences_{};
  std::uint64_t droppedGroups_{};
  std::uint64_t invalidSamples_{};
};

}  // namespace iee::core
