#include "item_icon_x2.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <cctype>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <exception>
#include <fstream>
#include <iterator>
#include <limits>
#include <mutex>
#include <string>
#include <type_traits>
#include <unordered_map>
#include <vector>

#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/opengl_types.h"

namespace iee::item_icon_x2 {
namespace {

constexpr std::array<char, 8> kMagic{{'I', 'E', 'E', 'I', 'C', 'X', '2', '\0'}};
constexpr std::uint32_t kVersion = 2;
constexpr std::uint32_t kScale = 2;
constexpr std::uint32_t kHeaderBytes = 40;
constexpr std::uint32_t kRecordBytes = 40;
constexpr std::uint32_t kMaximumRecords = 10000;
constexpr std::uint64_t kMaximumPackBytes = 256ull * 1024ull * 1024ull;
constexpr std::size_t kTextureCacheLimit = 64;
constexpr std::uint32_t kMaximumDetailedLogs = 64;

struct Record {
  std::array<char, 8> resref{};
  std::uint16_t sequence{};
  std::uint16_t slot{};
  std::uint16_t sourceWidth{};
  std::uint16_t sourceHeight{};
  std::uint16_t replacementWidth{};
  std::uint16_t replacementHeight{};
  std::uint32_t globalFrame{};
  std::uint64_t dataOffset{};
  std::uint32_t dataBytes{};
};

struct Key {
  std::array<char, 8> resref{};
  std::uint16_t sequence{};
  std::uint16_t slot{};
  [[nodiscard]] bool operator==(const Key&) const noexcept = default;
};

struct KeyHash {
  std::size_t operator()(const Key& key) const noexcept {
    std::size_t value = 14695981039346656037ull;
    for (const auto byte : key.resref) {
      value ^= static_cast<unsigned char>(byte);
      value *= 1099511628211ull;
    }
    value ^= (static_cast<std::size_t>(key.sequence) << 16u) | key.slot;
    return value;
  }
};

struct ResrefHash {
  std::size_t operator()(const std::array<char, 8>& value) const noexcept {
    std::size_t hash = 14695981039346656037ull;
    for (const auto byte : value) {
      hash ^= static_cast<unsigned char>(byte);
      hash *= 1099511628211ull;
    }
    return hash;
  }
};

struct TextureEntry {
  FrameHandle handle{};
  int textureId{};
  std::uint64_t lastUse{};
};

std::mutex g_mutex;
std::atomic<bool> g_ready{false};
std::vector<std::byte> g_pack;
std::vector<Record> g_records;
std::unordered_map<Key, std::uint32_t, KeyHash> g_lookup;
std::unordered_map<std::array<char, 8>, std::uint16_t, ResrefHash> g_sequenceCounts;
std::unordered_map<Key, std::uint16_t, KeyHash> g_cycleSizes;
std::vector<TextureEntry> g_textureCache;
std::uint64_t g_textureUseCounter{};
std::vector<bool> g_loggedRecords;
std::uint32_t g_detailedLogs{};
#ifdef _WIN32
HGLRC g_textureContext{};
#endif

template <typename T>
bool read_le(const std::vector<std::byte>& bytes, std::size_t offset, T& out) noexcept {
  static_assert(std::is_unsigned_v<T>);
  if (offset > bytes.size() || bytes.size() - offset < sizeof(T)) return false;
  T value{};
  for (std::size_t index = 0; index < sizeof(T); ++index) {
    value |= static_cast<T>(std::to_integer<unsigned char>(bytes[offset + index]))
             << (index * 8u);
  }
  out = value;
  return true;
}

bool canonical_resref(const std::array<char, 8>& value) noexcept {
  bool sawCharacter = false;
  bool sawPadding = false;
  for (const char character : value) {
    if (character == '\0') {
      sawPadding = true;
      continue;
    }
    const auto byte = static_cast<unsigned char>(character);
    if (sawPadding || byte < 0x21 || byte > 0x7E ||
        (std::isalpha(byte) && !std::isupper(byte))) return false;
    sawCharacter = true;
  }
  return sawCharacter;
}

std::string record_name(const Record& record) {
  std::size_t length = 0;
  while (length < record.resref.size() && record.resref[length] != '\0') ++length;
  return std::string(record.resref.data(), length) + ":" +
         std::to_string(record.sequence) + ":" + std::to_string(record.slot);
}

bool parse_pack(std::vector<std::byte> bytes, std::vector<Record>& records,
                std::unordered_map<Key, std::uint32_t, KeyHash>& lookup,
                std::unordered_map<std::array<char, 8>, std::uint16_t, ResrefHash>& sequenceCounts,
                std::unordered_map<Key, std::uint16_t, KeyHash>& cycleSizes) {
  if (bytes.size() < kHeaderBytes || bytes.size() > kMaximumPackBytes ||
      std::memcmp(bytes.data(), kMagic.data(), kMagic.size()) != 0) return false;
  std::uint32_t version = 0, scale = 0, recordCount = 0, recordBytes = 0;
  std::uint64_t dataOffset = 0, fileBytes = 0;
  if (!read_le(bytes, 8, version) || !read_le(bytes, 12, scale) ||
      !read_le(bytes, 16, recordCount) || !read_le(bytes, 20, recordBytes) ||
      !read_le(bytes, 24, dataOffset) || !read_le(bytes, 32, fileBytes) ||
      version != kVersion || scale != kScale || recordBytes != kRecordBytes ||
      recordCount == 0 || recordCount > kMaximumRecords || fileBytes != bytes.size() ||
      dataOffset != kHeaderBytes + static_cast<std::uint64_t>(recordCount) * kRecordBytes ||
      dataOffset > bytes.size()) return false;

  records.clear();
  lookup.clear();
  sequenceCounts.clear();
  cycleSizes.clear();
  records.reserve(recordCount);
  lookup.reserve(recordCount);
  std::uint64_t expectedDataOffset = dataOffset;
  for (std::uint32_t index = 0; index < recordCount; ++index) {
    const std::size_t base = kHeaderBytes + static_cast<std::size_t>(index) * kRecordBytes;
    Record record;
    std::memcpy(record.resref.data(), bytes.data() + base, record.resref.size());
    std::uint32_t reserved = 0;
    if (!read_le(bytes, base + 8, record.sequence) || !read_le(bytes, base + 10, record.slot) ||
        !read_le(bytes, base + 12, record.sourceWidth) ||
        !read_le(bytes, base + 14, record.sourceHeight) ||
        !read_le(bytes, base + 16, record.replacementWidth) ||
        !read_le(bytes, base + 18, record.replacementHeight) ||
        !read_le(bytes, base + 20, record.globalFrame) ||
        !read_le(bytes, base + 24, record.dataOffset) ||
        !read_le(bytes, base + 32, record.dataBytes) || !read_le(bytes, base + 36, reserved)) {
      return false;
    }
    const auto expectedBytes = static_cast<std::uint64_t>(record.replacementWidth) *
                               record.replacementHeight * 4ull;
    if (!canonical_resref(record.resref) || reserved != 0 ||
        record.sequence == (std::numeric_limits<std::uint16_t>::max)() ||
        record.slot == (std::numeric_limits<std::uint16_t>::max)() ||
        record.sourceWidth == 0 ||
        record.sourceHeight == 0 || record.replacementWidth != record.sourceWidth * kScale ||
        record.replacementHeight != record.sourceHeight * kScale ||
        record.dataBytes != expectedBytes || record.dataOffset != expectedDataOffset ||
        record.dataOffset > bytes.size() || bytes.size() - record.dataOffset < record.dataBytes) {
      return false;
    }
    expectedDataOffset += record.dataBytes;
    const Key key{record.resref, record.sequence, record.slot};
    if (!lookup.emplace(key, index).second) return false;
    auto& sequenceCount = sequenceCounts[record.resref];
    sequenceCount = (std::max)(sequenceCount, static_cast<std::uint16_t>(record.sequence + 1));
    auto& cycleSize = cycleSizes[{record.resref, record.sequence, 0}];
    cycleSize = (std::max)(cycleSize, static_cast<std::uint16_t>(record.slot + 1));
    records.push_back(record);
  }
  if (expectedDataOffset != bytes.size()) return false;
  for (const auto& [cycle, size] : cycleSizes) {
    for (std::uint16_t slot = 0; slot < size; ++slot) {
      if (!lookup.contains({cycle.resref, cycle.sequence, slot})) return false;
    }
  }
  g_pack = std::move(bytes);
  return true;
}

int logical_texture_id(const EngineTextureApi& api) noexcept {
  std::uint32_t state = 0;
  if (!api.glTextureState || !core::safe_read(api.glTextureState, state)) return 0;
  return static_cast<int>((state >> 21u) & 0x1FFu);
}

void clear_texture_cache_locked() noexcept {
  g_textureCache.clear();
  g_textureUseCounter = 0;
}

bool upload_frame_locked(const Record& frame, int textureId, const EngineTextureApi& api,
                         int previousTextureId) noexcept {
  auto& gl = game::gl::get_gl_functions();
  if ((!gl.valid && !gl.initialize()) || !gl.glGetIntegerv || !gl.glTexImage2D ||
      !gl.glTexParameteri || !gl.glPixelStorei || !gl.glGetTexLevelParameteriv ||
      !gl.glGetError || frame.dataOffset > g_pack.size() ||
      g_pack.size() - frame.dataOffset < frame.dataBytes) return false;
  int alignment = 4, rowLength = 0, skipRows = 0, skipPixels = 0, unpackBuffer = 0;
  gl.glGetIntegerv(game::gl::UNPACK_ALIGNMENT, &alignment);
  gl.glGetIntegerv(game::gl::UNPACK_ROW_LENGTH, &rowLength);
  gl.glGetIntegerv(game::gl::UNPACK_SKIP_ROWS, &skipRows);
  gl.glGetIntegerv(game::gl::UNPACK_SKIP_PIXELS, &skipPixels);
  gl.glGetIntegerv(game::gl::PIXEL_UNPACK_BUFFER_BINDING, &unpackBuffer);
  game::gl::discard_errors();
  if (unpackBuffer != 0) return false;
  const auto restore = [&] {
    gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, alignment);
    gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH, rowLength);
    gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS, skipRows);
    gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS, skipPixels);
    api.DrawBindTexture(previousTextureId);
  };
  gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, 1);
  gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH, 0);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS, 0);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS, 0);
  api.DrawBindTexture(textureId);
  api.TexImage(frame.sourceWidth, frame.sourceHeight, nullptr, 0);
  int boundTexture = 0;
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &boundTexture);
  if (boundTexture <= 0 || gl.glGetError() != game::gl::GL_NO_ERROR) {
    restore();
    return false;
  }
  gl.glTexImage2D(game::gl::TEXTURE_2D, 0, static_cast<int>(game::gl::RGBA8),
                  frame.replacementWidth, frame.replacementHeight, 0, game::gl::RGBA,
                  game::gl::UNSIGNED_BYTE, g_pack.data() + frame.dataOffset);
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_S,
                     static_cast<int>(game::gl::CLAMP_TO_EDGE));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_T,
                     static_cast<int>(game::gl::CLAMP_TO_EDGE));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MIN_FILTER,
                     static_cast<int>(game::gl::LINEAR));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER,
                     static_cast<int>(game::gl::LINEAR));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAX_LEVEL, 0);
  int width = 0, height = 0;
  gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_WIDTH, &width);
  gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_HEIGHT, &height);
  const bool success = width == frame.replacementWidth && height == frame.replacementHeight &&
                       gl.glGetError() == game::gl::GL_NO_ERROR;
  restore();
  return success;
}

}  // namespace

bool prepare(const std::filesystem::path& assetsDirectory) noexcept {
  try {
    const auto path = assetsDirectory / "ItemIcons-X2.registry";
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file || file.tellg() <= 0 || static_cast<std::uint64_t>(file.tellg()) > kMaximumPackBytes) {
      LOG_WARN("Item icon x2 disabled: missing or oversized {}", path.string());
      return false;
    }
    std::vector<std::byte> bytes(static_cast<std::size_t>(file.tellg()));
    file.seekg(0);
    if (!file.read(reinterpret_cast<char*>(bytes.data()),
                   static_cast<std::streamsize>(bytes.size()))) return false;
    std::vector<Record> records;
    std::unordered_map<Key, std::uint32_t, KeyHash> lookup;
    std::unordered_map<std::array<char, 8>, std::uint16_t, ResrefHash> sequenceCounts;
    std::unordered_map<Key, std::uint16_t, KeyHash> cycleSizes;
    std::lock_guard lock(g_mutex);
    g_ready.store(false, std::memory_order_release);
    g_pack.clear();
    if (!parse_pack(std::move(bytes), records, lookup, sequenceCounts, cycleSizes)) {
      LOG_WARN("Item icon x2 disabled: malformed v2 registry {}", path.string());
      return false;
    }
    g_records = std::move(records);
    g_lookup = std::move(lookup);
    g_sequenceCounts = std::move(sequenceCounts);
    g_cycleSizes = std::move(cycleSizes);
    clear_texture_cache_locked();
    g_loggedRecords.assign(g_records.size(), false);
    g_detailedLogs = 0;
#ifdef _WIN32
    g_textureContext = nullptr;
#endif
    g_ready.store(true, std::memory_order_release);
    LOG_INFO("Prepared item icon x2 registry v2: {} cycle slots, {} MiB", g_records.size(),
             g_pack.size() / (1024 * 1024));
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("Item icon x2 disabled: {}", error.what());
  } catch (...) {
    LOG_WARN("Item icon x2 disabled by an unknown loading error");
  }
  return false;
}

void release() noexcept {
  std::lock_guard lock(g_mutex);
  g_ready.store(false, std::memory_order_release);
  clear_texture_cache_locked();
  g_cycleSizes.clear();
  g_sequenceCounts.clear();
  g_lookup.clear();
  g_records.clear();
  g_pack.clear();
  g_pack.shrink_to_fit();
  g_loggedRecords.clear();
  g_detailedLogs = 0;
#ifdef _WIN32
  g_textureContext = nullptr;
#endif
}

bool ready() noexcept { return g_ready.load(std::memory_order_acquire); }

bool resolve_frame(const std::array<char, 8>& resref, int sequence, int currentFrame,
                   int playbackMode, int logicalWidth, int logicalHeight,
                   FrameHandle& out) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || logicalWidth <= 0 || logicalHeight <= 0) return false;
  std::lock_guard lock(g_mutex);
  const auto sequenceCount = g_sequenceCounts.find(resref);
  if (sequenceCount == g_sequenceCounts.end() || sequenceCount->second == 0) return false;
  if (sequence < 0 || sequence >= sequenceCount->second) sequence = 0;
  const Key cycle{resref, static_cast<std::uint16_t>(sequence), 0};
  const auto cycleSizeIt = g_cycleSizes.find(cycle);
  if (cycleSizeIt == g_cycleSizes.end() || cycleSizeIt->second == 0) return false;
  const int cycleSize = cycleSizeIt->second;
  int slot = currentFrame;
  if (slot >= cycleSize) slot = playbackMode != 0 ? slot % cycleSize : cycleSize - 1;
  if (slot < 0) slot = playbackMode != 0 ? ((slot % cycleSize) + cycleSize) % cycleSize : 0;
  const auto found = g_lookup.find(
      {resref, static_cast<std::uint16_t>(sequence), static_cast<std::uint16_t>(slot)});
  if (found == g_lookup.end() || found->second >= g_records.size()) return false;
  const auto& record = g_records[found->second];
  if (record.sourceWidth != logicalWidth || record.sourceHeight != logicalHeight) return false;
  out.recordIndex = found->second;
  return true;
}

bool bind_frame_texture(FrameHandle handle, int logicalWidth, int logicalHeight,
                        const EngineTextureApi& api, int& previousTextureId) noexcept {
  previousTextureId = 0;
  if (!g_ready.load(std::memory_order_acquire) || !api.DrawGenTexture ||
      !api.DrawBindTexture || !api.DrawDeleteTexture || !api.TexImage ||
      !api.DrawGetRenderer || !api.glTextureState || api.DrawGetRenderer() == 1) return false;
  try {
    std::lock_guard lock(g_mutex);
    if (handle.recordIndex >= g_records.size()) return false;
    const auto& record = g_records[handle.recordIndex];
    if (record.sourceWidth != logicalWidth || record.sourceHeight != logicalHeight) return false;
#ifdef _WIN32
    const auto context = game::gl::current_context();
    if (!context) return false;
    if (g_textureContext != context) {
      clear_texture_cache_locked();
      std::fill(g_loggedRecords.begin(), g_loggedRecords.end(), false);
      g_textureContext = context;
    }
#endif
    previousTextureId = logical_texture_id(api);
    if (previousTextureId <= 0) return false;
    auto found = std::find_if(g_textureCache.begin(), g_textureCache.end(),
                              [&](const TextureEntry& entry) { return entry.handle == handle; });
    if (found == g_textureCache.end()) {
      if (g_textureCache.size() < kTextureCacheLimit) {
        const int generated = api.DrawGenTexture(static_cast<int>(game::gl::LINEAR), 0, 0, 0);
        if (generated <= 0) return false;
        g_textureCache.push_back({handle, generated, 0});
        found = std::prev(g_textureCache.end());
      } else {
        found = std::min_element(g_textureCache.begin(), g_textureCache.end(),
                                 [](const TextureEntry& left, const TextureEntry& right) {
                                   return left.lastUse < right.lastUse;
                                 });
        found->handle = handle;
      }
      if (!upload_frame_locked(record, found->textureId, api, previousTextureId)) {
        api.DrawDeleteTexture(found->textureId);
        g_textureCache.erase(found);
        api.DrawBindTexture(previousTextureId);
        return false;
      }
    }
    found->lastUse = ++g_textureUseCounter;
    api.DrawBindTexture(found->textureId);
    if (!g_loggedRecords[handle.recordIndex]) {
      g_loggedRecords[handle.recordIndex] = true;
      if (g_detailedLogs++ < kMaximumDetailedLogs) {
        LOG_INFO("Composing item icon {} (global frame {}): logical {}x{}, physical {}x{}",
                 record_name(record), record.globalFrame, record.sourceWidth, record.sourceHeight,
                 record.replacementWidth, record.replacementHeight);
      }
    }
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("Item icon x2 composition failed: {}", error.what());
  } catch (...) {
    LOG_WARN("Item icon x2 composition failed with an unknown error");
  }
  return false;
}

void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept {
  if (api.DrawBindTexture && previousTextureId > 0) api.DrawBindTexture(previousTextureId);
}

void forget_engine_textures() noexcept {
  std::lock_guard lock(g_mutex);
  clear_texture_cache_locked();
  std::fill(g_loggedRecords.begin(), g_loggedRecords.end(), false);
#ifdef _WIN32
  g_textureContext = nullptr;
#endif
}

}  // namespace iee::item_icon_x2
