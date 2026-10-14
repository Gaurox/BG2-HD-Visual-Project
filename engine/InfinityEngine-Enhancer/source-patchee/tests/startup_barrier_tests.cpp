#include <windows.h>

#include <atomic>
#include <iostream>

#include "iee/core/startup_barrier.h"

namespace {
struct Context {
  HANDLE entered = CreateEventW(nullptr, TRUE, FALSE, nullptr);
  HANDLE release = CreateEventW(nullptr, TRUE, FALSE, nullptr);
  HANDLE waiting = CreateEventW(nullptr, TRUE, FALSE, nullptr);
  HANDLE resumed = CreateEventW(nullptr, TRUE, FALSE, nullptr);
  iee::core::StartupWaitHandle barrier;
  std::atomic<bool> assetsReady{false};
  std::atomic<bool> resumedReady{false};
  ~Context() {
    for (HANDLE handle : {entered, release, waiting, resumed}) if (handle) CloseHandle(handle);
  }
};

DWORD WINAPI initialize(LPVOID opaque) {
  auto& context = *static_cast<Context*>(opaque);
  SetEvent(context.entered);
  if (WaitForSingleObject(context.release, 5000) != WAIT_OBJECT_0) return 1;
  context.assetsReady.store(true, std::memory_order_release);
  return 0;
}

DWORD WINAPI host_startup(LPVOID opaque) {
  auto& context = *static_cast<Context*>(opaque);
  SetEvent(context.waiting);
  const bool completed = context.barrier.wait();
  context.resumedReady.store(completed && context.assetsReady.load(std::memory_order_acquire));
  SetEvent(context.resumed);
  return 0;
}
}  // namespace

int main() {
  iee::core::StartupWaitHandle empty;
  if (empty.capture(nullptr) || empty.wait()) return 1;
  Context context;
  if (!context.entered || !context.release || !context.waiting || !context.resumed) return 1;
  HANDLE worker = CreateThread(nullptr, 0, initialize, &context, 0, nullptr);
  if (!worker || !context.barrier.capture(worker)) return 1;
  if (context.barrier.capture(worker)) return 1;
  HANDLE host = CreateThread(nullptr, 0, host_startup, &context, 0, nullptr);
  if (!host) return 1;
  const bool began = WaitForSingleObject(context.entered, 5000) == WAIT_OBJECT_0 &&
                     WaitForSingleObject(context.waiting, 5000) == WAIT_OBJECT_0;
  const bool held = WaitForSingleObject(context.resumed, 40) == WAIT_TIMEOUT;
  // Explicit shutdown can take and close its owner handle independently;
  // the export's private wait handle must remain usable until completion.
  CloseHandle(worker);
  SetEvent(context.release);
  const bool completed = WaitForSingleObject(host, 5000) == WAIT_OBJECT_0;
  CloseHandle(host);
  if (!began || !held || !completed || !context.resumedReady.load()) return 1;
  std::cout << "Host startup cannot resume before CPU assets and hooks are ready; "
               "private wait survives owner-handle closure; null and duplicate capture rejected\n";
  return 0;
}
