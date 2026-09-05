#pragma once

#include <array>
#include <cstdint>
#include <string_view>

namespace iee::core {

// PerformanceLogs-only accounting for CResPVR::Demand. The engine hook owns
// the total duration while nested GL hooks contribute only the time spent in
// texture-name creation and compressed upload. The remainder is deliberately
// labeled residual: it includes resource lookup/read, zlib/PVR preparation and
// engine bookkeeping, and must not be presented as pure decompression time.
struct PvrDemandNestedTimings {
  std::uint64_t textureGenerationCalls{};
  std::uint64_t textureGenerationNanoseconds{};
  std::uint64_t compressedUploadCalls{};
  std::uint64_t compressedUploadNanoseconds{};
};

struct PvrDemandTelemetryStats {
  std::uint64_t calls{};
  std::uint64_t materializations{};
  std::uint64_t ioMeasuredMaterializations{};
  std::uint64_t textureCreations{};
  std::uint64_t readOperations{};
  std::uint64_t readBytes{};
  std::uint64_t demandNanoseconds{};
  std::uint64_t textureGenerationCalls{};
  std::uint64_t textureGenerationNanoseconds{};
  std::uint64_t compressedUploadCalls{};
  std::uint64_t compressedUploadNanoseconds{};
  std::uint64_t residualNanoseconds{};
};

struct PvrDemandFrameDetail {
  std::uint64_t frame{};
  std::array<char, 9> resref{};
  std::uint64_t demandNanoseconds{};
  std::uint64_t textureGenerationNanoseconds{};
  std::uint64_t compressedUploadNanoseconds{};
  std::uint64_t residualNanoseconds{};
  std::uint64_t readBytes{};
  std::int32_t width{};
  std::int32_t height{};
  bool ioMeasured{};

  [[nodiscard]] bool valid() const noexcept {
    return frame != 0 && demandNanoseconds != 0;
  }
};

void reset_pvr_demand_telemetry() noexcept;

// Scope is thread-local so unrelated GL calls on another thread cannot be
// charged to a PVR materialization. Nested scopes fail closed: only the outer
// scope receives the accumulated GL timings.
void begin_pvr_demand_scope() noexcept;
[[nodiscard]] PvrDemandNestedTimings end_pvr_demand_scope() noexcept;
void record_pvr_scope_texture_generation(std::uint64_t calls,
                                         std::uint64_t nanoseconds) noexcept;
void record_pvr_scope_compressed_upload(std::uint64_t nanoseconds) noexcept;

void record_pvr_demand(std::uint64_t frame, std::string_view resref,
                       bool materialized, bool ioMeasured,
                       bool textureCreated, std::int32_t width,
                       std::int32_t height, std::uint64_t demandNanoseconds,
                       std::uint64_t readOperations,
                       std::uint64_t readBytes,
                       const PvrDemandNestedTimings& nested) noexcept;

[[nodiscard]] PvrDemandTelemetryStats pvr_demand_telemetry_snapshot() noexcept;
[[nodiscard]] PvrDemandFrameDetail pvr_demand_frame_detail_snapshot(
    std::uint64_t frame) noexcept;

}  // namespace iee::core
