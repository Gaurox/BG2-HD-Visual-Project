#pragma once
#include <cstddef>
#include <cstdint>
#include <filesystem>

namespace iee::core {
struct EngineConfig {
  bool enableAnisotropicFiltering = false;
  float maxAnisotropy = 8.0f;
  float lodBias = -0.25f;
  // Generate a mip chain for upscaled PVRZ tile pages.  They are rendered
  // into the original 64px world quad and therefore normally minified.
  bool enableTileMipmaps = false;
  // Diagnostic switch: reapply tile filtering for every draw instead of
  // trusting the renderer's texture-state cache.
  bool forceTextureFilterEveryDraw = false;
  // Temporary WTPOOL-only diagnostic. It records the tile index seen by one
  // overlay draw instance; it never changes frame selection.
  bool enableWtpoolTileTrace = false;
  // Temporary A/B switch: delegate the x2 WPOOL00 page to the native
  // RenderTexture implementation instead of the custom tile renderer.
  bool bypassWtpoolTileRenderHook = false;
  // First-draw PVRZ-page diagnostics perform guarded engine-memory reads and
  // emit an INFO record for every observed page. Keep them opt-in so normal
  // rendering and performance telemetry do not pay that cost.
  bool enableTilePageDiagnostics = false;
  // Experimental map-only PVRZ prewarm. The engine's normal synchronous
  // Demand path remains authoritative for pages that are not ready yet.
  bool enableMapPagePrewarm = false;
  // Phase 3e-A read/decode-only probe. It never publishes bytes to the engine
  // or calls OpenGL; native Demand remains authoritative.
  bool enableMapPageOffframeProbe = false;
  // Phase 3e-B2 bounded diagnostics. The render thread may copy a fixed small
  // number of strictly matched prepared PVRs into destinations allocated by
  // native Demand per area generation; later pages use the native path.
  bool enableMapPageOffframeConsume = false;
  std::uint32_t mapPagePrewarmPagesPerFrame = 1;
  float mapPagePrewarmBudgetMs = 8.0f;
  // Leave 32 of the engine's evidenced 128 PVR slots outside the plan. This
  // is an engine-cache safety reserve, not a GPU-specific tuning value.
  std::uint32_t mapPagePrewarmMaxPages = 96;
  std::uint32_t mapPagePrewarmDelayFrames = 30;

  [[nodiscard]] constexpr bool wtpool_page_check_enabled() const noexcept {
    return enableWtpoolTileTrace || bypassWtpoolTileRenderHook;
  }
  // Diagnostic full-frame FXAA at the swap boundary. Until a world/UI render
  // bracket exists, this affects both the assembled world and the interface.
  bool enableFullFrameFxaa = false;
  // Diagnostic true supersampling: render both axes at 2x into an offscreen
  // target, then reduce the complete frame at presentation.
  bool enableFullFrameSsaa2x = false;

  bool dumpEngineShaders = false;
  bool enableDebugHotkeys = false;
  bool enableWaterEffect = true;
  // One-shot diagnostic for BAM/UI research. It logs texture uploads and
  // their call sites only; it never substitutes an asset or changes GL state.
  bool enableBamUiTextureProbe = false;
  // Reversible prototype: replace AM3000A's 248x221 uncompressed frame upload
  // with a 4x frame 000 texture while keeping the engine's draw geometry x1.
  bool enableAM3000AFrameX4Test = false;
  // Reversible prototype: replaces the seven fingerprinted AM0700A fountain
  // uploads at x4 while retaining the original x1 draw geometry and cadence.
  bool enableAM0700AAnimationX4Test = false;
  // Reversible prototype: replaces the nine fingerprinted AM0205E ground
  // animation uploads at x4 while retaining its original x1 draw geometry.
  bool enableAM0205EAnimationX4Test = false;
  // External multi-resource area-animation pack. Resrefs, BAM cycles and
  // native per-frame dimensions come from AreaAnimations-X4.registry.
  bool enableAreaAnimationX4 = false;
  // Read-only phase-0 diagnostic. Correlates the native WED clipping pass with
  // registry-backed xN draws; it never changes pixels or render state.
  bool enableNativeOcclusionProbe = false;
  // Experimental phase-1 A/B bridge. Captures the object-local visibility
  // transfer produced by the native WED clipping kernels and applies it to the
  // external xN backing. Disabled until the phase-0 in-game gates pass.
  bool enableNativeOcclusionBridge = false;
  // Reversible creature-sprite xN prototype. The native geometry remains x1;
  // the external registry supplies an x2 or x4 pixel backing.
  bool enableCreatureSpriteUpscaleTest = false;
  // Legacy activation key kept as an alias and regression surface for existing
  // x2 installations. New installers write EnableCreatureSpriteUpscaleTest.
  bool enableCreatureSpriteX2Test = false;
  // Explicit A/B diagnostic for creature-sprite xN backing textures. The
  // default remains NEAREST so released/validated packs retain pixel-exact
  // sampling; true selects OpenGL LINEAR for a reversible visual comparison.
  bool enableCreatureSpriteLinearFiltering = false;

  [[nodiscard]] constexpr bool creature_sprite_upscale_enabled() const noexcept {
    return enableCreatureSpriteUpscaleTest || enableCreatureSpriteX2Test;
  }
  // AR1300 BRIDGE01 transition: the final primary/secondary WED tile selection
  // drives bidirectional playback; F9 remains an opening-only diagnostic.
  bool enableBridgeTransitionPreview = false;
  // Reversible visual test: replace BIGLOGO's shared PVRZ page with a 4x
  // DXT5 atlas while leaving its BAM geometry untouched.
  bool enableBigLogoX4Test = false;
  // Reversible visual test: replace the static main-menu PVRZ pages (background,
  // title and button chrome) with 4x DXT5 atlases.  UI coordinates remain native.
  bool enableMainMenuX4Test = false;
  // Reversible comparison mode: replace the complete menu with x2 atlases.
  // This includes BIGLOGO and takes precedence over the x4 switches.
  bool enableMenuX2Test = false;

  bool enableVerboseLogging = false;
  bool enablePerformanceLogging = false;
};

struct ConfigLoadDiagnostics {
  bool fileExisted{};
  bool loadSucceeded{};
  bool defaultFileWritten{};
  std::size_t malformedLines{};
  std::size_t invalidValues{};
};

class ConfigManager {
 public:
  static std::filesystem::path config_path();

  static bool load(const std::filesystem::path& path, EngineConfig& out,
                   ConfigLoadDiagnostics* diagnostics = nullptr);

  static bool save(const std::filesystem::path& path, const EngineConfig& cfg);

  static EngineConfig load_or_default(ConfigLoadDiagnostics* diagnostics = nullptr);
};
}  // namespace iee::core
