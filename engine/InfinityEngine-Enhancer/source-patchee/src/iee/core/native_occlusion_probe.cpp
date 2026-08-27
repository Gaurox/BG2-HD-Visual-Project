#include "iee/core/native_occlusion_probe.h"

#include <limits>

namespace iee::core {
void NativeOcclusionCorrelation::record_clipping(const NativeOcclusionCall& call) noexcept {
  if (owner_ == NativeOcclusionOwner::None) return;
  if (clippingCallCount_ != (std::numeric_limits<std::uint32_t>::max)()) {
    ++clippingCallCount_;
  }
  lastClippingCall_ = call;
}

std::optional<NativeOcclusionSample> NativeOcclusionCorrelation::correlate_draw(
    const NativeOcclusionDraw& draw) const noexcept {
  if (owner_ == NativeOcclusionOwner::None) return std::nullopt;
  return NativeOcclusionSample{
      .owner = owner_,
      .ownerKey = ownerKey_,
      .subjectId = subjectId_,
      .clippingCallCount = clippingCallCount_,
      .lastClippingCall = lastClippingCall_,
      .draw = draw,
  };
}

bool NativeOcclusionSampleGate::accept(const NativeOcclusionSample& sample) noexcept {
  const Key key{
      .owner = sample.owner,
      .ownerKey = sample.ownerKey,
      .subjectId = sample.subjectId,
      .clippingCallCount = sample.clippingCallCount,
      .clippingFlags = sample.lastClippingCall.flags,
      .clippingResult = sample.lastClippingCall.result,
      .dither = sample.lastClippingCall.dither,
      .drawFlags = sample.draw.flags,
      .logicalWidth = sample.draw.logicalWidth,
      .logicalHeight = sample.draw.logicalHeight,
      .replacement = sample.draw.replacement,
  };
  for (std::size_t index = 0; index < size_; ++index) {
    if (keys_[index] == key) return false;
  }
  if (size_ == keys_.size()) return false;
  keys_[size_++] = key;
  return true;
}

void NativeOcclusionSampleGate::clear() noexcept {
  keys_ = {};
  size_ = 0;
}
}  // namespace iee::core
