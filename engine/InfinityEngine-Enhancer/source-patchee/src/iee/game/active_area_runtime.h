#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "iee/game/build_manifest.h"
#include "iee/game/runtime_types_x64.h"

namespace iee::game {
// Reader must reject unreadable engine memory; this resolver never dereferences it directly.
template <class Reader>
const CGameArea* read_loaded_area_candidate(const CGameArea* area, Reader&& read) {
  std::uint8_t flag = 0;
  return area && read(reinterpret_cast<const std::byte*>(area) +
                          offsetof(CGameArea, m_bAreaLoaded), flag) && flag != 0
             ? area : nullptr;
}

template <class Reader>
const CGameArea* resolve_active_area(void* infGame, const BuildManifest& manifest,
                                   Reader&& read) {
  if (!infGame) return nullptr;
  const auto loaded = [&](const CGameArea* area) -> const CGameArea* {
    return read_loaded_area_candidate(area, read);
  };
  const auto* bytes = reinterpret_cast<const std::byte*>(infGame);
  std::uint8_t visible = 0;
  std::array<CGameArea*, 12> areas{};
  if (!read(bytes + manifest.offsets.infGameVisibleArea, visible) ||
      !read(bytes + manifest.offsets.infGameAreas, areas) || visible >= areas.size()) {
    visible = 0xFF;
  } else if (const auto* area = loaded(areas[visible])) {
    return area;
  }
  CGameArea* master = nullptr;
  if (read(bytes + manifest.offsets.infGameAreaMaster, master)) {
    if (const auto* area = loaded(master)) return area;
  }
  if (visible != 0xFF) {
    for (const auto* candidate : areas) {
      if (const auto* area = loaded(candidate)) return area;
    }
  }
  return nullptr;
}

// Recover a missed LoadArea only from the active, loaded area actually being rendered.
// The owner's area table must point back to this exact object; offscreen areas cannot seed it.
template <class Reader>
CInfGame* resolve_rendered_area_owner(const CGameArea* rendered,
                                     const BuildManifest& manifest, Reader&& read) {
  if (!rendered) return nullptr;
  CInfGame* owner = nullptr;
  if (!read(reinterpret_cast<const std::byte*>(rendered) + offsetof(CGameArea, m_pGame),
            owner) || !owner || resolve_active_area(owner, manifest, read) != rendered) {
    return nullptr;
  }
  return owner;
}
}  // namespace iee::game
