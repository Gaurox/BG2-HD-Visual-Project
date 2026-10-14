#include <windows.h>

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "iee/core/hooking.h"

namespace {
using Function = int (*)();
int replacement() { return 99; }

// Reserve address space, not physical RAM. Reproduce the precise MinHook
// failure when a large CPU payload has filled the near-image search window.
struct AddressPressure {
  std::vector<void*> reservations;
  explicit AddressPressure(void* target) {
    SYSTEM_INFO info{};
    GetSystemInfo(&info);
    const auto origin = reinterpret_cast<std::uintptr_t>(target);
    constexpr std::uintptr_t range = 0x40000000;  // MinHook's actual search range.
    auto address = origin - range - info.dwAllocationGranularity;
    address -= address % info.dwAllocationGranularity;
    const auto end = origin + range + info.dwAllocationGranularity;
    while (address < end) {
      MEMORY_BASIC_INFORMATION region{};
      if (!VirtualQuery(reinterpret_cast<void*>(address), &region, sizeof(region)))
        throw std::runtime_error("VirtualQuery failed");
      const auto next = reinterpret_cast<std::uintptr_t>(region.BaseAddress) + region.RegionSize;
      if (region.State == MEM_FREE) {
        auto begin = address + info.dwAllocationGranularity - 1;
        begin -= begin % info.dwAllocationGranularity;
        const auto limit = (std::min)(next, end);
        if (begin < limit) {
          void* reservation = VirtualAlloc(reinterpret_cast<void*>(begin), limit - begin,
                                           MEM_RESERVE, PAGE_NOACCESS);
          if (!reservation) throw std::runtime_error("pressure reservation failed");
          reservations.push_back(reservation);
        }
      }
      if (next <= address) throw std::runtime_error("non-progressing memory region");
      address = next;
    }
  }
  ~AddressPressure() {
    for (void* reservation : reservations) VirtualFree(reservation, 0, MEM_RELEASE);
  }
};

bool exercise(bool reserveEarly) {
  // This address range models the game's low-address image. The test never
  // attaches to or writes memory in any other process.
  auto* target = static_cast<unsigned char*>(VirtualAlloc(
      reinterpret_cast<void*>(0x140000000ull), 0x10000,
      MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE));
  if (!target) throw std::runtime_error("synthetic image allocation failed");
  const unsigned char first[] = {0xB8, 42, 0, 0, 0, 0xC3};
  const unsigned char second[] = {0xB8, 24, 0, 0, 0, 0xC3};
  std::memcpy(target, first, sizeof(first));
  std::memcpy(target + 64, second, sizeof(second));
  FlushInstructionCache(GetCurrentProcess(), target, 128);
  bool passed = false;
  {
    iee::core::HookInit init;
    iee::core::Hook<Function> firstHook;
    iee::core::Hook<Function> secondHook;
    try {
      if (reserveEarly) firstHook.create(target, reinterpret_cast<void*>(&replacement));
      AddressPressure pressure(target);
      if (reserveEarly) {
        // Reserving the first disabled hook keeps MinHook's near-image pool
        // available for later hooks after the large payload has been loaded.
        secondHook.create(target + 64, reinterpret_cast<void*>(&replacement));
        passed = reinterpret_cast<Function>(target)() == 42;
        firstHook.enable();
        secondHook.enable();
        passed = passed && reinterpret_cast<Function>(target)() == 99 &&
                 reinterpret_cast<Function>(target + 64)() == 99 &&
                 firstHook.original()() == 42 && secondHook.original()() == 24;
      } else {
        try {
          firstHook.create(target, reinterpret_cast<void*>(&replacement));
        } catch (const std::runtime_error& error) {
          passed = std::string(error.what()).find("MH_ERROR_MEMORY_ALLOC") != std::string::npos;
        }
      }
      (void)secondHook.remove();
      (void)firstHook.remove();
    } catch (...) {
      (void)secondHook.remove();
      (void)firstHook.remove();
      VirtualFree(target, 0, MEM_RELEASE);
      throw;
    }
  }
  VirtualFree(target, 0, MEM_RELEASE);
  return passed;
}
}  // namespace

int main() {
  try {
    if (!exercise(false) || !exercise(true)) return 1;
    std::cout << "Late hook reproduces MH_ERROR_MEMORY_ALLOC; early disabled hook reservation "
                 "survives full near-image address pressure; original and detoured calls passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
