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

#include "iee/effect_animation_x4_registry.h"
#include "iee/game/opengl_types.h"
// The engine header declares named GL error constants; include the legacy
// Windows GL macros afterwards so they cannot replace those declarations.
#include <GL/gl.h>

namespace {
std::array<GLuint, 512> names{};
std::uint32_t textureState{};
int boundSlot{};
std::size_t peakSlots{};
bool denyAllocations{}, failUpload{};

int generate(int filter, unsigned char, int, unsigned char) {
  if (denyAllocations) return 0;
  for (int slot = 1; slot < 512; ++slot) {
    if (names[slot]) continue;
    glGenTextures(1, &names[slot]);
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
  glBindTexture(GL_TEXTURE_2D, names[slot]);
}
void erase(int slot) {
  glDeleteTextures(1, &names[slot]);
  names[slot] = 0;
}
void image(int width, int height, const void* pixels, unsigned char) {
  if (failUpload) { glBindTexture(GL_TEXTURE_2D, 0); return; }
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA,
               GL_UNSIGNED_BYTE, pixels);
}
int renderer() { return 0; }
void u32(std::ofstream& out, std::uint32_t value) {
  out.write(reinterpret_cast<const char*>(&value), 4);
}
bool fixture(const std::filesystem::path& root) {
  std::filesystem::create_directories(root);
  std::ofstream out(root / "EffectAnimations-X4.registry", std::ios::binary);
  out.write("IEEEFX4\0", 8);
  u32(out, 1); u32(out, 4); u32(out, 1); u32(out, 0);
  out.write("CACHEFX1", 8); u32(out, 720); u32(out, 1);
  for (int i = 0; i < 720; ++i) { u32(out, 2); u32(out, 2); }
  u32(out, 720);
  for (int i = 0; i < 720; ++i) u32(out, i);
  for (int i = 0; i < 720; ++i) {
    std::array<unsigned char, 8 * 8 * 4> pixels{};
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
      .DrawGetRenderer = renderer, .glTextureState = &textureState};
  // Native/world/UI/other HD caches already occupy 400 out of 511 usable slots.
  for (int i = 0; i < 400; ++i) if (generate(GL_NEAREST, 0, 0, 0) <= 0) return false;
  bind(1);
  const auto verifyFrame = [&](int frame) {
    int previous = 0;
    if (!iee::effect_animation_x4::bind_frame_texture(
            {0, static_cast<std::size_t>(frame)}, api, previous) || previous != 1) return false;
    GLint minFilter = 0, magFilter = 0, maximumMipLevel = -1;
    glGetTexParameteriv(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, &minFilter);
    glGetTexParameteriv(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, &magFilter);
    glGetTexParameteriv(GL_TEXTURE_2D, iee::game::gl::TEXTURE_MAX_LEVEL, &maximumMipLevel);
    if (minFilter != GL_NEAREST || magFilter != GL_NEAREST || maximumMipLevel != 0)
      return false;
    std::array<unsigned char, 8 * 8 * 4> actual{};
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, actual.data());
    if (glGetError() != GL_NO_ERROR) return false;
    for (std::size_t p = 0; p < actual.size(); p += 4) {
      if (actual[p] != frame % 251 || actual[p + 1] != frame / 251 ||
          actual[p + 2] != 0 || actual[p + 3] != 255) return false;
    }
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
    erase(character); bind(1);
  }
  const auto stats = iee::effect_animation_x4::texture_cache_stats();
  if (stats.capacity != 64 || stats.residentTextures != 64 || stats.reuses != 656 ||
      stats.allocationFailures || stats.uploadFailures || peakSlots > 465) return false;
  // Recent cache hit; then an evicted old frame; both have exact original pixels.
  if (!verifyFrame(719) || !verifyFrame(0)) return false;
  // Exercise recovery below capacity when native allocation is unavailable.
  iee::effect_animation_x4::release();
  for (int slot = 401; slot < 512; ++slot) if (names[slot]) erase(slot);
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
      recovery.uploadFailures != 1 || recovery.residentTextures != 2) return false;
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
    wglMakeCurrent(nullptr, nullptr);
  }
  if (context) wglDeleteContext(context);
  ReleaseDC(window, dc); DestroyWindow(window);
  std::filesystem::remove_all(root, error);
  if (!success) std::cerr << "effect cache/Character slot regression failed\n";
  return success ? 0 : 1;
}
