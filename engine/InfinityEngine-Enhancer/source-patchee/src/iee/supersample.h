#pragma once

namespace iee::supersample {

// Experimental 2x-per-axis supersampling of the complete frame. The engine
// renders into a 4x-pixel offscreen target between two swap boundaries, then
// the result is reduced to the real backbuffer for presentation.
bool configure(bool enabled) noexcept;
void before_swap() noexcept;
void after_swap() noexcept;
void shutdown() noexcept;

}  // namespace iee::supersample
