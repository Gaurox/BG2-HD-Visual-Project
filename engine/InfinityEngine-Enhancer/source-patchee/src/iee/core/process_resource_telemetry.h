#pragma once

#include <cstdint>

namespace iee::core {

// Process-wide counters sampled only by opt-in performance diagnostics. Windows
// reports Working Set and private commit independently; I/O counters are
// cumulative for the process and do not distinguish cached from physical disk
// transfers.
struct ProcessResourceSnapshot {
  bool memoryAvailable{};
  bool ioAvailable{};
  bool handlesAvailable{};
  std::uint64_t workingSetBytes{};
  std::uint64_t peakWorkingSetBytes{};
  std::uint64_t privateBytes{};
  std::uint64_t pageFaults{};
  std::uint64_t readOperations{};
  std::uint64_t readTransferBytes{};
  std::uint64_t writeOperations{};
  std::uint64_t writeTransferBytes{};
  std::uint64_t handleCount{};
};

[[nodiscard]] ProcessResourceSnapshot capture_process_resource_snapshot() noexcept;

// Memory gauges may move in either direction. Clamp differences that cannot
// fit in a signed 64-bit log field rather than overflowing diagnostics.
[[nodiscard]] std::int64_t signed_resource_delta(std::uint64_t before,
                                                 std::uint64_t after) noexcept;

// Process counters should be monotonic. A lower value means a reset or wrap,
// which this diagnostic deliberately treats as an unavailable delta.
[[nodiscard]] std::uint64_t monotonic_resource_delta(std::uint64_t before,
                                                     std::uint64_t after) noexcept;

}  // namespace iee::core
