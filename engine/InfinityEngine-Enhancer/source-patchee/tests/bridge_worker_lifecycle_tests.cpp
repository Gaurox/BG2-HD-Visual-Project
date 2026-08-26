#include <atomic>
#include <iostream>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

#include "iee/bridge_transition.h"

namespace {

int g_failures{};
iee::bridge::detail::ProcessLifetimeWorker g_processExitWorker;

void expect(bool condition, const char* message) {
  if (condition) return;
  ++g_failures;
  std::cerr << "FAIL: " << message << '\n';
}

struct WorkerContext {
  HANDLE entered{};
  HANDLE release{};
};

unsigned __stdcall worker_entry(void* opaque) {
  auto& context = *static_cast<WorkerContext*>(opaque);
  SetEvent(context.entered);
  (void)WaitForSingleObject(context.release, INFINITE);
  return 0;
}

struct SelfJoinContext {
  iee::bridge::detail::ProcessLifetimeWorker* worker{};
  HANDLE proceed{};
  std::atomic<int> result{-1};
};

unsigned __stdcall self_join_entry(void* opaque) {
  auto& context = *static_cast<SelfJoinContext*>(opaque);
  (void)WaitForSingleObject(context.proceed, INFINITE);
  context.result.store(static_cast<int>(context.worker->join()), std::memory_order_release);
  return 0;
}

void test_explicit_worker_lifecycle() {
  using Worker = iee::bridge::detail::ProcessLifetimeWorker;
  using JoinResult = Worker::JoinResult;

  // This is the regression gate for the exit crash: no destructor may call
  // std::terminate or synchronize while the CRT is under loader teardown.
  static_assert(std::is_trivially_destructible_v<Worker>);

  Worker worker;
  expect(!worker.active() && !worker.holds_module_reference(), "worker starts inert");

  WorkerContext context{
      CreateEventW(nullptr, TRUE, FALSE, nullptr),
      CreateEventW(nullptr, TRUE, FALSE, nullptr),
  };
  expect(context.entered != nullptr && context.release != nullptr, "test events are available");
  if (!context.entered || !context.release) {
    if (context.entered) CloseHandle(context.entered);
    if (context.release) CloseHandle(context.release);
    return;
  }

  // FROM_ADDRESS requires an address in the image, not the stack-owned worker.
  const bool started = worker.start(&worker_entry, &context, &g_failures);
  expect(started, "worker starts with a module lifetime reference");
  if (!started) {
    CloseHandle(context.entered);
    CloseHandle(context.release);
    return;
  }

  expect(WaitForSingleObject(context.entered, 5000) == WAIT_OBJECT_0,
         "worker entered its callback");
  expect(worker.active() && worker.holds_module_reference(),
         "active worker retains its code module");
  expect(!worker.start(&worker_entry, &context, &g_failures), "second start is rejected");
  expect(!worker.release_module_reference(), "module release before join is rejected");

  SetEvent(context.release);
  expect(worker.join() == JoinResult::Joined, "worker joins outside loader lock");
  expect(!worker.active() && worker.holds_module_reference(),
         "module stays retained through post-join shared-state cleanup");
  expect(worker.join() == JoinResult::NotStarted, "join is idempotent");
  expect(worker.release_module_reference() && !worker.holds_module_reference(),
         "module reference releases after join");
  expect(worker.release_module_reference(), "module release is idempotent");

  CloseHandle(context.entered);
  CloseHandle(context.release);
}

void test_worker_self_join_fails_closed() {
  using Worker = iee::bridge::detail::ProcessLifetimeWorker;
  using JoinResult = Worker::JoinResult;

  Worker worker;
  SelfJoinContext context{&worker, CreateEventW(nullptr, TRUE, FALSE, nullptr)};
  expect(context.proceed != nullptr, "self-join test event is available");
  if (!context.proceed) return;

  const bool started = worker.start(&self_join_entry, &context, &g_failures);
  expect(started, "self-join test worker starts");
  if (!started) {
    CloseHandle(context.proceed);
    return;
  }
  SetEvent(context.proceed);
  expect(worker.join() == JoinResult::Joined, "main thread can join after rejected self-join");
  expect(context.result.load(std::memory_order_acquire) ==
             static_cast<int>(JoinResult::SelfJoinRejected),
         "worker self-join is rejected without discarding ownership");
  expect(worker.release_module_reference(), "self-join test module reference releases");
  CloseHandle(context.proceed);
}

int run_process_exit_child() {
  WorkerContext context{
      CreateEventW(nullptr, TRUE, FALSE, nullptr),
      CreateEventW(nullptr, TRUE, FALSE, nullptr),
  };
  if (!context.entered || !context.release) return 2;
  if (!g_processExitWorker.start(&worker_entry, &context, &g_failures)) return 3;
  if (WaitForSingleObject(context.entered, 5000) != WAIT_OBJECT_0) return 4;

  // Intentionally return with an active worker. ProcessLifetimeWorker's
  // trivial destructor must not reproduce std::thread's terminate-on-exit.
  return 0;
}

void test_active_worker_process_exit() {
  std::vector<wchar_t> executable(32768);
  const DWORD length =
      GetModuleFileNameW(nullptr, executable.data(), static_cast<DWORD>(executable.size()));
  expect(length != 0 && length < executable.size(), "test executable path is available");
  if (length == 0 || length >= executable.size()) return;

  std::wstring command = L"\"" + std::wstring(executable.data(), length) +
                         L"\" --abandon-worker-at-process-exit";
  std::vector<wchar_t> mutableCommand(command.begin(), command.end());
  mutableCommand.push_back(L'\0');

  STARTUPINFOW startup{};
  startup.cb = sizeof(startup);
  PROCESS_INFORMATION process{};
  const BOOL created = CreateProcessW(nullptr, mutableCommand.data(), nullptr, nullptr, FALSE, 0,
                                      nullptr, nullptr, &startup, &process);
  expect(created != FALSE, "process-exit regression child starts");
  if (!created) return;

  const DWORD wait = WaitForSingleObject(process.hProcess, 10000);
  DWORD exitCode = STILL_ACTIVE;
  if (wait == WAIT_OBJECT_0) (void)GetExitCodeProcess(process.hProcess, &exitCode);
  expect(wait == WAIT_OBJECT_0, "process-exit regression child terminates");
  expect(exitCode == 0, "active worker does not trigger FAST_FAIL_FATAL_APP_EXIT");
  if (wait != WAIT_OBJECT_0) TerminateProcess(process.hProcess, 5);
  CloseHandle(process.hThread);
  CloseHandle(process.hProcess);
}

}  // namespace

int main(int argc, char** argv) {
  if (argc == 2 && std::string_view(argv[1]) == "--abandon-worker-at-process-exit") {
    return run_process_exit_child();
  }
  test_explicit_worker_lifecycle();
  test_worker_self_join_fails_closed();
  test_active_worker_process_exit();
  if (g_failures != 0) {
    std::cerr << g_failures << " bridge worker lifecycle test(s) failed\n";
    return 1;
  }
  std::cout << "All bridge worker lifecycle tests passed\n";
  return 0;
}
