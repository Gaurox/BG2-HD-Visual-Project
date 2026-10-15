#pragma once
#include <algorithm>
#include <cstdint>
namespace iee::core {
// BG2EE 2.7.3 CVEFVidCell: source sequence flags are copied to +0x78;
// +0xCC is the continuous-sequences boolean, despite the EEex field name.
// +0xC0/+0xC4/+0xC8 contain one-based start/hold/current sequence.
constexpr bool effect_once_profile(std::uint32_t flags, int start, int loop, int current) noexcept {
  return (flags & 1u) == 0 || current != (loop > 0 ? loop : std::max(start, 1));
}
} // namespace iee::core
