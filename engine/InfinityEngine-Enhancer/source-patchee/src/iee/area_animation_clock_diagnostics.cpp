#include "area_animation_clock_diagnostics.h"

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <string>

#include "iee/core/area_animation_clock_probe.h"
#include "iee/core/logger.h"
#include "iee/frame_hook.h"

namespace iee::area_animation_clock {
namespace {
constexpr std::int64_t kReportSeconds = 5;

std::atomic<bool> g_enabled{false};
std::atomic<std::uint64_t> g_requestedGeneration{1};
std::uint64_t g_activeGeneration{};
std::int64_t g_lastReportTicks{};
core::AreaAnimationClockProbe g_probe;

std::string resref_name(const std::array<char, 8>& resref) {
  const auto end = std::find(resref.begin(), resref.end(), '\0');
  return std::string(resref.begin(), end);
}

double ticks_to_ms(std::uint64_t ticks, std::int64_t frequency) noexcept {
  if (frequency <= 0) return 0.0;
  return static_cast<double>(ticks) * 1000.0 / static_cast<double>(frequency);
}

void log_report(const char* reason) noexcept {
  try {
    const auto report = g_probe.take_report();
    if (report.groupCount == 0 && report.droppedOccurrences == 0 && report.droppedGroups == 0 &&
        report.invalidSamples == 0) {
      return;
    }
    for (std::size_t index = 0; index < report.groupCount; ++index) {
      const auto& group = report.groups[index];
      const double epochsPerSlot =
          group.completedSlots != 0
              ? static_cast<double>(group.slotEpochsTotal) /
                    static_cast<double>(group.completedSlots)
              : 0.0;
      const double averageSlotMs =
          group.validSlotDurations != 0
              ? ticks_to_ms(group.slotDurationTicksTotal, report.ticksPerSecond) /
                    static_cast<double>(group.validSlotDurations)
              : 0.0;
      LOG_INFO(
          "Area animation clock probe ({}): gen={}, resref={}, seq={}, calls={}, "
          "occurrenceEpochs={}, sameEpochCalls={}, starts={}, slots={}, epochsPerSlot="
          "{:.2f}[{}..{}], slotMs={:.2f}[{:.2f}..{:.2f}], stalledSlots={}, longGaps={}, "
          "transitions={{sequential:{}, skipped:{}, wraps:{}, backward:{}, sequence:{}}}, "
          "worldActive={{on:{}, off:{}, unknown:{}, changes:{}}}, nonMonotonic={}",
          reason, report.areaGeneration, resref_name(group.resref), group.sequence, group.calls,
          group.occurrenceEpochs, group.sameEpochCalls, group.occurrenceStarts,
          group.completedSlots, epochsPerSlot, group.slotEpochsMinimum, group.slotEpochsMaximum,
          averageSlotMs, ticks_to_ms(group.slotDurationTicksMinimum, report.ticksPerSecond),
          ticks_to_ms(group.slotDurationTicksMaximum, report.ticksPerSecond), group.stalledSlots,
          group.longGaps, group.sequentialTransitions, group.skippedForwardTransitions,
          group.wraps, group.backwardTransitions, group.sequenceChanges, group.worldActiveCalls,
          group.worldInactiveCalls, group.worldActiveUnknownCalls, group.worldActiveTransitions,
          group.nonMonotonicClockSamples);
    }
    if (report.droppedOccurrences != 0 || report.droppedGroups != 0 ||
        report.invalidSamples != 0) {
      LOG_WARN(
          "Area animation clock probe capacity/input diagnostics ({}): gen={}, "
          "droppedOccurrences={}, droppedGroups={}, invalidSamples={}",
          reason, report.areaGeneration, report.droppedOccurrences, report.droppedGroups,
          report.invalidSamples);
    }
  } catch (...) {
    // Diagnostics must never escape through an engine render hook.
  }
}
}  // namespace

void configure(bool enabled) noexcept {
  g_enabled.store(false, std::memory_order_release);
  g_activeGeneration = 0;
  g_lastReportTicks = 0;
  g_requestedGeneration.store(1, std::memory_order_release);
  if (enabled) {
    try {
      LOG_INFO(
          "Area animation clock probe enabled; aggregated RenderBam cadence will be logged every "
          "five seconds for registry-backed animations");
    } catch (...) {
    }
  }
  g_enabled.store(enabled, std::memory_order_release);
}

void request_area_generation() noexcept {
  if (!g_enabled.load(std::memory_order_acquire)) return;
  g_requestedGeneration.fetch_add(1, std::memory_order_release);
}

void observe(void* instance, const std::array<char, 8>& resref, int sequence, int slot,
             int worldActive) noexcept {
  if (!g_enabled.load(std::memory_order_acquire) || !instance) return;
  try {
    const auto frequency = frame::clock_frequency();
    const auto now = frame::clock_ticks();
    if (frequency <= 0 || now <= 0) return;

    const auto requestedGeneration = g_requestedGeneration.load(std::memory_order_acquire);
    if (requestedGeneration != g_activeGeneration) {
      if (g_activeGeneration != 0) log_report("area-change");
      g_probe.set_ticks_per_second(frequency);
      g_probe.begin_area(requestedGeneration);
      g_activeGeneration = requestedGeneration;
      g_lastReportTicks = now;
    }

    g_probe.observe({.instance = reinterpret_cast<std::uintptr_t>(instance),
                     .resref = resref,
                     .sequence = sequence,
                     .slot = slot,
                     .presentationEpoch = frame::frame_count(),
                     .clockTicks = now,
                     .worldActive = worldActive});

    if (now >= g_lastReportTicks &&
        now - g_lastReportTicks >= frequency * kReportSeconds) {
      log_report("periodic");
      g_lastReportTicks = now;
    }
  } catch (...) {
    // Diagnostics must never escape through CGameStatic::RenderBam.
  }
}

void shutdown() noexcept {
  const bool wasEnabled = g_enabled.exchange(false, std::memory_order_acq_rel);
  if (wasEnabled && g_activeGeneration != 0) log_report("shutdown");
  g_activeGeneration = 0;
  g_lastReportTicks = 0;
}

}  // namespace iee::area_animation_clock
