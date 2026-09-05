#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace iee::core {

// PerformanceLogs-only diagnostic for the sudden world-view expansion that
// occurs when the in-game area map is shown. The tracker consumes cumulative
// counters at presentation boundaries and stores a short fixed-size capture;
// it never performs I/O, OpenGL work, or resource-demand changes.
inline constexpr std::size_t kMapViewBurstCaptureFrameCount = 8;
inline constexpr std::size_t kMapViewBurstExpansionWindowFrameCount = 16;
inline constexpr float kMapViewBurstMinimumExpansionRatio = 1.25f;

struct MapViewCumulativeCounters {
  std::uint64_t tileDraws{};
  std::uint64_t tablePagesObserved{};
  std::uint64_t sourceTextureIdsObserved{};
  std::uint64_t compressedUploadCalls{};
  std::uint64_t compressedUploadBytes{};
  std::uint64_t compressedUploadNanoseconds{};
  std::uint64_t largeS3tcBaseLevelCalls{};
  std::uint64_t largeS3tcBaseLevelBytes{};
  std::uint64_t deleteCalls{};
  std::uint64_t deletedTextureNames{};
  std::uint64_t pvrDemandCalls{};
  std::uint64_t pvrMaterializations{};
  std::uint64_t pvrIoMeasuredMaterializations{};
  std::uint64_t pvrTextureCreations{};
  std::uint64_t pvrReadOperations{};
  std::uint64_t pvrReadBytes{};
  std::uint64_t pvrDemandNanoseconds{};
  std::uint64_t pvrTextureGenerationCalls{};
  std::uint64_t pvrTextureGenerationNanoseconds{};
  std::uint64_t pvrCompressedUploadCalls{};
  std::uint64_t pvrCompressedUploadNanoseconds{};
  std::uint64_t pvrResidualNanoseconds{};
};

struct MapViewBurstFrameSample {
  std::uint64_t frame{};
  bool viewObserved{};
  float viewWorldWidth{};
  float viewWorldHeight{};
  double presentationIntervalMilliseconds{-1.0};
  double renderTextureCpuMilliseconds{};
  MapViewCumulativeCounters delta{};
};

struct MapViewBurstCapture {
  std::uint64_t eventId{};
  float previousViewWorldWidth{};
  float previousViewWorldHeight{};
  float triggerViewWorldWidth{};
  float triggerViewWorldHeight{};
  std::size_t frameCount{};
  std::array<MapViewBurstFrameSample, kMapViewBurstCaptureFrameCount> frames{};
};

class MapViewBurstTelemetry {
 public:
  void reset() noexcept;
  void observe_view(std::uint64_t frame, float viewWorldWidth,
                    float viewWorldHeight) noexcept;
  void record_render_texture_cpu(std::uint64_t frame,
                                 double milliseconds) noexcept;

  // Returns one completed buffered capture. Logging is deliberately left to
  // the caller so the hot frames do not pay for synchronous INFO flushes.
  [[nodiscard]] std::optional<MapViewBurstCapture> finish_frame(
      std::uint64_t frame, const MapViewCumulativeCounters& cumulative,
      double presentationIntervalMilliseconds) noexcept;

  // Read only from the presentation thread immediately after finish_frame().
  // It becomes true on the expansion-trigger frame, before the buffered
  // eight-frame capture is complete.
  [[nodiscard]] bool capture_active() const noexcept { return captureActive; }

 private:
  struct ViewState {
    float width{};
    float height{};
  };

  struct ViewObservation {
    std::uint64_t frame{};
    ViewState view{};
  };

  std::uint64_t observedViewFrame{};
  bool observedViewValid{};
  ViewState observedView_{};
  bool previousViewValid{};
  ViewState previousView_{};
  std::size_t viewHistoryCount{};
  std::array<ViewObservation, kMapViewBurstExpansionWindowFrameCount>
      viewHistory_{};
  bool expansionArmed{true};
  ViewState rearmBaseline_{};

  bool counterBaselineValid{};
  MapViewCumulativeCounters previousCounters_{};

  std::uint64_t renderCpuFrame{};
  double renderCpuMilliseconds{};

  std::uint64_t nextEventId{1};
  bool captureActive{};
  MapViewBurstCapture capture_{};
};

}  // namespace iee::core
