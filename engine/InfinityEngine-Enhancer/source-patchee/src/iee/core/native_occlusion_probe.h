#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

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
  NativeOcclusionCall lastClippingCall_{};
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
