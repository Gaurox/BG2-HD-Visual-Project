#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string_view>

#include "build_manifest.h"
#include "runtime_types_x64.h"

namespace iee::game {
struct PVRZTileEntry {
  int32_t page{};
  int32_t u{};
  int32_t v{};
};

struct TileInfo {
  const CResTile* resource{};
  const CResTileSet* tileset{};
  const PVRZTileEntry* table{};
  PVRZTileEntry entry{};
  const TisFileHeader* header{};
  int index{-1};
  uint32_t tileDataBlockLen{};
  uint32_t tileCount{};
};

[[nodiscard]] bool get_tile_info(void* vidTile, const BuildManifest& manifest, TileInfo& out,
                                 void* (*CRes_Demand)(void*));

// Reads one table entry with count, integer-overflow, and OS readability
// checks. CRes::nSize is the per-record block length for TIS resources, not
// the byte extent of the full nCount-entry table.
[[nodiscard]] bool read_tis_tile_entry(const TileInfo& tileInfo, std::uint32_t index,
                                       PVRZTileEntry& out) noexcept;

// Resource-wrapper arrays are mutable during an area transition. A slot requested for one
// overlay can temporarily expose a recycled wrapper from another tileset. Consumers that derive
// persistent area state from a wrapper must validate both identities before using its pixels.
[[nodiscard]] bool matches_tis_tile_identity(std::int32_t actualTileIndex,
                                             std::string_view actualTilesetResref,
                                             std::uint32_t expectedTileIndex,
                                             std::string_view expectedTilesetResref) noexcept;

// A tile wrapper can retain the right TIS and tile index while its PVR pointer still names a
// page from the previous area. Validate the Infinity page convention too: the page resref is the
// TIS resref without its second character, followed by a decimal page number padded to 2 digits.
[[nodiscard]] bool matches_pvrz_page_identity(std::string_view actualPageResref,
                                              std::string_view tilesetResref,
                                              std::int32_t page) noexcept;

[[nodiscard]] bool get_tis_linear_tiles_flag(const CResTileSet* tis, const BuildManifest& manifest);

[[nodiscard]] std::optional<std::uint32_t> get_tis_header_tile_dimension(
    const TileInfo& tileInfo, const BuildManifest& manifest);
}  // namespace iee::game
