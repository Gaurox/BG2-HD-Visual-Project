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
#include <unordered_map>
#include <memory>
#include <span>
#include <chrono>

#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/opengl_types.h"
#include "iee/game/build_manifest.h"
#include "iee/game/scoped_effect_gl_state.h"

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
  std::size_t cacheId{};
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
  std::uint64_t bytes{};
  bool valid{};
  bool pendingDelete{};
  std::uint32_t glName{};
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
std::mutex g_gpuMutex;
std::atomic<bool> g_ready{false};
std::atomic<bool> g_streaming{false};
std::vector<Resource> g_resources;
std::unordered_map<std::uint64_t, std::size_t> g_resourceIndex;
struct Occurrence { std::uint64_t serial{}, born{}; bool submitted{}; };
std::unordered_map<std::uintptr_t, Occurrence> g_occurrences;
struct TraceRow {
  std::uint64_t epoch{}, serial{}, generation{};
  std::int64_t ticks{};
  std::size_t resource{}, backing{};
  int slot{}, phase{}, worldActive{};
  bool swap{}, hd{}, masked{}, ok{};
  std::array<char, 8> resref{};
  std::uint32_t diagnostic{};
  int sequence{}, width{}, height{};
  bool once{}, paused{};
  DrawOutcome outcome{};
};
std::array<TraceRow, 4096> g_trace;
std::size_t g_traceCount{};
std::uint64_t steady_ns() noexcept {
  return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::steady_clock::now().time_since_epoch()).count());
}
std::uint64_t g_nextSerial{}, g_packGeneration{};
Options g_options;
// No static destructor may join a live DLL worker under loader teardown.
core::EffectFrameCache& cpu_cache() {
  static auto* cache = new core::EffectFrameCache;
  return *cache;
}
std::uint64_t resref_key(const std::array<char, 8>& ref) noexcept {
  std::uint64_t key = 0;
  for (std::size_t i = 0; i < ref.size() && ref[i]; ++i)
    key |= static_cast<std::uint64_t>(std::toupper(static_cast<unsigned char>(ref[i]))) << (i * 8);
  return key;
}
auto find_resource(const std::array<char, 8>& ref) {
  const auto found = g_resourceIndex.find(resref_key(ref));
  return found == g_resourceIndex.end() ? g_resources.end() :
      g_resources.begin() + static_cast<std::ptrdiff_t>(found->second);
}
std::vector<TextureCacheEntry> g_textureCache;
std::uint64_t g_textureUseCounter{};
TextureCacheStats g_textureCacheStats{.capacity = kTextureCacheLimit};
struct ScratchEntry { std::uint32_t name{}; std::uint64_t bytes{}; bool retiring{}; };
std::array<ScratchEntry, game::TextureDescriptorLayout::count> g_scratch{};
std::uint64_t g_scratchReserved{};
#ifdef _WIN32
HGLRC g_textureContext{};
#endif
bool g_rendererFailureLogged = false;
bool g_uploadFailureLogged = false;

std::vector<std::byte> read_file(const std::filesystem::path& path,
                                 std::uint64_t expectedBytes = 0,
                                 std::uint64_t maximum = kMaxRawBytes) {
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file) throw std::runtime_error("missing asset: " + path.string());
  const auto end = file.tellg();
  if (end < 0) throw std::runtime_error("cannot size asset: " + path.string());
  const auto byteCount = static_cast<std::uint64_t>(end);
  if (byteCount > maximum || (expectedBytes != 0 && byteCount != expectedBytes)) {
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
  g_textureUseCounter = 0;
  g_textureCacheStats = {.capacity = kTextureCacheLimit};
  g_textureCacheStats.budget = g_options.gpuBytes;
  g_scratch = {}; g_scratchReserved = 0;
}

bool upload_frame_locked(const Frame& frame, std::span<const std::byte> pixels,
                         int textureId, const EngineTextureApi& api,
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
  if (physicalWidth <= 0 || physicalHeight <= 0 || expectedBytes != pixels.size()) {
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
                  pixels.data());
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

bool flush_native_locked(const EngineTextureApi& api) noexcept {
  if (!api.DrawFlushGl || !api.DrawPushState || !api.DrawPopState) return false;
  api.DrawPushState();
  api.DrawFlushGl();
  api.DrawPopState();
  ++g_textureCacheStats.flushes;
  return true;
}

// Called on the owning GL thread before choosing any victim, including entries
// invalidated by an earlier upload. Never mutate a slot collected/reused by native.
void observe_texture_owners_locked(const EngineTextureApi& api) noexcept {
  if (!api.glTextureTable) return;
  std::erase_if(g_textureCache, [&](auto& e) {
    std::uint32_t name = 0; std::uint8_t pending = 0;
    if (!core::safe_read(api.glTextureTable + e.textureId * game::TextureDescriptorLayout::stride, name) ||
        !core::safe_read(api.glTextureTable + e.textureId * game::TextureDescriptorLayout::stride +
                        game::TextureDescriptorLayout::deletePending, pending)) {
      e.pendingDelete = true; e.valid = false; return false;
    }
    if (!name || (e.glName && name != e.glName) || (e.pendingDelete && !pending)) return true;
    if (pending) { e.pendingDelete = true; e.valid = false; }
    return false;
  });
  g_textureCacheStats.pendingDeletes = 0;
  g_textureCacheStats.residentBytes = 0;
  for (const auto& e : g_textureCache) {
    g_textureCacheStats.residentBytes += e.bytes;
    if (e.pendingDelete) ++g_textureCacheStats.pendingDeletes;
  }
}

bool bind_frame_texture_locked(FrameHandle handle, const EngineTextureApi& api,
                               int previousTextureId) noexcept {
  if ((handle.generation && handle.generation != g_packGeneration) ||
      (g_options.streaming && !handle.generation) ||
      handle.resourceIndex >= g_resources.size() ||
      handle.frameIndex >= g_resources[handle.resourceIndex].frames.size()) return false;
  handle.generation = g_packGeneration;
  observe_texture_owners_locked(api);
  ++g_textureCacheStats.requests;
  const auto existing = std::find_if(g_textureCache.begin(), g_textureCache.end(),
      [&](const TextureCacheEntry& e) { return e.valid && e.handle == handle; });
  if (existing != g_textureCache.end()) {
    if (api.glTextureTable) {
      std::uint32_t name = 0; std::uint8_t pending = 0;
      if (!core::safe_read(api.glTextureTable + existing->textureId * game::TextureDescriptorLayout::stride, name) ||
          !core::safe_read(api.glTextureTable + existing->textureId * game::TextureDescriptorLayout::stride +
                          game::TextureDescriptorLayout::deletePending, pending) ||
          !name || name != existing->glName || pending) {
        existing->valid = false;
        if (pending) existing->pendingDelete = true;
        return false;
      }
    }
    ++g_textureCacheStats.hits;
    existing->lastUse = ++g_textureUseCounter;
    api.DrawBindTexture(existing->textureId);
    return true;
  }
  const auto& frame = g_resources[handle.resourceIndex].frames[handle.frameIndex];
  core::EffectFrameCache::Lease lease;
  std::span<const std::byte> pixels = frame.replacement;
  if (g_options.streaming) {
    lease = cpu_cache().acquire(frame.cacheId);
    if (!lease) { ++g_textureCacheStats.cpuMisses; return false; }
    pixels = *lease;
  }
  const auto bytes = static_cast<std::uint64_t>(pixels.size());
  if (!bytes || bytes > g_options.gpuBytes) return false;
  struct UploadMetric {
    std::uint64_t started{steady_ns()}, bytes{};
    bool attempted{};
    ~UploadMetric() {
      if (!attempted) return;
      const auto elapsed = steady_ns() - started;
      ++g_textureCacheStats.uploads; g_textureCacheStats.uploadedBytes += bytes;
      g_textureCacheStats.uploadNanoseconds += elapsed;
      g_textureCacheStats.maximumUploadNanoseconds = std::max(
          g_textureCacheStats.maximumUploadNanoseconds, elapsed);
    }
  } metric;
  metric.bytes = bytes;
  // This boundary precedes the original CVidCell DrawBegin. A native flush
  // submits queued commands before any descriptor dimensions/storage mutate.
  game::ScopedEffectGlState glState;
  if (!glState.valid()) return false;
  bool flushed = false;
  const auto flush = [&] {
    if (!flushed) flushed = flush_native_locked(api);
    return flushed;
  };
  auto residentBytes = [&] {
    std::uint64_t total = 0;
    for (const auto& e : g_textureCache) total += e.bytes;
    return total;
  };
  const auto victim = [&]() {
    std::size_t selected = g_textureCache.size();
    for (std::size_t i = 0; i < g_textureCache.size(); ++i) {
      const auto& e = g_textureCache[i];
      if (e.textureId == previousTextureId || e.pendingDelete) continue;
      if (selected == g_textureCache.size() || e.lastUse < g_textureCache[selected].lastUse)
        selected = i;
    }
    return selected;
  };
  std::size_t slot = g_textureCache.size();
  int texture = 0;
  if (g_textureCache.size() < kTextureCacheLimit && residentBytes() <= g_options.gpuBytes - bytes) {
    texture = api.DrawGenTexture(static_cast<int>(game::gl::NEAREST), 0, 0, 0);
    if (texture <= 0) ++g_textureCacheStats.allocationFailures;
  }
  if (texture > 0) {
    std::uint32_t name = 0;
    if (api.glTextureTable) (void)core::safe_read(api.glTextureTable +
        texture * game::TextureDescriptorLayout::stride, name);
    g_textureCache.push_back({.textureId = texture, .glName = name});
  }
  else {
    slot = victim();
    if (slot == g_textureCache.size() || !flush()) return false;
    texture = g_textureCache[slot].textureId;
    ++g_textureCacheStats.reuses;
  }
  // Reduce other owned backings if a large frame needs more byte capacity.
  // Keep their descriptors (4-byte empty storage), so deletion cannot accumulate
  // pending engine slots and future uploads can reuse these same <=64 slots.
  while (residentBytes() - g_textureCache[slot].bytes > g_options.gpuBytes - bytes) {
    std::size_t other = g_textureCache.size();
    for (std::size_t i = 0; i < g_textureCache.size(); ++i) {
      if (i == slot || g_textureCache[i].textureId == previousTextureId ||
          g_textureCache[i].pendingDelete || g_textureCache[i].bytes <= 4) continue;
      if (other == g_textureCache.size() || g_textureCache[i].lastUse < g_textureCache[other].lastUse) other = i;
    }
    if (other == g_textureCache.size() || !flush()) return false;
    auto& e = g_textureCache[other];
    game::gl::discard_errors();
    api.DrawBindTexture(e.textureId); api.TexImage(1, 1, nullptr, 0);
    auto& gl = game::gl::get_gl_functions();
    int width = 0, height = 0;
    gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_WIDTH, &width);
    gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_HEIGHT, &height);
    if (width != 1 || height != 1 || gl.glGetError() != game::gl::GL_NO_ERROR) {
      e.valid = false; ++g_textureCacheStats.uploadFailures; return false;
    }
    e.bytes = 4; e.valid = false;
  }
  auto& entry = g_textureCache[slot];
  if (entry.bytes && !flush()) return false;
  entry.valid = false;
  metric.attempted = true;
  if (!upload_frame_locked(frame, pixels, texture, api, previousTextureId)) {
    ++g_textureCacheStats.uploadFailures;
    // Keep ownership on failure. DrawDeleteTexture is deferred and blindly
    // erasing this slot would allow allocations to bypass the descriptor cap.
    entry.bytes = std::max(entry.bytes, bytes);
    g_textureCacheStats.residentBytes = residentBytes();
    return false;
  }
  entry.handle = handle; entry.lastUse = ++g_textureUseCounter;
  entry.bytes = bytes; entry.valid = true;
  if (api.glTextureTable && (!core::safe_read(api.glTextureTable +
      texture * game::TextureDescriptorLayout::stride, entry.glName) || !entry.glName)) {
    entry.valid = false; ++g_textureCacheStats.uploadFailures; return false;
  }
  g_textureCacheStats.residentBytes = residentBytes();
  g_textureCacheStats.peakBytes = std::max(g_textureCacheStats.peakBytes, g_textureCacheStats.residentBytes);
  api.DrawBindTexture(texture);
  return true;
}
}  // namespace

bool prepare(const std::filesystem::path& assetsDirectory) noexcept {
  return prepare(assetsDirectory, Options{});
}

bool prepare(const std::filesystem::path& assetsDirectory, const Options& options) noexcept {
  g_ready.store(false, std::memory_order_release);
  cpu_cache().stop();
  try {
    {
      std::lock_guard lock(g_gpuMutex);
      if (!g_textureCache.empty())
        throw std::runtime_error("effect GPU owners must retire before pack replacement");
    }
    if (!options.metadataBytes || options.metadataBytes > (256ull << 20) ||
        !options.maxResources || options.maxResources > 65536 || !options.gpuBytes ||
        !options.cpu.owners || options.cpu.owners > 65536 ||
        !options.cpu.queued || options.cpu.queued > 65536)
      throw std::runtime_error("invalid effect cache configuration");
    const auto payload = read_file(assetsDirectory / "EffectAnimations-X4.registry", 0,
                                   options.metadataBytes);
    std::uint64_t metadata = payload.size();
    const auto charge = [&](std::uint64_t bytes) {
      if (bytes > options.metadataBytes - metadata)
        throw std::runtime_error("effect catalog exceeds metadata budget");
      metadata += bytes;
    };
    if (options.streaming) {
      charge(static_cast<std::uint64_t>(options.cpu.owners) * (128 * sizeof(std::size_t) + 256));
      charge(static_cast<std::uint64_t>(options.cpu.queued) * sizeof(std::size_t));
      charge(32768 * (sizeof(std::size_t) + 32)); // resident IDs + shutdown lease ledger
    }
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
        resourceCount > (options.streaming ? options.maxResources : kMaxResources)) {
      throw std::runtime_error("invalid EffectAnimations-X4.registry header");
    }

    std::vector<Resource> loaded;
    charge(static_cast<std::uint64_t>(resourceCount) * (sizeof(Resource) + 64));
    loaded.reserve(resourceCount);
    std::unordered_map<std::uint64_t, std::size_t> index;
    index.reserve(resourceCount);
    struct Source { std::array<char, 8> resref; std::size_t frame; };
    auto sources = std::make_shared<std::vector<Source>>();
    std::vector<std::uint64_t> sizes;
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
      if (!index.emplace(resref_key(resource.resref), loaded.size()).second) {
        throw std::runtime_error("duplicate effect resource resref");
      }
      resource.displayName = resref_name(resource.resref);
      // Includes mutable cache descriptors, source IDs, hash/vector overhead.
      charge(static_cast<std::uint64_t>(frameCount) * (sizeof(Frame) + 256));
      charge(static_cast<std::uint64_t>(cycleCount) * (sizeof(std::vector<std::uint32_t>) * 4 + 64));
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
        const auto maximumPayload = options.streaming ? options.packBytes : kMaxRawBytes;
        if (physicalBytes > maximumPayload || totalRawBytes > maximumPayload - physicalBytes) {
          throw std::runtime_error("effect runtime pack exceeds raw-byte limit");
        }
        totalRawBytes += physicalBytes;
        resource.frames.push_back({.logicalWidth = static_cast<int>(width),
            .logicalHeight = static_cast<int>(height), .cacheId = sizes.size()});
        sizes.push_back(physicalBytes);
        sources->push_back({resource.resref, frameIndex});
      }
      resource.cycles.reserve(cycleCount);
      resource.observedSlots.reserve(cycleCount);
      for (std::uint32_t cycleIndex = 0; cycleIndex < cycleCount; ++cycleIndex) {
        std::uint32_t slotCount = 0;
        if (!reader.read(slotCount) || slotCount == 0 || slotCount > kMaxCycleSlots) {
          throw std::runtime_error("invalid effect BAM cycle");
        }
        charge(static_cast<std::uint64_t>(slotCount) * 5);
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
            timeline.nativeFpsDenominator > 1000 || timeline.targetFpsDenominator > 1000 ||
            timeline.nativeFpsNumerator > 240000 || timeline.targetFpsNumerator > 240000 ||
            static_cast<std::uint64_t>(timeline.targetFpsNumerator) *
                    timeline.nativeFpsDenominator <=
                static_cast<std::uint64_t>(timeline.nativeFpsNumerator) *
                    timeline.targetFpsDenominator ||
            timeline.phaseCount == 0 || timeline.phaseCount > kMaxCycleSlots) {
          throw std::runtime_error("invalid effect timeline descriptor");
        }
        charge(static_cast<std::uint64_t>(cycleCount) * timeline.phaseCount * 4);
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
            charge(static_cast<std::uint64_t>(phases) * 4);
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

    if (!options.streaming) for (Resource& resource : loaded) {
      for (std::size_t frameIndex = 0; frameIndex < resource.frames.size(); ++frameIndex) {
        Frame& frame = resource.frames[frameIndex];
        const auto expectedBytes = static_cast<std::uint64_t>(frame.logicalWidth) * kScale *
                                   static_cast<std::uint64_t>(frame.logicalHeight) * kScale * 4ull;
        frame.replacement = read_file(assetsDirectory / frame_asset_name(resource.resref, frameIndex),
                                      expectedBytes);
      }
    }

    if (options.streaming) {
      const auto loader = [sources, assetsDirectory](std::size_t id, std::span<std::byte> out) {
        const auto& src = (*sources)[id];
        const auto beforeOpen = steady_ns();
        std::ifstream file(assetsDirectory / frame_asset_name(src.resref, src.frame),
                           std::ios::binary | std::ios::ate);
        const auto opened = steady_ns();
        bool success = false;
        if (file && file.tellg() == static_cast<std::streamoff>(out.size())) {
          file.seekg(0);
          success = static_cast<bool>(file.read(reinterpret_cast<char*>(out.data()),
                                                static_cast<std::streamsize>(out.size())));
        }
        cpu_cache().record_storage_timing(opened - beforeOpen, steady_ns() - opened);
        return success;
      };
      const auto reporter = [](const core::EffectFrameCache::Stats& cpu) {
        const auto gpu = texture_cache_stats();
        // This callback executes on a reader, without either cache lock held.
        LOG_INFO("Effect streaming CPU: bytes={}/{}, peak={}, ready={}, inFlight={}, pinned={}, "
                 "heads={}, queue={}, readers={}, owners={}, reads={}, hits={}, misses={}, "
                 "failures={}, cancelled={}, evictions={}, admissionFailures={}, readNs={}, maxReadNs={}, "
                 "coalesced={}, queueNs={}, openNs={}, storageReadNs={}, publicationNs={}, retired={}, "
                 "deadlineMisses={}, minReadyLeadNs={}, expiredIntents={}",
                 cpu.committedBytes, cpu.budget, cpu.peakBytes, cpu.readyBytes, cpu.inFlightBytes,
                 cpu.pinnedBytes, cpu.headBytes, cpu.queued, cpu.reading, cpu.owners, cpu.reads,
                 cpu.hits, cpu.misses, cpu.failures, cpu.cancelled, cpu.evictions, cpu.admissionFailures,
                 cpu.readNanoseconds, cpu.maximumReadNanoseconds, cpu.coalesced, cpu.queueNanoseconds,
                 cpu.storageOpenNanoseconds, cpu.storageReadNanoseconds, cpu.publicationNanoseconds,
                 cpu.retiredBytes, cpu.deadlineMisses,
                 cpu.minimumReadyLeadNanoseconds == INT64_MAX ? 0 : cpu.minimumReadyLeadNanoseconds,
                 cpu.expiredIntents);
        LOG_INFO("Effect streaming GPU: bytes={}/{}, peak={}, slots={}/{}, pending={}, scratch={}, "
                 "scratchPeak={}, scratchRefusals={}, flushes={}, cpuMisses={}, draws={}, "
                 "drawMisses={}, firstSubmitMisses={}/{}, leadNs={}, maxLeadNs={}, traceDropped={}, "
                 "uploads={}, uploadedBytes={}, uploadCpuNs={}, maxUploadCpuNs={}, horizonReductions={}",
                 gpu.residentBytes, gpu.budget, gpu.peakBytes, gpu.residentTextures, gpu.capacity,
                 gpu.pendingDeletes, gpu.scratchBytes, gpu.scratchPeakBytes, gpu.scratchRefusals,
                 gpu.flushes, gpu.cpuMisses, gpu.draws, gpu.drawMisses, gpu.firstSubmissionMisses,
                 gpu.firstSubmissions, gpu.hintToFirstSubmitNanoseconds,
                 gpu.maximumHintToFirstSubmitNanoseconds, gpu.traceDropped, gpu.uploads,
                 gpu.uploadedBytes, gpu.uploadNanoseconds, gpu.maximumUploadNanoseconds,
                 gpu.horizonReductions);
        std::array<TraceRow, 4096> rows;
        std::size_t count = 0;
        {
          std::lock_guard lock(g_mutex);
          count = g_traceCount;
          std::copy_n(g_trace.begin(), count, rows.begin()); g_traceCount = 0;
        }
        for (std::size_t i = 0; i < count; ++i) {
          const auto& r = rows[i];
          if (r.diagnostic) {
            LOG_INFO("EFX_STREAM_DIAGNOSTIC resref={} stage=0x{:X} sequence={} slot={} phase={} logical={}x{}",
                resref_name(r.resref), r.diagnostic, r.sequence, r.slot, r.phase, r.width, r.height);
            continue;
          }
          LOG_INFO("EFX_STREAM_ROW swap={} epoch={} qpc={} serial={} generation={} resource={} "
                   "backing={} slot={} phase={} hd={} masked={} ok={} worldActive={} "
                   "resref={} sequence={} once={} paused={} outcome={}",
                   r.swap, r.epoch, r.ticks, r.serial, r.generation, r.resource,
                   r.backing, r.slot, r.phase, r.hd, r.masked, r.ok, r.worldActive,
                   resref_name(r.resref), r.sequence, r.once, r.paused, static_cast<int>(r.outcome));
        }
      };
      if (!cpu_cache().start(std::move(sizes), options.cpu, loader, reporter))
        throw std::runtime_error("cannot start bounded effect readers (frame exceeds reservation?)");
      std::vector<std::size_t> heads;
      for (const auto& resource : loaded) {
        const auto append = [&](const auto& table) {
          for (std::size_t i = 0; i < std::min<std::size_t>(2, table.size()); ++i)
            heads.push_back(resource.frames[table[i]].cacheId);
        };
        if (resource.timeline.enabled) {
          for (const auto& cycle : resource.timeline.framesByCycle) append(cycle);
          for (const auto& cycle : resource.timeline.onceByCycle) append(cycle);
        } else for (const auto& cycle : resource.cycles) append(cycle);
      }
      std::sort(heads.begin(), heads.end());
      heads.erase(std::unique(heads.begin(), heads.end()), heads.end());
      cpu_cache().warm(heads);
      if (cpu_cache().stats().failures) throw std::runtime_error("effect bootstrap image failed");
    }
    std::scoped_lock lock(g_mutex, g_gpuMutex);
    g_traceCount = 0;
    g_options = options;
    ++g_packGeneration;
    g_occurrences.clear(); g_occurrences.reserve(options.cpu.owners);
    g_resourceIndex = std::move(index);
    g_resources = std::move(loaded);
    invalidate_texture_cache_locked();
    g_textureCache.reserve(kTextureCacheLimit);
#ifdef _WIN32
    g_textureContext = nullptr;
#endif
    g_rendererFailureLogged = false;
    g_uploadFailureLogged = false;
    g_streaming.store(options.streaming, std::memory_order_release);
    g_ready.store(true, std::memory_order_release);
    LOG_INFO("Prepared effect animation x4 runtime pack: resources={}, frames={}, rawBytes={}, "
             "gpuTextureCapacity={}, filter=NEAREST",
             g_resources.size(), [&] {
               std::size_t frames = 0;
               for (const auto& resource : g_resources) frames += resource.frames.size();
               return frames;
             }(), totalRawBytes, kTextureCacheLimit);
    LOG_INFO("Effect storage: backend={}, metadataBytes={}, cpuBudget={}, gpuBudget={}",
             options.streaming ? "streaming" : "eager", metadata,
             options.streaming ? options.cpu.bytes : totalRawBytes, options.gpuBytes);
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
  g_streaming.store(false, std::memory_order_release);
  cpu_cache().stop();
  try {
    std::scoped_lock lock(g_mutex, g_gpuMutex);
    g_traceCount = 0;
    g_occurrences.clear(); g_resourceIndex.clear();
    ++g_packGeneration;
    g_resources.clear();
    // Live GL descriptors are retired explicitly on their context thread.
    // Keep their IDs until release_gpu observes collection or context destruction.
    if (g_textureCache.empty()) invalidate_texture_cache_locked();
#ifdef _WIN32
    if (g_textureCache.empty()) g_textureContext = nullptr;
#endif
    g_rendererFailureLogged = false;
    g_uploadFailureLogged = false;
  } catch (...) {
  }
}

bool ready() noexcept { return g_ready.load(std::memory_order_acquire); }
bool streaming() noexcept { return ready() && g_streaming.load(std::memory_order_acquire); }

core::EffectFrameCache::Stats cpu_cache_stats() noexcept { return cpu_cache().stats(); }

core::EffectFrameCache::State cpu_frame_state(FrameHandle handle) noexcept {
  std::lock_guard lock(g_mutex);
  if (!ready() || handle.generation != g_packGeneration || handle.resourceIndex >= g_resources.size() ||
      handle.frameIndex >= g_resources[handle.resourceIndex].frames.size()) return core::EffectFrameCache::State::Absent;
  if (!g_options.streaming) return core::EffectFrameCache::State::Ready;
  return cpu_cache().state(g_resources[handle.resourceIndex].frames[handle.frameIndex].cacheId);
}

std::uint64_t begin_occurrence(std::uintptr_t owner) noexcept {
  if (!owner || !ready()) return 0;
  try {
    std::lock_guard lock(g_mutex);
    const auto existing = g_occurrences.find(owner);
    if (existing != g_occurrences.end()) {
      cpu_cache().remove_intent(existing->second.serial);
      g_occurrences.erase(existing);
    }
    if (g_occurrences.size() >= g_options.cpu.owners || g_nextSerial == UINT64_MAX) return 0;
    const auto serial = ++g_nextSerial;
    g_occurrences.emplace(owner, Occurrence{serial, steady_ns()});
    return serial;
  } catch (...) { return 0; }
}

std::uint64_t end_occurrence(std::uintptr_t owner) noexcept {
  if (!ready()) return 0;
  std::lock_guard lock(g_mutex);
  const auto found = g_occurrences.find(owner);
  if (found == g_occurrences.end()) return 0;
  const auto serial = found->second.serial;
  cpu_cache().remove_intent(serial);
  g_occurrences.erase(found);
  return serial;
}

std::uint64_t occurrence_serial(std::uintptr_t owner) noexcept {
  if (!owner || !ready()) return 0;
  {
    std::lock_guard lock(g_mutex);
    if (!g_options.streaming) return 0;
    const auto found = g_occurrences.find(owner);
    if (found != g_occurrences.end()) return found->second.serial;
  }
  return begin_occurrence(owner);
}

void begin_session() noexcept {
  if (!ready()) return;
  std::lock_guard lock(g_mutex);
  g_occurrences.clear();
  cpu_cache().begin_generation();
}

void prefetch_resource(const std::array<char, 8>& resref) noexcept {
  if (!ready()) return;
  try {
    std::lock_guard lock(g_mutex);
    if (!g_options.streaming) return;
    const auto resource = find_resource(resref);
    if (resource == g_resources.end()) return;
    const auto request = [&](const auto& table, std::size_t accessible) {
      for (std::size_t i = 0; i < std::min({std::size_t{16}, table.size(), accessible}); ++i)
        cpu_cache().request(resource->frames[table[i]].cacheId, 2);
    };
    if (resource->timeline.enabled) {
      const auto& t = resource->timeline;
      for (std::size_t cycle = 0; cycle < resource->cycles.size(); ++cycle) {
        const auto numerator = static_cast<std::uint64_t>(resource->cycles[cycle].size()) *
                               t.targetFpsNumerator * t.nativeFpsDenominator;
        const auto denominator = static_cast<std::uint64_t>(t.targetFpsDenominator) * t.nativeFpsNumerator;
        request(t.framesByCycle[cycle], static_cast<std::size_t>((numerator + denominator - 1) / denominator));
      }
      for (const auto& cycle : resource->timeline.onceByCycle) request(cycle, cycle.size());
    } else for (const auto& cycle : resource->cycles) request(cycle, cycle.size());
    std::uint64_t total = 0;
    for (const auto& frame : resource->frames)
      total += static_cast<std::uint64_t>(frame.logicalWidth) * frame.logicalHeight * 64;
    if (total <= (8ull << 20)) for (const auto& frame : resource->frames)
      cpu_cache().request(frame.cacheId, 4); // Whole small effects remain opportunistic, never pinned.
  } catch (...) {}
}

void prefetch_window(std::uintptr_t owner, const std::array<char, 8>& resref,
                     int sequence, std::uint32_t phase, bool once, bool paused) noexcept {
  if (!ready() || sequence < 0) return;
  try {
    const auto serial = occurrence_serial(owner);
    if (!serial) return;
    std::lock_guard lock(g_mutex);
    if (!g_options.streaming) return;
    const auto resource = find_resource(resref);
    if (resource == g_resources.end() || static_cast<std::size_t>(sequence) >= resource->cycles.size())
      return;
    const auto cycle = static_cast<std::size_t>(sequence);
    const auto& timing = resource->timeline;
    const bool alternate = once && cycle < timing.onceByCycle.size() && !timing.onceByCycle[cycle].empty();
    const auto& table = !timing.enabled ? resource->cycles[cycle] : alternate ?
        timing.onceByCycle[cycle] : timing.framesByCycle[cycle];
    std::size_t count = table.size();
    std::size_t window = 1;
    if (timing.enabled) {
      const auto numerator = static_cast<std::uint64_t>(resource->cycles[cycle].size()) *
                             timing.targetFpsNumerator * timing.nativeFpsDenominator;
      const auto denominator = static_cast<std::uint64_t>(timing.targetFpsDenominator) *
                               timing.nativeFpsNumerator;
      count = std::min<std::size_t>(count, static_cast<std::size_t>((numerator + denominator - 1) / denominator));
      if (!paused) window += static_cast<std::size_t>((static_cast<std::uint64_t>(g_options.horizonMs) *
          timing.targetFpsNumerator + 1000ull * timing.targetFpsDenominator - 1) /
          (1000ull * timing.targetFpsDenominator));
    } else if (!paused) window = 9;
    if (!count || phase >= count) return;
    std::array<std::size_t, 128> wanted{};
    window = std::min({window, count, wanted.size()});
    for (std::size_t n = 0; n < window; ++n) {
      const auto next = static_cast<std::size_t>(phase) + n;
      if (once && next >= count) { window = n; break; }
      wanted[n] = resource->frames[table[next % count]].cacheId;
    }
    // Keep the nearest deadlines when the union of active windows cannot fit.
    while (window) {
      const auto period = timing.enabled ? 1000000000ull * timing.targetFpsDenominator /
          timing.targetFpsNumerator : 66666666ull;
      if (cpu_cache().set_intent(serial, std::span(wanted.data(), window), 1, period)) break;
      if (window == 1) { cpu_cache().request(wanted[0], 0); break; }
      { std::lock_guard gpuLock(g_gpuMutex); ++g_textureCacheStats.horizonReductions; }
      window = (window + 1) / 2;
    }
  } catch (...) {}
}

TextureCacheStats texture_cache_stats() noexcept {
  try {
    std::lock_guard lock(g_gpuMutex);
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
    return g_ready.load(std::memory_order_acquire) && find_resource(resref) != g_resources.end();
  } catch (...) {
    return false;
  }
}

bool mark_diagnostic_stage_once(const std::array<char, 8>& resref,
                                std::uint32_t stage) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || stage == 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    const auto resource = find_resource(resref);
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
    const auto resource = find_resource(resref);
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
    const auto resource = find_resource(resref);
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
           .frameIndex = frameIndex, .generation = g_packGeneration};
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
    const auto resource = find_resource(resref);
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
    const auto resource = find_resource(resref);
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
           .frameIndex = frameIndex, .generation = g_packGeneration};
    return true;
  } catch (...) {
    return false;
  }
}

bool bind_frame_texture(FrameHandle handle, const EngineTextureApi& api,
                        int& previousTextureId, DrawOutcome* outcome) noexcept {
  if (outcome) *outcome = DrawOutcome::GpuRejected;
  previousTextureId = 0;
  if (!g_ready.load(std::memory_order_acquire) || !api.DrawGenTexture || !api.DrawBindTexture ||
      !api.DrawDeleteTexture || !api.TexImage || !api.DrawGetRenderer || !api.glTextureState) {
    return false;
  }
  try {
    std::lock_guard lock(g_gpuMutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;
    if (api.DrawGetRenderer() == 1) {
      if (!g_rendererFailureLogged) {
        g_rendererFailureLogged = true;
        if (!g_options.streaming) LOG_WARN("Effect animation x4 skipped: active renderer is not OpenGL");
      }
      return false;
    }
#ifdef _WIN32
    const auto context = game::gl::current_context();
    if (!context) return false;
    if (g_textureContext != context) {
      // A switch is not evidence of destruction. Never bind integers belonging
      // to another live context, or silently forget the slots we still own.
      if (!g_textureCache.empty()) return false;
      g_textureContext = context;
    }
#endif
    previousTextureId = logical_texture_id(api);
    if (previousTextureId <= 0) return false;
    const auto cpuMisses = g_textureCacheStats.cpuMisses;
    if (!bind_frame_texture_locked(handle, api, previousTextureId)) {
      api.DrawBindTexture(previousTextureId);
      if (cpuMisses != g_textureCacheStats.cpuMisses) {
        if (outcome) *outcome = cpu_cache().state(g_resources[handle.resourceIndex].frames[
            handle.frameIndex].cacheId) == core::EffectFrameCache::State::Failed ?
                DrawOutcome::StorageFailed : DrawOutcome::CpuNotReady;
        previousTextureId = 0; return false;
      }
      if (!g_uploadFailureLogged) {
        g_uploadFailureLogged = true;
        if (!g_options.streaming) LOG_WARN("Effect animation x4 texture creation failed; delegating to original BAM; "
                 "gpuCacheResident={}, gpuCacheCapacity={}, allocationFailures={}, uploadFailures={}",
                 g_textureCache.size(), kTextureCacheLimit,
                 g_textureCacheStats.allocationFailures, g_textureCacheStats.uploadFailures);
      }
      previousTextureId = 0;
      return false;
    }
    if (outcome) *outcome = DrawOutcome::Hd;
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

void release_gpu(const EngineTextureApi& api) noexcept {
  std::lock_guard lock(g_gpuMutex);
#ifdef _WIN32
  if (!g_textureContext || game::gl::current_context() != g_textureContext) return;
#endif
  if (!api.DrawDeleteTexture || g_textureCache.empty()) return;
  game::ScopedEffectGlState state;
  if (!state.valid() || !flush_native_locked(api)) return;
  for (auto& entry : g_textureCache) {
    if (!entry.pendingDelete) api.DrawDeleteTexture(entry.textureId);
    entry.pendingDelete = true; entry.valid = false;
  }
  if (api.glTextureTable) std::erase_if(g_textureCache, [&](const auto& entry) {
    std::uint32_t name = 0;
    return core::safe_read(api.glTextureTable + entry.textureId * game::TextureDescriptorLayout::stride, name) && name == 0;
  });
  g_textureCacheStats.pendingDeletes = g_textureCache.size();
  if (g_textureCache.empty()) invalidate_texture_cache_locked();
}

void context_destroyed(std::uintptr_t context) noexcept {
  std::lock_guard lock(g_gpuMutex);
#ifdef _WIN32
  if (reinterpret_cast<std::uintptr_t>(g_textureContext) != context) return;
  g_textureContext = nullptr;
#else
  (void)context;
#endif
  // Only a successful native context-destruction callback reaches this path.
  invalidate_texture_cache_locked();
}

bool reserve_scratch(std::uint64_t bytes, const std::byte* table) noexcept {
  std::lock_guard lock(g_gpuMutex);
  constexpr std::uint64_t budget = 64ull << 20;
  std::uint64_t held = g_scratchReserved;
  for (std::size_t i = 1; i < g_scratch.size(); ++i) {
    auto& e = g_scratch[i];
    if (!e.bytes) continue;
    std::uint32_t name = 0; std::uint8_t pending = 0;
    if (table && core::safe_read(table + i * game::TextureDescriptorLayout::stride, name) &&
        core::safe_read(table + i * game::TextureDescriptorLayout::stride + game::TextureDescriptorLayout::deletePending, pending) &&
        (!name || name != e.name || (e.retiring && !pending))) e = {};
    held += e.bytes;
  }
  g_textureCacheStats.scratchBytes = held;
  if (!table || held > budget || bytes > budget - held) {
    ++g_textureCacheStats.scratchRefusals; return false;
  }
  g_scratchReserved += bytes;
  g_textureCacheStats.scratchBytes += bytes;
  g_textureCacheStats.scratchPeakBytes = std::max(g_textureCacheStats.scratchPeakBytes,
                                                g_textureCacheStats.scratchBytes);
  return true;
}

void cancel_scratch(std::uint64_t bytes) noexcept {
  std::lock_guard lock(g_gpuMutex);
  const auto cancelled = std::min(bytes, g_scratchReserved);
  g_scratchReserved -= cancelled;
  g_textureCacheStats.scratchBytes -= std::min(cancelled, g_textureCacheStats.scratchBytes);
}

void track_scratch(int texture, std::uint64_t bytes, const std::byte* table) noexcept {
  std::lock_guard lock(g_gpuMutex);
  if (texture <= 0 || texture >= static_cast<int>(game::TextureDescriptorLayout::count)) return;
  std::uint32_t name = 0;
  if (table) (void)core::safe_read(table + texture * game::TextureDescriptorLayout::stride, name);
  g_scratchReserved -= std::min(bytes, g_scratchReserved);
  g_scratch[static_cast<std::size_t>(texture)] = {.name = name, .bytes = bytes};
}

void retire_scratch(int texture) noexcept {
  std::lock_guard lock(g_gpuMutex);
  if (texture > 0 && texture < static_cast<int>(game::TextureDescriptorLayout::count)) g_scratch[static_cast<std::size_t>(texture)].retiring = true;
}

void observe_gpu_retirements(const EngineTextureApi& api) noexcept {
  std::lock_guard lock(g_gpuMutex);
  if (!api.glTextureTable) return;
#ifdef _WIN32
  if (!g_textureContext || game::gl::current_context() != g_textureContext) return;
#endif
  std::uint64_t scratch = g_scratchReserved;
  for (std::size_t i = 1; i < g_scratch.size(); ++i) {
    auto& e = g_scratch[i];
    if (!e.bytes) continue;
    std::uint32_t name = 0; std::uint8_t pending = 0;
    if (core::safe_read(api.glTextureTable + i * game::TextureDescriptorLayout::stride, name) &&
        core::safe_read(api.glTextureTable + i * game::TextureDescriptorLayout::stride +
                        game::TextureDescriptorLayout::deletePending, pending) &&
        (!name || name != e.name || (e.retiring && !pending))) e = {};
    scratch += e.bytes;
  }
  g_textureCacheStats.scratchBytes = scratch;
  observe_texture_owners_locked(api);
}

void note_draw(std::uintptr_t cell, FrameHandle handle, int slot, int phase,
               std::uint64_t epoch, std::int64_t ticks, bool hd, bool masked,
               int sequence, bool once, bool paused, DrawOutcome outcome) noexcept {
  if (!ready()) return;
  std::scoped_lock lock(g_mutex, g_gpuMutex);
  ++g_textureCacheStats.draws;
  if (!hd) ++g_textureCacheStats.drawMisses;
  const auto found = g_occurrences.find(cell);
  const auto serial = found == g_occurrences.end() ? 0 : found->second.serial;
  if (found != g_occurrences.end() && !found->second.submitted) {
    found->second.submitted = true;
    ++g_textureCacheStats.firstSubmissions;
    if (!hd) ++g_textureCacheStats.firstSubmissionMisses;
    const auto elapsed = steady_ns() - found->second.born;
    g_textureCacheStats.hintToFirstSubmitNanoseconds += elapsed;
    g_textureCacheStats.maximumHintToFirstSubmitNanoseconds = std::max(
        g_textureCacheStats.maximumHintToFirstSubmitNanoseconds, elapsed);
  }
  if (!g_options.trace) return;
  if (g_traceCount == g_trace.size()) { ++g_textureCacheStats.traceDropped; return; }
  g_trace[g_traceCount++] = {.epoch = epoch, .serial = serial, .generation = handle.generation,
      .ticks = ticks, .resource = handle.resourceIndex, .backing = handle.frameIndex,
      .slot = slot, .phase = phase, .hd = hd, .masked = masked,
      .resref = handle.resourceIndex < g_resources.size() ? g_resources[handle.resourceIndex].resref :
          std::array<char, 8>{}, .sequence = sequence, .once = once, .paused = paused, .outcome = outcome};
}

void note_swap(std::uint64_t epoch, std::int64_t ticks, bool success, int worldActive) noexcept {
  if (!ready()) return;
  std::scoped_lock lock(g_mutex, g_gpuMutex);
  if (!g_options.trace) return;
  if (g_traceCount == g_trace.size()) { ++g_textureCacheStats.traceDropped; return; }
  g_trace[g_traceCount++] = {.epoch = epoch, .ticks = ticks, .worldActive = worldActive,
                            .swap = true, .ok = success};
}

void queue_diagnostic(const std::array<char, 8>& resref, std::uint32_t stage,
                      int sequence, int frame, int phase, int width, int height) noexcept {
  if (!streaming()) return;
  std::scoped_lock lock(g_mutex, g_gpuMutex);
  if (g_traceCount == g_trace.size()) { ++g_textureCacheStats.traceDropped; return; }
  g_trace[g_traceCount++] = {.slot = frame, .phase = phase, .resref = resref,
      .diagnostic = stage, .sequence = sequence, .width = width, .height = height};
}

}  // namespace iee::effect_animation_x4
