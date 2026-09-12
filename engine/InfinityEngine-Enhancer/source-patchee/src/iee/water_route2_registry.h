#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <span>
#include <string_view>

namespace iee::water_route2 {
using Resref = std::array<char, 9>;
using Sha256 = std::array<std::byte, 32>;

enum class RegistryFileKind : std::uint32_t {
  BaseTis = 1,
  BasePvrz = 2,
  OverlayTis = 3,
  OverlayPvrz = 4,
};

struct RegistryFileEvidence {
  RegistryFileKind kind{};
  Resref resref{};
  std::uint32_t width{};
  std::uint32_t height{};
  std::uint64_t bytes{};
  Sha256 sha256{};
};

struct RegistryEntry {
  Resref wed{};
  Resref baseTis{};
  Resref overlayTis{};
  std::uint32_t overlaySlot{};
  std::uint32_t gridWidth{};
  std::uint32_t gridHeight{};
  std::uint32_t slotCount{};
  std::uint32_t baseTileCount{};
  std::uint32_t overlayTileCount{};
  std::uint32_t tileDimension{};
  std::uint32_t overlayCoverageCells{};
  std::uint32_t fileStart{};
  std::uint32_t fileCount{};
  float approvedStrength{};
  std::uint32_t materialId{};
  std::uint32_t temporalFrameCount{};
  float temporalSourceFps{};
  float temporalTargetFps{};
  std::uint32_t temporalAtlasColumns{};
  std::uint32_t temporalAtlasStridePixels{};
  std::uint32_t temporalAtlasPaddingPixels{};
  std::array<Resref, 5> slots{};
  Sha256 wedSha256{};
  bool allowStockWedWhenOverrideAbsent{};
  // Optional authored-art experiment. Empty in native-composition recipes.
  std::span<const std::uint16_t> secondaryArtTiles{};
  std::uint32_t secondaryArtSourceAlpha{};
  std::uint32_t secondaryArtTargetAlpha{};
};

struct ArtOpacity {
  std::uint32_t source{};
  std::uint32_t target{};
};

inline unsigned long art_draw_color(unsigned long color, ArtOpacity opacity) noexcept {
  // Preserve RGB, fades, and every unexpected native alpha unchanged.
  if (opacity.source == 0 || opacity.target == 0 || opacity.target > 255 ||
      (color >> 24) != opacity.source) return color;
  return (color & 0x00FFFFFFUL) | (static_cast<unsigned long>(opacity.target) << 24);
}

template <std::size_t N>
consteval Resref resref_array(const char (&value)[N]) {
  static_assert(N >= 1 && N <= 9);
  Resref result{};
  for (std::size_t index = 0; index + 1 < N; ++index) result[index] = value[index];
  return result;
}

inline std::string_view resref_view(const Resref& value) noexcept {
  std::size_t length = 0;
  while (length < 8 && value[length] != '\0') ++length;
  return {value.data(), length};
}

struct Query {
  std::string_view wed;
  std::string_view baseTis;
  std::string_view overlayTis;
  std::string_view page;
  std::span<const std::string_view> slots;
  std::uint32_t overlaySlot{};
  std::uint32_t gridWidth{};
  std::uint32_t gridHeight{};
  std::uint32_t baseTileCount{};
  std::uint32_t overlayTileCount{};
  std::uint32_t overlayCoverageCells{};
  std::uint32_t pageWidth{};
  std::uint32_t pageHeight{};
};

struct Match {
  float approvedStrength{};
  std::uint32_t materialId{};
  std::uint32_t registryVersion{};
  std::uint32_t temporalFrameCount{};
  float temporalSourceFps{};
  float temporalTargetFps{};
  std::uint32_t temporalAtlasColumns{};
  std::uint32_t temporalAtlasStridePixels{};
  std::uint32_t temporalAtlasPaddingPixels{};
  Resref wed{};

  [[nodiscard]] bool temporal_enabled() const noexcept {
    return temporalFrameCount >= 2 && temporalSourceFps > 0.0f &&
           temporalTargetFps >= temporalSourceFps && temporalAtlasColumns > 0 &&
           temporalAtlasStridePixels > temporalAtlasPaddingPixels * 2;
  }
  bool weatherVariant{};
};

inline bool layout_matches(const Query& query, const RegistryEntry& entry) noexcept {
  if (query.slots.size() != entry.slotCount || entry.slotCount > entry.slots.size()) return false;
  for (std::size_t index = 0; index < query.slots.size(); ++index) {
    if (query.slots[index] != resref_view(entry.slots[index])) return false;
  }
  return true;
}

inline bool identity_matches(const Query& query, const RegistryEntry& entry) noexcept {
  return query.wed == resref_view(entry.wed) &&
         query.baseTis == resref_view(entry.baseTis) &&
         query.overlayTis == resref_view(entry.overlayTis) &&
         query.overlaySlot == entry.overlaySlot &&
         query.gridWidth == entry.gridWidth && query.gridHeight == entry.gridHeight &&
         query.baseTileCount == entry.baseTileCount &&
         query.overlayTileCount == entry.overlayTileCount &&
         query.overlayCoverageCells == entry.overlayCoverageCells &&
         layout_matches(query, entry);
}

// Validates every manifested override file before publishing any entry.
bool prepare(const std::filesystem::path& overrideRoot) noexcept;
std::optional<Match> match(const Query& query) noexcept;
// Pointer refers to immutable compiled data, only after all entry hashes pass.
const RegistryEntry* secondary_art_entry(std::string_view wed) noexcept;
std::uint32_t version() noexcept;
void release() noexcept;
}  // namespace iee::water_route2
