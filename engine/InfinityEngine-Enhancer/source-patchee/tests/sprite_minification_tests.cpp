#include <filesystem>
#include <chrono>
#include <fstream>
#include <iostream>

#include "iee/core/sprite_minification.h"
#include "iee/creature_sprite_filter.h"
#include "iee/creature_sprite_minification.h"

namespace {
int failures{}, minFilter{}, magFilter{}, maxLevel{}, generations{}, brokenLevel{};
void check(bool value, const char* message) {
  if (!value) { std::cerr << "FAIL: " << message << '\n'; ++failures; }
}
void APIENTRY parameter(unsigned, unsigned name, int value) {
  using namespace iee::game::gl;
  if (name == TEXTURE_MIN_FILTER) minFilter = value;
  if (name == TEXTURE_MAG_FILTER) magFilter = value;
  if (name == TEXTURE_MAX_LEVEL) maxLevel = value;
}
unsigned APIENTRY error() { return 0; }
void APIENTRY generate(unsigned) { ++generations; }
void APIENTRY dimensions(unsigned, int level, unsigned name, int* value) {
  *value = (std::max)(1, (name == iee::game::gl::TEXTURE_WIDTH ? 12 : 8) >> level);
  if (level == brokenLevel) *value = 0;
}
}

int main() {
  using iee::core::CreatureSpriteFilterMode;
  namespace math = iee::core::sprite_minification;
  using namespace iee::creature_sprite_filter;
  check(math::premultiply(0xffffffffu) == 0xffffffffu, "opaque RGB exact");
  check(math::premultiply(0x00ff7f01u) == 0, "hidden RGB cleared");
  check(math::premultiply(0x80ff8000u) == 0x80804000u, "alpha rounding in RGBA/BGRA");
  check(math::mip_layout(12, 8).maximumLevel == 3 && math::mip_layout(12, 8).bytes == 508,
        "NPOT levels include 12x8, 6x4, 3x2, 1x1");
  check(math::mip_layout(1, 8).bytes == 60 && math::mip_layout(-1, 8).bytes == 0,
        "one-axis chain and invalid dimensions");

  iee::game::gl::OpenGLFunctions gl{};
  gl.glTexParameteri = parameter; gl.glGetError = error;
  gl.glGenerateMipmap = generate; gl.glGetTexLevelParameteriv = dimensions;
  int level = -1;
  check(finish_texture_sampling(gl, CreatureSpriteFilterMode::Mipmaps, 12, 8, false, level) &&
        level == 3 && maxLevel == 3 && minFilter == 0x2703 && magFilter == 0x2600,
        "separate MIN trilinear / MAG nearest and full regenerated chain");
  check(finish_texture_sampling(gl, CreatureSpriteFilterMode::Mipmaps, 12, 8, true, level) &&
        generations == 2, "masked recomposition regenerates its own chain");
  brokenLevel = 2;
  check(!finish_texture_sampling(gl, CreatureSpriteFilterMode::Mipmaps, 12, 8, false, level) &&
        maxLevel == 0 && minFilter == 0x2600 && level == 0,
        "incomplete chain fails closed with MAX_LEVEL zero");
  brokenLevel = 0; gl.glGenerateMipmap = nullptr;
  check(!finish_texture_sampling(gl, CreatureSpriteFilterMode::Mipmaps, 12, 8, false, level),
        "missing GL generation fails closed");
  check(finish_texture_sampling(gl, CreatureSpriteFilterMode::Box, 12, 8, true, level) &&
        maxLevel == 0 && minFilter == 0x2600 && magFilter == 0x2600,
        "BOX reads exact texel centers after masking");
  check(finish_texture_sampling(gl, CreatureSpriteFilterMode::Nearest, 12, 8, true, level) &&
        minFilter == 0x2601 && magFilter == 0x2601, "legacy masked nearest keeps LINEAR");

  TextureRegistry registry;
  constexpr std::uintptr_t context = 0x1234;
  registry.configure(CreatureSpriteFilterMode::Mipmaps, 0x6110);
  check(!registry.publish(context, 1, 12, 8, 4, TextureProvenance::CharacterComposite, false, 0x6110),
        "mips publication requires premultiplied complete storage");
  check(registry.publish(context, 1, 12, 8, 4, TextureProvenance::CharacterComposite,
                         false, 0x6110, 3, true), "target mips registered");
  check(!registry.transfer_masked(context, 1, 2) && registry.transfer_masked(context, 1, 2, 3),
        "masked output cannot inherit stale parent levels");
  DrawObservation draw{.contextIdentity=context, .glName=2, .physicalWidth=12,
      .physicalHeight=8, .sampler=Sampler::TrilinearNearestMag, .routingProgram=true,
      .uniformsAvailable=true, .minificationContract=true, .maximumMipLevel=3};
  check(registry.decide(draw).owner && registry.decide(draw).mode == 4,
        "masked target retains premultiplied shader mode");
  draw.minificationContract = false;
  check(!registry.decide(draw).owner, "legacy shader cannot accept mip storage");
  draw.minificationContract = true; draw.maximumMipLevel = 0;
  check(!registry.decide(draw).owner, "sampler alone does not certify mips");
  check(registry.publish(context, 3, 12, 8, 4, TextureProvenance::Frame, false, 0x6100) &&
        registry.find(context, 3)->filterMode == CreatureSpriteFilterMode::Nearest,
        "other animation retains nearest and straight storage");
  check(registry.effective_mode(0x6110, 2) == CreatureSpriteFilterMode::Nearest,
        "x2 is outside new x4 minification modes");
  registry.configure(CreatureSpriteFilterMode::Box, 0x6110);
  check(!registry.find(context, 1) && registry.publish(context, 4, 12, 8, 4,
        TextureProvenance::Frame, false, 0x6110) && registry.transfer_masked(context, 4, 5),
        "mode transition clears registry and BOX masked storage stays straight");
  check(sampler_from_gl(0x2703, 0x2600) == Sampler::TrilinearNearestMag &&
        sampler_from_gl(0x2703, 0x2601) == Sampler::Unknown,
        "unsupported MIN/MAG pair rejected");

  const auto path = std::filesystem::temp_directory_path() /
      ("iee-p4-minification-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) + ".ini");
  iee::core::EngineConfig config{};
  config.creatureSpriteFilter = CreatureSpriteFilterMode::Mipmaps;
  config.creatureSpriteFilterAnimation = 0x6110;
  check(iee::core::ConfigManager::save(path, config), "config serialized");
  iee::core::EngineConfig loaded{};
  check(iee::core::ConfigManager::load(path, loaded) && loaded.creatureSpriteFilter == config.creatureSpriteFilter &&
        loaded.creatureSpriteFilterAnimation == 0x6110, "filter and animation scope roundtrip");
  { std::ofstream ini(path); ini << "[Shaders]\nCreatureSpriteFilter=Box\nCreatureSpriteFilterAnimation=oops\n"; }
  check(iee::core::ConfigManager::load(path, loaded) && loaded.creatureSpriteFilterAnimation == 0xffffu,
        "invalid scope never widens target to global");
  std::filesystem::remove(path);
  return failures == 0 ? 0 : 1;
}
