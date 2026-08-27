#pragma once

#include <array>

namespace iee::area_animation_clock {

// PerformanceLogs controls this diagnostic together with the existing frame
// presentation measurements. It never changes animation frame selection.
void configure(bool enabled) noexcept;
void request_area_generation() noexcept;
void observe(void* instance, const std::array<char, 8>& resref, int sequence, int slot,
             int worldActive) noexcept;
void shutdown() noexcept;

}  // namespace iee::area_animation_clock
