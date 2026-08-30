#include "hooks.h"

#include <intrin.h>
#include <windows.h>
#include <zlib.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <exception>
#include <filesystem>
#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include "iee/am0205e_animation_x4_test.h"
#include "iee/bridge_transition.h"
#include "iee/creature_sprite_x2.h"
#include "iee/area_animation_clock_diagnostics.h"
#include "iee/area_animation_x4_registry.h"
#include "app_context.h"
#include "area_state.h"
#include "iee/core/hooking.h"
#include "iee/core/area_animation_timeline.h"
#include "iee/core/config.h"
#include "iee/core/logger.h"
#include "iee/core/map_texture_telemetry.h"
#include "iee/core/map_view_burst_telemetry.h"
#include "iee/core/native_occlusion_probe.h"
#include "iee/core/pattern_scanner.h"
#include "iee/core/performance_samples.h"
#include "iee/core/process_resource_telemetry.h"
#include "iee/core/pvr_demand_telemetry.h"
#include "iee/features/tile_render.h"
#include "iee/frame_hook.h"
#include "iee/game/game_types.h"
#include "iee/game/renderer.h"
#include "iee/game/resref_runtime.h"
#include "iee/game/runtime_types_x64.h"
#include "iee/map_page_prewarm.h"
#include "iee/native_occlusion_bridge.h"
#include "iee/shader_probe.h"

namespace iee::hooks {
using LoadAreaFn = void* (*)(void*, void*, unsigned char, unsigned char, unsigned char);
using RenderTextureFn = void (*)(void*, int, void*, int, int, unsigned long);
using DrawColorToneFn = void (*)(int);
using GameStaticRenderBamFn = void (*)(void*, void*, void*);
using VidCellRenderTextureFn = void (*)(int, int, void*, std::uint64_t, void*, std::uint32_t);
using InfinityFxRenderClippingPolysFn = int (*)(void*, int, int, int, void*, void*,
                                                std::uint8_t, std::uint32_t);
using VidPaletteRealizeFn = void (*)(void*, std::uint32_t*, std::uint32_t, void*, std::uint32_t,
                                    std::uint32_t);
using MonsterIcewindRenderFn = void (*)(void*, std::uintptr_t, std::uintptr_t,
                                        std::uintptr_t, std::uintptr_t, std::uintptr_t,
                                        std::uintptr_t, std::uintptr_t, std::uintptr_t,
                                        std::uintptr_t, std::uintptr_t, std::uintptr_t,
                                        std::uintptr_t, std::uintptr_t);
using MonsterRenderFn = MonsterIcewindRenderFn;
using CharacterRenderFn = MonsterIcewindRenderFn;
using GameAreaRenderFn = void (*)(void*, void*);
using DrawFlushGlFn = void (*)();
using CResPvrDemandFn = void* (*)(void*);
using CResPvrUncompressFn = int (*)(void*, std::uint32_t*, const void*, std::uint32_t);
using CResPvrReleaseFn = void (*)(void*);
using CResFileOpenFn = int (*)(void*, const void*, std::uint32_t, void*);

// Hook management - initialize MinHook
// Intentionally explicit lifetime: a static smart-pointer destructor would
// call MinHook from the Windows loader lock if the loader skipped ShutdownBindings.
static core::HookInit* g_hookInit = nullptr;
static core::Hook<LoadAreaFn> g_loadAreaHook;
static core::Hook<RenderTextureFn> g_renderTextureHook;
static core::Hook<DrawColorToneFn> g_drawColorToneHook;
static core::Hook<GameStaticRenderBamFn> g_gameStaticRenderBamHook;
static core::Hook<VidCellRenderTextureFn> g_vidCellRenderTextureHook;
static core::Hook<InfinityFxRenderClippingPolysFn> g_infinityFxRenderClippingPolysHook;
static core::Hook<VidPaletteRealizeFn> g_vidPaletteRealizeHook;
static core::Hook<MonsterRenderFn> g_monsterRenderHook;
static core::Hook<MonsterIcewindRenderFn> g_monsterIcewindRenderHook;
static core::Hook<CharacterRenderFn> g_characterRenderHook;
static core::Hook<GameAreaRenderFn> g_gameAreaRenderHook;
static core::Hook<CResPvrDemandFn> g_pvrDemandHook;
static core::Hook<CResPvrDemandFn> g_resDemandDiagnosticHook;
static core::Hook<CResPvrUncompressFn> g_pvrUncompressHook;
static core::Hook<CResPvrReleaseFn> g_pvrCacheReleaseHook;
static core::Hook<CResFileOpenFn> g_resFileOpenDiagnosticHook;
static std::uintptr_t g_pvrUncompressExpectedReturn{};
static const void* g_pvrCacheEntries{};
static DrawFlushGlFn g_drawFlushGl{};

static AppContext* g_ctx = nullptr;
static am0205e_x4::EngineTextureApi g_am0205eTextureApi{};
static area_animation_x4::EngineTextureApi g_areaAnimationTextureApi{};
static creature_sprite_x2::EngineTextureApi g_creatureSpriteTextureApi{};
static native_occlusion_bridge::EngineTextureApi g_nativeOcclusionTextureApi{};
static const std::byte* g_nativeFxSurfacePools{};
thread_local int g_am0205eRenderDepth = 0;
thread_local int g_am0205eFrameIndex = -1;
thread_local int g_areaAnimationRenderDepth = 0;
thread_local area_animation_x4::FrameHandle g_areaAnimationFrame{};
thread_local core::NativeOcclusionCorrelation* g_nativeOcclusionCorrelation = nullptr;
thread_local core::NativeOcclusionMaskCapture* g_nativeOcclusionMaskCapture = nullptr;
thread_local core::NativeOcclusionSampleGate g_nativeOcclusionSampleGate{};
thread_local std::uint64_t g_nativeOcclusionSampleGeneration = 0;
thread_local map_page_prewarm::PvrConsumeAttempt* g_activePvrConsumeAttempt = nullptr;
thread_local void* g_activePvrConsumeResource = nullptr;
bool g_nativeOcclusionProbeHookEnabled = false;
bool g_nativeOcclusionProbeLoggingEnabled = false;
bool g_nativeOcclusionBridgeEnabled = false;
core::MapViewBurstTelemetry g_mapViewBurstTelemetry;
std::atomic<bool> g_mapViewBurstTelemetryResetRequested{false};

constexpr std::size_t kMaximumCreatureSpriteLayers = 4;
constexpr std::size_t kNoCreatureSpriteLayer = kMaximumCreatureSpriteLayers;
enum class CreatureSpriteOwner : std::uint8_t {
  None,
  Monster,
  MonsterIcewind,
  Character,
};

struct CreatureSpriteLayer {
  creature_sprite_x2::FrameHandle frame{};
  void* cell{};
  void* paletteOwner{};
  creature_sprite_x2::PaletteSnapshot palette{};
  std::uint64_t capturedGeneration{};
  void* capturedOwner{};
  bool captureValid{};
  bool replacementDone{};
};

struct CreatureSpriteScope {
  std::array<CreatureSpriteLayer, kMaximumCreatureSpriteLayers> layers{};
  std::array<creature_sprite_x2::CompositeLayer,
             creature_sprite_x2::kMaximumCompositeLayers>
      composition{};
  std::array<void*, kMaximumCreatureSpriteLayers - 1> unregisteredPaletteOwners{};
  std::size_t layerCount{};
  std::size_t compositionCount{};
  std::size_t unregisteredPaletteOwnerCount{};
  std::size_t pendingLayer{kNoCreatureSpriteLayer};
  std::uint64_t generation{};
  std::uint16_t animationId{};
  CreatureSpriteOwner owner{CreatureSpriteOwner::None};
  std::uint32_t targetRealizes{};
  std::uint32_t foreignRealizes{};
  std::uint32_t unregisteredLayerRealizes{};
  std::uint32_t replacements{};
  bool compositionIncomplete{};
  bool compositeReplacementDone{};
};

thread_local CreatureSpriteScope* g_creatureSpriteScope = nullptr;
thread_local std::uint64_t g_creatureSpriteGeneration = 0;
bool g_creatureSpriteHooksEnabled = false;
bool g_creatureSpriteCharacterHookEnabled = false;
bool g_creatureSpriteMonsterHookEnabled = false;
bool g_creatureSpriteMonsterIcewindHookEnabled = false;
std::uintptr_t g_creatureSpritePaletteReturn{};

// LoadArea can still resolve the outgoing area during a transition. The render
// thread resolves the settled area a moment later and retries this CPU-only
// selection before any animation frame is composed.
static void swap_area_animation_pack(AppContext& ctx, void* infGame) noexcept;

namespace {
enum class AreaCompositionMode : std::uint8_t { None, AM0205EPrototype, Registry };
AreaCompositionMode g_areaCompositionMode = AreaCompositionMode::None;

class CreatureSpriteScopeOverride {
 public:
  explicit CreatureSpriteScopeOverride(CreatureSpriteScope* scope) noexcept
      : previous_(g_creatureSpriteScope) {
    g_creatureSpriteScope = scope;
  }
  ~CreatureSpriteScopeOverride() { g_creatureSpriteScope = previous_; }

  CreatureSpriteScopeOverride(const CreatureSpriteScopeOverride&) = delete;
  CreatureSpriteScopeOverride& operator=(const CreatureSpriteScopeOverride&) = delete;

 private:
  CreatureSpriteScope* previous_{};
};

class NativeOcclusionCorrelationOverride {
 public:
  explicit NativeOcclusionCorrelationOverride(
      core::NativeOcclusionCorrelation* correlation) noexcept
      : previous_(g_nativeOcclusionCorrelation) {
    g_nativeOcclusionCorrelation = correlation;
  }
  ~NativeOcclusionCorrelationOverride() { g_nativeOcclusionCorrelation = previous_; }

  NativeOcclusionCorrelationOverride(const NativeOcclusionCorrelationOverride&) = delete;
  NativeOcclusionCorrelationOverride& operator=(const NativeOcclusionCorrelationOverride&) =
      delete;

 private:
  core::NativeOcclusionCorrelation* previous_{};
};

class NativeOcclusionMaskCaptureOverride {
 public:
  explicit NativeOcclusionMaskCaptureOverride(
      core::NativeOcclusionMaskCapture* capture) noexcept
      : previous_(g_nativeOcclusionMaskCapture) {
    g_nativeOcclusionMaskCapture = capture;
  }
  ~NativeOcclusionMaskCaptureOverride() { g_nativeOcclusionMaskCapture = previous_; }

  NativeOcclusionMaskCaptureOverride(const NativeOcclusionMaskCaptureOverride&) = delete;
  NativeOcclusionMaskCaptureOverride& operator=(const NativeOcclusionMaskCaptureOverride&) =
      delete;

 private:
  core::NativeOcclusionMaskCapture* previous_{};
};

std::uint64_t pack_probe_subject(const std::array<char, 8>& bytes) noexcept {
  std::uint64_t packed = 0;
  for (std::size_t index = 0; index < bytes.size(); ++index) {
    packed |= static_cast<std::uint64_t>(static_cast<unsigned char>(bytes[index])) <<
              (index * 8u);
  }
  return packed;
}

std::string_view native_occlusion_owner_label(core::NativeOcclusionOwner owner) noexcept {
  using Owner = core::NativeOcclusionOwner;
  switch (owner) {
    case Owner::AreaAnimation:
      return "CGameStatic";
    case Owner::Monster:
      return "Monster";
    case Owner::MonsterIcewind:
      return "MonsterIcewind";
    case Owner::Character:
      return "Character";
    default:
      return "None";
  }
}

std::string_view native_occlusion_replacement_label(
    core::NativeOcclusionReplacement replacement) noexcept {
  using Replacement = core::NativeOcclusionReplacement;
  switch (replacement) {
    case Replacement::AreaRegistry:
      return "area-registry";
    case Replacement::AreaPrototype:
      return "area-prototype";
    case Replacement::CreatureSprite:
      return "creature-sprite";
  }
  return "unknown";
}

void log_native_occlusion_sample(const core::NativeOcclusionSample& sample) noexcept {
  try {
    const auto owner = native_occlusion_owner_label(sample.owner);
    const auto replacement = native_occlusion_replacement_label(sample.draw.replacement);
    if (sample.clipping_seen()) {
      const auto& clipping = sample.lastClippingCall;
      LOG_INFO(
          "Native occlusion phase0: owner={} instance=0x{:X} subject=0x{:X}, "
          "clip_calls={} successful_clip_calls={}, native_clip=present "
          "infinity=0x{:X} at ({},{},z={}) "
          "fx_rect=0x{:X} clip_rect=0x{:X} dither={} clip_flags=0x{:X} result={}, "
          "final_draw=({},{}) logical={}x{} draw_flags=0x{:X} native_texture={} "
          "replacement={}",
          owner, sample.ownerKey, sample.subjectId, sample.clippingCallCount,
          sample.successfulClippingCallCount,
          clipping.infinity, clipping.x, clipping.y, clipping.referenceZ, clipping.fxRect,
          clipping.clipRect,
          static_cast<unsigned>(clipping.dither), clipping.flags, clipping.result,
          sample.draw.x, sample.draw.y, sample.draw.logicalWidth, sample.draw.logicalHeight,
          sample.draw.flags, sample.draw.nativeTextureId, replacement);
    } else {
      LOG_INFO(
          "Native occlusion phase0: owner={} instance=0x{:X} subject=0x{:X}, "
          "clip_calls=0 native_clip=absent, final_draw=({},{}) logical={}x{} "
          "draw_flags=0x{:X} native_texture={} replacement={}",
          owner, sample.ownerKey, sample.subjectId, sample.draw.x, sample.draw.y,
          sample.draw.logicalWidth, sample.draw.logicalHeight, sample.draw.flags,
          sample.draw.nativeTextureId, replacement);
    }
  } catch (...) {
    // Diagnostics must never affect the engine render path.
  }
}

std::uint64_t next_creature_sprite_generation() noexcept {
  ++g_creatureSpriteGeneration;
  if (g_creatureSpriteGeneration == 0) ++g_creatureSpriteGeneration;
  return g_creatureSpriteGeneration;
}

bool matches_pattern_at_rva(const core::ModuleSpan& module, std::uintptr_t rva,
                            std::string_view pattern) noexcept {
  std::vector<std::byte> bytes;
  std::vector<bool> mask;
  if (!core::parse_ida_pattern(pattern, bytes, mask) || rva > module.size ||
      bytes.size() > module.size - rva) {
    return false;
  }
  for (std::size_t index = 0; index < bytes.size(); ++index) {
    if (mask[index] && module.base[rva + index] != bytes[index]) return false;
  }
  return true;
}

int current_engine_texture_id(const native_occlusion_bridge::EngineTextureApi& api) noexcept {
  if (!api.glTextureState) return 0;
  std::uint32_t state = 0;
  if (!core::safe_read(api.glTextureState, state)) return 0;
  return static_cast<int>((state >> 21u) & 0x1FFu);
}

bool validate_native_occlusion_bridge_runtime(AppContext& ctx) noexcept {
  g_nativeOcclusionTextureApi = {};
  g_nativeFxSurfacePools = nullptr;
  if (!ctx.cfg.enableNativeOcclusionBridge) return false;
  if (ctx.cfg.enableFullFrameSsaa2x) {
    LOG_WARN(
        "Native occlusion phase1 bridge disabled: diagnostic full-frame SSAA2x "
        "owns glViewport during object-local FBO composition");
    return false;
  }
  if (!ctx.manifest || !ctx.manifest->areaAnimations.enabled) return false;
  const auto module = core::get_module_span(nullptr);
  if (!module) return false;
  const auto& runtime = ctx.manifest->areaAnimations;
  if (!runtime.fxSurfacePool || !runtime.fxSurfacePoolReference ||
      runtime.fxSurfacePoolReferenceSignature.empty() ||
      !matches_pattern_at_rva(*module, runtime.fxSurfacePoolReference,
                              runtime.fxSurfacePoolReferenceSignature)) {
    LOG_WARN("Native occlusion phase1 bridge disabled: FX surface-pool evidence is absent");
    return false;
  }

  const auto* reference = module->base + runtime.fxSurfacePoolReference;
  std::int32_t poolDisplacement = 0;
  if (reference[0] != std::byte{0x48} || reference[1] != std::byte{0x8D} ||
      reference[2] != std::byte{0x05} ||
      !core::safe_read(reference + 3, poolDisplacement) ||
      reference + 7 + poolDisplacement != module->base + runtime.fxSurfacePool) {
    LOG_WARN(
        "Native occlusion phase1 bridge disabled: manifested FX pool reference no "
        "longer resolves to its data span");
    return false;
  }

  constexpr std::size_t kFxPoolBytes = 0x60;
  constexpr std::size_t kTextureDescriptorBytes = 0x28 * 512;
  const auto moduleBase = reinterpret_cast<std::uintptr_t>(module->base);
  auto* textureTable = reinterpret_cast<std::byte*>(moduleBase + runtime.glTextureTable);
  const auto* fxPools = module->base + runtime.fxSurfacePool;
  if (!core::is_read_write_non_executable_section(*module, runtime.fxSurfacePool,
                                                   kFxPoolBytes) ||
      !core::is_writable_non_executable_memory(fxPools, kFxPoolBytes) ||
      !core::is_read_write_non_executable_section(*module, runtime.glTextureTable,
                                                   kTextureDescriptorBytes) ||
      !core::is_writable_non_executable_memory(textureTable,
                                                kTextureDescriptorBytes)) {
    LOG_WARN(
        "Native occlusion phase1 bridge disabled: FX pool or texture table is not "
        "a writable non-executable data span");
    return false;
  }

  constexpr std::array<std::uintptr_t, 3> kExpectedTableOffsets{{0x28, 0x00, 0x0D}};
  for (std::size_t index = 0; index < runtime.glTextureTableReferences.size(); ++index) {
    if (!matches_pattern_at_rva(*module, runtime.glTextureTableReferences[index],
                                runtime.signatures[10 + index])) {
      LOG_WARN(
          "Native occlusion phase1 bridge disabled: texture-table reference {} "
          "signature differs",
          index);
      return false;
    }
    const auto* instruction = module->base + runtime.glTextureTableReferences[index];
    std::int32_t displacement = 0;
    if (!core::safe_read(instruction + 3, displacement) ||
        instruction + 7 + displacement !=
            module->base + runtime.glTextureTable + kExpectedTableOffsets[index]) {
      return false;
    }
  }
  if (!matches_pattern_at_rva(*module, runtime.glTextureSecondarySelectorReference,
                              runtime.signatures[13])) {
    return false;
  }
  std::uint8_t secondaryOffset = 0;
  if (!core::safe_read(module->base + runtime.glTextureSecondarySelectorReference + 5,
                       secondaryOffset) ||
      secondaryOffset != 0x24) {
    return false;
  }

  g_nativeOcclusionTextureApi = {
      .DrawGenTexture =
          reinterpret_cast<native_occlusion_bridge::EngineTextureApi::DrawGenTextureFn>(
              moduleBase + runtime.drawGenTexture),
      .DrawBindTexture = ctx.draw.DrawBindTexture,
      .DrawDeleteTexture =
          reinterpret_cast<native_occlusion_bridge::EngineTextureApi::DrawDeleteTextureFn>(
              moduleBase + runtime.drawDeleteTexture),
      .TexImage = reinterpret_cast<native_occlusion_bridge::EngineTextureApi::TexImageFn>(
          moduleBase + runtime.texImage),
      .glTextureState =
          reinterpret_cast<const std::uint32_t*>(moduleBase + runtime.glTextureState),
      .glTextureTable = textureTable,
  };
  g_nativeFxSurfacePools = fxPools;
  return true;
}

bool read_native_fx_surface(std::uint32_t flags, const void* clipRect,
                            core::NativeFxSurfaceView& out) noexcept {
  out = {};
  if (!g_nativeOcclusionBridgeEnabled || !g_nativeFxSurfacePools || !clipRect ||
      !g_nativeOcclusionTextureApi.glTextureTable) {
    return false;
  }
  struct Rect {
    std::int32_t left{};
    std::int32_t top{};
    std::int32_t right{};
    std::int32_t bottom{};
  } rect{};
  if (!core::safe_read(clipRect, rect)) return false;
  const auto width64 = static_cast<std::int64_t>(rect.right) - rect.left;
  const auto height64 = static_cast<std::int64_t>(rect.bottom) - rect.top;
  if (width64 <= 0 || height64 <= 0 ||
      width64 > (std::numeric_limits<int>::max)() ||
      height64 > (std::numeric_limits<int>::max)()) {
    return false;
  }

  // FXRenderClippingPolys selects the second 0x30-byte allocator only for
  // filter 0x2601: ((~(flags >> 27)) & 1) | 0x2600.
  const bool linearPool = ((~(flags >> 27u)) & 1u) != 0;
  const auto* pool = g_nativeFxSurfacePools + (linearPool ? 0x30 : 0x00);
  std::int32_t pitchPixels = 0;
  std::int32_t originX = 0;
  std::int32_t originY = 0;
  const std::byte* allocation = nullptr;
  std::int32_t textureId = 0;
  if (!core::safe_read(pool + 0x00, pitchPixels) ||
      !core::safe_read(pool + 0x08, originX) ||
      !core::safe_read(pool + 0x0C, originY) ||
      !core::safe_read(pool + 0x20, allocation) ||
      !core::safe_read(pool + 0x28, textureId) || pitchPixels <= 0 || originX < 0 ||
      originY < 0 || !allocation || textureId <= 0 || textureId >= 512) {
    return false;
  }
  const auto* descriptor =
      g_nativeOcclusionTextureApi.glTextureTable +
      static_cast<std::size_t>(textureId) * 0x28;
  std::int32_t backingWidth = 0;
  std::int32_t backingHeight = 0;
  std::uint8_t deletePending = 0;
  if (!core::safe_read(descriptor + 0x04, backingWidth) ||
      !core::safe_read(descriptor + 0x08, backingHeight) ||
      !core::safe_read(descriptor + 0x0D, deletePending) || deletePending != 0 ||
      backingWidth != pitchPixels || backingHeight <= 0) {
    return false;
  }
  const auto width = static_cast<int>(width64);
  const auto height = static_cast<int>(height64);
  if (originX > backingWidth - width || originY > backingHeight - height ||
      pitchPixels > (std::numeric_limits<int>::max)() / 4) {
    return false;
  }
  const auto originPixels = static_cast<std::uint64_t>(originY) *
                                static_cast<std::uint64_t>(pitchPixels) +
                            static_cast<std::uint64_t>(originX);
  if (originPixels > (std::numeric_limits<std::size_t>::max)() / 4u) return false;
  out = {
      .pixels = allocation + static_cast<std::size_t>(originPixels) * 4u,
      .pitchBytes = pitchPixels * 4,
      .width = width,
      .height = height,
  };
  return true;
}

bool is_ar1300(const game::CGameArea* area) noexcept {
  if (!area) return false;
  game::CResRef resref{};
  if (!core::safe_read(&area->m_resref, resref)) return false;
  constexpr std::array<char, 8> kAr1300{{'A', 'R', '1', '3', '0', '0', '\0', '\0'}};
  return resref.m_resRef == kAr1300;
}

bool read_am0205e_frame(void* gameStatic, int& frameIndex) noexcept {
  frameIndex = -1;
  if (!gameStatic || !g_ctx || !g_ctx->manifest) return false;
  const auto& runtime = g_ctx->manifest->areaAnimations;
  if (!runtime.enabled) return false;
  const auto base = reinterpret_cast<std::uintptr_t>(gameStatic);
  std::array<char, 8> resref{};
  std::int16_t currentFrame = -1;
  if (!core::safe_read(reinterpret_cast<const void*>(base + runtime.gameStaticResref), resref) ||
      !core::safe_read(reinterpret_cast<const void*>(base + runtime.gameStaticCurrentFrame),
                       currentFrame)) {
    return false;
  }
  constexpr std::array<char, 8> kTarget{{'A', 'M', '0', '2', '0', '5', 'E', '\0'}};
  if (resref != kTarget || currentFrame < 0 || currentFrame >= 27) return false;
  frameIndex = currentFrame / 3;
  return frameIndex >= 0 && frameIndex < 9;
}

struct ResolvedAreaAnimationFrame {
  area_animation_x4::FrameHandle handle{};
  area_animation_x4::FrameResolution registry{};
  std::array<char, 8> resref{};
  int sequence{-1};
  int slot{-1};
};

struct ResolvedCreatureSpriteFrame {
  creature_sprite_x2::FrameHandle handle{};
  std::array<char, 8> resref{};
  void* cell{};
  std::uint16_t animationId{};
  int sequence{-1};
  int slot{-1};
};

bool is_target_creature_animation(void* animation, CreatureSpriteOwner owner,
                                  std::uint16_t& animationId) noexcept {
  animationId = 0;
  if (!animation || !g_ctx || !g_ctx->manifest || !creature_sprite_x2::ready()) return false;
  const auto& runtime = g_ctx->manifest->areaAnimations;
  if (!runtime.enabled) return false;
  const auto base = reinterpret_cast<std::uintptr_t>(animation);
  if (!core::safe_read(
          reinterpret_cast<const void*>(base + runtime.monsterAnimationId),
          animationId) ||
      !creature_sprite_x2::contains_animation(animationId)) {
    return false;
  }
  switch (owner) {
    case CreatureSpriteOwner::Character:
      return creature_sprite_x2::animation_targets_character(animationId);
    case CreatureSpriteOwner::Monster:
      return creature_sprite_x2::animation_targets_monster(animationId);
    case CreatureSpriteOwner::MonsterIcewind:
      return creature_sprite_x2::animation_targets_monster_icewind(animationId);
    default:
      return false;
  }
}

bool read_registered_creature_cell(std::uint16_t animationId, void* cell,
                                   const char* ownerLabel,
                                   ResolvedCreatureSpriteFrame& resolved) noexcept {
  if (!cell || !g_ctx || !g_ctx->manifest) return false;
  const auto& runtime = g_ctx->manifest->areaAnimations;
  const auto cellBase = reinterpret_cast<std::uintptr_t>(cell);
  std::array<char, 8> resref{};
  std::int16_t currentFrame = -1;
  std::uint16_t currentSequence = 0;
  if (!core::safe_read(reinterpret_cast<const void*>(cellBase + runtime.vidCellResref), resref) ||
      !core::safe_read(reinterpret_cast<const void*>(cellBase + runtime.vidCellCurrentFrame),
                       currentFrame) ||
      !core::safe_read(reinterpret_cast<const void*>(cellBase + runtime.vidCellCurrentSequence),
                       currentSequence)) {
    static std::atomic<bool> unreadableFrameLogged{false};
    if (!unreadableFrameLogged.exchange(true, std::memory_order_relaxed)) {
      LOG_WARN("Target {} CVidCell metadata is unreadable; native rendering retained",
               ownerLabel);
    }
    return false;
  }
  if (!creature_sprite_x2::resolve_frame(animationId, resref, currentSequence,
                                         currentFrame, resolved.handle)) {
    static std::atomic<bool> unresolvedFrameLogged{false};
    if (!unresolvedFrameLogged.exchange(true, std::memory_order_relaxed)) {
      LOG_WARN("Registered creature CVidCell frame could not be resolved: sequence={}, slot={}; "
               "native rendering retained",
               currentSequence, currentFrame);
    }
    return false;
  }
  resolved.resref = resref;
  resolved.cell = cell;
  resolved.animationId = animationId;
  resolved.sequence = currentSequence;
  resolved.slot = currentFrame;
  return true;
}

bool read_creature_sprite_frame(void* animation, CreatureSpriteOwner owner,
                                ResolvedCreatureSpriteFrame& resolved) noexcept {
  if (!animation || !g_ctx || !g_ctx->manifest) return false;
  const auto& runtime = g_ctx->manifest->areaAnimations;
  const auto base = reinterpret_cast<std::uintptr_t>(animation);
  std::uint16_t animationId = 0;
  void* cell = nullptr;
  if (!is_target_creature_animation(animation, owner, animationId)) return false;
  const auto currentCellOffset = owner == CreatureSpriteOwner::Character
                                     ? runtime.characterCurrentCell
                                     : runtime.monsterCurrentCell;
  const auto ownerLabel = owner == CreatureSpriteOwner::Character
                              ? "CGameAnimationTypeCharacter"
                          : owner == CreatureSpriteOwner::Monster
                              ? "CGameAnimationTypeMonster"
                              : "CGameAnimationTypeMonsterIcewind";
  if (!core::safe_read(reinterpret_cast<const void*>(base + currentCellOffset), cell) ||
      !cell) {
    static std::atomic<bool> unreadableCellLogged{false};
    if (!unreadableCellLogged.exchange(true, std::memory_order_relaxed)) {
      LOG_WARN("Target {} body CVidCell is unavailable; native rendering retained", ownerLabel);
    }
    return false;
  }
  if (!read_registered_creature_cell(animationId, cell, ownerLabel, resolved)) {
    return false;
  }
  static std::array<std::atomic<bool>, 65'536> animationReachedLogged{};
  if (!animationReachedLogged[animationId].exchange(true,
                                                     std::memory_order_relaxed)) {
    LOG_INFO("Creature sprite animation 0x{:04X} reached {}::Render with a registered "
             "body CVidCell",
             animationId, ownerLabel);
  }
  return true;
}

bool append_creature_sprite_layer(CreatureSpriteScope& scope,
                                  const ResolvedCreatureSpriteFrame& resolved) noexcept {
  if (!g_ctx || !g_ctx->manifest || !resolved.cell ||
      scope.layerCount >= scope.layers.size()) {
    return false;
  }
  for (std::size_t index = 0; index < scope.layerCount; ++index) {
    if (scope.layers[index].cell == resolved.cell) return false;
  }
  auto& layer = scope.layers[scope.layerCount++];
  layer.frame = resolved.handle;
  layer.cell = resolved.cell;
  layer.paletteOwner = reinterpret_cast<std::byte*>(resolved.cell) +
                       g_ctx->manifest->areaAnimations.vidCellPalette;
  return true;
}

bool append_unregistered_palette_owner(CreatureSpriteScope& scope, void* cell) noexcept {
  if (!g_ctx || !g_ctx->manifest || !cell ||
      scope.unregisteredPaletteOwnerCount >= scope.unregisteredPaletteOwners.size()) {
    return false;
  }
  auto* owner = reinterpret_cast<std::byte*>(cell) +
                g_ctx->manifest->areaAnimations.vidCellPalette;
  for (std::size_t index = 0; index < scope.layerCount; ++index) {
    if (scope.layers[index].paletteOwner == owner) return false;
  }
  for (std::size_t index = 0; index < scope.unregisteredPaletteOwnerCount; ++index) {
    if (scope.unregisteredPaletteOwners[index] == owner) return false;
  }
  scope.unregisteredPaletteOwners[scope.unregisteredPaletteOwnerCount++] = owner;
  return true;
}

bool read_area_animation_frame(void* gameStatic, ResolvedAreaAnimationFrame& resolved) noexcept {
  if (!gameStatic || !g_ctx || !g_ctx->manifest) return false;
  const auto& runtime = g_ctx->manifest->areaAnimations;
  if (!runtime.enabled) return false;
  const auto base = reinterpret_cast<std::uintptr_t>(gameStatic);
  std::array<char, 8> resref{};
  std::int16_t currentFrame = -1;
  std::int16_t currentSequence = -1;
  if (!core::safe_read(reinterpret_cast<const void*>(base + runtime.gameStaticResref), resref) ||
      !core::safe_read(reinterpret_cast<const void*>(base + runtime.gameStaticCurrentFrame),
                       currentFrame) ||
      !core::safe_read(reinterpret_cast<const void*>(base + runtime.gameStaticCurrentSequence),
                       currentSequence)) {
    return false;
  }
  // The raw ARE position distinguishes two occurrences of one resref, which is what lets each of
  // them carry its own occlusion. CGameStatic stores drawingY = ARE.y + ARE.height, so subtract
  // height before resolving the registry. The three offsets are optional on purpose: a build
  // without them, or an object whose fields cannot be read safely, falls back to resref-only
  // matching rather than failing the whole animation.
  int worldX = area_animation_x4::kAnyWorldPosition;
  int worldY = area_animation_x4::kAnyWorldPosition;
  if (runtime.gameStaticPositionX && runtime.gameStaticPositionY && runtime.gameStaticHeight) {
    std::int32_t positionX = 0;
    std::int32_t drawingY = 0;
    std::int32_t height = 0;
    if (core::safe_read(reinterpret_cast<const void*>(base + runtime.gameStaticPositionX),
                        positionX) &&
        core::safe_read(reinterpret_cast<const void*>(base + runtime.gameStaticPositionY),
                        drawingY) &&
        core::safe_read(reinterpret_cast<const void*>(base + runtime.gameStaticHeight),
                        height)) {
      if (const auto rawY = game::area_animation_are_y(drawingY, height)) {
        worldX = positionX;
        worldY = *rawY;
      }
    }
  }
  if (!area_animation_x4::resolve_frame(resref, worldX, worldY, currentSequence, currentFrame,
                                        resolved.registry)) {
    return false;
  }
  resolved.handle = resolved.registry.nativeFrame;
  resolved.resref = resref;
  resolved.sequence = currentSequence;
  resolved.slot = currentFrame;
  return true;
}

int read_world_active() noexcept {
  if (!g_ctx) return -1;
  const auto* infGame = g_ctx->infGame.load(std::memory_order_relaxed);
  if (!infGame) return -1;
  constexpr auto kWorldActiveOffset =
      offsetof(game::CInfGame, m_worldTime) + offsetof(game::CTimerWorld, m_active);
  std::uint8_t active = 0;
  if (!core::safe_read(reinterpret_cast<const std::byte*>(infGame) + kWorldActiveOffset,
                       active)) {
    return -1;
  }
  return active != 0 ? 1 : 0;
}

std::atomic<std::uint64_t> g_requestedAreaTimelineGeneration{1};
std::uint64_t g_activeAreaTimelineGeneration{};
core::AreaAnimationTimelineClock g_areaTimelineClock;
bool g_areaTimelineActivationLogged{};

void request_area_timeline_generation() noexcept {
  g_requestedAreaTimelineGeneration.fetch_add(1, std::memory_order_release);
}

void select_area_timeline_frame(void* instance, int worldActive,
                                ResolvedAreaAnimationFrame& resolved) noexcept {
  if (!instance || !resolved.registry.timeline.enabled || !frame::boundary_available()) return;
  try {
    const auto frequency = frame::clock_frequency();
    const auto now = frame::clock_ticks();
    const auto epoch = frame::frame_count();
    if (frequency <= 0 || now <= 0 || epoch == 0) return;

    const auto generation =
        g_requestedAreaTimelineGeneration.load(std::memory_order_acquire);
    if (generation != g_activeAreaTimelineGeneration) {
      g_areaTimelineClock.begin_area(generation);
      g_activeAreaTimelineGeneration = generation;
    }

    const auto& timing = resolved.registry.timeline;
    const auto selection = g_areaTimelineClock.select(
        {.instance = reinterpret_cast<std::uintptr_t>(instance),
         .resref = resolved.resref,
         .sequence = resolved.sequence,
         .nativeSlot = resolved.slot,
         .presentationEpoch = epoch,
         .clockTicks = now,
         .ticksPerSecond = frequency,
         .worldActive = worldActive,
         .nativeFpsNumerator = timing.nativeFpsNumerator,
         .nativeFpsDenominator = timing.nativeFpsDenominator,
         .targetFpsNumerator = timing.targetFpsNumerator,
         .targetFpsDenominator = timing.targetFpsDenominator,
         .timelinePhaseCount = timing.phaseCount});
    if (!selection.valid) return;
    area_animation_x4::FrameHandle timelineFrame{};
    if (!area_animation_x4::resolve_timeline_frame(resolved.registry, resolved.sequence,
                                                    selection.phase, timelineFrame)) {
      return;
    }
    resolved.handle = timelineFrame;
    if (!g_areaTimelineActivationLogged) {
      g_areaTimelineActivationLogged = true;
      LOG_INFO(
          "Area-animation TimedTimeline active: native={}/{}, target={}/{}, phases={}, "
          "QPC pause-aware scheduler with native fallback",
          timing.nativeFpsNumerator, timing.nativeFpsDenominator,
          timing.targetFpsNumerator, timing.targetFpsDenominator, timing.phaseCount);
    }
  } catch (...) {
    // The exact native frame selected by the registry remains the fallback.
  }
}

bool validate_area_animation_runtime(AppContext& ctx, const char* label) noexcept {
  if (!ctx.manifest || !ctx.manifest->areaAnimations.enabled) {
    LOG_WARN("{} composition hook is unavailable for build {}", label,
             ctx.manifest ? ctx.manifest->buildId : "<none>");
    return false;
  }
  const auto module = core::get_module_span(nullptr);
  if (!module) {
    LOG_WARN("{} composition hook skipped: game module span is unavailable", label);
    return false;
  }
  const auto& runtime = ctx.manifest->areaAnimations;
  const std::array<std::uintptr_t, 6> rvas{{
      runtime.gameStaticRenderBam,
      runtime.vidCellRenderTexture,
      runtime.drawDeleteTexture,
      runtime.drawGenTexture,
      runtime.drawGetRenderer,
      runtime.texImage,
  }};
  for (std::size_t index = 0; index < rvas.size(); ++index) {
    if (!matches_pattern_at_rva(*module, rvas[index], runtime.signatures[index])) {
      LOG_WARN("{} composition hook skipped: signature {} differs at RVA 0x{:X}", label,
               index, rvas[index]);
      return false;
    }
  }
  if (runtime.glTextureState > module->size ||
      sizeof(std::uint32_t) > module->size - runtime.glTextureState) {
    LOG_WARN("{} composition hook skipped: GL texture state is outside the module", label);
    return false;
  }
  constexpr auto kRealizedPaletteBytes = sizeof(std::uint32_t) * 256;
  if (runtime.realizedPalette > module->size ||
      kRealizedPaletteBytes > module->size - runtime.realizedPalette) {
    LOG_WARN("{} composition hook skipped: realized palette is outside the module", label);
    return false;
  }
  return true;
}

bool validate_creature_sprite_palette_runtime(AppContext& ctx,
                                              const core::ModuleSpan& module) noexcept {
  if (!ctx.manifest) return false;
  const auto& runtime = ctx.manifest->areaAnimations;
  if (!matches_pattern_at_rva(module, runtime.vidPaletteRealize, runtime.signatures[7])) {
    LOG_WARN(
        "Creature sprite xN hook skipped: CVidPalette::Realize signature differs at "
        "RVA 0x{:X}",
        runtime.vidPaletteRealize);
    return false;
  }
  if (!matches_pattern_at_rva(module, runtime.vidPaletteRealizeCallsite,
                              runtime.signatures[8])) {
    LOG_WARN(
        "Creature sprite xN hook skipped: owner palette callsite signature differs at "
        "RVA 0x{:X}",
        runtime.vidPaletteRealizeCallsite);
    return false;
  }
  for (std::size_t index = 0; index < runtime.glTextureTableReferences.size(); ++index) {
    if (!matches_pattern_at_rva(module, runtime.glTextureTableReferences[index],
                                runtime.signatures[10 + index])) {
      LOG_WARN(
          "Creature sprite xN hook skipped: engine texture-table reference {} "
          "differs at RVA 0x{:X}",
          index, runtime.glTextureTableReferences[index]);
      return false;
    }
  }
  if (!matches_pattern_at_rva(module, runtime.glTextureSecondarySelectorReference,
                              runtime.signatures[13])) {
    LOG_WARN(
        "Creature sprite xN hook skipped: engine secondary-texture selector "
        "differs at RVA 0x{:X}",
        runtime.glTextureSecondarySelectorReference);
    return false;
  }
  std::uint8_t secondaryFieldOffset = 0;
  if (!core::safe_read(module.base + runtime.glTextureSecondarySelectorReference + 5,
                       secondaryFieldOffset) ||
      secondaryFieldOffset != 0x24) {
    LOG_WARN(
        "Creature sprite xN hook skipped: engine secondary-texture selector no "
        "longer reads descriptor field +0x24");
    return false;
  }
  constexpr auto kPaletteBytes = sizeof(std::uint32_t) * 256;
  constexpr auto kEncodingBytes = sizeof(area_animation_x4::NativePixelEncoding);
  constexpr auto kTextureDescriptorStride = std::size_t{0x28};
  constexpr auto kTextureDescriptorCount = std::size_t{512};
  constexpr auto kTextureTableBytes = kTextureDescriptorStride * kTextureDescriptorCount;
  const auto moduleBase = reinterpret_cast<std::uintptr_t>(module.base);
  const auto* paletteAddress = reinterpret_cast<const void*>(moduleBase + runtime.realizedPalette);
  const auto* encodingAddress =
      reinterpret_cast<const void*>(moduleBase + runtime.nativeTextureFormat);
  const auto* textureTableAddress =
      reinterpret_cast<const void*>(moduleBase + runtime.glTextureTable);
  if (!core::is_read_write_non_executable_section(module, runtime.realizedPalette,
                                                   kPaletteBytes) ||
      !core::is_writable_non_executable_memory(paletteAddress, kPaletteBytes)) {
    LOG_WARN(
        "Creature sprite xN hook skipped: realized palette RVA 0x{:X} is not a "
        "writable non-executable data span",
        runtime.realizedPalette);
    return false;
  }
  if (!core::is_read_write_non_executable_section(module, runtime.nativeTextureFormat,
                                                   kEncodingBytes) ||
      !core::is_writable_non_executable_memory(encodingAddress, kEncodingBytes)) {
    LOG_WARN(
        "Creature sprite xN hook skipped: native pixel encoding globals are not a "
        "writable non-executable data span");
    return false;
  }
  if (!core::is_read_write_non_executable_section(module, runtime.glTextureTable,
                                                   kTextureTableBytes) ||
      !core::is_writable_non_executable_memory(textureTableAddress,
                                               kTextureTableBytes)) {
    LOG_WARN(
        "Creature sprite xN hook skipped: engine texture descriptor table is not a "
        "writable non-executable data span");
    return false;
  }

  constexpr std::array<std::uintptr_t, 3> kExpectedTableOffsets{{0x28, 0x00, 0x0D}};
  for (std::size_t index = 0; index < runtime.glTextureTableReferences.size(); ++index) {
    const auto* instruction =
        module.base + runtime.glTextureTableReferences[index];
    std::int32_t displacement = 0;
    if (!core::safe_read(instruction + 3, displacement) ||
        instruction + 7 + displacement !=
            module.base + runtime.glTextureTable + kExpectedTableOffsets[index]) {
      LOG_WARN(
          "Creature sprite xN hook skipped: engine texture-table reference {} no "
          "longer resolves to the manifested descriptor field",
          index);
      return false;
    }
  }

  const auto* callsite = module.base + runtime.vidPaletteRealizeCallsite;
  std::int32_t paletteDisplacement = 0;
  if (!core::safe_read(callsite + 3, paletteDisplacement)) return false;
  const auto* callsitePalette = callsite + 7 + paletteDisplacement;
  const auto* callTarget = core::rel32_target_checked(callsite + 13, 0xE8, 1, 5);
  if (callsitePalette != module.base + runtime.realizedPalette ||
      callTarget != module.base + runtime.vidPaletteRealize) {
    LOG_WARN(
        "Creature sprite xN hook skipped: palette owner callsite no longer targets the "
        "manifest scratch/Realize pair");
    return false;
  }
  return true;
}

bool prepare_area_animation_composition_hooks(AppContext& ctx) noexcept {
  // With per-area packs nothing is resident until the first LoadArea, so readiness
  // cannot gate installation. The render path already fails closed: resolve_frame()
  // returns false while no pack is loaded and the engine draws its own BAM.
  if (!ctx.cfg.enableAreaAnimationX4) return false;
  if (!area_animation_x4::ready() && !area_animation_x4::per_area_packs_active()) return false;
  if (!validate_area_animation_runtime(ctx, "Area-animation x4")) return false;
  const auto module = core::get_module_span(nullptr);
  if (!module) return false;
  const auto moduleBase = reinterpret_cast<std::uintptr_t>(module->base);
  const auto& runtime = ctx.manifest->areaAnimations;
  g_areaAnimationTextureApi = {
      .DrawGenTexture =
          reinterpret_cast<area_animation_x4::EngineTextureApi::DrawGenTextureFn>(
              moduleBase + runtime.drawGenTexture),
      .DrawBindTexture = ctx.draw.DrawBindTexture,
      .DrawDeleteTexture =
          reinterpret_cast<area_animation_x4::EngineTextureApi::DrawDeleteTextureFn>(
              moduleBase + runtime.drawDeleteTexture),
      .TexImage = reinterpret_cast<area_animation_x4::EngineTextureApi::TexImageFn>(
          moduleBase + runtime.texImage),
      .DrawGetRenderer =
          reinterpret_cast<area_animation_x4::EngineTextureApi::DrawGetRendererFn>(
              moduleBase + runtime.drawGetRenderer),
      .glTextureState = reinterpret_cast<const std::uint32_t*>(
          moduleBase + runtime.glTextureState),
  };
  return true;
}

bool prepare_creature_sprite_composition_hooks(AppContext& ctx) noexcept {
  g_creatureSpriteCharacterHookEnabled = false;
  g_creatureSpriteMonsterHookEnabled = false;
  g_creatureSpriteMonsterIcewindHookEnabled = false;
  g_creatureSpritePaletteReturn = 0;
  if (!ctx.cfg.creature_sprite_upscale_enabled() || !creature_sprite_x2::ready()) return false;
  if (!validate_area_animation_runtime(ctx, "Creature sprite xN")) return false;
  const auto module = core::get_module_span(nullptr);
  if (!module || !ctx.manifest) return false;
  const auto& runtime = ctx.manifest->areaAnimations;
  if (!validate_creature_sprite_palette_runtime(ctx, *module)) return false;
  const bool targetsCharacter = creature_sprite_x2::targets_character();
  const bool targetsMonster = creature_sprite_x2::targets_monster();
  const bool targetsMonsterIcewind =
      creature_sprite_x2::targets_monster_icewind();
  if (!targetsCharacter && !targetsMonster && !targetsMonsterIcewind) {
    LOG_WARN("Creature sprite xN hook skipped: pack has no validated owner scope");
    return false;
  }
  if (targetsCharacter &&
      !matches_pattern_at_rva(*module, runtime.characterRender,
                              runtime.signatures[9])) {
    LOG_WARN(
        "Creature sprite xN hook skipped: CGameAnimationTypeCharacter::Render "
        "signature differs at RVA 0x{:X}",
        runtime.characterRender);
    return false;
  }
  if (targetsMonsterIcewind &&
      !matches_pattern_at_rva(*module, runtime.monsterIcewindRender,
                              runtime.signatures[6])) {
    LOG_WARN(
        "Creature sprite xN hook skipped: CGameAnimationTypeMonsterIcewind::Render "
        "signature differs at RVA 0x{:X}",
        runtime.monsterIcewindRender);
    return false;
  }
  if (targetsMonster &&
      !matches_pattern_at_rva(*module, runtime.monsterRender,
                              runtime.signatures[14])) {
    LOG_WARN(
        "Creature sprite xN hook skipped: CGameAnimationTypeMonster::Render "
        "signature differs at RVA 0x{:X}",
        runtime.monsterRender);
    return false;
  }
  const auto moduleBase = reinterpret_cast<std::uintptr_t>(module->base);
  g_creatureSpritePaletteReturn =
      moduleBase + runtime.vidPaletteRealizeCallsite + 18;
  g_creatureSpriteTextureApi = {
      .DrawGenTexture =
          reinterpret_cast<creature_sprite_x2::EngineTextureApi::DrawGenTextureFn>(
              moduleBase + runtime.drawGenTexture),
      .DrawBindTexture = ctx.draw.DrawBindTexture,
      .DrawDeleteTexture =
          reinterpret_cast<creature_sprite_x2::EngineTextureApi::DrawDeleteTextureFn>(
              moduleBase + runtime.drawDeleteTexture),
      .TexImage = reinterpret_cast<creature_sprite_x2::EngineTextureApi::TexImageFn>(
          moduleBase + runtime.texImage),
      .DrawGetRenderer =
          reinterpret_cast<creature_sprite_x2::EngineTextureApi::DrawGetRendererFn>(
              moduleBase + runtime.drawGetRenderer),
      .glTextureState = reinterpret_cast<const std::uint32_t*>(
          moduleBase + runtime.glTextureState),
      .glTextureTable = reinterpret_cast<std::byte*>(
          moduleBase + runtime.glTextureTable),
      .realizedPalette = reinterpret_cast<const std::uint32_t*>(
          moduleBase + runtime.realizedPalette),
      .nativePixelEncoding =
          reinterpret_cast<const area_animation_x4::NativePixelEncoding*>(
              moduleBase + runtime.nativeTextureFormat),
  };
  // Publish owner selection only after every required signature and shared
  // palette/texture dependency has passed. A mixed catalog is all-or-nothing.
  g_creatureSpriteCharacterHookEnabled = targetsCharacter;
  g_creatureSpriteMonsterHookEnabled = targetsMonster;
  g_creatureSpriteMonsterIcewindHookEnabled = targetsMonsterIcewind;
  return true;
}

bool prepare_am0205e_composition_hooks(AppContext& ctx) noexcept {
  if (!ctx.cfg.enableAM0205EAnimationX4Test || !am0205e_x4::ready()) return false;
  if (!validate_area_animation_runtime(ctx, "AM0205E x4")) return false;
  const auto module = core::get_module_span(nullptr);
  if (!module) return false;
  const auto moduleBase = reinterpret_cast<std::uintptr_t>(module->base);
  const auto& runtime = ctx.manifest->areaAnimations;
  g_am0205eTextureApi = {
      .DrawGenTexture = reinterpret_cast<am0205e_x4::EngineTextureApi::DrawGenTextureFn>(
          moduleBase + runtime.drawGenTexture),
      .DrawBindTexture = ctx.draw.DrawBindTexture,
      .DrawDeleteTexture =
          reinterpret_cast<am0205e_x4::EngineTextureApi::DrawDeleteTextureFn>(
              moduleBase + runtime.drawDeleteTexture),
      .TexImage = reinterpret_cast<am0205e_x4::EngineTextureApi::TexImageFn>(
          moduleBase + runtime.texImage),
      .DrawGetRenderer = reinterpret_cast<am0205e_x4::EngineTextureApi::DrawGetRendererFn>(
          moduleBase + runtime.drawGetRenderer),
      .glTextureState = reinterpret_cast<const std::uint32_t*>(
          moduleBase + runtime.glTextureState),
  };
  return true;
}

void record_render_performance(const AppContext& ctx, bool handled,
                               long long elapsedTicks) noexcept {
  if (!ctx.cfg.enablePerformanceLogging || elapsedTicks < 0) return;

  try {
    static const long long frequency = [] {
      LARGE_INTEGER value{};
      return QueryPerformanceFrequency(&value) ? value.QuadPart : 0LL;
    }();
    if (frequency <= 0) return;

    struct Window {
      long long startedAt{};
      long long totalTicks{};
      long long maximumTicks{};
      unsigned long long calls{};
      unsigned long long handledCalls{};
      unsigned long long activeFrame{};
      long long activeFrameTicks{};
      std::uint64_t areaGeneration{};
      core::PerformanceSamples<2048> frameCpuMs;
      core::ProcessResourceSnapshot processResourceBaseline{};

      void finish_frame(double ticksToMilliseconds) noexcept {
        if (activeFrame != 0) {
          frameCpuMs.add(static_cast<double>(activeFrameTicks) * ticksToMilliseconds);
        }
        activeFrameTicks = 0;
      }

      void reset(long long nextStart) noexcept {
        startedAt = nextStart;
        totalTicks = 0;
        maximumTicks = 0;
        calls = 0;
        handledCalls = 0;
        activeFrame = 0;
        activeFrameTicks = 0;
        frameCpuMs.reset();
        processResourceBaseline = core::capture_process_resource_snapshot();
      }
    };
    static Window window;

    LARGE_INTEGER now{};
    if (!QueryPerformanceCounter(&now)) return;
    const auto areaGeneration =
        ctx.performanceAreaGeneration.load(std::memory_order_relaxed);
    if (window.areaGeneration != areaGeneration) {
      window.reset(now.QuadPart);
      window.areaGeneration = areaGeneration;
    }
    if (window.startedAt == 0) window.reset(now.QuadPart);
    window.totalTicks += elapsedTicks;
    window.maximumTicks = (std::max)(window.maximumTicks, elapsedTicks);
    ++window.calls;
    if (handled) ++window.handledCalls;

    const auto frameNumber = frame::frame_count();
    const double ticksToMilliseconds = 1000.0 / static_cast<double>(frequency);
    g_mapViewBurstTelemetry.record_render_texture_cpu(
        frameNumber, static_cast<double>(elapsedTicks) * ticksToMilliseconds);
    if (frameNumber != 0 && frameNumber != window.activeFrame) {
      window.finish_frame(ticksToMilliseconds);
      window.activeFrame = frameNumber;
    }
    if (frameNumber != 0) window.activeFrameTicks += elapsedTicks;

    constexpr long long kReportSeconds = 5;
    if (now.QuadPart - window.startedAt < frequency * kReportSeconds) return;

    const double ticksToMicroseconds = 1'000'000.0 / static_cast<double>(frequency);
    const double averageMicroseconds = static_cast<double>(window.totalTicks) *
                                       ticksToMicroseconds / static_cast<double>(window.calls);
    const double maximumMicroseconds =
        static_cast<double>(window.maximumTicks) * ticksToMicroseconds;
    const auto frameSummary = window.frameCpuMs.summarize();
    const auto readability = core::take_readability_stats();
    const auto textureStats = game::take_texture_configuration_stats();
    const auto tileStats = features::tile_render_telemetry_snapshot();
    const auto glStats = core::gl_texture_telemetry_snapshot();
    const auto pvrStats = core::pvr_demand_telemetry_snapshot();
    const auto areaAnimationTextureStats =
        area_animation_x4::texture_cache_telemetry_snapshot();
    const auto areaAnimationCacheBudgetSimulation =
        area_animation_x4::cache_budget_simulation_snapshot();
    const auto processResources = core::capture_process_resource_snapshot();
    const auto wed = ctx.wed.load(std::memory_order_acquire);
    const auto area = wed ? wed->areaResrefView() : std::string_view{"?"};
    LOG_INFO(
        "RenderTexture enhancement perf: calls={}, handled={}, delegated={}, avg={:.2f}us, "
        "max={:.2f}us; per-frame CPU samples={}, avg={:.2f}ms, p95={:.2f}ms, max={:.2f}ms "
        "over {}s; safe-read cache hits={}, VirtualQuery calls={}; texture config calls={}, "
        "cacheHits={}, configured={}, latchedFailures={}, evictions={}",
        window.calls, window.handledCalls, window.calls - window.handledCalls, averageMicroseconds,
        maximumMicroseconds, frameSummary.count, frameSummary.average, frameSummary.percentile95,
        frameSummary.maximum, kReportSeconds, readability.cacheHits, readability.virtualQueries,
        textureStats.calls, textureStats.cacheHits, textureStats.configured,
        textureStats.latchedFailures, textureStats.evictions);
    LOG_INFO(
        "Map texture telemetry (area total): generation={}, area={}, ignoredNoOpLoadAreaCalls={}, "
        "decodedTileDraws={}, tablePagesObserved={}, negativeTablePageSamples={}, "
        "tablePageAboveCapacitySamples={}, sourceTextureIdsObserved={}, "
        "sourceTextureCapacityMisses={}; glUncompressedCalls={}, glUncompressedKnownBytes={}, "
        "glUncompressedUnknownByteCalls={}; glCompressedCalls={}, glCompressedBytes={}, "
        "glCompressedBaseLevelCalls={}, glLargeS3tcBaseLevelCalls={}, "
        "glLargeS3tcBaseLevelBytes={}; glDeleteCalls={}, glDeletedTextureNames={}",
        areaGeneration, area,
        ctx.performanceNoOpLoadAreaCalls.load(std::memory_order_relaxed),
        tileStats.decodedTileDraws, tileStats.distinctTablePagesObserved,
        tileStats.negativeTablePageSamples, tileStats.tablePageAboveCapacitySamples,
        tileStats.sourceTextureIdsObserved, tileStats.sourceTextureCapacityMisses,
        glStats.uncompressedUploadCalls, glStats.uncompressedKnownBytes,
        glStats.uncompressedUnknownByteCalls, glStats.compressedUploadCalls,
        glStats.compressedUploadBytes, glStats.compressedBaseLevelCalls,
        glStats.largeS3tcBaseLevelCalls, glStats.largeS3tcBaseLevelBytes,
        glStats.deleteCalls, glStats.deletedTextureNames);
    constexpr double kNanosecondsToMilliseconds = 1.0 / 1'000'000.0;
    LOG_INFO(
        "PVR demand phase telemetry (area total): generation={}, area={}, calls={}, "
        "materializations={}, ioMeasuredMaterializations={}, textureCreations={}, "
        "readOperations={}, readBytes={}, demandMs={:.3f}, textureGenerationCalls={}, "
        "textureGenerationMs={:.3f}, compressedUploadCalls={}, compressedUploadMs={:.3f}, "
        "residualMs={:.3f}; allGlTextureGenerationCalls={}, allGlGeneratedTextureNames={}, "
        "allGlTextureGenerationMs={:.3f}, allGlCompressedUploadMs={:.3f}, "
        "maximumGlCompressedUploadMs={:.3f}",
        areaGeneration, area, pvrStats.calls, pvrStats.materializations,
        pvrStats.ioMeasuredMaterializations, pvrStats.textureCreations,
        pvrStats.readOperations, pvrStats.readBytes,
        pvrStats.demandNanoseconds * kNanosecondsToMilliseconds,
        pvrStats.textureGenerationCalls,
        pvrStats.textureGenerationNanoseconds * kNanosecondsToMilliseconds,
        pvrStats.compressedUploadCalls,
        pvrStats.compressedUploadNanoseconds * kNanosecondsToMilliseconds,
        pvrStats.residualNanoseconds * kNanosecondsToMilliseconds,
        glStats.textureGenerationCalls, glStats.generatedTextureNames,
        glStats.textureGenerationNanoseconds * kNanosecondsToMilliseconds,
        glStats.compressedUploadNanoseconds * kNanosecondsToMilliseconds,
        glStats.maximumCompressedUploadNanoseconds * kNanosecondsToMilliseconds);
    const bool processMemoryAvailable =
        window.processResourceBaseline.memoryAvailable && processResources.memoryAvailable;
    const bool processIoAvailable =
        window.processResourceBaseline.ioAvailable && processResources.ioAvailable;
    const auto workingSetWindowDelta =
        processMemoryAvailable
            ? core::signed_resource_delta(window.processResourceBaseline.workingSetBytes,
                                          processResources.workingSetBytes)
            : 0;
    const auto privateWindowDelta =
        processMemoryAvailable
            ? core::signed_resource_delta(window.processResourceBaseline.privateBytes,
                                          processResources.privateBytes)
            : 0;
    const auto pageFaultsWindowDelta =
        processMemoryAvailable
            ? core::monotonic_resource_delta(window.processResourceBaseline.pageFaults,
                                             processResources.pageFaults)
            : 0;
    const auto readOperationsWindowDelta =
        processIoAvailable
            ? core::monotonic_resource_delta(window.processResourceBaseline.readOperations,
                                             processResources.readOperations)
            : 0;
    const auto readTransferBytesWindowDelta =
        processIoAvailable
            ? core::monotonic_resource_delta(window.processResourceBaseline.readTransferBytes,
                                             processResources.readTransferBytes)
            : 0;
    const auto writeOperationsWindowDelta =
        processIoAvailable
            ? core::monotonic_resource_delta(window.processResourceBaseline.writeOperations,
                                             processResources.writeOperations)
            : 0;
    const auto writeTransferBytesWindowDelta =
        processIoAvailable
            ? core::monotonic_resource_delta(window.processResourceBaseline.writeTransferBytes,
                                             processResources.writeTransferBytes)
            : 0;
    LOG_INFO(
        "Process resource telemetry: area={}, reason=periodic, memoryAvailable={}, "
        "workingSetBytes={}, workingSetWindowDeltaBytes={}, peakWorkingSetBytes={}, "
        "privateBytes={}, privateWindowDeltaBytes={}, pageFaultsWindowDelta={}, "
        "ioAvailable={}, readOperationsWindowDelta={}, readTransferBytesWindowDelta={}, "
        "writeOperationsWindowDelta={}, writeTransferBytesWindowDelta={}",
        area, processMemoryAvailable, processResources.workingSetBytes,
        workingSetWindowDelta, processResources.peakWorkingSetBytes,
        processResources.privateBytes, privateWindowDelta, pageFaultsWindowDelta,
        processIoAvailable, readOperationsWindowDelta, readTransferBytesWindowDelta,
        writeOperationsWindowDelta, writeTransferBytesWindowDelta);
    if (areaAnimationTextureStats.active) {
      LOG_INFO(
          "Area-animation GPU cache telemetry: area={}, reason=periodic, capacity={}, "
          "requests={}, hits={}, misses={}, textureNameCreations={}, "
          "textureNameCreationFailures={}, uploadAttempts={}, successfulUploads={}, "
          "failedUploads={}, lruEvictions={}, failedUploadTextureDeletes={}, "
          "contextInvalidatedTextureNames={}, uploadedBaseLevelBytes={}, "
          "residentTextureNames={}, residentBaseLevelBytes={}, peakResidentBaseLevelBytes={}",
          area, areaAnimationTextureStats.capacity, areaAnimationTextureStats.requests,
          areaAnimationTextureStats.hits, areaAnimationTextureStats.misses,
          areaAnimationTextureStats.textureNameCreations,
          areaAnimationTextureStats.textureNameCreationFailures,
          areaAnimationTextureStats.uploadAttempts,
          areaAnimationTextureStats.successfulUploads,
          areaAnimationTextureStats.failedUploads,
          areaAnimationTextureStats.lruEvictions,
          areaAnimationTextureStats.failedUploadTextureDeletes,
          areaAnimationTextureStats.contextInvalidatedTextureNames,
          areaAnimationTextureStats.uploadedBaseLevelBytes,
          areaAnimationTextureStats.residentTextureNames,
          areaAnimationTextureStats.residentBaseLevelBytes,
          areaAnimationTextureStats.peakResidentBaseLevelBytes);
    }
    if (areaAnimationCacheBudgetSimulation.active) {
      for (const auto& profile : areaAnimationCacheBudgetSimulation.profiles) {
        LOG_INFO(
            "Area-animation cache budget simulation: area={}, reason=periodic, "
            "frameCapacity={}, cpuBudgetBytes={}, gpuBudgetBytes={}, gpuEntryLimit={}, "
            "requests={}, distinctFrames={}, predictedFrameReadBytes={}, "
            "predictedUploadBytes={}, cpuRequests={}, cpuHits={}, cpuMisses={}, "
            "cpuEvictions={}, cpuUncacheableRequests={}, cpuResidentEntries={}, "
            "cpuResidentBytes={}, cpuPeakResidentBytes={}, gpuHits={}, gpuMisses={}, "
            "gpuEvictions={}, gpuUncacheableRequests={}, gpuResidentEntries={}, "
            "gpuResidentBytes={}, gpuPeakResidentBytes={}",
            area, areaAnimationCacheBudgetSimulation.frameCapacity,
            profile.cpu.budgetBytes, profile.gpu.budgetBytes, profile.gpu.entryLimit,
            profile.requests, profile.distinctFrames, profile.predictedFrameReadBytes,
            profile.predictedUploadBytes, profile.cpu.requests, profile.cpu.hits,
            profile.cpu.misses, profile.cpu.evictions, profile.cpu.uncacheableRequests,
            profile.cpu.residentEntries, profile.cpu.residentBytes,
            profile.cpu.peakResidentBytes, profile.gpu.hits, profile.gpu.misses,
            profile.gpu.evictions, profile.gpu.uncacheableRequests,
            profile.gpu.residentEntries, profile.gpu.residentBytes,
            profile.gpu.peakResidentBytes);
      }
    }
    window.reset(now.QuadPart);
  } catch (...) {
    // Performance diagnostics must not affect rendering.
  }
}

std::string format_map_view_burst_samples(
    const core::MapViewBurstCapture& capture) {
  std::ostringstream output;
  output << std::fixed << std::setprecision(2);
  for (std::size_t index = 0; index < capture.frameCount; ++index) {
    if (index != 0) output << ';';
    const auto& sample = capture.frames[index];
    output << index << ':' << sample.frame << ',' << sample.viewWorldWidth << 'x'
           << sample.viewWorldHeight << ',' << (sample.viewObserved ? 1 : 0) << ','
           << sample.presentationIntervalMilliseconds << ','
           << sample.renderTextureCpuMilliseconds << ','
           << sample.delta.tileDraws << ',' << sample.delta.tablePagesObserved << ','
           << sample.delta.sourceTextureIdsObserved << ','
           << sample.delta.compressedUploadCalls << ','
           << sample.delta.compressedUploadBytes << ','
           << sample.delta.largeS3tcBaseLevelCalls << ','
           << sample.delta.largeS3tcBaseLevelBytes << ','
           << sample.delta.deleteCalls << ','
           << sample.delta.deletedTextureNames;
  }
  return output.str();
}

std::string format_map_pvr_phase_samples(
    const core::MapViewBurstCapture& capture) {
  constexpr double kNanosecondsToMilliseconds = 1.0 / 1'000'000.0;
  std::ostringstream output;
  output << std::fixed << std::setprecision(3);
  for (std::size_t index = 0; index < capture.frameCount; ++index) {
    if (index != 0) output << ';';
    const auto& sample = capture.frames[index];
    const auto detail =
        core::pvr_demand_frame_detail_snapshot(sample.frame);
    const auto detailName = detail.valid()
                                ? std::string_view(detail.resref.data())
                                : std::string_view{"-"};
    output << index << ':' << sample.frame << ','
           << sample.delta.pvrDemandCalls << ','
           << sample.delta.pvrMaterializations << ','
           << sample.delta.pvrIoMeasuredMaterializations << ','
           << sample.delta.pvrTextureCreations << ','
           << sample.delta.pvrReadOperations << ','
           << sample.delta.pvrReadBytes << ','
           << sample.delta.pvrDemandNanoseconds * kNanosecondsToMilliseconds << ','
           << sample.delta.pvrTextureGenerationCalls << ','
           << sample.delta.pvrTextureGenerationNanoseconds *
                  kNanosecondsToMilliseconds
           << ',' << sample.delta.pvrCompressedUploadCalls << ','
           << sample.delta.pvrCompressedUploadNanoseconds *
                  kNanosecondsToMilliseconds
           << ',' << sample.delta.pvrResidualNanoseconds *
                          kNanosecondsToMilliseconds
           << ',' << sample.delta.compressedUploadNanoseconds *
                          kNanosecondsToMilliseconds
           << ',' << detailName << ',' << detail.width << 'x' << detail.height
           << ',' << detail.demandNanoseconds * kNanosecondsToMilliseconds
           << ',' << detail.textureGenerationNanoseconds *
                          kNanosecondsToMilliseconds
           << ',' << detail.compressedUploadNanoseconds *
                          kNanosecondsToMilliseconds
           << ',' << detail.residualNanoseconds * kNanosecondsToMilliseconds
           << ',' << detail.readBytes << ',' << (detail.ioMeasured ? 1 : 0);
  }
  return output.str();
}

void install_shader_probes_once() {
  // Latch only on success: a transient first-frame failure (partial GL
  // table) must not permanently suppress the probes. Runs on the render
  // thread only, so plain statics are safe.
  static bool installed = false;
  static bool warnedOnce = false;
  static std::uint32_t lastAttemptTick = 0;
  if (installed) {
    return;
  }
  const auto now = GetTickCount();
  if (lastAttemptTick != 0 && now - lastAttemptTick < 1000) {
    return;
  }
  lastAttemptTick = now;
  if (!warnedOnce) {
    probe::log_shader_runtime_capabilities();
  }
  if (probe::install_shader_probes(g_ctx->cfg)) {
    installed = true;
  } else if (!warnedOnce) {
    warnedOnce = true;
    LOG_WARN("GL shader probes were not installed; will retry on subsequent frames");
  }
}

// Publishes the view transform while the engine's transient world-pass
// viewport is coherent.
// The active area is RE-RESOLVED here, not trusted from LoadArea time:
// on transitions the engine can settle the visible-area pointer after
// LoadArea returns, which left the cache on the OLD area (mask glued
// to the screen, or no water at all). When the resolved area differs,
// re-cache the WED from here — the render thread, where the GL upload
// belongs anyway. Throttled so a transiently unreadable WED retries
// once a second instead of every draw.
void publish_view_state(bool force = false, bool flushGpuUpload = true) {
  if (!g_ctx) {
    return;
  }
  static unsigned long long lastPublishedFrame = 0;
  static bool publishedAtFrameZero = false;
  static std::uint32_t lastFallbackPublishTick = 0;
  const auto frameNumber = frame::frame_count();
  if (!force && frameNumber != 0 && frameNumber == lastPublishedFrame) {
    return;
  }
  if (!force && flushGpuUpload && frameNumber == 0) {
    if (frame::boundary_available()) {
      if (publishedAtFrameZero) return;
      publishedAtFrameZero = true;
    } else {
      // Unsupported fallback: coalesce a burst of per-tile Seam calls while
      // still allowing camera state to advance when no swap hook exists.
      const auto now = GetTickCount();
      if (lastFallbackPublishTick != 0 && now - lastFallbackPublishTick < 8) return;
      lastFallbackPublishTick = now;
      // Without a swap hook nothing else advances the safe-read epoch, and a
      // stale readability cache must never outlive engine resource churn.
      core::advance_readability_cache_epoch();
    }
  }
  // A LoadArea CPU-only publication must not consume the render callback's
  // once-per-frame slot; the next Seam callback still owns the queued upload.
  if (flushGpuUpload && frameNumber != 0) {
    lastPublishedFrame = frameNumber;
  }
  if (flushGpuUpload) {
    // DrawColorTone runs inside the world render pass with a current GL
    // context. Flush even when active-area resolution is temporarily
    // unavailable so a queued no-liquid transition clears stale data.
    (void)area::flush_pending_gpu_upload();
  }
  auto* infGame = g_ctx->infGame.load(std::memory_order_relaxed);
  if (!infGame) {
    return;
  }
  const auto* resolved = area::resolve_active_area(infGame, *g_ctx->manifest);
  if (!resolved) {
    return;
  }
  if (resolved != g_ctx->activeArea.load()) {
    static const game::CGameArea* s_lastRefreshTarget = nullptr;
    static std::uint32_t s_lastRefreshTick = 0;
    const auto now = GetTickCount();
    if (resolved != s_lastRefreshTarget || now - s_lastRefreshTick > 1000) {
      s_lastRefreshTarget = resolved;
      s_lastRefreshTick = now;
      LOG_INFO("Active area changed after load; refreshing WED cache from the render thread");
      area::refresh_wed_cache(*g_ctx, infGame);
      // LoadArea may have selected the outgoing area's pack before the engine
      // publishes its settled active-area pointer. Keep the resident animation
      // pack in lockstep with the render-thread area resolution as well.
      swap_area_animation_pack(*g_ctx, infGame);
    }
  }
  if (!g_ctx->wed.load()) {
    return;
  }
  area::ViewTransform view{};
  if (area::read_view_transform(resolved, view)) {
    if (flushGpuUpload && g_ctx->cfg.enablePerformanceLogging &&
        frame::boundary_available()) {
      g_mapViewBurstTelemetry.observe_view(frameNumber, view.viewWorldW,
                                           view.viewWorldH);
    }
    const bool ar1300 = is_ar1300(resolved);
    probe::set_area_view(view.scrollX, view.scrollY, view.viewWorldW, view.viewWorldH);
    bridge::publish_view(view, ar1300);
  }
}
}  // namespace

void on_frame_boundary(unsigned long long frame,
                       double presentationIntervalMilliseconds) noexcept {
  try {
    auto* ctx = g_ctx;
    if (!ctx || !ctx->cfg.enablePerformanceLogging ||
        !frame::boundary_available()) {
      return;
    }
    if (g_mapViewBurstTelemetryResetRequested.exchange(false,
                                                       std::memory_order_acq_rel)) {
      g_mapViewBurstTelemetry.reset();
    }

    const auto tile = features::tile_render_telemetry_snapshot();
    const auto gl = core::gl_texture_telemetry_snapshot();
    const auto pvr = core::pvr_demand_telemetry_snapshot();
    const core::MapViewCumulativeCounters cumulative{
        .tileDraws = tile.decodedTileDraws,
        .tablePagesObserved = tile.distinctTablePagesObserved,
        .sourceTextureIdsObserved = tile.sourceTextureIdsObserved,
        .compressedUploadCalls = gl.compressedUploadCalls,
        .compressedUploadBytes = gl.compressedUploadBytes,
        .compressedUploadNanoseconds = gl.compressedUploadNanoseconds,
        .largeS3tcBaseLevelCalls = gl.largeS3tcBaseLevelCalls,
        .largeS3tcBaseLevelBytes = gl.largeS3tcBaseLevelBytes,
        .deleteCalls = gl.deleteCalls,
        .deletedTextureNames = gl.deletedTextureNames,
        .pvrDemandCalls = pvr.calls,
        .pvrMaterializations = pvr.materializations,
        .pvrIoMeasuredMaterializations = pvr.ioMeasuredMaterializations,
        .pvrTextureCreations = pvr.textureCreations,
        .pvrReadOperations = pvr.readOperations,
        .pvrReadBytes = pvr.readBytes,
        .pvrDemandNanoseconds = pvr.demandNanoseconds,
        .pvrTextureGenerationCalls = pvr.textureGenerationCalls,
        .pvrTextureGenerationNanoseconds = pvr.textureGenerationNanoseconds,
        .pvrCompressedUploadCalls = pvr.compressedUploadCalls,
        .pvrCompressedUploadNanoseconds = pvr.compressedUploadNanoseconds,
        .pvrResidualNanoseconds = pvr.residualNanoseconds,
    };
    const auto capture = g_mapViewBurstTelemetry.finish_frame(
        frame, cumulative, presentationIntervalMilliseconds);
    if (g_mapViewBurstTelemetry.capture_active()) {
      map_page_prewarm::notify_wide_view_expansion();
    }
    if (!capture) return;

    const auto wed = ctx->wed.load(std::memory_order_acquire);
    const auto area = wed ? wed->areaResrefView() : std::string_view{"?"};
    LOG_INFO(
        "Map wide-view burst telemetry: area={}, event={}, thresholdRatio={:.2f}, "
        "expansionWindowFrames={}, "
        "previousView={}x{}, triggerView={}x{}, frameCount={}, "
        "sampleFields=offset:frame,view,viewFresh,presentationMs,renderTextureCpuMs,tileDraws,"
        "newTablePages,newSourceTextures,compressedCalls,compressedBytes,"
        "largeS3tcCalls,largeS3tcBytes,deleteCalls,deletedTextureNames; samples=[{}]",
        area, capture->eventId, core::kMapViewBurstMinimumExpansionRatio,
        core::kMapViewBurstExpansionWindowFrameCount,
        capture->previousViewWorldWidth, capture->previousViewWorldHeight,
        capture->triggerViewWorldWidth, capture->triggerViewWorldHeight,
        capture->frameCount, format_map_view_burst_samples(*capture));
    LOG_INFO(
        "Map PVR demand phase telemetry: area={}, event={}, "
        "sampleFields=offset:frame,demandCalls,materializations,ioMeasuredMaterializations,"
        "textureCreations,readOperations,readBytes,demandMs,textureGenerationCalls,"
        "textureGenerationMs,pvrCompressedUploadCalls,pvrCompressedUploadMs,residualMs,"
        "allGlCompressedUploadMs,slowestResref,slowestDimensions,slowestDemandMs,"
        "slowestTextureGenerationMs,slowestCompressedUploadMs,slowestResidualMs,"
        "slowestReadBytes,slowestIoMeasured; samples=[{}]",
        area, capture->eventId, format_map_pvr_phase_samples(*capture));
  } catch (...) {
    // Buffered performance diagnostics must never affect presentation.
  }
}

static int detour_infinity_fx_render_clipping_polys(
    void* thisPtr, int x, int y, int referenceZ, void* fxRect, void* clipRect,
    std::uint8_t dither, std::uint32_t flags) {
  const auto original = g_infinityFxRenderClippingPolysHook.original();
  core::NativeFxSurfaceView fxSurface{};
  auto* maskCapture = g_nativeOcclusionMaskCapture;
  bool captureArmed = false;
  if (maskCapture) {
    if (read_native_fx_surface(flags, clipRect, fxSurface)) {
      captureArmed = maskCapture->begin_call(fxSurface);
    } else {
      maskCapture->invalidate();
    }
  }
  const int result = original(thisPtr, x, y, referenceZ, fxRect, clipRect, dither, flags);
  if (captureArmed) maskCapture->finish_call(fxSurface, result);
  if (auto* correlation = g_nativeOcclusionCorrelation) {
    correlation->record_clipping({
        .infinity = reinterpret_cast<std::uintptr_t>(thisPtr),
        .x = x,
        .y = y,
        .referenceZ = referenceZ,
        .fxRect = reinterpret_cast<std::uintptr_t>(fxRect),
        .clipRect = reinterpret_cast<std::uintptr_t>(clipRect),
        .dither = dither,
        .flags = flags,
        .result = result,
    });
  }
  return result;
}

static void detour_game_static_render_bam(void* thisPtr, void* gameArea, void* vidMode) {
  ResolvedAreaAnimationFrame resolvedAreaFrame{};
  int frameIndex = -1;
  const bool areaTarget =
      g_areaCompositionMode == AreaCompositionMode::Registry &&
      read_area_animation_frame(thisPtr, resolvedAreaFrame);
  const bool am0205eTarget =
      g_areaCompositionMode == AreaCompositionMode::AM0205EPrototype &&
      read_am0205e_frame(thisPtr, frameIndex);
  const auto previousAreaFrame = g_areaAnimationFrame;
  const int previousFrame = g_am0205eFrameIndex;
  if (areaTarget) {
    const int worldActive = read_world_active();
    area_animation_clock::observe(thisPtr, resolvedAreaFrame.resref, resolvedAreaFrame.sequence,
                                  resolvedAreaFrame.slot, worldActive);
    select_area_timeline_frame(thisPtr, worldActive, resolvedAreaFrame);
    ++g_areaAnimationRenderDepth;
    g_areaAnimationFrame = resolvedAreaFrame.handle;
  }
  if (am0205eTarget) {
    ++g_am0205eRenderDepth;
    g_am0205eFrameIndex = frameIndex;
  }
  constexpr std::array<char, 8> kAm0205e{{'A', 'M', '0', '2', '0', '5', 'E', '\0'}};
  const auto subjectId =
      areaTarget ? pack_probe_subject(resolvedAreaFrame.resref) : pack_probe_subject(kAm0205e);
  core::NativeOcclusionCorrelation nativeOcclusion{
      areaTarget || am0205eTarget ? core::NativeOcclusionOwner::AreaAnimation
                                 : core::NativeOcclusionOwner::None,
      reinterpret_cast<std::uintptr_t>(thisPtr), subjectId};
  // Every CGameStatic invocation masks an outer probe scope. Calls made by an
  // unrelated nested object must not be attributed to this replacement.
  NativeOcclusionCorrelationOverride nativeOcclusionOverride(
      g_nativeOcclusionProbeHookEnabled && (areaTarget || am0205eTarget)
          ? &nativeOcclusion
          : nullptr);
  core::NativeOcclusionMaskCapture nativeOcclusionMask{};
  NativeOcclusionMaskCaptureOverride nativeOcclusionMaskOverride(
      g_nativeOcclusionBridgeEnabled && areaTarget ? &nativeOcclusionMask : nullptr);

  g_gameStaticRenderBamHook.original()(thisPtr, gameArea, vidMode);

  if (am0205eTarget) {
    --g_am0205eRenderDepth;
    g_am0205eFrameIndex = previousFrame;
  }
  if (areaTarget) {
    --g_areaAnimationRenderDepth;
    g_areaAnimationFrame = previousAreaFrame;
  }
}

static void detour_monster_render(
    void* thisPtr, std::uintptr_t a2, std::uintptr_t a3, std::uintptr_t a4,
    std::uintptr_t a5, std::uintptr_t a6, std::uintptr_t a7, std::uintptr_t a8,
    std::uintptr_t a9, std::uintptr_t a10, std::uintptr_t a11, std::uintptr_t a12,
    std::uintptr_t a13, std::uintptr_t a14) {
  ResolvedCreatureSpriteFrame resolved{};
  const bool target =
      read_creature_sprite_frame(thisPtr, CreatureSpriteOwner::Monster, resolved);
  CreatureSpriteScope scope{};
  if (target) {
    scope.generation = next_creature_sprite_generation();
    scope.animationId = resolved.animationId;
    scope.owner = CreatureSpriteOwner::Monster;
    (void)append_creature_sprite_layer(scope, resolved);
  }
  // Every Monster invocation masks an outer creature scope. A nested
  // non-target render must never inherit the outer sprite's palette/frame.
  CreatureSpriteScopeOverride scopeOverride(target ? &scope : nullptr);
  core::NativeOcclusionCorrelation nativeOcclusion{
      target ? core::NativeOcclusionOwner::Monster : core::NativeOcclusionOwner::None,
      reinterpret_cast<std::uintptr_t>(thisPtr), resolved.animationId};
  NativeOcclusionCorrelationOverride nativeOcclusionOverride(
      g_nativeOcclusionProbeHookEnabled && target ? &nativeOcclusion : nullptr);
  core::NativeOcclusionMaskCapture nativeOcclusionMask{};
  NativeOcclusionMaskCaptureOverride nativeOcclusionMaskOverride(
      g_nativeOcclusionBridgeEnabled && target ? &nativeOcclusionMask : nullptr);

  g_monsterRenderHook.original()(thisPtr, a2, a3, a4, a5, a6, a7, a8, a9, a10,
                                 a11, a12, a13, a14);

  if (target) {
    static std::array<std::atomic<bool>, 65'536> noReplacementLogged{};
    if (scope.replacements == 0 &&
        !noReplacementLogged[scope.animationId].exchange(
            true, std::memory_order_relaxed)) {
      LOG_WARN(
          "Registered creature animation 0x{:04X} reached no compatible "
          "owner-scoped palette/texture (target Realize={}, foreign Realize={}); "
          "native BAM rendering remains active",
          scope.animationId, scope.targetRealizes, scope.foreignRealizes);
    }
  }
}

static void detour_monster_icewind_render(
    void* thisPtr, std::uintptr_t a2, std::uintptr_t a3, std::uintptr_t a4,
    std::uintptr_t a5, std::uintptr_t a6, std::uintptr_t a7, std::uintptr_t a8,
    std::uintptr_t a9, std::uintptr_t a10, std::uintptr_t a11, std::uintptr_t a12,
    std::uintptr_t a13, std::uintptr_t a14) {
  ResolvedCreatureSpriteFrame resolved{};
  const bool target =
      read_creature_sprite_frame(thisPtr, CreatureSpriteOwner::MonsterIcewind, resolved);
  CreatureSpriteScope scope{};
  if (target) {
    scope.generation = next_creature_sprite_generation();
    scope.animationId = resolved.animationId;
    scope.owner = CreatureSpriteOwner::MonsterIcewind;
    (void)append_creature_sprite_layer(scope, resolved);
  }
  // Every MonsterIcewind invocation masks an outer creature scope. A nested
  // non-target render must never inherit the outer sprite's palette/frame.
  CreatureSpriteScopeOverride scopeOverride(target ? &scope : nullptr);
  core::NativeOcclusionCorrelation nativeOcclusion{
      target ? core::NativeOcclusionOwner::MonsterIcewind
             : core::NativeOcclusionOwner::None,
      reinterpret_cast<std::uintptr_t>(thisPtr), resolved.animationId};
  NativeOcclusionCorrelationOverride nativeOcclusionOverride(
      g_nativeOcclusionProbeHookEnabled && target ? &nativeOcclusion : nullptr);
  core::NativeOcclusionMaskCapture nativeOcclusionMask{};
  NativeOcclusionMaskCaptureOverride nativeOcclusionMaskOverride(
      g_nativeOcclusionBridgeEnabled && target ? &nativeOcclusionMask : nullptr);

  g_monsterIcewindRenderHook.original()(thisPtr, a2, a3, a4, a5, a6, a7, a8, a9, a10,
                                        a11, a12, a13, a14);

  if (target) {
    static std::array<std::atomic<bool>, 65'536> noReplacementLogged{};
    if (scope.replacements == 0 &&
        !noReplacementLogged[scope.animationId].exchange(
            true, std::memory_order_relaxed)) {
      LOG_WARN(
          "Registered creature animation 0x{:04X} reached no compatible "
          "owner-scoped palette/texture (target Realize={}, foreign Realize={}); "
          "native BAM rendering remains active",
          scope.animationId, scope.targetRealizes, scope.foreignRealizes);
    }
  }
}

static void detour_character_render(
    void* thisPtr, std::uintptr_t a2, std::uintptr_t a3, std::uintptr_t a4,
    std::uintptr_t a5, std::uintptr_t a6, std::uintptr_t a7, std::uintptr_t a8,
    std::uintptr_t a9, std::uintptr_t a10, std::uintptr_t a11, std::uintptr_t a12,
    std::uintptr_t a13, std::uintptr_t a14) {
  ResolvedCreatureSpriteFrame resolved{};
  const bool target =
      read_creature_sprite_frame(thisPtr, CreatureSpriteOwner::Character, resolved);
  CreatureSpriteScope scope{};
  if (target) {
    scope.generation = next_creature_sprite_generation();
    scope.animationId = resolved.animationId;
    scope.owner = CreatureSpriteOwner::Character;
    (void)append_creature_sprite_layer(scope, resolved);
    if (g_ctx && g_ctx->manifest) {
      const auto animationBase = reinterpret_cast<std::uintptr_t>(thisPtr);
      constexpr std::array<const char*, 3> kOverlayLabels{{
          "CGameAnimationTypeCharacter weapon",
          "CGameAnimationTypeCharacter offhand",
          "CGameAnimationTypeCharacter helmet",
      }};
      const auto& runtime = g_ctx->manifest->areaAnimations;
      for (std::size_t index = 0; index < runtime.characterOverlayCells.size(); ++index) {
        void* overlayCell = nullptr;
        if (!core::safe_read(
                reinterpret_cast<const void*>(animationBase + runtime.characterOverlayCells[index]),
                overlayCell)) {
          scope.compositionIncomplete = true;
          continue;
        }
        if (!overlayCell) {
          continue;
        }
        ResolvedCreatureSpriteFrame overlay{};
        if (read_registered_creature_cell(scope.animationId, overlayCell,
                                          kOverlayLabels[index], overlay)) {
          (void)append_creature_sprite_layer(scope, overlay);
        } else {
          (void)append_unregistered_palette_owner(scope, overlayCell);
        }
      }
    }
  }
  // Character rendering is layered. Capture every registered native layer in
  // Realize order, then replace the engine's single final composite draw.
  CreatureSpriteScopeOverride scopeOverride(target ? &scope : nullptr);
  core::NativeOcclusionCorrelation nativeOcclusion{
      target ? core::NativeOcclusionOwner::Character : core::NativeOcclusionOwner::None,
      reinterpret_cast<std::uintptr_t>(thisPtr), resolved.animationId};
  NativeOcclusionCorrelationOverride nativeOcclusionOverride(
      g_nativeOcclusionProbeHookEnabled && target ? &nativeOcclusion : nullptr);
  core::NativeOcclusionMaskCapture nativeOcclusionMask{};
  NativeOcclusionMaskCaptureOverride nativeOcclusionMaskOverride(
      g_nativeOcclusionBridgeEnabled && target ? &nativeOcclusionMask : nullptr);

  g_characterRenderHook.original()(thisPtr, a2, a3, a4, a5, a6, a7, a8, a9, a10,
                                   a11, a12, a13, a14);

  if (target) {
    static std::array<std::atomic<bool>, 65'536> noReplacementLogged{};
    if (scope.replacements == 0 &&
        !noReplacementLogged[scope.animationId].exchange(
            true, std::memory_order_relaxed)) {
      LOG_WARN(
          "Registered character animation 0x{:04X} reached no compatible "
          "owner-scoped composite (target Realize={}, captured layers={}, foreign "
          "Realize={}, unregistered layers={}, incomplete={}); native BAM rendering "
          "remains active",
          scope.animationId, scope.targetRealizes, scope.compositionCount,
          scope.foreignRealizes, scope.unregisteredLayerRealizes,
          scope.compositionIncomplete);
    }
  }
}

static void detour_vid_palette_realize(void* paletteThis, std::uint32_t* realizedOutput,
                                       std::uint32_t flags, void* rangeEffects,
                                       std::uint32_t transparency, std::uint32_t arg6) {
  auto* scope = g_creatureSpriteScope;
  const auto generation = scope ? scope->generation : 0;
  const auto caller = reinterpret_cast<std::uintptr_t>(_ReturnAddress());
  bool ownerCandidate = false;
  std::size_t ownerLayer = kNoCreatureSpriteLayer;
  bool unregisteredOwner = false;
  if (scope) {
    scope->pendingLayer = kNoCreatureSpriteLayer;
    for (std::size_t index = 0; index < scope->layerCount; ++index) {
      if (paletteThis == scope->layers[index].paletteOwner) {
        ownerLayer = index;
        break;
      }
    }
    if (ownerLayer == kNoCreatureSpriteLayer) {
      for (std::size_t index = 0; index < scope->unregisteredPaletteOwnerCount; ++index) {
        if (paletteThis == scope->unregisteredPaletteOwners[index]) {
          unregisteredOwner = true;
          break;
        }
      }
    }
    const bool targetCallsite = caller == g_creatureSpritePaletteReturn;
    if (ownerLayer != kNoCreatureSpriteLayer && targetCallsite) {
      ++scope->targetRealizes;
      scope->layers[ownerLayer].captureValid = false;
      std::uint16_t paletteKind = 0xFFFF;
      ownerCandidate = core::safe_read(reinterpret_cast<const std::byte*>(paletteThis) + 0x20,
                                       paletteKind) &&
                       paletteKind <= 1;
      if (!ownerCandidate && scope->owner == CreatureSpriteOwner::Character) {
        scope->compositionIncomplete = true;
      }
    } else {
      ++scope->foreignRealizes;
      if (scope->owner == CreatureSpriteOwner::Character &&
          (targetCallsite || ownerLayer != kNoCreatureSpriteLayer || unregisteredOwner)) {
        scope->compositionIncomplete = true;
        if (targetCallsite && unregisteredOwner) {
          ++scope->unregisteredLayerRealizes;
        }
      }
    }
  }

  g_vidPaletteRealizeHook.original()(paletteThis, realizedOutput, flags, rangeEffects,
                                      transparency, arg6);

  if (!ownerCandidate || g_creatureSpriteScope != scope || scope->generation != generation ||
      ownerLayer >= scope->layerCount ||
      scope->layers[ownerLayer].paletteOwner != paletteThis) {
    return;
  }
  creature_sprite_x2::PaletteSnapshot captured{};
  if (!creature_sprite_x2::capture_palette_snapshot(realizedOutput, g_creatureSpriteTextureApi,
                                                     captured)) {
    if (scope->owner == CreatureSpriteOwner::Character) {
      scope->compositionIncomplete = true;
    }
    return;
  }
  auto& layer = scope->layers[ownerLayer];
  if (scope->owner == CreatureSpriteOwner::Character) {
    ResolvedCreatureSpriteFrame current{};
    if (!read_registered_creature_cell(scope->animationId, layer.cell,
                                       "CGameAnimationTypeCharacter layer", current) ||
        scope->compositionCount >= scope->composition.size()) {
      scope->compositionIncomplete = true;
      return;
    }
    scope->composition[scope->compositionCount++] = {
        .frame = current.handle,
        .palette = captured,
    };
    return;
  }
  layer.palette = captured;
  layer.capturedOwner = paletteThis;
  layer.capturedGeneration = generation;
  layer.captureValid = true;
  scope->pendingLayer = ownerLayer;
}

static void detour_vid_cell_render_texture(int x, int y, void* sourceRect,
                                           std::uint64_t logicalSize, void* clipRect,
                                           std::uint32_t flags) {
  const auto original = g_vidCellRenderTextureHook.original();
  enum class ReplacementKind : std::uint8_t { None, CreatureSprite, AreaRegistry, AM0205E };
  const int logicalWidth = static_cast<std::int32_t>(logicalSize & 0xFFFFFFFFull);
  const int logicalHeight = static_cast<std::int32_t>(logicalSize >> 32u);
  int previousTextureId = 0;
  int transientCreatureTextureId = 0;
  int transientOcclusionTextureId = 0;
  ReplacementKind replacement = ReplacementKind::None;
  auto* creatureScope = g_creatureSpriteScope;
  if (g_creatureSpriteHooksEnabled && creatureScope) {
    // A creature scope owns this dispatch even when it fails closed. Never fall
    // through to an unrelated area-animation substitution during creature rendering.
    if (creatureScope->owner == CreatureSpriteOwner::Character) {
      if (!creatureScope->compositeReplacementDone &&
          !creatureScope->compositionIncomplete &&
          creatureScope->compositionCount > 0 &&
          creature_sprite_x2::bind_composite_texture(
              creatureScope->composition.data(), creatureScope->compositionCount,
              logicalWidth, logicalHeight, g_creatureSpriteTextureApi,
              previousTextureId, transientCreatureTextureId)) {
        creatureScope->compositeReplacementDone = true;
        ++creatureScope->replacements;
        replacement = ReplacementKind::CreatureSprite;
      }
    } else {
      const auto layerIndex = creatureScope->pendingLayer;
      creatureScope->pendingLayer = kNoCreatureSpriteLayer;
      if (layerIndex < creatureScope->layerCount) {
        auto& layer = creatureScope->layers[layerIndex];
        if (!layer.replacementDone && layer.captureValid &&
            layer.capturedOwner == layer.paletteOwner &&
            layer.capturedGeneration == creatureScope->generation) {
          if (creature_sprite_x2::bind_frame_texture(
                  layer.frame, logicalWidth, logicalHeight, layer.palette,
                  g_creatureSpriteTextureApi, previousTextureId)) {
            layer.replacementDone = true;
            ++creatureScope->replacements;
            replacement = ReplacementKind::CreatureSprite;
          }
        }
      }
    }
  } else if (g_areaCompositionMode == AreaCompositionMode::Registry &&
      g_areaAnimationRenderDepth > 0) {
    if (area_animation_x4::bind_frame_texture(
            g_areaAnimationFrame, g_areaAnimationTextureApi, previousTextureId,
            g_ctx && g_ctx->cfg.enablePerformanceLogging)) {
      replacement = ReplacementKind::AreaRegistry;
    }
  } else if (g_areaCompositionMode == AreaCompositionMode::AM0205EPrototype &&
             g_am0205eRenderDepth > 0 && g_am0205eFrameIndex >= 0) {
    if (am0205e_x4::bind_frame_texture(g_am0205eFrameIndex, g_am0205eTextureApi,
                                      previousTextureId)) {
      replacement = ReplacementKind::AM0205E;
    }
  }
  std::optional<core::NativeOcclusionSample> nativeOcclusionSample;
  if (replacement != ReplacementKind::None && g_nativeOcclusionProbeHookEnabled &&
      g_nativeOcclusionCorrelation) {
    auto probeReplacement = core::NativeOcclusionReplacement::AreaRegistry;
    switch (replacement) {
      case ReplacementKind::CreatureSprite:
        probeReplacement = core::NativeOcclusionReplacement::CreatureSprite;
        break;
      case ReplacementKind::AM0205E:
        probeReplacement = core::NativeOcclusionReplacement::AreaPrototype;
        break;
      case ReplacementKind::AreaRegistry:
      case ReplacementKind::None:
        break;
    }
    nativeOcclusionSample = g_nativeOcclusionCorrelation->correlate_draw({
        .x = x,
        .y = y,
        .logicalWidth = logicalWidth,
        .logicalHeight = logicalHeight,
        .flags = flags,
        .nativeTextureId = previousTextureId,
        .replacement = probeReplacement,
    });
    if (g_nativeOcclusionProbeLoggingEnabled && nativeOcclusionSample) {
      const auto areaGeneration =
          g_requestedAreaTimelineGeneration.load(std::memory_order_acquire);
      if (areaGeneration != g_nativeOcclusionSampleGeneration) {
        g_nativeOcclusionSampleGate.clear();
        g_nativeOcclusionSampleGeneration = areaGeneration;
      }
      if (g_nativeOcclusionSampleGate.accept(*nativeOcclusionSample)) {
        log_native_occlusion_sample(*nativeOcclusionSample);
      }
    }
  }
  const bool legacyBakedAreaOcclusion =
      replacement == ReplacementKind::AreaRegistry &&
      area_animation_x4::has_baked_occurrence_occlusion(g_areaAnimationFrame);
  if (g_nativeOcclusionBridgeEnabled && nativeOcclusionSample &&
      replacement != ReplacementKind::AM0205E && !legacyBakedAreaOcclusion &&
      g_nativeOcclusionMaskCapture) {
    std::vector<std::uint8_t> visibilityTransfer;
    bool changed = false;
    if (g_nativeOcclusionMaskCapture->build_transfer(
            logicalWidth, logicalHeight, visibilityTransfer, changed) &&
        changed) {
      const int replacementTextureId =
          current_engine_texture_id(g_nativeOcclusionTextureApi);
      (void)native_occlusion_bridge::bind_masked_texture(
          visibilityTransfer, logicalWidth, logicalHeight, replacementTextureId,
          g_nativeOcclusionTextureApi, transientOcclusionTextureId);
    } else if (g_nativeOcclusionMaskCapture->successful_call_count() > 0 &&
               (g_nativeOcclusionMaskCapture->width() != logicalWidth ||
                g_nativeOcclusionMaskCapture->height() != logicalHeight)) {
      static std::atomic<bool> dimensionMismatchLogged{false};
      if (!dimensionMismatchLogged.exchange(true, std::memory_order_relaxed)) {
        LOG_WARN(
            "Native occlusion phase1 bridge skipped: captured FX surface {}x{} "
            "does not match final logical texture {}x{}; xN replacement retained",
            g_nativeOcclusionMaskCapture->width(),
            g_nativeOcclusionMaskCapture->height(), logicalWidth, logicalHeight);
      }
    }
  }
  original(x, y, sourceRect, logicalSize, clipRect, flags);
  if (transientOcclusionTextureId > 0) {
    native_occlusion_bridge::finish_masked_texture(
        g_nativeOcclusionTextureApi, previousTextureId, transientOcclusionTextureId);
  }
  if (replacement == ReplacementKind::CreatureSprite) {
    if (transientCreatureTextureId > 0) {
      creature_sprite_x2::finish_composite_texture(
          g_creatureSpriteTextureApi, previousTextureId, transientCreatureTextureId);
    } else {
      creature_sprite_x2::restore_texture(g_creatureSpriteTextureApi, previousTextureId);
    }
  } else if (replacement == ReplacementKind::AreaRegistry) {
    area_animation_x4::restore_texture(g_areaAnimationTextureApi, previousTextureId);
  } else if (replacement == ReplacementKind::AM0205E) {
    am0205e_x4::restore_texture(g_am0205eTextureApi, previousTextureId);
  }
}

// Swaps the resident area-animation pack to the one owned by the area that just loaded.
// CPU-only by contract: LoadArea may not touch OpenGL, so the outgoing textures are
// parked and reclaimed by the next Seam pass.
static void swap_area_animation_pack(AppContext& ctx, void* infGame) noexcept {
  if (!area_animation_x4::per_area_packs_active() || !ctx.manifest) return;
  const auto* area = area::resolve_active_area(infGame, *ctx.manifest);
  if (!area) {
    LOG_DEBUG("LoadArea: no active area resolved; area-animation pack left untouched");
    return;
  }
  const auto* areaBytes = reinterpret_cast<const std::byte*>(area);
  game::CResRef runtimeAreaResref{};
  if (!core::safe_read(areaBytes + offsetof(game::CGameArea, m_resref), runtimeAreaResref)) {
    LOG_DEBUG("LoadArea: area resref unreadable; area-animation pack left untouched");
    return;
  }
  game::ResrefBuffer areaResref{};
  if (!game::read_runtime_resref(runtimeAreaResref.m_resRef.data(), areaResref)) return;
  (void)area_animation_x4::prepare_for_area(game::resref_view(areaResref),
                                            ctx.cfg.enablePerformanceLogging);
}

// LoadArea hook - reset area-specific state for new area detection
static void* detour_load_area(void* thisPtr, void* pAreaNameString, unsigned char a2,
                              unsigned char a3, unsigned char a4) {
  const auto original = g_loadAreaHook.original();
  if (!g_ctx) {
    return original(thisPtr, pAreaNameString, a2, a3, a4);
  }

  auto& ctx = *g_ctx;
  game::ResrefBuffer previousPerformanceArea{};
  bool hadPreviousPerformanceArea = false;
  if (ctx.cfg.enablePerformanceLogging) {
    const auto previousWed = ctx.wed.load(std::memory_order_acquire);
    if (previousWed) {
      previousPerformanceArea = previousWed->areaResref;
      hadPreviousPerformanceArea = !game::resref_view(previousPerformanceArea).empty();
    }
  }
  LARGE_INTEGER totalStart{};
  const bool measurePerformance =
      ctx.cfg.enablePerformanceLogging && QueryPerformanceCounter(&totalStart);
  try {
    area_animation_clock::request_area_generation();
    request_area_timeline_generation();
    bridge::reset_area();
    core::advance_readability_cache_epoch();
    LOG_DEBUG("LoadArea called - resetting scale detection for new area");
    ctx.infGame.store(thisPtr, std::memory_order_relaxed);
    // Invalidate any older refresh before clearing its published CPU state.
    area::reset_gpu_area_state();
    ctx.reset_area_state();
    features::request_tile_render_state_reset();
    game::request_texture_configuration_cache_reset();
    g_mapViewBurstTelemetryResetRequested.store(true, std::memory_order_release);
    map_page_prewarm::request_area_reset();
  } catch (const std::exception& e) {
    LOG_ERROR("LoadArea pre-dispatch failed; continuing with the engine path: {}", e.what());
  } catch (...) {
    LOG_ERROR("LoadArea pre-dispatch failed; continuing with the engine path");
  }

  LARGE_INTEGER engineStart{};
  const bool measureEngine = measurePerformance && QueryPerformanceCounter(&engineStart);
  auto* result = original(thisPtr, pAreaNameString, a2, a3, a4);
  LARGE_INTEGER engineEnd{};
  const bool measuredEngine = measureEngine && QueryPerformanceCounter(&engineEnd);
  try {
    area::refresh_wed_cache(ctx, thisPtr);
    swap_area_animation_pack(ctx, thisPtr);
    // Seed CPU transform state; the next Seam pass owns the GL upload.
    publish_view_state(true, false);
  } catch (const std::exception& e) {
    LOG_ERROR("LoadArea post-dispatch failed; the feature remains disabled for this area: {}",
              e.what());
    area::reset_gpu_area_state();
  } catch (...) {
    LOG_ERROR("LoadArea post-dispatch failed; the feature remains disabled for this area");
    area::reset_gpu_area_state();
  }
  if (ctx.cfg.enablePerformanceLogging) {
    LARGE_INTEGER totalEnd{};
    LARGE_INTEGER frequency{};
    const bool measuredTotal = measurePerformance && QueryPerformanceCounter(&totalEnd);
    const bool haveFrequency = QueryPerformanceFrequency(&frequency) && frequency.QuadPart > 0;
    const auto engineTicks =
        measuredEngine ? engineEnd.QuadPart - engineStart.QuadPart : -1LL;
    const auto currentWed = ctx.wed.load(std::memory_order_acquire);
    const bool haveCurrentArea =
        currentWed && !currentWed->areaResrefView().empty();
    const bool areaChanged =
        hadPreviousPerformanceArea != haveCurrentArea ||
        (hadPreviousPerformanceArea && haveCurrentArea &&
         game::resref_view(previousPerformanceArea) != currentWed->areaResrefView());
    const bool meaningfulLoad = core::is_meaningful_load_area_call(
        areaChanged, measuredEngine && haveFrequency, engineTicks,
        haveFrequency ? frequency.QuadPart : 0);

    const double ticksToMilliseconds =
        haveFrequency ? 1000.0 / static_cast<double>(frequency.QuadPart) : 0.0;
    const double engineMilliseconds =
        measuredEngine && haveFrequency ? static_cast<double>(engineTicks) * ticksToMilliseconds
                                        : -1.0;
    const double totalMilliseconds =
        measuredTotal && haveFrequency
            ? static_cast<double>(totalEnd.QuadPart - totalStart.QuadPart) * ticksToMilliseconds
            : -1.0;
    const auto currentArea =
        haveCurrentArea ? currentWed->areaResrefView() : std::string_view{"?"};

    if (meaningfulLoad) {
      const auto performanceGeneration =
          ctx.performanceAreaGeneration.fetch_add(1, std::memory_order_relaxed) + 1;
      ctx.performanceNoOpLoadAreaCalls.store(0, std::memory_order_relaxed);
      // LoadArea and its post-dispatch preparation are CPU-only. Reset after
      // classification so a same-area no-op cannot erase the real load window.
      core::reset_gl_texture_telemetry();
      core::reset_pvr_demand_telemetry();
      LOG_INFO("Map telemetry marker: generation={}, area={}, overlays={}, base={}x{}",
               performanceGeneration, currentArea,
               currentWed ? currentWed->overlayCount : 0,
               currentWed ? currentWed->baseWidth : 0,
               currentWed ? currentWed->baseHeight : 0);
      LOG_INFO(
          "Map load telemetry: generation={}, area={}, engineLoad={:.2f}ms, "
          "totalDetour={:.2f}ms",
          performanceGeneration, currentArea, engineMilliseconds, totalMilliseconds);
    } else {
      ctx.performanceNoOpLoadAreaCalls.fetch_add(1, std::memory_order_relaxed);
      LOG_DEBUG("Ignored same-area LoadArea telemetry no-op: area={}, engineLoad={:.3f}ms",
                currentArea, engineMilliseconds);
    }
  }
  return result;
}

// DrawColorTone hook: the engine calls this throughout rendering (tile,
// sprite, font tones — decompile 464958/301145/245924). The Seam tone
// marks the tile pass on ALL map types (the engine's vanilla path and our
// upscale path both route through it), making it the reliable per-frame
// publish point with coherent viewport rects. Publish BEFORE the original:
// the original triggers the fpSEAM bind, which is when the uniform feed
// reads these values.
static void detour_draw_color_tone(int mode) {
  try {
    if (mode == static_cast<int>(game::ShaderTone::Seam)) {
      publish_view_state();
      // Seam is the world pass, so a GL context is current here. This is where the
      // texture names parked by an area-pack swap are actually returned to the engine.
      if (g_areaCompositionMode == AreaCompositionMode::Registry &&
          area_animation_x4::has_retired_textures()) {
        area_animation_x4::flush_retired_textures(g_areaAnimationTextureApi,
                                                   g_ctx && g_ctx->cfg.enablePerformanceLogging);
      }
    }
  } catch (...) {
    // Rendering must never depend on IEE diagnostics or uniform state.
  }
  g_drawColorToneHook.original()(mode);
}

std::uint64_t performance_nanoseconds(const LARGE_INTEGER& start,
                                      const LARGE_INTEGER& end) noexcept {
  static const std::int64_t frequency = [] {
    LARGE_INTEGER value{};
    return QueryPerformanceFrequency(&value) ? value.QuadPart : 0;
  }();
  if (frequency <= 0 || start.QuadPart <= 0 || end.QuadPart < start.QuadPart) return 0;
  const auto ticks = static_cast<long double>(end.QuadPart - start.QuadPart);
  return static_cast<std::uint64_t>(
      ticks * 1'000'000'000.0L / static_cast<long double>(frequency));
}

constexpr std::size_t kPvrLifecycleCacheEntries = 128;

struct PvrLifecycleCacheSnapshot {
  bool readable{};
  std::uint32_t occupied{};
  std::int32_t resourceIndex{-1};
  std::uint32_t resourceDuplicates{};
  std::uintptr_t head{};
  std::uintptr_t tail{};
  std::uint64_t fingerprint{};
};

PvrLifecycleCacheSnapshot capture_pvr_lifecycle_cache(void* resource) noexcept {
  PvrLifecycleCacheSnapshot snapshot{};
  if (!g_pvrCacheEntries) return snapshot;
  std::array<void*, kPvrLifecycleCacheEntries> entries{};
  if (!core::safe_read(g_pvrCacheEntries, entries)) return snapshot;
  snapshot.readable = true;
  snapshot.fingerprint = 1469598103934665603ull;
  for (std::size_t index = 0; index < entries.size(); ++index) {
    const auto value = reinterpret_cast<std::uintptr_t>(entries[index]);
    snapshot.fingerprint ^= value;
    snapshot.fingerprint *= 1099511628211ull;
    if (!entries[index]) continue;
    if (snapshot.occupied == 0) snapshot.head = value;
    snapshot.tail = value;
    ++snapshot.occupied;
    if (entries[index] == resource) {
      snapshot.resourceIndex = static_cast<std::int32_t>(index);
      ++snapshot.resourceDuplicates;
    }
  }
  return snapshot;
}

game::ResrefBuffer diagnostic_pvr_resref(void* resource) noexcept {
  game::ResrefBuffer resref{};
  game::CResPVR snapshot{};
  if (!resource || !core::safe_read(resource, snapshot) ||
      !game::read_runtime_resref(snapshot.baseclass_0.resref, resref)) {
    resref[0] = '?';
  }
  return resref;
}

std::string_view consume_outcome_diagnostic_name(
    map_page_prewarm::PvrConsumeOutcome outcome) noexcept {
  using map_page_prewarm::PvrConsumeOutcome;
  switch (outcome) {
    case PvrConsumeOutcome::NotReached:
      return "not-reached";
    case PvrConsumeOutcome::Consumed:
      return "consumed";
    case PvrConsumeOutcome::UnexpectedReturnAddress:
      return "unexpected-return-address";
    case PvrConsumeOutcome::ResourceMismatch:
      return "resource-mismatch";
    case PvrConsumeOutcome::SourceMismatch:
      return "source-mismatch";
    case PvrConsumeOutcome::SizeMismatch:
      return "size-mismatch";
    case PvrConsumeOutcome::CrcMismatch:
      return "crc-mismatch";
    case PvrConsumeOutcome::MemoryRejected:
      return "memory-rejected";
    case PvrConsumeOutcome::InternalError:
      return "internal-error";
  }
  return "unknown";
}

class PvrDemandScopeGuard {
 public:
  PvrDemandScopeGuard() noexcept { core::begin_pvr_demand_scope(); }
  ~PvrDemandScopeGuard() {
    if (!finished_) (void)core::end_pvr_demand_scope();
  }

  [[nodiscard]] core::PvrDemandNestedTimings finish() noexcept {
    if (finished_) return {};
    finished_ = true;
    return core::end_pvr_demand_scope();
  }

 private:
  bool finished_{};
};

class PvrConsumeThreadScope {
 public:
  PvrConsumeThreadScope(void* resource,
                        map_page_prewarm::PvrConsumeAttempt* attempt) noexcept
      : previousAttempt_(g_activePvrConsumeAttempt),
        previousResource_(g_activePvrConsumeResource) {
    // Every nested Demand replaces the current scope, even when it has no
    // candidate. It can therefore never consume an outer Demand's page.
    g_activePvrConsumeAttempt = attempt;
    g_activePvrConsumeResource = resource;
  }

  ~PvrConsumeThreadScope() {
    g_activePvrConsumeAttempt = previousAttempt_;
    g_activePvrConsumeResource = previousResource_;
  }

 private:
  map_page_prewarm::PvrConsumeAttempt* previousAttempt_{};
  void* previousResource_{};
};

map_page_prewarm::PvrConsumeOutcome consume_outcome(
    core::PvrConsumeValidationStatus status) noexcept {
  switch (status) {
    case core::PvrConsumeValidationStatus::UnexpectedReturnAddress:
      return map_page_prewarm::PvrConsumeOutcome::UnexpectedReturnAddress;
    case core::PvrConsumeValidationStatus::ResourceMismatch:
    case core::PvrConsumeValidationStatus::InactiveScope:
      return map_page_prewarm::PvrConsumeOutcome::ResourceMismatch;
    case core::PvrConsumeValidationStatus::SourceMismatch:
      return map_page_prewarm::PvrConsumeOutcome::SourceMismatch;
    case core::PvrConsumeValidationStatus::SizeMismatch:
      return map_page_prewarm::PvrConsumeOutcome::SizeMismatch;
    case core::PvrConsumeValidationStatus::CrcMismatch:
      return map_page_prewarm::PvrConsumeOutcome::CrcMismatch;
    case core::PvrConsumeValidationStatus::Ready:
      return map_page_prewarm::PvrConsumeOutcome::NotReached;
  }
  return map_page_prewarm::PvrConsumeOutcome::InternalError;
}

// Global zlib wrapper detour, but substitution is legal only for the one
// manifested CResPVR::Demand callsite and its exact active render-thread scope.
// Every rejected condition delegates to the original embedded zlib wrapper.
static int detour_pvr_uncompress(void* destination, std::uint32_t* destinationSize,
                                 const void* source, std::uint32_t sourceSize) {
  const auto original = g_pvrUncompressHook.original();
  auto* attempt = g_activePvrConsumeAttempt;
  const auto logDecision = [&](std::string_view action, std::string_view reason) {
    try {
      const auto resref = diagnostic_pvr_resref(g_activePvrConsumeResource);
      LOG_INFO(
          "Map page B2c zlib decision: page={}, resource=0x{:X}, action={}, reason={}, "
          "destination=0x{:X}, destinationSizePtr=0x{:X}, source=0x{:X}, sourceBytes={}, "
          "prepared=0x{:X}, preparedBytes={}",
          game::resref_view(resref),
          reinterpret_cast<std::uintptr_t>(g_activePvrConsumeResource), action, reason,
          reinterpret_cast<std::uintptr_t>(destination),
          reinterpret_cast<std::uintptr_t>(destinationSize),
          reinterpret_cast<std::uintptr_t>(source), sourceSize,
          attempt ? reinterpret_cast<std::uintptr_t>(attempt->page.decoded.data()) : 0,
          attempt ? attempt->page.decoded.size() : 0);
    } catch (...) {
    }
  };
  const auto fallback = [&](map_page_prewarm::PvrConsumeOutcome outcome) {
    if (attempt && attempt->outcome == map_page_prewarm::PvrConsumeOutcome::NotReached) {
      attempt->outcome = outcome;
    }
    logDecision("original-zlib", consume_outcome_diagnostic_name(outcome));
    return original(destination, destinationSize, source, sourceSize);
  };
  if (!attempt) {
    logDecision("original-zlib", "no-active-claim");
    return original(destination, destinationSize, source, sourceSize);
  }

  try {
    const auto actualReturn = reinterpret_cast<std::uintptr_t>(_ReturnAddress());
    if (actualReturn != g_pvrUncompressExpectedReturn) {
      return fallback(map_page_prewarm::PvrConsumeOutcome::UnexpectedReturnAddress);
    }
    if (!destination || !destinationSize || !source || !attempt->resource ||
        attempt->resource != g_activePvrConsumeResource ||
        attempt->page.status != core::PvrzPrepareStatus::Ready ||
        attempt->page.decoded.empty() ||
        attempt->page.decoded.size() > core::kShadowMaximumDecodedBytes ||
        attempt->page.compressedBytes > core::kShadowMaximumCompressedBytes) {
      return fallback(map_page_prewarm::PvrConsumeOutcome::ResourceMismatch);
    }

    game::CResPVR native{};
    std::uint32_t declaredDecodedSize{};
    std::uint32_t destinationCapacity{};
    if (!core::safe_read(attempt->resource, native) || !native.baseclass_0.pData ||
        native.baseclass_0.nSize < 4u ||
        native.baseclass_0.nSize > core::kShadowMaximumCompressedBytes ||
        !core::is_readable(native.baseclass_0.pData, native.baseclass_0.nSize) ||
        !core::safe_read(native.baseclass_0.pData, declaredDecodedSize) ||
        !core::safe_read(destinationSize, destinationCapacity) ||
        !core::is_writable_non_executable_memory(destinationSize,
                                                  sizeof(destinationCapacity)) ||
        !core::is_writable_non_executable_memory(destination,
                                                  attempt->page.decoded.size())) {
      return fallback(map_page_prewarm::PvrConsumeOutcome::MemoryRejected);
    }

    core::PvrConsumeEvidence evidence{
        .scopeActive = true,
        .expectedReturnAddress = g_pvrUncompressExpectedReturn,
        .actualReturnAddress = actualReturn,
        .expectedResource = reinterpret_cast<std::uintptr_t>(attempt->resource),
        .activeResource = reinterpret_cast<std::uintptr_t>(g_activePvrConsumeResource),
        .nativeData = reinterpret_cast<std::uintptr_t>(native.baseclass_0.pData),
        .source = reinterpret_cast<std::uintptr_t>(source),
        .nativeResourceBytes = native.baseclass_0.nSize,
        .sourceBytes = sourceSize,
        .preparedCompressedBytes = static_cast<std::size_t>(attempt->page.compressedBytes),
        .declaredDecodedBytes = declaredDecodedSize,
        .destinationCapacity = destinationCapacity,
        .preparedDecodedBytes = attempt->page.decoded.size(),
        .expectedCompressedCrc32 = attempt->page.compressedCrc32,
        .actualCompressedCrc32 = attempt->page.compressedCrc32,
    };
    auto validation = core::validate_pvr_consume(evidence);
    if (validation != core::PvrConsumeValidationStatus::Ready) {
      return fallback(consume_outcome(validation));
    }

    LARGE_INTEGER crcStarted{};
    LARGE_INTEGER crcEnded{};
    const bool crcMeasured = QueryPerformanceCounter(&crcStarted);
    evidence.actualCompressedCrc32 = static_cast<std::uint32_t>(crc32(
        crc32(0L, Z_NULL, 0), reinterpret_cast<const Bytef*>(source), sourceSize));
    if (crcMeasured && QueryPerformanceCounter(&crcEnded)) {
      attempt->crcNanoseconds = performance_nanoseconds(crcStarted, crcEnded);
    }
    validation = core::validate_pvr_consume(evidence);
    if (validation != core::PvrConsumeValidationStatus::Ready) {
      return fallback(consume_outcome(validation));
    }

    // Re-read the native owner after hashing the source. Any concurrent or
    // re-entrant mutation invalidates the attempt before bytes are published.
    game::CResPVR stable{};
    if (!core::safe_read(attempt->resource, stable) ||
        stable.baseclass_0.pData != native.baseclass_0.pData ||
        stable.baseclass_0.nSize != native.baseclass_0.nSize) {
      return fallback(map_page_prewarm::PvrConsumeOutcome::ResourceMismatch);
    }

    logDecision("prepared-copy", "validated");
    LARGE_INTEGER copyStarted{};
    LARGE_INTEGER copyEnded{};
    const bool copyMeasured = QueryPerformanceCounter(&copyStarted);
    std::memcpy(destination, attempt->page.decoded.data(), attempt->page.decoded.size());
    const auto produced = static_cast<std::uint32_t>(attempt->page.decoded.size());
    std::memcpy(destinationSize, &produced, sizeof(produced));
    if (copyMeasured && QueryPerformanceCounter(&copyEnded)) {
      attempt->copyNanoseconds = performance_nanoseconds(copyStarted, copyEnded);
    }
    attempt->outcome = map_page_prewarm::PvrConsumeOutcome::Consumed;
    return Z_OK;
  } catch (...) {
    return fallback(map_page_prewarm::PvrConsumeOutcome::InternalError);
  }
}

// Phase 3e-B2c observes the exact native CRes::Demand call nested inside the
// correlated CResPVR::Demand. Only statically proven data/size/loaded/texture
// fields and pointer/function boundaries are reported; no guessed count field
// or native return value is read or changed.
static void* detour_res_demand_diagnostic(void* thisPtr) {
  const auto original = g_resDemandDiagnosticHook.original();
  if (!thisPtr || thisPtr != g_activePvrConsumeResource) {
    return original(thisPtr);
  }

  game::CResPVR before{};
  const bool haveBefore = core::safe_read(thisPtr, before);
  const auto resref = diagnostic_pvr_resref(thisPtr);
  const auto* attempt = g_activePvrConsumeAttempt;
  const auto claimOrdinal = attempt ? attempt->claimOrdinal : 0u;
  const auto claimLimit = core::kMapPageConsumeMaximumClaimsPerGeneration;
  const auto lifecycle = map_page_prewarm::lifecycle_snapshot(thisPtr);
  const auto cacheBefore = capture_pvr_lifecycle_cache(thisPtr);
  const auto processBefore = core::capture_process_resource_snapshot();
  try {
    LOG_INFO(
        "Map page B2c CRes::Demand entry: page={}, resource=0x{:X}, activeClaim={}, "
        "claim={}/{}, rawData=0x{:X}, rawSize={}, loaded={}, texture={}, prepared=0x{:X}, "
        "preparedBytes={}, cacheReadable={}, cacheOccupied={}, cacheIndex={}, "
        "cacheDuplicates={}, cacheHead=0x{:X}, cacheTail=0x{:X}, cacheHash=0x{:X}, "
        "queuePending={}, queueInFlight={}, nativeFallbackWaits={}, queueCompleted={}, "
        "queueBytes={}, workingSetBytes={}, "
        "privateBytes={}, handles={}",
        game::resref_view(resref), reinterpret_cast<std::uintptr_t>(thisPtr),
        attempt != nullptr, claimOrdinal, claimLimit,
        haveBefore ? reinterpret_cast<std::uintptr_t>(before.baseclass_0.pData) : 0,
        haveBefore ? before.baseclass_0.nSize : 0u,
        haveBefore && before.baseclass_0.bLoaded,
        haveBefore ? before.texture : 0,
        attempt ? reinterpret_cast<std::uintptr_t>(attempt->page.decoded.data()) : 0,
        attempt ? attempt->page.decoded.size() : 0,
        cacheBefore.readable, cacheBefore.occupied, cacheBefore.resourceIndex,
        cacheBefore.resourceDuplicates, cacheBefore.head, cacheBefore.tail,
        cacheBefore.fingerprint, lifecycle ? lifecycle->pendingPages : 0,
        lifecycle ? lifecycle->inFlightPages : 0,
        lifecycle ? lifecycle->nativeFallbackWaits : 0,
        lifecycle ? lifecycle->completedPages : 0,
        lifecycle ? lifecycle->completedBytes : 0,
        processBefore.memoryAvailable ? processBefore.workingSetBytes : 0,
        processBefore.memoryAvailable ? processBefore.privateBytes : 0,
        processBefore.handlesAvailable ? processBefore.handleCount : 0);
  } catch (...) {
  }

  void* result = original(thisPtr);
  const DWORD lastError = GetLastError();
  game::CResPVR after{};
  const bool haveAfter = core::safe_read(thisPtr, after);
  const auto cacheAfter = capture_pvr_lifecycle_cache(thisPtr);
  const auto processAfter = core::capture_process_resource_snapshot();
  try {
    LOG_INFO(
        "Map page B2c CRes::Demand return: page={}, resource=0x{:X}, activeClaim={}, "
        "claim={}/{}, result={}, lastError={}, rawData=0x{:X}, rawSize={}, loaded={}, "
        "texture={}, cacheReadable={}, cacheOccupied={}, cacheIndex={}, cacheDuplicates={}, "
        "cacheHead=0x{:X}, cacheTail=0x{:X}, cacheHash=0x{:X}, workingSetBytes={}, "
        "privateBytes={}, handles={}, readOperationsDelta={}, readBytesDelta={}",
        game::resref_view(resref), reinterpret_cast<std::uintptr_t>(thisPtr),
        attempt != nullptr, claimOrdinal, claimLimit, result != nullptr, lastError,
        haveAfter ? reinterpret_cast<std::uintptr_t>(after.baseclass_0.pData) : 0,
        haveAfter ? after.baseclass_0.nSize : 0u,
        haveAfter && after.baseclass_0.bLoaded,
        haveAfter ? after.texture : 0,
        cacheAfter.readable, cacheAfter.occupied, cacheAfter.resourceIndex,
        cacheAfter.resourceDuplicates, cacheAfter.head, cacheAfter.tail,
        cacheAfter.fingerprint,
        processAfter.memoryAvailable ? processAfter.workingSetBytes : 0,
        processAfter.memoryAvailable ? processAfter.privateBytes : 0,
        processAfter.handlesAvailable ? processAfter.handleCount : 0,
        processBefore.ioAvailable && processAfter.ioAvailable
            ? core::monotonic_resource_delta(processBefore.readOperations,
                                             processAfter.readOperations)
            : 0,
        processBefore.ioAvailable && processAfter.ioAvailable
            ? core::monotonic_resource_delta(processBefore.readTransferBytes,
                                             processAfter.readTransferBytes)
            : 0);
  } catch (...) {
  }
  SetLastError(lastError);
  return result;
}

// The exact file-open helper at CRes::Demand+0xE2. Capturing GetLastError
// immediately after the native return distinguishes a path/open failure from
// later allocation or zlib work without changing the native result.
static int detour_res_file_open_diagnostic(void* fileObject, const void* pathObject,
                                           std::uint32_t mode, void* errorInfo) {
  const auto original = g_resFileOpenDiagnosticHook.original();
  if (!g_activePvrConsumeResource) {
    return original(fileObject, pathObject, mode, errorInfo);
  }

  const auto resref = diagnostic_pvr_resref(g_activePvrConsumeResource);
  const auto lifecycle =
      map_page_prewarm::lifecycle_snapshot(g_activePvrConsumeResource);
  if (!lifecycle) {
    return original(fileObject, pathObject, mode, errorInfo);
  }
  const auto cacheBefore = capture_pvr_lifecycle_cache(g_activePvrConsumeResource);
  const auto processBefore = core::capture_process_resource_snapshot();
  const int result = original(fileObject, pathObject, mode, errorInfo);
  const DWORD lastError = GetLastError();
  const auto cacheAfter = capture_pvr_lifecycle_cache(g_activePvrConsumeResource);
  const auto processAfter = core::capture_process_resource_snapshot();
  try {
    LOG_INFO(
        "Map page B2c CRes file open: page={}, resource=0x{:X}, fileObject=0x{:X}, "
        "pathObject=0x{:X}, mode=0x{:X}, errorInfo=0x{:X}, result={}, lastError={}, "
        "claim={}/{}, cacheBefore=0x{:X}, cacheAfter=0x{:X}, handlesBefore={}, "
        "handlesAfter={}, workingSetBefore={}, workingSetAfter={}, privateBefore={}, "
        "privateAfter={}, queueInFlight={}, nativeFallbackWaits={}, "
        "readOperationsDelta={}, readBytesDelta={}",
        game::resref_view(resref),
        reinterpret_cast<std::uintptr_t>(g_activePvrConsumeResource),
        reinterpret_cast<std::uintptr_t>(fileObject),
        reinterpret_cast<std::uintptr_t>(pathObject), mode,
        reinterpret_cast<std::uintptr_t>(errorInfo), result != 0, lastError,
        lifecycle->claims, lifecycle->claimLimit,
        cacheBefore.fingerprint, cacheAfter.fingerprint,
        processBefore.handlesAvailable ? processBefore.handleCount : 0,
        processAfter.handlesAvailable ? processAfter.handleCount : 0,
        processBefore.memoryAvailable ? processBefore.workingSetBytes : 0,
        processAfter.memoryAvailable ? processAfter.workingSetBytes : 0,
        processBefore.memoryAvailable ? processBefore.privateBytes : 0,
        processAfter.memoryAvailable ? processAfter.privateBytes : 0,
        lifecycle->inFlightPages, lifecycle->nativeFallbackWaits,
        processBefore.ioAvailable && processAfter.ioAvailable
            ? core::monotonic_resource_delta(processBefore.readOperations,
                                             processAfter.readOperations)
            : 0,
        processBefore.ioAvailable && processAfter.ioAvailable
            ? core::monotonic_resource_delta(processBefore.readTransferBytes,
                                             processAfter.readTransferBytes)
            : 0);
  } catch (...) {
  }
  SetLastError(lastError);
  return result;
}

// Observes the manifested CResPVR cache-release function for planned pages.
// The original call executes exactly once and owns every cache/texture change.
static void detour_pvr_cache_release_diagnostic(void* thisPtr) {
  const auto original = g_pvrCacheReleaseHook.original();
  const auto lifecycle = map_page_prewarm::lifecycle_snapshot(thisPtr);
  if (!lifecycle) {
    original(thisPtr);
    return;
  }

  const auto resref = diagnostic_pvr_resref(thisPtr);
  const auto cacheBefore = capture_pvr_lifecycle_cache(thisPtr);
  const auto processBefore = core::capture_process_resource_snapshot();
  try {
    LOG_INFO(
        "Map page B2c cache release entry: page={}, resource=0x{:X}, claim={}/{}, "
        "cacheOccupied={}, cacheIndex={}, cacheDuplicates={}, cacheHead=0x{:X}, "
        "cacheTail=0x{:X}, cacheHash=0x{:X}, handles={}",
        game::resref_view(resref), reinterpret_cast<std::uintptr_t>(thisPtr),
        lifecycle->claims, lifecycle->claimLimit, cacheBefore.occupied,
        cacheBefore.resourceIndex, cacheBefore.resourceDuplicates, cacheBefore.head,
        cacheBefore.tail, cacheBefore.fingerprint,
        processBefore.handlesAvailable ? processBefore.handleCount : 0);
  } catch (...) {
  }

  original(thisPtr);
  const DWORD lastError = GetLastError();
  const auto cacheAfter = capture_pvr_lifecycle_cache(thisPtr);
  const auto processAfter = core::capture_process_resource_snapshot();
  try {
    LOG_INFO(
        "Map page B2c cache release return: page={}, resource=0x{:X}, lastError={}, "
        "cacheOccupied={}, cacheIndex={}, cacheDuplicates={}, cacheHead=0x{:X}, "
        "cacheTail=0x{:X}, cacheHash=0x{:X}, handles={}",
        game::resref_view(resref), reinterpret_cast<std::uintptr_t>(thisPtr), lastError,
        cacheAfter.occupied, cacheAfter.resourceIndex, cacheAfter.resourceDuplicates,
        cacheAfter.head, cacheAfter.tail, cacheAfter.fingerprint,
        processAfter.handlesAvailable ? processAfter.handleCount : 0);
  } catch (...) {
  }
  SetLastError(lastError);
}

// Exact 2.7.3 CResPVR::Demand wrapper. It observes the engine's existing
// synchronous materialization and leaves the call, cache and texture policy
// unchanged. Nested GL hooks provide creation/upload time; the remaining time
// is intentionally reported as a combined resource/read/decode residual.
static void* detour_pvr_demand(void* thisPtr) {
  const auto original = g_pvrDemandHook.original();
  auto* ctx = g_ctx;
  if (!ctx || !ctx->cfg.enablePerformanceLogging || !thisPtr) {
    return original(thisPtr);
  }

  game::CResPVR before{};
  const bool haveBefore = core::safe_read(thisPtr, before);

  const bool ioCandidate = haveBefore &&
                           (before.texture <= 0 || !before.baseclass_0.bLoaded);
  auto consumeAttempt = ioCandidate ? map_page_prewarm::begin_native_demand(thisPtr)
                                     : std::nullopt;
  const auto lifecycle = ioCandidate ? map_page_prewarm::lifecycle_snapshot(thisPtr)
                                     : std::nullopt;
  const auto lifecycleResref = diagnostic_pvr_resref(thisPtr);
  const auto lifecycleCacheBefore = capture_pvr_lifecycle_cache(thisPtr);
  const auto lifecycleProcessBefore = core::capture_process_resource_snapshot();
  if (ctx->cfg.enableMapPageOffframeConsume && lifecycle) {
    try {
      LOG_INFO(
          "Map page B2c CResPVR::Demand entry: page={}, resource=0x{:X}, activeClaim={}, "
          "claim={}/{}, rawData=0x{:X}, rawSize={}, loaded={}, texture={}, prepared=0x{:X}, "
          "preparedBytes={}, cacheReadable={}, cacheOccupied={}, cacheIndex={}, "
          "cacheDuplicates={}, cacheHead=0x{:X}, cacheTail=0x{:X}, cacheHash=0x{:X}, "
          "queuePending={}, queueInFlight={}, nativeFallbackWaits={}, queueCompleted={}, "
          "queueBytes={}, workingSetBytes={}, "
          "privateBytes={}, handles={}",
          game::resref_view(lifecycleResref), reinterpret_cast<std::uintptr_t>(thisPtr),
          consumeAttempt.has_value(),
          consumeAttempt ? consumeAttempt->claimOrdinal : 0u,
          core::kMapPageConsumeMaximumClaimsPerGeneration,
          haveBefore ? reinterpret_cast<std::uintptr_t>(before.baseclass_0.pData) : 0,
          haveBefore ? before.baseclass_0.nSize : 0u,
          haveBefore && before.baseclass_0.bLoaded, haveBefore ? before.texture : 0,
          consumeAttempt
              ? reinterpret_cast<std::uintptr_t>(consumeAttempt->page.decoded.data())
              : 0,
          consumeAttempt ? consumeAttempt->page.decoded.size() : 0,
          lifecycleCacheBefore.readable, lifecycleCacheBefore.occupied,
          lifecycleCacheBefore.resourceIndex, lifecycleCacheBefore.resourceDuplicates,
          lifecycleCacheBefore.head, lifecycleCacheBefore.tail,
          lifecycleCacheBefore.fingerprint, lifecycle->pendingPages,
          lifecycle->inFlightPages, lifecycle->nativeFallbackWaits,
          lifecycle->completedPages, lifecycle->completedBytes,
          lifecycleProcessBefore.memoryAvailable
              ? lifecycleProcessBefore.workingSetBytes
              : 0,
          lifecycleProcessBefore.memoryAvailable ? lifecycleProcessBefore.privateBytes : 0,
          lifecycleProcessBefore.handlesAvailable ? lifecycleProcessBefore.handleCount : 0);
    } catch (...) {
    }
  }
  IO_COUNTERS ioBefore{};
  const bool haveIoBefore =
      ioCandidate && GetProcessIoCounters(GetCurrentProcess(), &ioBefore);

  LARGE_INTEGER started{};
  const bool measured = QueryPerformanceCounter(&started);
  PvrDemandScopeGuard scope;
  PvrConsumeThreadScope consumeScope(
      thisPtr, consumeAttempt ? &*consumeAttempt : nullptr);
  void* result = original(thisPtr);
  const DWORD lifecycleLastError = GetLastError();
  const auto nested = scope.finish();
  LARGE_INTEGER ended{};
  const auto durationNanoseconds = measured && QueryPerformanceCounter(&ended)
                                       ? performance_nanoseconds(started, ended)
                                       : 0;

  IO_COUNTERS ioAfter{};
  const bool ioMeasured =
      haveIoBefore && GetProcessIoCounters(GetCurrentProcess(), &ioAfter);
  game::CResPVR after{};
  const bool haveAfter = core::safe_read(thisPtr, after);
  if (ctx->cfg.enableMapPageOffframeConsume && lifecycle) {
    const auto lifecycleCacheAfter = capture_pvr_lifecycle_cache(thisPtr);
    const auto lifecycleProcessAfter = core::capture_process_resource_snapshot();
    try {
      LOG_INFO(
          "Map page B2c CResPVR::Demand return: page={}, resource=0x{:X}, activeClaim={}, "
          "claim={}/{}, result={}, lastError={}, rawData=0x{:X}, rawSize={}, loaded={}, "
          "texture={}, cacheReadable={}, cacheOccupied={}, cacheIndex={}, cacheDuplicates={}, "
          "cacheHead=0x{:X}, cacheTail=0x{:X}, cacheHash=0x{:X}, workingSetBytes={}, "
          "privateBytes={}, handles={}",
          game::resref_view(lifecycleResref), reinterpret_cast<std::uintptr_t>(thisPtr),
          consumeAttempt.has_value(),
          consumeAttempt ? consumeAttempt->claimOrdinal : 0u,
          core::kMapPageConsumeMaximumClaimsPerGeneration, result != nullptr,
          lifecycleLastError,
          haveAfter ? reinterpret_cast<std::uintptr_t>(after.baseclass_0.pData) : 0,
          haveAfter ? after.baseclass_0.nSize : 0u,
          haveAfter && after.baseclass_0.bLoaded, haveAfter ? after.texture : 0,
          lifecycleCacheAfter.readable, lifecycleCacheAfter.occupied,
          lifecycleCacheAfter.resourceIndex, lifecycleCacheAfter.resourceDuplicates,
          lifecycleCacheAfter.head, lifecycleCacheAfter.tail,
          lifecycleCacheAfter.fingerprint,
          lifecycleProcessAfter.memoryAvailable
              ? lifecycleProcessAfter.workingSetBytes
              : 0,
          lifecycleProcessAfter.memoryAvailable ? lifecycleProcessAfter.privateBytes : 0,
          lifecycleProcessAfter.handlesAvailable ? lifecycleProcessAfter.handleCount : 0);
    } catch (...) {
    }
  }
  const bool textureCreated =
      haveBefore && haveAfter && after.texture > 0 &&
      after.texture != before.texture;
  const bool materialized = textureCreated ||
                            nested.textureGenerationCalls != 0 ||
                            nested.compressedUploadCalls != 0;
  game::ResrefBuffer resref{};
  if (materialized &&
      (!haveAfter ||
       !game::read_runtime_resref(after.baseclass_0.resref, resref))) {
    resref[0] = '?';
  }
  const auto readOperations =
      ioMeasured && ioAfter.ReadOperationCount >= ioBefore.ReadOperationCount
          ? ioAfter.ReadOperationCount - ioBefore.ReadOperationCount
          : 0;
  const auto readBytes =
      ioMeasured && ioAfter.ReadTransferCount >= ioBefore.ReadTransferCount
          ? ioAfter.ReadTransferCount - ioBefore.ReadTransferCount
          : 0;
  const auto name = materialized ? game::resref_view(resref) : std::string_view{};
  core::record_pvr_demand(
      frame::frame_count(), name, materialized, ioMeasured, textureCreated,
      haveAfter ? after.size.cx : 0, haveAfter ? after.size.cy : 0,
      durationNanoseconds, readOperations, readBytes, nested);
  if (consumeAttempt) {
    map_page_prewarm::record_consume_attempt(*consumeAttempt, durationNanoseconds);
  }
  SetLastError(lifecycleLastError);
  return result;
}

// RenderTexture hook - thin dispatch into the tile upscale feature
static void detour_render_texture(void* thisPtr, int texId, void* unused, int x, int y,
                                  unsigned long flags) {
  const auto original = g_renderTextureHook.original();
  if (!g_ctx || !g_ctx->manifest) {
    original(thisPtr, texId, unused, x, y, flags);
    return;
  }

  auto& ctx = *g_ctx;
  bool handled = false;
  LARGE_INTEGER performanceStart{};
  const bool measurePerformance =
      ctx.cfg.enablePerformanceLogging && QueryPerformanceCounter(&performanceStart);
  try {
    install_shader_probes_once();
    handled = features::render_tile(ctx, thisPtr, texId, unused, x, y, flags);
  } catch (const std::exception& e) {
    LOG_ERROR("RenderTexture enhancement failed; using the engine renderer: {}", e.what());
  } catch (...) {
    LOG_ERROR("RenderTexture enhancement failed; using the engine renderer");
  }
  if (measurePerformance) {
    LARGE_INTEGER performanceEnd{};
    if (QueryPerformanceCounter(&performanceEnd)) {
      record_render_performance(ctx, handled,
                                performanceEnd.QuadPart - performanceStart.QuadPart);
    }
  }
  if (!handled) {
    original(thisPtr, texId, unused, x, y, flags);
  }
}

// Render runs between DrawBeginScaled and DrawEndScaled. Compose after the
// native area so the bridge is resolved as part of the map; all screen HUD and
// full-screen menus are consequently drawn above it.
static void detour_game_area_render(void* thisPtr, void* vidMode) {
  g_gameAreaRenderHook.original()(thisPtr, vidMode);
  // The GL renderer batches the native area's commands until DrawEndScaled.
  // Flush them while its map FBO is still current; otherwise those deferred
  // commands execute after our raw GL draw and completely cover the bridge.
  if (g_drawFlushGl) g_drawFlushGl();
  bridge::render_world_overlay();
}

bool install_all(AppContext& ctx) {
  g_ctx = &ctx;

  try {
    if (!g_hookInit) g_hookInit = new core::HookInit();
    g_loadAreaHook.create(reinterpret_cast<void*>(ctx.addrs.LoadArea),
                          reinterpret_cast<void*>(&detour_load_area));
    LOG_INFO("LoadArea hook created");

    g_renderTextureHook.create(reinterpret_cast<void*>(ctx.addrs.RenderTexture),
                               reinterpret_cast<void*>(&detour_render_texture));
    LOG_INFO("RenderTexture hook created");

    map_page_prewarm::configure(nullptr);
    (void)map_page_prewarm::configure_shadow(false, false, {});
    if ((ctx.cfg.enablePerformanceLogging || ctx.cfg.enableMapPagePrewarm ||
          ctx.cfg.enableMapPageOffframeProbe ||
          ctx.cfg.enableMapPageOffframeConsume) &&
        ctx.manifest) {
      try {
        const auto module = core::get_module_span(nullptr);
        const auto& runtime = ctx.manifest->pvrDemand;
        if (!module || !module->base) {
          throw std::runtime_error("module unavailable");
        }
        if (!runtime.enabled()) {
          throw std::runtime_error("manifest has no CResPVR::Demand evidence");
        }
        if (!matches_pattern_at_rva(*module, runtime.demand, runtime.signature)) {
          throw std::runtime_error("CResPVR::Demand signature mismatch");
        }
        const auto moduleBase = reinterpret_cast<std::uintptr_t>(module->base);
        const auto demandEntry = reinterpret_cast<CResPvrDemandFn>(moduleBase + runtime.demand);
        map_page_prewarm::configure(demandEntry);
        CResPvrDemandFn resourceDemandEntry = nullptr;
        CResPvrReleaseFn cacheReleaseEntry = nullptr;
        CResFileOpenFn resourceFileOpenEntry = nullptr;
        if (ctx.cfg.enableMapPageOffframeConsume && ctx.cfg.enablePerformanceLogging) {
          const auto& boundary = runtime.decodeBoundary;
          const auto& lifecycle = runtime.lifecycleBoundary;
          if (!boundary.enabled()) {
            throw std::runtime_error("manifest has no decoded-PVR consume boundary");
          }
          if (!lifecycle.enabled()) {
            throw std::runtime_error("manifest has no PVR lifecycle diagnostic boundary");
          }
          if (!matches_pattern_at_rva(*module, boundary.uncompress,
                                      boundary.uncompressSignature)) {
            throw std::runtime_error("PVR uncompress wrapper signature mismatch");
          }
          if (!matches_pattern_at_rva(*module,
                                      runtime.demand + boundary.consumeWindowOffset,
                                      boundary.consumeWindowSignature)) {
            throw std::runtime_error("PVR post-decode consume window mismatch");
          }
          const auto callAddress = moduleBase + runtime.demand +
                                   boundary.uncompressCallOffset;
          const auto decodedTarget = core::rel32_target_checked(
              reinterpret_cast<const void*>(callAddress), 0xE8, 1, 5);
          if (decodedTarget != reinterpret_cast<void*>(moduleBase + boundary.uncompress) ||
              boundary.consumeWindowOffset != boundary.uncompressCallOffset + 5u) {
            throw std::runtime_error("PVR uncompress call edge mismatch");
          }
          const auto resourceCallAddress = moduleBase + runtime.demand +
                                           boundary.resourceDemandCallOffset;
          const auto decodedResourceTarget = core::rel32_target_checked(
              reinterpret_cast<const void*>(resourceCallAddress), 0xE8, 1, 5);
          if (decodedResourceTarget !=
              reinterpret_cast<void*>(moduleBase + boundary.resourceDemand)) {
            throw std::runtime_error("CRes::Demand diagnostic call edge mismatch");
          }
          if (!matches_pattern_at_rva(*module, lifecycle.cacheRelease,
                                      lifecycle.cacheReleaseSignature)) {
            throw std::runtime_error("PVR cache-release signature mismatch");
          }
          if (!matches_pattern_at_rva(*module, lifecycle.resourceFileOpen,
                                      lifecycle.resourceFileOpenSignature)) {
            throw std::runtime_error("CRes file-open signature mismatch");
          }
          constexpr std::size_t kCacheEntryBytes =
              kPvrLifecycleCacheEntries * sizeof(void*);
          if (lifecycle.cacheEntryCount != kPvrLifecycleCacheEntries ||
              !core::is_read_write_non_executable_section(
                  *module, lifecycle.cacheEntries, kCacheEntryBytes) ||
              !core::is_writable_non_executable_memory(
                  reinterpret_cast<const void*>(moduleBase + lifecycle.cacheEntries),
                  kCacheEntryBytes)) {
            throw std::runtime_error("PVR cache table memory evidence mismatch");
          }
          const auto demandCacheReference = reinterpret_cast<const std::uint8_t*>(
              moduleBase + runtime.demand + lifecycle.cacheReferenceOffset);
          std::int32_t demandCacheDisplacement{};
          if (demandCacheReference[0] != 0x4C || demandCacheReference[1] != 0x8D ||
              demandCacheReference[2] != 0x35 ||
              !core::safe_read(demandCacheReference + 3, demandCacheDisplacement) ||
              reinterpret_cast<std::uintptr_t>(demandCacheReference + 7) +
                      demandCacheDisplacement !=
                  moduleBase + lifecycle.cacheEntries) {
            throw std::runtime_error("CResPVR::Demand cache reference mismatch");
          }
          const auto releaseCacheReference = reinterpret_cast<const std::uint8_t*>(
              moduleBase + lifecycle.cacheRelease +
              lifecycle.cacheReleaseReferenceOffset);
          std::int32_t releaseCacheDisplacement{};
          if (releaseCacheReference[0] != 0x48 || releaseCacheReference[1] != 0x8D ||
              releaseCacheReference[2] != 0x15 ||
              !core::safe_read(releaseCacheReference + 3, releaseCacheDisplacement) ||
              reinterpret_cast<std::uintptr_t>(releaseCacheReference + 7) +
                      releaseCacheDisplacement !=
                  moduleBase + lifecycle.cacheEntries) {
            throw std::runtime_error("PVR cache-release table reference mismatch");
          }
          const auto fileOpenCallAddress =
              moduleBase + boundary.resourceDemand +
              lifecycle.resourceFileOpenCallOffset;
          const auto decodedFileOpenTarget = core::rel32_target_checked(
              reinterpret_cast<const void*>(fileOpenCallAddress), 0xE8, 1, 5);
          if (decodedFileOpenTarget !=
              reinterpret_cast<void*>(moduleBase + lifecycle.resourceFileOpen)) {
            throw std::runtime_error("CRes file-open diagnostic call edge mismatch");
          }
          resourceDemandEntry = reinterpret_cast<CResPvrDemandFn>(decodedResourceTarget);
          cacheReleaseEntry = reinterpret_cast<CResPvrReleaseFn>(
              moduleBase + lifecycle.cacheRelease);
          resourceFileOpenEntry = reinterpret_cast<CResFileOpenFn>(
              decodedFileOpenTarget);
          g_pvrCacheEntries =
              reinterpret_cast<const void*>(moduleBase + lifecycle.cacheEntries);
          g_pvrUncompressExpectedReturn =
              moduleBase + runtime.demand + boundary.consumeWindowOffset;
        }
        if ((ctx.cfg.enableMapPageOffframeProbe ||
             ctx.cfg.enableMapPageOffframeConsume) &&
            ctx.cfg.enablePerformanceLogging) {
          const auto resourceDirectory =
              core::ConfigManager::config_path().parent_path() / "override";
          const bool shadowConfigured = map_page_prewarm::configure_shadow(
              true, ctx.cfg.enableMapPageOffframeConsume, resourceDirectory);
          if (ctx.cfg.enableMapPageOffframeConsume && !shadowConfigured) {
            throw std::runtime_error("off-frame consume worker unavailable");
          }
        }
        if (ctx.cfg.enableMapPageOffframeConsume && ctx.cfg.enablePerformanceLogging) {
          const auto& boundary = runtime.decodeBoundary;
          g_pvrUncompressHook.create(
              reinterpret_cast<void*>(moduleBase + boundary.uncompress),
              reinterpret_cast<void*>(&detour_pvr_uncompress));
          g_pvrUncompressHook.enable();
          LOG_INFO(
              "Map page off-frame diagnostic consume installed at zlib RVA 0x{:X}; "
              "expected return RVA 0x{:X}, up to {} claims per area generation, strict native "
              "fallback",
              boundary.uncompress, runtime.demand + boundary.consumeWindowOffset,
              core::kMapPageConsumeMaximumClaimsPerGeneration);
          g_resDemandDiagnosticHook.create(
              reinterpret_cast<void*>(resourceDemandEntry),
              reinterpret_cast<void*>(&detour_res_demand_diagnostic));
          g_resDemandDiagnosticHook.enable();
          LOG_INFO(
              "Map page off-frame CRes::Demand diagnostic installed at RVA 0x{:X}; native "
              "return value and resource fields remain authoritative",
              boundary.resourceDemand);
          g_resFileOpenDiagnosticHook.create(
              reinterpret_cast<void*>(resourceFileOpenEntry),
              reinterpret_cast<void*>(&detour_res_file_open_diagnostic));
          g_resFileOpenDiagnosticHook.enable();
          LOG_INFO(
              "Map page B2c file-open diagnostic installed at RVA 0x{:X}; return value "
              "and GetLastError remain authoritative",
              runtime.lifecycleBoundary.resourceFileOpen);
          g_pvrCacheReleaseHook.create(
              reinterpret_cast<void*>(cacheReleaseEntry),
              reinterpret_cast<void*>(&detour_pvr_cache_release_diagnostic));
          g_pvrCacheReleaseHook.enable();
          LOG_INFO(
              "Map page B2c cache-release diagnostic installed at RVA 0x{:X}; {} cache "
              "entries are observed read-only",
              runtime.lifecycleBoundary.cacheRelease,
              runtime.lifecycleBoundary.cacheEntryCount);
        }
        if (ctx.cfg.enablePerformanceLogging) {
          g_pvrDemandHook.create(
              reinterpret_cast<void*>(demandEntry),
              reinterpret_cast<void*>(&detour_pvr_demand));
          g_pvrDemandHook.enable();
          LOG_INFO(
              "PVR demand telemetry hook installed at CResPVR::Demand RVA 0x{:X}; "
              "native calls remain authoritative",
              runtime.demand);
        }
        if (ctx.cfg.enableMapPagePrewarm) {
          if (ctx.cfg.enablePerformanceLogging) {
            LOG_INFO(
                "Map page prewarm prepared at manifested CResPVR::Demand RVA 0x{:X}; "
                "opt-in post-swap scheduler with native synchronous fallback",
                runtime.demand);
          } else {
            LOG_WARN(
                "Map page prewarm is enabled but inactive because PerformanceLogs=false; "
                "the first prototype requires deletion telemetry for its eviction guard");
          }
        }
        if (ctx.cfg.enableMapPageOffframeProbe && !ctx.cfg.enablePerformanceLogging) {
          LOG_WARN(
              "Map page shadow probe is enabled but inactive because PerformanceLogs=false; "
              "the probe requires demand correlation telemetry");
        }
        if (ctx.cfg.enableMapPageOffframeConsume && !ctx.cfg.enablePerformanceLogging) {
          LOG_WARN(
              "Map page off-frame bounded consume is enabled but inactive because "
              "PerformanceLogs=false; strict demand correlation is required");
        }
      } catch (const std::exception& error) {
        (void)g_pvrUncompressHook.remove();
        g_pvrUncompressExpectedReturn = 0;
        (void)g_resFileOpenDiagnosticHook.remove();
        (void)g_resDemandDiagnosticHook.remove();
        (void)g_pvrCacheReleaseHook.remove();
        (void)g_pvrDemandHook.remove();
        g_pvrCacheEntries = nullptr;
        (void)map_page_prewarm::configure_shadow(false, false, {});
        map_page_prewarm::configure(nullptr);
        LOG_WARN("PVR demand phase telemetry unavailable: {}", error.what());
      } catch (...) {
        (void)g_pvrUncompressHook.remove();
        g_pvrUncompressExpectedReturn = 0;
        (void)g_resFileOpenDiagnosticHook.remove();
        (void)g_resDemandDiagnosticHook.remove();
        (void)g_pvrCacheReleaseHook.remove();
        (void)g_pvrDemandHook.remove();
        g_pvrCacheEntries = nullptr;
        (void)map_page_prewarm::configure_shadow(false, false, {});
        map_page_prewarm::configure(nullptr);
        LOG_WARN("PVR demand phase telemetry unavailable: unknown installation error");
      }
    }

    g_areaCompositionMode = AreaCompositionMode::None;
    g_nativeOcclusionProbeHookEnabled = false;
    g_nativeOcclusionProbeLoggingEnabled = false;
    g_nativeOcclusionBridgeEnabled = false;
    g_nativeOcclusionTextureApi = {};
    g_nativeFxSurfacePools = nullptr;
    if (prepare_area_animation_composition_hooks(ctx)) {
      g_areaCompositionMode = AreaCompositionMode::Registry;
    } else if (prepare_am0205e_composition_hooks(ctx)) {
      g_areaCompositionMode = AreaCompositionMode::AM0205EPrototype;
    }
    g_creatureSpriteHooksEnabled = prepare_creature_sprite_composition_hooks(ctx);
    const bool hasBridgeTarget =
        g_areaCompositionMode == AreaCompositionMode::Registry ||
        g_creatureSpriteHooksEnabled;
    if (ctx.cfg.enableNativeOcclusionBridge && hasBridgeTarget) {
      g_nativeOcclusionBridgeEnabled = validate_native_occlusion_bridge_runtime(ctx);
      if (g_nativeOcclusionBridgeEnabled) {
        LOG_INFO(
            "Native occlusion phase1 A/B bridge prepared: native FX alpha "
            "capture plus transient GPU visibility composition; disabled packs and "
            "non-xN draws remain native");
      }
    } else if (ctx.cfg.enableNativeOcclusionBridge) {
      LOG_WARN(
          "Native occlusion phase1 bridge not prepared: no registry-backed area "
          "animation or creature xN path is active");
    }
    if (g_areaCompositionMode != AreaCompositionMode::None || g_creatureSpriteHooksEnabled) {
      try {
        const auto module = core::get_module_span(nullptr);
        if (!module || !ctx.manifest) throw std::runtime_error("module or manifest unavailable");
        const auto moduleBase = reinterpret_cast<std::uintptr_t>(module->base);
        const auto& runtime = ctx.manifest->areaAnimations;
        g_vidCellRenderTextureHook.create(
            reinterpret_cast<void*>(moduleBase + runtime.vidCellRenderTexture),
            reinterpret_cast<void*>(&detour_vid_cell_render_texture));
        g_vidCellRenderTextureHook.enable();
        if (g_areaCompositionMode != AreaCompositionMode::None) {
          g_gameStaticRenderBamHook.create(
              reinterpret_cast<void*>(moduleBase + runtime.gameStaticRenderBam),
              reinterpret_cast<void*>(&detour_game_static_render_bam));
          g_gameStaticRenderBamHook.enable();
          LOG_INFO("{} high-level composition scope installed",
                   g_areaCompositionMode == AreaCompositionMode::Registry
                       ? "Area-animation x4 registry"
                       : "AM0205E x4");
        }
        if (g_creatureSpriteHooksEnabled) {
          g_vidPaletteRealizeHook.create(
              reinterpret_cast<void*>(moduleBase + runtime.vidPaletteRealize),
              reinterpret_cast<void*>(&detour_vid_palette_realize));
          g_vidPaletteRealizeHook.enable();
          if (g_creatureSpriteCharacterHookEnabled) {
            g_characterRenderHook.create(
                reinterpret_cast<void*>(moduleBase + runtime.characterRender),
                reinterpret_cast<void*>(&detour_character_render));
            g_characterRenderHook.enable();
            LOG_INFO(
                "Creature sprite xN owner scope installed: Character::Render RVA "
                "0x{:X}, body cell offset 0x{:X}, overlay cell offsets "
                "[0x{:X},0x{:X},0x{:X}], CVidPalette::Realize RVA 0x{:X}",
                runtime.characterRender, runtime.characterCurrentCell,
                runtime.characterOverlayCells[0], runtime.characterOverlayCells[1],
                runtime.characterOverlayCells[2],
                runtime.vidPaletteRealize);
          }
          if (g_creatureSpriteMonsterHookEnabled) {
            g_monsterRenderHook.create(
                reinterpret_cast<void*>(moduleBase + runtime.monsterRender),
                reinterpret_cast<void*>(&detour_monster_render));
            g_monsterRenderHook.enable();
            LOG_INFO(
                "Creature sprite xN owner scope installed: Monster::Render RVA "
                "0x{:X}, body cell offset 0x{:X}, CVidPalette::Realize RVA 0x{:X}",
                runtime.monsterRender, runtime.monsterCurrentCell,
                runtime.vidPaletteRealize);
          }
          if (g_creatureSpriteMonsterIcewindHookEnabled) {
            g_monsterIcewindRenderHook.create(
                reinterpret_cast<void*>(moduleBase + runtime.monsterIcewindRender),
                reinterpret_cast<void*>(&detour_monster_icewind_render));
            g_monsterIcewindRenderHook.enable();
            LOG_INFO(
                "Creature sprite xN owner scope installed: MonsterIcewind::Render RVA "
                "0x{:X}, CVidPalette::Realize RVA 0x{:X}",
                runtime.monsterIcewindRender, runtime.vidPaletteRealize);
          }
        }
        LOG_INFO("CVidCell high-level composition dispatcher installed");
      } catch (const std::exception& error) {
        (void)g_characterRenderHook.remove();
        (void)g_monsterRenderHook.remove();
        (void)g_monsterIcewindRenderHook.remove();
        (void)g_gameStaticRenderBamHook.remove();
        (void)g_vidPaletteRealizeHook.remove();
        (void)g_vidCellRenderTextureHook.remove();
        g_areaAnimationTextureApi = {};
        g_am0205eTextureApi = {};
        g_creatureSpriteTextureApi = {};
        g_creatureSpriteHooksEnabled = false;
        g_creatureSpriteCharacterHookEnabled = false;
        g_creatureSpriteMonsterHookEnabled = false;
        g_creatureSpriteMonsterIcewindHookEnabled = false;
        g_creatureSpritePaletteReturn = 0;
        g_areaCompositionMode = AreaCompositionMode::None;
        g_nativeOcclusionBridgeEnabled = false;
        g_nativeOcclusionTextureApi = {};
        g_nativeFxSurfacePools = nullptr;
        LOG_WARN("High-level composition hooks could not be installed: {}",
                 error.what());
      } catch (...) {
        (void)g_characterRenderHook.remove();
        (void)g_monsterRenderHook.remove();
        (void)g_monsterIcewindRenderHook.remove();
        (void)g_gameStaticRenderBamHook.remove();
        (void)g_vidPaletteRealizeHook.remove();
        (void)g_vidCellRenderTextureHook.remove();
        g_areaAnimationTextureApi = {};
        g_am0205eTextureApi = {};
        g_creatureSpriteTextureApi = {};
        g_creatureSpriteHooksEnabled = false;
        g_creatureSpriteCharacterHookEnabled = false;
        g_creatureSpriteMonsterHookEnabled = false;
        g_creatureSpriteMonsterIcewindHookEnabled = false;
        g_creatureSpritePaletteReturn = 0;
        g_areaCompositionMode = AreaCompositionMode::None;
        g_nativeOcclusionBridgeEnabled = false;
        g_nativeOcclusionTextureApi = {};
        g_nativeFxSurfacePools = nullptr;
        LOG_WARN("High-level composition hooks could not be installed");
      }
    }

    if (ctx.cfg.enableNativeOcclusionProbe || g_nativeOcclusionBridgeEnabled) {
      if (g_areaCompositionMode == AreaCompositionMode::None &&
          !g_creatureSpriteHooksEnabled) {
        LOG_WARN(
            "Native occlusion phase0 probe not installed: no xN area-animation or "
            "creature composition path is active");
      } else {
        try {
          const auto module = core::get_module_span(nullptr);
          if (!module || !module->base || !ctx.manifest) {
            throw std::runtime_error("module or manifest unavailable");
          }
          const auto& runtime = ctx.manifest->areaAnimations;
          if (!runtime.infinityFxRenderClippingPolys ||
              runtime.infinityFxRenderClippingPolysSignature.empty()) {
            throw std::runtime_error("manifest has no FXRenderClippingPolys evidence");
          }
          if (!matches_pattern_at_rva(
                  *module, runtime.infinityFxRenderClippingPolys,
                  runtime.infinityFxRenderClippingPolysSignature)) {
            throw std::runtime_error("FXRenderClippingPolys signature mismatch");
          }
          const auto moduleBase = reinterpret_cast<std::uintptr_t>(module->base);
          g_infinityFxRenderClippingPolysHook.create(
              reinterpret_cast<void*>(moduleBase + runtime.infinityFxRenderClippingPolys),
              reinterpret_cast<void*>(&detour_infinity_fx_render_clipping_polys));
          g_infinityFxRenderClippingPolysHook.enable();
          g_nativeOcclusionProbeHookEnabled = true;
          g_nativeOcclusionProbeLoggingEnabled = ctx.cfg.enableNativeOcclusionProbe;
          if (g_nativeOcclusionBridgeEnabled) {
            LOG_INFO(
                "Native occlusion phase1 hook installed at "
                "CInfinity::FXRenderClippingPolys RVA 0x{:X}; exact pre/post FX "
                "visibility capture enabled",
                runtime.infinityFxRenderClippingPolys);
          } else {
            LOG_INFO(
                "Native occlusion phase0 probe installed at "
                "CInfinity::FXRenderClippingPolys RVA 0x{:X}; metadata only, no "
                "pixel or render-state changes",
                runtime.infinityFxRenderClippingPolys);
          }
        } catch (const std::exception& error) {
          (void)g_infinityFxRenderClippingPolysHook.remove();
          g_nativeOcclusionProbeHookEnabled = false;
          g_nativeOcclusionProbeLoggingEnabled = false;
          g_nativeOcclusionBridgeEnabled = false;
          g_nativeOcclusionTextureApi = {};
          g_nativeFxSurfacePools = nullptr;
          LOG_ERROR("Native occlusion hook disabled: {}", error.what());
        } catch (...) {
          (void)g_infinityFxRenderClippingPolysHook.remove();
          g_nativeOcclusionProbeHookEnabled = false;
          g_nativeOcclusionProbeLoggingEnabled = false;
          g_nativeOcclusionBridgeEnabled = false;
          g_nativeOcclusionTextureApi = {};
          g_nativeFxSurfacePools = nullptr;
          LOG_ERROR("Native occlusion hook disabled: unknown installation error");
        }
      }
    }

    if (ctx.manifest && ctx.manifest->worldOverlay.enabled) {
      try {
        const auto module = core::get_module_span(nullptr);
        if (!module || !module->base) throw std::runtime_error("module unavailable");
        const auto& runtime = ctx.manifest->worldOverlay;
        const bool exactMatch = matches_pattern_at_rva(
            *module, runtime.gameAreaRender, runtime.gameAreaRenderSignature);
        if (!exactMatch &&
            !core::confirm_pattern_with_patched_prologue(
                nullptr, runtime.gameAreaRender, runtime.gameAreaRenderSignature)) {
          throw std::runtime_error("CGameArea::Render signature mismatch");
        }
        if (!exactMatch) {
          LOG_WARN(
              "CGameArea::Render prologue is already detoured; validated the remaining "
              "manifest signature before chaining the world-overlay hook");
        }
        if (!matches_pattern_at_rva(*module, runtime.drawFlushGl,
                                    runtime.drawFlushGlSignature)) {
          throw std::runtime_error("DrawFlush_GL signature mismatch");
        }
        const auto moduleBase = reinterpret_cast<std::uintptr_t>(module->base);
        g_drawFlushGl = reinterpret_cast<DrawFlushGlFn>(moduleBase + runtime.drawFlushGl);
        g_gameAreaRenderHook.create(
            reinterpret_cast<void*>(moduleBase + runtime.gameAreaRender),
            reinterpret_cast<void*>(&detour_game_area_render));
        g_gameAreaRenderHook.enable();
        LOG_INFO(
            "AR1300 bridge map-overlay hook installed at CGameArea::Render RVA "
            "0x{:X}; scaled map framebuffer below, all screen UI above",
            runtime.gameAreaRender);
      } catch (const std::exception& error) {
        (void)g_gameAreaRenderHook.remove();
        g_drawFlushGl = nullptr;
        LOG_ERROR("AR1300 bridge transition disabled: world-overlay hook failed ({})",
                  error.what());
      } catch (...) {
        (void)g_gameAreaRenderHook.remove();
        g_drawFlushGl = nullptr;
        LOG_ERROR("AR1300 bridge transition disabled: world-overlay hook failed");
      }
    }

    if (ctx.draw.DrawColorTone) {
      try {
        g_drawColorToneHook.create(reinterpret_cast<void*>(ctx.draw.DrawColorTone),
                                   reinterpret_cast<void*>(&detour_draw_color_tone));
        g_drawColorToneHook.enable();
        LOG_INFO("DrawColorTone hook installed");
      } catch (const std::exception& e) {
        ctx.cfg.enableWaterEffect = false;
        ctx.cfg.enableDebugHotkeys = false;
        LOG_ERROR(
            "Water effect disabled: DrawColorTone hook installation failed ({}); a coherent "
            "world-view transform cannot be published safely. Tile upscaling remains enabled.",
            e.what());
      } catch (...) {
        ctx.cfg.enableWaterEffect = false;
        ctx.cfg.enableDebugHotkeys = false;
        LOG_ERROR(
            "Water effect disabled: DrawColorTone hook installation failed with an unknown "
            "error; a coherent world-view transform cannot be published safely. Tile "
            "upscaling remains enabled.");
      }
    } else {
      ctx.cfg.enableWaterEffect = false;
      ctx.cfg.enableDebugHotkeys = false;
      LOG_ERROR(
          "Water effect disabled: DrawColorTone was not resolved; a coherent world-view "
          "transform cannot be published safely. Tile upscaling remains enabled.");
    }

    g_loadAreaHook.enable();
    LOG_INFO("LoadArea hook enabled");

    g_renderTextureHook.enable();
    LOG_INFO("RenderTexture hook enabled");

    LOG_INFO("All hooks installed successfully");
    LOG_INFO("LoadArea: 0x{:X}", ctx.addrs.LoadArea);
    LOG_INFO("RenderTexture: 0x{:X}", ctx.addrs.RenderTexture);
    LOG_INFO("RenderTexture hook enabled - will detect upscaled textures automatically");

    return true;
  } catch (const std::exception& e) {
    LOG_ERROR("Exception during hook installation: {}", e.what());
    (void)g_gameAreaRenderHook.remove();
    g_drawFlushGl = nullptr;
    (void)g_drawColorToneHook.remove();
    (void)g_characterRenderHook.remove();
    (void)g_monsterRenderHook.remove();
    (void)g_monsterIcewindRenderHook.remove();
    (void)g_gameStaticRenderBamHook.remove();
    (void)g_infinityFxRenderClippingPolysHook.remove();
    (void)g_vidPaletteRealizeHook.remove();
    (void)g_vidCellRenderTextureHook.remove();
    (void)g_pvrUncompressHook.remove();
    g_pvrUncompressExpectedReturn = 0;
    (void)g_resFileOpenDiagnosticHook.remove();
    (void)g_resDemandDiagnosticHook.remove();
    (void)g_pvrCacheReleaseHook.remove();
    (void)g_pvrDemandHook.remove();
    g_pvrCacheEntries = nullptr;
    map_page_prewarm::shutdown();
    (void)g_renderTextureHook.remove();
    (void)g_loadAreaHook.remove();
    g_areaCompositionMode = AreaCompositionMode::None;
    g_nativeOcclusionProbeHookEnabled = false;
    g_nativeOcclusionProbeLoggingEnabled = false;
    g_nativeOcclusionBridgeEnabled = false;
    g_nativeOcclusionTextureApi = {};
    g_nativeFxSurfacePools = nullptr;
    g_areaAnimationTextureApi = {};
    g_am0205eTextureApi = {};
    g_creatureSpriteTextureApi = {};
    g_creatureSpriteHooksEnabled = false;
    g_creatureSpriteCharacterHookEnabled = false;
    g_creatureSpriteMonsterHookEnabled = false;
    g_creatureSpriteMonsterIcewindHookEnabled = false;
    g_creatureSpritePaletteReturn = 0;
    g_ctx = nullptr;
    delete g_hookInit;
    g_hookInit = nullptr;
    return false;
  } catch (...) {
    LOG_ERROR("Unknown exception during hook installation");
    (void)g_gameAreaRenderHook.remove();
    g_drawFlushGl = nullptr;
    (void)g_drawColorToneHook.remove();
    (void)g_characterRenderHook.remove();
    (void)g_monsterRenderHook.remove();
    (void)g_monsterIcewindRenderHook.remove();
    (void)g_gameStaticRenderBamHook.remove();
    (void)g_infinityFxRenderClippingPolysHook.remove();
    (void)g_vidPaletteRealizeHook.remove();
    (void)g_vidCellRenderTextureHook.remove();
    (void)g_pvrUncompressHook.remove();
    g_pvrUncompressExpectedReturn = 0;
    (void)g_resFileOpenDiagnosticHook.remove();
    (void)g_resDemandDiagnosticHook.remove();
    (void)g_pvrCacheReleaseHook.remove();
    (void)g_pvrDemandHook.remove();
    g_pvrCacheEntries = nullptr;
    map_page_prewarm::shutdown();
    (void)g_renderTextureHook.remove();
    (void)g_loadAreaHook.remove();
    g_areaCompositionMode = AreaCompositionMode::None;
    g_nativeOcclusionProbeHookEnabled = false;
    g_nativeOcclusionProbeLoggingEnabled = false;
    g_nativeOcclusionBridgeEnabled = false;
    g_nativeOcclusionTextureApi = {};
    g_nativeFxSurfacePools = nullptr;
    g_areaAnimationTextureApi = {};
    g_am0205eTextureApi = {};
    g_creatureSpriteTextureApi = {};
    g_creatureSpriteHooksEnabled = false;
    g_creatureSpriteCharacterHookEnabled = false;
    g_creatureSpriteMonsterHookEnabled = false;
    g_creatureSpriteMonsterIcewindHookEnabled = false;
    g_creatureSpritePaletteReturn = 0;
    g_ctx = nullptr;
    delete g_hookInit;
    g_hookInit = nullptr;
    return false;
  }
}

void uninstall_all() noexcept {
  try {
    LOG_INFO("Uninstalling all hooks...");
  } catch (...) {
  }

  (void)g_gameAreaRenderHook.remove();
  g_drawFlushGl = nullptr;
  (void)g_drawColorToneHook.remove();
  (void)g_characterRenderHook.remove();
  (void)g_monsterRenderHook.remove();
  (void)g_monsterIcewindRenderHook.remove();
  (void)g_gameStaticRenderBamHook.remove();
  (void)g_infinityFxRenderClippingPolysHook.remove();
  (void)g_vidPaletteRealizeHook.remove();
  (void)g_vidCellRenderTextureHook.remove();
  (void)g_pvrUncompressHook.remove();
  g_pvrUncompressExpectedReturn = 0;
  (void)g_resFileOpenDiagnosticHook.remove();
  (void)g_resDemandDiagnosticHook.remove();
  (void)g_pvrCacheReleaseHook.remove();
  (void)g_pvrDemandHook.remove();
  g_pvrCacheEntries = nullptr;
  map_page_prewarm::shutdown();
  (void)g_renderTextureHook.remove();
  (void)g_loadAreaHook.remove();

  native_occlusion_bridge::shutdown();
  area_animation_x4::forget_engine_textures();
  creature_sprite_x2::forget_engine_textures();
  am0205e_x4::forget_engine_textures();
  g_areaAnimationTextureApi = {};
  g_am0205eTextureApi = {};
  g_creatureSpriteTextureApi = {};
  g_creatureSpriteHooksEnabled = false;
  g_creatureSpriteCharacterHookEnabled = false;
  g_creatureSpriteMonsterHookEnabled = false;
  g_creatureSpriteMonsterIcewindHookEnabled = false;
  g_creatureSpritePaletteReturn = 0;
  g_areaCompositionMode = AreaCompositionMode::None;
  g_nativeOcclusionProbeHookEnabled = false;
  g_nativeOcclusionProbeLoggingEnabled = false;
  g_nativeOcclusionBridgeEnabled = false;
  g_nativeOcclusionTextureApi = {};
  g_nativeFxSurfacePools = nullptr;

  g_ctx = nullptr;
  delete g_hookInit;
  g_hookInit = nullptr;

  try {
    LOG_INFO("Hook cleanup complete");
  } catch (...) {
  }
}

void prepare_for_shutdown() noexcept {
  // Quiesce engine entry points before dependent frame/GL hooks and shared
  // state are torn down. MinHook itself stays initialized until
  // uninstall_all(), after every MinHook-backed subsystem has removed its
  // hooks.
  (void)g_gameAreaRenderHook.disable();
  (void)g_drawColorToneHook.disable();
  (void)g_characterRenderHook.disable();
  (void)g_monsterRenderHook.disable();
  (void)g_monsterIcewindRenderHook.disable();
  (void)g_gameStaticRenderBamHook.disable();
  (void)g_infinityFxRenderClippingPolysHook.disable();
  (void)g_vidPaletteRealizeHook.disable();
  (void)g_vidCellRenderTextureHook.disable();
  (void)g_pvrUncompressHook.disable();
  g_pvrUncompressExpectedReturn = 0;
  (void)g_resFileOpenDiagnosticHook.disable();
  (void)g_resDemandDiagnosticHook.disable();
  (void)g_pvrCacheReleaseHook.disable();
  (void)g_pvrDemandHook.disable();
  g_pvrCacheEntries = nullptr;
  map_page_prewarm::shutdown();
  (void)g_renderTextureHook.disable();
  (void)g_loadAreaHook.disable();
  g_ctx = nullptr;
}

bool is_active() {
  // The RenderTexture hook is intentionally disabled on standard-resolution
  // areas while the DLL, area hooks, and shader features remain active.
  return g_ctx != nullptr;
}

void retry_shader_probe_install() noexcept {
  try {
    if (g_ctx) install_shader_probes_once();
  } catch (...) {
    // A frame boundary must never depend on optional shader-probe setup.
  }
}

void on_post_swap() noexcept {
  try {
    if (g_ctx) map_page_prewarm::on_post_swap(*g_ctx);
  } catch (...) {
    // Optional scheduling must never escape through the presentation ABI.
  }
}
}  // namespace iee::hooks
