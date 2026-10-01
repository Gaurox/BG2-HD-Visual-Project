#include "sprite_p4_probe.h"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>

#ifdef _WIN32
#include <windows.h>
#endif

#include "iee/core/logger.h"
#include "iee/core/process_resource_telemetry.h"

namespace iee::core::sprite_p4 {
namespace {
using Clock = std::chrono::steady_clock;
std::atomic<bool> g_enabled{false};
Window g_window;
std::ofstream g_output;
std::filesystem::path g_path;
Clock::time_point g_start{}, g_lastWrite{};
std::uint64_t g_lastViewFrame = (std::numeric_limits<std::uint64_t>::max)();
std::uint64_t g_rows{};
constexpr std::uint64_t kMaximumRows = 7200;

std::string utc_stamp() {
  const auto now = std::chrono::system_clock::now();
  const auto value = std::chrono::system_clock::to_time_t(now);
  std::tm utc{};
#ifdef _WIN32
  gmtime_s(&utc, &value);
#else
  gmtime_r(&value, &utc);
#endif
  std::ostringstream text;
  text << std::put_time(&utc, "%Y%m%dT%H%M%S") << '-'
       << std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch()).count();
  return text.str();
}

void write_window(Clock::time_point now) {
  const auto frame = g_window.frames.summarize();
  const auto memory = capture_process_resource_snapshot();
  const auto& v = g_window.view;
  const bool viewValid = g_window.views > 0 && g_window.invalidViews == 0;
  const double zoomX = viewValid ? static_cast<double>(v.viewportWidth) / v.worldWidth : 0.0;
  const double zoomY = viewValid ? static_cast<double>(v.viewportHeight) / v.worldHeight : 0.0;
  g_output << std::fixed << std::setprecision(6)
      << std::chrono::duration<double>(now - g_start).count() << ','
      << std::chrono::duration<double>(now - g_lastWrite).count() << ','
      << g_window.frameCount << ',' << frame.count << ',' << frame.dropped << ','
      << frame.average << ',' << frame.percentile95 << ',' << frame.maximum << ','
      << (frame.average > 0.0 ? 1000.0 / frame.average : 0.0) << ','
      << g_window.views << ',' << viewValid << ',' << g_window.mixedView << ','
      << v.viewportWidth << ',' << v.viewportHeight << ',' << v.framebuffer << ','
      << v.worldWidth << ',' << v.worldHeight << ',' << zoomX << ',' << zoomY << ','
      << g_window.minZoomX << ',' << g_window.maxZoomX << ','
      << g_window.minZoomY << ',' << g_window.maxZoomY << ','
      << v.scrollX << ',' << v.scrollY << ',' << v.scale << ','
      << v.minFilter << ',' << v.magFilter << ','
      << g_window.composites << ',' << g_window.successfulComposites << ','
      << g_window.compositeMs << ',' << g_window.compositeMaxMs << ','
      << g_window.pixelCalls << ',' << g_window.pixelCacheHits << ',' << g_window.pixelMs << ','
      << g_window.uploads << ',' << g_window.successfulUploads << ',' << g_window.uploadBytes << ','
      << g_window.uploadMs << ',' << g_window.uploadMaxMs << ','
      << memory.memoryAvailable << ',' << memory.workingSetBytes << ',' << memory.privateBytes
      << ',' << v.filterMode << ',' << v.maximumMipLevel << ',' << v.provenance << ',' << v.animationId
      << ',' << g_window.masks << ',' << g_window.successfulMasks << ','
      << g_window.maskMs << ',' << g_window.maskMaxMs
      << '\n';
  g_output.flush();
  if (!g_output) throw std::runtime_error("CSV write failed");
  g_window = {};
  g_lastWrite = now;
  ++g_rows;
}
}  // namespace

void Window::add_frame(double intervalMs) noexcept {
  ++frameCount;
  if (std::isfinite(intervalMs) && intervalMs > 0.0) frames.add(intervalMs);
}

void Window::add_view(const View& value) noexcept {
  if (value.viewportWidth <= 0 || value.viewportHeight <= 0 ||
      !std::isfinite(value.worldWidth) || !std::isfinite(value.worldHeight) ||
      value.worldWidth <= 0.0f || value.worldHeight <= 0.0f ||
      !std::isfinite(value.scrollX) || !std::isfinite(value.scrollY) ||
      (value.scale != 2 && value.scale != 4)) {
    ++invalidViews;
    return;
  }
  const double x = static_cast<double>(value.viewportWidth) / value.worldWidth;
  const double y = static_cast<double>(value.viewportHeight) / value.worldHeight;
  if (views == 0) {
    minZoomX = maxZoomX = x;
    minZoomY = maxZoomY = y;
  } else {
    mixedView = mixedView || value.viewportWidth != view.viewportWidth ||
        value.viewportHeight != view.viewportHeight || value.framebuffer != view.framebuffer ||
        value.scale != view.scale || value.minFilter != view.minFilter || value.magFilter != view.magFilter ||
        value.filterMode != view.filterMode ||
        std::abs(x - maxZoomX) > 1e-5 || std::abs(y - maxZoomY) > 1e-5;
    minZoomX = (std::min)(minZoomX, x);
    maxZoomX = (std::max)(maxZoomX, x);
    minZoomY = (std::min)(minZoomY, y);
    maxZoomY = (std::max)(maxZoomY, y);
  }
  view = value;
  ++views;
}

bool enabled() noexcept { return g_enabled.load(std::memory_order_relaxed); }

bool configure(bool enable, const std::filesystem::path& directory) noexcept {
  shutdown();
  g_path.clear();
  if (!enable) return false;
  try {
    if (directory.empty() || !directory.is_absolute()) return false;
    std::filesystem::create_directories(directory);
    g_path = directory / ("p4-" + utc_stamp() + ".csv");
    if (std::filesystem::exists(g_path)) return false;
    g_output.open(g_path, std::ios::out);
    g_output.imbue(std::locale::classic());
    g_output << "elapsed_s,window_s,frames,frame_samples,frame_dropped,frame_avg_ms,frame_p95_ms,frame_max_ms,fps,"
                "view_samples,view_valid,view_mixed,viewport_w,viewport_h,framebuffer,world_w,world_h,zoom_x,zoom_y,"
                "zoom_min_x,zoom_max_x,zoom_min_y,zoom_max_y,scroll_x,scroll_y,scale,min_filter,mag_filter,"
                "target_calls,target_successes,target_cpu_ms,target_cpu_max_ms,pixel_calls,pixel_cache_hits,pixel_cpu_ms,"
                "upload_calls,upload_successes,upload_bytes,upload_cpu_ms,upload_cpu_max_ms,"
                "memory_valid,working_set_bytes,private_bytes,filter_mode,max_mip_level,provenance,animation_id,"
                "mask_calls,mask_successes,mask_cpu_ms,mask_cpu_max_ms\n";
    g_output.flush();
    if (!g_output) throw std::runtime_error("CSV open failed");
    g_start = g_lastWrite = Clock::now();
    g_window = {};
    g_rows = 0;
    g_lastViewFrame = (std::numeric_limits<std::uint64_t>::max)();
    g_enabled.store(true, std::memory_order_relaxed);
    LOG_INFO("P4_SPRITE_PROBE enabled: target=0x6110, period=1s, maxRows={}, CSV={}",
             kMaximumRows, g_path.string());
    return true;
  } catch (...) {
    g_enabled.store(false, std::memory_order_relaxed);
    g_output.close();
    LOG_WARN("P4_SPRITE_PROBE unavailable; native rendering is unchanged");
    return false;
  }
}

std::filesystem::path output_path() { return g_path; }
bool wants_view(std::uint64_t frame) noexcept { return enabled() && frame != g_lastViewFrame; }
void observe_view(std::uint64_t frame, const View& view) noexcept {
  if (!wants_view(frame)) return;
  g_lastViewFrame = frame;
  g_window.add_view(view);
}

void record_metric(Metric metric, double milliseconds, bool success, std::uint64_t bytes) noexcept {
  if (!enabled() || !std::isfinite(milliseconds) || milliseconds < 0.0) return;
  if (metric == Metric::Composite) {
    ++g_window.composites;
    g_window.successfulComposites += success ? 1 : 0;
    g_window.compositeMs += milliseconds;
    g_window.compositeMaxMs = (std::max)(g_window.compositeMaxMs, milliseconds);
  } else if (metric == Metric::Pixels) {
    ++g_window.pixelCalls;
    g_window.pixelMs += milliseconds;
  } else if (metric == Metric::Mask) {
    ++g_window.masks;
    g_window.successfulMasks += success ? 1 : 0;
    g_window.maskMs += milliseconds;
    g_window.maskMaxMs = (std::max)(g_window.maskMaxMs, milliseconds);
  } else {
    ++g_window.uploads;
    g_window.successfulUploads += success ? 1 : 0;
    g_window.uploadBytes += success ? bytes : 0;
    g_window.uploadMs += milliseconds;
    g_window.uploadMaxMs = (std::max)(g_window.uploadMaxMs, milliseconds);
  }
}

void record_pixel_cache_hit() noexcept { if (enabled()) ++g_window.pixelCacheHits; }

void on_frame(double presentationIntervalMs) noexcept {
  if (!enabled()) return;
  g_window.add_frame(presentationIntervalMs);
  const auto now = Clock::now();
  if (now - g_lastWrite < std::chrono::seconds(1)) return;
  try {
    write_window(now);
    if (g_rows >= kMaximumRows) {
      g_enabled.store(false, std::memory_order_relaxed);
      g_output.close();
      LOG_INFO("P4_SPRITE_PROBE stopped at row limit");
    }
  } catch (...) {
    g_enabled.store(false, std::memory_order_relaxed);
    g_output.close();
    LOG_WARN("P4_SPRITE_PROBE stopped after CSV write failure");
  }
}

void shutdown() noexcept {
  if (g_enabled.exchange(false, std::memory_order_relaxed)) {
    try { if (g_window.frameCount > 0) write_window(Clock::now()); } catch (...) {}
  }
  if (g_output.is_open()) g_output.close();
  g_output.clear();
}

ScopedMetric::ScopedMetric(Metric metric, bool target) noexcept
    : metric_(metric), active_(target && enabled()) {
  if (active_) start_ = Clock::now();
}
ScopedMetric::~ScopedMetric() noexcept {
  if (active_) record_metric(metric_, std::chrono::duration<double, std::milli>(Clock::now() - start_).count(),
                             success_, bytes_);
}
}  // namespace iee::core::sprite_p4
