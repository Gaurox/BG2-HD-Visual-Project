#pragma once

#include <cstddef>
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

// The first detected wide-view expansion ends background preparation for the
// current area. Queued/ready work is released without blocking presentation;
// an active file reader retains the existing native-fallback handshake.
void notify_wide_view_expansion() noexcept;

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
  std::uint32_t claimOrdinal{};
  std::uint32_t claimLimit{};
  PvrConsumeOutcome outcome{PvrConsumeOutcome::NotReached};
  std::uint64_t crcNanoseconds{};
  std::uint64_t copyNanoseconds{};
};

// Read-only Phase 3e-B2c correlation for one planned PVR object. It exposes
// only the project's own scheduler state; no native resource field is
// interpreted or modified.
struct PvrLifecycleSnapshot {
  core::ShadowPageIdentity identity{};
  std::uint32_t claims{};
  std::uint32_t claimLimit{};
  std::size_t pendingPages{};
  std::size_t inFlightPages{};
  std::uint64_t nativeFallbackWaits{};
  std::size_t completedPages{};
  std::size_t completedBytes{};
};

// Called immediately before an unloaded native PVR demand. Shadow-only mode
// observes and retires the buffer. A bounded diagnostic may move a fixed small
// number of ready pages out of the queue for their exact Demand and generation.
[[nodiscard]] std::optional<PvrConsumeAttempt> begin_native_demand(void* pvr) noexcept;

[[nodiscard]] std::optional<PvrLifecycleSnapshot> lifecycle_snapshot(void* pvr) noexcept;

// Records one bounded-consume result after native Demand has resumed through
// its ordinary parse/publish/upload/free path.
void record_consume_attempt(const PvrConsumeAttempt& attempt,
                            std::uint64_t demandNanoseconds) noexcept;

void shutdown() noexcept;
}  // namespace iee::map_page_prewarm
