#pragma once

#include <filesystem>

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
[[nodiscard]] bool configure_shadow(bool enabled,
                                    const std::filesystem::path& resourceDirectory) noexcept;

// LoadArea may run outside the presentation callback. It only requests a
// reset; all wrapper traversal and PVR demands remain on the render thread.
void request_area_reset() noexcept;

// Called after swap and post-processing state restoration, while the WGL
// context still belongs to the engine render thread.
void on_post_swap(AppContext& ctx) noexcept;

// Called immediately before an unloaded native PVR demand. It only records
// whether the immutable shadow result was ready and retires that CPU buffer.
void observe_native_demand(void* pvr) noexcept;

void shutdown() noexcept;
}  // namespace iee::map_page_prewarm
