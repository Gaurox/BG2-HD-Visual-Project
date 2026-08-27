#pragma once

#include <array>
#include <cstddef>
#include <climits>
#include <cstdint>
#include <filesystem>
#include <string_view>

namespace iee::area_animation_x4 {
struct FrameHandle {
  std::size_t resourceIndex{};
  std::size_t frameIndex{};

  [[nodiscard]] constexpr bool operator==(const FrameHandle&) const noexcept = default;
};

struct TimelineTiming {
  bool enabled{};
  std::uint32_t nativeFpsNumerator{};
  std::uint32_t nativeFpsDenominator{};
  std::uint32_t targetFpsNumerator{};
  std::uint32_t targetFpsDenominator{};
  std::uint32_t phaseCount{};
};

struct FrameResolution {
  FrameHandle nativeFrame{};
  TimelineTiming timeline{};
};

struct NativePixelEncoding {
  std::uint32_t externalFormat{};
  std::uint32_t type{};

  [[nodiscard]] constexpr bool operator==(const NativePixelEncoding&) const noexcept = default;
};

struct EngineTextureApi {
  using DrawGenTextureFn = int (*)(int filter, unsigned char formatKind, int wrapMode,
                                   unsigned char secondaryTexture);
  using DrawBindTextureFn = void (*)(int textureId);
  using DrawDeleteTextureFn = void (*)(int textureId);
  using TexImageFn = void (*)(int width, int height, const void* pixels,
                              unsigned char secondaryTexture);
  using DrawGetRendererFn = int (*)();

  DrawGenTextureFn DrawGenTexture{};
  DrawBindTextureFn DrawBindTexture{};
  DrawDeleteTextureFn DrawDeleteTexture{};
  TexImageFn TexImage{};
  DrawGetRendererFn DrawGetRenderer{};
  const std::uint32_t* glTextureState{};
  // Optional 512-entry engine texture descriptor table. Creature replacement
  // uploads validate the generated logical ID against its exact GL name.
  std::byte* glTextureTable{};
  // Optional 256-entry BGRA/RGBA table most recently produced by
  // CVidPalette::Realize. Creature composition consumes it synchronously from
  // the same render call; area-animation composition leaves it null.
  const std::uint32_t* realizedPalette{};
  // Adjacent runtime GL external-format/type globals used by the engine's own
  // texture uploads. Creature composition snapshots both values with its palette.
  const NativePixelEncoding* nativePixelEncoding{};
};

// Loads AreaAnimations-X4.registry and every referenced raw RGBA frame before
// hooks are installed. Any malformed/missing asset disables the whole pack.
bool prepare(const std::filesystem::path& assetsDirectory) noexcept;
void release() noexcept;
[[nodiscard]] bool ready() noexcept;

// Per-area packs. A single global registry cannot hold the game: its raw payload is
// capped at 512 MiB and the full converted inventory is several gigabytes. When
// <assetsDirectory>/areas exists, each area owns a pack under areas/<AREA>/ and only
// the current one is resident.
//
// configure_area_packs() records the layout and reports whether per-area mode is
// active; when it is not, the historical single global pack keeps working unchanged.
// prepare_for_area() swaps the resident pack on an area transition, and releases
// everything when the area has no pack, which fails closed to the engine's own BAM path.
bool configure_area_packs(const std::filesystem::path& assetsDirectory) noexcept;
[[nodiscard]] bool per_area_packs_active() noexcept;
bool prepare_for_area(std::string_view areaResref) noexcept;

// Resolves CGameStatic's current sequence slot through the original BAM cycle
// lookup. Resrefs are the exact eight bytes embedded in CGameStatic.
//
// `worldX`/`worldY` are CGameStatic's own world pixel position, and they select between several
// variants sharing one resref: an area may pose the same BAM more than once, and each occurrence
// may need different pixels because the decor occluding it differs. A variant bound to a position
// wins; a variant bound to none is the fallback for every other occurrence. Pass
// `kAnyWorldPosition` when the build cannot supply a position — matching then degrades to the
// historical resref-only behaviour.
inline constexpr int kAnyWorldPosition = INT32_MIN;

bool resolve_frame(const std::array<char, 8>& resref, int worldX, int worldY, int sequence,
                   int currentFrame, FrameResolution& out) noexcept;

// Resolves a phase from a validated TimedTimeline cycle. The native frame in
// FrameResolution remains the fail-closed fallback if scheduling is unavailable.
bool resolve_timeline_frame(const FrameResolution& resolution, int sequence,
                            std::uint32_t phase, FrameHandle& out) noexcept;

// Lazily creates or reuses a bounded engine texture whose descriptor retains
// native x1 dimensions while its OpenGL storage contains the x4 pixels.
bool bind_frame_texture(FrameHandle handle, const EngineTextureApi& api,
                        int& previousTextureId) noexcept;
void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept;

// Drops cached texture names WITHOUT returning them to the engine. Correct only when
// the names are already invalid: a recreated WGL context, or hook teardown.
void forget_engine_textures() noexcept;

// Releases cached textures while the context is still alive. Deletion needs the GL
// thread, which an area transition is not, so names are parked here and reclaimed by
// flush_retired_textures() on the next render pass. Without this an area swap would
// abandon up to kTextureCacheLimit engine texture names per transition.
void flush_retired_textures(const EngineTextureApi& api) noexcept;
[[nodiscard]] bool has_retired_textures() noexcept;
}  // namespace iee::area_animation_x4
