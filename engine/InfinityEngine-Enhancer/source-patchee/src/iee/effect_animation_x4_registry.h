#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>

#include "iee/area_animation_x4_registry.h"
#include "iee/core/effect_frame_cache.h"

namespace iee::effect_animation_x4 {

struct FrameHandle {
  std::size_t resourceIndex{};
  std::size_t frameIndex{};
  std::uint64_t generation{};

  [[nodiscard]] constexpr bool operator==(const FrameHandle&) const noexcept = default;
};

struct TimelineInfo {
  bool enabled{};
  std::uint32_t nativeFpsNumerator{};
  std::uint32_t nativeFpsDenominator{};
  std::uint32_t targetFpsNumerator{};
  std::uint32_t targetFpsDenominator{};
  std::uint32_t phaseCount{};
};

// Effects use an isolated registry and GPU cache, but the engine texture ABI is
// identical to the established area-animation compositor.
struct EngineTextureApi {
  using Base = area_animation_x4::EngineTextureApi;
  using DrawGenTextureFn = Base::DrawGenTextureFn;
  using DrawBindTextureFn = Base::DrawBindTextureFn;
  using DrawDeleteTextureFn = Base::DrawDeleteTextureFn;
  using TexImageFn = Base::TexImageFn;
  using DrawGetRendererFn = Base::DrawGetRendererFn;
  DrawGenTextureFn DrawGenTexture{};
  DrawBindTextureFn DrawBindTexture{};
  DrawDeleteTextureFn DrawDeleteTexture{};
  TexImageFn TexImage{};
  DrawGetRendererFn DrawGetRenderer{};
  const std::uint32_t* glTextureState{};
  // Native queue submission, not glFlush/glFinish. Required before mutation.
  void (*DrawFlushGl)(){};
  void (*DrawPushState)(){};
  void (*DrawPopState)(){};
  std::byte* glTextureTable{};
};

struct Options {
  bool streaming{false}; // Explicit backend choice; legacy host callers stay eager.
  core::EffectFrameCache::Limits cpu{};
  std::uint64_t gpuBytes{288ull << 20};
  std::uint64_t metadataBytes{16ull << 20};
  std::uint64_t packBytes{512ull << 30};
  std::uint32_t maxResources{8192};
  std::uint32_t horizonMs{500};
  bool trace{};
};

struct TextureCacheStats {
  std::size_t capacity{};
  std::size_t residentTextures{};
  std::uint64_t requests{}, hits{}, reuses{}, allocationFailures{}, uploadFailures{};
  std::uint64_t residentBytes{}, peakBytes{}, budget{}, flushes{}, cpuMisses{}, pendingDeletes{};
  std::uint64_t scratchBytes{}, scratchPeakBytes{}, scratchRefusals{};
  std::uint64_t draws{}, drawMisses{}, firstSubmissions{}, firstSubmissionMisses{};
  std::uint64_t hintToFirstSubmitNanoseconds{}, maximumHintToFirstSubmitNanoseconds{}, traceDropped{};
  std::uint64_t uploads{}, uploadedBytes{}, uploadNanoseconds{}, maximumUploadNanoseconds{};
  std::uint64_t horizonReductions{};
};
[[nodiscard]] TextureCacheStats texture_cache_stats() noexcept;

// Eager loads every raw RGBA; streaming loads only metadata and quota-bound
// bootstrap heads before installing owner hooks. Malformed metadata/bootstrap
// rejects the pack; later missing backings are quarantined and counted as misses.
bool prepare(const std::filesystem::path& assetsDirectory) noexcept;
bool prepare(const std::filesystem::path& assetsDirectory, const Options& options) noexcept;
void release() noexcept;
[[nodiscard]] core::EffectFrameCache::Stats cpu_cache_stats() noexcept;
[[nodiscard]] core::EffectFrameCache::State cpu_frame_state(FrameHandle handle) noexcept;
// Native callbacks copy scalars only; address identities are never sent to workers.
std::uint64_t begin_occurrence(std::uintptr_t owner) noexcept;
std::uint64_t end_occurrence(std::uintptr_t owner) noexcept;
void begin_session() noexcept;
std::uint64_t occurrence_serial(std::uintptr_t owner) noexcept;
void prefetch_resource(const std::array<char, 8>& resref) noexcept;
void prefetch_window(std::uintptr_t owner, const std::array<char, 8>& resref,
                     int sequence, std::uint32_t phase, bool once, bool paused) noexcept;
// Called at a verified queue-empty boundary / before context destruction, GL thread only.
void release_gpu(const EngineTextureApi& api) noexcept;
void context_destroyed(std::uintptr_t context) noexcept;
bool reserve_scratch(std::uint64_t bytes, const std::byte* textureTable) noexcept;
void cancel_scratch(std::uint64_t bytes) noexcept;
void track_scratch(int texture, std::uint64_t bytes, const std::byte* textureTable) noexcept;
void retire_scratch(int texture) noexcept;
void observe_gpu_retirements(const EngineTextureApi& api) noexcept;
enum class DrawOutcome : std::uint8_t { Hd, CpuNotReady, StorageFailed, GpuRejected, MaskRejected };
void note_draw(std::uintptr_t cell, FrameHandle handle, int slot, int phase,
               std::uint64_t epoch, std::int64_t ticks, bool hd, bool masked,
               int sequence, bool once, bool paused, DrawOutcome outcome) noexcept;
void note_swap(std::uint64_t epoch, std::int64_t ticks, bool success, int worldActive) noexcept;
[[nodiscard]] bool ready() noexcept;
[[nodiscard]] bool streaming() noexcept;
void queue_diagnostic(const std::array<char, 8>& resref, std::uint32_t stage,
                      int sequence, int frame, int phase, int width, int height) noexcept;
[[nodiscard]] bool contains_resource(const std::array<char, 8>& resref) noexcept;

// Per-resource diagnostic gates. They keep renderer logs bounded while still
// collecting geometry evidence independently for every future effect pack.
[[nodiscard]] bool mark_diagnostic_stage_once(const std::array<char, 8>& resref,
                                              std::uint32_t stage) noexcept;
[[nodiscard]] bool mark_geometry_observation_once(const std::array<char, 8>& resref,
                                                  int sequence,
                                                  int nativeFrame) noexcept;

// Resolves one native CVidCell cycle slot. RESREF matching is case-insensitive;
// sequence, native frame and logical dimensions must match exactly.
bool resolve_frame(const std::array<char, 8>& resref, int sequence, int currentFrame,
                   int logicalWidth, int logicalHeight, FrameHandle& out, bool onceProfile = false) noexcept;

// Registry v2/v3 packs retain the native BAM slots for fallback and add a
// QPC-scheduled timeline. v3 adds optional once-profile tables per cycle;
// the VVC owner chooses the mode without changing native BAM/VVC controls.
// The timeline resolver rejects any mismatch exactly
// like the native resolver, leaving the engine's original draw untouched.
bool timeline_info(const std::array<char, 8>& resref, int sequence,
                   TimelineInfo& out, bool onceProfile = false) noexcept;
bool resolve_timeline_frame(const std::array<char, 8>& resref, int sequence,
                            std::uint32_t phase, int logicalWidth,
                            int logicalHeight, FrameHandle& out, bool onceProfile = false) noexcept;

// Binds a x4 backing texture while preserving the engine's original x1 texture
// descriptor and draw geometry. Returns false without changing the current
// binding when any OpenGL or pack precondition fails.
bool bind_frame_texture(FrameHandle handle, const EngineTextureApi& api,
                        int& previousTextureId, DrawOutcome* outcome = nullptr) noexcept;
void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept;

}  // namespace iee::effect_animation_x4
