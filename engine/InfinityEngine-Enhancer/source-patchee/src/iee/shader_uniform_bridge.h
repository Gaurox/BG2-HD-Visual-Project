#pragma once

#include <cstdint>

#include "iee/shader_suite.h"

namespace iee::probe::uniforms {

struct Locations {
  static constexpr int kUnresolved = -2;

  int time{kUnresolved};
  int enabled{kUnresolved};
  int shaderSuiteEnabled{kUnresolved};
  int scroll{kUnresolved};
  int zoom{kUnresolved};
  int viewport{kUnresolved};
  int worldSizeInv{kUnresolved};
  int waterTint{kUnresolved};
  int areaMask{kUnresolved};
  int normalMap{kUnresolved};
  int dudvMap{kUnresolved};
  int foamMap{kUnresolved};
  int creatureSampler{kUnresolved};
  int creatureFilterMode{kUnresolved};
  int creatureTexelSize{kUnresolved};
  int creatureStyleEnabled{kUnresolved};
  int creatureColorSpace{kUnresolved};
  int creatureSharpen{kUnresolved};
  int creatureGamma{kUnresolved};
  int creatureContrast{kUnresolved};
  int creatureBrightness{kUnresolved};
  int creatureSaturation{kUnresolved};
  int creatureHueDegrees{kUnresolved};
  int creatureOutlineMode{kUnresolved};
  int creatureOutlineSize{kUnresolved};
  int creatureTextureScale{kUnresolved};

  bool samplersInitialized{};
  bool viewInitialized{};
  bool worldSizeInitialized{};
  bool waterTintInitialized{};
  bool creatureStyleGateInitialized{};
  bool lastCreatureStyleEnabled{};
  bool creatureStyleParametersInitialized{};
  float lastScrollX{};
  float lastScrollY{};
  float lastViewWorldWidth{};
  float lastViewWorldHeight{};
  float lastWorldWidth{};
  float lastWorldHeight{};
  float lastWaterTintR{};
  float lastWaterTintG{};
  float lastWaterTintB{};
  float lastCreatureColorSpace{};
  float lastCreatureSharpen{};
  float lastCreatureGamma{};
  float lastCreatureContrast{};
  float lastCreatureBrightness{};
  float lastCreatureSaturation{};
  float lastCreatureHueDegrees{};
  float lastCreatureOutlineMode{};
  float lastCreatureOutlineSize{};
  float lastCreatureTextureScale{};
  int lastViewportWidth{};
  int lastViewportHeight{};
  std::uint64_t lastAppliedRevision{};
};

struct FeedPerformanceStats {
  std::uint64_t calls{};
  std::uint64_t skippedUnchanged{};
  std::uint64_t textureBindPasses{};
  std::uint64_t totalTicks{};
  std::uint64_t maximumTicks{};
};

struct Snapshot {
  float effectValue{};
  float scrollX{};
  float scrollY{};
  float viewWorldWidth{};
  float viewWorldHeight{};
  float worldWidth{};
  float worldHeight{};
  unsigned feedCount{};
};

void initialize(bool effectEnabled, bool shaderSuiteEnabled,
                bool performanceEnabled) noexcept;
void reset() noexcept;
void set_time(float secondsSinceStart) noexcept;
void set_effect_enabled(bool enabled) noexcept;
[[nodiscard]] bool effect_enabled() noexcept;
[[nodiscard]] float cycle_debug_effect() noexcept;
void set_world_size(float widthPx, float heightPx) noexcept;
void set_water_tint(float r, float g, float b) noexcept;
void set_view(float scrollX, float scrollY, float viewWorldWidth, float viewWorldHeight) noexcept;
[[nodiscard]] Snapshot snapshot() noexcept;
[[nodiscard]] FeedPerformanceStats take_performance_stats() noexcept;

// The caller owns program classification and location caching. This function
// only resolves missing locations and feeds the currently bound program.
void feed(unsigned program, Locations& locations);

// Per-draw creature routing. These uniforms deliberately bypass
// lastAppliedRevision because uTex may change while the program stays bound.
[[nodiscard]] bool resolve_creature_draw_locations(
    unsigned program, Locations& locations) noexcept;
[[nodiscard]] int creature_sampler_unit(unsigned program,
                                        Locations& locations) noexcept;
[[nodiscard]] bool set_creature_draw(unsigned program, Locations& locations,
                                     float mode, float texelWidth,
                                     float texelHeight,
                                     const shader_suite::CreatureHdDrawStyle& style) noexcept;

}  // namespace iee::probe::uniforms
