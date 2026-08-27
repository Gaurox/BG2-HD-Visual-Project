#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace iee::core {

struct AreaAnimationTimelineSample {
  std::uintptr_t instance{};
  std::array<char, 8> resref{};
  int sequence{-1};
  int nativeSlot{-1};
  std::uint64_t presentationEpoch{};
  std::int64_t clockTicks{};
  std::int64_t ticksPerSecond{};
  int worldActive{-1};
  std::uint32_t nativeFpsNumerator{};
  std::uint32_t nativeFpsDenominator{};
  std::uint32_t targetFpsNumerator{};
  std::uint32_t targetFpsDenominator{};
  std::uint32_t timelinePhaseCount{};
};

struct AreaAnimationTimelineSelection {
  bool valid{};
  std::uint32_t phase{};
  bool occurrenceReset{};
  bool paused{};
};

// Render-thread-owned, allocation-free clock for registry v2 TimedTimeline
// resources. Native slot changes are authoritative phase anchors; QPC only
// selects the intermediate phase inside the currently observed slot.
class AreaAnimationTimelineClock {
 public:
  static constexpr std::size_t kMaximumOccurrences = 1024;

  void begin_area(std::uint64_t generation) noexcept;
  [[nodiscard]] AreaAnimationTimelineSelection select(
      const AreaAnimationTimelineSample& sample) noexcept;
  [[nodiscard]] std::uint64_t area_generation() const noexcept { return areaGeneration_; }
  [[nodiscard]] std::uint64_t dropped_occurrences() const noexcept {
    return droppedOccurrences_;
  }

 private:
  struct OccurrenceState {
    bool occupied{};
    std::uintptr_t instance{};
    std::array<char, 8> resref{};
    int sequence{-1};
    int nativeSlot{-1};
    std::uint64_t lastEpoch{};
    std::int64_t lastClockTicks{};
    std::int64_t slotStartTicks{};
    std::int64_t pauseStartTicks{};
    std::uint32_t lastPhase{};
    bool paused{};
  };

  [[nodiscard]] std::size_t find_or_create(const AreaAnimationTimelineSample& sample,
                                           bool& created) noexcept;
  [[nodiscard]] static std::uint32_t calculate_phase(
      const AreaAnimationTimelineSample& sample, std::int64_t slotStartTicks,
      std::int64_t effectiveTicks) noexcept;

  std::uint64_t areaGeneration_{};
  std::array<OccurrenceState, kMaximumOccurrences> occurrences_{};
  std::uint64_t droppedOccurrences_{};
};

}  // namespace iee::core
