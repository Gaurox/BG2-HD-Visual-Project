#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <limits>

#include "iee/area_animation_x4_registry.h"

namespace iee::creature_sprite_x2 {
inline constexpr int kNativeLogicalBorder = 1;
inline constexpr std::size_t kMaximumCompositeLayers = 8;
inline constexpr std::uint64_t kMaximumX2RegistryBytes =
    128ull * 1024ull * 1024ull;
inline constexpr std::uint64_t kMaximumX4RegistryBytes =
    512ull * 1024ull * 1024ull;
// Compatibility name for the historical/legacy x2 bound.
inline constexpr std::uint64_t kMaximumRegistryBytes = kMaximumX2RegistryBytes;
// A registry-set is intentionally much larger than one process-resident pack:
// each shard retains the 128-resource boundary and uses the scale-specific
// 128-MiB (x2) or 512-MiB (x4) byte bound, while only frame metadata and a
// bounded working set of palette indices stay resident. These limits cover the
// measured complete 0x6110 x4 inventory without permitting an unbounded
// manifest or cache allocation.
inline constexpr std::uint32_t kMaximumRegistrySetShards = 64;
inline constexpr std::uint32_t kMaximumRegistrySetResources = 8192;
inline constexpr std::uint64_t kMaximumRegistrySetFrames = 1'048'576;
inline constexpr std::uint64_t kMaximumRegistrySetBytes =
    8ull * 1024ull * 1024ull * 1024ull;
inline constexpr std::uint64_t kLazyIndexCacheBudgetBytes =
    128ull * 1024ull * 1024ull;
inline constexpr std::uint64_t kCatalogMetadataCacheBudgetBytes =
    128ull * 1024ull * 1024ull;
// Registry V5 stores each lazy frame independently. These values are part of
// the on-disk format, not Windows Compression API algorithm identifiers.
inline constexpr std::uint8_t kRegistryFrameCodecRaw = 0;
inline constexpr std::uint8_t kRegistryFrameCodecXpressHuff = 1;
inline constexpr std::uint32_t kMaximumCatalogDirectoryEntries = 1'048'576;
// The catalog is a bounded, immutable map from animation ids to reusable V3 or
// V5 components. Its limits are deliberately independent from the legacy
// set-V1 limits: a catalog may grow incrementally without flattening every
// animation into one registry-set.
inline constexpr std::uint32_t kMaximumCatalogAnimations = 512;
inline constexpr std::uint32_t kMaximumCatalogComponents = 16'384;
inline constexpr std::uint32_t kMaximumCatalogMemberships = 262'144;
inline constexpr std::uint32_t kMaximumCatalogShards = 16'384;
inline constexpr std::uint32_t kMaximumCatalogResources = 32'768;
inline constexpr std::uint64_t kMaximumCatalogFrames = 4'194'304;
inline constexpr std::uint64_t kMaximumCatalogRegistryBytes =
    128ull * 1024ull * 1024ull * 1024ull;

[[nodiscard]] constexpr bool supported_physical_scale(std::uint32_t scale) noexcept {
  return scale == 2 || scale == 4;
}

[[nodiscard]] constexpr std::uint64_t maximum_registry_bytes_for_scale(
    std::uint32_t scale) noexcept {
  return scale == 2 ? kMaximumX2RegistryBytes
                    : (scale == 4 ? kMaximumX4RegistryBytes : 0);
}

// CVidCell allocates one transparent logical pixel on every side of a BAM
// frame. The replacement backing scales that complete native texture, not
// only the visible BAM payload.
[[nodiscard]] constexpr int logical_texture_extent(int frameExtent) noexcept {
  return frameExtent + 2 * kNativeLogicalBorder;
}

[[nodiscard]] constexpr std::int64_t physical_texture_extent(
    int frameExtent, std::uint32_t scale) noexcept {
  return static_cast<std::int64_t>(logical_texture_extent(frameExtent)) * scale;
}

[[nodiscard]] constexpr std::int64_t physical_content_offset(
    std::uint32_t scale) noexcept {
  return static_cast<std::int64_t>(kNativeLogicalBorder) * scale;
}

[[nodiscard]] constexpr std::int64_t physical_layer_offset(
    int frameCenter, int compositeOrigin, std::uint32_t scale) noexcept {
  return (-static_cast<std::int64_t>(frameCenter) -
          static_cast<std::int64_t>(compositeOrigin) + kNativeLogicalBorder) *
         static_cast<std::int64_t>(scale);
}

struct FrameHandle {
  std::size_t resourceIndex{};
  std::size_t frameIndex{};
  // Resolution scope is part of the handle identity. Components may be shared
  // and distinct animations may legally expose the same resref, so QA and
  // composition diagnostics must never infer this id from the resource alone.
  std::uint16_t animationId{};
  // Catalog metadata is evictable. These fields make a handle fail closed if
  // its owning shard was evicted and later reused between resolve and draw.
  std::uint32_t catalogShardIndex{(std::numeric_limits<std::uint32_t>::max)()};
  std::uint64_t catalogGeneration{};

  [[nodiscard]] constexpr bool operator==(const FrameHandle&) const noexcept = default;
};

using EngineTextureApi = area_animation_x4::EngineTextureApi;
using NativePixelEncoding = area_animation_x4::NativePixelEncoding;

struct PaletteSnapshot {
  std::array<std::uint32_t, 256> colors{};
  NativePixelEncoding encoding{};
};

struct CompositeLayer {
  FrameHandle frame{};
  PaletteSnapshot palette{};
};

struct FrameGeometry {
  int logicalWidth{};
  int logicalHeight{};
  int centerX{};
  int centerY{};
};

struct CompositeBounds {
  int left{};
  int top{};
  int right{};
  int bottom{};

  [[nodiscard]] constexpr int content_width() const noexcept { return right - left; }
  [[nodiscard]] constexpr int content_height() const noexcept { return bottom - top; }
  [[nodiscard]] constexpr int logical_width() const noexcept {
    return logical_texture_extent(content_width());
  }
  [[nodiscard]] constexpr int logical_height() const noexcept {
    return logical_texture_extent(content_height());
  }
};

// Character BAM layers share a world-space origin. Their BAM centers map each
// frame into that coordinate system; the final native composite is their union
// plus CVidCell's one-logical-pixel transparent border.
bool calculate_composite_bounds(const FrameGeometry* frames, std::size_t frameCount,
                                CompositeBounds& out) noexcept;

// Character's native CPU compositor copies every non-zero palette color over
// the previous layer and preserves its alpha for the final GPU draw.
[[nodiscard]] constexpr std::uint32_t overwrite_nontransparent_pixel(
    std::uint32_t destination, std::uint32_t source) noexcept {
  return source != 0 ? source : destination;
}

// Replays Scalepix pixelInterpolate exactly over the engine's packed palette
// colors. RGB and BGR layouts are both safe because the three color bytes are
// blended independently; every supported native format stores alpha in the
// high byte of the host dword.
[[nodiscard]] constexpr std::uint32_t xbr_blend_pixel(
    std::uint32_t destination, std::uint32_t source,
    std::uint8_t blendCode) noexcept {
  constexpr std::array<std::array<std::uint8_t, 2>, 5> kWeights{{
      {{7, 1}}, {{3, 1}}, {{1, 1}}, {{1, 3}}, {{1, 7}},
  }};
  if (blendCode >= kWeights.size()) return destination;
  const auto q1 = kWeights[blendCode][0];
  const auto q2 = kWeights[blendCode][1];
  const auto alphaDestination = static_cast<std::uint8_t>(destination >> 24u);
  const auto alphaSource = static_cast<std::uint8_t>(source >> 24u);
  std::uint32_t result = 0;
  for (unsigned shift = 0; shift < 24; shift += 8) {
    const auto destinationChannel =
        static_cast<std::uint8_t>(destination >> shift);
    const auto sourceChannel = static_cast<std::uint8_t>(source >> shift);
    const auto channel =
        alphaDestination == 0
            ? sourceChannel
            : (alphaSource == 0
                   ? destinationChannel
                   : static_cast<std::uint8_t>(
                         (q2 * sourceChannel + q1 * destinationChannel) /
                         (q1 + q2)));
    result |= static_cast<std::uint32_t>(channel) << shift;
  }
  const auto alpha = static_cast<std::uint8_t>(
      (q2 * alphaSource + q1 * alphaDestination) / (q1 + q2));
  return result | (static_cast<std::uint32_t>(alpha) << 24u);
}

[[nodiscard]] constexpr bool supported_native_pixel_encoding(
    NativePixelEncoding encoding) noexcept {
  constexpr std::uint32_t kRgba = 0x1908;
  constexpr std::uint32_t kBgra = 0x80E1;
  constexpr std::uint32_t kUnsignedByte = 0x1401;
  constexpr std::uint32_t kUnsignedInt8888Rev = 0x8367;
  return (encoding.externalFormat == kRgba && encoding.type == kUnsignedByte) ||
         (encoding.externalFormat == kBgra && encoding.type == kUnsignedByte) ||
         (encoding.externalFormat == kBgra && encoding.type == kUnsignedInt8888Rev);
}

// Prefers the multi-animation xN catalog when present, then the xN
// registry-set, the version-3 monolithic xN registry, and finally the legacy
// x2 registry. A present but invalid higher-priority source fails closed
// without falling through. No game or GL state is touched.
void configure_linear_filtering(bool enabled) noexcept;
bool prepare(const std::filesystem::path& assetsDirectory) noexcept;
void release() noexcept;
[[nodiscard]] bool ready() noexcept;
// Compatibility surface for legacy single-animation packs. A catalog returns
// its id only when it contains exactly one animation; multi-animation catalogs
// return zero so callers cannot accidentally resolve an ambiguous resref.
[[nodiscard]] std::uint16_t target_animation_id() noexcept;
[[nodiscard]] std::uint32_t loaded_scale() noexcept;
[[nodiscard]] bool contains_animation(std::uint16_t animationId) noexcept;
[[nodiscard]] bool animation_targets_character(std::uint16_t animationId) noexcept;
[[nodiscard]] bool animation_targets_monster(std::uint16_t animationId) noexcept;
[[nodiscard]] bool animation_targets_monster_icewind(
    std::uint16_t animationId) noexcept;
[[nodiscard]] bool targets_character() noexcept;
[[nodiscard]] bool targets_monster() noexcept;
[[nodiscard]] bool targets_monster_icewind() noexcept;
[[nodiscard]] bool contains_resource(std::uint16_t animationId,
                                     const std::array<char, 8>& resref) noexcept;
[[nodiscard]] bool contains_resource(const std::array<char, 8>& resref) noexcept;

// Resolves CVidCell's current cycle slot through the original BAM lookup.
bool resolve_frame(std::uint16_t animationId, const std::array<char, 8>& resref,
                   int sequence, int currentFrame, FrameHandle& out) noexcept;
bool resolve_frame(const std::array<char, 8>& resref, int sequence, int currentFrame,
                   FrameHandle& out) noexcept;

// Materializes a lazy xN frame in the bounded index cache. This is also a
// read-only diagnostic surface for native tests; normal rendering calls it
// implicitly before composing a frame. Any backing registry removal or
// metadata change disables the whole pack so creature rendering falls back
// atomically. Retained handles do not extend source validity: every public
// payload/bind call rechecks the owning file identity before using a cache,
// and each newly read lazy payload must match the SHA-256 captured while its
// fully validated shard was parsed.
bool ensure_frame_payload_available(FrameHandle handle) noexcept;
[[nodiscard]] std::uint64_t resident_index_bytes() noexcept;
[[nodiscard]] std::uint64_t resident_catalog_metadata_bytes() noexcept;
[[nodiscard]] std::size_t pending_catalog_loads() noexcept;
// Monotonic diagnostic used by native tests/QA to prove that cache-hit draws
// do not reopen, stat, or reread catalog/shard files.
[[nodiscard]] std::uint64_t filesystem_access_count() noexcept;

// Reuses the synchronous CVidPalette::Realize output, reconstructs the upscaled
// frame from its current palette colors, and binds a physical x2/x4 backing
// while retaining the engine's native bordered logical texture descriptor.
bool capture_palette_snapshot(const std::uint32_t* realizedOutput, const EngineTextureApi& api,
                              PaletteSnapshot& out) noexcept;
bool bind_frame_texture(FrameHandle handle, int logicalWidth, int logicalHeight,
                        const PaletteSnapshot& palette, const EngineTextureApi& api,
                        int& previousTextureId) noexcept;
bool bind_composite_texture(const CompositeLayer* layers, std::size_t layerCount,
                            int logicalWidth, int logicalHeight,
                            const EngineTextureApi& api,
                            int& previousTextureId,
                            int& transientTextureId) noexcept;
void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept;
void finish_composite_texture(const EngineTextureApi& api, int previousTextureId,
                              int transientTextureId) noexcept;

// Drops enhancer-owned cached logical texture ids after hooks are quiesced or
// a WGL context is recreated. Character composite IDs are transient and are
// marked delete-pending immediately after their queued draw.
void forget_engine_textures() noexcept;
}  // namespace iee::creature_sprite_x2
