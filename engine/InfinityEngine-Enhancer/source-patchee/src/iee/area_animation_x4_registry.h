#pragma once

#include <array>
#include <cstddef>
#include <climits>
#include <cstdint>
#include <filesystem>
#include <string_view>

#include "iee/core/cache_budget_simulator.h"
#include "iee/core/process_resource_telemetry.h"

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

// Cumulative per-area accounting for the bounded GPU cache. Byte counts describe the uploaded
// RGBA8 base level owned by this runtime; driver allocation overhead is not observable here.
struct TextureCacheTelemetryStats {
  bool active{};
  std::uint64_t capacity{};
  std::uint64_t requests{};
  std::uint64_t hits{};
  std::uint64_t misses{};
  std::uint64_t textureNameCreations{};
  std::uint64_t textureNameCreationFailures{};
  std::uint64_t uploadAttempts{};
  std::uint64_t successfulUploads{};
  std::uint64_t failedUploads{};
  std::uint64_t lruEvictions{};
  std::uint64_t failedUploadTextureDeletes{};
  std::uint64_t contextInvalidatedTextureNames{};
  std::uint64_t uploadedBaseLevelBytes{};
  std::uint64_t residentTextureNames{};
  std::uint64_t residentBaseLevelBytes{};
  std::uint64_t peakResidentBaseLevelBytes{};
};

inline constexpr std::size_t kCacheBudgetSimulationProfileCount = 5;

// Shadow models fed by the real frame-request stream. They predict a lazy CPU
// cache followed by an independent GPU cache, but never alter runtime state,
// perform I/O or issue OpenGL calls.
struct CacheBudgetSimulationSnapshot {
  bool active{};
  std::uint64_t frameCapacity{};
  std::array<core::HierarchicalCacheBudgetSimulationStats,
             kCacheBudgetSimulationProfileCount>
      profiles{};
};

// Diagnostic-only accounting for one synchronous pack preparation. Byte counts cover the raw
// RGBA frame payload owned by this runtime, not allocator overhead or process working set.
struct PackPreparationStats {
  std::uint64_t registryBytes{};
  std::uint64_t frameFiles{};
  std::uint64_t frameBytes{};
  std::uint64_t outgoingRawBytes{};
  std::uint64_t residentRawBytes{};
  std::uint64_t peakRawBytes{};
  std::uint64_t resourceCount{};
  std::uint64_t timedResourceCount{};
  std::uint64_t frameCount{};
  std::uint64_t outgoingTextureNames{};
  std::uint64_t deferredTextureNames{};
  TextureCacheTelemetryStats outgoingTextureCache{};
  CacheBudgetSimulationSnapshot outgoingCacheBudgetSimulation{};
  core::ProcessResourceSnapshot processBefore{};
  core::ProcessResourceSnapshot processAtCoexistence{};
  core::ProcessResourceSnapshot processAfterSwap{};
  double registryReadMilliseconds{};
  double frameReadMilliseconds{};
  double parseAndAllocateMilliseconds{};
  double swapMilliseconds{};
  double totalMilliseconds{};
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
bool prepare(const std::filesystem::path& assetsDirectory,
             PackPreparationStats* stats = nullptr) noexcept;
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
bool prepare_for_area(std::string_view areaResref,
                      bool enablePerformanceLogging = false) noexcept;

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

// Registry-v3 position-bound variants were introduced for legacy pixels with
// occurrence-specific baked foreground masks. Phase 1 must leave those pixels
// unchanged to avoid applying a partial native dither twice. V1/V2 and unbound
// V3 resources return false and remain eligible for the structural bridge.
[[nodiscard]] bool has_baked_occurrence_occlusion(FrameHandle handle) noexcept;

// Lazily creates or reuses a bounded engine texture whose descriptor retains
// native x1 dimensions while its OpenGL storage contains the x4 pixels.
bool bind_frame_texture(FrameHandle handle, const EngineTextureApi& api,
                        int& previousTextureId,
                        bool enablePerformanceLogging = false) noexcept;
void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept;

// Returns a coherent cumulative snapshot for the resident area. Counters remain zero when
// PerformanceLogs is disabled; resident base-level size still reflects the actual bounded cache.
[[nodiscard]] TextureCacheTelemetryStats texture_cache_telemetry_snapshot() noexcept;

// Returns passive predictions for five bounded CPU/GPU profiles. The snapshot
// stays inactive unless PerformanceLogs has observed at least one valid frame
// request in the resident area.
[[nodiscard]] CacheBudgetSimulationSnapshot cache_budget_simulation_snapshot() noexcept;

// Drops cached texture names WITHOUT returning them to the engine. Correct only when
// the names are already invalid: a recreated WGL context, or hook teardown.
void forget_engine_textures() noexcept;

// Releases cached textures while the context is still alive. Deletion needs the GL
// thread, which an area transition is not, so names are parked here and reclaimed by
// flush_retired_textures() on the next render pass. Without this an area swap would
// abandon up to kTextureCacheLimit engine texture names per transition.
void flush_retired_textures(const EngineTextureApi& api,
                            bool enablePerformanceLogging = false) noexcept;
[[nodiscard]] bool has_retired_textures() noexcept;
}  // namespace iee::area_animation_x4
