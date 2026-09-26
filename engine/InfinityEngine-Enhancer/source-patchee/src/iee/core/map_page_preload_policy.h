#pragma once
#include <cstdint>
#include <istream>
#include <span>
#include <string>
#include <vector>

namespace iee::core {
struct MapPageBinding {
  std::string page, tileset;
  std::int32_t pageNumber{};
  std::uint32_t tileIndex{};
};
bool parse_map_page_bindings(std::istream& input, std::vector<MapPageBinding>& out);
bool preserves_pvr_cache(std::span<const std::uintptr_t> before,
                         std::span<const std::uintptr_t> after) noexcept;

// Admission is predictive: a native Demand cannot be preempted. One page per
// presentation, 32 free native slots retained, and no further preloads after
// a failed substitution or an observed per-page budget overrun in this plan.
class MapPagePreloadPolicy {
 public:
  static constexpr double budgetMs = 8.0;
  static constexpr double targetMs = 1000.0 / 30.0;
  bool admit(std::uint64_t frame, double lastIntervalMs, double elapsedMs,
             std::size_t decodedBytes, std::size_t occupiedSlots) const noexcept;
  void completed(std::uint64_t frame, double milliseconds, bool valid) noexcept;
  bool stopped() const noexcept { return stopped_; }
  double estimate_ms() const noexcept { return estimateMs_; }
 private:
  std::uint64_t lastFrame_{~std::uint64_t{0}};
  double estimateMs_{6.0};
  bool stopped_{};
};
}
