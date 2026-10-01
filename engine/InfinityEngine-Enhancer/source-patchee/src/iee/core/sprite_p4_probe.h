#pragma once

#include <chrono>
#include <cstdint>
#include <filesystem>

#include "iee/core/performance_samples.h"

namespace iee::core::sprite_p4 {

// Diagnostic state is render-thread owned; startup/shutdown occur with hooks quiesced.
// CPU durations include driver submission, never GPU execution time.
struct View {
  int viewportWidth{}, viewportHeight{}, framebuffer{};
  float worldWidth{}, worldHeight{}, scrollX{}, scrollY{};
  int scale{}, minFilter{}, magFilter{};
  int filterMode{}, maximumMipLevel{}, provenance{}, animationId{};
};

struct Window {
  PerformanceSamples<2048> frames;
  std::uint64_t frameCount{}, views{}, invalidViews{};
  View view{};
  double minZoomX{}, maxZoomX{}, minZoomY{}, maxZoomY{};
  bool mixedView{};
  std::uint64_t composites{}, successfulComposites{}, pixelCalls{}, pixelCacheHits{};
  std::uint64_t uploads{}, successfulUploads{}, uploadBytes{};
  std::uint64_t masks{}, successfulMasks{};
  double compositeMs{}, compositeMaxMs{}, pixelMs{}, uploadMs{}, uploadMaxMs{};
  double maskMs{}, maskMaxMs{};

  void add_frame(double intervalMs) noexcept;
  void add_view(const View& value) noexcept;
};

enum class Metric { Composite, Pixels, Upload, Mask };

[[nodiscard]] bool enabled() noexcept;
// Empty/relative directory, existing output or write failure disables the probe.
[[nodiscard]] bool configure(bool enable, const std::filesystem::path& directory) noexcept;
[[nodiscard]] std::filesystem::path output_path();
[[nodiscard]] bool wants_view(std::uint64_t frame) noexcept;
void observe_view(std::uint64_t frame, const View& view) noexcept;
void record_metric(Metric metric, double milliseconds, bool success,
                   std::uint64_t bytes = 0) noexcept;
void record_pixel_cache_hit() noexcept;
void on_frame(double presentationIntervalMs) noexcept;
void shutdown() noexcept;

class ScopedMetric {
 public:
  ScopedMetric(Metric metric, bool target) noexcept;
  ~ScopedMetric() noexcept;
  void success(std::uint64_t bytes = 0) noexcept { success_ = true; bytes_ = bytes; }
  ScopedMetric(const ScopedMetric&) = delete;
  ScopedMetric& operator=(const ScopedMetric&) = delete;
 private:
  Metric metric_;
  bool active_{}, success_{};
  std::uint64_t bytes_{};
  std::chrono::steady_clock::time_point start_{};
};

}  // namespace iee::core::sprite_p4
