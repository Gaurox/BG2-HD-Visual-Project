#pragma once

#ifdef _WIN32

#include <process.h>
#include <windows.h>

#include <cstdint>
#include <type_traits>
#include <utility>

namespace iee::core {

// A DLL worker cannot be owned by a global std::thread: if the host terminates
// without calling ShutdownBindings, the CRT destroys a still-joinable thread
// under loader teardown and std::terminate issues FAST_FAIL_FATAL_APP_EXIT.
//
// This owner intentionally has a trivial destructor. start() also retains the
// module containing moduleAddress, so an unexpected FreeLibrary cannot unmap
// the worker's code. Normal shutdown must request the worker stop, call join(),
// release all worker-visible state, then call release_module_reference(). At
// process termination Windows reclaims both scalar handles without running
// unsafe synchronization from DllMain.
class ProcessLifetimeWorker {
 public:
  using Entry = unsigned(__stdcall*)(void*);

  enum class JoinResult : std::uint8_t {
    NotStarted,
    Joined,
    SelfJoinRejected,
    WaitFailed,
  };

  ProcessLifetimeWorker() noexcept = default;
  ProcessLifetimeWorker(const ProcessLifetimeWorker&) = delete;
  ProcessLifetimeWorker& operator=(const ProcessLifetimeWorker&) = delete;

  [[nodiscard]] bool start(Entry entry, void* context,
                           const void* moduleAddress) noexcept {
    if (thread_ || moduleReference_ || !entry || !moduleAddress) return false;

    HMODULE module = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,
                            reinterpret_cast<LPCWSTR>(moduleAddress), &module)) {
      return false;
    }

    const auto rawThread = _beginthreadex(nullptr, 0, entry, context, 0, nullptr);
    if (rawThread == 0) {
      FreeLibrary(module);
      return false;
    }

    moduleReference_ = module;
    thread_ = reinterpret_cast<HANDLE>(rawThread);
    return true;
  }

  [[nodiscard]] JoinResult join() noexcept {
    if (!thread_) return JoinResult::NotStarted;
    if (GetThreadId(thread_) == GetCurrentThreadId()) return JoinResult::SelfJoinRejected;
    if (WaitForSingleObject(thread_, INFINITE) != WAIT_OBJECT_0) return JoinResult::WaitFailed;
    CloseHandle(std::exchange(thread_, nullptr));
    return JoinResult::Joined;
  }

  [[nodiscard]] bool release_module_reference() noexcept {
    if (thread_) return false;
    if (HMODULE module = std::exchange(moduleReference_, nullptr)) FreeLibrary(module);
    return true;
  }

  [[nodiscard]] bool set_priority(int priority) noexcept {
    return thread_ && SetThreadPriority(thread_, priority) != FALSE;
  }

  [[nodiscard]] bool active() const noexcept { return thread_ != nullptr; }
  [[nodiscard]] bool holds_module_reference() const noexcept {
    return moduleReference_ != nullptr;
  }

 private:
  HANDLE thread_{};
  HMODULE moduleReference_{};
};

static_assert(std::is_trivially_destructible_v<ProcessLifetimeWorker>);

}  // namespace iee::core

#endif
