#include "creature_sprite_x2.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <cctype>
#include <cstdint>
#include <cstring>
#include <exception>
#include <fstream>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <string>
#include <system_error>
#include <type_traits>
#include <utility>
#include <vector>

#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/opengl_types.h"

namespace iee::creature_sprite_x2 {

bool calculate_composite_bounds(const FrameGeometry* frames, std::size_t frameCount,
                                CompositeBounds& out) noexcept {
  out = {};
  if (!frames || frameCount == 0) return false;
  CompositeBounds bounds{
      .left = -frames[0].centerX,
      .top = -frames[0].centerY,
      .right = frames[0].logicalWidth - frames[0].centerX,
      .bottom = frames[0].logicalHeight - frames[0].centerY,
  };
  if (frames[0].logicalWidth <= 0 || frames[0].logicalHeight <= 0) return false;
  for (std::size_t index = 1; index < frameCount; ++index) {
    const auto& frame = frames[index];
    if (frame.logicalWidth <= 0 || frame.logicalHeight <= 0) return false;
    bounds.left = (std::min)(bounds.left, -frame.centerX);
    bounds.top = (std::min)(bounds.top, -frame.centerY);
    bounds.right = (std::max)(bounds.right, frame.logicalWidth - frame.centerX);
    bounds.bottom = (std::max)(bounds.bottom, frame.logicalHeight - frame.centerY);
  }
  if (bounds.content_width() <= 0 || bounds.content_height() <= 0) return false;
  out = bounds;
  return true;
}

namespace {
constexpr std::array<char, 8> kLegacyRegistryMagic{
    {'I', 'E', 'E', 'C', 'S', 'X', '2', '\0'}};
constexpr std::array<char, 8> kXnRegistryMagic{
    {'I', 'E', 'E', 'C', 'S', 'X', 'N', '\0'}};
constexpr std::uint32_t kLegacyRegistryVersion = 1;
constexpr std::uint32_t kLegacyCurrentRegistryVersion = 2;
constexpr std::uint32_t kXnRegistryVersion = 3;
constexpr std::uint16_t kLegacyMgo1AnimationId = 0xE400;
constexpr char kLegacyRegistryFilename[] = "CreatureSprites-X2.registry";
constexpr char kXnRegistryFilename[] = "CreatureSprites-XN.registry";
// Four Character body armor codes require 92 split BAMs; the remaining room
// carries the registered weapon/offhand/helmet overlays in the same pack.
constexpr std::uint32_t kMaximumResources = 128;
constexpr std::uint32_t kMaximumFramesPerResource = 4096;
constexpr std::uint32_t kMaximumCyclesPerResource = 256;
constexpr std::uint32_t kMaximumCycleSlots = 65536;
constexpr std::size_t kTextureCacheEntryLimit = 128;
constexpr std::uint64_t kTextureCacheBudgetBytes = 128ull * 1024ull * 1024ull;
constexpr std::size_t kCompositePixelCacheLimit = 32;
constexpr std::size_t kEngineTextureDescriptorCount = 512;
constexpr std::size_t kEngineTextureDescriptorStride = 0x28;
// Character replacements keep CPU pixels only. Bound the aggregate cache to
// four MiB; each draw uses one dedicated engine texture marked delete-pending
// immediately after its queued draw.
constexpr std::uint64_t kCompositePixelCacheBudgetBytes = 4ull * 1024ull * 1024ull;

struct Frame {
  int logicalWidth{};
  int logicalHeight{};
  int centerX{};
  int centerY{};
  std::uint8_t transparent{};
  std::array<std::uint16_t, 256> representatives{};
  std::vector<std::uint8_t> indices;
};

struct Resource {
  std::array<char, 8> resref{};
  std::array<std::byte, 32> sourceSha256{};
  std::vector<Frame> frames;
  std::vector<std::vector<std::uint32_t>> cycles;
  std::vector<bool> compositionLogged;
};

struct TextureCacheEntry {
  FrameHandle handle{};
  std::uint64_t paletteFingerprint{};
  int textureId{};
  std::uint64_t physicalBytes{};
  std::uint64_t lastUse{};
};

struct CompositeLayerCacheKey {
  FrameHandle frame{};
  std::uint64_t paletteFingerprint{};

  [[nodiscard]] constexpr bool operator==(const CompositeLayerCacheKey&) const noexcept = default;
};

struct CompositePixelCacheEntry {
  std::array<CompositeLayerCacheKey, kMaximumCompositeLayers> layers{};
  std::size_t layerCount{};
  int logicalWidth{};
  int logicalHeight{};
  std::uint32_t physicalScale{};
  NativePixelEncoding encoding{};
  std::vector<std::uint32_t> pixels;
  std::uint64_t lastUse{};
};

class BinaryReader {
 public:
  explicit BinaryReader(std::vector<std::byte> bytes) : bytes_(std::move(bytes)) {}

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

  bool read_bytes(std::vector<std::uint8_t>& out, std::size_t byteCount) {
    if (offset_ > bytes_.size() || byteCount > bytes_.size() - offset_) return false;
    out.resize(byteCount);
    if (byteCount != 0) std::memcpy(out.data(), bytes_.data() + offset_, byteCount);
    offset_ += byteCount;
    return true;
  }

  [[nodiscard]] bool at_end() const noexcept { return offset_ == bytes_.size(); }

 private:
  std::vector<std::byte> bytes_;
  std::size_t offset_{};
};

std::mutex g_mutex;
std::atomic<bool> g_ready{false};
std::atomic<std::uint16_t> g_targetAnimationId{0};
std::atomic<std::uint32_t> g_loadedScale{0};
std::vector<Resource> g_resources;
std::vector<TextureCacheEntry> g_textureCache;
std::vector<CompositePixelCacheEntry> g_compositePixelCache;
std::uint64_t g_textureUseCounter{};
bool g_creationFailureLogged{};
bool g_dimensionMismatchLogged{};
bool g_compositeDimensionMismatchLogged{};
bool g_rendererFailureLogged{};
bool g_contextFailureLogged{};
bool g_sourceTextureFailureLogged{};
std::atomic<bool> g_paletteApiFailureLogged{false};
std::atomic<bool> g_realizedPaletteLogged{false};
bool g_compositeBackingFailureLogged{};
#ifdef _WIN32
HGLRC g_textureContext{};
#endif

void reset_diagnostics_locked() noexcept {
  g_creationFailureLogged = false;
  g_dimensionMismatchLogged = false;
  g_compositeDimensionMismatchLogged = false;
  g_rendererFailureLogged = false;
  g_contextFailureLogged = false;
  g_sourceTextureFailureLogged = false;
  g_paletteApiFailureLogged.store(false, std::memory_order_release);
  g_realizedPaletteLogged.store(false, std::memory_order_release);
  g_compositeBackingFailureLogged = false;
}

std::vector<std::byte> read_file(const std::filesystem::path& path) {
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file) throw std::runtime_error("missing creature-sprite registry: " + path.string());
  const auto end = file.tellg();
  if (end <= 0 || static_cast<std::uint64_t>(end) > kMaximumRegistryBytes) {
    throw std::runtime_error("invalid creature-sprite registry size");
  }
  file.seekg(0);
  std::vector<std::byte> bytes(static_cast<std::size_t>(end));
  if (!file.read(reinterpret_cast<char*>(bytes.data()),
                 static_cast<std::streamsize>(bytes.size()))) {
    throw std::runtime_error("cannot read creature-sprite registry");
  }
  return bytes;
}

std::string resref_name(const std::array<char, 8>& resref) {
  const auto end = std::find(resref.begin(), resref.end(), '\0');
  return std::string(resref.begin(), end);
}

bool checked_physical_metrics(int logicalWidth, int logicalHeight,
                              std::uint32_t scale, int& physicalWidth,
                              int& physicalHeight, std::uint64_t& pixelCount,
                              std::uint64_t& rgbaBytes) noexcept {
  physicalWidth = 0;
  physicalHeight = 0;
  pixelCount = 0;
  rgbaBytes = 0;
  if (logicalWidth <= 0 || logicalHeight <= 0 || !supported_physical_scale(scale)) {
    return false;
  }
  const auto width64 = static_cast<std::uint64_t>(logicalWidth) * scale;
  const auto height64 = static_cast<std::uint64_t>(logicalHeight) * scale;
  if (width64 > static_cast<std::uint64_t>((std::numeric_limits<int>::max)()) ||
      height64 > static_cast<std::uint64_t>((std::numeric_limits<int>::max)()) ||
      width64 > (std::numeric_limits<std::uint64_t>::max)() / height64) {
    return false;
  }
  const auto pixels = width64 * height64;
  if (pixels == 0 || pixels > (std::numeric_limits<std::uint64_t>::max)() /
                                  sizeof(std::uint32_t) ||
      pixels > (std::numeric_limits<std::size_t>::max)()) {
    return false;
  }
  physicalWidth = static_cast<int>(width64);
  physicalHeight = static_cast<int>(height64);
  pixelCount = pixels;
  rgbaBytes = pixels * sizeof(std::uint32_t);
  return true;
}

bool maximum_texture_size_allows(game::gl::OpenGLFunctions& gl, int physicalWidth,
                                 int physicalHeight) noexcept {
  if (!gl.glGetError) return false;
  game::gl::discard_errors();
  int maximumTextureSize = 0;
  gl.glGetIntegerv(game::gl::MAX_TEXTURE_SIZE, &maximumTextureSize);
  const auto error = gl.glGetError();
  return error == game::gl::GL_NO_ERROR && maximumTextureSize > 0 &&
         physicalWidth <= maximumTextureSize && physicalHeight <= maximumTextureSize;
}

std::uint64_t texture_cache_bytes_locked() noexcept {
  std::uint64_t total = 0;
  for (const auto& entry : g_textureCache) {
    if (entry.physicalBytes > (std::numeric_limits<std::uint64_t>::max)() - total) {
      return (std::numeric_limits<std::uint64_t>::max)();
    }
    total += entry.physicalBytes;
  }
  return total;
}

int logical_texture_id(const EngineTextureApi& api) noexcept {
  if (!api.glTextureState) return 0;
  std::uint32_t state = 0;
  if (!core::safe_read(api.glTextureState, state)) return 0;
  return static_cast<int>((state >> 21u) & 0x1FFu);
}

struct EngineTextureDescriptorSnapshot {
  std::uint32_t glName{};
  std::int32_t logicalWidth{};
  std::int32_t logicalHeight{};
  std::uint8_t deletePending{};
  std::uint32_t secondaryGlName{};
};

bool read_engine_texture_descriptor(const EngineTextureApi& api, int textureId,
                                    EngineTextureDescriptorSnapshot& out) noexcept {
  out = {};
  if (!api.glTextureTable || textureId <= 0 ||
      textureId >= static_cast<int>(kEngineTextureDescriptorCount)) {
    return false;
  }
  const auto* descriptor =
      api.glTextureTable +
      static_cast<std::size_t>(textureId) * kEngineTextureDescriptorStride;
  return core::safe_read(descriptor + 0x00, out.glName) &&
         core::safe_read(descriptor + 0x04, out.logicalWidth) &&
         core::safe_read(descriptor + 0x08, out.logicalHeight) &&
         core::safe_read(descriptor + 0x0D, out.deletePending) &&
         core::safe_read(descriptor + 0x24, out.secondaryGlName);
}

bool clear_private_recycled_secondary(const EngineTextureApi& api, int textureId,
                                      EngineTextureDescriptorSnapshot& snapshot) noexcept {
  if (snapshot.secondaryGlName == 0) return true;
  if (!api.glTextureTable || textureId <= 0 ||
      textureId >= static_cast<int>(kEngineTextureDescriptorCount) || snapshot.glName == 0 ||
      snapshot.deletePending != 0) {
    return false;
  }

  // DrawGenTexture can recycle a descriptor whose +0x24 multitexture name was
  // never cleared by the engine sweep. This ID is private and has not been
  // queued yet. Clear only the stale selector; do not delete the GL name,
  // because another live descriptor may still own the same object.
  auto* secondaryField =
      api.glTextureTable +
      static_cast<std::size_t>(textureId) * kEngineTextureDescriptorStride + 0x24;
  if (!core::is_writable_non_executable_memory(secondaryField,
                                               sizeof(std::uint32_t))) {
    return false;
  }
  const std::uint32_t zero = 0;
  std::memcpy(secondaryField, &zero, sizeof(zero));

  EngineTextureDescriptorSnapshot cleared{};
  if (!read_engine_texture_descriptor(api, textureId, cleared) ||
      cleared.glName != snapshot.glName || cleared.deletePending != 0 ||
      cleared.secondaryGlName != 0) {
    return false;
  }
  snapshot = cleared;
  return true;
}

void clear_texture_cache_locked() noexcept {
  g_textureCache.clear();
  g_compositePixelCache.clear();
  g_textureUseCounter = 0;
}

void delete_texture_entry_locked(const EngineTextureApi& api,
                                  std::size_t entryIndex) noexcept {
  if (entryIndex >= g_textureCache.size()) return;
  const int textureId = g_textureCache[entryIndex].textureId;
  if (textureId > 0 && api.DrawDeleteTexture) api.DrawDeleteTexture(textureId);
  g_textureCache.erase(g_textureCache.begin() + static_cast<std::ptrdiff_t>(entryIndex));
}

void delete_owned_textures_locked(const EngineTextureApi& api) noexcept {
  if (api.DrawDeleteTexture) {
    for (const auto& entry : g_textureCache) {
      if (entry.textureId > 0) api.DrawDeleteTexture(entry.textureId);
    }
  }
  clear_texture_cache_locked();
}

std::uint64_t fnv1a_append(std::uint64_t hash, std::uint8_t value) noexcept {
  constexpr std::uint64_t kPrime = 1099511628211ull;
  return (hash ^ value) * kPrime;
}

std::uint64_t palette_fingerprint(const Frame& frame,
                                  const std::array<std::uint32_t, 256>& realized,
                                  NativePixelEncoding encoding) noexcept {
  std::uint64_t fingerprint = 1469598103934665603ull;
  const auto appendDword = [&](std::uint32_t value) {
    for (unsigned shift = 0; shift < 32; shift += 8) {
      fingerprint = fnv1a_append(fingerprint, static_cast<std::uint8_t>(value >> shift));
    }
  };
  appendDword(encoding.externalFormat);
  appendDword(encoding.type);
  for (std::size_t paletteIndex = 0; paletteIndex < frame.representatives.size();
       ++paletteIndex) {
    if (frame.representatives[paletteIndex] == 0xFFFFu) continue;
    fingerprint = fnv1a_append(fingerprint, static_cast<std::uint8_t>(paletteIndex));
    appendDword(realized[paletteIndex]);
  }
  return fingerprint;
}

void enforce_transparent_entry(const Frame& frame,
                               std::array<std::uint32_t, 256>& realized) noexcept;

std::array<CompositeLayerCacheKey, kMaximumCompositeLayers>
composite_cache_layers_locked(const CompositeLayer* layers,
                              std::size_t layerCount) noexcept {
  std::array<CompositeLayerCacheKey, kMaximumCompositeLayers> key{};
  for (std::size_t index = 0; index < layerCount; ++index) {
    const auto& layer = layers[index];
    const auto& frame = g_resources[layer.frame.resourceIndex].frames[layer.frame.frameIndex];
    auto realized = layer.palette.colors;
    enforce_transparent_entry(frame, realized);
    key[index] = {
        .frame = layer.frame,
        .paletteFingerprint = palette_fingerprint(frame, realized, layer.palette.encoding),
    };
  }
  return key;
}

void enforce_transparent_entry(const Frame& frame,
                               std::array<std::uint32_t, 256>& realized) noexcept {
  // CVidCell zeros its transparent entry immediately after Realize. Enforce
  // the same invariant because the owner-scoped snapshot is taken on return
  // from Realize, just before CVidCell clears this slot itself.
  realized[frame.transparent] = 0;
}

bool upload_frame_locked(const Frame& frame, const std::array<std::uint32_t, 256>& realized,
                         NativePixelEncoding encoding, std::uint32_t physicalScale,
                         int textureId, int previousTextureId,
                         const EngineTextureApi& api) {
  auto& gl = game::gl::get_gl_functions();
  if ((!gl.valid && !gl.initialize()) || !gl.glGetIntegerv || !gl.glTexImage2D ||
      !gl.glTexParameteri || !gl.glPixelStorei || !gl.glGetTexLevelParameteriv ||
      !gl.glGetError) {
    return false;
  }
  const int textureLogicalWidth = logical_texture_extent(frame.logicalWidth);
  const int textureLogicalHeight = logical_texture_extent(frame.logicalHeight);
  int contentPhysicalWidth = 0;
  int contentPhysicalHeight = 0;
  std::uint64_t expectedContentPixels = 0;
  std::uint64_t contentBytes = 0;
  int physicalWidth = 0;
  int physicalHeight = 0;
  std::uint64_t texturePixels = 0;
  std::uint64_t textureBytes = 0;
  if (!checked_physical_metrics(frame.logicalWidth, frame.logicalHeight, physicalScale,
                                contentPhysicalWidth, contentPhysicalHeight,
                                expectedContentPixels, contentBytes) ||
      !checked_physical_metrics(textureLogicalWidth, textureLogicalHeight, physicalScale,
                                physicalWidth, physicalHeight, texturePixels,
                                textureBytes) ||
      frame.indices.size() != expectedContentPixels ||
      !maximum_texture_size_allows(gl, physicalWidth, physicalHeight)) {
    return false;
  }
  std::vector<std::uint32_t> replacement(static_cast<std::size_t>(texturePixels), 0);
  const auto contentOffset = static_cast<std::size_t>(physical_content_offset(physicalScale));
  for (int y = 0; y < contentPhysicalHeight; ++y) {
    const auto sourceRow = static_cast<std::size_t>(y) * contentPhysicalWidth;
    const auto destinationRow = (static_cast<std::size_t>(y) + contentOffset) * physicalWidth +
                                contentOffset;
    for (int x = 0; x < contentPhysicalWidth; ++x) {
      const auto sourceIndex = sourceRow + static_cast<std::size_t>(x);
      replacement[destinationRow + static_cast<std::size_t>(x)] =
          realized[frame.indices[sourceIndex]];
    }
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
  if (unpackBuffer != 0) return false;
  const auto restoreState = [&] {
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
  api.TexImage(textureLogicalWidth, textureLogicalHeight, nullptr, 0);
  int boundTexture = 0;
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &boundTexture);
  if (boundTexture <= 0 || gl.glGetError() != game::gl::GL_NO_ERROR) {
    restoreState();
    return false;
  }
  gl.glTexImage2D(game::gl::TEXTURE_2D, 0, static_cast<int>(game::gl::RGBA8), physicalWidth,
                   physicalHeight, 0, encoding.externalFormat, encoding.type,
                   replacement.data());
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
  restoreState();
  return success;
}

bool compose_composite_pixels_locked(const CompositeLayer* layers,
                                     std::size_t layerCount,
                                     const CompositeBounds& bounds,
                                     int logicalWidth, int logicalHeight,
                                     std::uint32_t physicalScale,
                                     std::vector<std::uint32_t>& replacement) {
  if (!layers || layerCount == 0 || logicalWidth <= 0 || logicalHeight <= 0 ||
      logicalWidth > 512 || logicalHeight > 512) {
    return false;
  }
  int physicalWidth = 0;
  int physicalHeight = 0;
  std::uint64_t texturePixels = 0;
  std::uint64_t textureBytes = 0;
  if (!checked_physical_metrics(logicalWidth, logicalHeight, physicalScale,
                                physicalWidth, physicalHeight, texturePixels,
                                textureBytes) ||
      textureBytes > kCompositePixelCacheBudgetBytes) {
    return false;
  }
  replacement.assign(static_cast<std::size_t>(texturePixels), 0);

  for (std::size_t layerIndex = 0; layerIndex < layerCount; ++layerIndex) {
    const auto& layer = layers[layerIndex];
    const auto& frame = g_resources[layer.frame.resourceIndex].frames[layer.frame.frameIndex];
    int sourceWidth = 0;
    int sourceHeight = 0;
    std::uint64_t expectedPixels = 0;
    std::uint64_t sourceBytes = 0;
    if (!checked_physical_metrics(frame.logicalWidth, frame.logicalHeight, physicalScale,
                                  sourceWidth, sourceHeight, expectedPixels,
                                  sourceBytes) ||
        frame.indices.size() != expectedPixels) {
      return false;
    }
    const auto destinationX64 =
        physical_layer_offset(frame.centerX, bounds.left, physicalScale);
    const auto destinationY64 =
        physical_layer_offset(frame.centerY, bounds.top, physicalScale);
    if (destinationX64 < 0 || destinationY64 < 0 ||
        destinationX64 > (std::numeric_limits<int>::max)() ||
        destinationY64 > (std::numeric_limits<int>::max)()) {
      return false;
    }
    const int destinationX = static_cast<int>(destinationX64);
    const int destinationY = static_cast<int>(destinationY64);
    if (destinationX < 0 || destinationY < 0 ||
        sourceWidth > physicalWidth - destinationX ||
        sourceHeight > physicalHeight - destinationY) {
      return false;
    }
    auto realized = layer.palette.colors;
    enforce_transparent_entry(frame, realized);
    for (int y = 0; y < sourceHeight; ++y) {
      const auto sourceRow = static_cast<std::size_t>(y) * sourceWidth;
      const auto destinationRow = static_cast<std::size_t>(destinationY + y) * physicalWidth +
                                  static_cast<std::size_t>(destinationX);
      for (int x = 0; x < sourceWidth; ++x) {
        const auto pixel = realized[frame.indices[sourceRow + static_cast<std::size_t>(x)]];
        // Character's native CPU compositor overwrites with every non-zero
        // palette color. Alpha is retained for the single final GPU draw.
        auto& destination = replacement[destinationRow + static_cast<std::size_t>(x)];
        destination = overwrite_nontransparent_pixel(destination, pixel);
      }
    }
  }
  return true;
}

bool upload_composite_texture_locked(const std::vector<std::uint32_t>& replacement,
                                     int logicalWidth, int logicalHeight,
                                     NativePixelEncoding encoding,
                                     std::uint32_t physicalScale, int textureId,
                                     int previousTextureId,
                                     const EngineTextureApi& api) noexcept {
  auto& gl = game::gl::get_gl_functions();
  if ((!gl.valid && !gl.initialize()) || !gl.glGetIntegerv || !gl.glTexImage2D ||
      !gl.glBindTexture || !gl.glTexParameteri || !gl.glPixelStorei ||
      !gl.glGetTexLevelParameteriv ||
      !gl.glGetError || !api.DrawBindTexture || !api.TexImage || !api.glTextureState ||
      !api.glTextureTable || logicalWidth <= 0 || logicalHeight <= 0 || textureId <= 0 ||
      previousTextureId <= 0) {
    return false;
  }
  int physicalWidth = 0;
  int physicalHeight = 0;
  std::uint64_t expectedPixels = 0;
  std::uint64_t expectedBytes = 0;
  if (!checked_physical_metrics(logicalWidth, logicalHeight, physicalScale,
                                physicalWidth, physicalHeight, expectedPixels,
                                expectedBytes) ||
      expectedBytes > kCompositePixelCacheBudgetBytes ||
      replacement.size() != expectedPixels ||
      !maximum_texture_size_allows(gl, physicalWidth, physicalHeight)) {
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

  const auto restoreState = [&] {
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

  // Switching from the native transient ID to an enhancer-owned ID forces the
  // deferred renderer to resolve the correct backing. Any failure below only
  // clears that dedicated replacement; the native sprite remains untouched.
  EngineTextureDescriptorSnapshot generated{};
  if (!read_engine_texture_descriptor(api, textureId, generated) ||
      generated.glName == 0 || generated.deletePending != 0 ||
      !clear_private_recycled_secondary(api, textureId, generated)) {
    restoreState();
    return false;
  }
  api.DrawBindTexture(textureId);
  if (logical_texture_id(api) != textureId) {
    restoreState();
    return false;
  }
  gl.glBindTexture(game::gl::TEXTURE_2D, generated.glName);
  int forcedBinding = 0;
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &forcedBinding);
  if (forcedBinding != static_cast<int>(generated.glName) ||
      gl.glGetError() != game::gl::GL_NO_ERROR) {
    restoreState();
    return false;
  }
  api.TexImage(logicalWidth, logicalHeight, nullptr, 0);
  int boundTexture = 0;
  int backingWidth = 0;
  int backingHeight = 0;
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &boundTexture);
  gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_WIDTH,
                              &backingWidth);
  gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_HEIGHT,
                              &backingHeight);
  EngineTextureDescriptorSnapshot materialized{};
  const auto materializeError = gl.glGetError();
  const bool descriptorMatches =
      read_engine_texture_descriptor(api, textureId, materialized) &&
      materialized.glName == generated.glName && materialized.deletePending == 0 &&
      materialized.secondaryGlName == 0 &&
      materialized.logicalWidth == logicalWidth &&
      materialized.logicalHeight == logicalHeight;
  if (!descriptorMatches || boundTexture != static_cast<int>(generated.glName) ||
      backingWidth != logicalWidth || backingHeight != logicalHeight ||
      materializeError != game::gl::GL_NO_ERROR) {
    if (!g_compositeBackingFailureLogged) {
      g_compositeBackingFailureLogged = true;
      LOG_WARN(
          "Creature sprite xBR2x Character replacement backing rejected: texture id {}, "
          "GL name {}, backing {}x{}, expected {}x{}, error={} (0x{:X}); native "
          "composite retained",
          textureId, boundTexture, backingWidth, backingHeight, logicalWidth,
          logicalHeight, game::gl::error_string(materializeError), materializeError);
    }
    restoreState();
    return false;
  }
  gl.glTexImage2D(game::gl::TEXTURE_2D, 0, static_cast<int>(game::gl::RGBA8), physicalWidth,
                  physicalHeight, 0, encoding.externalFormat, encoding.type,
                  replacement.data());
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
  gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_HEIGHT,
                              &actualHeight);
  const bool success = actualWidth == physicalWidth && actualHeight == physicalHeight &&
                       gl.glGetError() == game::gl::GL_NO_ERROR;
  restoreState();
  return success;
}

bool ensure_texture_locked(FrameHandle handle, const std::array<std::uint32_t, 256>& realized,
                            NativePixelEncoding encoding, std::uint64_t fingerprint,
                            std::uint32_t physicalScale, int previousTextureId,
                            const EngineTextureApi& api, int& textureId) {
  textureId = 0;
  const auto& frame = g_resources[handle.resourceIndex].frames[handle.frameIndex];
  int physicalWidth = 0;
  int physicalHeight = 0;
  std::uint64_t physicalPixels = 0;
  std::uint64_t physicalBytes = 0;
  if (!checked_physical_metrics(logical_texture_extent(frame.logicalWidth),
                                logical_texture_extent(frame.logicalHeight),
                                physicalScale, physicalWidth, physicalHeight,
                                physicalPixels, physicalBytes) ||
      physicalBytes > kTextureCacheBudgetBytes) {
    return false;
  }
  auto existing = std::find_if(g_textureCache.begin(), g_textureCache.end(),
                               [&](const TextureCacheEntry& entry) {
                                 return entry.handle == handle &&
                                        entry.paletteFingerprint == fingerprint;
                               });
  if (existing != g_textureCache.end()) {
    existing->lastUse = ++g_textureUseCounter;
    textureId = existing->textureId;
    return textureId > 0;
  }

  auto cachedBytes = texture_cache_bytes_locked();
  std::size_t entryIndex = 0;
  const bool newTexture =
      g_textureCache.size() < kTextureCacheEntryLimit &&
      cachedBytes <= kTextureCacheBudgetBytes &&
      physicalBytes <= kTextureCacheBudgetBytes - cachedBytes;
  if (newTexture) {
    const int generated = api.DrawGenTexture(static_cast<int>(game::gl::NEAREST), 0, 0, 0);
    if (generated <= 0) return false;
    g_textureCache.push_back({.handle = handle,
                              .paletteFingerprint = fingerprint,
                              .textureId = generated,
                              .physicalBytes = physicalBytes});
    entryIndex = g_textureCache.size() - 1;
  } else {
    if (g_textureCache.empty()) return false;
    const auto lru = std::min_element(
        g_textureCache.begin(), g_textureCache.end(),
        [](const TextureCacheEntry& left, const TextureCacheEntry& right) {
          return left.lastUse < right.lastUse;
        });
    entryIndex = static_cast<std::size_t>(std::distance(g_textureCache.begin(), lru));
    const auto replacementFits = [&] {
      const auto replacedBytes = g_textureCache[entryIndex].physicalBytes;
      return cachedBytes >= replacedBytes &&
             cachedBytes - replacedBytes <= kTextureCacheBudgetBytes &&
             physicalBytes <=
                 kTextureCacheBudgetBytes - (cachedBytes - replacedBytes);
    };
    while (!replacementFits() && g_textureCache.size() > 1) {
      std::size_t victimIndex = g_textureCache.size();
      for (std::size_t index = 0; index < g_textureCache.size(); ++index) {
        if (index == entryIndex) continue;
        if (victimIndex == g_textureCache.size() ||
            g_textureCache[index].lastUse < g_textureCache[victimIndex].lastUse) {
          victimIndex = index;
        }
      }
      if (victimIndex == g_textureCache.size()) break;
      const auto victimBytes = g_textureCache[victimIndex].physicalBytes;
      if (cachedBytes < victimBytes) return false;
      cachedBytes -= victimBytes;
      delete_texture_entry_locked(api, victimIndex);
      if (victimIndex < entryIndex) --entryIndex;
    }
    if (!replacementFits()) return false;
    auto& replacement = g_textureCache[entryIndex];
    replacement.handle = handle;
    replacement.paletteFingerprint = fingerprint;
    replacement.physicalBytes = physicalBytes;
  }
  auto& entry = g_textureCache[entryIndex];
  if (!upload_frame_locked(frame, realized, encoding, physicalScale, entry.textureId,
                           previousTextureId, api)) {
    delete_texture_entry_locked(api, entryIndex);
    api.DrawBindTexture(previousTextureId);
    return false;
  }
  entry.lastUse = ++g_textureUseCounter;
  textureId = entry.textureId;
  return true;
}

bool ensure_composite_pixels_locked(
    const CompositeLayer* layers, std::size_t layerCount,
    const CompositeBounds& bounds, int logicalWidth, int logicalHeight,
    NativePixelEncoding encoding, std::uint32_t physicalScale,
    const std::array<CompositeLayerCacheKey, kMaximumCompositeLayers>& cacheLayers,
    const std::vector<std::uint32_t>*& pixels) {
  pixels = nullptr;
  auto existing = std::find_if(
      g_compositePixelCache.begin(), g_compositePixelCache.end(),
      [&](const CompositePixelCacheEntry& entry) {
        return entry.layerCount == layerCount && entry.layers == cacheLayers &&
               entry.logicalWidth == logicalWidth && entry.logicalHeight == logicalHeight &&
               entry.physicalScale == physicalScale &&
               entry.encoding.externalFormat == encoding.externalFormat &&
               entry.encoding.type == encoding.type;
      });
  if (existing != g_compositePixelCache.end()) {
    existing->lastUse = ++g_textureUseCounter;
    pixels = &existing->pixels;
    return !pixels->empty();
  }
  CompositePixelCacheEntry prepared{
      .layers = cacheLayers,
      .layerCount = layerCount,
      .logicalWidth = logicalWidth,
      .logicalHeight = logicalHeight,
      .physicalScale = physicalScale,
      .encoding = encoding,
  };
  if (!compose_composite_pixels_locked(layers, layerCount, bounds, logicalWidth,
                                       logicalHeight, physicalScale, prepared.pixels)) {
    return false;
  }
  prepared.lastUse = ++g_textureUseCounter;
  const auto preparedBytes =
      static_cast<std::uint64_t>(prepared.pixels.size()) * sizeof(std::uint32_t);
  if (preparedBytes > kCompositePixelCacheBudgetBytes) return false;
  auto cachedBytes = [] {
    std::uint64_t total = 0;
    for (const auto& entry : g_compositePixelCache) {
      const auto entryBytes =
          static_cast<std::uint64_t>(entry.pixels.size()) * sizeof(std::uint32_t);
      if (entryBytes > (std::numeric_limits<std::uint64_t>::max)() - total) {
        return (std::numeric_limits<std::uint64_t>::max)();
      }
      total += entryBytes;
    }
    return total;
  }();
  while (!g_compositePixelCache.empty() &&
         (g_compositePixelCache.size() >= kCompositePixelCacheLimit ||
          cachedBytes > kCompositePixelCacheBudgetBytes ||
          preparedBytes > kCompositePixelCacheBudgetBytes - cachedBytes)) {
    const auto lru = std::min_element(
        g_compositePixelCache.begin(), g_compositePixelCache.end(),
        [](const CompositePixelCacheEntry& left,
           const CompositePixelCacheEntry& right) {
          return left.lastUse < right.lastUse;
        });
    const auto lruBytes =
        static_cast<std::uint64_t>(lru->pixels.size()) * sizeof(std::uint32_t);
    if (cachedBytes < lruBytes) return false;
    cachedBytes -= lruBytes;
    g_compositePixelCache.erase(lru);
  }
  g_compositePixelCache.push_back(std::move(prepared));
  pixels = &g_compositePixelCache.back().pixels;
  return pixels && !pixels->empty();
}
}  // namespace

bool prepare(const std::filesystem::path& assetsDirectory) noexcept {
  try {
    const auto xnPath = assetsDirectory / kXnRegistryFilename;
    const auto legacyPath = assetsDirectory / kLegacyRegistryFilename;
    std::error_code pathError;
    const bool xnExists = std::filesystem::exists(xnPath, pathError);
    if (pathError) {
      throw std::runtime_error("cannot inspect creature-sprite xN registry");
    }
    const bool xnFormat = xnExists;
    const auto& registryPath = xnFormat ? xnPath : legacyPath;
    BinaryReader reader(read_file(registryPath));
    std::array<char, 8> magic{};
    std::uint32_t version = 0;
    std::uint32_t scale = 0;
    std::uint32_t resourceCount = 0;
    std::uint32_t metadata = 0;
    if (!reader.read(magic) || !reader.read(version) || !reader.read(scale) ||
        !reader.read(resourceCount) || !reader.read(metadata)) {
      throw std::runtime_error("truncated creature-sprite registry header");
    }
    const bool formatHeaderValid =
        xnFormat
            ? magic == kXnRegistryMagic && version == kXnRegistryVersion &&
                  supported_physical_scale(scale)
            : magic == kLegacyRegistryMagic &&
                  (version == kLegacyRegistryVersion ||
                   version == kLegacyCurrentRegistryVersion) &&
                  scale == 2;
    if (!formatHeaderValid || resourceCount == 0 || resourceCount > kMaximumResources) {
      throw std::runtime_error("invalid creature-sprite registry header: " +
                               registryPath.filename().string());
    }
    std::uint16_t animationId = 0;
    if (!xnFormat && version == kLegacyRegistryVersion) {
      if (metadata != 0) throw std::runtime_error("invalid legacy creature-sprite metadata");
      animationId = kLegacyMgo1AnimationId;
    } else {
      if (metadata == 0 || metadata > std::numeric_limits<std::uint16_t>::max()) {
        throw std::runtime_error("invalid creature-sprite animation id");
      }
      animationId = static_cast<std::uint16_t>(metadata);
    }
    std::vector<Resource> loaded;
    loaded.reserve(resourceCount);
    std::size_t totalFrames = 0;
    std::uint64_t totalIndexBytes = 0;
    for (std::uint32_t resourceIndex = 0; resourceIndex < resourceCount; ++resourceIndex) {
      Resource resource;
      std::uint32_t frameCount = 0;
      std::uint32_t cycleCount = 0;
      if (!reader.read(resource.resref) || !reader.read(resource.sourceSha256) ||
          !reader.read(frameCount) || !reader.read(cycleCount) || frameCount == 0 ||
          frameCount > kMaximumFramesPerResource || cycleCount == 0 ||
          cycleCount > kMaximumCyclesPerResource) {
        throw std::runtime_error("invalid creature-sprite resource header");
      }
      if (std::find_if(loaded.begin(), loaded.end(), [&](const Resource& existing) {
            return existing.resref == resource.resref;
          }) != loaded.end()) {
        throw std::runtime_error("duplicate creature-sprite resref");
      }
      resource.frames.reserve(frameCount);
      for (std::uint32_t frameIndex = 0; frameIndex < frameCount; ++frameIndex) {
        Frame frame;
        std::uint16_t width = 0;
        std::uint16_t height = 0;
        std::int16_t centerX = 0;
        std::int16_t centerY = 0;
        std::array<std::byte, 3> frameReserved{};
        std::uint32_t indexBytes = 0;
        if (!reader.read(width) || !reader.read(height) || !reader.read(centerX) ||
            !reader.read(centerY) || !reader.read(frame.transparent) ||
            !reader.read(frameReserved) || !reader.read(indexBytes) || width == 0 || height == 0 ||
            frameReserved != std::array<std::byte, 3>{}) {
          throw std::runtime_error("invalid creature-sprite frame header");
        }
        const auto nativePixels = static_cast<std::uint64_t>(width) * height;
        const auto scaleSquared = static_cast<std::uint64_t>(scale) * scale;
        if (nativePixels > (std::numeric_limits<std::uint64_t>::max)() / scaleSquared) {
          throw std::runtime_error("creature-sprite frame payload overflows");
        }
        const auto expectedIndices = nativePixels * scaleSquared;
        if (expectedIndices > (std::numeric_limits<std::uint32_t>::max)() ||
            expectedIndices != indexBytes || indexBytes > kMaximumRegistryBytes ||
            totalIndexBytes > kMaximumRegistryBytes - indexBytes ||
            !reader.read(frame.representatives) ||
            !reader.read_bytes(frame.indices, indexBytes)) {
          throw std::runtime_error("invalid creature-sprite frame payload");
        }
        for (const auto paletteIndex : frame.indices) {
          if (frame.representatives[paletteIndex] == 0xFFFFu) {
            throw std::runtime_error("creature-sprite payload lacks a palette representative");
          }
        }
        frame.logicalWidth = width;
        frame.logicalHeight = height;
        frame.centerX = centerX;
        frame.centerY = centerY;
        resource.frames.push_back(std::move(frame));
        totalIndexBytes += indexBytes;
      }
      resource.cycles.resize(cycleCount);
      for (std::uint32_t cycleIndex = 0; cycleIndex < cycleCount; ++cycleIndex) {
        std::uint32_t slotCount = 0;
        if (!reader.read(slotCount) || slotCount > kMaximumCycleSlots) {
          throw std::runtime_error("invalid creature-sprite cycle");
        }
        auto& cycle = resource.cycles[cycleIndex];
        cycle.resize(slotCount);
        for (auto& frameIndex : cycle) {
          if (!reader.read(frameIndex) || frameIndex >= frameCount) {
            throw std::runtime_error("invalid creature-sprite cycle lookup");
          }
        }
      }
      resource.compositionLogged.resize(frameCount, false);
      totalFrames += frameCount;
      loaded.push_back(std::move(resource));
    }
    if (!reader.at_end()) throw std::runtime_error("trailing creature-sprite registry bytes");
    {
      std::lock_guard lock(g_mutex);
      g_resources = std::move(loaded);
      clear_texture_cache_locked();
      reset_diagnostics_locked();
      g_targetAnimationId.store(animationId, std::memory_order_release);
      g_loadedScale.store(scale, std::memory_order_release);
      g_ready.store(true, std::memory_order_release);
    }
    LOG_INFO(
        "Creature sprite xBR2x pack ready: animation 0x{:04X}, scale=x{}, {} resources, {} "
        "frames, {} index bytes; source={}; filter=NEAREST; registry budget={} MiB",
        animationId, scale, resourceCount, totalFrames, totalIndexBytes,
        registryPath.filename().string(), kMaximumRegistryBytes / (1024ull * 1024ull));
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("Creature sprite xBR2x pack disabled: {}", error.what());
  } catch (...) {
    LOG_WARN("Creature sprite xBR2x pack disabled by an unknown error");
  }
  release();
  return false;
}

void release() noexcept {
  std::lock_guard lock(g_mutex);
  g_ready.store(false, std::memory_order_release);
  g_targetAnimationId.store(0, std::memory_order_release);
  g_loadedScale.store(0, std::memory_order_release);
  g_resources.clear();
  clear_texture_cache_locked();
  reset_diagnostics_locked();
#ifdef _WIN32
  g_textureContext = nullptr;
#endif
}

bool ready() noexcept { return g_ready.load(std::memory_order_acquire); }

std::uint16_t target_animation_id() noexcept {
  return g_targetAnimationId.load(std::memory_order_acquire);
}

std::uint32_t loaded_scale() noexcept {
  return g_loadedScale.load(std::memory_order_acquire);
}

bool contains_resource(const std::array<char, 8>& resref) noexcept {
  if (!g_ready.load(std::memory_order_acquire)) return false;
  try {
    std::lock_guard lock(g_mutex);
    return std::find_if(g_resources.begin(), g_resources.end(), [&](const Resource& resource) {
             return resource.resref == resref;
           }) != g_resources.end();
  } catch (...) {
    return false;
  }
}

bool capture_palette_snapshot(const std::uint32_t* realizedOutput, const EngineTextureApi& api,
                              PaletteSnapshot& out) noexcept {
  out = {};
  PaletteSnapshot snapshot{};
  if (!realizedOutput || realizedOutput != api.realizedPalette || !api.nativePixelEncoding ||
      !core::safe_read(realizedOutput, snapshot.colors) ||
      !core::safe_read(api.nativePixelEncoding, snapshot.encoding)) {
    if (!g_paletteApiFailureLogged.exchange(true, std::memory_order_acq_rel)) {
      LOG_WARN(
          "Creature sprite xBR2x owner palette or native pixel encoding is unavailable; "
          "native BAM rendering retained");
    }
    return false;
  }
  if (!supported_native_pixel_encoding(snapshot.encoding)) {
    if (!g_paletteApiFailureLogged.exchange(true, std::memory_order_acq_rel)) {
      LOG_WARN(
          "Creature sprite xBR2x native pixel encoding is invalid: format=0x{:X}, "
          "type=0x{:X}; native BAM rendering retained",
          snapshot.encoding.externalFormat, snapshot.encoding.type);
    }
    return false;
  }
  out = snapshot;
  if (!g_realizedPaletteLogged.exchange(true, std::memory_order_acq_rel)) {
    LOG_INFO(
        "Creature sprite xBR2x uses an owner-scoped CVidPalette::Realize snapshot at {}; "
        "native pixel encoding format=0x{:X}, type=0x{:X} is uploaded without repacking",
        static_cast<const void*>(realizedOutput), snapshot.encoding.externalFormat,
        snapshot.encoding.type);
  }
  return true;
}

bool resolve_frame(const std::array<char, 8>& resref, int sequence, int currentFrame,
                   FrameHandle& out) noexcept {
  out = {};
  if (!g_ready.load(std::memory_order_acquire) || sequence < 0 || currentFrame < 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    const auto resource = std::find_if(g_resources.begin(), g_resources.end(),
                                       [&](const Resource& item) { return item.resref == resref; });
    if (resource == g_resources.end() || static_cast<std::size_t>(sequence) >= resource->cycles.size()) {
      return false;
    }
    const auto& cycle = resource->cycles[static_cast<std::size_t>(sequence)];
    if (static_cast<std::size_t>(currentFrame) >= cycle.size()) return false;
    out.resourceIndex = static_cast<std::size_t>(std::distance(g_resources.begin(), resource));
    out.frameIndex = cycle[static_cast<std::size_t>(currentFrame)];
    return out.frameIndex < resource->frames.size();
  } catch (...) {
    return false;
  }
}

bool bind_frame_texture(FrameHandle handle, int logicalWidth, int logicalHeight,
                        const PaletteSnapshot& palette, const EngineTextureApi& api,
                        int& previousTextureId) noexcept {
  previousTextureId = 0;
  if (!g_ready.load(std::memory_order_acquire) || !api.DrawGenTexture ||
      !api.DrawBindTexture || !api.DrawDeleteTexture || !api.TexImage ||
      !api.DrawGetRenderer || !api.glTextureState ||
      !supported_native_pixel_encoding(palette.encoding)) {
    return false;
  }
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) || handle.resourceIndex >= g_resources.size() ||
        handle.frameIndex >= g_resources[handle.resourceIndex].frames.size()) {
      return false;
    }
    const auto physicalScale = g_loadedScale.load(std::memory_order_acquire);
    if (!supported_physical_scale(physicalScale)) return false;
    const auto& frame = g_resources[handle.resourceIndex].frames[handle.frameIndex];
    const int expectedLogicalWidth = logical_texture_extent(frame.logicalWidth);
    const int expectedLogicalHeight = logical_texture_extent(frame.logicalHeight);
    if (logicalWidth != expectedLogicalWidth || logicalHeight != expectedLogicalHeight) {
      if (!g_dimensionMismatchLogged) {
        g_dimensionMismatchLogged = true;
        LOG_WARN(
            "Creature sprite xBR2x skipped: RenderTexture packed argument is {}x{}, "
            "expected native bordered texture {}x{} for BAM frame {}x{}",
            logicalWidth, logicalHeight, expectedLogicalWidth, expectedLogicalHeight,
            frame.logicalWidth, frame.logicalHeight);
      }
      return false;
    }
    if (api.DrawGetRenderer() == 1) {
      if (!g_rendererFailureLogged) {
        g_rendererFailureLogged = true;
        LOG_WARN("Creature sprite xBR2x skipped: active renderer is not OpenGL");
      }
      return false;
    }
#ifdef _WIN32
    const auto context = game::gl::current_context();
    if (!context) {
      if (!g_contextFailureLogged) {
        g_contextFailureLogged = true;
        LOG_WARN("Creature sprite xBR2x skipped: no current OpenGL context");
      }
      return false;
    }
    if (g_textureContext != context) {
      delete_owned_textures_locked(api);
      g_textureContext = context;
      for (auto& resource : g_resources) {
        std::fill(resource.compositionLogged.begin(), resource.compositionLogged.end(), false);
      }
    }
#endif
    previousTextureId = logical_texture_id(api);
    if (previousTextureId <= 0) {
      if (!g_sourceTextureFailureLogged) {
        g_sourceTextureFailureLogged = true;
        LOG_WARN("Creature sprite xBR2x skipped: native logical texture id is unavailable");
      }
      return false;
    }
    auto realized = palette.colors;
    enforce_transparent_entry(frame, realized);
    const auto fingerprint = palette_fingerprint(frame, realized, palette.encoding);
    int replacementTexture = 0;
    if (!ensure_texture_locked(handle, realized, palette.encoding, fingerprint,
                               physicalScale, previousTextureId, api,
                               replacementTexture)) {
      if (!g_creationFailureLogged) {
        g_creationFailureLogged = true;
        LOG_WARN("Creature sprite xBR2x texture creation failed; using native BAM rendering");
      }
      return false;
    }
    api.DrawBindTexture(replacementTexture);
    auto& resource = g_resources[handle.resourceIndex];
    if (!resource.compositionLogged[handle.frameIndex]) {
      resource.compositionLogged[handle.frameIndex] = true;
      LOG_INFO(
          "Composing creature sprite {} frame {:03}: scale=x{}, BAM logical {}x{}, "
          "upscaled content {}x{}, bordered texture {}x{} (NEAREST)",
          resref_name(resource.resref), handle.frameIndex, physicalScale,
          frame.logicalWidth, frame.logicalHeight,
          static_cast<std::int64_t>(frame.logicalWidth) * physicalScale,
          static_cast<std::int64_t>(frame.logicalHeight) * physicalScale,
          physical_texture_extent(frame.logicalWidth, physicalScale),
          physical_texture_extent(frame.logicalHeight, physicalScale));
    }
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("Creature sprite xBR2x composition failed: {}", error.what());
  } catch (...) {
    LOG_WARN("Creature sprite xBR2x composition failed with an unknown error");
  }
  return false;
}

bool bind_composite_texture(const CompositeLayer* layers, std::size_t layerCount,
                            int logicalWidth, int logicalHeight,
                            const EngineTextureApi& api,
                            int& previousTextureId,
                            int& transientTextureId) noexcept {
  previousTextureId = 0;
  transientTextureId = 0;
  if (!g_ready.load(std::memory_order_acquire) || !layers || layerCount == 0 ||
      layerCount > kMaximumCompositeLayers || !api.DrawGenTexture ||
      !api.DrawBindTexture || !api.DrawDeleteTexture || !api.TexImage ||
      !api.DrawGetRenderer || !api.glTextureState || !api.glTextureTable) {
    return false;
  }
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;
    const auto physicalScale = g_loadedScale.load(std::memory_order_acquire);
    if (!supported_physical_scale(physicalScale)) return false;
    std::array<FrameGeometry, kMaximumCompositeLayers> geometries{};
    NativePixelEncoding encoding{};
    for (std::size_t index = 0; index < layerCount; ++index) {
      const auto& layer = layers[index];
      if (layer.frame.resourceIndex >= g_resources.size() ||
          layer.frame.frameIndex >= g_resources[layer.frame.resourceIndex].frames.size() ||
          !supported_native_pixel_encoding(layer.palette.encoding)) {
        return false;
      }
      if (index == 0) {
        encoding = layer.palette.encoding;
      } else if (layer.palette.encoding.externalFormat != encoding.externalFormat ||
                 layer.palette.encoding.type != encoding.type) {
        return false;
      }
      const auto& frame =
          g_resources[layer.frame.resourceIndex].frames[layer.frame.frameIndex];
      geometries[index] = {.logicalWidth = frame.logicalWidth,
                           .logicalHeight = frame.logicalHeight,
                           .centerX = frame.centerX,
                           .centerY = frame.centerY};
    }
    CompositeBounds bounds{};
    if (!calculate_composite_bounds(geometries.data(), layerCount, bounds)) return false;
    if (logicalWidth != bounds.logical_width() || logicalHeight != bounds.logical_height()) {
      if (!g_compositeDimensionMismatchLogged) {
        g_compositeDimensionMismatchLogged = true;
        LOG_WARN(
            "Creature sprite xBR2x Character composite skipped: RenderTexture packed "
            "argument is {}x{}, registered layer union requires {}x{}; native composite "
            "retained",
            logicalWidth, logicalHeight, bounds.logical_width(), bounds.logical_height());
      }
      return false;
    }
    if (api.DrawGetRenderer() == 1) {
      if (!g_rendererFailureLogged) {
        g_rendererFailureLogged = true;
        LOG_WARN("Creature sprite xBR2x skipped: active renderer is not OpenGL");
      }
      return false;
    }
#ifdef _WIN32
    const auto context = game::gl::current_context();
    if (!context) {
      if (!g_contextFailureLogged) {
        g_contextFailureLogged = true;
        LOG_WARN("Creature sprite xBR2x skipped: no current OpenGL context");
      }
      return false;
    }
    if (g_textureContext != context) {
      delete_owned_textures_locked(api);
      g_textureContext = context;
      for (auto& resource : g_resources) {
        std::fill(resource.compositionLogged.begin(), resource.compositionLogged.end(), false);
      }
    }
#endif
    previousTextureId = logical_texture_id(api);
    if (previousTextureId <= 0) {
      if (!g_sourceTextureFailureLogged) {
        g_sourceTextureFailureLogged = true;
        LOG_WARN(
            "Creature sprite xBR2x Character skipped: native logical texture id is "
            "unavailable");
      }
      return false;
    }
    const auto cacheLayers = composite_cache_layers_locked(layers, layerCount);
    const std::vector<std::uint32_t>* pixels = nullptr;
    if (!ensure_composite_pixels_locked(layers, layerCount, bounds, logicalWidth,
                                        logicalHeight, encoding, physicalScale,
                                        cacheLayers, pixels) ||
        !pixels) {
      if (!g_creationFailureLogged) {
        g_creationFailureLogged = true;
        LOG_WARN(
            "Creature sprite xBR2x Character pixel composition failed; native composite "
            "retained");
      }
      return false;
    }
    transientTextureId =
        api.DrawGenTexture(static_cast<int>(game::gl::NEAREST), 0, 0, 0);
    if (transientTextureId <= 0 || transientTextureId == previousTextureId ||
        !upload_composite_texture_locked(*pixels, logicalWidth, logicalHeight,
                                         encoding, physicalScale,
                                         transientTextureId, previousTextureId,
                                         api)) {
      api.DrawBindTexture(previousTextureId);
      if (transientTextureId > 0 && transientTextureId != previousTextureId) {
        api.DrawDeleteTexture(transientTextureId);
      }
      transientTextureId = 0;
      if (!g_creationFailureLogged) {
        g_creationFailureLogged = true;
        LOG_WARN(
            "Creature sprite xBR2x Character transient replacement failed; native "
            "composite retained");
      }
      return false;
    }
    api.DrawBindTexture(transientTextureId);
    if (logical_texture_id(api) != transientTextureId) {
      api.DrawBindTexture(previousTextureId);
      if (transientTextureId != previousTextureId) {
        api.DrawDeleteTexture(transientTextureId);
      }
      transientTextureId = 0;
      return false;
    }
    for (std::size_t index = 0; index < layerCount; ++index) {
      const auto& layer = layers[index];
      auto& resource = g_resources[layer.frame.resourceIndex];
      if (resource.compositionLogged[layer.frame.frameIndex]) continue;
      resource.compositionLogged[layer.frame.frameIndex] = true;
      const auto& frame = resource.frames[layer.frame.frameIndex];
      LOG_INFO(
          "Composing creature sprite {} frame {:03} as Character composite layer "
          "{}/{}: scale=x{}, BAM logical {}x{}, final bordered texture {}x{} physical {}x{} "
          "via transient replacement id {} (NEAREST, delete-pending after queued draw)",
          resref_name(resource.resref), layer.frame.frameIndex, index + 1, layerCount,
          physicalScale, frame.logicalWidth, frame.logicalHeight, logicalWidth,
          logicalHeight, static_cast<std::int64_t>(logicalWidth) * physicalScale,
          static_cast<std::int64_t>(logicalHeight) * physicalScale,
          transientTextureId);
    }
    return true;
  } catch (const std::exception& error) {
    if (api.DrawBindTexture && previousTextureId > 0) {
      api.DrawBindTexture(previousTextureId);
    }
    if (api.DrawDeleteTexture && transientTextureId > 0 &&
        transientTextureId != previousTextureId) {
      api.DrawDeleteTexture(transientTextureId);
    }
    transientTextureId = 0;
    LOG_WARN("Creature sprite xBR2x Character composition failed: {}", error.what());
  } catch (...) {
    if (api.DrawBindTexture && previousTextureId > 0) {
      api.DrawBindTexture(previousTextureId);
    }
    if (api.DrawDeleteTexture && transientTextureId > 0 &&
        transientTextureId != previousTextureId) {
      api.DrawDeleteTexture(transientTextureId);
    }
    transientTextureId = 0;
    LOG_WARN("Creature sprite xBR2x Character composition failed with an unknown error");
  }
  return false;
}

void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept {
  if (api.DrawBindTexture && previousTextureId > 0) api.DrawBindTexture(previousTextureId);
}

void finish_composite_texture(const EngineTextureApi& api, int previousTextureId,
                              int transientTextureId) noexcept {
  if (api.DrawBindTexture && previousTextureId > 0) api.DrawBindTexture(previousTextureId);
  if (api.DrawDeleteTexture && transientTextureId > 0 &&
      transientTextureId != previousTextureId) {
    api.DrawDeleteTexture(transientTextureId);
  }
}

void forget_engine_textures() noexcept {
  std::lock_guard lock(g_mutex);
  clear_texture_cache_locked();
#ifdef _WIN32
  g_textureContext = nullptr;
#endif
  for (auto& resource : g_resources) {
    std::fill(resource.compositionLogged.begin(), resource.compositionLogged.end(), false);
  }
}
}  // namespace iee::creature_sprite_x2
