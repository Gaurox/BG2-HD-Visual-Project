#pragma once

#include <filesystem>

#include "area_state.h"
#ifdef _WIN32
#include "iee/core/process_lifetime_worker.h"
#endif

namespace iee::bridge {

#ifdef _WIN32
namespace detail {
using ProcessLifetimeWorker = core::ProcessLifetimeWorker;

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
