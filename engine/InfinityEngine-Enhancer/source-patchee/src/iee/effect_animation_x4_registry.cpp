#include "iee/effect_animation_x4_registry.h"

#include <algorithm>
#include <atomic>
#include <cctype>
#include <cstdio>
#include <cstring>
#include <exception>
#include <fstream>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/opengl_types.h"

namespace iee::effect_animation_x4 {
namespace {
constexpr std::array<char, 8> kRegistryMagic{{'I', 'E', 'E', 'E', 'F', 'X', '4', '\0'}};
constexpr std::uint32_t kRegistryVersion = 1;
constexpr std::uint32_t kTimelineRegistryVersion = 2;
constexpr std::uint32_t kScale = 4;
constexpr std::uint32_t kMaxResources = 512;
constexpr std::uint32_t kMaxFramesPerResource = 4096;
constexpr std::uint32_t kMaxCyclesPerResource = 256;
constexpr std::uint32_t kMaxCycleSlots = 65536;
constexpr std::uint64_t kMaxRawBytes = 128ull * 1024ull * 1024ull;

struct Frame {
  int logicalWidth{};
  int logicalHeight{};
  std::vector<std::byte> replacement;
};

struct Resource {
  std::array<char, 8> resref{};
  std::string displayName;
  std::vector<Frame> frames;
  std::vector<std::vector<std::uint32_t>> cycles;
  struct Timeline {
    bool enabled{};
    std::uint32_t nativeFpsNumerator{};
    std::uint32_t nativeFpsDenominator{};
    std::uint32_t targetFpsNumerator{};
    std::uint32_t targetFpsDenominator{};
    std::uint32_t phaseCount{};
    std::vector<std::vector<std::uint32_t>> framesByCycle;
  } timeline;
};

struct TextureCacheEntry {
  FrameHandle handle{};
  int textureId{};
};

class BinaryReader {
 public:
  explicit BinaryReader(const std::vector<std::byte>& bytes) : bytes_(bytes) {}

  template <class T>
  bool read(T& out) noexcept {
    static_assert(std::is_trivially_copyable_v<T>);
    if (offset_ > bytes_.size() || sizeof(T) > bytes_.size() - offset_) return false;
    std::memcpy(&out, bytes_.data() + offset_, sizeof(T));
    offset_ += sizeof(T);
    return true;
  }

  template <class T, std::size_t N>
  bool read(std::array<T, N>& out) noexcept {
    static_assert(std::is_trivially_copyable_v<T>);
    constexpr auto byteCount = sizeof(T) * N;
    if (offset_ > bytes_.size() || byteCount > bytes_.size() - offset_) return false;
    std::memcpy(out.data(), bytes_.data() + offset_, byteCount);
    offset_ += byteCount;
    return true;
  }

  [[nodiscard]] bool at_end() const noexcept { return offset_ == bytes_.size(); }

 private:
  const std::vector<std::byte>& bytes_;
  std::size_t offset_{};
};

std::mutex g_mutex;
std::atomic<bool> g_ready{false};
std::vector<Resource> g_resources;
std::vector<TextureCacheEntry> g_textureCache;
#ifdef _WIN32
HGLRC g_textureContext{};
#endif
bool g_rendererFailureLogged = false;
bool g_uploadFailureLogged = false;

std::vector<std::byte> read_file(const std::filesystem::path& path,
                                 std::uint64_t expectedBytes = 0) {
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file) throw std::runtime_error("missing asset: " + path.string());
  const auto end = file.tellg();
  if (end < 0) throw std::runtime_error("cannot size asset: " + path.string());
  const auto byteCount = static_cast<std::uint64_t>(end);
  if (byteCount > kMaxRawBytes || (expectedBytes != 0 && byteCount != expectedBytes)) {
    throw std::runtime_error("invalid asset size: " + path.string());
  }
  file.seekg(0);
  std::vector<std::byte> bytes(static_cast<std::size_t>(byteCount));
  if (!bytes.empty() &&
      !file.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()))) {
    throw std::runtime_error("cannot read asset: " + path.string());
  }
  return bytes;
}

std::string resref_name(const std::array<char, 8>& resref) {
  const auto end = std::find(resref.begin(), resref.end(), '\0');
  return std::string(resref.begin(), end);
}

bool valid_resref(const std::array<char, 8>& resref) noexcept {
  bool sawCharacter = false;
  bool terminated = false;
  for (const char value : resref) {
    if (value == '\0') {
      terminated = true;
      continue;
    }
    if (terminated || !(std::isalnum(static_cast<unsigned char>(value)) != 0 || value == '_')) {
      return false;
    }
    sawCharacter = true;
  }
  return sawCharacter;
}

std::string frame_asset_name(const std::array<char, 8>& resref, std::size_t frameIndex) {
  const auto name = resref_name(resref);
  char buffer[64]{};
  const auto written = std::snprintf(buffer, sizeof(buffer), "EFX4-%s-frame%03zu.rgba",
                                     name.c_str(), frameIndex);
  if (written <= 0 || static_cast<std::size_t>(written) >= sizeof(buffer)) {
    throw std::runtime_error("runtime frame asset name is too long");
  }
  return buffer;
}

int logical_texture_id(const EngineTextureApi& api) noexcept {
  if (!api.glTextureState) return 0;
  std::uint32_t state = 0;
  if (!core::safe_read(api.glTextureState, state)) return 0;
  return static_cast<int>((state >> 21u) & 0x1FFu);
}

void invalidate_texture_cache_locked() noexcept {
  // Texture names are valid only for their original WGL context. Context loss
  // already releases them in the driver; retaining their integers could bind an
  // unrelated texture in the replacement context.
  g_textureCache.clear();
}

bool upload_frame_locked(const Frame& frame, int textureId, const EngineTextureApi& api,
                         int previousTextureId) noexcept {
  auto& gl = game::gl::get_gl_functions();
  if ((!gl.valid && !gl.initialize()) || !gl.glGetIntegerv || !gl.glTexImage2D ||
      !gl.glTexParameteri || !gl.glPixelStorei || !gl.glGetTexLevelParameteriv ||
      !gl.glGetError) {
    return false;
  }
  const auto physicalWidth = frame.logicalWidth * static_cast<int>(kScale);
  const auto physicalHeight = frame.logicalHeight * static_cast<int>(kScale);
  const auto expectedBytes = static_cast<std::uint64_t>(physicalWidth) *
                             static_cast<std::uint64_t>(physicalHeight) * 4ull;
  if (physicalWidth <= 0 || physicalHeight <= 0 || expectedBytes != frame.replacement.size()) {
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
  if (unpackBuffer != 0) return false;

  const auto restore_state = [&] {
    gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, unpackAlignment);
    gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH, unpackRowLength);
    gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS, unpackSkipRows);
    gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS, unpackSkipPixels);
    api.DrawBindTexture(previousTextureId);
  };
  gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, 1);
  gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH, 0);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS, 0);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS, 0);

  api.DrawBindTexture(textureId);
  api.TexImage(frame.logicalWidth, frame.logicalHeight, nullptr, 0);
  int boundTexture = 0;
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &boundTexture);
  if (boundTexture <= 0 || gl.glGetError() != game::gl::GL_NO_ERROR) {
    restore_state();
    return false;
  }
  gl.glTexImage2D(game::gl::TEXTURE_2D, 0, static_cast<int>(game::gl::RGBA8), physicalWidth,
                  physicalHeight, 0, game::gl::RGBA, game::gl::UNSIGNED_BYTE,
                  frame.replacement.data());
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_S,
                     static_cast<int>(game::gl::CLAMP_TO_EDGE));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_T,
                     static_cast<int>(game::gl::CLAMP_TO_EDGE));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MIN_FILTER,
                     static_cast<int>(game::gl::LINEAR));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER,
                     static_cast<int>(game::gl::LINEAR));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAX_LEVEL, 0);
  int actualWidth = 0;
  int actualHeight = 0;
  gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_WIDTH, &actualWidth);
  gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_HEIGHT, &actualHeight);
  const bool success = actualWidth == physicalWidth && actualHeight == physicalHeight &&
                       gl.glGetError() == game::gl::GL_NO_ERROR;
  restore_state();
  return success;
}

bool bind_frame_texture_locked(FrameHandle handle, const EngineTextureApi& api,
                               int previousTextureId) noexcept {
  if (handle.resourceIndex >= g_resources.size() ||
      handle.frameIndex >= g_resources[handle.resourceIndex].frames.size()) {
    return false;
  }
  const auto existing = std::find_if(
      g_textureCache.begin(), g_textureCache.end(),
      [&](const TextureCacheEntry& entry) { return entry.handle == handle; });
  if (existing != g_textureCache.end()) {
    api.DrawBindTexture(existing->textureId);
    return true;
  }

  const int textureId = api.DrawGenTexture(static_cast<int>(game::gl::LINEAR), 0, 0, 0);
  if (textureId <= 0) return false;
  const auto& frame = g_resources[handle.resourceIndex].frames[handle.frameIndex];
  if (!upload_frame_locked(frame, textureId, api, previousTextureId)) {
    api.DrawDeleteTexture(textureId);
    api.DrawBindTexture(previousTextureId);
    return false;
  }
  g_textureCache.push_back({.handle = handle, .textureId = textureId});
  api.DrawBindTexture(textureId);
  LOG_DEBUG("Effect animation x4 texture {}: {} frame {:03}, logical {}x{}, physical {}x{}",
            textureId, g_resources[handle.resourceIndex].displayName, handle.frameIndex,
            frame.logicalWidth, frame.logicalHeight, frame.logicalWidth * kScale,
            frame.logicalHeight * kScale);
  return true;
}
}  // namespace

bool prepare(const std::filesystem::path& assetsDirectory) noexcept {
  g_ready.store(false, std::memory_order_release);
  try {
    const auto payload = read_file(assetsDirectory / "EffectAnimations-X4.registry");
    BinaryReader reader(payload);
    std::array<char, 8> magic{};
    std::uint32_t version = 0;
    std::uint32_t scale = 0;
    std::uint32_t resourceCount = 0;
    std::uint32_t reserved = 0;
    if (!reader.read(magic) || !reader.read(version) || !reader.read(scale) ||
        !reader.read(resourceCount) || !reader.read(reserved) || magic != kRegistryMagic ||
        (version != kRegistryVersion && version != kTimelineRegistryVersion) || scale != kScale ||
        reserved != 0 || resourceCount == 0 ||
        resourceCount > kMaxResources) {
      throw std::runtime_error("invalid EffectAnimations-X4.registry header");
    }

    std::vector<Resource> loaded;
    loaded.reserve(resourceCount);
    std::uint64_t totalRawBytes = 0;
    for (std::uint32_t resourceIndex = 0; resourceIndex < resourceCount; ++resourceIndex) {
      Resource resource{};
      std::uint32_t frameCount = 0;
      std::uint32_t cycleCount = 0;
      if (!reader.read(resource.resref) || !reader.read(frameCount) || !reader.read(cycleCount) ||
          !valid_resref(resource.resref) || frameCount == 0 || frameCount > kMaxFramesPerResource ||
          cycleCount == 0 || cycleCount > kMaxCyclesPerResource) {
        throw std::runtime_error("invalid effect resource descriptor");
      }
      if (std::any_of(loaded.begin(), loaded.end(), [&](const Resource& existing) {
            return existing.resref == resource.resref;
          })) {
        throw std::runtime_error("duplicate effect resource resref");
      }
      resource.displayName = resref_name(resource.resref);
      resource.frames.reserve(frameCount);
      for (std::uint32_t frameIndex = 0; frameIndex < frameCount; ++frameIndex) {
        std::uint32_t width = 0;
        std::uint32_t height = 0;
        if (!reader.read(width) || !reader.read(height) || width == 0 || height == 0 ||
            width > 2048 || height > 2048) {
          throw std::runtime_error("invalid effect frame dimensions");
        }
        const auto physicalBytes = static_cast<std::uint64_t>(width) * kScale *
                                  static_cast<std::uint64_t>(height) * kScale * 4ull;
        if (physicalBytes > kMaxRawBytes || totalRawBytes > kMaxRawBytes - physicalBytes) {
          throw std::runtime_error("effect runtime pack exceeds raw-byte limit");
        }
        totalRawBytes += physicalBytes;
        resource.frames.push_back(
            {.logicalWidth = static_cast<int>(width), .logicalHeight = static_cast<int>(height)});
      }
      resource.cycles.reserve(cycleCount);
      for (std::uint32_t cycleIndex = 0; cycleIndex < cycleCount; ++cycleIndex) {
        std::uint32_t slotCount = 0;
        if (!reader.read(slotCount) || slotCount == 0 || slotCount > kMaxCycleSlots) {
          throw std::runtime_error("invalid effect BAM cycle");
        }
        std::vector<std::uint32_t> slots(slotCount);
        for (std::uint32_t& slot : slots) {
          if (!reader.read(slot) || slot >= frameCount) {
            throw std::runtime_error("invalid effect BAM cycle slot");
          }
        }
        resource.cycles.push_back(std::move(slots));
      }
      if (version == kTimelineRegistryVersion) {
        auto& timeline = resource.timeline;
        if (!reader.read(timeline.nativeFpsNumerator) ||
            !reader.read(timeline.nativeFpsDenominator) ||
            !reader.read(timeline.targetFpsNumerator) ||
            !reader.read(timeline.targetFpsDenominator) || !reader.read(timeline.phaseCount) ||
            timeline.nativeFpsNumerator == 0 || timeline.nativeFpsDenominator == 0 ||
            timeline.targetFpsNumerator == 0 || timeline.targetFpsDenominator == 0 ||
            static_cast<std::uint64_t>(timeline.targetFpsNumerator) *
                    timeline.nativeFpsDenominator <=
                static_cast<std::uint64_t>(timeline.nativeFpsNumerator) *
                    timeline.targetFpsDenominator ||
            timeline.phaseCount == 0 || timeline.phaseCount > kMaxCycleSlots) {
          throw std::runtime_error("invalid effect timeline descriptor");
        }
        timeline.framesByCycle.reserve(cycleCount);
        for (std::uint32_t cycleIndex = 0; cycleIndex < cycleCount; ++cycleIndex) {
          std::vector<std::uint32_t> phases(timeline.phaseCount);
          for (std::uint32_t& frame : phases) {
            if (!reader.read(frame) || frame >= frameCount) {
              throw std::runtime_error("invalid effect timeline phase");
            }
          }
          timeline.framesByCycle.push_back(std::move(phases));
        }
        timeline.enabled = true;
      }
      loaded.push_back(std::move(resource));
    }
    if (!reader.at_end()) throw std::runtime_error("trailing effect registry bytes");

    for (Resource& resource : loaded) {
      for (std::size_t frameIndex = 0; frameIndex < resource.frames.size(); ++frameIndex) {
        Frame& frame = resource.frames[frameIndex];
        const auto expectedBytes = static_cast<std::uint64_t>(frame.logicalWidth) * kScale *
                                   static_cast<std::uint64_t>(frame.logicalHeight) * kScale * 4ull;
        frame.replacement = read_file(assetsDirectory / frame_asset_name(resource.resref, frameIndex),
                                      expectedBytes);
      }
    }

    std::lock_guard lock(g_mutex);
    g_resources = std::move(loaded);
    invalidate_texture_cache_locked();
#ifdef _WIN32
    g_textureContext = nullptr;
#endif
    g_rendererFailureLogged = false;
    g_uploadFailureLogged = false;
    g_ready.store(true, std::memory_order_release);
    LOG_INFO("Prepared effect animation x4 runtime pack: resources={}, frames={}, rawBytes={}",
             g_resources.size(), [&] {
               std::size_t frames = 0;
               for (const auto& resource : g_resources) frames += resource.frames.size();
               return frames;
             }(), totalRawBytes);
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("Effect animation x4 runtime pack disabled: {}", error.what());
  } catch (...) {
    LOG_WARN("Effect animation x4 runtime pack disabled by an unknown loading error");
  }
  release();
  return false;
}

void release() noexcept {
  g_ready.store(false, std::memory_order_release);
  try {
    std::lock_guard lock(g_mutex);
    g_resources.clear();
    invalidate_texture_cache_locked();
#ifdef _WIN32
    g_textureContext = nullptr;
#endif
    g_rendererFailureLogged = false;
    g_uploadFailureLogged = false;
  } catch (...) {
  }
}

bool ready() noexcept { return g_ready.load(std::memory_order_acquire); }

bool resolve_frame(const std::array<char, 8>& resref, int sequence, int currentFrame,
                   int logicalWidth, int logicalHeight, FrameHandle& out) noexcept {
  out = {};
  if (!g_ready.load(std::memory_order_acquire) || sequence < 0 || currentFrame < 0 ||
      logicalWidth <= 0 || logicalHeight <= 0) {
    return false;
  }
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;
    const auto resource = std::find_if(g_resources.begin(), g_resources.end(),
                                       [&](const Resource& item) { return item.resref == resref; });
    if (resource == g_resources.end() ||
        static_cast<std::size_t>(sequence) >= resource->cycles.size()) {
      return false;
    }
    const auto& cycle = resource->cycles[static_cast<std::size_t>(sequence)];
    if (static_cast<std::size_t>(currentFrame) >= cycle.size()) return false;
    const auto frameIndex = cycle[static_cast<std::size_t>(currentFrame)];
    if (frameIndex >= resource->frames.size()) return false;
    const auto& frame = resource->frames[frameIndex];
    if (frame.logicalWidth != logicalWidth || frame.logicalHeight != logicalHeight) return false;
    out = {.resourceIndex = static_cast<std::size_t>(std::distance(g_resources.begin(), resource)),
           .frameIndex = frameIndex};
    return true;
  } catch (...) {
    return false;
  }
}

bool timeline_info(const std::array<char, 8>& resref, int sequence,
                   TimelineInfo& out) noexcept {
  out = {};
  if (!g_ready.load(std::memory_order_acquire) || sequence < 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;
    const auto resource = std::find_if(g_resources.begin(), g_resources.end(),
                                       [&](const Resource& item) { return item.resref == resref; });
    if (resource == g_resources.end() ||
        static_cast<std::size_t>(sequence) >= resource->cycles.size() ||
        !resource->timeline.enabled ||
        static_cast<std::size_t>(sequence) >= resource->timeline.framesByCycle.size()) {
      return false;
    }
    out = {
        .enabled = true,
        .nativeFpsNumerator = resource->timeline.nativeFpsNumerator,
        .nativeFpsDenominator = resource->timeline.nativeFpsDenominator,
        .targetFpsNumerator = resource->timeline.targetFpsNumerator,
        .targetFpsDenominator = resource->timeline.targetFpsDenominator,
        .phaseCount = resource->timeline.phaseCount,
    };
    return true;
  } catch (...) {
    return false;
  }
}

bool resolve_timeline_frame(const std::array<char, 8>& resref, int sequence,
                            std::uint32_t phase, int logicalWidth,
                            int logicalHeight, FrameHandle& out) noexcept {
  out = {};
  if (!g_ready.load(std::memory_order_acquire) || sequence < 0 || logicalWidth <= 0 ||
      logicalHeight <= 0) {
    return false;
  }
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;
    const auto resource = std::find_if(g_resources.begin(), g_resources.end(),
                                       [&](const Resource& item) { return item.resref == resref; });
    if (resource == g_resources.end() || !resource->timeline.enabled ||
        static_cast<std::size_t>(sequence) >= resource->timeline.framesByCycle.size() ||
        phase >= resource->timeline.phaseCount) {
      return false;
    }
    const auto& phases = resource->timeline.framesByCycle[static_cast<std::size_t>(sequence)];
    if (phase >= phases.size()) return false;
    const auto frameIndex = phases[phase];
    if (frameIndex >= resource->frames.size()) return false;
    const auto& frame = resource->frames[frameIndex];
    if (frame.logicalWidth != logicalWidth || frame.logicalHeight != logicalHeight) return false;
    out = {.resourceIndex = static_cast<std::size_t>(std::distance(g_resources.begin(), resource)),
           .frameIndex = frameIndex};
    return true;
  } catch (...) {
    return false;
  }
}

bool bind_frame_texture(FrameHandle handle, const EngineTextureApi& api,
                        int& previousTextureId) noexcept {
  previousTextureId = 0;
  if (!g_ready.load(std::memory_order_acquire) || !api.DrawGenTexture || !api.DrawBindTexture ||
      !api.DrawDeleteTexture || !api.TexImage || !api.DrawGetRenderer || !api.glTextureState) {
    return false;
  }
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;
    if (api.DrawGetRenderer() == 1) {
      if (!g_rendererFailureLogged) {
        g_rendererFailureLogged = true;
        LOG_WARN("Effect animation x4 skipped: active renderer is not OpenGL");
      }
      return false;
    }
#ifdef _WIN32
    const auto context = game::gl::current_context();
    if (!context) return false;
    if (g_textureContext != context) {
      invalidate_texture_cache_locked();
      g_textureContext = context;
    }
#endif
    previousTextureId = logical_texture_id(api);
    if (previousTextureId <= 0 ||
        !bind_frame_texture_locked(handle, api, previousTextureId)) {
      if (!g_uploadFailureLogged) {
        g_uploadFailureLogged = true;
        LOG_WARN("Effect animation x4 texture creation failed; delegating to original BAM");
      }
      previousTextureId = 0;
      return false;
    }
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("Effect animation x4 composition failed: {}", error.what());
  } catch (...) {
    LOG_WARN("Effect animation x4 composition failed with an unknown error");
  }
  previousTextureId = 0;
  return false;
}

void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept {
  if (api.DrawBindTexture && previousTextureId > 0) api.DrawBindTexture(previousTextureId);
}

}  // namespace iee::effect_animation_x4
