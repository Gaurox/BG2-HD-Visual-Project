#include "map_view_burst_telemetry.h"

#include <algorithm>
#include <cmath>

namespace iee::core {
namespace {

std::uint64_t cumulative_delta(std::uint64_t previous,
                               std::uint64_t current) noexcept {
  return current >= previous ? current - previous : current;
}

MapViewCumulativeCounters counter_delta(
    const MapViewCumulativeCounters& previous,
    const MapViewCumulativeCounters& current) noexcept {
  return {
      .tileDraws = cumulative_delta(previous.tileDraws, current.tileDraws),
      .tablePagesObserved =
          cumulative_delta(previous.tablePagesObserved, current.tablePagesObserved),
      .sourceTextureIdsObserved = cumulative_delta(
          previous.sourceTextureIdsObserved, current.sourceTextureIdsObserved),
      .compressedUploadCalls = cumulative_delta(
          previous.compressedUploadCalls, current.compressedUploadCalls),
      .compressedUploadBytes = cumulative_delta(
          previous.compressedUploadBytes, current.compressedUploadBytes),
      .compressedUploadNanoseconds = cumulative_delta(
          previous.compressedUploadNanoseconds,
          current.compressedUploadNanoseconds),
      .largeS3tcBaseLevelCalls = cumulative_delta(
          previous.largeS3tcBaseLevelCalls, current.largeS3tcBaseLevelCalls),
      .largeS3tcBaseLevelBytes = cumulative_delta(
          previous.largeS3tcBaseLevelBytes, current.largeS3tcBaseLevelBytes),
      .deleteCalls = cumulative_delta(previous.deleteCalls, current.deleteCalls),
      .deletedTextureNames =
          cumulative_delta(previous.deletedTextureNames, current.deletedTextureNames),
      .pvrDemandCalls =
          cumulative_delta(previous.pvrDemandCalls, current.pvrDemandCalls),
      .pvrMaterializations = cumulative_delta(
          previous.pvrMaterializations, current.pvrMaterializations),
      .pvrIoMeasuredMaterializations = cumulative_delta(
          previous.pvrIoMeasuredMaterializations,
          current.pvrIoMeasuredMaterializations),
      .pvrTextureCreations = cumulative_delta(
          previous.pvrTextureCreations, current.pvrTextureCreations),
      .pvrReadOperations = cumulative_delta(
          previous.pvrReadOperations, current.pvrReadOperations),
      .pvrReadBytes =
          cumulative_delta(previous.pvrReadBytes, current.pvrReadBytes),
      .pvrDemandNanoseconds = cumulative_delta(
          previous.pvrDemandNanoseconds, current.pvrDemandNanoseconds),
      .pvrTextureGenerationCalls = cumulative_delta(
          previous.pvrTextureGenerationCalls,
          current.pvrTextureGenerationCalls),
      .pvrTextureGenerationNanoseconds = cumulative_delta(
          previous.pvrTextureGenerationNanoseconds,
          current.pvrTextureGenerationNanoseconds),
      .pvrCompressedUploadCalls = cumulative_delta(
          previous.pvrCompressedUploadCalls,
          current.pvrCompressedUploadCalls),
      .pvrCompressedUploadNanoseconds = cumulative_delta(
          previous.pvrCompressedUploadNanoseconds,
          current.pvrCompressedUploadNanoseconds),
      .pvrResidualNanoseconds = cumulative_delta(
          previous.pvrResidualNanoseconds, current.pvrResidualNanoseconds),
  };
}

bool valid_view(float width, float height) noexcept {
  return std::isfinite(width) && std::isfinite(height) && width > 0.0f &&
         height > 0.0f;
}

bool is_sudden_expansion(float previousWidth, float previousHeight,
                         float currentWidth, float currentHeight) noexcept {
  return currentWidth >= previousWidth * kMapViewBurstMinimumExpansionRatio &&
         currentHeight >= previousHeight * kMapViewBurstMinimumExpansionRatio;
}

bool has_returned_below_expansion_threshold(
    float baselineWidth, float baselineHeight, float currentWidth,
    float currentHeight) noexcept {
  return currentWidth < baselineWidth * kMapViewBurstMinimumExpansionRatio &&
         currentHeight < baselineHeight * kMapViewBurstMinimumExpansionRatio;
}

}  // namespace

void MapViewBurstTelemetry::reset() noexcept { *this = {}; }

void MapViewBurstTelemetry::observe_view(std::uint64_t frame, float viewWorldWidth,
                                         float viewWorldHeight) noexcept {
  if (!valid_view(viewWorldWidth, viewWorldHeight)) return;
  observedViewFrame = frame;
  observedViewValid = true;
  observedView_ = {.width = viewWorldWidth, .height = viewWorldHeight};
}

void MapViewBurstTelemetry::record_render_texture_cpu(
    std::uint64_t frame, double milliseconds) noexcept {
  if (!std::isfinite(milliseconds) || milliseconds < 0.0) return;
  if (renderCpuFrame != frame) {
    renderCpuFrame = frame;
    renderCpuMilliseconds = 0.0;
  }
  renderCpuMilliseconds += milliseconds;
}

std::optional<MapViewBurstCapture> MapViewBurstTelemetry::finish_frame(
    std::uint64_t frame, const MapViewCumulativeCounters& cumulative,
    double presentationIntervalMilliseconds) noexcept {
  MapViewCumulativeCounters delta{};
  if (counterBaselineValid) {
    delta = counter_delta(previousCounters_, cumulative);
  }
  previousCounters_ = cumulative;
  counterBaselineValid = true;

  const bool haveCurrentView = observedViewValid && observedViewFrame == frame;
  const ViewState currentView = haveCurrentView ? observedView_ : previousView_;
  MapViewBurstFrameSample sample{
      .frame = frame,
      .viewObserved = haveCurrentView,
      .viewWorldWidth = currentView.width,
      .viewWorldHeight = currentView.height,
      .presentationIntervalMilliseconds =
          std::isfinite(presentationIntervalMilliseconds)
              ? presentationIntervalMilliseconds
              : -1.0,
      .renderTextureCpuMilliseconds =
          renderCpuFrame == frame ? renderCpuMilliseconds : 0.0,
      .delta = delta,
  };
  if (renderCpuFrame == frame) {
    renderCpuMilliseconds = 0.0;
  }

  if (!expansionArmed && haveCurrentView &&
      has_returned_below_expansion_threshold(
          rearmBaseline_.width, rearmBaseline_.height, currentView.width,
          currentView.height)) {
    expansionArmed = true;
    viewHistoryCount = 0;
  }

  std::optional<ViewState> expansionBaseline;
  if (expansionArmed && !captureActive && haveCurrentView) {
    for (std::size_t offset = 0; offset < viewHistoryCount; ++offset) {
      const auto index = viewHistoryCount - offset - 1;
      const auto& observation = viewHistory_[index];
      if (frame <= observation.frame ||
          frame - observation.frame > kMapViewBurstExpansionWindowFrameCount) {
        continue;
      }
      if (is_sudden_expansion(observation.view.width, observation.view.height,
                              currentView.width, currentView.height)) {
        expansionBaseline = observation.view;
        break;
      }
    }
  }

  if (expansionBaseline) {
    expansionArmed = false;
    rearmBaseline_ = *expansionBaseline;
    captureActive = true;
    capture_ = {
        .eventId = nextEventId++,
        .previousViewWorldWidth = expansionBaseline->width,
        .previousViewWorldHeight = expansionBaseline->height,
        .triggerViewWorldWidth = currentView.width,
        .triggerViewWorldHeight = currentView.height,
    };
    // Do not retain the pre-map baseline. The detector remains disarmed until
    // both dimensions contract below the trigger threshold relative to it.
    viewHistoryCount = 0;
  }

  if (haveCurrentView) {
    previousView_ = currentView;
    previousViewValid = true;
    if (expansionArmed) {
      if (viewHistoryCount == viewHistory_.size()) {
        std::move(viewHistory_.begin() + 1, viewHistory_.end(),
                  viewHistory_.begin());
        --viewHistoryCount;
      }
      viewHistory_[viewHistoryCount++] = {
          .frame = frame,
          .view = currentView,
      };
    }
  }

  if (!captureActive) return std::nullopt;
  if (capture_.frameCount < capture_.frames.size()) {
    capture_.frames[capture_.frameCount++] = sample;
  }
  if (capture_.frameCount < capture_.frames.size()) return std::nullopt;

  auto completed = capture_;
  capture_ = {};
  captureActive = false;
  return completed;
}

}  // namespace iee::core
