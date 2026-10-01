#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "iee/core/config.h"
#include "iee/core/sprite_p4_probe.h"

namespace {
int failures{};
void check(bool value, const char* label) {
  if (!value) { std::cerr << "FAIL: " << label << '\n'; ++failures; }
}
std::vector<std::string> columns(const std::string& row) {
  std::vector<std::string> result;
  std::istringstream input(row);
  for (std::string cell; std::getline(input, cell, ',');) result.push_back(cell);
  return result;
}
}

int main() {
  namespace p4 = iee::core::sprite_p4;
  p4::Window window;
  const p4::View view{.viewportWidth = 2528, .viewportHeight = 1339,
      .worldWidth = 1264.0f, .worldHeight = 669.5f, .scale = 4,
      .minFilter = 0x2600, .magFilter = 0x2600};
  window.add_view(view);
  check(window.views == 1 && window.maxZoomX == 2.0 && window.maxZoomY == 2.0,
        "zoom uses actual viewport on both axes");
  auto scrolling = view;
  scrolling.scrollX = 50.0f;
  window.add_view(scrolling);
  check(!window.mixedView, "camera translation preserves scale");
  auto changed = view;
  changed.worldWidth *= 2.0f;
  changed.worldHeight *= 2.0f;
  window.add_view(changed);
  check(window.mixedView && window.minZoomX == 1.0 && window.maxZoomX == 2.0,
        "transition windows preserve extrema and are flagged");
  changed.worldWidth = std::numeric_limits<float>::quiet_NaN();
  window.add_view(changed);
  check(window.invalidViews == 1 && window.views == 3, "invalid engine state rejected");
  for (int i = 1; i <= 100; ++i) window.add_frame(i);
  window.add_frame(-1);
  window.add_frame(std::numeric_limits<double>::infinity());
  const auto summary = window.frames.summarize();
  check(summary.count == 100 && summary.percentile95 == 95.0,
        "frame p95 excludes invalid intervals");

  const auto root = std::filesystem::temp_directory_path() /
      ("iee-p4-test-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
  check(!p4::configure(false, root) && !std::filesystem::exists(root),
        "disabled probe makes no directory");
  check(!p4::configure(true, "relative-path"), "ambiguous output paths rejected");
  check(p4::configure(true, root), "session opens");
  const auto first = p4::output_path();
  p4::observe_view(1, view);
  p4::observe_view(1, changed);  // Same-frame duplicates must not poison the sample.
  p4::record_metric(p4::Metric::Composite, 2.0, true);
  p4::record_metric(p4::Metric::Composite, 1.0, false);
  p4::record_metric(p4::Metric::Pixels, 0.5, true);
  p4::record_pixel_cache_hit();
  p4::record_metric(p4::Metric::Upload, 0.25, true, 1024);
  p4::record_metric(p4::Metric::Upload, 0.125, false, 2048);
  p4::record_metric(p4::Metric::Mask, 0.5, true);
  p4::record_metric(p4::Metric::Mask, 0.25, false);
  p4::on_frame(16.0);
  std::this_thread::sleep_for(std::chrono::milliseconds(1050));
  p4::on_frame(16.0);
  check(std::filesystem::file_size(first) > 500, "periodic CSV row is flushed before shutdown");
  p4::shutdown();
  std::ifstream input(first);
  std::string header, row;
  std::getline(input, header);
  std::getline(input, row);
  const auto keys = columns(header), values = columns(row);
  check(keys.size() == values.size(), "CSV schema and row have matching width");
  const auto get = [&](const std::string& key) -> std::string {
    for (std::size_t i = 0; i < keys.size() && i < values.size(); ++i) {
      if (keys[i] == key) return values[i];
    }
    return "";
  };
  check(get("view_samples") == "1" && get("view_valid") == "1", "one real view per frame");
  check(get("target_calls") == "2" && get("target_successes") == "1", "failures counted");
  check(get("target_cpu_ms") == "3.000000" && get("pixel_cache_hits") == "1", "CPU/cache totals");
  check(get("upload_bytes") == "1024" && get("upload_successes") == "1", "only successful upload bytes");
  check(get("mask_calls") == "2" && get("mask_successes") == "1" &&
        get("mask_cpu_ms") == "0.750000", "masked driver CPU accounted separately");
  check(p4::configure(true, root) && p4::output_path() != first, "new launch creates distinct CSV");
  p4::shutdown();
  check(std::filesystem::file_size(first) > header.size(), "prior session preserved");
  iee::core::EngineConfig cfg;
  check(!cfg.enableCreatureSpriteP4Probe, "INI opt-in defaults off");
  cfg.enableCreatureSpriteP4Probe = true;
  cfg.creatureSpriteP4Output = root;
  const auto ini = root / "probe.ini";
  check(iee::core::ConfigManager::save(ini, cfg), "config writes");
  iee::core::EngineConfig loaded;
  check(iee::core::ConfigManager::load(ini, loaded) && loaded.enableCreatureSpriteP4Probe &&
        loaded.creatureSpriteP4Output == root, "config round-trip");
  input.close();
  std::filesystem::remove(first);
  std::filesystem::remove(p4::output_path());
  std::filesystem::remove(ini);
  std::filesystem::remove(root);
  if (failures == 0) std::cout << "P4 probe tests passed\n";
  return failures ? 1 : 0;
}
