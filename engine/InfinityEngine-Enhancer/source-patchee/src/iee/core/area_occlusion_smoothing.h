#pragma once

#include "iee/core/native_occlusion_probe.h"
#include <string_view>

namespace iee::core {
inline bool area_occlusion_smoothing_enabled(const NativeOcclusionSample& sample,
                                             std::string_view area) noexcept {
  if (sample.owner != NativeOcclusionOwner::AreaAnimation ||
      sample.draw.replacement != NativeOcclusionReplacement::AreaRegistry ||
      sample.lastClippingCall.dither != 0) return false;
  // Preserve the accepted BDFORCEW treatment exactly.
  if (sample.subjectId == 0x574543524F464442ull) return true;
  // The AR0517 foreground arch, only at this SPHINCT occurrence.
  return area == "AR0517" && sample.subjectId == 0x0054434E49485053ull &&
         sample.successfulClippingCallCount > 0 &&
         sample.lastClippingCall.x == 497 && sample.lastClippingCall.y == 452;
}
}  // namespace iee::core
