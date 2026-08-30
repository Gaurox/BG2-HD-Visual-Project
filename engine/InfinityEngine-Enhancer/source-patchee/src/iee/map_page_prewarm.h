#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>

#include "iee/core/map_page_shadow.h"

namespace iee {
struct AppContext;
}

namespace iee::map_page_prewarm {
using PvrDemandFn = void* (*)(void*);

// Installs the exact manifested native Demand entry used by the runtime
// scheduler. A null entry leaves the experiment unavailable and preserves the
// engine's ordinary synchronous path.
void configure(PvrDemandFn demand) noexcept;

// Starts/stops the phase 3e-A CPU-only worker. The directory is restricted to
// explicit override PVRZ files; missing resources retain native fallback.
[[nodiscard]] bool configure_shadow(bool enabled, bool consumeEnabled,
                                    const std::filesystem::path& resourceDirectory) noexcept;

// LoadArea may run outside the presentation callback. It only requests a
// reset; all wrapper traversal and PVR demands remain on the render thread.
void request_area_reset() noexcept;

// Called after swap and post-processing state restoration, while the WGL
// context still belongs to the engine render thread.
void on_post_swap(AppContext& ctx) noexcept;

enum class PvrConsumeOutcome : std::uint8_t {
  NotReached,
  Consumed,
  UnexpectedReturnAddress,
  ResourceMismatch,
  SourceMismatch,
  SizeMismatch,
  CrcMismatch,
  MemoryRejected,
  InternalError,
};

struct PvrConsumeAttempt {
  void* resource{};
  core::ShadowPageIdentity identity{};
  core::PvrzPreparedPage page{};
  PvrConsumeOutcome outcome{PvrConsumeOutcome::NotReached};
  std::uint64_t crcNanoseconds{};
  std::uint64_t copyNanoseconds{};
};

// Called immediately before an unloaded native PVR demand. Shadow-only mode
// observes and retires the buffer. B1 mode may move one ready page out of the
// queue for this exact Demand and area generation.
[[nodiscard]] std::optional<PvrConsumeAttempt> begin_native_demand(void* pvr) noexcept;

// Records the single canary result after native Demand has resumed through its
// ordinary parse/publish/upload/free path.
void record_consume_attempt(const PvrConsumeAttempt& attempt,
                            std::uint64_t demandNanoseconds) noexcept;

void shutdown() noexcept;
}  // namespace iee::map_page_prewarm
