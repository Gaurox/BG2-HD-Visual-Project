#include "process_resource_telemetry.h"

#include <limits>

#ifdef _WIN32
#include <windows.h>
#include <psapi.h>
#endif

namespace iee::core {

ProcessResourceSnapshot capture_process_resource_snapshot() noexcept {
  ProcessResourceSnapshot snapshot{};
#ifdef _WIN32
  const HANDLE process = GetCurrentProcess();
  PROCESS_MEMORY_COUNTERS_EX memory{};
  if (GetProcessMemoryInfo(process, reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&memory),
                           static_cast<DWORD>(sizeof(memory)))) {
    snapshot.memoryAvailable = true;
    snapshot.workingSetBytes = static_cast<std::uint64_t>(memory.WorkingSetSize);
    snapshot.peakWorkingSetBytes = static_cast<std::uint64_t>(memory.PeakWorkingSetSize);
    snapshot.privateBytes = static_cast<std::uint64_t>(memory.PrivateUsage);
    snapshot.pageFaults = static_cast<std::uint64_t>(memory.PageFaultCount);
  }

  IO_COUNTERS io{};
  if (GetProcessIoCounters(process, &io)) {
    snapshot.ioAvailable = true;
    snapshot.readOperations = io.ReadOperationCount;
    snapshot.readTransferBytes = io.ReadTransferCount;
    snapshot.writeOperations = io.WriteOperationCount;
    snapshot.writeTransferBytes = io.WriteTransferCount;
  }

  DWORD handleCount = 0;
  if (GetProcessHandleCount(process, &handleCount)) {
    snapshot.handlesAvailable = true;
    snapshot.handleCount = static_cast<std::uint64_t>(handleCount);
  }
#endif
  return snapshot;
}

std::int64_t signed_resource_delta(std::uint64_t before,
                                   std::uint64_t after) noexcept {
  constexpr auto maximum =
      static_cast<std::uint64_t>((std::numeric_limits<std::int64_t>::max)());
  if (after >= before) {
    const auto difference = after - before;
    return difference > maximum ? (std::numeric_limits<std::int64_t>::max)()
                                : static_cast<std::int64_t>(difference);
  }
  const auto difference = before - after;
  if (difference > maximum) return (std::numeric_limits<std::int64_t>::min)();
  return -static_cast<std::int64_t>(difference);
}

std::uint64_t monotonic_resource_delta(std::uint64_t before,
                                       std::uint64_t after) noexcept {
  return after >= before ? after - before : 0;
}

}  // namespace iee::core
