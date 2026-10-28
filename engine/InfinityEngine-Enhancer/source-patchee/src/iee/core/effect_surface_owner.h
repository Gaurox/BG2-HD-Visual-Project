#pragma once
#include <cstdint>

namespace iee::core {
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
