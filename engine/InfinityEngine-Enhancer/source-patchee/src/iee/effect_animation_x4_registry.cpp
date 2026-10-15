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
constexpr std::uint32_t kProfileRegistryVersion = 3;
constexpr std::uint32_t kScale = 4;
// Effects share the engine's 512 descriptor slots with native sprites, UI,
// area animations and transient Character composites. Never retain one slot
// per timeline frame: a short series of spells used to exhaust that table.
constexpr std::size_t kTextureCacheLimit = 64;
constexpr std::uint32_t kMaxResources = 512;
constexpr std::uint32_t kMaxFramesPerResource = 4096;
constexpr std::uint32_t kMaxCyclesPerResource = 256;
constexpr std::uint32_t kMaxCycleSlots = 65536;
// The cumulative 161-effect pack needs 8,208,516,864 CPU bytes.
// Keep a bounded CPU payload limit, independent from the 64-slot GPU cache
// and the geometry, frame and resource limits.
constexpr std::uint64_t kMaxRawBytes = 8192ull * 1024ull * 1024ull;

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
  std::vector<std::vector<std::uint8_t>> observedSlots;
  std::uint32_t reportedDiagnosticStages{};
  struct Timeline {
    bool enabled{};
    std::uint32_t nativeFpsNumerator{};
    std::uint32_t nativeFpsDenominator{};
    std::uint32_t targetFpsNumerator{};
    std::uint32_t targetFpsDenominator{};
    std::uint32_t phaseCount{};
    std::vector<std::vector<std::uint32_t>> framesByCycle;
    std::vector<std::vector<std::uint32_t>> onceByCycle;
  } timeline;
};

struct TextureCacheEntry {
  FrameHandle handle{};
  int textureId{};
  std::uint64_t lastUse{};
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
std::uint64_t g_textureUseCounter{};
TextureCacheStats g_textureCacheStats{.capacity = kTextureCacheLimit};
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

// Infinity resources are case-insensitive; VVCs commonly contain e.g. "SPsump".
// Do not inspect padding after the first NUL in a runtime RESREF.
bool same_resref(const std::array<char, 8>& left,
                 const std::array<char, 8>& right) noexcept {
  for (std::size_t i = 0; i < left.size(); ++i) {
    const auto a = static_cast<unsigned char>(left[i]);
    const auto b = static_cast<unsigned char>(right[i]);
    if (a == 0 || b == 0) return a == b;
    if (std::toupper(a) != std::toupper(b)) return false;
  }
  return true;
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
  g_textureUseCounter = 0;
  g_textureCacheStats = {.capacity = kTextureCacheLimit};
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
                     static_cast<int>(game::gl::NEAREST));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER,
                     static_cast<int>(game::gl::NEAREST));
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
  ++g_textureCacheStats.requests;
  const auto existing = std::find_if(
      g_textureCache.begin(), g_textureCache.end(),
      [&](const TextureCacheEntry& entry) { return entry.handle == handle; });
  if (existing != g_textureCache.end()) {
    ++g_textureCacheStats.hits;
    existing->lastUse = ++g_textureUseCounter;
    api.DrawBindTexture(existing->textureId);
    return true;
  }

  int textureId = 0;
  std::size_t entryIndex = g_textureCache.size();
  if (g_textureCache.size() < kTextureCacheLimit) {
    textureId = api.DrawGenTexture(static_cast<int>(game::gl::NEAREST), 0, 0, 0);
    if (textureId <= 0) ++g_textureCacheStats.allocationFailures;
  }
  if (textureId > 0) {
    g_textureCache.push_back({.handle = handle, .textureId = textureId});
  } else {
    // Reuse an owned LRU descriptor, as the established area-animation cache
    // does. Also recover from native slot pressure before reaching our cap.
    // Binding switches through the engine API preserve its deferred draws.
    for (std::size_t index = 0; index < g_textureCache.size(); ++index) {
      if (g_textureCache[index].textureId == previousTextureId) continue;
      if (entryIndex == g_textureCache.size() ||
          g_textureCache[index].lastUse < g_textureCache[entryIndex].lastUse) {
        entryIndex = index;
      }
    }
    if (entryIndex == g_textureCache.size()) return false;
    textureId = g_textureCache[entryIndex].textureId;
    ++g_textureCacheStats.reuses;
    if (g_textureCacheStats.reuses == 1) {
      LOG_INFO("Effect animation x4 GPU cache reusing owned slots: capacity={}, resident={}; "
               "native Character/UI texture slots remain available",
               kTextureCacheLimit, g_textureCache.size());
    }
  }
  const auto& frame = g_resources[handle.resourceIndex].frames[handle.frameIndex];
  if (!upload_frame_locked(frame, textureId, api, previousTextureId)) {
    ++g_textureCacheStats.uploadFailures;
    api.DrawDeleteTexture(textureId);
    g_textureCache.erase(g_textureCache.begin() + entryIndex);
    api.DrawBindTexture(previousTextureId);
    return false;
  }
  g_textureCache[entryIndex].handle = handle;
  g_textureCache[entryIndex].lastUse = ++g_textureUseCounter;
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
        (version != kRegistryVersion && version != kTimelineRegistryVersion && version != kProfileRegistryVersion) || scale != kScale ||
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
            return same_resref(existing.resref, resource.resref);
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
      resource.observedSlots.reserve(cycleCount);
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
        resource.observedSlots.emplace_back(slotCount, std::uint8_t{0});
        resource.cycles.push_back(std::move(slots));
      }
      if (version >= kTimelineRegistryVersion) {
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
        if (version >= kProfileRegistryVersion) {
          std::uint32_t count = 0;
          if (!reader.read(count) || count > cycleCount) throw std::runtime_error("invalid once profile count");
          timeline.onceByCycle.resize(cycleCount);
          for (std::uint32_t i = 0; i < count; ++i) {
            std::uint32_t cycle = 0, phases = 0;
            if (!reader.read(cycle) || !reader.read(phases) || cycle >= cycleCount ||
                !timeline.onceByCycle[cycle].empty() ||
                phases != resource.cycles[cycle].size() * 2 || phases > timeline.phaseCount)
              throw std::runtime_error("invalid once profile descriptor");
            auto& table = timeline.onceByCycle[cycle];
            table.resize(phases);
            for (auto& frame : table) {
              if (!reader.read(frame) || frame >= frameCount) throw std::runtime_error("invalid once profile frame");
            }
          }
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
    LOG_INFO("Prepared effect animation x4 runtime pack: resources={}, frames={}, rawBytes={}, "
             "gpuTextureCapacity={}, filter=NEAREST",
             g_resources.size(), [&] {
               std::size_t frames = 0;
               for (const auto& resource : g_resources) frames += resource.frames.size();
               return frames;
             }(), totalRawBytes, kTextureCacheLimit);
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

TextureCacheStats texture_cache_stats() noexcept {
  try {
    std::lock_guard lock(g_mutex);
    auto stats = g_textureCacheStats;
    stats.residentTextures = g_textureCache.size();
    return stats;
  } catch (...) {
    return {.capacity = kTextureCacheLimit};
  }
}

bool contains_resource(const std::array<char, 8>& resref) noexcept {
  if (!g_ready.load(std::memory_order_acquire)) return false;
  try {
    std::lock_guard lock(g_mutex);
    return g_ready.load(std::memory_order_acquire) &&
           std::any_of(g_resources.begin(), g_resources.end(),
                       [&](const Resource& item) { return same_resref(item.resref, resref); });
  } catch (...) {
    return false;
  }
}

bool mark_diagnostic_stage_once(const std::array<char, 8>& resref,
                                std::uint32_t stage) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || stage == 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    const auto resource = std::find_if(g_resources.begin(), g_resources.end(),
                                       [&](const Resource& item) { return same_resref(item.resref, resref); });
    if (resource == g_resources.end() || (resource->reportedDiagnosticStages & stage) != 0) {
      return false;
    }
    resource->reportedDiagnosticStages |= stage;
    return true;
  } catch (...) {
    return false;
  }
}

bool mark_geometry_observation_once(const std::array<char, 8>& resref, int sequence,
                                    int nativeFrame) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || sequence < 0 || nativeFrame < 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    const auto resource = std::find_if(g_resources.begin(), g_resources.end(),
                                       [&](const Resource& item) { return same_resref(item.resref, resref); });
    if (resource == g_resources.end() ||
        static_cast<std::size_t>(sequence) >= resource->observedSlots.size()) {
      return false;
    }
    auto& slots = resource->observedSlots[static_cast<std::size_t>(sequence)];
    if (static_cast<std::size_t>(nativeFrame) >= slots.size() || slots[nativeFrame] != 0) {
      return false;
    }
    slots[nativeFrame] = 1;
    return true;
  } catch (...) {
    return false;
  }
}

bool resolve_frame(const std::array<char, 8>& resref, int sequence, int currentFrame,
                   int logicalWidth, int logicalHeight, FrameHandle& out, bool onceProfile) noexcept {
  out = {};
  if (!g_ready.load(std::memory_order_acquire) || sequence < 0 || currentFrame < 0 ||
      logicalWidth <= 0 || logicalHeight <= 0) {
    return false;
  }
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;
    const auto resource = std::find_if(g_resources.begin(), g_resources.end(),
                                       [&](const Resource& item) { return same_resref(item.resref, resref); });
    if (resource == g_resources.end() ||
        static_cast<std::size_t>(sequence) >= resource->cycles.size()) {
      return false;
    }
    const auto& cycle = resource->cycles[static_cast<std::size_t>(sequence)];
    if (static_cast<std::size_t>(currentFrame) >= cycle.size()) return false;
    auto frameIndex = cycle[static_cast<std::size_t>(currentFrame)];
    if (onceProfile && static_cast<std::size_t>(sequence) < resource->timeline.onceByCycle.size()) {
      const auto& table = resource->timeline.onceByCycle[sequence];
      if (!table.empty()) frameIndex = table[static_cast<std::size_t>(currentFrame) * 2];
    }
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
                   TimelineInfo& out, bool onceProfile) noexcept {
  out = {};
  if (!g_ready.load(std::memory_order_acquire) || sequence < 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;
    const auto resource = std::find_if(g_resources.begin(), g_resources.end(),
                                       [&](const Resource& item) { return same_resref(item.resref, resref); });
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
        .phaseCount = onceProfile && static_cast<std::size_t>(sequence) < resource->timeline.onceByCycle.size() &&
                              !resource->timeline.onceByCycle[sequence].empty()
                          ? static_cast<std::uint32_t>(resource->timeline.onceByCycle[sequence].size())
                          : resource->timeline.phaseCount,
    };
    return true;
  } catch (...) {
    return false;
  }
}

bool resolve_timeline_frame(const std::array<char, 8>& resref, int sequence,
                            std::uint32_t phase, int logicalWidth,
                            int logicalHeight, FrameHandle& out, bool onceProfile) noexcept {
  out = {};
  if (!g_ready.load(std::memory_order_acquire) || sequence < 0 || logicalWidth <= 0 ||
      logicalHeight <= 0) {
    return false;
  }
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;
    const auto resource = std::find_if(g_resources.begin(), g_resources.end(),
                                       [&](const Resource& item) { return same_resref(item.resref, resref); });
    if (resource == g_resources.end() || !resource->timeline.enabled ||
        static_cast<std::size_t>(sequence) >= resource->timeline.framesByCycle.size() ||
        phase >= resource->timeline.phaseCount) {
      return false;
    }
    const auto& phases = onceProfile && static_cast<std::size_t>(sequence) < resource->timeline.onceByCycle.size() &&
                                  !resource->timeline.onceByCycle[sequence].empty()
                             ? resource->timeline.onceByCycle[sequence]
                             : resource->timeline.framesByCycle[static_cast<std::size_t>(sequence)];
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
        LOG_WARN("Effect animation x4 texture creation failed; delegating to original BAM; "
                 "gpuCacheResident={}, gpuCacheCapacity={}, allocationFailures={}, uploadFailures={}",
                 g_textureCache.size(), kTextureCacheLimit,
                 g_textureCacheStats.allocationFailures, g_textureCacheStats.uploadFailures);
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
