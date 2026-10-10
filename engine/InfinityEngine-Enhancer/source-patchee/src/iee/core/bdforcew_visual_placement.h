#pragma once

#include "iee/core/native_occlusion_probe.h"
#include <limits>
#include <string_view>

namespace iee::core {
// User-authorized non-vanilla visual placement, after native WED masking.
// Native world coordinates, BAM centres, collision and save state stay intact.
inline int bdforcew_visual_draw_x(const NativeOcclusionSample& sample,
                                 std::string_view area, bool masked,
                                 int originalX) noexcept {
  const auto& clip = sample.lastClippingCall;
  const bool occurrence = (clip.x == 2286 && clip.y == 820) ||
                          (clip.x == 2350 && clip.y == 866);
  if (!masked || area != "OH8100" || !occurrence ||
      sample.owner != NativeOcclusionOwner::AreaAnimation ||
      sample.subjectId != 0x574543524F464442ull ||
      sample.draw.replacement != NativeOcclusionReplacement::AreaRegistry ||
      sample.successfulClippingCallCount == 0 || clip.dither != 0 ||
      originalX > std::numeric_limits<int>::max() - 6) return originalX;
  return originalX + 6;
}
}  // namespace iee::core
