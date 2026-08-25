#include "hooks.h"

#include <intrin.h>
#include <windows.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <exception>
#include <stdexcept>
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
#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/core/performance_samples.h"
#include "iee/features/tile_render.h"
#include "iee/frame_hook.h"
#include "iee/game/game_types.h"
#include "iee/game/renderer.h"
#include "iee/game/runtime_types_x64.h"
#include "iee/shader_probe.h"

namespace iee::hooks {
using LoadAreaFn = void* (*)(void*, void*, unsigned char, unsigned char, unsigned char);
using RenderTextureFn = void (*)(void*, int, void*, int, int, unsigned long);
using DrawColorToneFn = void (*)(int);
using GameStaticRenderBamFn = void (*)(void*, void*, void*);
using VidCellRenderTextureFn = void (*)(int, int, void*, std::uint64_t, void*, std::uint32_t);
using VidPaletteRealizeFn = void (*)(void*, std::uint32_t*, std::uint32_t, void*, std::uint32_t,
                                    std::uint32_t);
using MonsterIcewindRenderFn = void (*)(void*, std::uintptr_t, std::uintptr_t,
                                        std::uintptr_t, std::uintptr_t, std::uintptr_t,
                                        std::uintptr_t, std::uintptr_t, std::uintptr_t,
                                        std::uintptr_t, std::uintptr_t, std::uintptr_t,
                                        std::uintptr_t, std::uintptr_t);
using CharacterRenderFn = MonsterIcewindRenderFn;
using GameAreaRenderFn = void (*)(void*, void*);
using DrawFlushGlFn = void (*)();

// Hook management - initialize MinHook
// Intentionally explicit lifetime: a static smart-pointer destructor would
// call MinHook from the Windows loader lock if the loader skipped ShutdownBindings.
static core::HookInit* g_hookInit = nullptr;
static core::Hook<LoadAreaFn> g_loadAreaHook;
static core::Hook<RenderTextureFn> g_renderTextureHook;
static core::Hook<DrawColorToneFn> g_drawColorToneHook;
static core::Hook<GameStaticRenderBamFn> g_gameStaticRenderBamHook;
static core::Hook<VidCellRenderTextureFn> g_vidCellRenderTextureHook;
static core::Hook<VidPaletteRealizeFn> g_vidPaletteRealizeHook;
static core::Hook<MonsterIcewindRenderFn> g_monsterIcewindRenderHook;
static core::Hook<CharacterRenderFn> g_characterRenderHook;
static core::Hook<GameAreaRenderFn> g_gameAreaRenderHook;
static DrawFlushGlFn g_drawFlushGl{};

static AppContext* g_ctx = nullptr;
static am0205e_x4::EngineTextureApi g_am0205eTextureApi{};
static area_animation_x4::EngineTextureApi g_areaAnimationTextureApi{};
static creature_sprite_x2::EngineTextureApi g_creatureSpriteTextureApi{};
thread_local int g_am0205eRenderDepth = 0;
thread_local int g_am0205eFrameIndex = -1;
thread_local int g_areaAnimationRenderDepth = 0;
thread_local area_animation_x4::FrameHandle g_areaAnimationFrame{};

constexpr std::size_t kMaximumCreatureSpriteLayers = 4;
constexpr std::size_t kNoCreatureSpriteLayer = kMaximumCreatureSpriteLayers;

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
std::uintptr_t g_creatureSpritePaletteReturn{};

enum class CreatureSpriteOwner : std::uint8_t { None, MonsterIcewind, Character };
CreatureSpriteOwner g_creatureSpriteOwner = CreatureSpriteOwner::None;

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
  int sequence{-1};
  int slot{-1};
};

bool is_target_creature_animation(void* animation, std::uint16_t& animationId) noexcept {
  animationId = 0;
  if (!animation || !g_ctx || !g_ctx->manifest || !creature_sprite_x2::ready()) return false;
  const auto& runtime = g_ctx->manifest->areaAnimations;
  if (!runtime.enabled) return false;
  const auto base = reinterpret_cast<std::uintptr_t>(animation);
  return core::safe_read(reinterpret_cast<const void*>(base + runtime.monsterAnimationId),
                         animationId) &&
         animationId == creature_sprite_x2::target_animation_id();
}

bool read_registered_creature_cell(void* cell, const char* ownerLabel,
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
  if (!creature_sprite_x2::contains_resource(resref)) return false;
  if (!creature_sprite_x2::resolve_frame(resref, currentSequence, currentFrame,
                                         resolved.handle)) {
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
  if (!is_target_creature_animation(animation, animationId)) return false;
  const auto currentCellOffset = owner == CreatureSpriteOwner::Character
                                     ? runtime.characterCurrentCell
                                     : runtime.monsterCurrentCell;
  const auto ownerLabel = owner == CreatureSpriteOwner::Character
                              ? "CGameAnimationTypeCharacter"
                              : "CGameAnimationTypeMonsterIcewind";
  if (!core::safe_read(reinterpret_cast<const void*>(base + currentCellOffset), cell) ||
      !cell) {
    static std::atomic<bool> unreadableCellLogged{false};
    if (!unreadableCellLogged.exchange(true, std::memory_order_relaxed)) {
      LOG_WARN("Target {} body CVidCell is unavailable; native rendering retained", ownerLabel);
    }
    return false;
  }
  if (!read_registered_creature_cell(cell, ownerLabel, resolved)) return false;
  static std::atomic<bool> animationReachedLogged{false};
  if (!animationReachedLogged.exchange(true, std::memory_order_relaxed)) {
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
  if (!area_animation_x4::resolve_frame(resref, currentSequence, currentFrame,
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
        "Creature sprite xBR2x hook skipped: CVidPalette::Realize signature differs at "
        "RVA 0x{:X}",
        runtime.vidPaletteRealize);
    return false;
  }
  if (!matches_pattern_at_rva(module, runtime.vidPaletteRealizeCallsite,
                              runtime.signatures[8])) {
    LOG_WARN(
        "Creature sprite xBR2x hook skipped: owner palette callsite signature differs at "
        "RVA 0x{:X}",
        runtime.vidPaletteRealizeCallsite);
    return false;
  }
  for (std::size_t index = 0; index < runtime.glTextureTableReferences.size(); ++index) {
    if (!matches_pattern_at_rva(module, runtime.glTextureTableReferences[index],
                                runtime.signatures[10 + index])) {
      LOG_WARN(
          "Creature sprite xBR2x hook skipped: engine texture-table reference {} "
          "differs at RVA 0x{:X}",
          index, runtime.glTextureTableReferences[index]);
      return false;
    }
  }
  if (!matches_pattern_at_rva(module, runtime.glTextureSecondarySelectorReference,
                              runtime.signatures[13])) {
    LOG_WARN(
        "Creature sprite xBR2x hook skipped: engine secondary-texture selector "
        "differs at RVA 0x{:X}",
        runtime.glTextureSecondarySelectorReference);
    return false;
  }
  std::uint8_t secondaryFieldOffset = 0;
  if (!core::safe_read(module.base + runtime.glTextureSecondarySelectorReference + 5,
                       secondaryFieldOffset) ||
      secondaryFieldOffset != 0x24) {
    LOG_WARN(
        "Creature sprite xBR2x hook skipped: engine secondary-texture selector no "
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
        "Creature sprite xBR2x hook skipped: realized palette RVA 0x{:X} is not a "
        "writable non-executable data span",
        runtime.realizedPalette);
    return false;
  }
  if (!core::is_read_write_non_executable_section(module, runtime.nativeTextureFormat,
                                                   kEncodingBytes) ||
      !core::is_writable_non_executable_memory(encodingAddress, kEncodingBytes)) {
    LOG_WARN(
        "Creature sprite xBR2x hook skipped: native pixel encoding globals are not a "
        "writable non-executable data span");
    return false;
  }
  if (!core::is_read_write_non_executable_section(module, runtime.glTextureTable,
                                                   kTextureTableBytes) ||
      !core::is_writable_non_executable_memory(textureTableAddress,
                                               kTextureTableBytes)) {
    LOG_WARN(
        "Creature sprite xBR2x hook skipped: engine texture descriptor table is not a "
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
          "Creature sprite xBR2x hook skipped: engine texture-table reference {} no "
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
        "Creature sprite xBR2x hook skipped: palette owner callsite no longer targets the "
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
  g_creatureSpriteOwner = CreatureSpriteOwner::None;
  g_creatureSpritePaletteReturn = 0;
  if (!ctx.cfg.enableCreatureSpriteX2Test || !creature_sprite_x2::ready()) return false;
  if (!validate_area_animation_runtime(ctx, "Creature sprite xBR2x")) return false;
  const auto module = core::get_module_span(nullptr);
  if (!module || !ctx.manifest) return false;
  const auto& runtime = ctx.manifest->areaAnimations;
  if (!validate_creature_sprite_palette_runtime(ctx, *module)) return false;
  const auto animationFamily = creature_sprite_x2::target_animation_id() & 0xF000u;
  std::uintptr_t ownerRender = 0;
  std::size_t ownerSignature = 0;
  const char* ownerLabel = nullptr;
  if (animationFamily == 0xE000u) {
    g_creatureSpriteOwner = CreatureSpriteOwner::MonsterIcewind;
    ownerRender = runtime.monsterIcewindRender;
    ownerSignature = 6;
    ownerLabel = "CGameAnimationTypeMonsterIcewind::Render";
  } else if (animationFamily == 0x5000u || animationFamily == 0x6000u) {
    g_creatureSpriteOwner = CreatureSpriteOwner::Character;
    ownerRender = runtime.characterRender;
    ownerSignature = 9;
    ownerLabel = "CGameAnimationTypeCharacter::Render";
  } else {
    LOG_WARN(
        "Creature sprite xBR2x hook skipped: animation 0x{:04X} has no validated owner "
        "scope",
        creature_sprite_x2::target_animation_id());
    return false;
  }
  if (!matches_pattern_at_rva(*module, ownerRender, runtime.signatures[ownerSignature])) {
    LOG_WARN("Creature sprite xBR2x hook skipped: {} signature differs at RVA 0x{:X}",
             ownerLabel, ownerRender);
    g_creatureSpriteOwner = CreatureSpriteOwner::None;
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

void record_render_performance(bool enabled, bool handled, long long elapsedTicks) noexcept {
  if (!enabled || elapsedTicks < 0) return;

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
      core::PerformanceSamples<2048> frameCpuMs;

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
        frameCpuMs.reset();
      }
    };
    static Window window;

    LARGE_INTEGER now{};
    if (!QueryPerformanceCounter(&now)) return;
    if (window.startedAt == 0) window.startedAt = now.QuadPart;
    window.totalTicks += elapsedTicks;
    window.maximumTicks = (std::max)(window.maximumTicks, elapsedTicks);
    ++window.calls;
    if (handled) ++window.handledCalls;

    const auto frameNumber = frame::frame_count();
    const double ticksToMilliseconds = 1000.0 / static_cast<double>(frequency);
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
    window.reset(now.QuadPart);
  } catch (...) {
    // Performance diagnostics must not affect rendering.
  }
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
    const bool ar1300 = is_ar1300(resolved);
    probe::set_area_view(view.scrollX, view.scrollY, view.viewWorldW, view.viewWorldH);
    bridge::publish_view(view, ar1300);
  }
}
}  // namespace

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
    (void)append_creature_sprite_layer(scope, resolved);
  }
  // Every MonsterIcewind invocation masks an outer creature scope. A nested
  // non-target render must never inherit the outer sprite's palette/frame.
  CreatureSpriteScopeOverride scopeOverride(target ? &scope : nullptr);

  g_monsterIcewindRenderHook.original()(thisPtr, a2, a3, a4, a5, a6, a7, a8, a9, a10,
                                        a11, a12, a13, a14);

  if (target) {
    static std::atomic<bool> noReplacementLogged{false};
    if (scope.replacements == 0 &&
        !noReplacementLogged.exchange(true, std::memory_order_relaxed)) {
      LOG_WARN(
          "Registered creature render reached no compatible owner-scoped palette/texture "
          "(target Realize={}, foreign Realize={}); native BAM rendering remains active",
          scope.targetRealizes, scope.foreignRealizes);
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
        if (read_registered_creature_cell(overlayCell, kOverlayLabels[index], overlay)) {
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

  g_characterRenderHook.original()(thisPtr, a2, a3, a4, a5, a6, a7, a8, a9, a10,
                                   a11, a12, a13, a14);

  if (target) {
    static std::atomic<bool> noReplacementLogged{false};
    if (scope.replacements == 0 &&
        !noReplacementLogged.exchange(true, std::memory_order_relaxed)) {
      LOG_WARN(
          "Registered character render reached no compatible owner-scoped "
          "composite (target Realize={}, captured layers={}, foreign Realize={}, "
          "unregistered layers={}, incomplete={}); native BAM rendering remains active",
          scope.targetRealizes, scope.compositionCount, scope.foreignRealizes,
          scope.unregisteredLayerRealizes, scope.compositionIncomplete);
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
      if (!ownerCandidate && g_creatureSpriteOwner == CreatureSpriteOwner::Character) {
        scope->compositionIncomplete = true;
      }
    } else {
      ++scope->foreignRealizes;
      if (g_creatureSpriteOwner == CreatureSpriteOwner::Character &&
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
    if (g_creatureSpriteOwner == CreatureSpriteOwner::Character) {
      scope->compositionIncomplete = true;
    }
    return;
  }
  auto& layer = scope->layers[ownerLayer];
  if (g_creatureSpriteOwner == CreatureSpriteOwner::Character) {
    ResolvedCreatureSpriteFrame current{};
    if (!read_registered_creature_cell(layer.cell, "CGameAnimationTypeCharacter layer",
                                       current) ||
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
  int previousTextureId = 0;
  int transientCreatureTextureId = 0;
  ReplacementKind replacement = ReplacementKind::None;
  auto* creatureScope = g_creatureSpriteScope;
  if (g_creatureSpriteHooksEnabled && creatureScope) {
    // A creature scope owns this dispatch even when it fails closed. Never fall
    // through to an unrelated area-animation substitution during creature rendering.
    const int logicalWidth = static_cast<std::int32_t>(logicalSize & 0xFFFFFFFFull);
    const int logicalHeight = static_cast<std::int32_t>(logicalSize >> 32u);
    if (g_creatureSpriteOwner == CreatureSpriteOwner::Character) {
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
    if (area_animation_x4::bind_frame_texture(g_areaAnimationFrame, g_areaAnimationTextureApi,
                                              previousTextureId)) {
      replacement = ReplacementKind::AreaRegistry;
    }
  } else if (g_areaCompositionMode == AreaCompositionMode::AM0205EPrototype &&
             g_am0205eRenderDepth > 0 && g_am0205eFrameIndex >= 0) {
    if (am0205e_x4::bind_frame_texture(g_am0205eFrameIndex, g_am0205eTextureApi,
                                      previousTextureId)) {
      replacement = ReplacementKind::AM0205E;
    }
  }
  original(x, y, sourceRect, logicalSize, clipRect, flags);
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
  (void)area_animation_x4::prepare_for_area(game::resref_view(areaResref));
}

// LoadArea hook - reset area-specific state for new area detection
static void* detour_load_area(void* thisPtr, void* pAreaNameString, unsigned char a2,
                              unsigned char a3, unsigned char a4) {
  const auto original = g_loadAreaHook.original();
  if (!g_ctx) {
    return original(thisPtr, pAreaNameString, a2, a3, a4);
  }

  auto& ctx = *g_ctx;
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
  } catch (const std::exception& e) {
    LOG_ERROR("LoadArea pre-dispatch failed; continuing with the engine path: {}", e.what());
  } catch (...) {
    LOG_ERROR("LoadArea pre-dispatch failed; continuing with the engine path");
  }

  auto* result = original(thisPtr, pAreaNameString, a2, a3, a4);
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
        area_animation_x4::flush_retired_textures(g_areaAnimationTextureApi);
      }
    }
  } catch (...) {
    // Rendering must never depend on IEE diagnostics or uniform state.
  }
  g_drawColorToneHook.original()(mode);
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
      record_render_performance(true, handled, performanceEnd.QuadPart - performanceStart.QuadPart);
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

    g_areaCompositionMode = AreaCompositionMode::None;
    if (prepare_area_animation_composition_hooks(ctx)) {
      g_areaCompositionMode = AreaCompositionMode::Registry;
    } else if (prepare_am0205e_composition_hooks(ctx)) {
      g_areaCompositionMode = AreaCompositionMode::AM0205EPrototype;
    }
    g_creatureSpriteHooksEnabled = prepare_creature_sprite_composition_hooks(ctx);
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
          if (g_creatureSpriteOwner == CreatureSpriteOwner::Character) {
            g_characterRenderHook.create(
                reinterpret_cast<void*>(moduleBase + runtime.characterRender),
                reinterpret_cast<void*>(&detour_character_render));
            g_characterRenderHook.enable();
            LOG_INFO(
                "Creature sprite xBR2x owner scope installed: Character::Render RVA "
                "0x{:X}, body cell offset 0x{:X}, overlay cell offsets "
                "[0x{:X},0x{:X},0x{:X}], CVidPalette::Realize RVA 0x{:X}",
                runtime.characterRender, runtime.characterCurrentCell,
                runtime.characterOverlayCells[0], runtime.characterOverlayCells[1],
                runtime.characterOverlayCells[2],
                runtime.vidPaletteRealize);
          } else {
            g_monsterIcewindRenderHook.create(
                reinterpret_cast<void*>(moduleBase + runtime.monsterIcewindRender),
                reinterpret_cast<void*>(&detour_monster_icewind_render));
            g_monsterIcewindRenderHook.enable();
            LOG_INFO(
                "Creature sprite xBR2x owner scope installed: MonsterIcewind::Render RVA "
                "0x{:X}, CVidPalette::Realize RVA 0x{:X}",
                runtime.monsterIcewindRender, runtime.vidPaletteRealize);
          }
        }
        LOG_INFO("CVidCell high-level composition dispatcher installed");
      } catch (const std::exception& error) {
        (void)g_characterRenderHook.remove();
        (void)g_monsterIcewindRenderHook.remove();
        (void)g_gameStaticRenderBamHook.remove();
        (void)g_vidPaletteRealizeHook.remove();
        (void)g_vidCellRenderTextureHook.remove();
        g_areaAnimationTextureApi = {};
        g_am0205eTextureApi = {};
        g_creatureSpriteTextureApi = {};
        g_creatureSpriteHooksEnabled = false;
        g_creatureSpriteOwner = CreatureSpriteOwner::None;
        g_creatureSpritePaletteReturn = 0;
        g_areaCompositionMode = AreaCompositionMode::None;
        LOG_WARN("High-level composition hooks could not be installed: {}",
                 error.what());
      } catch (...) {
        (void)g_characterRenderHook.remove();
        (void)g_monsterIcewindRenderHook.remove();
        (void)g_gameStaticRenderBamHook.remove();
        (void)g_vidPaletteRealizeHook.remove();
        (void)g_vidCellRenderTextureHook.remove();
        g_areaAnimationTextureApi = {};
        g_am0205eTextureApi = {};
        g_creatureSpriteTextureApi = {};
        g_creatureSpriteHooksEnabled = false;
        g_creatureSpriteOwner = CreatureSpriteOwner::None;
        g_creatureSpritePaletteReturn = 0;
        g_areaCompositionMode = AreaCompositionMode::None;
        LOG_WARN("High-level composition hooks could not be installed");
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
    (void)g_monsterIcewindRenderHook.remove();
    (void)g_gameStaticRenderBamHook.remove();
    (void)g_vidPaletteRealizeHook.remove();
    (void)g_vidCellRenderTextureHook.remove();
    (void)g_renderTextureHook.remove();
    (void)g_loadAreaHook.remove();
    g_areaCompositionMode = AreaCompositionMode::None;
    g_areaAnimationTextureApi = {};
    g_am0205eTextureApi = {};
    g_creatureSpriteTextureApi = {};
    g_creatureSpriteHooksEnabled = false;
    g_creatureSpriteOwner = CreatureSpriteOwner::None;
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
    (void)g_monsterIcewindRenderHook.remove();
    (void)g_gameStaticRenderBamHook.remove();
    (void)g_vidPaletteRealizeHook.remove();
    (void)g_vidCellRenderTextureHook.remove();
    (void)g_renderTextureHook.remove();
    (void)g_loadAreaHook.remove();
    g_areaCompositionMode = AreaCompositionMode::None;
    g_areaAnimationTextureApi = {};
    g_am0205eTextureApi = {};
    g_creatureSpriteTextureApi = {};
    g_creatureSpriteHooksEnabled = false;
    g_creatureSpriteOwner = CreatureSpriteOwner::None;
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
  (void)g_monsterIcewindRenderHook.remove();
  (void)g_gameStaticRenderBamHook.remove();
  (void)g_vidPaletteRealizeHook.remove();
  (void)g_vidCellRenderTextureHook.remove();
  (void)g_renderTextureHook.remove();
  (void)g_loadAreaHook.remove();

  area_animation_x4::forget_engine_textures();
  creature_sprite_x2::forget_engine_textures();
  am0205e_x4::forget_engine_textures();
  g_areaAnimationTextureApi = {};
  g_am0205eTextureApi = {};
  g_creatureSpriteTextureApi = {};
  g_creatureSpriteHooksEnabled = false;
  g_creatureSpriteOwner = CreatureSpriteOwner::None;
  g_creatureSpritePaletteReturn = 0;
  g_areaCompositionMode = AreaCompositionMode::None;

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
  (void)g_monsterIcewindRenderHook.disable();
  (void)g_gameStaticRenderBamHook.disable();
  (void)g_vidPaletteRealizeHook.disable();
  (void)g_vidCellRenderTextureHook.disable();
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
}  // namespace iee::hooks
