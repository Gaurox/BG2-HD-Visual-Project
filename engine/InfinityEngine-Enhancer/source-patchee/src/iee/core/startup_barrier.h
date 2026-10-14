#pragma once

#include <windows.h>

namespace iee::core {
// An export may wait outside the publication lock while ShutdownBindings
// takes ownership of the original thread handle. Keep a private wait handle.
class StartupWaitHandle {
 public:
  StartupWaitHandle() noexcept = default;
  StartupWaitHandle(const StartupWaitHandle&) = delete;
  StartupWaitHandle& operator=(const StartupWaitHandle&) = delete;
  ~StartupWaitHandle() { if (handle_) CloseHandle(handle_); }

  bool capture(HANDLE thread) noexcept {
    if (!thread || handle_) return false;
    return DuplicateHandle(GetCurrentProcess(), thread, GetCurrentProcess(), &handle_,
                           SYNCHRONIZE, FALSE, 0) != FALSE;
  }
  bool captured() const noexcept { return handle_ != nullptr; }
  bool wait() const noexcept {
    return handle_ && WaitForSingleObject(handle_, INFINITE) == WAIT_OBJECT_0;
  }

 private:
  HANDLE handle_{};
};
}  // namespace iee::core
