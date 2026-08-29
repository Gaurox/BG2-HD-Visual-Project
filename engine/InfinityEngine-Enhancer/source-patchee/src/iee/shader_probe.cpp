#include "shader_probe.h"

#include <intrin.h>
#include <windows.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cctype>
#include <cstdint>
#include <cstring>
#include <exception>
#include <filesystem>
#include <iterator>
#include <memory>
#include <mutex>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "iee/core/hooking.h"
#include "iee/core/logger.h"
#include "iee/core/map_texture_telemetry.h"
#include "iee/core/pvr_demand_telemetry.h"
#include "iee/am0205e_animation_x4_test.h"
#include "iee/am0700a_animation_x4_test.h"
#include "iee/am3000a_frame_x4_test.h"
#include "iee/biglogo_ui_upscale.h"
#include "iee/game/opengl_types.h"
#include "iee/game/renderer.h"
#include "iee/game/shader_override.h"
#include "iee/water_textures.h"
#include "shader_diagnostics.h"
#include "shader_uniform_bridge.h"

namespace iee::probe {
namespace {
constexpr unsigned SHADER_TYPE = 0x8B4F;
constexpr unsigned ATTACHED_SHADERS = 0x8B85;
constexpr unsigned COMPILE_STATUS = 0x8B81;
constexpr unsigned LINK_STATUS = 0x8B82;
constexpr unsigned INFO_LOG_LENGTH = 0x8B84;
constexpr unsigned VERTEX_SHADER = 0x8B31;
constexpr unsigned FRAGMENT_SHADER = 0x8B30;
constexpr unsigned SHADER_SOURCE_LENGTH = 0x8B88;

struct ShaderRecord {
  std::string sourcePreview;
  std::size_t sourceBytes{};
  bool compileLogged{};
  std::string shaderName;
};

struct ProgramRecord {
  bool linkLogged{};
  bool introspected{};
  std::unordered_set<std::uintptr_t> callerLogged;
};

// Hook signatures are aliases of the canonical OpenGL declarations.
using Fn_glShaderSource = game::gl::PFN_glShaderSource;
using Fn_glCompileShader = game::gl::PFN_glCompileShader;
using Fn_glDeleteShader = game::gl::PFN_glDeleteShader;
using Fn_glLinkProgram = game::gl::PFN_glLinkProgram;
using Fn_glUseProgram = game::gl::PFN_glUseProgram;
using Fn_glDeleteProgram = game::gl::PFN_glDeleteProgram;
using Fn_glShaderSourceARB = game::gl::PFN_glShaderSourceARB;
using Fn_glCompileShaderARB = game::gl::PFN_glCompileShaderARB;
using Fn_glLinkProgramARB = game::gl::PFN_glLinkProgramARB;
using Fn_glUseProgramObjectARB = game::gl::PFN_glUseProgramObjectARB;
using Fn_glDeleteObjectARB = game::gl::PFN_glDeleteObjectARB;
using Fn_glBindFramebuffer = game::gl::PFN_glBindFramebuffer;
using Fn_glGenTextures = game::gl::PFN_glGenTextures;
using Fn_glDeleteTextures = game::gl::PFN_glDeleteTextures;
using Fn_glTexImage2D = game::gl::PFN_glTexImage2D;
using Fn_glTexSubImage2D = game::gl::PFN_glTexSubImage2D;
using Fn_glCompressedTexImage2D = game::gl::PFN_glCompressedTexImage2D;

core::Hook<Fn_glShaderSource> g_glShaderSourceHook;
core::Hook<Fn_glCompileShader> g_glCompileShaderHook;
core::Hook<Fn_glDeleteShader> g_glDeleteShaderHook;
core::Hook<Fn_glLinkProgram> g_glLinkProgramHook;
core::Hook<Fn_glUseProgram> g_glUseProgramHook;
core::Hook<Fn_glDeleteProgram> g_glDeleteProgramHook;
core::Hook<Fn_glShaderSourceARB> g_glShaderSourceARBHook;
core::Hook<Fn_glCompileShaderARB> g_glCompileShaderARBHook;
core::Hook<Fn_glLinkProgramARB> g_glLinkProgramARBHook;
core::Hook<Fn_glUseProgramObjectARB> g_glUseProgramObjectARBHook;
core::Hook<Fn_glDeleteObjectARB> g_glDeleteObjectARBHook;
core::Hook<Fn_glBindFramebuffer> g_glBindFramebufferHook;
core::Hook<Fn_glGenTextures> g_glGenTexturesHook;
core::Hook<Fn_glDeleteTextures> g_glDeleteTexturesHook;
core::Hook<Fn_glTexImage2D> g_glTexImage2DHook;
core::Hook<Fn_glTexSubImage2D> g_glTexSubImage2DHook;
core::Hook<Fn_glCompressedTexImage2D> g_glCompressedTexImage2DHook;

void finish_queued_probe_hooks() noexcept {
  g_glShaderSourceHook.finish_queued_enable();
  g_glCompileShaderHook.finish_queued_enable();
  g_glDeleteShaderHook.finish_queued_enable();
  g_glLinkProgramHook.finish_queued_enable();
  g_glUseProgramHook.finish_queued_enable();
  g_glDeleteProgramHook.finish_queued_enable();
  g_glGenTexturesHook.finish_queued_enable();
  g_glDeleteTexturesHook.finish_queued_enable();
  g_glTexImage2DHook.finish_queued_enable();
  g_glTexSubImage2DHook.finish_queued_enable();
  g_glCompressedTexImage2DHook.finish_queued_enable();
  g_glShaderSourceARBHook.finish_queued_enable();
  g_glCompileShaderARBHook.finish_queued_enable();
  g_glLinkProgramARBHook.finish_queued_enable();
  g_glUseProgramObjectARBHook.finish_queued_enable();
  g_glDeleteObjectARBHook.finish_queued_enable();
  g_glBindFramebufferHook.finish_queued_enable();
}

bool remove_probe_hooks() noexcept {
  bool removed = true;
  removed = g_glCompressedTexImage2DHook.remove() && removed;
  removed = g_glTexSubImage2DHook.remove() && removed;
  removed = g_glTexImage2DHook.remove() && removed;
  removed = g_glDeleteTexturesHook.remove() && removed;
  removed = g_glGenTexturesHook.remove() && removed;
  removed = g_glBindFramebufferHook.remove() && removed;
  removed = g_glDeleteObjectARBHook.remove() && removed;
  removed = g_glUseProgramObjectARBHook.remove() && removed;
  removed = g_glLinkProgramARBHook.remove() && removed;
  removed = g_glCompileShaderARBHook.remove() && removed;
  removed = g_glShaderSourceARBHook.remove() && removed;
  removed = g_glUseProgramHook.remove() && removed;
  removed = g_glDeleteProgramHook.remove() && removed;
  removed = g_glLinkProgramHook.remove() && removed;
  removed = g_glDeleteShaderHook.remove() && removed;
  removed = g_glCompileShaderHook.remove() && removed;
  removed = g_glShaderSourceHook.remove() && removed;
  return removed;
}

std::uint64_t elapsed_nanoseconds(const LARGE_INTEGER& start,
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

std::mutex g_probeMutex;
std::unordered_map<unsigned, ShaderRecord> g_shaderRecords;
std::unordered_map<unsigned, ProgramRecord> g_programRecords;
std::unordered_map<unsigned, std::shared_ptr<uniforms::Locations>> g_overriddenPrograms;
std::set<std::string> g_dumpedShaders;  // names already written to disk
bool g_shaderProbesInstalled = false;
bool g_waterOverrideActiveLogged = false;
bool g_waterOverrideMissingLogged = false;
bool g_uniformsInitialized = false;
std::atomic<HGLRC> g_programContext{nullptr};
std::atomic<HGLRC> g_hookContext{nullptr};
std::atomic<bool> g_contextRefreshPending{false};
core::EngineConfig g_cfg;
std::filesystem::path g_dumpDir;
std::set<std::uint64_t> g_bamUiUploadsLogged;

struct BamAtlasKey {
  HGLRC context{};
  unsigned texture{};

  bool operator==(const BamAtlasKey& other) const noexcept {
    return context == other.context && texture == other.texture;
  }
};

struct BamAtlasKeyHash {
  std::size_t operator()(const BamAtlasKey& key) const noexcept {
    const auto context = reinterpret_cast<std::uintptr_t>(key.context);
    return std::hash<std::uintptr_t>{}(context) ^
           (std::hash<unsigned>{}(key.texture) + 0x9E3779B9u + (context << 6) +
            (context >> 2));
  }
};

std::mutex g_bamAtlasMutex;
std::unordered_set<BamAtlasKey, BamAtlasKeyHash> g_promotedBamAtlases;
std::atomic<bool> g_bamAtlasPromotionFailureLogged{false};
std::atomic<bool> g_bamAtlasUnsupportedUploadLogged{false};

constexpr int kBamAtlasLogicalSize = 1024;
constexpr int kBamAtlasScale = 4;

constexpr std::size_t kMaximumBamUiUploadLogs = 256;

std::uint64_t fnv1a64(const void* data, int byteCount) noexcept {
  if (!data || byteCount <= 0 || byteCount > 64 * 1024 * 1024) return 0;
  const auto* bytes = static_cast<const unsigned char*>(data);
  std::uint64_t value = 14695981039346656037ull;
#ifdef _WIN32
  __try {
#endif
    for (int index = 0; index < byteCount; ++index) {
      value ^= bytes[index];
      value *= 1099511628211ull;
    }
#ifdef _WIN32
  } __except (EXCEPTION_EXECUTE_HANDLER) {
    return 0;
  }
#endif
  return value;
}

void log_bam_ui_texture_upload(bool compressed, unsigned target, int level,
                               unsigned internalFormat, int width, int height,
                               int byteCount, const void* data,
                               std::uintptr_t caller) noexcept {
  // Only level zero carries an independently identifiable page. Keeping the
  // probe to large uploads avoids a mip-chain log flood and makes its overhead
  // bounded to the brief loading phase.
  if (!g_cfg.enableBamUiTextureProbe || target != game::gl::TEXTURE_2D || level != 0 ||
      width < 128 || height < 128) {
    return;
  }

  const auto fingerprint = fnv1a64(data, byteCount);
  const auto identity = fingerprint ^ (static_cast<std::uint64_t>(width) << 48) ^
                        (static_cast<std::uint64_t>(height) << 32) ^ internalFormat ^
                        (compressed ? 0x8000000000000000ull : 0ull);
  bool shouldLog = false;
  {
    std::lock_guard lock(g_probeMutex);
    if (g_bamUiUploadsLogged.size() < kMaximumBamUiUploadLogs) {
      shouldLog = g_bamUiUploadsLogged.insert(identity).second;
    }
  }
  if (!shouldLog) return;

  int textureName = 0;
  int activeUnit = 0;
  const auto& gl = game::gl::get_gl_functions();
  if (gl.glGetIntegerv) {
    gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &textureName);
    gl.glGetIntegerv(game::gl::ACTIVE_TEXTURE, &activeUnit);
  }
  LOG_INFO(
      "BAM/UI texture probe: compressed={}, texture={}, unit=0x{:X}, format=0x{:X}, "
      "size={}x{}, bytes={}, fnv1a64=0x{:016X}, {}",
      compressed, static_cast<unsigned>(textureName), activeUnit, internalFormat, width, height,
      byteCount, fingerprint,
      diagnostics::caller_summary(caller));
}

bool current_bam_atlas_key(unsigned target, BamAtlasKey& out) noexcept {
  if (target != game::gl::TEXTURE_2D) return false;
  const auto context = game::gl::current_context();
  const auto& gl = game::gl::get_gl_functions();
  if (!context || !gl.glGetIntegerv) return false;

  int texture = 0;
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &texture);
  if (texture <= 0) return false;
  out = {context, static_cast<unsigned>(texture)};
  return true;
}

bool is_promoted_bam_atlas(const BamAtlasKey& key) noexcept {
  std::lock_guard lock(g_bamAtlasMutex);
  return g_promotedBamAtlases.find(key) != g_promotedBamAtlases.end();
}

void remember_promoted_bam_atlas(const BamAtlasKey& key) {
  std::lock_guard lock(g_bamAtlasMutex);
  g_promotedBamAtlases.insert(key);
}

void forget_promoted_bam_atlas(const BamAtlasKey& key) noexcept {
  std::lock_guard lock(g_bamAtlasMutex);
  g_promotedBamAtlases.erase(key);
}

void forget_promoted_bam_textures(int count, const unsigned* textures) noexcept {
  if (count <= 0 || !textures) return;
  std::lock_guard lock(g_bamAtlasMutex);
  for (auto it = g_promotedBamAtlases.begin(); it != g_promotedBamAtlases.end();) {
    bool deleted = false;
    for (int index = 0; index < count; ++index) {
      if (it->texture == textures[index]) {
        deleted = true;
        break;
      }
    }
    it = deleted ? g_promotedBamAtlases.erase(it) : std::next(it);
  }
}

struct PixelStoreState {
  int alignment{4};
  int rowLength{};
  int skipRows{};
  int skipPixels{};
};

PixelStoreState read_unpack_state() noexcept {
  PixelStoreState state;
  const auto& gl = game::gl::get_gl_functions();
  if (!gl.glGetIntegerv) return state;
  gl.glGetIntegerv(game::gl::UNPACK_ALIGNMENT, &state.alignment);
  gl.glGetIntegerv(game::gl::UNPACK_ROW_LENGTH, &state.rowLength);
  gl.glGetIntegerv(game::gl::UNPACK_SKIP_ROWS, &state.skipRows);
  gl.glGetIntegerv(game::gl::UNPACK_SKIP_PIXELS, &state.skipPixels);
  if (state.alignment != 1 && state.alignment != 2 && state.alignment != 4 &&
      state.alignment != 8) {
    state.alignment = 4;
  }
  return state;
}

void set_tight_unpack() noexcept {
  const auto& gl = game::gl::get_gl_functions();
  if (!gl.glPixelStorei) return;
  gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, 1);
  gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH, 0);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS, 0);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS, 0);
}

void restore_unpack(const PixelStoreState& state) noexcept {
  const auto& gl = game::gl::get_gl_functions();
  if (!gl.glPixelStorei) return;
  gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, state.alignment);
  gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH, state.rowLength);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS, state.skipRows);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS, state.skipPixels);
}

int bytes_per_pixel(unsigned format, unsigned type) noexcept {
  if (type == game::gl::UNSIGNED_INT_8_8_8_8 ||
      type == game::gl::UNSIGNED_INT_8_8_8_8_REV) {
    return 4;
  }
  // Packed 16-bit colour representations used by legacy GL paths.
  if (type == 0x8033 || type == 0x8034 || type == 0x8363 || type == 0x8364 ||
      type == 0x8365 || type == 0x8366) {
    return 2;
  }
  if (type != game::gl::UNSIGNED_BYTE) return 0;
  switch (format) {
    case game::gl::RGBA:
    case game::gl::BGRA:
      return 4;
    case game::gl::RGB:
    case game::gl::BGR:
      return 3;
    case game::gl::LUMINANCE_ALPHA:
      return 2;
    case game::gl::RED:
    case game::gl::ALPHA:
    case game::gl::LUMINANCE:
      return 1;
    default:
      return 0;
  }
}

std::vector<unsigned char> upscale_subimage_nearest(const void* data, int width, int height,
                                                     unsigned format, unsigned type,
                                                     const PixelStoreState& state) {
  if (!data || width <= 0 || height <= 0 || width > 4096 || height > 4096) return {};
  const auto& gl = game::gl::get_gl_functions();
  if (!gl.glGetIntegerv) return {};

  int unpackBuffer = 0;
  gl.glGetIntegerv(game::gl::PIXEL_UNPACK_BUFFER_BINDING, &unpackBuffer);
  if (unpackBuffer != 0) return {};

  const int pixelBytes = bytes_per_pixel(format, type);
  if (pixelBytes <= 0) return {};
  const int rowPixels = state.rowLength > 0 ? state.rowLength : width;
  if (state.skipRows < 0 || state.skipPixels < 0 || rowPixels < state.skipPixels + width) {
    return {};
  }

  const std::size_t unalignedStride =
      static_cast<std::size_t>(rowPixels) * static_cast<std::size_t>(pixelBytes);
  const std::size_t alignment = static_cast<std::size_t>(state.alignment);
  const std::size_t sourceStride = (unalignedStride + alignment - 1) & ~(alignment - 1);
  const std::size_t sourceStart = static_cast<std::size_t>(state.skipRows) * sourceStride +
                                  static_cast<std::size_t>(state.skipPixels) * pixelBytes;
  const std::size_t destinationWidth = static_cast<std::size_t>(width) * kBamAtlasScale;
  const std::size_t destinationHeight = static_cast<std::size_t>(height) * kBamAtlasScale;
  const std::size_t destinationStride = destinationWidth * pixelBytes;
  std::vector<unsigned char> scaled(destinationStride * destinationHeight);
  const auto* sourceBytes = static_cast<const unsigned char*>(data);

  for (int sourceY = 0; sourceY < height; ++sourceY) {
    const auto* sourceRow = sourceBytes + sourceStart +
                            static_cast<std::size_t>(sourceY) * sourceStride;
    for (int repeatY = 0; repeatY < kBamAtlasScale; ++repeatY) {
      auto* destinationRow =
          scaled.data() +
          (static_cast<std::size_t>(sourceY) * kBamAtlasScale + repeatY) * destinationStride;
      for (int sourceX = 0; sourceX < width; ++sourceX) {
        const auto* sourcePixel = sourceRow + static_cast<std::size_t>(sourceX) * pixelBytes;
        auto* destinationPixel =
            destinationRow + static_cast<std::size_t>(sourceX) * kBamAtlasScale * pixelBytes;
        for (int repeatX = 0; repeatX < kBamAtlasScale; ++repeatX) {
          std::memcpy(destinationPixel + static_cast<std::size_t>(repeatX) * pixelBytes,
                      sourcePixel, pixelBytes);
        }
      }
    }
  }
  return scaled;
}

std::vector<unsigned char> upscale_rgba_atlas_nearest(const unsigned char* source, int width,
                                                       int height) {
  if (!source || width <= 0 || height <= 0) return {};
  const std::size_t destinationWidth = static_cast<std::size_t>(width) * kBamAtlasScale;
  const std::size_t destinationHeight = static_cast<std::size_t>(height) * kBamAtlasScale;
  std::vector<unsigned char> scaled(destinationWidth * destinationHeight * 4);
  for (int sourceY = 0; sourceY < height; ++sourceY) {
    const auto* sourceRow = source + static_cast<std::size_t>(sourceY) * width * 4;
    for (int repeatY = 0; repeatY < kBamAtlasScale; ++repeatY) {
      auto* destinationRow =
          scaled.data() +
          (static_cast<std::size_t>(sourceY) * kBamAtlasScale + repeatY) *
              destinationWidth * 4;
      for (int sourceX = 0; sourceX < width; ++sourceX) {
        const auto* sourcePixel = sourceRow + static_cast<std::size_t>(sourceX) * 4;
        auto* destinationPixel =
            destinationRow + static_cast<std::size_t>(sourceX) * kBamAtlasScale * 4;
        for (int repeatX = 0; repeatX < kBamAtlasScale; ++repeatX) {
          std::memcpy(destinationPixel + static_cast<std::size_t>(repeatX) * 4, sourcePixel, 4);
        }
      }
    }
  }
  return scaled;
}

bool promote_bound_bam_atlas(const BamAtlasKey& key, unsigned target, int level, int xoffset,
                             int yoffset, int sourceWidth, int sourceHeight,
                             const am0205e_x4::ReplacementUpload& replacement,
                             const PixelStoreState& unpackState) {
  const auto& gl = game::gl::get_gl_functions();
  if (!gl.glGetTexLevelParameteriv || !gl.glGetTexImage || !gl.glGetIntegerv ||
      !gl.glPixelStorei || !g_glTexImage2DHook.original()) {
    return false;
  }

  int atlasWidth = 0;
  int atlasHeight = 0;
  gl.glGetTexLevelParameteriv(target, level, game::gl::TEXTURE_WIDTH, &atlasWidth);
  gl.glGetTexLevelParameteriv(target, level, game::gl::TEXTURE_HEIGHT, &atlasHeight);
  if (atlasWidth != kBamAtlasLogicalSize || atlasHeight != kBamAtlasLogicalSize ||
      xoffset < 0 || yoffset < 0 || xoffset + sourceWidth > atlasWidth ||
      yoffset + sourceHeight > atlasHeight ||
      replacement.width != sourceWidth * kBamAtlasScale ||
      replacement.height != sourceHeight * kBamAtlasScale || !replacement.data) {
    return false;
  }

  int maximumTextureSize = 0;
  int packBuffer = 0;
  gl.glGetIntegerv(game::gl::MAX_TEXTURE_SIZE, &maximumTextureSize);
  gl.glGetIntegerv(game::gl::PIXEL_PACK_BUFFER_BINDING, &packBuffer);
  if (maximumTextureSize < atlasWidth * kBamAtlasScale || packBuffer != 0) return false;

  std::vector<unsigned char> original(static_cast<std::size_t>(atlasWidth) * atlasHeight * 4);
  int packAlignment = 4;
  gl.glGetIntegerv(game::gl::PACK_ALIGNMENT, &packAlignment);
  game::gl::discard_errors();
  gl.glPixelStorei(game::gl::PACK_ALIGNMENT, 1);
  gl.glGetTexImage(target, level, game::gl::RGBA, game::gl::UNSIGNED_BYTE, original.data());
  gl.glPixelStorei(game::gl::PACK_ALIGNMENT, packAlignment);
  if (gl.glGetError && gl.glGetError() != game::gl::GL_NO_ERROR) return false;

  auto promoted = upscale_rgba_atlas_nearest(original.data(), atlasWidth, atlasHeight);
  if (promoted.empty()) return false;
  const auto* replacementBytes = static_cast<const unsigned char*>(replacement.data);
  const std::size_t promotedStride =
      static_cast<std::size_t>(atlasWidth) * kBamAtlasScale * 4;
  const std::size_t replacementStride = static_cast<std::size_t>(replacement.width) * 4;
  for (int row = 0; row < replacement.height; ++row) {
    auto* destination =
        promoted.data() +
        (static_cast<std::size_t>(yoffset) * kBamAtlasScale + row) * promotedStride +
        static_cast<std::size_t>(xoffset) * kBamAtlasScale * 4;
    std::memcpy(destination, replacementBytes + static_cast<std::size_t>(row) * replacementStride,
                replacementStride);
  }

  remember_promoted_bam_atlas(key);
  game::gl::discard_errors();
  set_tight_unpack();
  g_glTexImage2DHook.original()(target, level, static_cast<int>(game::gl::RGBA8),
                                atlasWidth * kBamAtlasScale,
                                atlasHeight * kBamAtlasScale, 0, game::gl::RGBA,
                                game::gl::UNSIGNED_BYTE, promoted.data());
  restore_unpack(unpackState);
  if (gl.glGetError && gl.glGetError() != game::gl::GL_NO_ERROR) {
    forget_promoted_bam_atlas(key);
    set_tight_unpack();
    g_glTexImage2DHook.original()(target, level, static_cast<int>(game::gl::RGBA8), atlasWidth,
                                  atlasHeight, 0, game::gl::RGBA,
                                  game::gl::UNSIGNED_BYTE, original.data());
    restore_unpack(unpackState);
    return false;
  }
  return true;
}

// Set by install; consumed by the first frame tick (sweep runs at the
// frame boundary, never mid-draw).
std::atomic<bool> g_sweepPending{false};

bool ensure_program_context() {
  const auto context = game::gl::current_context();
  if (context == g_programContext.load(std::memory_order_acquire)) return false;

  std::lock_guard lock(g_probeMutex);
  if (context == g_programContext.load(std::memory_order_relaxed)) return false;

  // Shader and program names are scoped to a WGL context and may be reused by
  // a replacement context. Never carry classifications or uniform locations
  // across that boundary.
  g_shaderRecords.clear();
  g_programRecords.clear();
  g_overriddenPrograms.clear();
  g_waterOverrideActiveLogged = false;
  g_waterOverrideMissingLogged = false;
  g_programContext.store(context, std::memory_order_release);
  return true;
}

std::string sanitize_preview(std::string text) {
  for (char& ch : text) {
    if (ch == '\n' || ch == '\r' || ch == '\t') ch = ' ';
  }
  constexpr std::size_t kMaxPreviewBytes = 240;
  if (text.size() > kMaxPreviewBytes) {
    text.resize(kMaxPreviewBytes);
    text += "...";
  }
  return text;
}

// Joins ALL chunks into a single string, honouring lengths[i] >= 0.
std::string gather_full_source(int count, const char* const* strings, const int* lengths) {
  if (count <= 0 || !strings) return {};
  std::string combined;
  for (int i = 0; i < count; ++i) {
    const char* chunk = strings[i];
    if (!chunk) continue;
    std::size_t chunkSize = (lengths && lengths[i] >= 0) ? static_cast<std::size_t>(lengths[i])
                                                         : std::char_traits<char>::length(chunk);
    combined.append(chunk, chunkSize);
  }
  return combined;
}

std::string sanitized_preview_of(std::string_view source) {
  std::string s(source.substr(0, 256));
  return sanitize_preview(std::move(s));
}

const char* shader_type_name(int shaderType) noexcept {
  switch (shaderType) {
    case VERTEX_SHADER:
      return "vertex";
    case FRAGMENT_SHADER:
      return "fragment";
    default:
      return "unknown";
  }
}

std::string read_shader_log(const game::gl::OpenGLFunctions& gl, unsigned shader) {
  if (!gl.glGetShaderiv || !gl.glGetShaderInfoLog) return {};
  int infoLogLength = 0;
  gl.glGetShaderiv(shader, INFO_LOG_LENGTH, &infoLogLength);
  if (infoLogLength <= 1) return {};
  std::string infoLog(static_cast<std::size_t>(infoLogLength), '\0');
  int written = 0;
  gl.glGetShaderInfoLog(shader, infoLogLength, &written, infoLog.data());
  if (written > 0 && written < infoLogLength) infoLog.resize(static_cast<std::size_t>(written));
  return sanitize_preview(std::move(infoLog));
}

std::string read_program_log(const game::gl::OpenGLFunctions& gl, unsigned program) {
  if (!gl.glGetProgramiv || !gl.glGetProgramInfoLog) return {};
  int infoLogLength = 0;
  gl.glGetProgramiv(program, INFO_LOG_LENGTH, &infoLogLength);
  if (infoLogLength <= 1) return {};
  std::string infoLog(static_cast<std::size_t>(infoLogLength), '\0');
  int written = 0;
  gl.glGetProgramInfoLog(program, infoLogLength, &written, infoLog.data());
  if (written > 0 && written < infoLogLength) infoLog.resize(static_cast<std::size_t>(written));
  return sanitize_preview(std::move(infoLog));
}

std::string read_shader_source_preview(const game::gl::OpenGLFunctions& gl, unsigned shader) {
  if (!gl.glGetShaderSource) return {};
  constexpr int kMaxSourceBytes = 1024;
  std::array<char, kMaxSourceBytes> buffer{};
  int written = 0;
  gl.glGetShaderSource(shader, kMaxSourceBytes, &written, buffer.data());
  if (written <= 0) return {};
  return sanitize_preview(std::string(buffer.data(), static_cast<std::size_t>(written)));
}

// Un-truncated source prefix for content checks (the 240-byte sanitized
// preview is for logs only — uniform declarations sit past it when the
// engine prepends its header block; confirmed live 2026-06-11).
std::string read_shader_source_prefix(const game::gl::OpenGLFunctions& gl, unsigned shader,
                                      int maxBytes = 4096) {
  if (!gl.glGetShaderiv || !gl.glGetShaderSource) return {};
  int sourceLength = 0;
  gl.glGetShaderiv(shader, SHADER_SOURCE_LENGTH, &sourceLength);
  if (sourceLength <= 1) return {};
  const int cap = sourceLength < maxBytes ? sourceLength : maxBytes;
  std::string buffer(static_cast<std::size_t>(cap), '\0');
  int written = 0;
  gl.glGetShaderSource(shader, cap, &written, buffer.data());
  if (written <= 0) return {};
  buffer.resize(static_cast<std::size_t>(written));
  return buffer;
}

std::string_view get_gl_string(const game::gl::OpenGLFunctions& gl, unsigned name) noexcept {
  if (!gl.glGetString) return {};
  const auto* value = gl.glGetString(name);
  if (!value) return {};
  return reinterpret_cast<const char*>(value);
}

std::optional<int> infer_program_slot(std::string_view vertexShaderName,
                                      std::string_view fragmentShaderName) {
  if (vertexShaderName == "vpDraw" && fragmentShaderName == "fpDraw") return 0;
  if (vertexShaderName == "vpDraw" && fragmentShaderName == "fpTone") return 1;
  if (vertexShaderName == "vpBlit" && fragmentShaderName == "fpCatRom") return 2;
  if ((vertexShaderName == "vpYUV" || vertexShaderName == "vpDraw") &&
      fragmentShaderName == "fpYUV")
    return 3;
  if (vertexShaderName == "vpYUV" && fragmentShaderName == "fpYUVGRY") return 4;
  if (vertexShaderName == "vpDraw" && fragmentShaderName == "fpSprite") return 5;
  if (vertexShaderName == "vpDraw" && fragmentShaderName == "fpFONT") return 6;
  if (vertexShaderName == "vpDraw" && fragmentShaderName == "fpSELECT") return 7;
  if (vertexShaderName == "vpDraw" && fragmentShaderName == "fpSEAM") return 8;
  return std::nullopt;
}

void submit_shader_source(unsigned shader, int count, const char* const* strings,
                          const int* lengths, Fn_glShaderSource forward, bool& forwarded) {
  ensure_program_context();
  const std::string fullSource = gather_full_source(count, strings, lengths);
  const auto name = game::extract_shader_name(fullSource, "");

  {
    std::lock_guard lock(g_probeMutex);
    auto& record = g_shaderRecords[shader];
    record.sourcePreview = sanitized_preview_of(fullSource);
    record.sourceBytes = fullSource.size();
    record.compileLogged = false;
    record.shaderName = name;
  }

  forwarded = true;
  forward(shader, count, strings, lengths);
}

void compile_shader(unsigned shader, Fn_glCompileShader compile, bool isArb) {
  compile(shader);

  const auto& gl = game::gl::get_gl_functions();
  int shaderType = 0;
  int compileStatus = 1;
  if (gl.glGetShaderiv) {
    gl.glGetShaderiv(shader, SHADER_TYPE, &shaderType);
    gl.glGetShaderiv(shader, COMPILE_STATUS, &compileStatus);
  }

  std::string preview;
  std::size_t sourceBytes = 0;
  bool shouldLog = false;
  {
    std::lock_guard lock(g_probeMutex);
    auto& record = g_shaderRecords[shader];
    shouldLog = !record.compileLogged;
    record.compileLogged = true;
    preview = record.sourcePreview;
    sourceBytes = record.sourceBytes;
  }

  if (!shouldLog) return;

  const auto infoLog = read_shader_log(gl, shader);
  if (compileStatus == 0) {
    LOG_WARN("GL shader compile{} failed: shader={}, type={}, bytes={}, preview={}, log={}",
             isArb ? " (ARB)" : "", shader, shader_type_name(shaderType), sourceBytes,
             preview.empty() ? "<empty>" : preview, infoLog.empty() ? "<empty>" : infoLog);
  } else {
    LOG_DEBUG("GL shader compile{}: shader={} type={} status=ok bytes={} preview={}",
              isArb ? " (ARB)" : "", shader, shader_type_name(shaderType), sourceBytes,
              preview.empty() ? "<empty>" : preview);
    if (!infoLog.empty()) {
      LOG_DEBUG("GL shader compile log{}: shader={} log={}", isArb ? " (ARB)" : "", shader,
                infoLog);
    }
  }
}

static void APIENTRY detour_glShaderSource(unsigned shader, int count, const char* const* strings,
                                           const int* lengths) noexcept {
  bool forwarded = false;
  try {
    submit_shader_source(shader, count, strings, lengths, g_glShaderSourceHook.original(),
                         forwarded);
  } catch (...) {
    if (!forwarded) {
      g_glShaderSourceHook.original()(shader, count, strings, lengths);
    }
  }
}

static void APIENTRY detour_glShaderSourceARB(unsigned shader, int count,
                                              const char* const* strings,
                                              const int* lengths) noexcept {
  bool forwarded = false;
  try {
    submit_shader_source(shader, count, strings, lengths, g_glShaderSourceARBHook.original(),
                         forwarded);
  } catch (...) {
    if (!forwarded) {
      g_glShaderSourceARBHook.original()(shader, count, strings, lengths);
    }
  }
}

static void APIENTRY detour_glCompileShader(unsigned shader) noexcept {
  try {
    compile_shader(shader, g_glCompileShaderHook.original(), false);
  } catch (...) {
    // The engine compile already ran; diagnostics are optional.
  }
}

static void APIENTRY detour_glCompileShaderARB(unsigned shader) noexcept {
  try {
    compile_shader(shader, g_glCompileShaderARBHook.original(), true);
  } catch (...) {
    // The engine compile already ran; diagnostics are optional.
  }
}

// Checks g_dumpedShaders under the lock, then releases before all GL/file work,
// then re-locks to insert the record — never holds g_probeMutex across GL calls.
void maybe_dump_engine_shader(const game::gl::OpenGLFunctions& gl, unsigned shader,
                              const std::string& name) {
  if (!g_cfg.dumpEngineShaders) return;
  if (name.empty()) return;

  bool alreadyDumped = false;
  {
    std::lock_guard lock(g_probeMutex);
    alreadyDumped = g_dumpedShaders.contains(name);
  }
  if (alreadyDumped) return;

  // GL work outside the lock
  if (gl.glGetShaderiv && gl.glGetShaderSource) {
    int srcLen = 0;
    gl.glGetShaderiv(shader, SHADER_SOURCE_LENGTH, &srcLen);
    if (srcLen > 1) {
      std::string fullSrc(static_cast<std::size_t>(srcLen), '\0');
      int written = 0;
      gl.glGetShaderSource(shader, srcLen, &written, fullSrc.data());
      if (written > 0) {
        fullSrc.resize(static_cast<std::size_t>(written));
        diagnostics::dump_shader_source(g_dumpDir, name, fullSrc);
      }
    }
  }

  std::lock_guard lock(g_probeMutex);
  g_dumpedShaders.insert(name);
}

// Introspect a program without holding g_probeMutex across OpenGL calls.
void link_program_introspect(unsigned program, bool isArb, bool logDetails = true) {
  ensure_program_context();
  const auto& gl = game::gl::get_gl_functions();
  if (!gl.glGetProgramiv || !gl.glGetAttachedShaders || !gl.glGetShaderiv) return;

  int attachedShaderCount = 0;
  gl.glGetProgramiv(program, ATTACHED_SHADERS, &attachedShaderCount);
  if (attachedShaderCount <= 0) return;

  std::vector<unsigned> shaders(static_cast<std::size_t>(attachedShaderCount), 0u);
  int actualShaderCount = 0;
  gl.glGetAttachedShaders(program, attachedShaderCount, &actualShaderCount, shaders.data());

  std::string vertexShaderName;
  std::string fragmentShaderName;
  bool anyOverride = false;

  for (int i = 0; i < actualShaderCount; ++i) {
    const unsigned s = shaders[static_cast<std::size_t>(i)];
    int shaderType = 0;
    gl.glGetShaderiv(s, SHADER_TYPE, &shaderType);

    // Determine name: prefer cached record, fall back to glGetShaderSource query
    std::string nameForShader;
    {
      std::lock_guard lock(g_probeMutex);
      auto it = g_shaderRecords.find(s);
      if (it != g_shaderRecords.end()) {
        nameForShader = it->second.shaderName;
      }
    }

    const auto preview = read_shader_source_preview(gl, s);
    // If we don't have a name from the record, try reading from the GL source preview
    if (nameForShader.empty()) {
      nameForShader = game::extract_shader_name(preview, shaderType == VERTEX_SHADER ? "vp" : "fp");
    }

    // Archival: fetch full source and write to disk (engine source only,
    // not our override). Must run AFTER the name fallback — swept programs
    // have no shader records, so the record name is always empty here.
    maybe_dump_engine_shader(gl, s, nameForShader);

    if (shaderType == VERTEX_SHADER)
      vertexShaderName = nameForShader;
    else if (shaderType == FRAGMENT_SHADER)
      fragmentShaderName = nameForShader;

    // Shaders declaring uIee* uniforms (our replacement sources delivered
    // through the game's override directory) get the uniform feed.
    if (read_shader_source_prefix(gl, s).find("uIee") != std::string::npos) anyOverride = true;

    if (logDetails) {
      LOG_DEBUG("GL program attached shader{}: program={} shader={} type={} preview={}",
                isArb ? " (ARB)" : "", program, s, shader_type_name(shaderType), preview);
    }
  }

  const auto inferredSlot = infer_program_slot(vertexShaderName, fragmentShaderName);
  bool logWaterOverrideActive = false;
  bool logWaterOverrideMissing = false;
  {
    std::lock_guard lock(g_probeMutex);
    g_programRecords[program].introspected = true;
    if (anyOverride) {
      g_overriddenPrograms.try_emplace(program, std::make_shared<uniforms::Locations>());
    } else {
      g_overriddenPrograms.erase(program);
    }

    // Validate what the engine actually linked. This covers its source
    // preamble, override discovery, driver compiler, and link path.
    if (fragmentShaderName == "fpSEAM" && g_cfg.enableWaterEffect) {
      if (anyOverride && !g_waterOverrideActiveLogged) {
        g_waterOverrideActiveLogged = true;
        logWaterOverrideActive = true;
      } else if (!anyOverride && !g_waterOverrideMissingLogged) {
        g_waterOverrideMissingLogged = true;
        logWaterOverrideMissing = true;
      }
    }
  }

  if (logWaterOverrideActive) {
    LOG_INFO("Water shader override is active in engine program {}", program);
  }
  if (logWaterOverrideMissing) {
    LOG_ERROR(
        "Engine fpSEAM program {} has no Infinity Engine Enhancer uniforms; the water "
        "override was not loaded or linked. Water animation is unavailable, but tile upscaling "
        "remains active. Check override/fpSEAM.glsl and the earlier shader compile/link logs.",
        program);
  }

  if (!logDetails) return;

  if (inferredSlot) {
    LOG_DEBUG("GL program slot inference{}: program={} slot={} vertex={} fragment={}",
              isArb ? " (ARB)" : "", program, *inferredSlot, vertexShaderName, fragmentShaderName);
  } else {
    LOG_DEBUG("GL program slot inference{}: program={} slot=<unknown> vertex={} fragment={}",
              isArb ? " (ARB)" : "", program,
              vertexShaderName.empty() ? "<unknown>" : vertexShaderName,
              fragmentShaderName.empty() ? "<unknown>" : fragmentShaderName);
  }
}
void link_program(unsigned program, Fn_glLinkProgram link, bool isArb) {
  link(program);
  ensure_program_context();

  const auto& gl = game::gl::get_gl_functions();
  int linkStatus = 1;
  if (gl.glGetProgramiv) {
    gl.glGetProgramiv(program, LINK_STATUS, &linkStatus);
  }

  bool shouldLog = false;
  {
    std::lock_guard lock(g_probeMutex);
    auto& record = g_programRecords[program];
    shouldLog = !record.linkLogged;
    record.linkLogged = true;
    record.introspected = false;
    g_overriddenPrograms.erase(program);
  }

  if (shouldLog || linkStatus == 0) {
    const auto infoLog = read_program_log(gl, program);
    if (linkStatus == 0) {
      LOG_WARN("GL program link{} failed: program={}, log={}", isArb ? " (ARB)" : "", program,
               infoLog.empty() ? "<empty>" : infoLog);
    } else {
      LOG_DEBUG("GL program link{}: program={} status=ok", isArb ? " (ARB)" : "", program);
      if (!infoLog.empty()) {
        LOG_DEBUG("GL program link log{}: program={} log={}", isArb ? " (ARB)" : "", program,
                  infoLog);
      }
    }
  }

  // Program identifiers may be reused or relinked with a different shader set.
  // Rebuild classification and uniform locations after every successful link.
  if (linkStatus != 0) {
    link_program_introspect(program, isArb, shouldLog);
  }
}

static void APIENTRY detour_glLinkProgram(unsigned program) noexcept {
  try {
    link_program(program, g_glLinkProgramHook.original(), false);
  } catch (...) {
    // The engine link already ran; introspection must not affect it.
  }
}

static void APIENTRY detour_glLinkProgramARB(unsigned program) noexcept {
  try {
    link_program(program, g_glLinkProgramARBHook.original(), true);
  } catch (...) {
    // The engine link already ran; introspection must not affect it.
  }
}

// Uniform state and GL feeding live in shader_uniform_bridge.cpp. The
// probe owns only program classification and location-cache lifetime.
void feed_uniforms_to_program(unsigned program) {
  std::shared_ptr<uniforms::Locations> locations;
  {
    std::lock_guard lock(g_probeMutex);
    auto it = g_overriddenPrograms.find(program);
    if (it == g_overriddenPrograms.end()) return;
    locations = it->second;
  }
  uniforms::feed(program, *locations);
}

void use_program(unsigned program, std::uintptr_t caller, bool isArb) {
  if (program == 0) return;
  ensure_program_context();

  bool shouldInspect = false;
  bool shouldLogCaller = false;
  std::shared_ptr<uniforms::Locations> locations;
  {
    std::lock_guard lock(g_probeMutex);
    auto& record = g_programRecords[program];
    shouldInspect = !record.introspected;
    if (!shouldInspect) {
      if (const auto it = g_overriddenPrograms.find(program); it != g_overriddenPrograms.end()) {
        locations = it->second;
      }
    }
    if (g_cfg.enableVerboseLogging) {
      shouldLogCaller = record.callerLogged.insert(caller).second;
    }
  }

  if (shouldLogCaller) {
    LOG_DEBUG("GL program bind{}: program={} {}", isArb ? " (ARB)" : "", program,
              diagnostics::caller_summary(caller));
  }
  if (shouldInspect) {
    // This also discovers programs linked before probe installation. Detailed
    // caller/symbol work remains strictly opt-in through verbose logging.
    link_program_introspect(program, isArb, g_cfg.enableVerboseLogging);
    feed_uniforms_to_program(program);
  } else if (locations) {
    uniforms::feed(program, *locations);
  }
}

static void APIENTRY detour_glUseProgram(unsigned program) noexcept {
  bool forwarded = false;
  try {
    const auto caller = reinterpret_cast<std::uintptr_t>(_ReturnAddress());
    forwarded = true;
    g_glUseProgramHook.original()(program);
    use_program(program, caller, false);
  } catch (...) {
    if (!forwarded) g_glUseProgramHook.original()(program);
  }
}

static void APIENTRY detour_glUseProgramObjectARB(unsigned program) noexcept {
  bool forwarded = false;
  try {
    const auto caller = reinterpret_cast<std::uintptr_t>(_ReturnAddress());
    forwarded = true;
    g_glUseProgramObjectARBHook.original()(program);
    use_program(program, caller, true);
  } catch (...) {
    if (!forwarded) g_glUseProgramObjectARBHook.original()(program);
  }
}

void forget_shader(unsigned shader) {
  std::lock_guard lock(g_probeMutex);
  g_shaderRecords.erase(shader);
}

void forget_program(unsigned program) {
  std::lock_guard lock(g_probeMutex);
  g_programRecords.erase(program);
  g_overriddenPrograms.erase(program);
}

static void APIENTRY detour_glDeleteShader(unsigned shader) noexcept {
  bool forwarded = false;
  try {
    forwarded = true;
    g_glDeleteShaderHook.original()(shader);
    forget_shader(shader);
  } catch (...) {
    if (!forwarded) g_glDeleteShaderHook.original()(shader);
  }
}

static void APIENTRY detour_glDeleteProgram(unsigned program) noexcept {
  bool forwarded = false;
  try {
    forwarded = true;
    g_glDeleteProgramHook.original()(program);
    forget_program(program);
  } catch (...) {
    if (!forwarded) g_glDeleteProgramHook.original()(program);
  }
}

static void APIENTRY detour_glGenTextures(int count, unsigned* textures) noexcept {
  bool forwarded = false;
  try {
    LARGE_INTEGER started{};
    const bool measured =
        g_cfg.enablePerformanceLogging && QueryPerformanceCounter(&started);
    forwarded = true;
    g_glGenTexturesHook.original()(count, textures);
    if (g_cfg.enablePerformanceLogging) {
      LARGE_INTEGER ended{};
      const auto nanoseconds = measured && QueryPerformanceCounter(&ended)
                                   ? elapsed_nanoseconds(started, ended)
                                   : 0;
      core::record_gl_texture_generation(count, nanoseconds);
      core::record_pvr_scope_texture_generation(
          count > 0 ? static_cast<std::uint64_t>(count) : 0, nanoseconds);
    }
  } catch (...) {
    if (!forwarded) g_glGenTexturesHook.original()(count, textures);
  }
}

static void APIENTRY detour_glDeleteTextures(int count, const unsigned* textures) noexcept {
  bool forwarded = false;
  try {
    forget_promoted_bam_textures(count, textures);
    forwarded = true;
    g_glDeleteTexturesHook.original()(count, textures);
    if (g_cfg.enablePerformanceLogging) core::record_gl_texture_delete(count);
    game::request_texture_configuration_cache_reset();
  } catch (...) {
    if (!forwarded) g_glDeleteTexturesHook.original()(count, textures);
  }
}

std::uint64_t known_uncompressed_pixel_bytes(int width, int height, unsigned format,
                                             unsigned type) noexcept {
  if (width <= 0 || height <= 0) return 0;

  unsigned bytesPerPixel = 0;
  if (type == game::gl::UNSIGNED_BYTE) {
    switch (format) {
      case game::gl::RGBA:
      case game::gl::BGRA:
        bytesPerPixel = 4;
        break;
      case game::gl::RGB:
      case game::gl::BGR:
        bytesPerPixel = 3;
        break;
      case game::gl::LUMINANCE_ALPHA:
        bytesPerPixel = 2;
        break;
      case game::gl::RED:
      case game::gl::ALPHA:
      case game::gl::LUMINANCE:
        bytesPerPixel = 1;
        break;
      default:
        break;
    }
  } else if ((type == game::gl::UNSIGNED_INT_8_8_8_8 ||
              type == game::gl::UNSIGNED_INT_8_8_8_8_REV) &&
             (format == game::gl::RGBA || format == game::gl::BGRA)) {
    bytesPerPixel = 4;
  }
  if (bytesPerPixel == 0) return 0;
  return static_cast<std::uint64_t>(width) * static_cast<std::uint64_t>(height) * bytesPerPixel;
}

static void APIENTRY detour_glTexImage2D(unsigned target, int level, int internalFormat,
                                         int width, int height, int border, unsigned format,
                                         unsigned type, const void* data) noexcept {
  bool forwarded = false;
  try {
    BamAtlasKey reboundAtlas{};
    if (g_cfg.enableAM0205EAnimationX4Test && level == 0 &&
        current_bam_atlas_key(target, reboundAtlas)) {
      // A complete image upload invalidates any previous promotion associated
      // with this texture name. Our own promotion bypasses this detour.
      forget_promoted_bam_atlas(reboundAtlas);
    }
    const auto caller = reinterpret_cast<std::uintptr_t>(_ReturnAddress());
    am3000a_x4::ReplacementUpload replacement{};
    const bool useAM3000AReplacement =
        g_cfg.enableAM3000AFrameX4Test && am3000a_x4::try_replacement(
                                               target, level, internalFormat, width, height, border,
                                               format, type, data, replacement);
    am0700a_x4::ReplacementUpload fountainReplacement{};
    const bool useAM0700AReplacement =
        !useAM3000AReplacement && g_cfg.enableAM0700AAnimationX4Test &&
        am0700a_x4::try_replacement(target, level, internalFormat, width, height, border, format,
                                    type, data, fountainReplacement);
    am0205e_x4::ReplacementUpload orificeReplacement{};
    const bool useAM0205EReplacement =
        !useAM3000AReplacement && !useAM0700AReplacement &&
        g_cfg.enableAM0205EAnimationX4Test && am0205e_x4::try_replacement(
                                                    target, level, internalFormat, width, height,
                                                    border, format, type, data, orificeReplacement);
    const bool useReplacement =
        useAM3000AReplacement || useAM0700AReplacement || useAM0205EReplacement;
    forwarded = true;
    if (useAM3000AReplacement) {
      g_glTexImage2DHook.original()(target, level, internalFormat, replacement.width,
                                    replacement.height, border, game::gl::RGBA,
                                    game::gl::UNSIGNED_BYTE, replacement.data);
    } else if (useAM0700AReplacement) {
      g_glTexImage2DHook.original()(target, level, internalFormat, fountainReplacement.width,
                                    fountainReplacement.height, border, game::gl::RGBA,
                                    game::gl::UNSIGNED_BYTE, fountainReplacement.data);
    } else if (useAM0205EReplacement) {
      g_glTexImage2DHook.original()(target, level, internalFormat, orificeReplacement.width,
                                    orificeReplacement.height, border, game::gl::RGBA,
                                    game::gl::UNSIGNED_BYTE, orificeReplacement.data);
    } else {
      g_glTexImage2DHook.original()(target, level, internalFormat, width, height, border, format,
                                    type, data);
    }
    // The engine's uncompressed UI uploads are normally RGBA8. Record a
    // fingerprint only for the known byte-sized formats; unsupported inputs
    // still get a geometry/caller record with a zero fingerprint.
    const int loggedWidth = useAM3000AReplacement
                                ? replacement.width
                                : (useAM0700AReplacement ? fountainReplacement.width
                                                         : (useAM0205EReplacement
                                                                ? orificeReplacement.width
                                                                : width));
    const int loggedHeight = useAM3000AReplacement
                                 ? replacement.height
                                 : (useAM0700AReplacement ? fountainReplacement.height
                                                          : (useAM0205EReplacement
                                                                 ? orificeReplacement.height
                                                                 : height));
    const unsigned loggedFormat = useReplacement ? game::gl::RGBA : format;
    const unsigned loggedType = useReplacement ? game::gl::UNSIGNED_BYTE : type;
    const void* loggedData =
        useAM3000AReplacement
            ? replacement.data
            : (useAM0700AReplacement ? fountainReplacement.data
                                      : (useAM0205EReplacement ? orificeReplacement.data : data));
    if (g_cfg.enablePerformanceLogging) {
      core::record_gl_uncompressed_upload(
          known_uncompressed_pixel_bytes(loggedWidth, loggedHeight, loggedFormat, loggedType));
    }
    const int byteCount =
        (loggedType == game::gl::UNSIGNED_BYTE && loggedWidth > 0 && loggedHeight > 0 &&
         loggedWidth <= 4096 && loggedHeight <= 4096)
            ? loggedWidth * loggedHeight * (loggedFormat == game::gl::RGBA ? 4 : 1)
            : 0;
    log_bam_ui_texture_upload(false, target, level, static_cast<unsigned>(internalFormat),
                              loggedWidth, loggedHeight, byteCount, loggedData, caller);
  } catch (...) {
    if (!forwarded)
      g_glTexImage2DHook.original()(target, level, internalFormat, width, height, border, format,
                                    type, data);
  }
}

static void APIENTRY detour_glTexSubImage2D(unsigned target, int level, int xoffset, int yoffset,
                                            int width, int height, unsigned format, unsigned type,
                                            const void* data) noexcept {
  bool forwarded = false;
  try {
    if (!g_cfg.enableAM0205EAnimationX4Test) {
      forwarded = true;
      g_glTexSubImage2DHook.original()(target, level, xoffset, yoffset, width, height, format, type,
                                       data);
      if (g_cfg.enablePerformanceLogging) {
        core::record_gl_uncompressed_upload(
            known_uncompressed_pixel_bytes(width, height, format, type));
      }
      return;
    }

    BamAtlasKey atlasKey{};
    const bool hasAtlas = current_bam_atlas_key(target, atlasKey);
    const bool atlasPromoted = hasAtlas && is_promoted_bam_atlas(atlasKey);
    const auto unpackState = read_unpack_state();
    am0205e_x4::ReplacementUpload replacement{};
    const bool useAM0205EReplacement =
        hasAtlas && am0205e_x4::try_subimage_replacement(
                        target, level, width, height, format, type, data, replacement);

    if (atlasPromoted) {
      // Once promoted, every update to this shared atlas must move to x4
      // coordinates. Non-target BAM/UI rectangles are replicated nearest so
      // neighbouring cached content remains intact and correctly addressed.
      forwarded = true;
      if (level != 0 || xoffset < 0 || yoffset < 0 || width <= 0 || height <= 0) {
        if (!g_bamAtlasUnsupportedUploadLogged.exchange(true, std::memory_order_acq_rel)) {
          LOG_WARN("Skipping unsupported update to promoted BAM atlas texture {}: level={}, "
                   "offset=({}, {}), size={}x{}",
                   atlasKey.texture, level, xoffset, yoffset, width, height);
        }
        return;
      }

      if (useAM0205EReplacement) {
        set_tight_unpack();
        g_glTexSubImage2DHook.original()(
            target, level, xoffset * kBamAtlasScale, yoffset * kBamAtlasScale,
            replacement.width, replacement.height, game::gl::RGBA,
            game::gl::UNSIGNED_BYTE, replacement.data);
        if (g_cfg.enablePerformanceLogging) {
          core::record_gl_uncompressed_upload(known_uncompressed_pixel_bytes(
              replacement.width, replacement.height, game::gl::RGBA, game::gl::UNSIGNED_BYTE));
        }
        restore_unpack(unpackState);
        am0205e_x4::log_atlas_replacement(replacement.frameIndex, atlasKey.texture, xoffset,
                                          yoffset, false);
        return;
      }

      auto scaled = upscale_subimage_nearest(data, width, height, format, type, unpackState);
      if (scaled.empty()) {
        if (!g_bamAtlasUnsupportedUploadLogged.exchange(true, std::memory_order_acq_rel)) {
          LOG_WARN("Skipping unsupported pixel format in promoted BAM atlas texture {}: "
                   "format=0x{:X}, type=0x{:X}, size={}x{}",
                   atlasKey.texture, format, type, width, height);
        }
        return;
      }
      set_tight_unpack();
      g_glTexSubImage2DHook.original()(target, level, xoffset * kBamAtlasScale,
                                       yoffset * kBamAtlasScale,
                                       width * kBamAtlasScale, height * kBamAtlasScale,
                                       format, type, scaled.data());
      if (g_cfg.enablePerformanceLogging) {
        core::record_gl_uncompressed_upload(known_uncompressed_pixel_bytes(
            width * kBamAtlasScale, height * kBamAtlasScale, format, type));
      }
      restore_unpack(unpackState);
      return;
    }

    if (useAM0205EReplacement) {
      // The first exact source-frame match identifies the otherwise anonymous
      // streaming atlas. Promote its existing contents before consuming this
      // subimage so normalized UVs continue to address the same logical area.
      forwarded = true;
      if (promote_bound_bam_atlas(atlasKey, target, level, xoffset, yoffset, width, height,
                                  replacement, unpackState)) {
        if (g_cfg.enablePerformanceLogging) {
          core::record_gl_uncompressed_upload(known_uncompressed_pixel_bytes(
              replacement.width, replacement.height, game::gl::RGBA, game::gl::UNSIGNED_BYTE));
        }
        LOG_INFO("Promoted BAM streaming atlas texture {} from 1024x1024 to 4096x4096 for "
                 "AM0205E; logical UV geometry stays unchanged",
                 atlasKey.texture);
        am0205e_x4::log_atlas_replacement(replacement.frameIndex, atlasKey.texture, xoffset,
                                          yoffset, true);
        return;
      }

      if (!g_bamAtlasPromotionFailureLogged.exchange(true, std::memory_order_acq_rel)) {
        LOG_WARN("AM0205E frame matched, but the bound BAM atlas texture {} could not be "
                 "promoted safely; retaining the original x1 upload",
                 atlasKey.texture);
      }
      g_glTexSubImage2DHook.original()(target, level, xoffset, yoffset, width, height, format,
                                       type, data);
      if (g_cfg.enablePerformanceLogging) {
        core::record_gl_uncompressed_upload(
            known_uncompressed_pixel_bytes(width, height, format, type));
      }
      return;
    }

    forwarded = true;
    g_glTexSubImage2DHook.original()(target, level, xoffset, yoffset, width, height, format, type,
                                     data);
    if (g_cfg.enablePerformanceLogging) {
      core::record_gl_uncompressed_upload(
          known_uncompressed_pixel_bytes(width, height, format, type));
    }
  } catch (...) {
    if (!forwarded) {
      g_glTexSubImage2DHook.original()(target, level, xoffset, yoffset, width, height, format,
                                       type, data);
    }
  }
}

static void APIENTRY detour_glCompressedTexImage2D(unsigned target, int level,
                                                   unsigned internalFormat, int width, int height,
                                                   int border, int imageSize, const void* data) noexcept {
  bool forwarded = false;
  try {
    const auto caller = reinterpret_cast<std::uintptr_t>(_ReturnAddress());
    biglogo::ReplacementUpload replacement{};
    const bool logoReplacementEnabled = g_cfg.enableBigLogoX4Test ||
                                        g_cfg.enableMainMenuX4Test || g_cfg.enableMenuX2Test;
    const bool useReplacement =
        logoReplacementEnabled && biglogo::try_replacement(
                                      target, level, internalFormat, width, height, imageSize,
                                      data, replacement);
    LARGE_INTEGER uploadStarted{};
    const bool measured =
        g_cfg.enablePerformanceLogging && QueryPerformanceCounter(&uploadStarted);
    forwarded = true;
    if (useReplacement) {
      g_glCompressedTexImage2DHook.original()(target, level, internalFormat, replacement.width,
                                              replacement.height, border, replacement.byteCount,
                                              replacement.data);
      if (g_cfg.enablePerformanceLogging) {
        LARGE_INTEGER uploadEnded{};
        const auto nanoseconds = measured && QueryPerformanceCounter(&uploadEnded)
                                     ? elapsed_nanoseconds(uploadStarted, uploadEnded)
                                     : 0;
        core::record_gl_compressed_upload(level, internalFormat, replacement.width,
                                          replacement.height, replacement.byteCount,
                                          nanoseconds);
        core::record_pvr_scope_compressed_upload(nanoseconds);
      }
      log_bam_ui_texture_upload(true, target, level, internalFormat, replacement.width,
                                replacement.height, replacement.byteCount, replacement.data,
                                caller);
    } else {
      g_glCompressedTexImage2DHook.original()(target, level, internalFormat, width, height, border,
                                              imageSize, data);
      if (g_cfg.enablePerformanceLogging) {
        LARGE_INTEGER uploadEnded{};
        const auto nanoseconds = measured && QueryPerformanceCounter(&uploadEnded)
                                     ? elapsed_nanoseconds(uploadStarted, uploadEnded)
                                     : 0;
        core::record_gl_compressed_upload(level, internalFormat, width, height, imageSize,
                                          nanoseconds);
        core::record_pvr_scope_compressed_upload(nanoseconds);
      }
      log_bam_ui_texture_upload(true, target, level, internalFormat, width, height, imageSize,
                                data, caller);
    }
  } catch (...) {
    if (!forwarded)
      g_glCompressedTexImage2DHook.original()(target, level, internalFormat, width, height,
                                              border, imageSize, data);
  }
}

static void APIENTRY detour_glDeleteObjectARB(unsigned object) noexcept {
  bool forwarded = false;
  try {
    const auto& gl = game::gl::get_gl_functions();
    bool isProgram = gl.glIsProgram && gl.glIsProgram(object) != 0;
    if (!gl.glIsProgram) {
      std::lock_guard lock(g_probeMutex);
      isProgram = g_programRecords.contains(object);
    }

    forwarded = true;
    g_glDeleteObjectARBHook.original()(object);
    if (isProgram) {
      forget_program(object);
    } else {
      forget_shader(object);
    }
  } catch (...) {
    if (!forwarded) g_glDeleteObjectARBHook.original()(object);
  }
}

}  // anonymous namespace

ShaderRuntimeCapabilities detect_shader_runtime_capabilities() noexcept {
  const auto& gl = game::gl::get_gl_functions();
  ShaderRuntimeCapabilities caps{};
  caps.baseGlReady = gl.valid;
  caps.shaderObjectsAvailable = gl.shaderObjectsAvailable;
  caps.shaderIntrospectionAvailable = gl.shaderIntrospectionAvailable;
  caps.uniformApiAvailable = gl.uniformApiAvailable;
  caps.readyForSourcePatching =
      gl.shaderObjectsAvailable && gl.shaderIntrospectionAvailable && gl.uniformApiAvailable;
  caps.glVersion = get_gl_string(gl, game::gl::VERSION);
  caps.glslVersion = get_gl_string(gl, game::gl::SHADING_LANGUAGE_VERSION);
  caps.glVendor = get_gl_string(gl, game::gl::VENDOR);
  caps.glRenderer = get_gl_string(gl, game::gl::RENDERER);
  return caps;
}

void log_shader_runtime_capabilities() {
  const auto caps = detect_shader_runtime_capabilities();
  LOG_INFO("Shader runtime source patching: {}",
           caps.readyForSourcePatching ? "ready" : "not ready");
  LOG_DEBUG(
      "Shader runtime capabilities: base={}, objects={}, introspection={}, uniforms={}, "
      "ARB={}, GL='{}', GLSL='{}', vendor='{}', renderer='{}'",
      caps.baseGlReady, caps.shaderObjectsAvailable, caps.shaderIntrospectionAvailable,
      caps.uniformApiAvailable, game::gl::get_gl_functions().arbShaderObjectsAvailable,
      caps.glVersion, caps.glslVersion, caps.glVendor, caps.glRenderer);
}

namespace {
// Optional diagnostic probe for framebuffer ownership research.
std::set<unsigned long long> g_fboBindsLogged;

void APIENTRY detour_glBindFramebuffer(unsigned target, unsigned framebuffer) noexcept {
  bool forwarded = false;
  try {
    if (framebuffer != 0) {
      const auto key = (static_cast<unsigned long long>(target) << 32) | framebuffer;
      bool shouldLog = false;
      {
        std::lock_guard lock(g_probeMutex);
        shouldLog = g_fboBindsLogged.insert(key).second;
      }
      if (shouldLog) {
        LOG_WARN("Engine bound FBO {} on target 0x{:X}", framebuffer, target);
      }
    }
    g_glBindFramebufferHook.original()(target, framebuffer);
    forwarded = true;
  } catch (...) {
    if (!forwarded) g_glBindFramebufferHook.original()(target, framebuffer);
  }
}
}  // namespace

bool install_shader_probes(const core::EngineConfig& cfg) noexcept {
  try {
    std::lock_guard lock(g_probeMutex);
    if (g_shaderProbesInstalled) return true;

    g_cfg = cfg;

    // The water effect ships ON by default; the ini can disable it and
    // the F10 debug cycle (when enabled) still overrides at runtime.
    if (!g_uniformsInitialized) {
      uniforms::initialize(cfg.enableWaterEffect, cfg.enablePerformanceLogging);
      g_uniformsInitialized = true;
    }

    // Derive the DLL directory for the dump dir and shipped water textures
#ifdef _WIN64
    {
      wchar_t wpath[MAX_PATH]{};
      HMODULE selfModule = nullptr;
      GetModuleHandleExA(
          GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
          reinterpret_cast<LPCSTR>(&install_shader_probes), &selfModule);
      GetModuleFileNameW(selfModule ? selfModule : GetModuleHandleW(nullptr), wpath, MAX_PATH);
      const std::filesystem::path dllPath(wpath);
      const auto dllDir = dllPath.parent_path();

      g_dumpDir = dllDir / "iee-shader-dumps";

      // CPU assets were prepared during DLL initialization. Keep the GL
      // upload on this render thread while removing file I/O and decoding from
      // the first RenderTexture call.
      if (cfg.enableWaterEffect || cfg.enableDebugHotkeys) {
        (void)water::upload_water_textures();
      }
    }
#else
    {
      // macOS/Linux build path (host tests only — GL hooks never run)
      g_dumpDir = std::filesystem::current_path() / "iee-shader-dumps";
    }
#endif

    const auto& gl = game::gl::get_gl_functions();
    if (!gl.readyForSourcePatching && !gl.arbShaderObjectsAvailable &&
        !(gl.shaderObjectsAvailable && gl.shaderIntrospectionAvailable)) {
      return false;
    }

    try {
      if (gl.glShaderSource) {
        g_glShaderSourceHook.create(reinterpret_cast<void*>(gl.glShaderSource),
                                    reinterpret_cast<void*>(&detour_glShaderSource));
        g_glShaderSourceHook.queue_enable();
      }
      if (gl.glCompileShader) {
        g_glCompileShaderHook.create(reinterpret_cast<void*>(gl.glCompileShader),
                                     reinterpret_cast<void*>(&detour_glCompileShader));
        g_glCompileShaderHook.queue_enable();
      }
      if (gl.glDeleteShader) {
        g_glDeleteShaderHook.create(reinterpret_cast<void*>(gl.glDeleteShader),
                                    reinterpret_cast<void*>(&detour_glDeleteShader));
        g_glDeleteShaderHook.queue_enable();
      }
      if (gl.glLinkProgram) {
        g_glLinkProgramHook.create(reinterpret_cast<void*>(gl.glLinkProgram),
                                   reinterpret_cast<void*>(&detour_glLinkProgram));
        g_glLinkProgramHook.queue_enable();
      }
      if (gl.glUseProgram) {
        g_glUseProgramHook.create(reinterpret_cast<void*>(gl.glUseProgram),
                                  reinterpret_cast<void*>(&detour_glUseProgram));
        g_glUseProgramHook.queue_enable();
      }
      if (gl.glDeleteProgram) {
        g_glDeleteProgramHook.create(reinterpret_cast<void*>(gl.glDeleteProgram),
                                     reinterpret_cast<void*>(&detour_glDeleteProgram));
        g_glDeleteProgramHook.queue_enable();
      }
      if (cfg.enablePerformanceLogging && gl.glGenTextures) {
        g_glGenTexturesHook.create(reinterpret_cast<void*>(gl.glGenTextures),
                                   reinterpret_cast<void*>(&detour_glGenTextures));
        g_glGenTexturesHook.queue_enable();
      }
      if (gl.glDeleteTextures) {
        g_glDeleteTexturesHook.create(reinterpret_cast<void*>(gl.glDeleteTextures),
                                      reinterpret_cast<void*>(&detour_glDeleteTextures));
        g_glDeleteTexturesHook.queue_enable();
      }
      if ((cfg.enablePerformanceLogging || cfg.enableBamUiTextureProbe ||
           cfg.enableAM3000AFrameX4Test ||
           cfg.enableAM0700AAnimationX4Test || cfg.enableAM0205EAnimationX4Test) &&
          gl.glTexImage2D) {
        g_glTexImage2DHook.create(reinterpret_cast<void*>(gl.glTexImage2D),
                                  reinterpret_cast<void*>(&detour_glTexImage2D));
        g_glTexImage2DHook.queue_enable();
      }
      if ((cfg.enablePerformanceLogging || cfg.enableAM0205EAnimationX4Test) &&
          gl.glTexSubImage2D) {
        g_glTexSubImage2DHook.create(reinterpret_cast<void*>(gl.glTexSubImage2D),
                                     reinterpret_cast<void*>(&detour_glTexSubImage2D));
        g_glTexSubImage2DHook.queue_enable();
      } else if (cfg.enableAM0205EAnimationX4Test) {
        LOG_WARN("AM0205E x4 atlas test cannot start: glTexSubImage2D is unavailable");
      }
      if ((cfg.enablePerformanceLogging || cfg.enableBamUiTextureProbe ||
           cfg.enableBigLogoX4Test || cfg.enableMainMenuX4Test || cfg.enableMenuX2Test) &&
          gl.glCompressedTexImage2D) {
        g_glCompressedTexImage2DHook.create(reinterpret_cast<void*>(gl.glCompressedTexImage2D),
                                            reinterpret_cast<void*>(
                                                &detour_glCompressedTexImage2D));
        g_glCompressedTexImage2DHook.queue_enable();
      }
      // Some ICDs return the same dispatch address for promoted ARB/core
      // pairs; a second MH_CreateHook on the same target would throw and
      // roll back everything. Hook ARB entry points only when distinct.
      if (gl.glShaderSourceARB && reinterpret_cast<void*>(gl.glShaderSourceARB) !=
                                      reinterpret_cast<void*>(gl.glShaderSource)) {
        g_glShaderSourceARBHook.create(reinterpret_cast<void*>(gl.glShaderSourceARB),
                                       reinterpret_cast<void*>(&detour_glShaderSourceARB));
        g_glShaderSourceARBHook.queue_enable();
      }
      if (gl.glCompileShaderARB && reinterpret_cast<void*>(gl.glCompileShaderARB) !=
                                       reinterpret_cast<void*>(gl.glCompileShader)) {
        g_glCompileShaderARBHook.create(reinterpret_cast<void*>(gl.glCompileShaderARB),
                                        reinterpret_cast<void*>(&detour_glCompileShaderARB));
        g_glCompileShaderARBHook.queue_enable();
      }
      if (gl.glLinkProgramARB && reinterpret_cast<void*>(gl.glLinkProgramARB) !=
                                     reinterpret_cast<void*>(gl.glLinkProgram)) {
        g_glLinkProgramARBHook.create(reinterpret_cast<void*>(gl.glLinkProgramARB),
                                      reinterpret_cast<void*>(&detour_glLinkProgramARB));
        g_glLinkProgramARBHook.queue_enable();
      }
      if (gl.glUseProgramObjectARB && reinterpret_cast<void*>(gl.glUseProgramObjectARB) !=
                                          reinterpret_cast<void*>(gl.glUseProgram)) {
        g_glUseProgramObjectARBHook.create(reinterpret_cast<void*>(gl.glUseProgramObjectARB),
                                           reinterpret_cast<void*>(&detour_glUseProgramObjectARB));
        g_glUseProgramObjectARBHook.queue_enable();
      }
      if (gl.glDeleteObjectARB &&
          reinterpret_cast<void*>(gl.glDeleteObjectARB) !=
              reinterpret_cast<void*>(gl.glDeleteShader) &&
          reinterpret_cast<void*>(gl.glDeleteObjectARB) !=
              reinterpret_cast<void*>(gl.glDeleteProgram)) {
        g_glDeleteObjectARBHook.create(reinterpret_cast<void*>(gl.glDeleteObjectARB),
                                       reinterpret_cast<void*>(&detour_glDeleteObjectARB));
        g_glDeleteObjectARBHook.queue_enable();
      }
      if (cfg.enableVerboseLogging && gl.glBindFramebuffer) {
        g_glBindFramebufferHook.create(reinterpret_cast<void*>(gl.glBindFramebuffer),
                                       reinterpret_cast<void*>(&detour_glBindFramebuffer));
        g_glBindFramebufferHook.queue_enable();
      }
      const auto applyStatus = MH_ApplyQueued();
      finish_queued_probe_hooks();
      if (applyStatus != MH_OK) {
        throw std::runtime_error("MH_ApplyQueued failed for GL shader probes");
      }
    } catch (const std::exception& e) {
      (void)MH_ApplyQueued();
      finish_queued_probe_hooks();
      LOG_WARN("Failed to install GL shader probes: {}", e.what());
      remove_probe_hooks();
      return false;
    } catch (...) {
      (void)MH_ApplyQueued();
      finish_queued_probe_hooks();
      LOG_WARN("Failed to install GL shader probes with an unknown exception");
      remove_probe_hooks();
      return false;
    }

    g_shaderProbesInstalled = true;
    const auto context = game::gl::current_context();
    g_hookContext.store(context, std::memory_order_release);
    g_programContext.store(context, std::memory_order_release);
    g_sweepPending.store(true, std::memory_order_relaxed);
    LOG_INFO("Installed GL shader probes");
    return true;
  } catch (const std::exception& e) {
    remove_probe_hooks();
    LOG_ERROR("GL shader probe initialization failed: {}", e.what());
    return false;
  } catch (...) {
    remove_probe_hooks();
    LOG_ERROR("GL shader probe initialization failed with an unknown exception");
    return false;
  }
}

void uninstall_shader_probes() noexcept {
  remove_probe_hooks();
  uniforms::reset();
  try {
    std::lock_guard lock(g_probeMutex);
    g_shaderRecords.clear();
    g_programRecords.clear();
    g_overriddenPrograms.clear();
    g_dumpedShaders.clear();
    g_fboBindsLogged.clear();
    g_bamUiUploadsLogged.clear();
    g_waterOverrideActiveLogged = false;
    g_waterOverrideMissingLogged = false;
    g_programContext.store(nullptr, std::memory_order_release);
    g_hookContext.store(nullptr, std::memory_order_release);
    g_contextRefreshPending.store(false, std::memory_order_relaxed);
    g_shaderProbesInstalled = false;
    g_uniformsInitialized = false;
    g_sweepPending.store(false, std::memory_order_relaxed);
  } catch (...) {
    // Hooks are already gone; shutdown must not escape into the loader.
  }
}

void on_frame_tick(float secondsSinceStart) noexcept {
  try {
    uniforms::set_time(secondsSinceStart);

    if (g_contextRefreshPending.load(std::memory_order_acquire)) {
      if (!remove_probe_hooks()) return;
      if (!install_shader_probes(g_cfg)) return;
      g_contextRefreshPending.store(false, std::memory_order_release);
      LOG_INFO("Reinstalled GL shader probes for replacement context");
    }
    {
      std::lock_guard lock(g_probeMutex);
      if (!g_shaderProbesInstalled) return;
    }

    const bool hookContextChanged =
        game::gl::current_context() != g_hookContext.load(std::memory_order_acquire);
    const bool programContextChanged = ensure_program_context();
    if (hookContextChanged || programContextChanged) {
      {
        std::lock_guard lock(g_probeMutex);
        g_shaderProbesInstalled = false;
      }
      g_hookContext.store(nullptr, std::memory_order_release);
      g_contextRefreshPending.store(true, std::memory_order_release);
      game::request_texture_configuration_cache_reset();
      if (!remove_probe_hooks()) {
        LOG_WARN("Could not fully remove stale GL probes; retrying at the next frame boundary");
        return;
      }
      if (!install_shader_probes(g_cfg)) return;
      g_contextRefreshPending.store(false, std::memory_order_release);
      LOG_INFO("Reinstalled GL shader probes after WGL context replacement");
      g_sweepPending.store(true, std::memory_order_relaxed);
    }

    // Deferred program sweep: runs at the frame boundary (SDL swap detour)
    // instead of mid-draw inside RenderTexture — no open engine batch, clean
    // GL state for the introspection queries and dump file I/O.
    if (g_sweepPending.exchange(false, std::memory_order_relaxed)) {
      const auto& glSweep = game::gl::get_gl_functions();
      if (glSweep.glIsProgram) {
        int sweptCount = 0;
        for (unsigned id = 1; id <= 512; ++id) {
          if (glSweep.glIsProgram(id)) {
            link_program_introspect(id, false);
            ++sweptCount;
          }
        }
        LOG_DEBUG("Program sweep introspected {} pre-existing GL programs", sweptCount);
      }
    }

    // The bind-time feed misses programs the engine keeps bound across
    // frames; refresh the currently-bound program here (render thread,
    // context current — we are inside the SDL swap detour).
    const auto& gl = game::gl::get_gl_functions();
    if (gl.glGetIntegerv) {
      int currentProgram = 0;
      gl.glGetIntegerv(0x8B8D /*CURRENT_PROGRAM*/, &currentProgram);
      if (currentProgram > 0) {
        bool isOverridden = false;
        {
          std::lock_guard lock(g_probeMutex);
          isOverridden = g_overriddenPrograms.contains(static_cast<unsigned>(currentProgram));
        }
        if (isOverridden) {
          feed_uniforms_to_program(static_cast<unsigned>(currentProgram));
        }
      }
    }

    if (g_cfg.enablePerformanceLogging) {
      static std::uint32_t lastPerformanceLogTick = 0;
      const auto now = GetTickCount();
      if (lastPerformanceLogTick == 0) lastPerformanceLogTick = now;
      if (now - lastPerformanceLogTick >= 5000) {
        lastPerformanceLogTick = now;
        const auto stats = uniforms::take_performance_stats();
        static const long long frequency = [] {
          LARGE_INTEGER value{};
          return QueryPerformanceFrequency(&value) ? value.QuadPart : 0LL;
        }();
        const double ticksToMicroseconds =
            frequency > 0 ? 1'000'000.0 / static_cast<double>(frequency) : 0.0;
        const double averageMicroseconds = stats.calls > 0 ? static_cast<double>(stats.totalTicks) *
                                                                 ticksToMicroseconds /
                                                                 static_cast<double>(stats.calls)
                                                           : 0.0;
        LOG_INFO(
            "Shader uniform feed perf: calls={}, unchangedSkipped={}, textureBindPasses={}, "
            "avg={:.2f}us, max={:.2f}us over 5s",
            stats.calls, stats.skippedUnchanged, stats.textureBindPasses, averageMicroseconds,
            static_cast<double>(stats.maximumTicks) * ticksToMicroseconds);
      }
    }

    if (!g_cfg.enableDebugHotkeys) {
      return;
    }

    // F10: cycle the visual effect gate OFF(0) -> WATER(1) -> ALIGN(2) -> OFF.
    static bool f10WasDown = false;
    const bool f10Down = (GetAsyncKeyState(VK_F10) & 0x8000) != 0;
    if (f10Down && !f10WasDown) {
      const float next = uniforms::cycle_debug_effect();

      // Snapshot the world-transform inputs so screenshots pair with the
      // exact values the shader saw (render thread; context current).
      int vp[4] = {0, 0, 0, 0};
      const auto& glState = game::gl::get_gl_functions();
      if (glState.glGetIntegerv) {
        glState.glGetIntegerv(0x0BA2 /*GL_VIEWPORT*/, vp);
      }
      const auto state = uniforms::snapshot();
      LOG_INFO(
          "Hotkey F10: override effect value {} (scroll=({}, {}), viewWorld={}x{}, viewport={}x{} "
          "at ({}, {}), world={}x{}, feeds={})",
          next, state.scrollX, state.scrollY, state.viewWorldWidth, state.viewWorldHeight, vp[2],
          vp[3], vp[0], vp[1], state.worldWidth, state.worldHeight, state.feedCount);
    }
    f10WasDown = f10Down;
  } catch (...) {
    // Frame presentation and the original swap must never depend on probes.
  }
}

void set_override_effect_enabled(bool enabled) noexcept { uniforms::set_effect_enabled(enabled); }

bool override_effect_enabled() noexcept { return uniforms::effect_enabled(); }

void set_area_world_size(float widthPx, float heightPx) noexcept {
  uniforms::set_world_size(widthPx, heightPx);
}

void set_area_water_tint(float r, float g, float b) noexcept { uniforms::set_water_tint(r, g, b); }

void set_area_view(float scrollX, float scrollY, float viewWorldW, float viewWorldH) noexcept {
  uniforms::set_view(scrollX, scrollY, viewWorldW, viewWorldH);
}

}  // namespace iee::probe
