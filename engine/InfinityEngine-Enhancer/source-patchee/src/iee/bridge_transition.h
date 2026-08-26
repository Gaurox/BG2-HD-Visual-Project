#pragma once

#include <filesystem>

#ifdef _WIN32
#include <process.h>
#include <windows.h>

#include <cstdint>
#include <type_traits>
#include <utility>
#endif

#include "area_state.h"

namespace iee::bridge {

#ifdef _WIN32
namespace detail {

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

  [[nodiscard]] bool start(Entry entry, void* context, const void* moduleAddress) noexcept {
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

    // Publish both values only after every fallible operation succeeded. The
    // module reference remains held until explicit post-join cleanup.
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

  // Releasing the self-reference while executable worker code remains would
  // reintroduce an unload/use-after-free race. Fail closed if join() did not
  // complete; the reference is intentionally retained until process exit.
  [[nodiscard]] bool release_module_reference() noexcept {
    if (thread_) return false;
    if (HMODULE module = std::exchange(moduleReference_, nullptr)) FreeLibrary(module);
    return true;
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

}  // namespace detail
#endif

// Prepares the optional AR1300 bridge-transition preview. Video decoding runs
// on a worker; all OpenGL work remains on the render thread.
bool prepare(const std::filesystem::path& assetDirectory) noexcept;

// Receives the coherent world transform from the Seam render callback.  The
// caller supplies the area match so this module never displays a stale bridge
// over a newly loaded area.
void publish_view(const area::ViewTransform& view, bool isAr1300) noexcept;

// Observes the actual AR1300 WED tile variant selected by BRIDGE01. A state
// edge starts the matching direction; another edge reverses from the currently
// displayed logical frame.
void observe_rendered_tile(int tileIndex) noexcept;
void reset_area() noexcept;

// Starts an opening playback from the closed endpoint. This remains exported
// and bound to F9 as a diagnostic; normal gameplay follows the rendered door.
bool request() noexcept;

// Called at the end of CGameArea::Render while the engine's scaled map
// framebuffer is still bound. DrawEndScaled resolves the result afterward, so
// the bridge remains part of the map and below every HUD or full-screen menu.
void render_world_overlay() noexcept;

void shutdown() noexcept;

}  // namespace iee::bridge
