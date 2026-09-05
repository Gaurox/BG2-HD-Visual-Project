#pragma once

namespace iee::post {

// Diagnostic full-frame FXAA pass. It runs at the validated swap boundary, so
// it intentionally affects both the world and the UI until a world/UI bracket
// is implemented.
void configure(bool enabled) noexcept;
void apply_frame_fxaa() noexcept;
void release_resources() noexcept;

}  // namespace iee::post
