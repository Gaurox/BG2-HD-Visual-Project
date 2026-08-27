#include "am0205e_animation_x4_test.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <fstream>
#include <mutex>
#include <utility>
#include <vector>

#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/opengl_types.h"

namespace iee::am0205e_x4 {
namespace {
constexpr int kSourceWidth = 165;
constexpr int kSourceHeight = 130;
constexpr int kScale = 4;
constexpr int kReplacementWidth = kSourceWidth * kScale;
constexpr int kReplacementHeight = kSourceHeight * kScale;
constexpr int kReplacementBytes = kReplacementWidth * kReplacementHeight * 4;
constexpr int kSourceBytes = kSourceWidth * kSourceHeight * 4;

struct Frame {
  const char* assetName;
  // RGBA/BGRA, with both original and cleared transparent RGB. The identity
  // remains exact: only one of AM0205E's extracted x1 frame byte streams can
  // select a given x4 replacement.
  std::array<std::uint64_t, 4> originalFingerprints;
  std::vector<std::byte> replacement;
};

std::array<Frame, 9> g_frames{{
    {"AM0205E-frame000-x4.rgba",
     {0x27575318642013F7ull, 0x0071E0B4BAEE2F05ull, 0xBC6703329075C54Bull,
      0x1AFAF7300AFDA20Dull}, {}},
    {"AM0205E-frame001-x4.rgba",
     {0x8A9055C03F5FD4FFull, 0xBF1DD8FA299AA171ull, 0x9BB1D2E2DBE04DE3ull,
      0x50FDC9E0E900B429ull}, {}},
    {"AM0205E-frame002-x4.rgba",
     {0xE81074C43D35C4CAull, 0x6EFB8928FF6B66D4ull, 0x8F27CF56A588891Eull,
      0xEB83C38FA79FADCCull}, {}},
    {"AM0205E-frame003-x4.rgba",
     {0x0777662FFC7FA9FAull, 0x7813B3647ECCF640ull, 0x6DCD29091FE4FC16ull,
      0x9E2AF4CA7379B0C0ull}, {}},
    {"AM0205E-frame004-x4.rgba",
     {0xF2917AD050D3550Bull, 0xB27F63A13F08544Dull, 0xE7D74760A3A9B8E3ull,
      0x4BA605C10E72A219ull}, {}},
    {"AM0205E-frame005-x4.rgba",
     {0x46D5F0542739FFC3ull, 0xC9A7B73C7ADDEBD3ull, 0xC3F5A631D7E2E8A7ull,
      0x0284ED379A9DE427ull}, {}},
    {"AM0205E-frame006-x4.rgba",
     {0x9EBE8744B4D0881Full, 0x7781302CECF59D5Full, 0xD92CA50E97C96A8Bull,
      0xA8816A83FBBF476Bull}, {}},
    {"AM0205E-frame007-x4.rgba",
     {0x2C7ABF293B6EF95Full, 0xEBE6E8F9D660CE8Full, 0xD8ADD71E2F2C27DBull,
      0xCF62220D402ADFCBull}, {}},
    {"AM0205E-frame008-x4.rgba",
     {0x06F4F63427ADEE7Eull, 0x59201782496C3696ull, 0x7AF6FF442595A012ull,
      0x0BCFFB8C189B82DAull}, {}},
}};

std::mutex g_mutex;
std::atomic<bool> g_ready{false};
std::array<std::atomic<bool>, 9> g_loggedFrames{};
std::atomic<bool> g_unmatchedCandidateLogged{false};
std::array<int, 9> g_engineTextureIds{};
#ifdef _WIN32
HGLRC g_engineTextureContext{};
#endif
std::array<bool, 9> g_compositionLogged{};
bool g_creationFailureLogged = false;

std::uint64_t fnv1a64(const void* data, int byteCount) noexcept {
  if (!data || byteCount != kSourceBytes) return 0;
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

void reset_logs() noexcept {
  for (auto& logged : g_loggedFrames) logged.store(false, std::memory_order_release);
  g_unmatchedCandidateLogged.store(false, std::memory_order_release);
  g_compositionLogged.fill(false);
  g_creationFailureLogged = false;
}

int logical_texture_id(const EngineTextureApi& api) noexcept {
  if (!api.glTextureState) return 0;
  std::uint32_t state = 0;
  if (!core::safe_read(api.glTextureState, state)) return 0;
  return static_cast<int>((state >> 21u) & 0x1FFu);
}

void delete_textures_locked(const EngineTextureApi& api) noexcept {
  if (api.DrawDeleteTexture) {
    for (const int textureId : g_engineTextureIds) {
      if (textureId > 0) api.DrawDeleteTexture(textureId);
    }
  }
  g_engineTextureIds.fill(0);
}

bool create_engine_textures_locked(const EngineTextureApi& api, int previousTextureId) noexcept {
  auto& gl = game::gl::get_gl_functions();
  if ((!gl.valid && !gl.initialize()) || !gl.glGetIntegerv || !gl.glTexImage2D ||
      !gl.glTexParameteri || !gl.glPixelStorei || !gl.glGetTexLevelParameteriv ||
      !gl.glGetError) {
    return false;
  }

  int unpackAlignment = 4;
  int unpackRowLength = 0;
  int unpackSkipRows = 0;
  int unpackSkipPixels = 0;
  int unpackBuffer = 0;
  gl.glGetIntegerv(game::gl::UNPACK_ALIGNMENT, &unpackAlignment);
  gl.glGetIntegerv(game::gl::UNPACK_ROW_LENGTH, &unpackRowLength);
  gl.glGetIntegerv(game::gl::UNPACK_SKIP_ROWS, &unpackSkipRows);
  gl.glGetIntegerv(game::gl::UNPACK_SKIP_PIXELS, &unpackSkipPixels);
  gl.glGetIntegerv(game::gl::PIXEL_UNPACK_BUFFER_BINDING, &unpackBuffer);
  game::gl::discard_errors();
  if (unpackBuffer != 0) {
    LOG_WARN("AM0205E x4 composition textures postponed: a pixel-unpack buffer is bound");
    return false;
  }

  const auto restorePixelStore = [&] {
    gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, unpackAlignment);
    gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH, unpackRowLength);
    gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS, unpackSkipRows);
    gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS, unpackSkipPixels);
  };

  gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, 1);
  gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH, 0);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS, 0);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS, 0);

  bool success = true;
  for (std::size_t index = 0; index < g_frames.size(); ++index) {
    const auto& pixels = g_frames[index].replacement;
    if (static_cast<int>(pixels.size()) != kReplacementBytes) {
      success = false;
      break;
    }

    // LINEAR is recorded in the engine texture descriptor. TexImage stores the
    // logical 165x130 dimensions there and allocates matching temporary GL
    // storage; the raw GL call immediately below changes only physical storage.
    const int textureId = api.DrawGenTexture(static_cast<int>(game::gl::LINEAR), 0, 0, 0);
    if (textureId <= 0) {
      success = false;
      break;
    }
    g_engineTextureIds[index] = textureId;
    api.DrawBindTexture(textureId);
    api.TexImage(kSourceWidth, kSourceHeight, nullptr, 0);

    int boundTexture = 0;
    gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &boundTexture);
    if (boundTexture <= 0 || gl.glGetError() != game::gl::GL_NO_ERROR) {
      success = false;
      break;
    }

    gl.glTexImage2D(game::gl::TEXTURE_2D, 0, static_cast<int>(game::gl::RGBA8),
                    kReplacementWidth, kReplacementHeight, 0, game::gl::RGBA,
                    game::gl::UNSIGNED_BYTE, pixels.data());
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_S,
                       static_cast<int>(game::gl::CLAMP_TO_EDGE));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_T,
                       static_cast<int>(game::gl::CLAMP_TO_EDGE));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MIN_FILTER,
                       static_cast<int>(game::gl::LINEAR));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER,
                       static_cast<int>(game::gl::LINEAR));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAX_LEVEL, 0);

    int physicalWidth = 0;
    int physicalHeight = 0;
    gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_WIDTH,
                                &physicalWidth);
    gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_HEIGHT,
                                &physicalHeight);
    if (physicalWidth != kReplacementWidth || physicalHeight != kReplacementHeight ||
        gl.glGetError() != game::gl::GL_NO_ERROR) {
      success = false;
      break;
    }
  }

  restorePixelStore();
  api.DrawBindTexture(previousTextureId);
  if (!success) {
    delete_textures_locked(api);
    api.DrawBindTexture(previousTextureId);
    return false;
  }

  LOG_INFO(
      "Created AM0205E composition textures: engine logical size 165x130, physical GL size "
      "660x520 (9 frames)");
  return true;
}
}  // namespace

bool prepare(const std::filesystem::path& assetsDirectory) noexcept {
  try {
    std::array<std::vector<std::byte>, 9> loaded;
    for (std::size_t index = 0; index < g_frames.size(); ++index) {
      const auto assetPath = assetsDirectory / g_frames[index].assetName;
      std::ifstream file(assetPath, std::ios::binary | std::ios::ate);
      if (!file) {
        LOG_WARN("AM0205E x4 test skipped: missing {}", assetPath.string());
        return false;
      }
      if (file.tellg() != kReplacementBytes) {
        LOG_WARN("AM0205E x4 test skipped: {} has {} bytes (expected {})", assetPath.string(),
                 static_cast<long long>(file.tellg()), kReplacementBytes);
        return false;
      }
      file.seekg(0);
      loaded[index].resize(kReplacementBytes);
      if (!file.read(reinterpret_cast<char*>(loaded[index].data()), loaded[index].size())) {
        LOG_WARN("AM0205E x4 test skipped: could not read {}", assetPath.string());
        return false;
      }
    }

    std::lock_guard lock(g_mutex);
    g_ready.store(false, std::memory_order_release);
    for (std::size_t index = 0; index < g_frames.size(); ++index) {
      g_frames[index].replacement = std::move(loaded[index]);
    }
    reset_logs();
    g_ready.store(true, std::memory_order_release);
    LOG_INFO("Prepared reversible AM0205E animation x4 textures (9 frames): {}",
             assetsDirectory.string());
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("AM0205E x4 test disabled: {}", error.what());
    return false;
  } catch (...) {
    LOG_WARN("AM0205E x4 test disabled by an unknown loading error");
    return false;
  }
}

void release() noexcept {
  std::lock_guard lock(g_mutex);
  g_ready.store(false, std::memory_order_release);
  // Hook teardown happens before release(). The process / engine owns GL
  // context destruction, so shutdown merely forgets ids; deleting them from a
  // non-render thread would be unsafe.
  g_engineTextureIds.fill(0);
#ifdef _WIN32
  g_engineTextureContext = nullptr;
#endif
  for (auto& frame : g_frames) {
    frame.replacement.clear();
    frame.replacement.shrink_to_fit();
  }
  reset_logs();
}

bool ready() noexcept { return g_ready.load(std::memory_order_acquire); }

bool bind_frame_texture(int frameIndex, const EngineTextureApi& api,
                        int& previousTextureId) noexcept {
  previousTextureId = 0;
  if (frameIndex < 0 || frameIndex >= static_cast<int>(g_frames.size()) ||
      !g_ready.load(std::memory_order_acquire) || !api.DrawGenTexture ||
      !api.DrawBindTexture || !api.DrawDeleteTexture || !api.TexImage ||
      !api.DrawGetRenderer || !api.glTextureState) {
    return false;
  }

  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;
    // Renderer 1 is the legacy DX backend. This prototype deliberately uses
    // physical OpenGL storage and must never be armed on that path.
    if (api.DrawGetRenderer() == 1) {
      if (!g_creationFailureLogged) {
        g_creationFailureLogged = true;
        LOG_WARN("AM0205E x4 composition hook skipped: active renderer is not OpenGL");
      }
      return false;
    }

#ifdef _WIN32
    const auto context = game::gl::current_context();
    if (!context) return false;
    if (g_engineTextureContext != context) {
      g_engineTextureIds.fill(0);
      g_engineTextureContext = context;
      g_compositionLogged.fill(false);
    }
#endif

    previousTextureId = logical_texture_id(api);
    if (previousTextureId <= 0) return false;
    if (g_engineTextureIds[0] <= 0 &&
        !create_engine_textures_locked(api, previousTextureId)) {
      if (!g_creationFailureLogged) {
        g_creationFailureLogged = true;
        LOG_WARN("AM0205E x4 composition textures could not be created; using original BAM");
      }
      return false;
    }

    const int replacementTexture = g_engineTextureIds[static_cast<std::size_t>(frameIndex)];
    if (replacementTexture <= 0) return false;
    api.DrawBindTexture(replacementTexture);
    if (!g_compositionLogged[static_cast<std::size_t>(frameIndex)]) {
      g_compositionLogged[static_cast<std::size_t>(frameIndex)] = true;
      LOG_INFO("Composing AM0205E frame {:03} from its dedicated x4 physical texture",
               frameIndex);
    }
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("AM0205E x4 composition failed: {}", error.what());
  } catch (...) {
    LOG_WARN("AM0205E x4 composition failed with an unknown error");
  }
  return false;
}

void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept {
  if (api.DrawBindTexture && previousTextureId > 0) api.DrawBindTexture(previousTextureId);
}

void forget_engine_textures() noexcept {
  std::lock_guard lock(g_mutex);
  g_engineTextureIds.fill(0);
#ifdef _WIN32
  g_engineTextureContext = nullptr;
#endif
  g_compositionLogged.fill(false);
}

bool try_replacement(unsigned target, int level, int internalFormat, int width, int height,
                     int border, unsigned format, unsigned type, const void* originalData,
                     ReplacementUpload& out) noexcept {
  // BG2EE uploads area-animation pixels either as bytes (0x1401) or as its
  // native BGRA/RGBA packed 8:8:8:8-reversed representation (0x8367). Both
  // have exactly four bytes per pixel and are fingerprinted before use.
  if (target != game::gl::TEXTURE_2D || level != 0 || border != 0 || width != kSourceWidth ||
      height != kSourceHeight || !originalData ||
      (type != game::gl::UNSIGNED_BYTE && type != game::gl::UNSIGNED_INT_8_8_8_8_REV) ||
      (format != game::gl::RGBA && format != game::gl::BGRA) ||
      (internalFormat != static_cast<int>(game::gl::RGBA) &&
       internalFormat != static_cast<int>(game::gl::RGBA8))) {
    return false;
  }

  const auto fingerprint = fnv1a64(originalData, kSourceBytes);
  std::lock_guard lock(g_mutex);
  if (!g_ready.load(std::memory_order_acquire)) return false;
  for (std::size_t index = 0; index < g_frames.size(); ++index) {
    const auto& frame = g_frames[index];
    bool matches = false;
    for (const auto candidate : frame.originalFingerprints) matches = matches || fingerprint == candidate;
    if (!matches) continue;
    if (static_cast<int>(frame.replacement.size()) != kReplacementBytes) return false;
    out = {kReplacementWidth, kReplacementHeight, frame.replacement.data(),
           static_cast<int>(index)};
    if (!g_loggedFrames[index].exchange(true, std::memory_order_acq_rel)) {
      LOG_INFO("Replacing AM0205E frame {:03} 165x130 upload with x4; draw geometry stays native",
               index);
    }
    return true;
  }
  if (!g_unmatchedCandidateLogged.exchange(true, std::memory_order_acq_rel)) {
    LOG_WARN("AM0205E x4 candidate 165x130 did not match the extracted source fingerprints: "
             "fnv1a64=0x{:016X}",
             fingerprint);
  }
  return false;
}

bool try_subimage_replacement(unsigned target, int level, int width, int height,
                              unsigned format, unsigned type, const void* originalData,
                              ReplacementUpload& out) noexcept {
  if (target != game::gl::TEXTURE_2D || level != 0 || width != kSourceWidth ||
      height != kSourceHeight || !originalData ||
      (type != game::gl::UNSIGNED_BYTE && type != game::gl::UNSIGNED_INT_8_8_8_8_REV) ||
      (format != game::gl::RGBA && format != game::gl::BGRA)) {
    return false;
  }

  const auto fingerprint = fnv1a64(originalData, kSourceBytes);
  std::lock_guard lock(g_mutex);
  if (!g_ready.load(std::memory_order_acquire)) return false;
  for (std::size_t index = 0; index < g_frames.size(); ++index) {
    const auto& frame = g_frames[index];
    bool matches = false;
    for (const auto candidate : frame.originalFingerprints) matches = matches || fingerprint == candidate;
    if (!matches) continue;
    if (static_cast<int>(frame.replacement.size()) != kReplacementBytes) return false;
    out = {kReplacementWidth, kReplacementHeight, frame.replacement.data(),
           static_cast<int>(index)};
    return true;
  }
  if (!g_unmatchedCandidateLogged.exchange(true, std::memory_order_acq_rel)) {
    LOG_WARN("AM0205E x4 subimage candidate 165x130 did not match the extracted source "
             "fingerprints: fnv1a64=0x{:016X}",
             fingerprint);
  }
  return false;
}

void log_atlas_replacement(int frameIndex, unsigned texture, int xoffset, int yoffset,
                           bool atlasPromoted) noexcept {
  if (frameIndex < 0 || frameIndex >= static_cast<int>(g_loggedFrames.size())) return;
  if (!g_loggedFrames[static_cast<std::size_t>(frameIndex)].exchange(
          true, std::memory_order_acq_rel)) {
    LOG_INFO(
        "Replacing AM0205E frame {:03} in promoted BAM atlas texture {} at ({}, {}); "
        "draw geometry stays native{}",
        frameIndex, texture, xoffset, yoffset, atlasPromoted ? " (atlas promoted now)" : "");
  }
}
}  // namespace iee::am0205e_x4
