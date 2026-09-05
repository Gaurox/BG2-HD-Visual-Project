#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <vector>

namespace iee::core {
enum class NativeOcclusionOwner : std::uint8_t {
  None,
  AreaAnimation,
  Monster,
  MonsterIcewind,
  Character,
};

enum class NativeOcclusionReplacement : std::uint8_t {
  AreaRegistry,
  AreaPrototype,
  CreatureSprite,
};

struct NativeOcclusionCall {
  std::uintptr_t infinity{};
  int x{};
  int y{};
  int referenceZ{};
  std::uintptr_t fxRect{};
  std::uintptr_t clipRect{};
  std::uint8_t dither{};
  std::uint32_t flags{};
  int result{};
};

struct NativeOcclusionDraw {
  int x{};
  int y{};
  int logicalWidth{};
  int logicalHeight{};
  std::uint32_t flags{};
  int nativeTextureId{};
  NativeOcclusionReplacement replacement{NativeOcclusionReplacement::AreaRegistry};
};

struct NativeOcclusionSample {
  NativeOcclusionOwner owner{NativeOcclusionOwner::None};
  std::uintptr_t ownerKey{};
  std::uint64_t subjectId{};
  std::uint32_t clippingCallCount{};
  std::uint32_t successfulClippingCallCount{};
  NativeOcclusionCall lastClippingCall{};
  NativeOcclusionDraw draw{};

  [[nodiscard]] constexpr bool clipping_seen() const noexcept {
    return clippingCallCount != 0;
  }
};

// Correlates the native WED clipping pass with the final CVidCell draw inside one
// high-level world-object render invocation. It records metadata only: no pixels,
// OpenGL state, engine surfaces, or call arguments are changed.
class NativeOcclusionCorrelation {
 public:
  constexpr NativeOcclusionCorrelation(NativeOcclusionOwner owner,
                                       std::uintptr_t ownerKey,
                                       std::uint64_t subjectId) noexcept
      : owner_(owner), ownerKey_(ownerKey), subjectId_(subjectId) {}

  void record_clipping(const NativeOcclusionCall& call) noexcept;
  [[nodiscard]] std::optional<NativeOcclusionSample> correlate_draw(
      const NativeOcclusionDraw& draw) const noexcept;

 private:
  NativeOcclusionOwner owner_{NativeOcclusionOwner::None};
  std::uintptr_t ownerKey_{};
  std::uint64_t subjectId_{};
  std::uint32_t clippingCallCount_{};
  std::uint32_t successfulClippingCallCount_{};
  NativeOcclusionCall lastClippingCall_{};
};

struct NativeFxSurfaceView {
  const std::byte* pixels{};
  int pitchBytes{};
  int width{};
  int height{};
};

// Phase 1 captures pixels immediately before the first native WED clipping
// call and after the last call in the same owner scope. For the ordinary alpha
// kernels, the quotient post/pre is the native visibility transfer only;
// sprite alpha, translucency and palette realization cancel out instead of
// being applied twice to the xN backing.
//
// The capture is deliberately object-local and bounded. A changed surface,
// geometry mismatch, unreadable row, or oversized frame invalidates the whole
// capture and leaves the native/xN path untouched.
class NativeOcclusionMaskCapture {
 public:
  static constexpr std::size_t kMaximumPixels = 2u * 1024u * 1024u;

  [[nodiscard]] bool begin_call(const NativeFxSurfaceView& surface) noexcept;
  void finish_call(const NativeFxSurfaceView& surface, int nativeResult) noexcept;
  // Emits RGBA8 transfer texels: R is the alpha multiplier (including the
  // native complete-pixel clear); G is a fixed black-alpha replacement used by
  // the native 0x4F000000 dither kernel; B clears xN edge pixels in an adjacent
  // logical cell that was transparent in the x1 source. Any other RGB mutation
  // is rejected rather than approximated.
  [[nodiscard]] bool build_transfer(int logicalWidth, int logicalHeight,
                                    std::vector<std::uint8_t>& transfer,
                                    bool& changed) const noexcept;
  void invalidate() noexcept;

  [[nodiscard]] constexpr bool valid() const noexcept { return valid_; }
  [[nodiscard]] constexpr std::uint32_t successful_call_count() const noexcept {
    return successfulCallCount_;
  }
  [[nodiscard]] constexpr int width() const noexcept { return width_; }
  [[nodiscard]] constexpr int height() const noexcept { return height_; }

 private:
  [[nodiscard]] bool copy_pixels(const NativeFxSurfaceView& surface,
                                 std::vector<std::uint32_t>& destination) const noexcept;

  const std::byte* pixels_{};
  int pitchBytes_{};
  int width_{};
  int height_{};
  std::uint32_t successfulCallCount_{};
  bool valid_{true};
  bool initialized_{};
  bool callArmed_{};
  std::vector<std::uint32_t> before_{};
  std::vector<std::uint32_t> after_{};
};

// Phase 0 logging is deliberately bounded. One render thread retains at most
// 256 compact keys and emits only the first occurrence of an equivalent sample.
class NativeOcclusionSampleGate {
 public:
  static constexpr std::size_t kCapacity = 256;

  [[nodiscard]] bool accept(const NativeOcclusionSample& sample) noexcept;
  void clear() noexcept;
  [[nodiscard]] constexpr std::size_t size() const noexcept { return size_; }

 private:
  struct Key {
    NativeOcclusionOwner owner{NativeOcclusionOwner::None};
    std::uintptr_t ownerKey{};
    std::uint64_t subjectId{};
    std::uint32_t clippingCallCount{};
    std::uint32_t successfulClippingCallCount{};
    std::uint32_t clippingFlags{};
    int clippingResult{};
    std::uint8_t dither{};
    std::uint32_t drawFlags{};
    int logicalWidth{};
    int logicalHeight{};
    NativeOcclusionReplacement replacement{NativeOcclusionReplacement::AreaRegistry};

    [[nodiscard]] constexpr bool operator==(const Key&) const noexcept = default;
  };

  std::array<Key, kCapacity> keys_{};
  std::size_t size_{};
};
}  // namespace iee::core
