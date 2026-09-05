#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <limits>
#include <optional>
#include <string>
#include <string_view>

namespace iee::game {
enum class BranchInstructionKind : std::uint8_t {
  CallRel32,
  JmpRel32,
};

struct BranchInstructionDesc {
  const char* name{};
  std::size_t offset{};
  BranchInstructionKind kind{BranchInstructionKind::CallRel32};
  std::uint8_t opcode{};
  std::size_t displacementOffset{};
  std::size_t instructionSize{};
  bool required{true};

  [[nodiscard]] constexpr bool validate() const noexcept {
    return name != nullptr && name[0] != '\0' && instructionSize > displacementOffset;
  }
};

struct PatternSet {
  std::string_view loadArea{};
  std::string_view renderTexture{};
};

struct ReferenceRvas {
  std::uintptr_t loadArea{};
  std::uintptr_t renderTexture{};
};

// Optional, static evidence for the render-thread-only decoded-PVR handoff.
// Nothing calls or patches this boundary until a consuming prototype validates
// both the unique uncompress wrapper and the native post-decode field/upload
// window on the positively identified build.
struct PvrDecodeBoundary {
  std::size_t resourceDemandCallOffset{};
  std::uintptr_t resourceDemand{};
  std::size_t uncompressCallOffset{};
  std::uintptr_t uncompress{};
  std::string_view uncompressSignature{};
  std::size_t consumeWindowOffset{};
  std::string_view consumeWindowSignature{};

  [[nodiscard]] constexpr bool enabled() const noexcept {
    return resourceDemandCallOffset != 0 && resourceDemand != 0 &&
           uncompressCallOffset != 0 && uncompress != 0 &&
           !uncompressSignature.empty() && consumeWindowOffset != 0 &&
           !consumeWindowSignature.empty();
  }

  [[nodiscard]] constexpr bool validate() const noexcept {
    const bool empty = resourceDemandCallOffset == 0 && resourceDemand == 0 &&
                       uncompressCallOffset == 0 && uncompress == 0 &&
                       uncompressSignature.empty() && consumeWindowOffset == 0 &&
                       consumeWindowSignature.empty();
    return empty || enabled();
  }
};

// Optional Phase 3e-B2c evidence for observing the native PVR cache and the
// file-open boundary nested in CRes::Demand. These RVAs are diagnostic only:
// runtime code may read stable pointer identities and hook function entries,
// but must never edit cache slots or native resource fields.
struct PvrLifecycleBoundary {
  std::size_t cacheReferenceOffset{};
  std::uintptr_t cacheEntries{};
  std::size_t cacheEntryCount{};
  std::uintptr_t cacheRelease{};
  std::string_view cacheReleaseSignature{};
  std::size_t cacheReleaseReferenceOffset{};
  std::size_t resourceFileOpenCallOffset{};
  std::uintptr_t resourceFileOpen{};
  std::string_view resourceFileOpenSignature{};

  [[nodiscard]] constexpr bool enabled() const noexcept {
    return cacheReferenceOffset != 0 && cacheEntries != 0 && cacheEntryCount != 0 &&
           cacheRelease != 0 && !cacheReleaseSignature.empty() &&
           cacheReleaseReferenceOffset != 0 && resourceFileOpenCallOffset != 0 &&
           resourceFileOpen != 0 && !resourceFileOpenSignature.empty();
  }

  [[nodiscard]] constexpr bool validate() const noexcept {
    const bool empty = cacheReferenceOffset == 0 && cacheEntries == 0 &&
                       cacheEntryCount == 0 && cacheRelease == 0 &&
                       cacheReleaseSignature.empty() && cacheReleaseReferenceOffset == 0 &&
                       resourceFileOpenCallOffset == 0 && resourceFileOpen == 0 &&
                       resourceFileOpenSignature.empty();
    return empty || (enabled() && cacheEntryCount == 128);
  }
};

// Optional CResPVR::Demand target. Diagnostics use the entry signature alone;
// Phase 3e-B consumers additionally require the exact decoded-PVR boundary.
struct PvrDemandRuntime {
  std::uintptr_t demand{};
  std::string_view signature{};
  PvrDecodeBoundary decodeBoundary{};
  PvrLifecycleBoundary lifecycleBoundary{};

  [[nodiscard]] constexpr bool enabled() const noexcept {
    return demand != 0 && !signature.empty();
  }

  [[nodiscard]] constexpr bool validate() const noexcept {
    return (demand == 0) == signature.empty() && decodeBoundary.validate() &&
           lifecycleBoundary.validate() &&
           (!decodeBoundary.enabled() || enabled()) &&
           (!lifecycleBoundary.enabled() || (enabled() && decodeBoundary.enabled()));
  }
};

struct RuntimeOffsets {
  std::uintptr_t vidTileResource{};
  std::uintptr_t tisLinearTilesFlag{};
  std::uintptr_t tisHeaderTileDimension{};
  std::uintptr_t infGameVisibleArea{};
  std::uintptr_t infGameAreas{};
  std::uintptr_t infGameAreaMaster{};
};

// CGameStatic stores its drawing Y, while registry-v3 occurrences use the raw ARE coordinate.
// Widen the subtraction so a malformed object cannot trigger signed overflow in the render hook.
[[nodiscard]] constexpr std::optional<std::int32_t> area_animation_are_y(
    std::int32_t drawingY, std::int32_t height) noexcept {
  const auto rawY = static_cast<std::int64_t>(drawingY) - static_cast<std::int64_t>(height);
  if (rawY < (std::numeric_limits<std::int32_t>::min)() ||
      rawY > (std::numeric_limits<std::int32_t>::max)()) {
    return std::nullopt;
  }
  return static_cast<std::int32_t>(rawY);
}

// Optional high-level CGameStatic/CVidCell composition bridge used by external
// area-animation runtime packs. Every RVA, object offset and signature is tied
// to one positively identified executable manifest.
struct AreaAnimationRuntime {
  bool enabled{};
  std::uintptr_t gameStaticRenderBam{};
  std::uintptr_t vidCellRenderTexture{};
  std::uintptr_t drawDeleteTexture{};
  std::uintptr_t drawGenTexture{};
  std::uintptr_t drawGetRenderer{};
  std::uintptr_t texImage{};
  std::uintptr_t glTextureState{};
  std::uintptr_t glTextureTable{};
  std::array<std::uintptr_t, 3> glTextureTableReferences{};
  std::uintptr_t glTextureSecondarySelectorReference{};
  std::uintptr_t realizedPalette{};
  std::uintptr_t vidPaletteRealize{};
  std::uintptr_t vidPaletteRealizeCallsite{};
  std::uintptr_t nativeTextureFormat{};
  std::uintptr_t nativeTextureType{};
  std::uintptr_t gameStaticResref{};
  std::uintptr_t gameStaticCurrentFrame{};
  std::uintptr_t gameStaticCurrentSequence{};
  // Optional generic-monster and Icewind-monster creature-sprite scopes for
  // the same high-level CVidCell bridge. BG2EE animation families 0x7000 and
  // 0xE000 use these distinct subclasses.
  std::uintptr_t monsterRender{};
  std::uintptr_t monsterIcewindRender{};
  std::uintptr_t monsterAnimationId{};
  std::uintptr_t monsterCurrentCell{};
  // Optional layered-character scope. BG2EE animation families 0x5000/0x6000
  // use this subclass. characterCurrentCell selects the body CVidCell;
  // characterOverlayCells select weapon, offhand/shield, and helmet cells.
  std::uintptr_t characterRender{};
  std::uintptr_t characterCurrentCell{};
  std::array<std::uintptr_t, 3> characterOverlayCells{};
  std::uintptr_t vidCellPalette{};
  std::uintptr_t vidCellResref{};
  std::uintptr_t vidCellCurrentFrame{};
  std::uintptr_t vidCellCurrentSequence{};
  std::array<std::string_view, 15> signatures{};
  // Position and height of the animated object, in pixels, inside CGameStatic.
  //
  // Found by static analysis of CGameStatic::RenderBam: its fog-of-war gate computes the
  // visibility cell as (drawingY - height) / 64 * areaWidthInTiles + positionX / 64, bounded by
  // the area's cell count. Runtime observation confirms that drawingY is ARE.y + ARE.height;
  // the hook therefore subtracts height to recover the registry's raw ARE y coordinate.
  //
  // OPTIONAL by design: a build without them keeps the historical behaviour of matching a
  // replacement texture on the resref alone, so a registry that binds a variant to a position
  // simply finds no match and the engine renders its own BAM.
  //
  // Appended after `signatures` rather than grouped with the other CGameStatic offsets because
  // this manifest is built from a positional initializer list: appending is the only edit that
  // cannot silently shift the RVAs that follow it.
  std::uintptr_t gameStaticPositionX{};
  std::uintptr_t gameStaticPositionY{};
  std::uintptr_t gameStaticHeight{};
  // Optional phase-0 diagnostic hook. It observes the native WED clipping pass
  // without altering its arguments, result, surface, or the subsequent draw.
  // Kept as an appended pair because this aggregate uses positional initializers.
  std::uintptr_t infinityFxRenderClippingPolys{};
  std::string_view infinityFxRenderClippingPolysSignature{};
  // Optional phase-1 bridge evidence. The OpenGL FX allocator keeps two
  // 0x30-byte CPU staging-pool descriptors here; the manifested LEA reference
  // must resolve to the exact data address before any alpha is observed.
  std::uintptr_t fxSurfacePool{};
  std::uintptr_t fxSurfacePoolReference{};
  std::string_view fxSurfacePoolReferenceSignature{};

  [[nodiscard]] constexpr bool validate() const noexcept {
    if (!enabled) return true;
    if (!gameStaticRenderBam || !vidCellRenderTexture || !drawDeleteTexture ||
        !drawGenTexture || !drawGetRenderer || !texImage || !glTextureState ||
        !glTextureTable || !glTextureTableReferences[0] ||
        !glTextureTableReferences[1] || !glTextureTableReferences[2] ||
        !glTextureSecondarySelectorReference ||
        !realizedPalette || !vidPaletteRealize || !vidPaletteRealizeCallsite ||
        !nativeTextureFormat || nativeTextureType != nativeTextureFormat + sizeof(std::uint32_t) ||
        !gameStaticResref || !gameStaticCurrentFrame || !gameStaticCurrentSequence ||
        !monsterRender || !monsterIcewindRender || !monsterAnimationId ||
        !monsterCurrentCell ||
        !characterRender || !characterCurrentCell || !characterOverlayCells[0] ||
        !characterOverlayCells[1] || !characterOverlayCells[2] || !vidCellPalette ||
        !vidCellResref || !vidCellCurrentFrame || !vidCellCurrentSequence) {
      return false;
    }
    for (const auto signature : signatures) {
      if (signature.empty()) return false;
    }
    const bool hasAnyPositionOffset =
        gameStaticPositionX || gameStaticPositionY || gameStaticHeight;
    const bool hasCompletePositionOffsets =
        gameStaticPositionX && gameStaticPositionY && gameStaticHeight;
    if (hasAnyPositionOffset && !hasCompletePositionOffsets) return false;
    const bool hasClippingProbeRva = infinityFxRenderClippingPolys != 0;
    const bool hasClippingProbeSignature = !infinityFxRenderClippingPolysSignature.empty();
    if (hasClippingProbeRva != hasClippingProbeSignature) return false;
    const bool hasAnyFxSurfaceEvidence =
        fxSurfacePool || fxSurfacePoolReference || !fxSurfacePoolReferenceSignature.empty();
    const bool hasCompleteFxSurfaceEvidence =
        fxSurfacePool && fxSurfacePoolReference && !fxSurfacePoolReferenceSignature.empty();
    if (hasAnyFxSurfaceEvidence && !hasCompleteFxSurfaceEvidence) return false;
    return true;
  }
};

// Optional map-composition point used by area-specific overlays. The overlay
// is drawn at the end of CGameArea::Render, while DrawBeginScaled's map
// framebuffer is still bound. DrawEndScaled then resolves the map (including
// the overlay) before any screen UI is composed.
struct WorldOverlayRuntime {
  bool enabled{};
  std::uintptr_t gameAreaRender{};
  std::string_view gameAreaRenderSignature{};
  std::uintptr_t drawFlushGl{};
  std::string_view drawFlushGlSignature{};

  [[nodiscard]] constexpr bool validate() const noexcept {
    return !enabled ||
           (gameAreaRender != 0 && !gameAreaRenderSignature.empty() && drawFlushGl != 0 &&
            !drawFlushGlSignature.empty());
  }
};

struct ExecutableVersion {
  static constexpr std::uint16_t kAnyRevision = 0xFFFF;

  std::uint16_t major{};
  std::uint16_t minor{};
  std::uint16_t patch{};
  std::uint16_t revision{};

  [[nodiscard]] constexpr bool matches(std::uint16_t candidateMajor, std::uint16_t candidateMinor,
                                       std::uint16_t candidatePatch,
                                       std::uint16_t candidateRevision) const noexcept {
    return major == candidateMajor && minor == candidateMinor && patch == candidatePatch &&
           (revision == kAnyRevision || revision == candidateRevision);
  }
};

struct BuildManifest {
  std::string_view buildId{};
  std::array<std::string_view, 2> supportedProductNames{};
  ExecutableVersion executableVersion{};
  PatternSet patterns{};
  ReferenceRvas referenceRvas{};
  RuntimeOffsets offsets{};
  AreaAnimationRuntime areaAnimations{};
  WorldOverlayRuntime worldOverlay{};
  std::array<BranchInstructionDesc, 11> renderTextureCallsites{};
  // Appended because this aggregate uses positional initializers.
  PvrDemandRuntime pvrDemand{};

  [[nodiscard]] constexpr bool validate() const noexcept {
    if (buildId.empty() || supportedProductNames[0].empty() || executableVersion.major == 0 ||
        patterns.loadArea.empty() || patterns.renderTexture.empty()) {
      return false;
    }
    if (!referenceRvas.loadArea || !referenceRvas.renderTexture) {
      return false;
    }
    if (!offsets.vidTileResource || !offsets.tisLinearTilesFlag ||
        !offsets.tisHeaderTileDimension) {
      return false;
    }
    if (!offsets.infGameVisibleArea || !offsets.infGameAreas || !offsets.infGameAreaMaster) {
      return false;
    }
    if (!areaAnimations.validate()) return false;
    if (!worldOverlay.validate()) return false;
    if (!pvrDemand.validate()) return false;

    for (const auto& callsite : renderTextureCallsites) {
      if (!callsite.validate()) {
        return false;
      }
    }

    return true;
  }
};

[[nodiscard]] const BuildManifest& current_manifest() noexcept;

[[nodiscard]] std::optional<std::reference_wrapper<const BuildManifest>> find_manifest(
    std::string_view buildId) noexcept;

[[nodiscard]] std::optional<std::reference_wrapper<const BuildManifest>> find_manifest_for_version(
    std::uint16_t major, std::uint16_t minor, std::uint16_t patch, std::uint16_t revision) noexcept;

// Sibling Infinity Engine games ship the same unified engine image and thus the
// same fixed file version; only the version resource distinguishes them. Select
// on version *and* product name so a shared version cannot pick a sibling's
// manifest.
[[nodiscard]] std::optional<std::reference_wrapper<const BuildManifest>> find_manifest_for_identity(
    std::uint16_t major, std::uint16_t minor, std::uint16_t patch, std::uint16_t revision,
    std::string_view productName);

// Product names are compared case-insensitively after removing ASCII
// punctuation/spacing. This accepts harmless version-resource punctuation
// differences while rejecting sibling Infinity Engine games.
[[nodiscard]] bool supports_product_name(const BuildManifest& manifest,
                                         std::string_view productName);

// Selects a manifest from the main executable's fixed file version. Unknown
// versions are deliberately unsupported and return nullptr before scanning
// or installing any hooks.
[[nodiscard]] const BuildManifest* detect_manifest(
    ExecutableVersion* detectedVersion = nullptr,
    std::string* detectedProductName = nullptr) noexcept;
}  // namespace iee::game
