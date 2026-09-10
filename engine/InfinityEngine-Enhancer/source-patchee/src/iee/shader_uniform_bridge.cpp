#include "shader_uniform_bridge.h"

#include <windows.h>

#include <algorithm>
#include <atomic>

#include "area_state.h"
#include "iee/game/opengl_types.h"
#include "iee/game/texture_units.h"
#include "iee/water_textures.h"

namespace iee::probe::uniforms {
namespace {

std::atomic<float> g_time{0.0f};
std::atomic<float> g_worldWidth{0.0f};
std::atomic<float> g_worldHeight{0.0f};
std::atomic<float> g_scrollX{0.0f};
std::atomic<float> g_scrollY{0.0f};
std::atomic<float> g_viewWorldWidth{0.0f};
std::atomic<float> g_viewWorldHeight{0.0f};
std::atomic<float> g_waterTintR{0.5f};
std::atomic<float> g_waterTintG{0.5f};
std::atomic<float> g_waterTintB{0.5f};
std::atomic<float> g_effectValue{0.0f};
std::atomic<float> g_shaderSuiteEnabled{0.0f};
std::atomic<unsigned> g_feedCount{0};
std::atomic<std::uint64_t> g_stateRevision{1};
std::atomic<std::uint64_t> g_performanceCalls{0};
std::atomic<std::uint64_t> g_performanceSkipped{0};
std::atomic<std::uint64_t> g_performanceTextureBindPasses{0};
std::atomic<std::uint64_t> g_performanceTotalTicks{0};
std::atomic<std::uint64_t> g_performanceMaximumTicks{0};
std::atomic<bool> g_performanceEnabled{false};

int resolve_location(const game::gl::OpenGLFunctions& gl, unsigned program, int current,
                     const char* name) {
  if (current != Locations::kUnresolved) {
    return current;
  }
  return gl.glGetUniformLocation(program, name);
}

void advance_state_revision() noexcept {
  g_stateRevision.fetch_add(1, std::memory_order_release);
}

bool replace_if_changed(std::atomic<float>& target, float value) noexcept {
  return target.exchange(value, std::memory_order_relaxed) != value;
}

void update_maximum_ticks(std::uint64_t elapsed) noexcept {
  auto current = g_performanceMaximumTicks.load(std::memory_order_relaxed);
  while (current < elapsed && !g_performanceMaximumTicks.compare_exchange_weak(
                                  current, elapsed, std::memory_order_relaxed)) {
  }
}

void record_feed_performance(const LARGE_INTEGER& started, bool measured, bool skipped,
                             bool boundTextures) noexcept {
  if (!g_performanceEnabled.load(std::memory_order_relaxed)) return;
  g_performanceCalls.fetch_add(1, std::memory_order_relaxed);
  if (skipped) g_performanceSkipped.fetch_add(1, std::memory_order_relaxed);
  if (boundTextures) {
    g_performanceTextureBindPasses.fetch_add(1, std::memory_order_relaxed);
  }
  if (!measured) return;

  LARGE_INTEGER finished{};
  if (!QueryPerformanceCounter(&finished) || finished.QuadPart < started.QuadPart) return;
  const auto elapsed = static_cast<std::uint64_t>(finished.QuadPart - started.QuadPart);
  g_performanceTotalTicks.fetch_add(elapsed, std::memory_order_relaxed);
  update_maximum_ticks(elapsed);
}

}  // namespace

void initialize(bool effectEnabled, bool shaderSuiteEnabled,
                bool performanceEnabled) noexcept {
  g_effectValue.store(effectEnabled ? 1.0f : 0.0f, std::memory_order_relaxed);
  g_shaderSuiteEnabled.store(shaderSuiteEnabled ? 1.0f : 0.0f,
                             std::memory_order_relaxed);
  g_performanceEnabled.store(performanceEnabled, std::memory_order_relaxed);
  g_feedCount.store(0, std::memory_order_relaxed);
  g_stateRevision.store(1, std::memory_order_release);
}

void reset() noexcept {
  g_time.store(0.0f, std::memory_order_relaxed);
  g_worldWidth.store(0.0f, std::memory_order_relaxed);
  g_worldHeight.store(0.0f, std::memory_order_relaxed);
  g_scrollX.store(0.0f, std::memory_order_relaxed);
  g_scrollY.store(0.0f, std::memory_order_relaxed);
  g_viewWorldWidth.store(0.0f, std::memory_order_relaxed);
  g_viewWorldHeight.store(0.0f, std::memory_order_relaxed);
  g_waterTintR.store(0.5f, std::memory_order_relaxed);
  g_waterTintG.store(0.5f, std::memory_order_relaxed);
  g_waterTintB.store(0.5f, std::memory_order_relaxed);
  g_effectValue.store(0.0f, std::memory_order_relaxed);
  g_shaderSuiteEnabled.store(0.0f, std::memory_order_relaxed);
  g_performanceEnabled.store(false, std::memory_order_relaxed);
  g_feedCount.store(0, std::memory_order_relaxed);
  g_stateRevision.store(1, std::memory_order_release);
  (void)take_performance_stats();
}

void set_time(float secondsSinceStart) noexcept {
  if (replace_if_changed(g_time, secondsSinceStart)) advance_state_revision();
}

void set_effect_enabled(bool enabled) noexcept {
  if (replace_if_changed(g_effectValue, enabled ? 1.0f : 0.0f)) advance_state_revision();
}

bool effect_enabled() noexcept { return g_effectValue.load(std::memory_order_relaxed) >= 0.5f; }

float cycle_debug_effect() noexcept {
  const float current = g_effectValue.load(std::memory_order_relaxed);
  const float next = current < 0.5f ? 1.0f : (current < 1.5f ? 2.0f : 0.0f);
  g_effectValue.store(next, std::memory_order_relaxed);
  advance_state_revision();
  return next;
}

void set_world_size(float widthPx, float heightPx) noexcept {
  const bool changed = replace_if_changed(g_worldWidth, std::max(widthPx, 0.0f)) |
                       replace_if_changed(g_worldHeight, std::max(heightPx, 0.0f));
  if (changed) advance_state_revision();
}

void set_water_tint(float r, float g, float b) noexcept {
  const bool changed = replace_if_changed(g_waterTintR, r) | replace_if_changed(g_waterTintG, g) |
                       replace_if_changed(g_waterTintB, b);
  if (changed) advance_state_revision();
}

void set_view(float scrollX, float scrollY, float viewWorldWidth, float viewWorldHeight) noexcept {
  const bool changed =
      replace_if_changed(g_scrollX, scrollX) | replace_if_changed(g_scrollY, scrollY) |
      replace_if_changed(g_viewWorldWidth, std::max(viewWorldWidth, 0.0f)) |
      replace_if_changed(g_viewWorldHeight, std::max(viewWorldHeight, 0.0f));
  if (changed) advance_state_revision();
}

Snapshot snapshot() noexcept {
  return {
      .effectValue = g_effectValue.load(std::memory_order_relaxed),
      .scrollX = g_scrollX.load(std::memory_order_relaxed),
      .scrollY = g_scrollY.load(std::memory_order_relaxed),
      .viewWorldWidth = g_viewWorldWidth.load(std::memory_order_relaxed),
      .viewWorldHeight = g_viewWorldHeight.load(std::memory_order_relaxed),
      .worldWidth = g_worldWidth.load(std::memory_order_relaxed),
      .worldHeight = g_worldHeight.load(std::memory_order_relaxed),
      .feedCount = g_feedCount.load(std::memory_order_relaxed),
  };
}

FeedPerformanceStats take_performance_stats() noexcept {
  return {
      .calls = g_performanceCalls.exchange(0, std::memory_order_relaxed),
      .skippedUnchanged = g_performanceSkipped.exchange(0, std::memory_order_relaxed),
      .textureBindPasses =
          g_performanceTextureBindPasses.exchange(0, std::memory_order_relaxed),
      .totalTicks = g_performanceTotalTicks.exchange(0, std::memory_order_relaxed),
      .maximumTicks = g_performanceMaximumTicks.exchange(0, std::memory_order_relaxed),
  };
}

void feed(unsigned program, Locations& locations) {
  LARGE_INTEGER performanceStart{};
  const bool measurePerformance = g_performanceEnabled.load(std::memory_order_relaxed) &&
                                  QueryPerformanceCounter(&performanceStart) != 0;
  const auto& gl = game::gl::get_gl_functions();
  if (!gl.glGetUniformLocation || !gl.glUniform1f || !gl.glUniform1i || !gl.glUniform2f ||
      !gl.glUniform3f) {
    record_feed_performance(performanceStart, measurePerformance, false, false);
    return;
  }

  locations.time = resolve_location(gl, program, locations.time, "uIeeTime");
  locations.enabled = resolve_location(gl, program, locations.enabled, "uIeeEnabled");
  locations.shaderSuiteEnabled = resolve_location(
      gl, program, locations.shaderSuiteEnabled, "uIeeShaderSuiteEnabled");
  locations.scroll = resolve_location(gl, program, locations.scroll, "uIeeScroll");
  locations.zoom = resolve_location(gl, program, locations.zoom, "uIeeZoom");
  locations.viewport = resolve_location(gl, program, locations.viewport, "uIeeViewport");
  locations.worldSizeInv =
      resolve_location(gl, program, locations.worldSizeInv, "uIeeWorldSizeInv");
  locations.waterTint = resolve_location(gl, program, locations.waterTint, "uIeeWaterTint");
  locations.areaMask = resolve_location(gl, program, locations.areaMask, "uIeeAreaMask");
  locations.normalMap = resolve_location(gl, program, locations.normalMap, "uIeeNormalMap");
  locations.dudvMap = resolve_location(gl, program, locations.dudvMap, "uIeeDudvMap");
  locations.foamMap = resolve_location(gl, program, locations.foamMap, "uIeeFoamMap");

  g_feedCount.fetch_add(1, std::memory_order_relaxed);
  const auto stateRevision = g_stateRevision.load(std::memory_order_acquire);
  if (locations.lastAppliedRevision == stateRevision) {
    record_feed_performance(performanceStart, measurePerformance, true, false);
    return;
  }

  float effectValue = g_effectValue.load(std::memory_order_relaxed);
  bool boundTextures = false;
  if (effectValue >= 0.5f) {
    boundTextures = locations.areaMask >= 0 || locations.normalMap >= 0 || locations.dudvMap >= 0 ||
                    locations.foamMap >= 0;
    if (locations.areaMask >= 0 && !area::bind_area_texture()) {
      effectValue = 0.0f;
    }
    if ((locations.normalMap >= 0 || locations.dudvMap >= 0 || locations.foamMap >= 0) &&
        !water::ensure_water_textures_bound()) {
      effectValue = 0.0f;
    }
  }

  if (locations.time >= 0) {
    gl.glUniform1f(locations.time, g_time.load(std::memory_order_relaxed));
  }
  if (locations.enabled >= 0) {
    gl.glUniform1f(locations.enabled, effectValue);
  }
  if (locations.shaderSuiteEnabled >= 0) {
    gl.glUniform1f(locations.shaderSuiteEnabled,
                   g_shaderSuiteEnabled.load(std::memory_order_relaxed));
  }

  int viewport[4] = {0, 0, 0, 0};
  if (gl.glGetIntegerv) {
    gl.glGetIntegerv(0x0BA2 /* GL_VIEWPORT */, viewport);
  }
  const float scrollX = g_scrollX.load(std::memory_order_relaxed);
  const float scrollY = g_scrollY.load(std::memory_order_relaxed);
  const float viewWidth = g_viewWorldWidth.load(std::memory_order_relaxed);
  const float viewHeight = g_viewWorldHeight.load(std::memory_order_relaxed);
  const bool viewChanged =
      !locations.viewInitialized || locations.lastScrollX != scrollX ||
      locations.lastScrollY != scrollY || locations.lastViewWorldWidth != viewWidth ||
      locations.lastViewWorldHeight != viewHeight || locations.lastViewportWidth != viewport[2] ||
      locations.lastViewportHeight != viewport[3];
  if (viewChanged) {
    if (locations.scroll >= 0 && gl.glUniform2f) {
      gl.glUniform2f(locations.scroll, scrollX, scrollY);
    }
    if (locations.zoom >= 0 && gl.glUniform2f && viewWidth > 0.0f && viewHeight > 0.0f &&
        viewport[2] > 0 && viewport[3] > 0) {
      gl.glUniform2f(locations.zoom, static_cast<float>(viewport[2]) / viewWidth,
                     static_cast<float>(viewport[3]) / viewHeight);
    }
    if (locations.viewport >= 0 && gl.glUniform2f) {
      gl.glUniform2f(locations.viewport, static_cast<float>(viewport[2]),
                     static_cast<float>(viewport[3]));
    }
    locations.viewInitialized = true;
    locations.lastScrollX = scrollX;
    locations.lastScrollY = scrollY;
    locations.lastViewWorldWidth = viewWidth;
    locations.lastViewWorldHeight = viewHeight;
    locations.lastViewportWidth = viewport[2];
    locations.lastViewportHeight = viewport[3];
  }

  const float worldWidth = g_worldWidth.load(std::memory_order_relaxed);
  const float worldHeight = g_worldHeight.load(std::memory_order_relaxed);
  if ((!locations.worldSizeInitialized || locations.lastWorldWidth != worldWidth ||
       locations.lastWorldHeight != worldHeight) &&
      locations.worldSizeInv >= 0 && gl.glUniform2f && worldWidth > 0.0f && worldHeight > 0.0f) {
    gl.glUniform2f(locations.worldSizeInv, 1.0f / worldWidth, 1.0f / worldHeight);
    locations.worldSizeInitialized = true;
    locations.lastWorldWidth = worldWidth;
    locations.lastWorldHeight = worldHeight;
  }
  const float waterTintR = g_waterTintR.load(std::memory_order_relaxed);
  const float waterTintG = g_waterTintG.load(std::memory_order_relaxed);
  const float waterTintB = g_waterTintB.load(std::memory_order_relaxed);
  if ((!locations.waterTintInitialized || locations.lastWaterTintR != waterTintR ||
       locations.lastWaterTintG != waterTintG || locations.lastWaterTintB != waterTintB) &&
      locations.waterTint >= 0 && gl.glUniform3f) {
    gl.glUniform3f(locations.waterTint, waterTintR, waterTintG, waterTintB);
    locations.waterTintInitialized = true;
    locations.lastWaterTintR = waterTintR;
    locations.lastWaterTintG = waterTintG;
    locations.lastWaterTintB = waterTintB;
  }
  if (!locations.samplersInitialized && gl.glUniform1i) {
    if (locations.areaMask >= 0)
      gl.glUniform1i(locations.areaMask, static_cast<int>(game::texture_units::AreaMask));
    if (locations.normalMap >= 0)
      gl.glUniform1i(locations.normalMap, static_cast<int>(game::texture_units::WaterNormal));
    if (locations.dudvMap >= 0)
      gl.glUniform1i(locations.dudvMap, static_cast<int>(game::texture_units::WaterDudv));
    if (locations.foamMap >= 0)
      gl.glUniform1i(locations.foamMap, static_cast<int>(game::texture_units::WaterFoam));
    locations.samplersInitialized = true;
  }
  locations.lastAppliedRevision = stateRevision;
  record_feed_performance(performanceStart, measurePerformance, false, boundTextures);
}

bool resolve_creature_draw_locations(unsigned program,
                                     Locations& locations) noexcept {
  const auto& gl = game::gl::get_gl_functions();
  if (program == 0 || !gl.glGetUniformLocation || !gl.glGetUniformiv ||
      !gl.glUniform1f || !gl.glUniform2f || !gl.glGetIntegerv) {
    return false;
  }
  locations.creatureSampler = resolve_location(
      gl, program, locations.creatureSampler, "uTex");
  locations.creatureFilterMode = resolve_location(
      gl, program, locations.creatureFilterMode, "uIeeCreatureFilterMode");
  locations.creatureTexelSize = resolve_location(
      gl, program, locations.creatureTexelSize, "uIeeCreatureTexelSize");
  return locations.creatureSampler >= 0 && locations.creatureFilterMode >= 0 &&
         locations.creatureTexelSize >= 0;
}

int creature_sampler_unit(unsigned program, Locations& locations) noexcept {
  if (!resolve_creature_draw_locations(program, locations)) return -1;
  const auto& gl = game::gl::get_gl_functions();
  int unit = -1;
  gl.glGetUniformiv(program, locations.creatureSampler, &unit);
  return unit >= 0 && unit < 32 ? unit : -1;
}

bool set_creature_draw(unsigned program, Locations& locations, float mode,
                       float texelWidth, float texelHeight,
                       const shader_suite::CreatureHdDrawStyle& style) noexcept {
  if (!resolve_creature_draw_locations(program, locations)) return false;
  const auto& gl = game::gl::get_gl_functions();
  int currentProgram = 0;
  gl.glGetIntegerv(game::gl::CURRENT_PROGRAM, &currentProgram);
  if (currentProgram <= 0 || static_cast<unsigned>(currentProgram) != program) {
    return false;
  }
  gl.glUniform1f(locations.creatureFilterMode, mode);
  gl.glUniform2f(locations.creatureTexelSize, texelWidth, texelHeight);

  locations.creatureStyleEnabled = resolve_location(
      gl, program, locations.creatureStyleEnabled, "uIeeCreatureStyleEnabled");
  locations.creatureColorSpace = resolve_location(
      gl, program, locations.creatureColorSpace, "uIeeCreatureColorSpace");
  locations.creatureSharpen = resolve_location(
      gl, program, locations.creatureSharpen, "uIeeCreatureSharpen");
  locations.creatureGamma = resolve_location(
      gl, program, locations.creatureGamma, "uIeeCreatureGamma");
  locations.creatureContrast = resolve_location(
      gl, program, locations.creatureContrast, "uIeeCreatureContrast");
  locations.creatureBrightness = resolve_location(
      gl, program, locations.creatureBrightness, "uIeeCreatureBrightness");
  locations.creatureSaturation = resolve_location(
      gl, program, locations.creatureSaturation, "uIeeCreatureSaturation");
  locations.creatureHueDegrees = resolve_location(
      gl, program, locations.creatureHueDegrees, "uIeeCreatureHueDegrees");
  locations.creatureOutlineMode = resolve_location(
      gl, program, locations.creatureOutlineMode, "uIeeCreatureOutlineMode");
  locations.creatureOutlineSize = resolve_location(
      gl, program, locations.creatureOutlineSize, "uIeeCreatureOutlineSize");
  locations.creatureTextureScale = resolve_location(
      gl, program, locations.creatureTextureScale, "uIeeCreatureTextureScale");

  const bool styleLocationsReady =
      locations.creatureStyleEnabled >= 0 && locations.creatureColorSpace >= 0 &&
      locations.creatureSharpen >= 0 && locations.creatureGamma >= 0 &&
      locations.creatureContrast >= 0 && locations.creatureBrightness >= 0 &&
      locations.creatureSaturation >= 0 && locations.creatureHueDegrees >= 0 &&
      locations.creatureOutlineMode >= 0 && locations.creatureOutlineSize >= 0 &&
      locations.creatureTextureScale >= 0;
  const bool styleEnabled = style.active && styleLocationsReady;
  if (styleEnabled) {
    const bool initialize = !locations.creatureStyleParametersInitialized;
    const auto set_if_changed = [&](int location, float value, float& previous) {
      if (initialize || previous != value) {
        gl.glUniform1f(location, value);
        previous = value;
      }
    };
    set_if_changed(locations.creatureColorSpace, style.colorSpace,
                   locations.lastCreatureColorSpace);
    set_if_changed(locations.creatureSharpen, style.sharpen,
                   locations.lastCreatureSharpen);
    set_if_changed(locations.creatureGamma, style.gamma,
                   locations.lastCreatureGamma);
    set_if_changed(locations.creatureContrast, style.contrast,
                   locations.lastCreatureContrast);
    set_if_changed(locations.creatureBrightness, style.brightness,
                   locations.lastCreatureBrightness);
    set_if_changed(locations.creatureSaturation, style.saturation,
                   locations.lastCreatureSaturation);
    set_if_changed(locations.creatureHueDegrees, style.hueDegrees,
                   locations.lastCreatureHueDegrees);
    set_if_changed(locations.creatureOutlineMode, style.outlineMode,
                   locations.lastCreatureOutlineMode);
    set_if_changed(locations.creatureOutlineSize, style.outlineSize,
                   locations.lastCreatureOutlineSize);
    set_if_changed(locations.creatureTextureScale, style.textureScale,
                   locations.lastCreatureTextureScale);
    locations.creatureStyleParametersInitialized = true;
  }
  if (locations.creatureStyleEnabled >= 0 &&
      (!locations.creatureStyleGateInitialized ||
       locations.lastCreatureStyleEnabled != styleEnabled)) {
    gl.glUniform1f(locations.creatureStyleEnabled, styleEnabled ? 1.0f : 0.0f);
    locations.creatureStyleGateInitialized = true;
    locations.lastCreatureStyleEnabled = styleEnabled;
  }
  return true;
}

}  // namespace iee::probe::uniforms
