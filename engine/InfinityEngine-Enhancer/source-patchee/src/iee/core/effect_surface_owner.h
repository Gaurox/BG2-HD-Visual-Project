#pragma once
#include <array>
#include <cstdint>

namespace iee::core {
enum class EffectSurfaceLayout { SourcePlacement, CroppedSource, NativeOnly };
// SPMAGMIS's existing pack is already contained at y=7 in the final64x78
// canvas (effects/runtime-geometry/SPMAGMIS-v1.json). Its native cell is64x64.
// Resolve the pack64x78, remove its seven padding rows at each end in memory,
// and place the native64x64 content on the actual variable FX canvas.
// A captured prefix has a different layout contract and stays native here.
[[nodiscard]] constexpr EffectSurfaceLayout effect_surface_layout(
    const std::array<char,8>& ref, int sourceWidth, int sourceHeight,
    bool composed) noexcept {
  if (ref==std::array<char,8>{'S','P','M','A','G','M','I','S'} &&
      sourceWidth==64 && sourceHeight==64)
    return composed ? EffectSurfaceLayout::NativeOnly : EffectSurfaceLayout::CroppedSource;
  return EffectSurfaceLayout::SourcePlacement;
}

[[nodiscard]] constexpr std::array<int,2> effect_frame_lookup_size(
    const std::array<char,8>& ref,int width,int height) noexcept {
  return effect_surface_layout(ref,width,height,false)==EffectSurfaceLayout::CroppedSource
      ? std::array<int,2>{64,78} : std::array<int,2>{width,height};
}

// One native FX pass. Multiple submissions (including the same cell twice)
// cannot be replaced by a single pre-rendered texture without losing layers.
// candidate_cell is separate: it requires a captured native prefix at the caller.
class EffectSurfaceOwner {
 public:
  void begin(std::uintptr_t surface) noexcept { surface_=surface; cell_=0; last_=0; submissions_=0; }
  void submit(std::uintptr_t surface, std::uintptr_t cell, bool registered) noexcept {
    if (!surface_ || surface != surface_) { begin(0); return; }
    if (submissions_ < 9) ++submissions_;
    cell_ = submissions_ == 1 && registered ? cell : 0;
    last_ = submissions_ <= 8 && registered ? cell : 0;
  }
  [[nodiscard]] std::uintptr_t cell(std::uintptr_t surface) const noexcept {
    return surface && surface == surface_ && submissions_ == 1 ? cell_ : 0;
  }
  [[nodiscard]] std::uintptr_t pending_cell() const noexcept {
    return submissions_ == 1 ? cell_ : 0;
  }
  // A captured native prefix can accompany the LAST registered layer. A native
  // overlay after it, a ninth layer or an unrelated FX pass must fail closed.
  [[nodiscard]] std::uintptr_t candidate_cell(std::uintptr_t surface) const noexcept {
    return surface && surface == surface_ ? last_ : 0;
  }
  [[nodiscard]] std::uintptr_t pending_candidate() const noexcept { return last_; }
  [[nodiscard]] unsigned submissions() const noexcept { return submissions_; }
  void clear() noexcept { begin(0); }
 private:
  std::uintptr_t surface_{}, cell_{}, last_{};
  unsigned submissions_{};
};
}
