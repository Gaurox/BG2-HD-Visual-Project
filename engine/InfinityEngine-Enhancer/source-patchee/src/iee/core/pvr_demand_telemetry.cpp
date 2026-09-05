#include "pvr_demand_telemetry.h"

#include <algorithm>
#include <atomic>
#include <cstddef>
#include <mutex>

namespace iee::core {
namespace {

struct AtomicPvrDemandTelemetry {
  std::atomic<std::uint64_t> calls{};
  std::atomic<std::uint64_t> materializations{};
  std::atomic<std::uint64_t> ioMeasuredMaterializations{};
  std::atomic<std::uint64_t> textureCreations{};
  std::atomic<std::uint64_t> readOperations{};
  std::atomic<std::uint64_t> readBytes{};
  std::atomic<std::uint64_t> demandNanoseconds{};
  std::atomic<std::uint64_t> textureGenerationCalls{};
  std::atomic<std::uint64_t> textureGenerationNanoseconds{};
  std::atomic<std::uint64_t> compressedUploadCalls{};
  std::atomic<std::uint64_t> compressedUploadNanoseconds{};
  std::atomic<std::uint64_t> residualNanoseconds{};
};

struct ActivePvrDemandScope {
  std::uint32_t depth{};
  PvrDemandNestedTimings timings{};
};

constexpr std::size_t kFrameDetailCapacity = 16;
AtomicPvrDemandTelemetry g_stats;
thread_local ActivePvrDemandScope g_activeScope;
std::mutex g_frameDetailMutex;
std::array<PvrDemandFrameDetail, kFrameDetailCapacity> g_frameDetails{};

void reset(std::atomic<std::uint64_t>& value) noexcept {
  value.store(0, std::memory_order_relaxed);
}

std::uint64_t saturated_subtract(std::uint64_t value,
                                 std::uint64_t subtract) noexcept {
  return value >= subtract ? value - subtract : 0;
}

void copy_resref(std::string_view source, std::array<char, 9>& destination) noexcept {
  destination = {};
  const auto count = (std::min)(source.size(), destination.size() - 1);
  std::copy_n(source.begin(), count, destination.begin());
}

}  // namespace

void reset_pvr_demand_telemetry() noexcept {
  reset(g_stats.calls);
  reset(g_stats.materializations);
  reset(g_stats.ioMeasuredMaterializations);
  reset(g_stats.textureCreations);
  reset(g_stats.readOperations);
  reset(g_stats.readBytes);
  reset(g_stats.demandNanoseconds);
  reset(g_stats.textureGenerationCalls);
  reset(g_stats.textureGenerationNanoseconds);
  reset(g_stats.compressedUploadCalls);
  reset(g_stats.compressedUploadNanoseconds);
  reset(g_stats.residualNanoseconds);
  g_activeScope = {};
  std::lock_guard lock(g_frameDetailMutex);
  g_frameDetails = {};
}

void begin_pvr_demand_scope() noexcept {
  if (g_activeScope.depth++ == 0) g_activeScope.timings = {};
}

PvrDemandNestedTimings end_pvr_demand_scope() noexcept {
  if (g_activeScope.depth == 0) return {};
  --g_activeScope.depth;
  if (g_activeScope.depth != 0) return {};
  const auto completed = g_activeScope.timings;
  g_activeScope.timings = {};
  return completed;
}

void record_pvr_scope_texture_generation(std::uint64_t calls,
                                         std::uint64_t nanoseconds) noexcept {
  if (g_activeScope.depth == 0) return;
  g_activeScope.timings.textureGenerationCalls += calls;
  g_activeScope.timings.textureGenerationNanoseconds += nanoseconds;
}

void record_pvr_scope_compressed_upload(std::uint64_t nanoseconds) noexcept {
  if (g_activeScope.depth == 0) return;
  ++g_activeScope.timings.compressedUploadCalls;
  g_activeScope.timings.compressedUploadNanoseconds += nanoseconds;
}

void record_pvr_demand(std::uint64_t frame, std::string_view resref,
                       bool materialized, bool ioMeasured,
                       bool textureCreated, std::int32_t width,
                       std::int32_t height, std::uint64_t demandNanoseconds,
                       std::uint64_t readOperations,
                       std::uint64_t readBytes,
                       const PvrDemandNestedTimings& nested) noexcept {
  g_stats.calls.fetch_add(1, std::memory_order_relaxed);
  if (!materialized) return;

  const auto nestedNanoseconds =
      nested.textureGenerationNanoseconds + nested.compressedUploadNanoseconds;
  const auto residualNanoseconds =
      saturated_subtract(demandNanoseconds, nestedNanoseconds);
  g_stats.materializations.fetch_add(1, std::memory_order_relaxed);
  if (ioMeasured) {
    g_stats.ioMeasuredMaterializations.fetch_add(1, std::memory_order_relaxed);
  }
  if (textureCreated) {
    g_stats.textureCreations.fetch_add(1, std::memory_order_relaxed);
  }
  g_stats.readOperations.fetch_add(readOperations, std::memory_order_relaxed);
  g_stats.readBytes.fetch_add(readBytes, std::memory_order_relaxed);
  g_stats.demandNanoseconds.fetch_add(demandNanoseconds, std::memory_order_relaxed);
  g_stats.textureGenerationCalls.fetch_add(nested.textureGenerationCalls,
                                           std::memory_order_relaxed);
  g_stats.textureGenerationNanoseconds.fetch_add(
      nested.textureGenerationNanoseconds, std::memory_order_relaxed);
  g_stats.compressedUploadCalls.fetch_add(nested.compressedUploadCalls,
                                          std::memory_order_relaxed);
  g_stats.compressedUploadNanoseconds.fetch_add(
      nested.compressedUploadNanoseconds, std::memory_order_relaxed);
  g_stats.residualNanoseconds.fetch_add(residualNanoseconds,
                                        std::memory_order_relaxed);

  if (frame == 0 || demandNanoseconds == 0) return;
  std::lock_guard lock(g_frameDetailMutex);
  auto& detail = g_frameDetails[frame % g_frameDetails.size()];
  if (detail.frame == frame && detail.demandNanoseconds >= demandNanoseconds) return;
  detail = {
      .frame = frame,
      .demandNanoseconds = demandNanoseconds,
      .textureGenerationNanoseconds = nested.textureGenerationNanoseconds,
      .compressedUploadNanoseconds = nested.compressedUploadNanoseconds,
      .residualNanoseconds = residualNanoseconds,
      .readBytes = readBytes,
      .width = width,
      .height = height,
      .ioMeasured = ioMeasured,
  };
  copy_resref(resref, detail.resref);
}

PvrDemandTelemetryStats pvr_demand_telemetry_snapshot() noexcept {
  return {
      .calls = g_stats.calls.load(std::memory_order_relaxed),
      .materializations = g_stats.materializations.load(std::memory_order_relaxed),
      .ioMeasuredMaterializations =
          g_stats.ioMeasuredMaterializations.load(std::memory_order_relaxed),
      .textureCreations = g_stats.textureCreations.load(std::memory_order_relaxed),
      .readOperations = g_stats.readOperations.load(std::memory_order_relaxed),
      .readBytes = g_stats.readBytes.load(std::memory_order_relaxed),
      .demandNanoseconds = g_stats.demandNanoseconds.load(std::memory_order_relaxed),
      .textureGenerationCalls =
          g_stats.textureGenerationCalls.load(std::memory_order_relaxed),
      .textureGenerationNanoseconds =
          g_stats.textureGenerationNanoseconds.load(std::memory_order_relaxed),
      .compressedUploadCalls =
          g_stats.compressedUploadCalls.load(std::memory_order_relaxed),
      .compressedUploadNanoseconds =
          g_stats.compressedUploadNanoseconds.load(std::memory_order_relaxed),
      .residualNanoseconds =
          g_stats.residualNanoseconds.load(std::memory_order_relaxed),
  };
}

PvrDemandFrameDetail pvr_demand_frame_detail_snapshot(
    std::uint64_t frame) noexcept {
  std::lock_guard lock(g_frameDetailMutex);
  const auto detail = g_frameDetails[frame % g_frameDetails.size()];
  return detail.frame == frame ? detail : PvrDemandFrameDetail{};
}

}  // namespace iee::core
