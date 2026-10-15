#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>

#include "iee/area_animation_x4_registry.h"

namespace iee::effect_animation_x4 {

struct FrameHandle {
  std::size_t resourceIndex{};
  std::size_t frameIndex{};

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
using EngineTextureApi = area_animation_x4::EngineTextureApi;

struct TextureCacheStats {
  std::size_t capacity{};
  std::size_t residentTextures{};
  std::uint64_t requests{}, hits{}, reuses{}, allocationFailures{}, uploadFailures{};
};
[[nodiscard]] TextureCacheStats texture_cache_stats() noexcept;

// Loads EffectAnimations-X4.registry and every declared raw RGBA frame before
// installing the effect-owner hooks. A malformed or incomplete pack is
// rejected as a whole; callers then retain the native BAM path.
bool prepare(const std::filesystem::path& assetsDirectory) noexcept;
void release() noexcept;
[[nodiscard]] bool ready() noexcept;
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
                        int& previousTextureId) noexcept;
void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept;

}  // namespace iee::effect_animation_x4
