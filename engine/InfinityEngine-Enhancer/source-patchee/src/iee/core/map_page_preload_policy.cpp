#include "map_page_preload_policy.h"
#include "map_page_prepare_queue.h"
#include <algorithm>
#include <cmath>

namespace iee::core {
namespace {
bool valid_name(std::string_view name) {
  return !name.empty() && name.size() <= 8 &&
      std::all_of(name.begin(), name.end(), [](char c) {
        return (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_';
      });
}
}
bool parse_map_page_bindings(std::istream& input, std::vector<MapPageBinding>& out) {
  out.clear();
  std::string magic, area, keyword;
  if (!(input >> magic >> area) || magic != "IEE_PRELOAD_BINDINGS_V1" || area != "AR0900")
    return false;
  std::vector<MapPageBinding> parsed;
  while (input >> keyword) {
    MapPageBinding b;
    if (keyword != "PAGE" || parsed.size() >= kPreparePageLimit ||
        !(input >> b.page >> b.tileset >> b.pageNumber >> b.tileIndex) ||
        !valid_name(b.page) || !valid_name(b.tileset) || b.tileset.size() < 2 ||
        b.pageNumber < 0 || b.tileIndex >= 1048576) return false;
    auto number = std::to_string(b.pageNumber);
    if (number.size() < 2) number.insert(0, 1, '0');
    if (b.page != b.tileset.substr(0, 1) + b.tileset.substr(2) + number) return false;
    for (const auto& previous : parsed) if (previous.page == b.page) return false;
    parsed.push_back(std::move(b));
  }
  if (!input.eof() || parsed.empty()) return false;
  out = std::move(parsed);
  return true;
}
bool preserves_pvr_cache(std::span<const std::uintptr_t> before,
                         std::span<const std::uintptr_t> after) noexcept {
  for (auto p : before)
    if (p && std::find(after.begin(), after.end(), p) == after.end()) return false;
  return true;
}
bool MapPagePreloadPolicy::admit(std::uint64_t frame, double lastIntervalMs, double elapsedMs,
                               std::size_t decodedBytes, std::size_t occupiedSlots) const noexcept {
  if (stopped_ || frame == lastFrame_ || !std::isfinite(lastIntervalMs) ||
      !std::isfinite(elapsedMs) || lastIntervalMs <= 0 || elapsedMs < 0 ||
      decodedBytes < 52 || decodedBytes > kShadowMaximumDecodedBytes || occupiedSlots >= 96)
    return false;
  // Presentation intervals include the game's 30fps limiter: they are not CPU
  // busy time. Admit capped steady frames; skip a frame following a slowdown.
  return lastIntervalMs <= targetMs + 2.0 && elapsedMs + estimateMs_ <= budgetMs;
}
void MapPagePreloadPolicy::completed(std::uint64_t frame, double milliseconds, bool valid) noexcept {
  lastFrame_ = frame;
  if (!valid || !std::isfinite(milliseconds) || milliseconds < 0 || milliseconds > budgetMs) {
    stopped_ = true;
    return;
  }
  estimateMs_ = (std::max)(2.0, (std::max)(milliseconds * 1.15,
                                         estimateMs_ * 0.75 + milliseconds * 0.25));
}
}
