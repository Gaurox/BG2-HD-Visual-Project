#include "effect_sharea_palette_fixtures.h"
#include "effect_native_projectile_palette_fixtures.h"
#include "effect_residual_projectile_palette_fixtures.h"
// Exercise the production effect uploader on a real hidden WGL context and
// a finite native descriptor allocator. A long spell sequence must leave a
// slot for the next Character composite, and recycled frames must stay exact.
#include <windows.h>
#include <algorithm>
#include <array>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>

#include "iee/effect_animation_x4_registry.h"
#include "iee/game/opengl_types.h"
// The engine header declares named GL error constants; include the legacy
// Windows GL macros afterwards so they cannot replace those declarations.
#include <GL/gl.h>

namespace {
std::uint32_t textureState{};
int boundSlot{};
std::array<GLuint, 512> names{};
struct Descriptor {
  std::uint32_t name{}, width{}, height{};
  std::uint8_t format{}, pending{};
  std::array<std::byte, 26> rest{};
};
static_assert(sizeof(Descriptor) == 0x28);
std::array<Descriptor, 512> descriptors{};
struct Queued { int slot{}, frame{}; GLuint program{}; };
std::vector<Queued> queued;
GLuint appliedProgram{}, desiredProgram{};
// Model the native applied-state cache: a repeated desired shader skips
// glUseProgram. DrawPush/PopState preserves desired state, not this cache.
void apply_program(GLuint program) {
  if (program != appliedProgram) {
    iee::game::gl::get_gl_functions().glUseProgram(program);
    appliedProgram = program;
  }
}
std::array<std::uint32_t, 16> savedStates{};
std::size_t stateDepth{};
bool queueCorrect{true};
std::uint64_t nativeFlushes{};
int logical_size(int frame) { return frame == 719 ? 4 : 2; }
void push() { savedStates[stateDepth++] = textureState; }
void pop() { textureState = savedStates[--stateDepth]; boundSlot = static_cast<int>(textureState >> 21u); }
void flush() {
  ++nativeFlushes;
  for (const auto& draw : queued) {
    apply_program(draw.program);
    if (descriptors[draw.slot].width != static_cast<std::uint32_t>(logical_size(draw.frame)) ||
        descriptors[draw.slot].height != static_cast<std::uint32_t>(logical_size(draw.frame)))
      queueCorrect = false;
    glBindTexture(GL_TEXTURE_2D, names[draw.slot]);
    std::vector<unsigned char> pixels(logical_size(draw.frame) * logical_size(draw.frame) * 64);
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels.data());
    for (std::size_t p = 0; p < pixels.size(); p += 4)
      if (pixels[p] != draw.frame % 251 || pixels[p + 1] != draw.frame / 251 || pixels[p + 3] != 255)
        queueCorrect = false;
  }
  queued.clear();
  textureState = 0; // A flush may alter the native compact state.
}
void collect() {
  flush();
  for (int slot = 1; slot < 512; ++slot) if (descriptors[slot].pending) {
    glDeleteTextures(1, &names[slot]); names[slot] = 0; descriptors[slot] = {};
  }
}
std::size_t peakSlots{};
bool denyAllocations{}, failUpload{};

int generate(int filter, unsigned char, int, unsigned char) {
  if (denyAllocations) return 0;
  for (int slot = 1; slot < 512; ++slot) {
    if (names[slot]) continue;
    glGenTextures(1, &names[slot]);
    descriptors[slot].name = names[slot];
    glBindTexture(GL_TEXTURE_2D, names[slot]);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filter);
    peakSlots = (std::max)(peakSlots, static_cast<std::size_t>(std::count_if(
        names.begin(), names.end(), [](GLuint name) { return name != 0; })));
    return slot;
  }
  return 0;
}
void bind(int slot) {
  boundSlot = slot;
  textureState = static_cast<std::uint32_t>(slot) << 21u;
  // Native DrawBindTexture only changes compact state, not GL binding.
}
void erase(int slot) {
  descriptors[slot].pending = 1;
}
void image(int width, int height, const void* pixels, unsigned char) {
  if (failUpload) { glBindTexture(GL_TEXTURE_2D, 0); return; }
  glBindTexture(GL_TEXTURE_2D, names[boundSlot]);
  descriptors[boundSlot].width = width; descriptors[boundSlot].height = height;
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA,
               GL_UNSIGNED_BYTE, pixels);
}
int renderer() { return 0; }
GLuint program(const char* fragment) {
  auto& gl = iee::game::gl::get_gl_functions();
  const auto shader = [&](unsigned type, const char* source) {
    const auto id = gl.glCreateShader(type);
    gl.glShaderSource(id, 1, &source, nullptr); gl.glCompileShader(id);
    int ok = 0; gl.glGetShaderiv(id, 0x8B81, &ok);
    if (!ok) { gl.glDeleteShader(id); return 0u; }
    return id;
  };
  const auto vertex = shader(0x8B31, "#version 120\nvoid main(){gl_Position=gl_Vertex;}");
  const auto pixel = shader(0x8B30, fragment);
  const auto id = gl.glCreateProgram();
  if (vertex) gl.glAttachShader(id, vertex);
  if (pixel) gl.glAttachShader(id, pixel);
  gl.glLinkProgram(id);
  int ok = 0; gl.glGetProgramiv(id, 0x8B82, &ok);
  if (vertex) gl.glDeleteShader(vertex);
  if (pixel) gl.glDeleteShader(pixel);
  if (!vertex || !pixel || !ok) { gl.glDeleteProgram(id); return 0; }
  return id;
}
bool verify_native_draw(GLuint red, const char* boundary) {
  GLint actualProgram = 0;
  glGetIntegerv(iee::game::gl::CURRENT_PROGRAM, &actualProgram);
  // The next native batch wants the same shader as the last flushed batch.
  // Its cache fast path must still produce red, never a stale white stripe.
  apply_program(red);
  glViewport(0, 0, 16, 16); glDisable(GL_SCISSOR_TEST); glDisable(GL_BLEND);
  glClearColor(0, 0, 0, 1); glClear(GL_COLOR_BUFFER_BIT);
  glBegin(GL_QUADS);
  glVertex2f(-0.25f, -1); glVertex2f(0.25f, -1);
  glVertex2f(0.25f, 1); glVertex2f(-0.25f, 1);
  glEnd();
  std::array<unsigned char, 4> pixel{};
  glReadPixels(8, 8, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel.data());
  const auto error = glGetError();
  const bool correct = static_cast<GLuint>(actualProgram) == appliedProgram &&
      pixel[0] == 255 && pixel[1] == 0 && pixel[2] == 0 && error == GL_NO_ERROR;
  std::cout << boundary << ": actualProgram=" << actualProgram << ", nativeCache=" << appliedProgram
            << ", pixel=" << int(pixel[0]) << ',' << int(pixel[1]) << ',' << int(pixel[2])
            << ", glError=" << error << '\n';
  return correct;
}
void u32(std::ofstream& out, std::uint32_t value) {
  out.write(reinterpret_cast<const char*>(&value), 4);
}
bool fixture(const std::filesystem::path& root) {
  std::filesystem::create_directories(root);
  std::ofstream out(root / "EffectAnimations-X4.registry", std::ios::binary);
  out.write("IEEEFX4\0", 8);
  u32(out, 1); u32(out, 4); u32(out, 1); u32(out, 0);
  out.write("CACHEFX1", 8); u32(out, 720); u32(out, 1);
  for (int i = 0; i < 720; ++i) { u32(out, logical_size(i)); u32(out, logical_size(i)); }
  u32(out, 720);
  for (int i = 0; i < 720; ++i) u32(out, i);
  for (int i = 0; i < 720; ++i) {
    std::vector<unsigned char> pixels(logical_size(i) * logical_size(i) * 64);
    for (std::size_t p = 0; p < pixels.size(); p += 4) {
      pixels[p] = static_cast<unsigned char>(i % 251);
      pixels[p + 1] = static_cast<unsigned char>(i / 251);
      pixels[p + 3] = 255;
    }
    char name[64]{};
    std::snprintf(name, sizeof(name), "EFX4-CACHEFX1-frame%03d.rgba", i);
    std::ofstream frame(root / name, std::ios::binary);
    frame.write(reinterpret_cast<const char*>(pixels.data()), pixels.size());
    if (!frame) return false;
  }
  return static_cast<bool>(out);
}
bool exercise(const std::filesystem::path& root) {
  if (!fixture(root) || !iee::effect_animation_x4::prepare(root)) return false;
  iee::effect_animation_x4::EngineTextureApi api{
      .DrawGenTexture = generate, .DrawBindTexture = bind,
      .DrawDeleteTexture = erase, .TexImage = image,
      .DrawGetRenderer = renderer, .glTextureState = &textureState,
      .DrawFlushGl = flush, .DrawPushState = push, .DrawPopState = pop,
      .glTextureTable = reinterpret_cast<std::byte*>(descriptors.data())};
  // Native/world/UI/other HD caches already occupy 400 out of 511 usable slots.
  for (int i = 0; i < 400; ++i) if (generate(GL_NEAREST, 0, 0, 0) <= 0) return false;
  bind(1);
  const auto verifyFrame = [&](int frame) {
    bind(1); // Native FX submission always binds its original descriptor first.
    int previous = 0;
    iee::effect_animation_x4::FrameHandle handle{};
    constexpr std::array<char, 8> ref{'C','A','C','H','E','F','X','1'};
    if (!iee::effect_animation_x4::resolve_frame(ref, 0, frame, logical_size(frame), logical_size(frame), handle) ||
        !iee::effect_animation_x4::bind_frame_texture(handle, api, previous) || previous != 1) return false;
    glBindTexture(GL_TEXTURE_2D, names[boundSlot]);
    GLint minFilter = 0, magFilter = 0, maximumMipLevel = -1;
    glGetTexParameteriv(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, &minFilter);
    glGetTexParameteriv(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, &magFilter);
    glGetTexParameteriv(GL_TEXTURE_2D, iee::game::gl::TEXTURE_MAX_LEVEL, &maximumMipLevel);
    if (minFilter != GL_NEAREST || magFilter != GL_NEAREST || maximumMipLevel != 0)
      return false;
    std::vector<unsigned char> actual(logical_size(frame) * logical_size(frame) * 64);
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, actual.data());
    if (glGetError() != GL_NO_ERROR) return false;
    for (std::size_t p = 0; p < actual.size(); p += 4) {
      if (actual[p] != frame % 251 || actual[p + 1] != frame / 251 ||
          actual[p + 2] != 0 || actual[p + 3] != 255) return false;
    }
    queued.push_back({boundSlot, frame, desiredProgram});
    iee::effect_animation_x4::restore_texture(api, previous);
    return boundSlot == 1;
  };
  for (int frame = 0; frame < 720; ++frame) {
    if (!verifyFrame(frame)) { std::cerr << "frame failed: " << frame << '\n'; return false; }
    // A Character composite must still be able to allocate its transient slot.
    const int character = generate(GL_NEAREST, 0, 0, 0);
    if (character <= 0) {
      std::cerr << "Character allocation failed after effect frame " << frame << '\n';
      return false;
    }
    erase(character); collect(); bind(1);
    if (!queueCorrect) return false;
  }
  const auto stats = iee::effect_animation_x4::texture_cache_stats();
  if (stats.capacity != 64 || stats.residentTextures != 64 || stats.reuses != 656 ||
      stats.allocationFailures || stats.uploadFailures || peakSlots > 465) return false;
  // Recent cache hit; then an evicted old frame; both have exact original pixels.
  const auto white = program("#version 120\nvoid main(){gl_FragColor=vec4(1.0);}");
  const auto red = program("#version 120\nvoid main(){gl_FragColor=vec4(1,0,0,1);}");
  if (!white || !red) return false;
  apply_program(white); desiredProgram = red;
  if (!verifyFrame(719) || !verifyFrame(0) || !verify_native_draw(red, "LRU upload")) return false;
  // Multiple effects in one native batch: old queued descriptors must be
  // consumed before the LRU reuses them, including different logical sizes.
  for (int i = 80; i < 160; ++i) if (!verifyFrame(i)) return false;
  flush(); bind(1);
  if (!queueCorrect || !nativeFlushes || stateDepth) return false;
  // Exercise recovery below capacity when native allocation is unavailable.
  apply_program(white);
  if (!verifyFrame(159)) return false;
  iee::effect_animation_x4::release_gpu(api);
  if (!verify_native_draw(red, "GPU release")) return false;
  collect();
  iee::effect_animation_x4::release_gpu(api);
  iee::effect_animation_x4::release();
  desiredProgram = 0; apply_program(0);
  if (!iee::effect_animation_x4::prepare(root) || !verifyFrame(0)) return false;
  denyAllocations = true;
  if (!verifyFrame(1)) return false;
  denyAllocations = false;
  failUpload = true;
  int previous = 0;
  if (iee::effect_animation_x4::bind_frame_texture({0, 2}, api, previous) || boundSlot != 1)
    return false;
  failUpload = false;
  if (!verifyFrame(2)) return false;
  const auto recovery = iee::effect_animation_x4::texture_cache_stats();
  if (recovery.allocationFailures != 1 || recovery.reuses != 1 ||
      recovery.uploadFailures != 1 || recovery.residentTextures > 3) return false;
  // A palette variant must never replace the neutral frame's cache entry.
  iee::core::area_lighting::Transfer tint{};
  for(unsigned c=0;c<3;++c) for(unsigned v=0;v<256;++v)
    tint.rgb[c][v]=static_cast<std::uint8_t>(c==0?std::min(v+1,255u):v);
  tint.valid=true;tint.fingerprint=iee::core::area_lighting::fingerprint(tint);
  api.paletteTransfer=&tint;
  if (!iee::effect_animation_x4::bind_frame_texture({0,2},api,previous)) return false;
  std::vector<unsigned char> tinted(logical_size(2)*logical_size(2)*64);
  glBindTexture(GL_TEXTURE_2D,names[boundSlot]);
  glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,tinted.data());
  if (tinted[0]!=3 || tinted[1]!=0 || tinted[2]!=0 || tinted[3]!=255) {
    std::cerr << "palette variant pixel=" << unsigned(tinted[0]) << ',' << unsigned(tinted[1])
        << ',' << unsigned(tinted[2]) << ',' << unsigned(tinted[3]) << '\n';
    return false;
  }
  iee::effect_animation_x4::restore_texture(api,previous);
  api.paletteTransfer=nullptr;
  if (!verifyFrame(2)) return false;
  // Same frame, different native ring palettes; no cross-variant GPU reuse,
  // neutral fallback remains exact, and conflicting transfer modes fail closed.
  for(unsigned variant:{3u,5u,6u,3u}) {
    auto transfer=iee::core::effect_indexed_palette::derive(shareaPalettes[variant],true);
    api.indexedPaletteTransfer=&transfer;
    if(!iee::effect_animation_x4::bind_frame_texture({0,2},api,previous))return false;
    glBindTexture(GL_TEXTURE_2D,names[boundSlot]);
    glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,tinted.data());
    const auto expected=iee::core::effect_indexed_palette::recolor({2,0,0},transfer);
    if(tinted[0]!=expected[0] || tinted[1]!=expected[1] || tinted[2]!=expected[2] || tinted[3]!=255)
      return false;
    iee::effect_animation_x4::restore_texture(api,previous);
    api.paletteTransfer=&tint;
    if(iee::effect_animation_x4::bind_frame_texture({0,2},api,previous))return false;
    api.paletteTransfer=nullptr;api.indexedPaletteTransfer=nullptr;
    if(!verifyFrame(2))return false;
  }
    // Reuse one GPU backing across different source-palette families; returning
    // to a previous tint or neutral must never retain another family's colors.
    using iee::core::effect_indexed_palette::SourceKind;
    for(const auto kind:{SourceKind::Air,SourceKind::Earth,SourceKind::HolyMight,SourceKind::Air}) {
      auto realized=kind==SourceKind::Air ? fixtureSHAIR4 :
                    kind==SourceKind::Earth ? fixtureSHEARTH6 : fixtureHLYMITE;
      if(kind==SourceKind::HolyMight) for(auto& value:realized)value&=0xffff0000u;
      auto transfer=iee::core::effect_indexed_palette::derive(realized,true,kind);
      if(!transfer.valid)return false;
      api.indexedPaletteTransfer=&transfer;
      if(!iee::effect_animation_x4::bind_frame_texture({0,2},api,previous))return false;
      glBindTexture(GL_TEXTURE_2D,names[boundSlot]);
      glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,tinted.data());
      const auto expected=iee::core::effect_indexed_palette::recolor({2,0,0},transfer);
      if(tinted[0]!=expected[0] || tinted[1]!=expected[1] || tinted[2]!=expected[2] || tinted[3]!=255)return false;
      iee::effect_animation_x4::restore_texture(api,previous);
      api.indexedPaletteTransfer=nullptr;
      if(!verifyFrame(2))return false;
    }
    {
      const auto tint=iee::core::effect_indexed_palette::derive(fixtureSPBOOM67,true,SourceKind::Boom);
      auto premult=tint;
      const auto normal=iee::core::effect_indexed_palette::for_draw(tint,true);
      api.indexedPaletteTransfer=&premult;
      if(!iee::effect_animation_x4::bind_frame_texture({0,2},api,previous))return false;
      iee::effect_animation_x4::restore_texture(api,previous);
      const auto before=iee::effect_animation_x4::texture_cache_stats().uploads;
      api.indexedPaletteTransfer=&normal;
      if(!iee::effect_animation_x4::bind_frame_texture({0,2},api,previous) ||
          iee::effect_animation_x4::texture_cache_stats().uploads!=before+1)return false;
      iee::effect_animation_x4::restore_texture(api,previous);
      api.indexedPaletteTransfer=nullptr;
      if(!verifyFrame(2))return false;
    }
    for(const auto& item:{std::pair{SourceKind::Water,fixtureSHWATER1},
                         std::pair{SourceKind::Boom,fixtureSPBOOM67},
                         std::pair{SourceKind::Water,fixtureSHWATER7},
                         std::pair{SourceKind::Boom,fixtureSPBOOM65},
                         std::pair{SourceKind::Boom,fixtureSPBOOM69}}) {
      const auto transfer=iee::core::effect_indexed_palette::derive(item.second,true,item.first);
      if(!transfer.valid)return false;
      api.indexedPaletteTransfer=&transfer;
      if(!iee::effect_animation_x4::bind_frame_texture({0,2},api,previous))return false;
      glBindTexture(GL_TEXTURE_2D,names[boundSlot]);
      glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,tinted.data());
      const auto expected=iee::core::effect_indexed_palette::recolor({2,0,0},transfer);
      if(tinted[0]!=expected[0] || tinted[1]!=expected[1] || tinted[2]!=expected[2] || tinted[3]!=255)return false;
      iee::effect_animation_x4::restore_texture(api,previous);
      api.indexedPaletteTransfer=nullptr;
      if(!verifyFrame(2))return false;
    }
    api.canvasWidth=4;api.canvasHeight=5;api.offsetX=1;api.offsetY=2;
  if (!iee::effect_animation_x4::bind_frame_texture({0,2},api,previous)) return false;
  glBindTexture(GL_TEXTURE_2D,names[boundSlot]);
  std::vector<unsigned char> canvas(4*5*64);
  glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,canvas.data());
  for(int y=0;y<20;++y) for(int x=0;x<16;++x) {
    const auto at=(y*16+x)*4;
    const bool inside=x>=4 && x<12 && y>=8 && y<16;
    if (canvas[at]!=(inside?2:0) || canvas[at+1]!=0 || canvas[at+2]!=0 ||
        canvas[at+3]!=(inside?255:0)) return false;
  }
  iee::effect_animation_x4::restore_texture(api,previous);
  // Native prefix + last HD layer on the real GL uploader. A changed shadow
  // or native alpha must not reuse another composite's GPU cache entry.
  std::vector<std::byte> prefix(4*5*4);
  for(std::size_t p=0;p<prefix.size();p+=4) {
    prefix[p]=std::byte{11};prefix[p+1]=std::byte{22};
    prefix[p+2]=std::byte{33};prefix[p+3]=std::byte{99};
  }
  api.nativeUnderlay=prefix;api.nativeOpacity=127;
  const auto verifyComposite=[&](unsigned corner,unsigned alpha) {
    if(!iee::effect_animation_x4::bind_frame_texture({0,2},api,previous)) return false;
    glBindTexture(GL_TEXTURE_2D,names[boundSlot]);
    glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,canvas.data());
    const auto center=(8*16+4)*4;
    const bool ok=canvas[0]==corner && canvas[1]==22 && canvas[2]==33 && canvas[3]==99 &&
        canvas[center]==2 && canvas[center+1]==0 && canvas[center+2]==0 && canvas[center+3]==alpha;
    iee::effect_animation_x4::restore_texture(api,previous);
    return ok;
  };
  if(!verifyComposite(11,127)) return false;
  prefix[0]=std::byte{55};if(!verifyComposite(55,127)) return false;
  api.nativeOpacity=191;if(!verifyComposite(55,191)) return false;
  api.nativeUnderlay={};api.nativeOpacity=255;
  // Already-padded source: remove rows before native-canvas placement, not
  // after upload. Cropped and complete variants cannot share a GPU entry.
  api.canvasWidth=4;api.canvasHeight=5;api.offsetX=1;api.offsetY=2;
  api.cropTop=1;
  if(!iee::effect_animation_x4::bind_frame_texture({0,2},api,previous))return false;
  glBindTexture(GL_TEXTURE_2D,names[boundSlot]);
  glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,canvas.data());
  for(int y=0;y<20;++y)for(int x=0;x<16;++x) {
    const auto at=(y*16+x)*4;
    const bool inside=x>=4 && x<12 && y>=8 && y<12;
    if(canvas[at]!=(inside?2:0) || canvas[at+3]!=(inside?255:0))return false;
  }
  iee::effect_animation_x4::restore_texture(api,previous);
  const auto uploadsBeforeCropVariant=iee::effect_animation_x4::texture_cache_stats().uploads;
  api.cropTop=0;api.cropBottom=1;
  if(!iee::effect_animation_x4::bind_frame_texture({0,2},api,previous) ||
      iee::effect_animation_x4::texture_cache_stats().uploads!=uploadsBeforeCropVariant+1)return false;
  iee::effect_animation_x4::restore_texture(api,previous);
  api.cropTop=2;
  if(iee::effect_animation_x4::bind_frame_texture({0,2},api,previous))return false;
  api.cropTop=api.cropBottom=0;
  api.offsetX=-1;
  if (iee::effect_animation_x4::bind_frame_texture({0,2},api,previous)) return false;
  api.canvasWidth=api.canvasHeight=api.offsetX=api.offsetY=0;
  if (!verifyFrame(2)) return false;
  iee::effect_animation_x4::release_gpu(api); collect();
  iee::effect_animation_x4::release_gpu(api); iee::effect_animation_x4::release();
  iee::effect_animation_x4::Options byteOptions;
  byteOptions.gpuBytes = 4096; // Byte pressure before the 64-descriptor limit.
  if (!iee::effect_animation_x4::prepare(root, byteOptions)) return false;
  for (int i = 0; i < 80; ++i) if (!verifyFrame(i)) return false;
  apply_program(white); desiredProgram = red;
  if (!verifyFrame(79)) return false; // Queue red while the hardware still uses white.
  if (!verifyFrame(719)) return false; // Requires shrinking several owned textures.
  if (!verify_native_draw(red, "Byte-pressure upload")) return false;
  flush(); bind(1);
  if (!queueCorrect || iee::effect_animation_x4::texture_cache_stats().peakBytes > byteOptions.gpuBytes)
    return false;
  iee::effect_animation_x4::release_gpu(api); collect();
  iee::effect_animation_x4::release_gpu(api); iee::effect_animation_x4::release();
  desiredProgram = 0; apply_program(0);
  auto& gl = iee::game::gl::get_gl_functions();
  gl.glDeleteProgram(white); gl.glDeleteProgram(red);
  byteOptions.streaming = true; byteOptions.cpu.bytes = 2048; byteOptions.cpu.inFlightBytes = 1024;
  byteOptions.cpu.headBytes = 512;
  if (!iee::effect_animation_x4::prepare(root, byteOptions)) return false;
  constexpr std::array<char, 8> ref{'C','A','C','H','E','F','X','1'};
  for (int i = 0; i < 80; ++i) {
    iee::effect_animation_x4::FrameHandle handle{};
    if (!iee::effect_animation_x4::resolve_frame(ref, 0, i, 2, 2, handle)) return false;
    iee::effect_animation_x4::prefetch_window(0x1234, ref, 0, i, false, true);
    const auto end = std::chrono::steady_clock::now() + std::chrono::seconds(3);
    while (iee::effect_animation_x4::cpu_frame_state(handle) != iee::core::EffectFrameCache::State::Ready &&
        std::chrono::steady_clock::now() < end) std::this_thread::sleep_for(std::chrono::milliseconds(1));
    if (!verifyFrame(i) || iee::effect_animation_x4::cpu_cache_stats().peakBytes > 2048) return false;
  }
  collect(); bind(1);
  if (!queueCorrect) return false;
  // Pending masked outputs remain charged until the native collector removes
  // them; reserving/cancelling an unsuccessful output must restore the budget.
  auto* table = reinterpret_cast<std::byte*>(descriptors.data());
  if (!iee::effect_animation_x4::reserve_scratch(320, table)) return false;
  const int scratch = generate(GL_NEAREST, 0, 0, 0);
  if (scratch <= 0) return false;
  iee::effect_animation_x4::track_scratch(scratch, 320, table);
  erase(scratch); iee::effect_animation_x4::retire_scratch(scratch);
  iee::effect_animation_x4::observe_gpu_retirements(api);
  if (iee::effect_animation_x4::texture_cache_stats().scratchBytes != 320 ||
      iee::effect_animation_x4::reserve_scratch(64ull << 20, table)) return false;
  collect(); bind(1); iee::effect_animation_x4::observe_gpu_retirements(api);
  if (iee::effect_animation_x4::texture_cache_stats().scratchBytes ||
      !iee::effect_animation_x4::reserve_scratch(128, table)) return false;
  iee::effect_animation_x4::cancel_scratch(128);
  if (iee::effect_animation_x4::texture_cache_stats().scratchBytes) return false;
  iee::effect_animation_x4::release_gpu(api); collect();
  iee::effect_animation_x4::release_gpu(api); iee::effect_animation_x4::release();
  // Regression: native SPMAGMIS is64x64, while its retained pack is64x78
  // and the actual FX destination can be64x88. Padding must never determine
  // the final draw dimensions or be applied twice. Inspect every GPU pixel.
  const auto padded=root/"padded";
  std::filesystem::create_directories(padded);
  std::vector<unsigned char> paddedPixels(64*78*64);
  for(int y=0;y<78*4;++y)for(int x=0;x<64*4;++x) {
    const auto at=(y*64*4+x)*4;
    paddedPixels[at]=static_cast<unsigned char>(y/4>=7 && y/4<71 ? y/4-6 : 230);
    paddedPixels[at+1]=77;paddedPixels[at+3]=255;
  }
  {
    std::ofstream registry(padded/"EffectAnimations-X4.registry",std::ios::binary);
    registry.write("IEEEFX4\0",8);u32(registry,1);u32(registry,4);u32(registry,1);u32(registry,0);
    registry.write("PADDEDFX",8);u32(registry,1);u32(registry,1);
    u32(registry,64);u32(registry,78);u32(registry,1);u32(registry,0);
    std::ofstream pixels(padded/"EFX4-PADDEDFX-frame000.rgba",std::ios::binary);
    pixels.write(reinterpret_cast<const char*>(paddedPixels.data()),paddedPixels.size());
  }
  if(!iee::effect_animation_x4::prepare(padded))return false;
  api.canvasWidth=64;api.offsetX=0;api.cropTop=api.cropBottom=7;
  for(const auto geometry:{std::array<int,2>{78,7},std::array<int,2>{88,0},std::array<int,2>{88,12}}) {
    api.canvasHeight=geometry[0];api.offsetY=geometry[1];
    bind(1); // The engine binds its original FX descriptor before replacement.
    if(!iee::effect_animation_x4::bind_frame_texture({0,0},api,previous))return false;
    glBindTexture(GL_TEXTURE_2D,names[boundSlot]);
    std::vector<unsigned char> readback(64*api.canvasHeight*64);
    glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,readback.data());
    for(int y=0;y<api.canvasHeight*4;++y)for(int x=0;x<64*4;++x) {
      const auto at=(y*64*4+x)*4;
      const bool inside=y>=api.offsetY*4 && y<(api.offsetY+64)*4;
      if(readback[at]!=(inside?y/4-api.offsetY+1:0) || readback[at+1]!=(inside?77:0) ||
          readback[at+2]!=0 || readback[at+3]!=(inside?255:0))return false;
    }
    iee::effect_animation_x4::restore_texture(api,previous);
  }
  std::ifstream original(padded/"EFX4-PADDEDFX-frame000.rgba",std::ios::binary);
  std::vector<unsigned char> unchanged(paddedPixels.size());
  original.read(reinterpret_cast<char*>(unchanged.data()),unchanged.size());
  if(unchanged!=paddedPixels)return false;
  iee::effect_animation_x4::release_gpu(api);collect();
  iee::effect_animation_x4::release_gpu(api);iee::effect_animation_x4::release();
  std::cout << "Padded64x78 source cropped to64x64 on native64x78/64x88 canvases: exact GPU pixels; source unchanged\n";
  std::cout << "720 distinct effect frames: exact GPU pixels, NEAREST min/mag, no mips, cache <=64; "
               "Character allocation succeeds on every frame with 400 occupied slots; "
               "LRU hit/reload, allocation pressure and upload recovery passed\n";
  return true;
}
}  // namespace

int main() {
  const auto root = std::filesystem::temp_directory_path() / "iee-effect-cache-hidden-gl-test";
  std::error_code error;
  std::filesystem::remove_all(root, error);
  HWND window = CreateWindowExW(WS_EX_NOACTIVATE, L"STATIC", L"IEE hidden cache test",
                                WS_POPUP, 0, 0, 16, 16, nullptr, nullptr, nullptr, nullptr);
  if (!window) return 1;
  const HDC dc = GetDC(window);
  PIXELFORMATDESCRIPTOR format{};
  format.nSize = sizeof(format); format.nVersion = 1;
  format.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL;
  format.iPixelType = PFD_TYPE_RGBA; format.cColorBits = 32; format.cAlphaBits = 8;
  const int pixelFormat = ChoosePixelFormat(dc, &format);
  const bool configured = pixelFormat && SetPixelFormat(dc, pixelFormat, &format);
  const HGLRC context = configured ? wglCreateContext(dc) : nullptr;
  bool success = false;
  if (context && wglMakeCurrent(dc, context)) {
    success = exercise(root);
    iee::effect_animation_x4::release();
    for (int slot = 1; slot < 512; ++slot) if (names[slot]) erase(slot);
    collect();
    wglMakeCurrent(nullptr, nullptr);
  }
  if (context) wglDeleteContext(context);
  ReleaseDC(window, dc); DestroyWindow(window);
  std::filesystem::remove_all(root, error);
  if (!success) std::cerr << "effect cache/Character slot regression failed\n";
  return success ? 0 : 1;
}
