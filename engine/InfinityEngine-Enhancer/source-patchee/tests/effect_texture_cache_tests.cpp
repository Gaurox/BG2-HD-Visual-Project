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
struct Queued { int slot{}, frame{}; };
std::vector<Queued> queued;
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
    queued.push_back({boundSlot, frame});
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
  if (!verifyFrame(719) || !verifyFrame(0)) return false;
  // Multiple effects in one native batch: old queued descriptors must be
  // consumed before the LRU reuses them, including different logical sizes.
  for (int i = 80; i < 160; ++i) if (!verifyFrame(i)) return false;
  flush(); bind(1);
  if (!queueCorrect || !nativeFlushes || stateDepth) return false;
  // Exercise recovery below capacity when native allocation is unavailable.
  iee::effect_animation_x4::release_gpu(api); collect();
  iee::effect_animation_x4::release_gpu(api);
  iee::effect_animation_x4::release();
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
  iee::effect_animation_x4::release_gpu(api); collect();
  iee::effect_animation_x4::release_gpu(api); iee::effect_animation_x4::release();
  iee::effect_animation_x4::Options byteOptions;
  byteOptions.gpuBytes = 4096; // Byte pressure before the 64-descriptor limit.
  if (!iee::effect_animation_x4::prepare(root, byteOptions)) return false;
  for (int i = 0; i < 80; ++i) if (!verifyFrame(i)) return false;
  if (!verifyFrame(719)) return false; // Requires shrinking several owned textures.
  flush(); bind(1);
  if (!queueCorrect || iee::effect_animation_x4::texture_cache_stats().peakBytes > byteOptions.gpuBytes)
    return false;
  iee::effect_animation_x4::release_gpu(api); collect();
  iee::effect_animation_x4::release_gpu(api); iee::effect_animation_x4::release();
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
