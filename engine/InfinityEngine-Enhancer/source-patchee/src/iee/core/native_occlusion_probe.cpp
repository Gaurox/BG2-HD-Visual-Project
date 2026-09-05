#include "iee/core/native_occlusion_probe.h"

#include <algorithm>
#include <cstring>
#include <limits>

#include "iee/core/pattern_scanner.h"

namespace iee::core {
void NativeOcclusionCorrelation::record_clipping(const NativeOcclusionCall& call) noexcept {
  if (owner_ == NativeOcclusionOwner::None) return;
  if (clippingCallCount_ != (std::numeric_limits<std::uint32_t>::max)()) {
    ++clippingCallCount_;
  }
  if (call.result != 0 &&
      successfulClippingCallCount_ != (std::numeric_limits<std::uint32_t>::max)()) {
    ++successfulClippingCallCount_;
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
      .successfulClippingCallCount = successfulClippingCallCount_,
      .lastClippingCall = lastClippingCall_,
      .draw = draw,
  };
}

bool NativeOcclusionMaskCapture::copy_pixels(
    const NativeFxSurfaceView& surface,
    std::vector<std::uint32_t>& destination) const noexcept {
  if (!surface.pixels || surface.width <= 0 || surface.height <= 0 ||
      surface.pitchBytes <= 0) {
    return false;
  }
  const auto width = static_cast<std::size_t>(surface.width);
  const auto height = static_cast<std::size_t>(surface.height);
  if (width > kMaximumPixels || height > kMaximumPixels ||
      width > kMaximumPixels / height ||
      width > static_cast<std::size_t>(surface.pitchBytes) / 4u) {
    return false;
  }
  const auto rowBytes = width * 4u;
  const auto pitch = static_cast<std::size_t>(surface.pitchBytes);
  if (height > 1 && pitch > ((std::numeric_limits<std::size_t>::max)() - rowBytes) /
                                (height - 1u)) {
    return false;
  }
  const auto readableBytes = pitch * (height - 1u) + rowBytes;
  if (!is_readable(surface.pixels, readableBytes)) return false;

  try {
    destination.resize(width * height);
    for (std::size_t y = 0; y < height; ++y) {
      const auto* source = surface.pixels + y * pitch;
      auto* output = destination.data() + y * width;
      for (std::size_t x = 0; x < width; ++x) {
        std::memcpy(output + x, source + x * 4u, sizeof(std::uint32_t));
      }
    }
    return true;
  } catch (...) {
    destination.clear();
    return false;
  }
}

bool NativeOcclusionMaskCapture::begin_call(
    const NativeFxSurfaceView& surface) noexcept {
  callArmed_ = false;
  if (!valid_) return false;
  if (!initialized_) {
    if (!copy_pixels(surface, before_)) {
      invalidate();
      return false;
    }
    pixels_ = surface.pixels;
    pitchBytes_ = surface.pitchBytes;
    width_ = surface.width;
    height_ = surface.height;
    try {
      after_ = before_;
    } catch (...) {
      invalidate();
      return false;
    }
    initialized_ = true;
  } else if (surface.pixels != pixels_ || surface.pitchBytes != pitchBytes_ ||
             surface.width != width_ || surface.height != height_) {
    invalidate();
    return false;
  }
  callArmed_ = true;
  return true;
}

void NativeOcclusionMaskCapture::finish_call(const NativeFxSurfaceView& surface,
                                             int nativeResult) noexcept {
  if (!valid_ || !callArmed_) return;
  callArmed_ = false;
  if (surface.pixels != pixels_ || surface.pitchBytes != pitchBytes_ ||
      surface.width != width_ || surface.height != height_ ||
      !copy_pixels(surface, after_)) {
    invalidate();
    return;
  }
  if (nativeResult != 0 &&
      successfulCallCount_ != (std::numeric_limits<std::uint32_t>::max)()) {
    ++successfulCallCount_;
  }
}

bool NativeOcclusionMaskCapture::build_transfer(
    int logicalWidth, int logicalHeight, std::vector<std::uint8_t>& transfer,
    bool& changed) const noexcept {
  transfer.clear();
  changed = false;
  if (!valid_ || !initialized_ || successfulCallCount_ == 0 ||
      logicalWidth != width_ || logicalHeight != height_ ||
      before_.size() != after_.size() || before_.empty()) {
    return false;
  }
  try {
    if (before_.size() >
        (std::numeric_limits<std::size_t>::max)() / 4u) {
      return false;
    }
    transfer.resize(before_.size() * 4u, 0u);
    for (std::size_t index = 0; index < before_.size(); ++index) {
      const auto beforePixel = before_[index];
      const auto afterPixel = after_[index];
      const auto before = static_cast<unsigned>(beforePixel >> 24u);
      const auto after = static_cast<unsigned>(afterPixel >> 24u);
      unsigned visibility = 255u;
      unsigned fixedBlackAlpha = 0u;
      if (afterPixel == 0u && beforePixel != 0u) {
        // The native 0x29D920/0x29D960 kernels clear the complete pixel for
        // fully occluded samples. Treat only that exact RGB mutation as a
        // supported zero-visibility operation.
        visibility = 0u;
      } else if (afterPixel == 0x4F000000u && beforePixel != afterPixel) {
        fixedBlackAlpha = 0x4Fu;
      } else if ((beforePixel & 0x00FFFFFFu) !=
                 (afterPixel & 0x00FFFFFFu)) {
        transfer.clear();
        changed = false;
        return false;
      } else if (before != 0u && after <= before) {
        visibility = std::min(255u, (after * 255u + before / 2u) / before);
      } else if (before != after) {
        transfer.clear();
        changed = false;
        return false;
      }
      const auto output = index * 4u;
      transfer[output + 0u] = static_cast<std::uint8_t>(visibility);
      transfer[output + 1u] = static_cast<std::uint8_t>(fixedBlackAlpha);
      // Keep the native source support temporarily. Edge-directed xN upscalers can
      // introduce colour/alpha in an adjacent logical cell whose x1 source was
      // transparent. The native clip cannot mutate that empty cell, so its ordinary
      // visibility remains 255 even when the contributing source pixel was cleared.
      transfer[output + 2u] = before == 0u ? 0xFFu : 0u;
      transfer[output + 3u] = 0xFFu;
      changed = changed || visibility != 255u || fixedBlackAlpha != 0u;
    }

    // Turn B into an exact one-cell expansion-clear marker. This is deliberately
    // narrower than dilating the WED mask: only x1-transparent cells touching an
    // exact native complete-pixel clear are affected. Native source pixels, partial
    // visibility and unoccluded xN edge smoothing keep their existing result.
    for (int y = 0; y < logicalHeight; ++y) {
      for (int x = 0; x < logicalWidth; ++x) {
        const auto index = static_cast<std::size_t>(y) *
                               static_cast<std::size_t>(logicalWidth) +
                           static_cast<std::size_t>(x);
        const auto output = index * 4u;
        if (transfer[output + 2u] == 0u) continue;

        bool touchesCompleteClear = false;
        for (int dy = -1; dy <= 1 && !touchesCompleteClear; ++dy) {
          const int neighbourY = y + dy;
          if (neighbourY < 0 || neighbourY >= logicalHeight) continue;
          for (int dx = -1; dx <= 1; ++dx) {
            const int neighbourX = x + dx;
            if (neighbourX < 0 || neighbourX >= logicalWidth) continue;
            const auto neighbour =
                (static_cast<std::size_t>(neighbourY) *
                     static_cast<std::size_t>(logicalWidth) +
                 static_cast<std::size_t>(neighbourX)) *
                4u;
            if (transfer[neighbour] == 0u) {
              touchesCompleteClear = true;
              break;
            }
          }
        }
        transfer[output + 2u] = touchesCompleteClear ? 0xFFu : 0u;
      }
    }
    return true;
  } catch (...) {
    transfer.clear();
    changed = false;
    return false;
  }
}

void NativeOcclusionMaskCapture::invalidate() noexcept {
  pixels_ = nullptr;
  pitchBytes_ = 0;
  width_ = 0;
  height_ = 0;
  successfulCallCount_ = 0;
  valid_ = false;
  initialized_ = false;
  callArmed_ = false;
  before_.clear();
  after_.clear();
}

bool NativeOcclusionSampleGate::accept(const NativeOcclusionSample& sample) noexcept {
  const Key key{
      .owner = sample.owner,
      .ownerKey = sample.ownerKey,
      .subjectId = sample.subjectId,
      .clippingCallCount = sample.clippingCallCount,
      .successfulClippingCallCount = sample.successfulClippingCallCount,
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
