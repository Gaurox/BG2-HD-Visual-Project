#pragma once

namespace iee {
struct AppContext;
}

namespace iee::map_page_prewarm {
using PvrDemandFn = void* (*)(void*);

// Installs the exact manifested native Demand entry used by the runtime
// scheduler. A null entry leaves the experiment unavailable and preserves the
// engine's ordinary synchronous path.
void configure(PvrDemandFn demand) noexcept;

// LoadArea may run outside the presentation callback. It only requests a
// reset; all wrapper traversal and PVR demands remain on the render thread.
void request_area_reset() noexcept;

// Called after swap and post-processing state restoration, while the WGL
// context still belongs to the engine render thread.
void on_post_swap(AppContext& ctx) noexcept;

void shutdown() noexcept;
}  // namespace iee::map_page_prewarm
