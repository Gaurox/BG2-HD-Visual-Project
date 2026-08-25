#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>

#include "iee/area_animation_x4_registry.h"

namespace iee::creature_sprite_x2 {
inline constexpr int kNativeLogicalBorder = 1;
inline constexpr std::size_t kMaximumCompositeLayers = 8;
inline constexpr std::uint64_t kMaximumRegistryBytes =
    128ull * 1024ull * 1024ull;

[[nodiscard]] constexpr bool supported_physical_scale(std::uint32_t scale) noexcept {
  return scale == 2 || scale == 4;
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

// Prefers the version-3 xN palette-index registry when present and otherwise
// loads the legacy x2 registry. No game or GL state is touched.
bool prepare(const std::filesystem::path& assetsDirectory) noexcept;
void release() noexcept;
[[nodiscard]] bool ready() noexcept;
[[nodiscard]] std::uint16_t target_animation_id() noexcept;
[[nodiscard]] std::uint32_t loaded_scale() noexcept;
[[nodiscard]] bool contains_resource(const std::array<char, 8>& resref) noexcept;

// Resolves CVidCell's current cycle slot through the original BAM lookup.
bool resolve_frame(const std::array<char, 8>& resref, int sequence, int currentFrame,
                   FrameHandle& out) noexcept;

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
