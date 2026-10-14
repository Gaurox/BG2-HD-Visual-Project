#pragma once

#include <cstddef>
#include <cstdint>

#include "iee/game/active_area_runtime.h"

namespace iee::game {
// Render-thread state. The native renderer consumes bRefreshVRamRect once;
// never set it every frame or alter the camera/zoom to invalidate its cache.
class AreaRedrawRequest {
 public:
  template <class Reader, class Writer>
  bool request(CGameArea* rendered, const BuildManifest& manifest,
               std::uint64_t loadGeneration, Reader&& read, Writer&& write) {
    if (!resolve_rendered_area_owner(rendered, manifest, read)) return false;
    CResWED* wed = nullptr;
    const auto* areaBytes = reinterpret_cast<const std::byte*>(rendered);
    if (!read(areaBytes + offsetof(CGameArea, m_pResWED), wed) || !wed) return false;
    if (rendered == area_ && wed == wed_ && loadGeneration == generation_) return false;

    auto* infinity = reinterpret_cast<std::byte*>(rendered) + offsetof(CGameArea, m_cInfinity);
    CGameArea* owner = nullptr;
    CResWED* infinityWed = nullptr;
    std::int32_t initialized = 0;
    if (!read(infinity + offsetof(CInfinity, m_pArea), owner) || owner != rendered ||
        !read(infinity + offsetof(CInfinity, pResWED), infinityWed) || infinityWed != wed ||
        !read(infinity + offsetof(CInfinity, bInitialized), initialized) || !initialized) {
      return false;
    }
    const std::int32_t refresh = 1;
    if (!write(infinity + offsetof(CInfinity, bRefreshVRamRect), refresh)) return false;
    area_ = rendered;
    wed_ = wed;
    generation_ = loadGeneration;
    return true;
  }

 private:
  CGameArea* area_{};
  CResWED* wed_{};
  std::uint64_t generation_{};
};
}  // namespace iee::game
