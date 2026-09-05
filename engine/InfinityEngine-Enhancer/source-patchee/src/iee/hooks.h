#pragma once
#include "app_context.h"

namespace iee::hooks {
bool install_all(AppContext& ctx);

void uninstall_all() noexcept;

// Disables engine entry-point hooks without uninitializing MinHook. The
// caller must remove other MinHook-backed subsystems, then call
// uninstall_all().
void prepare_for_shutdown() noexcept;

// Render-thread retry point used by the frame boundary. Probe recovery must
// not depend on successful tile decoding or a later RenderTexture call.
void retry_shader_probe_install() noexcept;

// Presentation-boundary publication for the buffered map wide-view burst
// diagnostic. `frame` is the completed frame, before frame_count advances.
void on_frame_boundary(unsigned long long frame,
                       double presentationIntervalMilliseconds) noexcept;

// Render-thread callback after presentation and post-process restoration.
// Experimental page prewarm runs here so no mid-draw binding is disturbed.
void on_post_swap() noexcept;

bool is_active();
}  // namespace iee::hooks
