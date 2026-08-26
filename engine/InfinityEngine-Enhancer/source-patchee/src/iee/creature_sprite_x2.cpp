#include "creature_sprite_x2.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <cctype>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstring>
#include <exception>
#include <fstream>
#include <iterator>
#include <limits>
#include <mutex>
#include <deque>
#include <set>
#include <stdexcept>
#include <string>
#include <system_error>
#include <thread>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#include <compressapi.h>
#endif

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
constexpr std::array<char, 8> kRegistrySetMagic{
    {'I', 'E', 'E', 'C', 'S', 'N', 'S', '\0'}};
constexpr std::array<char, 8> kRegistryCatalogMagic{
    {'I', 'E', 'E', 'C', 'S', 'N', 'C', '\0'}};
constexpr std::uint32_t kLegacyRegistryVersion = 1;
constexpr std::uint32_t kLegacyCurrentRegistryVersion = 2;
constexpr std::uint32_t kXnRegistryVersion = 3;
constexpr std::uint32_t kXnAntialiasRegistryVersion = 4;
constexpr std::uint32_t kXnCompressedRegistryVersion = 5;
constexpr std::uint32_t kRegistrySetVersion = 1;
constexpr std::uint32_t kRegistryCatalogVersion = 1;
constexpr std::uint32_t kRegistryCatalogDirectoryVersion = 2;
constexpr std::uint32_t kCatalogCharacterOwner = 1;
constexpr std::uint32_t kCatalogMonsterIcewindOwner = 2;
constexpr std::uint32_t kCatalogMonsterOwner = 3;
constexpr std::uint16_t kCatalogShardAnimationSentinel = 0xFFFFu;
constexpr std::uint16_t kLegacyMgo1AnimationId = 0xE400;
constexpr char kLegacyRegistryFilename[] = "CreatureSprites-X2.registry";
constexpr char kXnRegistryFilename[] = "CreatureSprites-XN.registry";
constexpr char kRegistrySetFilename[] = "CreatureSprites-XN.set";
constexpr char kRegistryCatalogFilename[] = "CreatureSprites-XN.catalog";
constexpr std::size_t kRegistrySetHeaderBytes = 56;
constexpr std::size_t kRegistrySetEntryBytes = 64;
constexpr std::size_t kRegistryCatalogHeaderBytes = 64;
constexpr std::size_t kRegistryCatalogDirectoryHeaderBytes = 104;
constexpr std::size_t kRegistryCatalogAnimationBytes = 16;
constexpr std::size_t kRegistryCatalogMembershipBytes = 4;
constexpr std::size_t kRegistryCatalogComponentBytes = 72;
constexpr std::size_t kRegistryCatalogShardBytes = 64;
constexpr std::size_t kRegistryCatalogDirectoryEntryBytes = 24;
constexpr std::size_t kMaximumRegistryCatalogBytes =
    kRegistryCatalogHeaderBytes +
    static_cast<std::size_t>(kMaximumCatalogAnimations) *
        kRegistryCatalogAnimationBytes +
    static_cast<std::size_t>(kMaximumCatalogMemberships) *
        kRegistryCatalogMembershipBytes +
    static_cast<std::size_t>(kMaximumCatalogComponents) *
        kRegistryCatalogComponentBytes +
    static_cast<std::size_t>(kMaximumCatalogShards) *
        kRegistryCatalogShardBytes;
static_assert(kMaximumRegistryCatalogBytes == 3'285'056);
constexpr std::size_t kMaximumRegistryCatalogDirectoryBytes =
    kRegistryCatalogDirectoryHeaderBytes +
    static_cast<std::size_t>(kMaximumCatalogAnimations) *
        kRegistryCatalogAnimationBytes +
    static_cast<std::size_t>(kMaximumCatalogMemberships) *
        kRegistryCatalogMembershipBytes +
    static_cast<std::size_t>(kMaximumCatalogComponents) *
        kRegistryCatalogComponentBytes +
    static_cast<std::size_t>(kMaximumCatalogShards) *
        kRegistryCatalogShardBytes +
    static_cast<std::size_t>(kMaximumCatalogDirectoryEntries) *
        kRegistryCatalogDirectoryEntryBytes;
static_assert(kMaximumRegistryCatalogDirectoryBytes == 28'450'920);
constexpr std::uint32_t kResidentFrameShard =
    (std::numeric_limits<std::uint32_t>::max)();
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
  // V4 monoliths retain a compact ordered stream of xBR blend operations.
  // V2/V3 frames leave this empty and keep their original index-only path.
  std::vector<std::uint8_t> blendRecipes;
  bool antialias{};
  std::uint32_t lazyShardIndex{kResidentFrameShard};
  std::uint64_t lazyIndexOffset{};
  // The cache and all aggregate index-byte accounting use the logical,
  // decompressed length. Only the bounded read uses lazyStoredBytes.
  std::uint32_t lazyIndexBytes{};
  std::uint32_t lazyStoredBytes{};
  std::uint8_t lazyCompressionCodec{kRegistryFrameCodecRaw};
  // The complete shard is SHA-256/CRC-32 validated before its metadata is
  // accepted. Retain a per-frame digest so a later lazy read cannot substitute
  // payload bytes while preserving the file's size and timestamp.
  std::array<std::byte, 32> lazyIndexSha256{};
  bool lazyIndexDigestValid{};
};

struct Resource {
  std::array<char, 8> resref{};
  std::array<std::byte, 32> sourceSha256{};
  std::vector<Frame> frames;
  std::vector<std::vector<std::uint32_t>> cycles;
  // QA needs one proof per animation/resref, not one synchronous disk flush per
  // frame. Keep this bounded to the animations sharing the resource.
  std::set<std::uint16_t> compositionLogged;
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

struct FileIdentity {
  std::uint64_t bytes{};
  std::uint64_t writeStamp{};

  [[nodiscard]] constexpr bool operator==(const FileIdentity&) const noexcept = default;
};

struct ReadLease {
#ifdef _WIN32
  HANDLE handle{INVALID_HANDLE_VALUE};

  ReadLease() noexcept = default;
  ReadLease(const ReadLease&) = delete;
  ReadLease& operator=(const ReadLease&) = delete;
  ReadLease(ReadLease&& other) noexcept
      : handle(std::exchange(other.handle, INVALID_HANDLE_VALUE)) {}
  ReadLease& operator=(ReadLease&& other) noexcept {
    if (this != &other) {
      reset();
      handle = std::exchange(other.handle, INVALID_HANDLE_VALUE);
    }
    return *this;
  }
  ~ReadLease() noexcept { reset(); }

  [[nodiscard]] bool valid() const noexcept {
    return handle != nullptr && handle != INVALID_HANDLE_VALUE;
  }
  void reset() noexcept {
    if (valid()) CloseHandle(handle);
    handle = INVALID_HANDLE_VALUE;
  }
#else
  [[nodiscard]] constexpr bool valid() const noexcept { return false; }
  void reset() noexcept {}
#endif
};

struct CatalogShardEntry {
  std::array<std::byte, kRegistryCatalogShardBytes> encoded{};
  std::array<std::byte, 32> sha256{};
  std::uint32_t checksum{};
  std::uint32_t resourceCount{};
  std::uint64_t frameCount{};
  std::uint64_t indexBytes{};
  std::uint64_t registryBytes{};
  std::filesystem::path path;
  FileIdentity identity{};
  std::uint32_t componentIndex{};
  std::vector<std::array<char, 8>> directory;
  std::vector<std::size_t> resourceIndices;
  std::uint64_t residentMetadataBytes{};
  std::uint64_t lastUse{};
  std::uint64_t generation{};
  enum class Status : std::uint8_t {
    Unprobed,
    DirectoryReady,
    Loading,
    Resident,
    Quarantined,
  } status{Status::Unprobed};
  bool failureLogged{};
};

struct CatalogComponent {
  std::array<std::byte, 32> digest{};
  std::uint32_t shardStart{};
  std::uint32_t shardCount{};
  std::uint32_t resourceCount{};
  std::uint64_t frameCount{};
  std::uint64_t indexBytes{};
  std::uint64_t registryBytes{};
  bool quarantined{};
  bool failureLogged{};
};

struct CatalogAnimation {
  std::uint16_t animationId{};
  std::uint32_t owner{};
  std::uint32_t membershipStart{};
  std::uint32_t membershipCount{};
  std::vector<std::size_t> resourceIndices;
  bool loaded{};
};

struct CatalogDirectoryEntry {
  std::uint16_t animationId{};
  std::array<char, 8> resref{};
  std::uint32_t componentIndex{};
  std::uint32_t shardIndex{};
  std::uint32_t resourceOrdinal{};
};

struct CatalogState {
  bool active{};
  std::uint32_t version{};
  std::filesystem::path path;
  FileIdentity identity{};
  ReadLease lease;
  std::uint32_t scale{};
  std::uint64_t resourceCount{};
  std::uint64_t frameCount{};
  std::uint64_t indexBytes{};
  std::uint64_t registryBytes{};
  std::vector<CatalogAnimation> animations;
  std::vector<std::uint32_t> memberships;
  std::vector<CatalogComponent> components;
  std::vector<CatalogShardEntry> shards;
  std::vector<CatalogDirectoryEntry> directory;
  std::uint64_t epoch{};
};

struct CatalogLoadRequest {
  std::uint16_t animationId{};
  std::array<char, 8> resref{};

  [[nodiscard]] constexpr bool operator==(const CatalogLoadRequest&) const noexcept = default;
};

struct LazyShard {
  std::filesystem::path path;
  FileIdentity identity{};
  ReadLease lease;
};

struct LazyIndexCacheEntry {
  FrameHandle handle{};
  std::vector<std::uint8_t> indices;
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

  bool read_view(const std::byte*& out, std::size_t byteCount) noexcept {
    out = nullptr;
    if (offset_ > bytes_.size() || byteCount > bytes_.size() - offset_) return false;
    out = bytes_.data() + offset_;
    offset_ += byteCount;
    return true;
  }

  [[nodiscard]] std::size_t position() const noexcept { return offset_; }
  [[nodiscard]] std::size_t size() const noexcept { return bytes_.size(); }

  [[nodiscard]] bool at_end() const noexcept { return offset_ == bytes_.size(); }

 private:
  std::vector<std::byte> bytes_;
  std::size_t offset_{};
};

std::mutex g_mutex;
std::atomic<bool> g_ready{false};
std::atomic<std::uint16_t> g_targetAnimationId{0};
std::atomic<std::uint32_t> g_loadedScale{0};
std::atomic<bool> g_targetsCharacter{false};
std::atomic<bool> g_targetsMonster{false};
std::atomic<bool> g_targetsMonsterIcewind{false};
std::atomic<bool> g_linearFiltering{false};
std::vector<Resource> g_resources;
std::vector<CatalogAnimation> g_packAnimations;
CatalogState g_catalog;
std::vector<TextureCacheEntry> g_textureCache;
std::vector<CompositePixelCacheEntry> g_compositePixelCache;
std::vector<LazyShard> g_lazyShards;
std::vector<LazyIndexCacheEntry> g_lazyIndexCache;
std::uint64_t g_textureUseCounter{};
std::uint64_t g_lazyIndexUseCounter{};
std::uint64_t g_catalogMetadataUseCounter{};
std::uint64_t g_catalogEpochCounter{};
bool g_lazyPackLoaded{};
bool g_lazyPackFailureLogged{};
bool g_creationFailureLogged{};
bool g_dimensionMismatchLogged{};
bool g_compositeDimensionMismatchLogged{};
bool g_rendererFailureLogged{};
bool g_contextFailureLogged{};
bool g_sourceTextureFailureLogged{};
std::atomic<bool> g_paletteApiFailureLogged{false};
std::atomic<bool> g_realizedPaletteLogged{false};
std::atomic<std::uint64_t> g_filesystemAccessCounter{0};
bool g_compositeBackingFailureLogged{};
#ifdef _WIN32
HGLRC g_textureContext{};
DECOMPRESSOR_HANDLE g_xpressHuffDecompressor{};
#endif
std::deque<CatalogLoadRequest> g_catalogLoadQueue;
std::set<std::pair<std::uint16_t, std::array<char, 8>>>
    g_catalogPendingRequests;
std::condition_variable_any g_catalogWorkChanged;
std::jthread g_catalogWorker;

void quarantine_catalog_component_locked(std::uint32_t componentIndex,
                                         const char* reason) noexcept;

[[nodiscard]] int sampling_filter() noexcept {
  return static_cast<int>(g_linearFiltering.load(std::memory_order_acquire)
                              ? game::gl::LINEAR
                              : game::gl::NEAREST);
}

[[nodiscard]] const char* sampling_filter_name() noexcept {
  return g_linearFiltering.load(std::memory_order_acquire) ? "LINEAR" : "NEAREST";
}

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

bool query_file_identity(const std::filesystem::path& path,
                         FileIdentity& out) noexcept {
  out = {};
  g_filesystemAccessCounter.fetch_add(1, std::memory_order_relaxed);
#ifdef _WIN32
  WIN32_FILE_ATTRIBUTE_DATA attributes{};
  if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &attributes) ||
      (attributes.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0) {
    return false;
  }
  out.bytes = (static_cast<std::uint64_t>(attributes.nFileSizeHigh) << 32u) |
              attributes.nFileSizeLow;
  out.writeStamp =
      (static_cast<std::uint64_t>(attributes.ftLastWriteTime.dwHighDateTime) << 32u) |
      attributes.ftLastWriteTime.dwLowDateTime;
  return true;
#else
  std::error_code error;
  const auto bytes = std::filesystem::file_size(path, error);
  if (error) return false;
  const auto writeTime = std::filesystem::last_write_time(path, error);
  if (error) return false;
  out.bytes = static_cast<std::uint64_t>(bytes);
  out.writeStamp = static_cast<std::uint64_t>(writeTime.time_since_epoch().count());
  return true;
#endif
}

#ifdef _WIN32
bool query_open_file_identity(HANDLE handle, FileIdentity& out) noexcept {
  out = {};
  BY_HANDLE_FILE_INFORMATION information{};
  if (!handle || handle == INVALID_HANDLE_VALUE ||
      !GetFileInformationByHandle(handle, &information) ||
      (information.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0) {
    return false;
  }
  out.bytes = (static_cast<std::uint64_t>(information.nFileSizeHigh) << 32u) |
              information.nFileSizeLow;
  out.writeStamp =
      (static_cast<std::uint64_t>(information.ftLastWriteTime.dwHighDateTime)
       << 32u) |
      information.ftLastWriteTime.dwLowDateTime;
  return true;
}
#endif

std::vector<std::byte> read_file(const std::filesystem::path& path,
                                 std::uint64_t maximumBytes,
                                 FileIdentity* identity = nullptr,
                                 ReadLease* retainedLease = nullptr) {
#ifdef _WIN32
  if (retainedLease) {
    retainedLease->reset();
    ReadLease opened;
    g_filesystemAccessCounter.fetch_add(1, std::memory_order_relaxed);
    opened.handle = CreateFileW(
        path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN, nullptr);
    FileIdentity initialIdentity{};
    if (!opened.valid() ||
        !query_open_file_identity(opened.handle, initialIdentity) ||
        initialIdentity.bytes == 0 || initialIdentity.bytes > maximumBytes ||
        initialIdentity.bytes >
            static_cast<std::uint64_t>((std::numeric_limits<std::size_t>::max)())) {
      throw std::runtime_error("invalid creature-sprite registry size: " +
                               path.string());
    }
    std::vector<std::byte> bytes(
        static_cast<std::size_t>(initialIdentity.bytes));
    std::size_t offset = 0;
    while (offset < bytes.size()) {
      const auto chunk = static_cast<DWORD>((std::min)(
          bytes.size() - offset,
          static_cast<std::size_t>((std::numeric_limits<DWORD>::max)())));
      DWORD read = 0;
      if (!ReadFile(opened.handle, bytes.data() + offset, chunk, &read,
                    nullptr) ||
          read != chunk) {
        throw std::runtime_error("cannot read creature-sprite registry");
      }
      offset += read;
    }
    FileIdentity finalIdentity{};
    if (!query_open_file_identity(opened.handle, finalIdentity) ||
        finalIdentity != initialIdentity) {
      throw std::runtime_error("creature-sprite registry changed while reading");
    }
    if (identity) *identity = finalIdentity;
    *retainedLease = std::move(opened);
    return bytes;
  }
#else
  (void)retainedLease;
#endif
  FileIdentity initialIdentity{};
  if (!query_file_identity(path, initialIdentity) || initialIdentity.bytes == 0 ||
      initialIdentity.bytes > maximumBytes) {
    throw std::runtime_error("invalid creature-sprite registry size: " + path.string());
  }
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file) throw std::runtime_error("missing creature-sprite registry: " + path.string());
  const auto end = file.tellg();
  if (end <= 0 || static_cast<std::uint64_t>(end) != initialIdentity.bytes) {
    throw std::runtime_error("creature-sprite registry changed while opening");
  }
  file.seekg(0);
  std::vector<std::byte> bytes(static_cast<std::size_t>(end));
  if (!file.read(reinterpret_cast<char*>(bytes.data()),
                 static_cast<std::streamsize>(bytes.size()))) {
    throw std::runtime_error("cannot read creature-sprite registry");
  }
  FileIdentity finalIdentity{};
  if (!query_file_identity(path, finalIdentity) || finalIdentity != initialIdentity) {
    throw std::runtime_error("creature-sprite registry changed while reading");
  }
  if (identity) *identity = finalIdentity;
  return bytes;
}

std::uint32_t crc32(const std::vector<std::byte>& bytes) noexcept {
  static const auto table = [] {
    std::array<std::uint32_t, 256> values{};
    for (std::uint32_t index = 0; index < values.size(); ++index) {
      auto value = index;
      for (unsigned bit = 0; bit < 8; ++bit) {
        value = (value >> 1u) ^ (0xEDB88320u & (0u - (value & 1u)));
      }
      values[index] = value;
    }
    return values;
  }();
  std::uint32_t value = 0xFFFFFFFFu;
  for (const auto byte : bytes) {
    value = table[(value ^ std::to_integer<std::uint8_t>(byte)) & 0xFFu] ^
            (value >> 8u);
  }
  return value ^ 0xFFFFFFFFu;
}

std::array<std::byte, 32> sha256_bytes(const std::byte* bytes,
                                      std::size_t byteCount) noexcept {
  constexpr std::array<std::uint32_t, 64> constants{{
      0x428A2F98u, 0x71374491u, 0xB5C0FBCFu, 0xE9B5DBA5u, 0x3956C25Bu,
      0x59F111F1u, 0x923F82A4u, 0xAB1C5ED5u, 0xD807AA98u, 0x12835B01u,
      0x243185BEu, 0x550C7DC3u, 0x72BE5D74u, 0x80DEB1FEu, 0x9BDC06A7u,
      0xC19BF174u, 0xE49B69C1u, 0xEFBE4786u, 0x0FC19DC6u, 0x240CA1CCu,
      0x2DE92C6Fu, 0x4A7484AAu, 0x5CB0A9DCu, 0x76F988DAu, 0x983E5152u,
      0xA831C66Du, 0xB00327C8u, 0xBF597FC7u, 0xC6E00BF3u, 0xD5A79147u,
      0x06CA6351u, 0x14292967u, 0x27B70A85u, 0x2E1B2138u, 0x4D2C6DFCu,
      0x53380D13u, 0x650A7354u, 0x766A0ABBu, 0x81C2C92Eu, 0x92722C85u,
      0xA2BFE8A1u, 0xA81A664Bu, 0xC24B8B70u, 0xC76C51A3u, 0xD192E819u,
      0xD6990624u, 0xF40E3585u, 0x106AA070u, 0x19A4C116u, 0x1E376C08u,
      0x2748774Cu, 0x34B0BCB5u, 0x391C0CB3u, 0x4ED8AA4Au, 0x5B9CCA4Fu,
      0x682E6FF3u, 0x748F82EEu, 0x78A5636Fu, 0x84C87814u, 0x8CC70208u,
      0x90BEFFFAu, 0xA4506CEBu, 0xBEF9A3F7u, 0xC67178F2u,
  }};
  std::array<std::uint32_t, 8> state{{
      0x6A09E667u, 0xBB67AE85u, 0x3C6EF372u, 0xA54FF53Au,
      0x510E527Fu, 0x9B05688Cu, 0x1F83D9ABu, 0x5BE0CD19u,
  }};
  const auto rotateRight = [](std::uint32_t value, unsigned count) noexcept {
    return (value >> count) | (value << (32u - count));
  };
  const auto transform = [&](const std::uint8_t* block) noexcept {
    std::array<std::uint32_t, 64> words{};
    for (std::size_t index = 0; index < 16; ++index) {
      const auto offset = index * 4;
      words[index] = (static_cast<std::uint32_t>(block[offset]) << 24u) |
                     (static_cast<std::uint32_t>(block[offset + 1]) << 16u) |
                     (static_cast<std::uint32_t>(block[offset + 2]) << 8u) |
                     static_cast<std::uint32_t>(block[offset + 3]);
    }
    for (std::size_t index = 16; index < words.size(); ++index) {
      const auto s0 = rotateRight(words[index - 15], 7) ^
                      rotateRight(words[index - 15], 18) ^
                      (words[index - 15] >> 3u);
      const auto s1 = rotateRight(words[index - 2], 17) ^
                      rotateRight(words[index - 2], 19) ^
                      (words[index - 2] >> 10u);
      words[index] = words[index - 16] + s0 + words[index - 7] + s1;
    }
    auto a = state[0];
    auto b = state[1];
    auto c = state[2];
    auto d = state[3];
    auto e = state[4];
    auto f = state[5];
    auto g = state[6];
    auto h = state[7];
    for (std::size_t index = 0; index < words.size(); ++index) {
      const auto sum1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
      const auto choice = (e & f) ^ (~e & g);
      const auto temporary1 = h + sum1 + choice + constants[index] + words[index];
      const auto sum0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
      const auto majority = (a & b) ^ (a & c) ^ (b & c);
      const auto temporary2 = sum0 + majority;
      h = g;
      g = f;
      f = e;
      e = d + temporary1;
      d = c;
      c = b;
      b = a;
      a = temporary1 + temporary2;
    }
    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
    state[4] += e;
    state[5] += f;
    state[6] += g;
    state[7] += h;
  };

  const auto* data = reinterpret_cast<const std::uint8_t*>(bytes);
  std::size_t offset = 0;
  while (byteCount - offset >= 64) {
    transform(data + offset);
    offset += 64;
  }
  std::array<std::uint8_t, 128> tail{};
  const auto remaining = byteCount - offset;
  if (remaining != 0) std::memcpy(tail.data(), data + offset, remaining);
  tail[remaining] = 0x80u;
  const std::size_t tailBytes = remaining < 56 ? 64 : 128;
  const auto bitLength = static_cast<std::uint64_t>(byteCount) * 8u;
  for (unsigned index = 0; index < 8; ++index) {
    tail[tailBytes - 1 - index] =
        static_cast<std::uint8_t>(bitLength >> (index * 8u));
  }
  transform(tail.data());
  if (tailBytes == 128) transform(tail.data() + 64);
  std::array<std::byte, 32> digest{};
  for (std::size_t index = 0; index < state.size(); ++index) {
    for (unsigned byte = 0; byte < 4; ++byte) {
      digest[index * 4 + byte] =
          static_cast<std::byte>(state[index] >> (24u - byte * 8u));
    }
  }
  return digest;
}

std::array<std::byte, 32> sha256(
    const std::vector<std::byte>& bytes) noexcept {
  return sha256_bytes(bytes.data(), bytes.size());
}

bool checked_add(std::uint64_t& total, std::uint64_t value,
                 std::uint64_t maximum) noexcept {
  if (value > maximum || total > maximum - value) return false;
  total += value;
  return true;
}

std::string registry_shard_filename(std::uint32_t index) {
  auto digits = std::to_string(index);
  if (digits.size() > 4) throw std::runtime_error("creature-sprite shard index overflow");
  return "CreatureSprites-XN-" + std::string(4 - digits.size(), '0') + digits +
         ".registry";
}

char uppercase_hex_digit(std::uint8_t value) noexcept {
  return static_cast<char>(value < 10 ? '0' + value : 'A' + (value - 10));
}

std::string catalog_shard_filename(const std::array<std::byte, 32>& digest) {
  std::string filename = "CreatureSprites-XN-";
  filename.reserve(filename.size() + digest.size() * 2 + 9);
  for (const auto value : digest) {
    const auto byte = std::to_integer<std::uint8_t>(value);
    filename.push_back(uppercase_hex_digit(static_cast<std::uint8_t>(byte >> 4u)));
    filename.push_back(uppercase_hex_digit(static_cast<std::uint8_t>(byte & 0x0Fu)));
  }
  filename += ".registry";
  return filename;
}

template <class T, std::size_t N>
T encoded_field(const std::array<std::byte, N>& encoded,
                std::size_t offset) noexcept {
  static_assert(std::is_trivially_copyable_v<T>);
  T value{};
  if (offset <= encoded.size() && sizeof(T) <= encoded.size() - offset) {
    std::memcpy(&value, encoded.data() + offset, sizeof(T));
  }
  return value;
}

std::array<std::byte, 32> catalog_component_digest(
    std::uint32_t scale, const std::vector<CatalogShardEntry>& shards,
    std::uint32_t shardStart, std::uint32_t shardCount) {
  constexpr char kDomain[] = "IEECSNC-COMPONENT-V1";
  std::vector<std::byte> bytes;
  bytes.reserve(sizeof(kDomain) + sizeof(scale) +
                static_cast<std::size_t>(shardCount) *
                    kRegistryCatalogShardBytes);
  for (const auto value : kDomain) {
    bytes.push_back(static_cast<std::byte>(value));
  }
  for (unsigned shift = 0; shift < 32; shift += 8) {
    bytes.push_back(static_cast<std::byte>(scale >> shift));
  }
  for (std::uint32_t index = 0; index < shardCount; ++index) {
    const auto& encoded = shards[shardStart + index].encoded;
    bytes.insert(bytes.end(), encoded.begin(), encoded.end());
  }
  return sha256(bytes);
}

std::array<std::byte, 32> catalog_directory_digest(
    std::uint32_t scale, const std::byte* entries,
    std::size_t entryBytes) {
  constexpr char kDomain[] = "IEECSNC-DIRECTORY-V2";
  std::vector<std::byte> bytes;
  bytes.reserve(sizeof(kDomain) + sizeof(scale) + entryBytes);
  for (const auto value : kDomain) {
    bytes.push_back(static_cast<std::byte>(value));
  }
  for (unsigned shift = 0; shift < 32; shift += 8) {
    bytes.push_back(static_cast<std::byte>(scale >> shift));
  }
  if (entryBytes != 0) bytes.insert(bytes.end(), entries, entries + entryBytes);
  return sha256(bytes);
}

std::string resref_name(const std::array<char, 8>& resref) {
  const auto end = std::find(resref.begin(), resref.end(), '\0');
  return std::string(resref.begin(), end);
}

bool canonical_catalog_resref(const std::array<char, 8>& resref) noexcept {
  bool hasCharacter = false;
  bool terminated = false;
  for (const auto raw : resref) {
    const auto value = static_cast<unsigned char>(raw);
    if (terminated) {
      if (value != 0) return false;
      continue;
    }
    if (value == 0) {
      terminated = true;
      continue;
    }
    if (!((value >= 'A' && value <= 'Z') ||
          (value >= '0' && value <= '9') || value == '_')) {
      return false;
    }
    hasCharacter = true;
  }
  return hasCharacter;
}

bool catalog_owner_matches_animation(std::uint32_t owner,
                                     std::uint32_t animationId) noexcept {
  const auto family = animationId & 0xF000u;
  return (owner == kCatalogCharacterOwner &&
          (family == 0x5000u || family == 0x6000u)) ||
         (owner == kCatalogMonsterIcewindOwner && family == 0xE000u) ||
         (owner == kCatalogMonsterOwner && family == 0x7000u);
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

std::uint64_t lazy_index_cache_bytes_locked() noexcept {
  std::uint64_t total = 0;
  for (const auto& entry : g_lazyIndexCache) {
    if (!checked_add(total, static_cast<std::uint64_t>(entry.indices.size()),
                     kLazyIndexCacheBudgetBytes)) {
      return (std::numeric_limits<std::uint64_t>::max)();
    }
  }
  return total;
}

void clear_lazy_index_cache_locked() noexcept {
  g_lazyIndexCache.clear();
  g_lazyIndexUseCounter = 0;
}

bool decompress_xpress_huff_locked(
    const std::vector<std::uint8_t>& stored,
    std::vector<std::uint8_t>& logical) noexcept {
#ifdef _WIN32
  if (stored.empty() || logical.empty()) return false;
  if (!g_xpressHuffDecompressor &&
      !CreateDecompressor(COMPRESS_ALGORITHM_XPRESS_HUFF, nullptr,
                          &g_xpressHuffDecompressor)) {
    return false;
  }
  SIZE_T written = 0;
  if (Decompress(g_xpressHuffDecompressor, stored.data(), stored.size(),
                 logical.data(), logical.size(), &written) &&
      written == logical.size()) {
    return true;
  }
  // A malformed stream must not leave reusable codec state behind. The next
  // independently authenticated component gets a fresh decoder.
  CloseDecompressor(g_xpressHuffDecompressor);
  g_xpressHuffDecompressor = nullptr;
#else
  (void)stored;
  (void)logical;
#endif
  return false;
}

void close_frame_decompressor_locked() noexcept {
#ifdef _WIN32
  if (g_xpressHuffDecompressor) {
    CloseDecompressor(g_xpressHuffDecompressor);
    g_xpressHuffDecompressor = nullptr;
  }
#endif
}

void disable_lazy_pack_locked(const char* reason) noexcept {
  g_ready.store(false, std::memory_order_release);
  g_targetAnimationId.store(0, std::memory_order_release);
  g_loadedScale.store(0, std::memory_order_release);
  g_targetsCharacter.store(false, std::memory_order_release);
  g_targetsMonster.store(false, std::memory_order_release);
  g_targetsMonsterIcewind.store(false, std::memory_order_release);
  clear_texture_cache_locked();
  clear_lazy_index_cache_locked();
  close_frame_decompressor_locked();
  g_catalog.lease.reset();
  for (auto& shard : g_lazyShards) shard.lease.reset();
  if (!g_lazyPackFailureLogged) {
    g_lazyPackFailureLogged = true;
    LOG_WARN(
        "Creature sprite lazy pack disabled after payload failure: {}; native "
        "creature rendering retained",
        reason ? reason : "unknown shard error");
  }
}

bool lazy_shard_identity_matches(const LazyShard& shard) noexcept {
#ifdef _WIN32
  // The validated shard is retained with FILE_SHARE_READ only. A successful
  // lease therefore proves that no writer/delete/replace can enter the hot
  // path, without a GetFileAttributesEx call on every draw.
  return shard.lease.valid();
#else
  FileIdentity current{};
  return query_file_identity(shard.path, current) && current == shard.identity;
#endif
}

bool catalog_identity_matches_locked() noexcept {
  if (!g_catalog.active) return true;
#ifdef _WIN32
  if (g_catalog.lease.valid()) return true;
#else
  FileIdentity current{};
  if (query_file_identity(g_catalog.path, current) &&
      current == g_catalog.identity) {
    return true;
  }
#endif
  disable_lazy_pack_locked("catalog was removed or changed after validation");
  return false;
}

Resource* resource_for_handle_locked(FrameHandle handle) noexcept {
  if (handle.resourceIndex >= g_resources.size()) return nullptr;
  if (g_catalog.active) {
    if (handle.catalogShardIndex == kResidentFrameShard ||
        handle.catalogShardIndex >= g_catalog.shards.size()) {
      return nullptr;
    }
    const auto& shard = g_catalog.shards[handle.catalogShardIndex];
    if (shard.status != CatalogShardEntry::Status::Resident ||
        shard.generation != handle.catalogGeneration ||
        std::find(shard.resourceIndices.begin(), shard.resourceIndices.end(),
                  handle.resourceIndex) == shard.resourceIndices.end()) {
      return nullptr;
    }
  } else if (handle.catalogShardIndex != kResidentFrameShard ||
             handle.catalogGeneration != 0) {
    return nullptr;
  }
  return &g_resources[handle.resourceIndex];
}

bool validate_lazy_frame_source_locked(FrameHandle handle) noexcept {
  if (!catalog_identity_matches_locked()) return false;
  auto* resource = resource_for_handle_locked(handle);
  if (!resource || handle.frameIndex >= resource->frames.size()) {
    return false;
  }
  const auto& frame = resource->frames[handle.frameIndex];
  if (frame.lazyShardIndex == kResidentFrameShard) return true;
  if (!g_lazyPackLoaded || frame.lazyShardIndex >= g_lazyShards.size()) {
    if (g_catalog.active &&
        handle.catalogShardIndex < g_catalog.shards.size()) {
      quarantine_catalog_component_locked(
          g_catalog.shards[handle.catalogShardIndex].componentIndex,
          "invalid lazy frame source metadata");
    } else {
      disable_lazy_pack_locked("invalid lazy frame source metadata");
    }
    return false;
  }
  if (!lazy_shard_identity_matches(g_lazyShards[frame.lazyShardIndex])) {
    if (g_catalog.active &&
        handle.catalogShardIndex < g_catalog.shards.size()) {
      quarantine_catalog_component_locked(
          g_catalog.shards[handle.catalogShardIndex].componentIndex,
          "registry file was removed or changed before frame resolution");
    } else {
      disable_lazy_pack_locked(
          "registry file was removed or changed before frame resolution");
    }
    return false;
  }
  return true;
}

void fail_lazy_frame_locked(FrameHandle handle, const char* reason) noexcept {
  if (g_catalog.active &&
      handle.catalogShardIndex < g_catalog.shards.size()) {
    quarantine_catalog_component_locked(
        g_catalog.shards[handle.catalogShardIndex].componentIndex, reason);
  } else {
    disable_lazy_pack_locked(reason);
  }
}

bool read_lazy_shard_range_locked(const LazyShard& shard,
                                  std::uint64_t offset,
                                  std::vector<std::uint8_t>& bytes) noexcept {
  if (bytes.empty()) return false;
  g_filesystemAccessCounter.fetch_add(1, std::memory_order_relaxed);
#ifdef _WIN32
  if (!shard.lease.valid() ||
      offset > static_cast<std::uint64_t>(
                   (std::numeric_limits<LONGLONG>::max)())) {
    return false;
  }
  LARGE_INTEGER position{};
  position.QuadPart = static_cast<LONGLONG>(offset);
  if (!SetFilePointerEx(shard.lease.handle, position, nullptr, FILE_BEGIN)) {
    return false;
  }
  std::size_t complete = 0;
  while (complete < bytes.size()) {
    const auto chunk = static_cast<DWORD>((std::min)(
        bytes.size() - complete,
        static_cast<std::size_t>((std::numeric_limits<DWORD>::max)())));
    DWORD read = 0;
    if (!ReadFile(shard.lease.handle, bytes.data() + complete, chunk, &read,
                  nullptr) ||
        read != chunk) {
      return false;
    }
    complete += read;
  }
  return true;
#else
  std::ifstream input(shard.path, std::ios::binary);
  return input &&
         offset <= static_cast<std::uint64_t>(
                       (std::numeric_limits<std::streamoff>::max)()) &&
         input.seekg(static_cast<std::streamoff>(offset), std::ios::beg) &&
         input.read(reinterpret_cast<char*>(bytes.data()),
                    static_cast<std::streamsize>(bytes.size()));
#endif
}

const std::vector<std::uint8_t>* frame_indices_locked(
    FrameHandle handle, bool sourceIdentityValidated = false) noexcept {
  try {
    if (!sourceIdentityValidated && !validate_lazy_frame_source_locked(handle)) {
      return nullptr;
    }
    auto* resource = resource_for_handle_locked(handle);
    if (!resource || handle.frameIndex >= resource->frames.size()) {
      return nullptr;
    }
    const auto& frame = resource->frames[handle.frameIndex];
    if (frame.lazyShardIndex == kResidentFrameShard) return &frame.indices;
    if (!g_lazyPackLoaded || frame.lazyShardIndex >= g_lazyShards.size() ||
        frame.lazyIndexBytes == 0 ||
        frame.lazyIndexBytes > kLazyIndexCacheBudgetBytes ||
        frame.lazyStoredBytes == 0 ||
        (frame.lazyCompressionCodec == kRegistryFrameCodecRaw &&
         frame.lazyStoredBytes != frame.lazyIndexBytes) ||
        (frame.lazyCompressionCodec == kRegistryFrameCodecXpressHuff &&
         frame.lazyStoredBytes >= frame.lazyIndexBytes) ||
        (frame.lazyCompressionCodec != kRegistryFrameCodecRaw &&
         frame.lazyCompressionCodec != kRegistryFrameCodecXpressHuff)) {
      fail_lazy_frame_locked(handle, "invalid lazy frame metadata");
      return nullptr;
    }
    auto cached = std::find_if(
        g_lazyIndexCache.begin(), g_lazyIndexCache.end(),
        [&](const LazyIndexCacheEntry& entry) { return entry.handle == handle; });
    if (cached != g_lazyIndexCache.end()) {
      cached->lastUse = ++g_lazyIndexUseCounter;
      return &cached->indices;
    }
    const auto& shard = g_lazyShards[frame.lazyShardIndex];
    if (frame.lazyIndexOffset > shard.identity.bytes ||
        frame.lazyStoredBytes > shard.identity.bytes - frame.lazyIndexOffset ||
        frame.lazyIndexOffset >
            static_cast<std::uint64_t>((std::numeric_limits<std::streamoff>::max)())) {
      fail_lazy_frame_locked(handle,
                             "lazy frame range is outside its registry");
      return nullptr;
    }
    LazyIndexCacheEntry prepared{.handle = handle};
    std::vector<std::uint8_t> compressed;
    auto* stored = &prepared.indices;
    if (frame.lazyCompressionCodec == kRegistryFrameCodecXpressHuff) {
      stored = &compressed;
    }
    stored->resize(frame.lazyStoredBytes);
    if (!read_lazy_shard_range_locked(shard, frame.lazyIndexOffset, *stored)) {
      fail_lazy_frame_locked(handle, "cannot read a lazy frame payload");
      return nullptr;
    }
    if (!lazy_shard_identity_matches(shard)) {
      fail_lazy_frame_locked(handle,
                             "registry changed during a lazy frame read");
      return nullptr;
    }
    if (!frame.lazyIndexDigestValid ||
        sha256_bytes(
            reinterpret_cast<const std::byte*>(stored->data()),
            stored->size()) != frame.lazyIndexSha256) {
      fail_lazy_frame_locked(
          handle,
          "lazy frame payload differs from its validated shard metadata");
      return nullptr;
    }
    if (frame.lazyCompressionCodec == kRegistryFrameCodecXpressHuff) {
      prepared.indices.resize(frame.lazyIndexBytes);
      if (!decompress_xpress_huff_locked(compressed, prepared.indices)) {
        fail_lazy_frame_locked(handle,
                               "cannot decompress an XPRESS_HUFF frame exactly");
        return nullptr;
      }
    }
    for (const auto paletteIndex : prepared.indices) {
      if (frame.representatives[paletteIndex] == 0xFFFFu) {
        fail_lazy_frame_locked(
            handle, "lazy payload lacks a palette representative");
        return nullptr;
      }
    }
    auto cachedBytes = lazy_index_cache_bytes_locked();
    while (!g_lazyIndexCache.empty() &&
           (cachedBytes > kLazyIndexCacheBudgetBytes ||
            prepared.indices.size() > kLazyIndexCacheBudgetBytes - cachedBytes)) {
      const auto victim = std::min_element(
          g_lazyIndexCache.begin(), g_lazyIndexCache.end(),
          [](const LazyIndexCacheEntry& left, const LazyIndexCacheEntry& right) {
            return left.lastUse < right.lastUse;
          });
      const auto victimBytes = static_cast<std::uint64_t>(victim->indices.size());
      if (cachedBytes < victimBytes) {
        fail_lazy_frame_locked(handle,
                               "lazy payload cache accounting failed");
        return nullptr;
      }
      cachedBytes -= victimBytes;
      g_lazyIndexCache.erase(victim);
    }
    if (cachedBytes > kLazyIndexCacheBudgetBytes ||
        prepared.indices.size() > kLazyIndexCacheBudgetBytes - cachedBytes) {
      fail_lazy_frame_locked(
          handle, "lazy frame exceeds the payload cache budget");
      return nullptr;
    }
    prepared.lastUse = ++g_lazyIndexUseCounter;
    g_lazyIndexCache.push_back(std::move(prepared));
    return &g_lazyIndexCache.back().indices;
  } catch (...) {
    fail_lazy_frame_locked(handle,
                           "exception while loading a lazy frame payload");
    return nullptr;
  }
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
    const auto* resource = resource_for_handle_locked(layer.frame);
    if (!resource || layer.frame.frameIndex >= resource->frames.size()) return {};
    const auto& frame = resource->frames[layer.frame.frameIndex];
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

template <class Visitor>
bool visit_blend_recipes(const Frame& frame, std::uint64_t expectedPixels,
                         Visitor&& visitor) noexcept {
  if (!frame.antialias) return frame.blendRecipes.empty();
  const auto& bytes = frame.blendRecipes;
  if (bytes.size() < sizeof(std::uint32_t)) return false;
  std::size_t offset = 0;
  const auto readU32 = [&](std::uint32_t& value) {
    if (offset > bytes.size() || sizeof(value) > bytes.size() - offset) return false;
    std::memcpy(&value, bytes.data() + offset, sizeof(value));
    offset += sizeof(value);
    return true;
  };
  std::uint32_t recipeCount = 0;
  if (!readU32(recipeCount) || recipeCount > expectedPixels) return false;
  std::uint64_t previousPixel = (std::numeric_limits<std::uint64_t>::max)();
  for (std::uint32_t recipe = 0; recipe < recipeCount; ++recipe) {
    std::uint32_t pixel = 0;
    if (!readU32(pixel) || offset >= bytes.size()) return false;
    const auto operationCount = bytes[offset++];
    if (pixel >= expectedPixels || operationCount == 0 || operationCount > 8 ||
        (recipe != 0 && pixel <= previousPixel) ||
        static_cast<std::size_t>(operationCount) * 2 > bytes.size() - offset) {
      return false;
    }
    for (std::uint8_t operation = 0; operation < operationCount; ++operation) {
      const auto sourceIndex = bytes[offset++];
      const auto blendCode = bytes[offset++];
      if (blendCode >= 5 || frame.representatives[sourceIndex] == 0xFFFFu ||
          !visitor(pixel, sourceIndex, blendCode)) {
        return false;
      }
    }
    previousPixel = pixel;
  }
  return offset == bytes.size();
}

bool apply_blend_recipes(const Frame& frame,
                         const std::array<std::uint32_t, 256>& realized,
                         std::vector<std::uint32_t>& destination,
                         int destinationWidth, int destinationHeight,
                         int sourceWidth, int sourceHeight,
                         int destinationX, int destinationY) noexcept {
  if (!frame.antialias) return frame.blendRecipes.empty();
  if (destinationWidth <= 0 || destinationHeight <= 0 || sourceWidth <= 0 ||
      sourceHeight <= 0 || destinationX < 0 || destinationY < 0 ||
      sourceWidth > destinationWidth - destinationX ||
      sourceHeight > destinationHeight - destinationY) {
    return false;
  }
  const auto expectedPixels =
      static_cast<std::uint64_t>(sourceWidth) * sourceHeight;
  return visit_blend_recipes(
      frame, expectedPixels,
      [&](std::uint32_t pixel, std::uint8_t sourceIndex,
          std::uint8_t blendCode) noexcept {
        const auto sourceX = static_cast<int>(pixel % sourceWidth);
        const auto sourceY = static_cast<int>(pixel / sourceWidth);
        if (sourceY >= sourceHeight) return false;
        const auto destinationIndex =
            static_cast<std::size_t>(destinationY + sourceY) * destinationWidth +
            static_cast<std::size_t>(destinationX + sourceX);
        if (destinationIndex >= destination.size()) return false;
        destination[destinationIndex] = xbr_blend_pixel(
            destination[destinationIndex], realized[sourceIndex], blendCode);
        return true;
      });
}

bool upload_frame_locked(const Frame& frame,
                         const std::vector<std::uint8_t>& indices,
                         const std::array<std::uint32_t, 256>& realized,
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
      indices.size() != expectedContentPixels ||
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
          realized[indices[sourceIndex]];
    }
  }
  if (!apply_blend_recipes(frame, realized, replacement, physicalWidth,
                           physicalHeight, contentPhysicalWidth,
                           contentPhysicalHeight,
                           static_cast<int>(contentOffset),
                           static_cast<int>(contentOffset))) {
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
                     sampling_filter());
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER,
                     sampling_filter());
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
    const auto* resource = resource_for_handle_locked(layer.frame);
    if (!resource || layer.frame.frameIndex >= resource->frames.size()) return false;
    const auto& frame = resource->frames[layer.frame.frameIndex];
    const auto* indices = frame_indices_locked(layer.frame, true);
    int sourceWidth = 0;
    int sourceHeight = 0;
    std::uint64_t expectedPixels = 0;
    std::uint64_t sourceBytes = 0;
    if (!checked_physical_metrics(frame.logicalWidth, frame.logicalHeight, physicalScale,
                                  sourceWidth, sourceHeight, expectedPixels,
                                  sourceBytes) ||
        !indices || indices->size() != expectedPixels) {
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
        const auto pixel = realized[(*indices)[sourceRow + static_cast<std::size_t>(x)]];
        // Character's native CPU compositor overwrites with every non-zero
        // palette color. Alpha is retained for the single final GPU draw.
        auto& destination = replacement[destinationRow + static_cast<std::size_t>(x)];
        destination = overwrite_nontransparent_pixel(destination, pixel);
      }
    }
    if (!apply_blend_recipes(frame, realized, replacement, physicalWidth,
                             physicalHeight, sourceWidth, sourceHeight,
                             destinationX, destinationY)) {
      return false;
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
                     sampling_filter());
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER,
                     sampling_filter());
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
  if (!validate_lazy_frame_source_locked(handle)) return false;
  const auto* resource = resource_for_handle_locked(handle);
  if (!resource || handle.frameIndex >= resource->frames.size()) return false;
  const auto& frame = resource->frames[handle.frameIndex];
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
  const auto* indices = frame_indices_locked(handle, true);
  if (!indices) return false;

  auto cachedBytes = texture_cache_bytes_locked();
  std::size_t entryIndex = 0;
  const bool newTexture =
      g_textureCache.size() < kTextureCacheEntryLimit &&
      cachedBytes <= kTextureCacheBudgetBytes &&
      physicalBytes <= kTextureCacheBudgetBytes - cachedBytes;
  if (newTexture) {
    const int generated = api.DrawGenTexture(sampling_filter(), 0, 0, 0);
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
  if (!upload_frame_locked(frame, *indices, realized, encoding, physicalScale, entry.textureId,
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
  for (std::size_t index = 0; index < layerCount; ++index) {
    if (!frame_indices_locked(layers[index].frame, true)) return false;
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

namespace {
enum class RegistryFormat { Legacy, Xn };

struct ParsedRegistry {
  std::uint32_t version{};
  std::uint32_t scale{};
  std::uint16_t animationId{};
  std::uint32_t resourceCount{};
  std::uint64_t frameCount{};
  std::uint64_t indexBytes{};
  std::uint64_t registryBytes{};
  std::uint32_t checksum{};
  std::array<std::byte, 32> sha256{};
  FileIdentity identity{};
  ReadLease lease;
  std::vector<Resource> resources;
};

struct RegistrySetEntry {
  std::array<std::byte, 32> sha256{};
  std::uint32_t checksum{};
  std::uint32_t resourceCount{};
  std::uint64_t frameCount{};
  std::uint64_t indexBytes{};
  std::uint64_t registryBytes{};
};

struct ParsedRegistrySet {
  std::uint32_t scale{};
  std::uint16_t animationId{};
  std::uint32_t resourceCount{};
  std::uint64_t frameCount{};
  std::uint64_t indexBytes{};
  std::uint64_t registryBytes{};
  std::vector<RegistrySetEntry> entries;
};

struct LoadedPack {
  std::uint32_t scale{};
  std::uint16_t animationId{};
  std::uint64_t frameCount{};
  std::uint64_t indexBytes{};
  bool lazyPayloads{};
  std::vector<Resource> resources;
  std::vector<LazyShard> lazyShards;
};

bool file_exists(const std::filesystem::path& path, const char* description) {
  std::error_code error;
  // Inspect the directory entry rather than following it. A dangling symlink
  // or reparse point at a higher-priority manifest path is still "present":
  // opening it must fail closed instead of silently selecting an older pack.
  const auto status = std::filesystem::symlink_status(path, error);
  if (error) {
    if (error == std::errc::no_such_file_or_directory) return false;
    throw std::runtime_error(std::string("cannot inspect ") + description);
  }
  return status.type() != std::filesystem::file_type::not_found;
}

std::uint64_t registry_read_limit(const std::filesystem::path& path,
                                  RegistryFormat format) {
  if (format == RegistryFormat::Legacy) return kMaximumX2RegistryBytes;
  std::ifstream input(path, std::ios::binary);
  std::array<char, 8> magic{};
  std::uint32_t version = 0;
  std::uint32_t scale = 0;
  if (!input || !input.read(magic.data(), static_cast<std::streamsize>(magic.size())) ||
      !input.read(reinterpret_cast<char*>(&version), sizeof(version)) ||
      !input.read(reinterpret_cast<char*>(&scale), sizeof(scale)) ||
      magic != kXnRegistryMagic ||
      (version != kXnRegistryVersion &&
       version != kXnAntialiasRegistryVersion &&
       version != kXnCompressedRegistryVersion) ||
      !supported_physical_scale(scale) ||
      (version == kXnAntialiasRegistryVersion && scale != 2)) {
    throw std::runtime_error("invalid creature-sprite xN registry prefix: " +
                             path.filename().string());
  }
  return maximum_registry_bytes_for_scale(scale);
}

ParsedRegistry parse_registry(const std::filesystem::path& path, RegistryFormat format,
                              bool lazyPayloads, std::uint32_t lazyShardIndex = 0,
                              bool verifyDigests = false,
                              bool catalogShard = false) {
  ParsedRegistry parsed;
  const auto maximumReadBytes = registry_read_limit(path, format);
  auto bytes = read_file(path, maximumReadBytes, &parsed.identity,
                         lazyPayloads ? &parsed.lease : nullptr);
  parsed.registryBytes = static_cast<std::uint64_t>(bytes.size());
  if (verifyDigests) {
    parsed.checksum = crc32(bytes);
    parsed.sha256 = sha256(bytes);
  }
  BinaryReader reader(std::move(bytes));
  std::array<char, 8> magic{};
  std::uint32_t metadata = 0;
  if (!reader.read(magic) || !reader.read(parsed.version) || !reader.read(parsed.scale) ||
      !reader.read(parsed.resourceCount) || !reader.read(metadata)) {
    throw std::runtime_error("truncated creature-sprite registry header");
  }
  const bool xnFormat = format == RegistryFormat::Xn;
  const bool formatHeaderValid =
      xnFormat
          ? magic == kXnRegistryMagic && supported_physical_scale(parsed.scale) &&
                (parsed.version == kXnRegistryVersion ||
                 (parsed.version == kXnAntialiasRegistryVersion &&
                  parsed.scale == 2 && !lazyPayloads && !catalogShard) ||
                 (parsed.version == kXnCompressedRegistryVersion &&
                  lazyPayloads && catalogShard))
          : magic == kLegacyRegistryMagic &&
                (parsed.version == kLegacyRegistryVersion ||
                 parsed.version == kLegacyCurrentRegistryVersion) &&
                parsed.scale == 2;
  if (!formatHeaderValid || parsed.resourceCount == 0 ||
      parsed.resourceCount > kMaximumResources ||
      parsed.registryBytes > maximum_registry_bytes_for_scale(parsed.scale)) {
    throw std::runtime_error("invalid creature-sprite registry header: " +
                             path.filename().string());
  }
  if (!xnFormat && parsed.version == kLegacyRegistryVersion) {
    if (metadata != 0) throw std::runtime_error("invalid legacy creature-sprite metadata");
    parsed.animationId = kLegacyMgo1AnimationId;
  } else {
    if (metadata == 0 || metadata > std::numeric_limits<std::uint16_t>::max() ||
        (catalogShard && metadata != kCatalogShardAnimationSentinel) ||
        (!catalogShard && metadata == kCatalogShardAnimationSentinel)) {
      throw std::runtime_error("invalid creature-sprite animation id");
    }
    parsed.animationId = static_cast<std::uint16_t>(metadata);
  }
  parsed.resources.reserve(parsed.resourceCount);
  for (std::uint32_t resourceIndex = 0; resourceIndex < parsed.resourceCount;
       ++resourceIndex) {
    Resource resource;
    std::uint32_t frameCount = 0;
    std::uint32_t cycleCount = 0;
    if (!reader.read(resource.resref) || !reader.read(resource.sourceSha256) ||
        !reader.read(frameCount) || !reader.read(cycleCount) || frameCount == 0 ||
        frameCount > kMaximumFramesPerResource || cycleCount == 0 ||
        cycleCount > kMaximumCyclesPerResource ||
        (catalogShard && !canonical_catalog_resref(resource.resref))) {
      throw std::runtime_error("invalid creature-sprite resource header");
    }
    if (std::find_if(parsed.resources.begin(), parsed.resources.end(),
                     [&](const Resource& existing) {
                       return existing.resref == resource.resref;
                     }) != parsed.resources.end()) {
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
      std::uint32_t storedBytes = 0;
      if (!reader.read(width) || !reader.read(height) || !reader.read(centerX) ||
          !reader.read(centerY) || !reader.read(frame.transparent) ||
          !reader.read(frameReserved) || !reader.read(storedBytes) || width == 0 ||
          height == 0) {
        throw std::runtime_error("invalid creature-sprite frame header");
      }
      const bool compressedRegistry =
          parsed.version == kXnCompressedRegistryVersion;
      const auto frameCodec = compressedRegistry
                                  ? std::to_integer<std::uint8_t>(frameReserved[0])
                                  : kRegistryFrameCodecRaw;
      if ((!compressedRegistry &&
           frameReserved != std::array<std::byte, 3>{}) ||
          (compressedRegistry &&
           (frameReserved[1] != std::byte{0} ||
            frameReserved[2] != std::byte{0}))) {
        throw std::runtime_error("invalid creature-sprite frame header");
      }
      const auto nativePixels = static_cast<std::uint64_t>(width) * height;
      const auto scaleSquared =
          static_cast<std::uint64_t>(parsed.scale) * parsed.scale;
      if (nativePixels > (std::numeric_limits<std::uint64_t>::max)() / scaleSquared) {
        throw std::runtime_error("creature-sprite frame payload overflows");
      }
      const auto expectedIndices = nativePixels * scaleSquared;
      if (expectedIndices > (std::numeric_limits<std::uint32_t>::max)() ||
          expectedIndices > maximum_registry_bytes_for_scale(parsed.scale) ||
          (lazyPayloads && expectedIndices > kLazyIndexCacheBudgetBytes) ||
          (!compressedRegistry && expectedIndices != storedBytes) ||
          (compressedRegistry &&
           ((frameCodec == kRegistryFrameCodecRaw &&
             storedBytes != expectedIndices) ||
            (frameCodec == kRegistryFrameCodecXpressHuff &&
             (storedBytes == 0 || storedBytes >= expectedIndices)) ||
            (frameCodec != kRegistryFrameCodecRaw &&
             frameCodec != kRegistryFrameCodecXpressHuff))) ||
          !checked_add(parsed.indexBytes, expectedIndices,
                       maximum_registry_bytes_for_scale(parsed.scale)) ||
          !reader.read(frame.representatives)) {
        throw std::runtime_error("invalid creature-sprite frame payload");
      }
      const auto indexOffset = reader.position();
      const std::byte* indexData = nullptr;
      if (!reader.read_view(indexData, storedBytes)) {
        throw std::runtime_error("truncated creature-sprite frame payload");
      }
      if (frameCodec == kRegistryFrameCodecRaw) {
        for (std::uint32_t index = 0; index < storedBytes; ++index) {
          const auto paletteIndex =
              std::to_integer<std::uint8_t>(indexData[index]);
          if (frame.representatives[paletteIndex] == 0xFFFFu) {
            throw std::runtime_error(
                "creature-sprite payload lacks a palette representative");
          }
        }
      }
      if (lazyPayloads) {
        frame.lazyShardIndex = lazyShardIndex;
        frame.lazyIndexOffset = indexOffset;
        frame.lazyIndexBytes = static_cast<std::uint32_t>(expectedIndices);
        frame.lazyStoredBytes = storedBytes;
        frame.lazyCompressionCodec = frameCodec;
        frame.lazyIndexSha256 = sha256_bytes(indexData, storedBytes);
        frame.lazyIndexDigestValid = true;
      } else {
        frame.indices.assign(reinterpret_cast<const std::uint8_t*>(indexData),
                             reinterpret_cast<const std::uint8_t*>(indexData) +
                                 storedBytes);
      }
      if (parsed.version == kXnAntialiasRegistryVersion) {
        std::uint32_t recipeBytes = 0;
        frame.antialias = true;
        if (!reader.read(recipeBytes) || recipeBytes < sizeof(std::uint32_t) ||
            recipeBytes > maximum_registry_bytes_for_scale(parsed.scale) ||
            !reader.read_bytes(frame.blendRecipes, recipeBytes) ||
            !visit_blend_recipes(
                frame, expectedIndices,
                [](std::uint32_t, std::uint8_t, std::uint8_t) noexcept {
                  return true;
                })) {
          throw std::runtime_error("invalid creature-sprite antialias recipe payload");
        }
      }
      frame.logicalWidth = width;
      frame.logicalHeight = height;
      frame.centerX = centerX;
      frame.centerY = centerY;
      resource.frames.push_back(std::move(frame));
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
    if (!checked_add(parsed.frameCount, frameCount,
                     static_cast<std::uint64_t>(kMaximumResources) *
                         kMaximumFramesPerResource)) {
      throw std::runtime_error("creature-sprite frame count overflow");
    }
    parsed.resources.push_back(std::move(resource));
  }
  if (!reader.at_end()) throw std::runtime_error("trailing creature-sprite registry bytes");
  return parsed;
}

struct ProbedRegistryDirectory {
  FileIdentity identity{};
  std::vector<std::array<char, 8>> resrefs;
};

template <class T>
bool read_stream_value(std::ifstream& input, std::uint64_t& position,
                       std::uint64_t fileBytes, T& value) {
  static_assert(std::is_trivially_copyable_v<T>);
  if (position > fileBytes || sizeof(T) > fileBytes - position ||
      !input.read(reinterpret_cast<char*>(&value), sizeof(T))) {
    return false;
  }
  position += sizeof(T);
  return true;
}

bool skip_stream_bytes(std::ifstream& input, std::uint64_t& position,
                       std::uint64_t fileBytes, std::uint64_t byteCount) {
  if (position > fileBytes || byteCount > fileBytes - position ||
      byteCount > static_cast<std::uint64_t>(
                      (std::numeric_limits<std::streamoff>::max)())) {
    return false;
  }
  position += byteCount;
  if (position > static_cast<std::uint64_t>(
                     (std::numeric_limits<std::streamoff>::max)())) {
    return false;
  }
  input.seekg(static_cast<std::streamoff>(position), std::ios::beg);
  return static_cast<bool>(input);
}

ProbedRegistryDirectory probe_catalog_registry_directory(
    const CatalogShardEntry& expected, std::uint32_t expectedScale) {
  ProbedRegistryDirectory probed;
  if (!query_file_identity(expected.path, probed.identity) ||
      probed.identity.bytes != expected.registryBytes ||
      probed.identity.bytes < 24) {
    throw std::runtime_error("missing or resized catalog shard");
  }
  std::ifstream input(expected.path, std::ios::binary);
  if (!input) throw std::runtime_error("cannot open catalog shard directory");
  std::uint64_t position = 0;
  std::array<char, 8> magic{};
  std::uint32_t version = 0;
  std::uint32_t scale = 0;
  std::uint32_t resourceCount = 0;
  std::uint32_t animationId = 0;
  if (!read_stream_value(input, position, probed.identity.bytes, magic) ||
      !read_stream_value(input, position, probed.identity.bytes, version) ||
      !read_stream_value(input, position, probed.identity.bytes, scale) ||
      !read_stream_value(input, position, probed.identity.bytes, resourceCount) ||
      !read_stream_value(input, position, probed.identity.bytes, animationId) ||
      magic != kXnRegistryMagic || version != kXnRegistryVersion ||
      scale != expectedScale ||
      animationId != kCatalogShardAnimationSentinel ||
      resourceCount != expected.resourceCount) {
    throw std::runtime_error("invalid catalog shard directory header");
  }
  probed.resrefs.reserve(resourceCount);
  std::set<std::array<char, 8>> uniqueResrefs;
  std::uint64_t frameCountSum = 0;
  std::uint64_t indexBytesSum = 0;
  for (std::uint32_t resourceIndex = 0; resourceIndex < resourceCount;
       ++resourceIndex) {
    std::array<char, 8> resref{};
    std::array<std::byte, 32> sourceDigest{};
    std::uint32_t frameCount = 0;
    std::uint32_t cycleCount = 0;
    if (!read_stream_value(input, position, probed.identity.bytes, resref) ||
        !read_stream_value(input, position, probed.identity.bytes,
                           sourceDigest) ||
        !read_stream_value(input, position, probed.identity.bytes,
                           frameCount) ||
        !read_stream_value(input, position, probed.identity.bytes,
                           cycleCount) ||
        !canonical_catalog_resref(resref) ||
        !uniqueResrefs.insert(resref).second || frameCount == 0 ||
        frameCount > kMaximumFramesPerResource || cycleCount == 0 ||
        cycleCount > kMaximumCyclesPerResource) {
      throw std::runtime_error("invalid catalog shard resource directory");
    }
    for (std::uint32_t frameIndex = 0; frameIndex < frameCount;
         ++frameIndex) {
      std::uint16_t width = 0;
      std::uint16_t height = 0;
      std::int16_t centerX = 0;
      std::int16_t centerY = 0;
      std::uint8_t transparent = 0;
      std::array<std::byte, 3> reserved{};
      std::uint32_t indexBytes = 0;
      if (!read_stream_value(input, position, probed.identity.bytes, width) ||
          !read_stream_value(input, position, probed.identity.bytes, height) ||
          !read_stream_value(input, position, probed.identity.bytes, centerX) ||
          !read_stream_value(input, position, probed.identity.bytes, centerY) ||
          !read_stream_value(input, position, probed.identity.bytes,
                             transparent) ||
          !read_stream_value(input, position, probed.identity.bytes, reserved) ||
          !read_stream_value(input, position, probed.identity.bytes,
                             indexBytes) ||
          width == 0 || height == 0 || reserved != std::array<std::byte, 3>{}) {
        throw std::runtime_error("invalid catalog shard frame directory");
      }
      const auto expectedIndices = static_cast<std::uint64_t>(width) * height *
                                   scale * scale;
      if (expectedIndices != indexBytes || indexBytes == 0 ||
          indexBytes > kLazyIndexCacheBudgetBytes ||
          !checked_add(indexBytesSum, indexBytes,
                       maximum_registry_bytes_for_scale(scale)) ||
          !skip_stream_bytes(input, position, probed.identity.bytes,
                             sizeof(std::uint16_t) * 256ull + indexBytes)) {
        throw std::runtime_error("invalid catalog shard frame range");
      }
    }
    for (std::uint32_t cycleIndex = 0; cycleIndex < cycleCount;
         ++cycleIndex) {
      std::uint32_t slotCount = 0;
      if (!read_stream_value(input, position, probed.identity.bytes,
                             slotCount) ||
          slotCount > kMaximumCycleSlots ||
          !skip_stream_bytes(input, position, probed.identity.bytes,
                             static_cast<std::uint64_t>(slotCount) *
                                 sizeof(std::uint32_t))) {
        throw std::runtime_error("invalid catalog shard cycle directory");
      }
    }
    if (!checked_add(frameCountSum, frameCount, kMaximumCatalogFrames)) {
      throw std::runtime_error("catalog shard directory frame overflow");
    }
    probed.resrefs.push_back(resref);
  }
  FileIdentity finalIdentity{};
  if (position != probed.identity.bytes ||
      frameCountSum != expected.frameCount ||
      indexBytesSum != expected.indexBytes ||
      !query_file_identity(expected.path, finalIdentity) ||
      finalIdentity != probed.identity) {
    throw std::runtime_error("catalog shard changed during directory probe");
  }
  return probed;
}

ParsedRegistrySet parse_registry_set(const std::filesystem::path& path) {
  constexpr auto kMaximumSetManifestBytes =
      kRegistrySetHeaderBytes +
      static_cast<std::size_t>(kMaximumRegistrySetShards) * kRegistrySetEntryBytes;
  BinaryReader reader(read_file(path, kMaximumSetManifestBytes));
  ParsedRegistrySet parsed;
  std::array<char, 8> magic{};
  std::uint32_t version = 0;
  std::uint32_t shardCount = 0;
  std::uint32_t animationId = 0;
  std::uint32_t reserved = 0;
  if (!reader.read(magic) || !reader.read(version) || !reader.read(parsed.scale) ||
      !reader.read(shardCount) || !reader.read(parsed.resourceCount) ||
      !reader.read(animationId) || !reader.read(reserved) ||
      !reader.read(parsed.frameCount) || !reader.read(parsed.indexBytes) ||
      !reader.read(parsed.registryBytes)) {
    throw std::runtime_error("truncated creature-sprite registry-set header");
  }
  if (magic != kRegistrySetMagic || version != kRegistrySetVersion ||
      !supported_physical_scale(parsed.scale) || shardCount == 0 ||
      shardCount > kMaximumRegistrySetShards || parsed.resourceCount == 0 ||
      parsed.resourceCount > kMaximumRegistrySetResources || animationId == 0 ||
      animationId > std::numeric_limits<std::uint16_t>::max() || reserved != 0 ||
      parsed.frameCount == 0 || parsed.frameCount > kMaximumRegistrySetFrames ||
      parsed.indexBytes == 0 || parsed.indexBytes > kMaximumRegistrySetBytes ||
      parsed.registryBytes == 0 || parsed.registryBytes > kMaximumRegistrySetBytes ||
      parsed.indexBytes > parsed.registryBytes ||
      parsed.resourceCount > shardCount * kMaximumResources) {
    throw std::runtime_error("invalid creature-sprite registry-set header");
  }
  parsed.animationId = static_cast<std::uint16_t>(animationId);
  const auto maximumShardBytes = maximum_registry_bytes_for_scale(parsed.scale);
  parsed.entries.reserve(shardCount);
  std::uint64_t resourceSum = 0;
  std::uint64_t frameSum = 0;
  std::uint64_t indexSum = 0;
  std::uint64_t registrySum = 0;
  for (std::uint32_t shardIndex = 0; shardIndex < shardCount; ++shardIndex) {
    RegistrySetEntry entry;
    if (!reader.read(entry.sha256) || !reader.read(entry.checksum) ||
        !reader.read(entry.resourceCount) || !reader.read(entry.frameCount) ||
        !reader.read(entry.indexBytes) || !reader.read(entry.registryBytes)) {
      throw std::runtime_error("truncated creature-sprite registry-set entry");
    }
    const bool nonzeroHash = std::any_of(
        entry.sha256.begin(), entry.sha256.end(),
        [](std::byte value) { return value != std::byte{0}; });
    if (!nonzeroHash || entry.resourceCount == 0 ||
        entry.resourceCount > kMaximumResources || entry.frameCount == 0 ||
        entry.frameCount > static_cast<std::uint64_t>(entry.resourceCount) *
                               kMaximumFramesPerResource ||
        entry.indexBytes == 0 || entry.indexBytes > maximumShardBytes ||
        entry.registryBytes < 24 || entry.registryBytes > maximumShardBytes ||
        entry.indexBytes > entry.registryBytes ||
        !checked_add(resourceSum, entry.resourceCount, kMaximumRegistrySetResources) ||
        !checked_add(frameSum, entry.frameCount, kMaximumRegistrySetFrames) ||
        !checked_add(indexSum, entry.indexBytes, kMaximumRegistrySetBytes) ||
        !checked_add(registrySum, entry.registryBytes, kMaximumRegistrySetBytes)) {
      throw std::runtime_error("invalid creature-sprite registry-set entry");
    }
    parsed.entries.push_back(entry);
  }
  if (!reader.at_end() || resourceSum != parsed.resourceCount ||
      frameSum != parsed.frameCount || indexSum != parsed.indexBytes ||
      registrySum != parsed.registryBytes) {
    throw std::runtime_error("creature-sprite registry-set totals mismatch");
  }
  return parsed;
}

CatalogState load_registry_catalog(const std::filesystem::path& assetsDirectory,
                                   const std::filesystem::path& catalogPath) {
  CatalogState catalog;
  catalog.active = true;
  catalog.path = catalogPath;
  auto bytes = read_file(catalogPath, kMaximumRegistryCatalogDirectoryBytes,
                         &catalog.identity, &catalog.lease);
  BinaryReader reader(std::move(bytes));
  std::array<char, 8> magic{};
  std::uint32_t version = 0;
  std::uint32_t animationCount = 0;
  std::uint32_t componentCount = 0;
  std::uint32_t membershipCount = 0;
  std::uint32_t shardCount = 0;
  std::uint32_t directoryCount = 0;
  std::uint32_t directoryEntryBytes = 0;
  std::array<std::byte, 32> expectedDirectoryDigest{};
  if (!reader.read(magic) || !reader.read(version) ||
      !reader.read(catalog.scale) || !reader.read(animationCount) ||
      !reader.read(componentCount) || !reader.read(membershipCount) ||
      !reader.read(shardCount) || !reader.read(catalog.resourceCount) ||
      !reader.read(catalog.frameCount) || !reader.read(catalog.indexBytes) ||
      !reader.read(catalog.registryBytes)) {
    throw std::runtime_error("truncated creature-sprite registry catalog header");
  }
  catalog.version = version;
  if (version == kRegistryCatalogDirectoryVersion &&
      (!reader.read(directoryCount) || !reader.read(directoryEntryBytes) ||
       !reader.read(expectedDirectoryDigest))) {
    throw std::runtime_error(
        "truncated creature-sprite registry catalog V2 header");
  }
  if (magic != kRegistryCatalogMagic ||
      (version != kRegistryCatalogVersion &&
       version != kRegistryCatalogDirectoryVersion) ||
      (version == kRegistryCatalogVersion &&
       catalog.identity.bytes > kMaximumRegistryCatalogBytes) ||
      !supported_physical_scale(catalog.scale) || animationCount == 0 ||
      animationCount > kMaximumCatalogAnimations || componentCount == 0 ||
      componentCount > kMaximumCatalogComponents || membershipCount == 0 ||
      membershipCount > kMaximumCatalogMemberships || shardCount == 0 ||
      shardCount > kMaximumCatalogShards || componentCount > shardCount ||
      animationCount > membershipCount || catalog.resourceCount == 0 ||
      catalog.resourceCount > kMaximumCatalogResources ||
      catalog.frameCount == 0 || catalog.frameCount > kMaximumCatalogFrames ||
      catalog.indexBytes == 0 ||
      catalog.indexBytes > kMaximumCatalogRegistryBytes ||
      catalog.registryBytes == 0 ||
      catalog.registryBytes > kMaximumCatalogRegistryBytes ||
      (version == kRegistryCatalogVersion &&
       catalog.indexBytes > catalog.registryBytes) ||
      (version == kRegistryCatalogVersion && directoryCount != 0) ||
      (version == kRegistryCatalogDirectoryVersion &&
       (directoryCount == 0 ||
        directoryCount > kMaximumCatalogDirectoryEntries ||
        directoryEntryBytes != kRegistryCatalogDirectoryEntryBytes ||
        !std::any_of(expectedDirectoryDigest.begin(),
                     expectedDirectoryDigest.end(),
                     [](std::byte value) { return value != std::byte{0}; })))) {
    throw std::runtime_error("invalid creature-sprite registry catalog header");
  }

  catalog.animations.reserve(animationCount);
  std::set<std::uint16_t> animationIds;
  std::vector<bool> membershipCovered(membershipCount, false);
  std::uint32_t previousAnimationId = 0;
  std::uint32_t expectedMembershipStart = 0;
  for (std::uint32_t index = 0; index < animationCount; ++index) {
    std::uint32_t animationId = 0;
    CatalogAnimation animation;
    if (!reader.read(animationId) || !reader.read(animation.owner) ||
        !reader.read(animation.membershipStart) ||
        !reader.read(animation.membershipCount) || animationId == 0 ||
        animationId >= kCatalogShardAnimationSentinel ||
        animationId <= previousAnimationId ||
        !catalog_owner_matches_animation(animation.owner, animationId) ||
        animation.membershipCount == 0 ||
        animation.membershipStart != expectedMembershipStart ||
        animation.membershipStart > membershipCount ||
        animation.membershipCount >
            membershipCount - animation.membershipStart) {
      throw std::runtime_error("invalid creature-sprite catalog animation entry");
    }
    animation.animationId = static_cast<std::uint16_t>(animationId);
    if (!animationIds.insert(animation.animationId).second) {
      throw std::runtime_error("duplicate creature-sprite catalog animation id");
    }
    for (std::uint32_t membership = animation.membershipStart;
         membership < animation.membershipStart + animation.membershipCount;
         ++membership) {
      if (membershipCovered[membership]) {
        throw std::runtime_error("overlapping creature-sprite catalog memberships");
      }
      membershipCovered[membership] = true;
    }
    previousAnimationId = animationId;
    expectedMembershipStart =
        animation.membershipStart + animation.membershipCount;
    catalog.animations.push_back(std::move(animation));
  }
  if (expectedMembershipStart != membershipCount ||
      std::find(membershipCovered.begin(), membershipCovered.end(), false) !=
          membershipCovered.end()) {
    throw std::runtime_error("incomplete creature-sprite catalog membership coverage");
  }

  catalog.memberships.resize(membershipCount);
  for (auto& componentIndex : catalog.memberships) {
    if (!reader.read(componentIndex) || componentIndex >= componentCount) {
      throw std::runtime_error("invalid creature-sprite catalog component membership");
    }
  }

  catalog.components.reserve(componentCount);
  std::vector<bool> shardCovered(shardCount, false);
  std::vector<std::uint32_t> componentReferences(componentCount, 0);
  std::set<std::array<std::byte, 32>> componentDigests;
  std::uint32_t expectedShardStart = 0;
  for (std::uint32_t index = 0; index < componentCount; ++index) {
    CatalogComponent component;
    std::uint32_t reserved = 0;
    if (!reader.read(component.digest) || !reader.read(component.shardStart) ||
        !reader.read(component.shardCount) ||
        !reader.read(component.resourceCount) || !reader.read(reserved) ||
        !reader.read(component.frameCount) || !reader.read(component.indexBytes) ||
        !reader.read(component.registryBytes)) {
      throw std::runtime_error("truncated creature-sprite catalog component entry");
    }
    const bool nonzeroDigest = std::any_of(
        component.digest.begin(), component.digest.end(),
        [](std::byte value) { return value != std::byte{0}; });
    if (!nonzeroDigest || !componentDigests.insert(component.digest).second ||
        component.shardCount == 0 || component.shardStart > shardCount ||
        component.shardStart != expectedShardStart ||
        component.shardCount > shardCount - component.shardStart ||
        component.resourceCount == 0 ||
        component.resourceCount > kMaximumCatalogResources || reserved != 0 ||
        component.frameCount == 0 ||
        component.frameCount >
            static_cast<std::uint64_t>(component.resourceCount) *
                kMaximumFramesPerResource ||
        component.indexBytes == 0 ||
        component.indexBytes > kMaximumCatalogRegistryBytes ||
        component.registryBytes == 0 ||
        component.registryBytes > kMaximumCatalogRegistryBytes ||
        (catalog.version == kRegistryCatalogVersion &&
         component.indexBytes > component.registryBytes) ||
        component.resourceCount > component.shardCount * kMaximumResources) {
      throw std::runtime_error("invalid creature-sprite catalog component entry");
    }
    for (std::uint32_t shard = component.shardStart;
         shard < component.shardStart + component.shardCount; ++shard) {
      if (shardCovered[shard]) {
        throw std::runtime_error("overlapping creature-sprite catalog shard ranges");
      }
      shardCovered[shard] = true;
    }
    expectedShardStart = component.shardStart + component.shardCount;
    catalog.components.push_back(std::move(component));
  }
  if (expectedShardStart != shardCount ||
      std::find(shardCovered.begin(), shardCovered.end(), false) !=
          shardCovered.end()) {
    throw std::runtime_error("incomplete creature-sprite catalog shard coverage");
  }

  catalog.shards.reserve(shardCount);
  std::set<std::array<std::byte, 32>> shardDigests;
  const auto maximumShardBytes = maximum_registry_bytes_for_scale(catalog.scale);
  std::uint64_t resourceSum = 0;
  std::uint64_t frameSum = 0;
  std::uint64_t indexSum = 0;
  std::uint64_t registrySum = 0;
  for (std::uint32_t index = 0; index < shardCount; ++index) {
    CatalogShardEntry shard;
    if (!reader.read(shard.encoded)) {
      throw std::runtime_error("truncated creature-sprite catalog shard entry");
    }
    std::copy_n(shard.encoded.begin(), shard.sha256.size(),
                shard.sha256.begin());
    shard.checksum = encoded_field<std::uint32_t>(shard.encoded, 32);
    shard.resourceCount = encoded_field<std::uint32_t>(shard.encoded, 36);
    shard.frameCount = encoded_field<std::uint64_t>(shard.encoded, 40);
    shard.indexBytes = encoded_field<std::uint64_t>(shard.encoded, 48);
    shard.registryBytes = encoded_field<std::uint64_t>(shard.encoded, 56);
    const bool nonzeroHash = std::any_of(
        shard.sha256.begin(), shard.sha256.end(),
        [](std::byte value) { return value != std::byte{0}; });
    if (!nonzeroHash || !shardDigests.insert(shard.sha256).second ||
        shard.resourceCount == 0 || shard.resourceCount > kMaximumResources ||
        shard.frameCount == 0 ||
        shard.frameCount >
            static_cast<std::uint64_t>(shard.resourceCount) *
                kMaximumFramesPerResource ||
        shard.indexBytes == 0 || shard.indexBytes > maximumShardBytes ||
        shard.registryBytes < 24 || shard.registryBytes > maximumShardBytes ||
        (catalog.version == kRegistryCatalogVersion &&
         shard.indexBytes > shard.registryBytes) ||
        !checked_add(resourceSum, shard.resourceCount,
                     kMaximumCatalogResources) ||
        !checked_add(frameSum, shard.frameCount, kMaximumCatalogFrames) ||
        !checked_add(indexSum, shard.indexBytes,
                     kMaximumCatalogRegistryBytes) ||
        !checked_add(registrySum, shard.registryBytes,
                     kMaximumCatalogRegistryBytes)) {
      throw std::runtime_error("invalid creature-sprite catalog shard entry");
    }
    shard.path = assetsDirectory / catalog_shard_filename(shard.sha256);
    catalog.shards.push_back(std::move(shard));
  }
  if (resourceSum != catalog.resourceCount ||
      frameSum != catalog.frameCount || indexSum != catalog.indexBytes ||
      registrySum != catalog.registryBytes) {
    throw std::runtime_error("creature-sprite catalog totals mismatch");
  }

  // Activation authenticates the small catalog only. Shard bytes are never
  // opened or hashed here; V3/V5 registries are validated by the background
  // resolver only when one of their resrefs is requested.
  for (std::uint32_t componentIndex = 0; componentIndex < componentCount;
       ++componentIndex) {
    const auto& component = catalog.components[componentIndex];
    for (std::uint32_t offset = 0; offset < component.shardCount; ++offset) {
      catalog.shards[component.shardStart + offset].componentIndex =
          componentIndex;
    }
  }

  resourceSum = 0;
  frameSum = 0;
  indexSum = 0;
  registrySum = 0;
  for (std::uint32_t componentIndex = 0; componentIndex < componentCount;
       ++componentIndex) {
    auto& component = catalog.components[componentIndex];
    std::uint64_t componentResources = 0;
    std::uint64_t componentFrames = 0;
    std::uint64_t componentIndices = 0;
    std::uint64_t componentRegistry = 0;
    for (std::uint32_t offset = 0; offset < component.shardCount; ++offset) {
      const auto& shard = catalog.shards[component.shardStart + offset];
      if (!checked_add(componentResources, shard.resourceCount,
                       kMaximumCatalogResources) ||
          !checked_add(componentFrames, shard.frameCount,
                       kMaximumCatalogFrames) ||
          !checked_add(componentIndices, shard.indexBytes,
                       kMaximumCatalogRegistryBytes) ||
          !checked_add(componentRegistry, shard.registryBytes,
                       kMaximumCatalogRegistryBytes)) {
        throw std::runtime_error("creature-sprite catalog component overflow");
      }
    }
    if (componentResources != component.resourceCount ||
        componentFrames != component.frameCount ||
        componentIndices != component.indexBytes ||
        componentRegistry != component.registryBytes ||
        catalog_component_digest(catalog.scale, catalog.shards,
                                 component.shardStart,
                                 component.shardCount) != component.digest ||
        !checked_add(resourceSum, component.resourceCount,
                     kMaximumCatalogResources) ||
        !checked_add(frameSum, component.frameCount, kMaximumCatalogFrames) ||
        !checked_add(indexSum, component.indexBytes,
                     kMaximumCatalogRegistryBytes) ||
        !checked_add(registrySum, component.registryBytes,
                     kMaximumCatalogRegistryBytes)) {
      throw std::runtime_error("creature-sprite catalog component mismatch");
    }
  }
  if (resourceSum != catalog.resourceCount || frameSum != catalog.frameCount ||
      indexSum != catalog.indexBytes || registrySum != catalog.registryBytes) {
    throw std::runtime_error("creature-sprite catalog component totals mismatch");
  }

  std::vector<std::set<std::uint32_t>> animationComponents(
      catalog.animations.size());
  std::vector<std::uint32_t> expectedDirectoryCounts(
      catalog.animations.size(), 0);
  for (std::size_t animationIndex = 0;
       animationIndex < catalog.animations.size(); ++animationIndex) {
    const auto& animation = catalog.animations[animationIndex];
    std::set<std::uint32_t> uniqueComponents;
    std::uint32_t previousComponentIndex = 0;
    for (std::uint32_t offset = 0; offset < animation.membershipCount; ++offset) {
      const auto componentIndex =
          catalog.memberships[animation.membershipStart + offset];
      if ((offset != 0 && componentIndex <= previousComponentIndex) ||
          !uniqueComponents.insert(componentIndex).second) {
        throw std::runtime_error(
            "non-canonical creature-sprite animation membership");
      }
      previousComponentIndex = componentIndex;
      ++componentReferences[componentIndex];
      animationComponents[animationIndex].insert(componentIndex);
      const auto resources = catalog.components[componentIndex].resourceCount;
      if (resources > kMaximumCatalogDirectoryEntries -
                          expectedDirectoryCounts[animationIndex]) {
        throw std::runtime_error(
            "creature-sprite catalog animation directory overflow");
      }
      expectedDirectoryCounts[animationIndex] += resources;
    }
  }
  if (std::find(componentReferences.begin(), componentReferences.end(), 0u) !=
      componentReferences.end()) {
    throw std::runtime_error("unreferenced creature-sprite catalog component");
  }

  if (catalog.version == kRegistryCatalogDirectoryVersion) {
    catalog.directory.reserve(directoryCount);
    std::vector<std::byte> rawDirectory;
    rawDirectory.reserve(static_cast<std::size_t>(directoryCount) *
                         kRegistryCatalogDirectoryEntryBytes);
    std::set<std::tuple<std::uint16_t, std::uint32_t, std::uint32_t>>
        occupiedOrdinals;
    std::vector<std::uint32_t> actualDirectoryCounts(
        catalog.animations.size(), 0);
    CatalogDirectoryEntry previous{};
    bool havePrevious = false;
    for (std::uint32_t index = 0; index < directoryCount; ++index) {
      std::array<std::byte, kRegistryCatalogDirectoryEntryBytes> encoded{};
      if (!reader.read(encoded)) {
        throw std::runtime_error(
            "truncated creature-sprite catalog directory entry");
      }
      rawDirectory.insert(rawDirectory.end(), encoded.begin(), encoded.end());
      const auto animationId = encoded_field<std::uint32_t>(encoded, 0);
      CatalogDirectoryEntry entry;
      if (animationId == 0 || animationId >= kCatalogShardAnimationSentinel) {
        throw std::runtime_error(
            "invalid creature-sprite catalog directory animation");
      }
      entry.animationId = static_cast<std::uint16_t>(animationId);
      std::memcpy(entry.resref.data(), encoded.data() + 4,
                  entry.resref.size());
      entry.componentIndex = encoded_field<std::uint32_t>(encoded, 12);
      entry.shardIndex = encoded_field<std::uint32_t>(encoded, 16);
      entry.resourceOrdinal = encoded_field<std::uint32_t>(encoded, 20);
      const auto animation = std::lower_bound(
          catalog.animations.begin(), catalog.animations.end(),
          entry.animationId,
          [](const CatalogAnimation& item, std::uint16_t id) {
            return item.animationId < id;
          });
      if (animation == catalog.animations.end() ||
          animation->animationId != entry.animationId ||
          !canonical_catalog_resref(entry.resref)) {
        throw std::runtime_error(
            "invalid creature-sprite catalog directory key");
      }
      const auto animationIndex = static_cast<std::size_t>(
          std::distance(catalog.animations.begin(), animation));
      if (entry.componentIndex >= catalog.components.size() ||
          !animationComponents[animationIndex].contains(entry.componentIndex)) {
        throw std::runtime_error(
            "catalog directory references a non-member component");
      }
      const auto& component = catalog.components[entry.componentIndex];
      if (entry.shardIndex < component.shardStart ||
          entry.shardIndex >= component.shardStart + component.shardCount ||
          entry.resourceOrdinal >=
              catalog.shards[entry.shardIndex].resourceCount ||
          !occupiedOrdinals
               .insert({entry.animationId, entry.shardIndex,
                        entry.resourceOrdinal})
               .second) {
        throw std::runtime_error(
            "invalid creature-sprite catalog directory target");
      }
      if (havePrevious &&
          !(std::tie(previous.animationId, previous.resref) <
            std::tie(entry.animationId, entry.resref))) {
        throw std::runtime_error(
            "non-canonical creature-sprite catalog directory order");
      }
      previous = entry;
      havePrevious = true;
      ++actualDirectoryCounts[animationIndex];
      catalog.directory.push_back(entry);
    }
    if (actualDirectoryCounts != expectedDirectoryCounts ||
        catalog_directory_digest(catalog.scale, rawDirectory.data(),
                                 rawDirectory.size()) !=
            expectedDirectoryDigest) {
      throw std::runtime_error(
          "creature-sprite catalog directory digest/count mismatch");
    }
  }
  if (!reader.at_end()) {
    throw std::runtime_error("trailing creature-sprite catalog bytes");
  }
  FileIdentity finalCatalogIdentity{};
#ifdef _WIN32
  if (!query_open_file_identity(catalog.lease.handle, finalCatalogIdentity) ||
#else
  if (!query_file_identity(catalog.path, finalCatalogIdentity) ||
#endif
      finalCatalogIdentity != catalog.identity) {
    throw std::runtime_error("creature-sprite catalog changed during validation");
  }
  return catalog;
}

LoadedPack load_registry_set(const std::filesystem::path& assetsDirectory,
                             const std::filesystem::path& setPath) {
  const auto set = parse_registry_set(setPath);
  LoadedPack loaded{.scale = set.scale,
                    .animationId = set.animationId,
                    .frameCount = set.frameCount,
                    .indexBytes = set.indexBytes,
                    .lazyPayloads = true};
  loaded.resources.reserve(set.resourceCount);
  loaded.lazyShards.reserve(set.entries.size());
  std::set<std::array<char, 8>> resrefs;
  std::uint64_t resourceSum = 0;
  std::uint64_t frameSum = 0;
  std::uint64_t indexSum = 0;
  std::uint64_t registrySum = 0;
  for (std::uint32_t shardIndex = 0; shardIndex < set.entries.size(); ++shardIndex) {
    const auto shardPath = assetsDirectory / registry_shard_filename(shardIndex);
    auto shard = parse_registry(shardPath, RegistryFormat::Xn, true, shardIndex, true);
    const auto& expected = set.entries[shardIndex];
    if (shard.version != kXnRegistryVersion || shard.scale != set.scale ||
        shard.animationId != set.animationId ||
        shard.resourceCount != expected.resourceCount ||
        shard.frameCount != expected.frameCount || shard.indexBytes != expected.indexBytes ||
        shard.registryBytes != expected.registryBytes ||
        shard.checksum != expected.checksum || shard.sha256 != expected.sha256) {
      throw std::runtime_error("creature-sprite registry-set shard mismatch: " +
                               shardPath.filename().string());
    }
    for (const auto& resource : shard.resources) {
      if (!resrefs.insert(resource.resref).second) {
        throw std::runtime_error("duplicate creature-sprite resref across shards");
      }
    }
    if (!checked_add(resourceSum, shard.resourceCount, kMaximumRegistrySetResources) ||
        !checked_add(frameSum, shard.frameCount, kMaximumRegistrySetFrames) ||
        !checked_add(indexSum, shard.indexBytes, kMaximumRegistrySetBytes) ||
        !checked_add(registrySum, shard.registryBytes, kMaximumRegistrySetBytes)) {
      throw std::runtime_error("creature-sprite registry-set aggregate overflow");
    }
    loaded.lazyShards.push_back({.path = shardPath,
                                 .identity = shard.identity,
                                 .lease = std::move(shard.lease)});
    loaded.resources.insert(loaded.resources.end(),
                            std::make_move_iterator(shard.resources.begin()),
                            std::make_move_iterator(shard.resources.end()));
  }
  if (resourceSum != set.resourceCount || frameSum != set.frameCount ||
      indexSum != set.indexBytes || registrySum != set.registryBytes ||
      loaded.resources.size() != set.resourceCount) {
    throw std::runtime_error("creature-sprite registry-set loaded totals mismatch");
  }
  return loaded;
}

LoadedPack load_monolithic_registry(const std::filesystem::path& path,
                                    RegistryFormat format) {
  bool lazyPayloads = false;
  if (format == RegistryFormat::Xn) {
    std::ifstream input(path, std::ios::binary);
    std::array<char, 8> magic{};
    std::uint32_t version = 0;
    if (!input ||
        !input.read(magic.data(), static_cast<std::streamsize>(magic.size())) ||
        !input.read(reinterpret_cast<char*>(&version), sizeof(version)) ||
        magic != kXnRegistryMagic ||
        (version != kXnRegistryVersion &&
         version != kXnAntialiasRegistryVersion)) {
      throw std::runtime_error("invalid creature-sprite xN monolith prefix");
    }
    // V3 remains lazy. The initial V4 AA experiment is monolithic and keeps
    // its compact base indices plus recipes resident; registry-set support is
    // deliberately not inferred from the V3 set contract.
    lazyPayloads = version == kXnRegistryVersion;
  }
  auto parsed = parse_registry(path, format, lazyPayloads);
  LoadedPack loaded{.scale = parsed.scale,
                    .animationId = parsed.animationId,
                    .frameCount = parsed.frameCount,
                    .indexBytes = parsed.indexBytes,
                    .lazyPayloads = lazyPayloads,
                    .resources = std::move(parsed.resources)};
  if (lazyPayloads) {
    loaded.lazyShards.push_back({.path = path,
                                 .identity = parsed.identity,
                                 .lease = std::move(parsed.lease)});
  }
  return loaded;
}

std::uint32_t legacy_owner_for_animation(std::uint16_t animationId) noexcept {
  const auto family = animationId & 0xF000u;
  if (family == 0x5000u || family == 0x6000u) {
    return kCatalogCharacterOwner;
  }
  if (family == 0xE000u) return kCatalogMonsterIcewindOwner;
  if (family == 0x7000u) return kCatalogMonsterOwner;
  return 0;
}

CatalogAnimation* find_catalog_animation_locked(
    std::uint16_t animationId) noexcept {
  const auto found = std::find_if(
      g_catalog.animations.begin(), g_catalog.animations.end(),
      [&](const CatalogAnimation& animation) {
        return animation.animationId == animationId;
      });
  return found == g_catalog.animations.end() ? nullptr : &*found;
}

const CatalogAnimation* find_pack_animation_locked(
    std::uint16_t animationId) noexcept {
  const auto found = std::find_if(
      g_packAnimations.begin(), g_packAnimations.end(),
      [&](const CatalogAnimation& animation) {
        return animation.animationId == animationId;
      });
  return found == g_packAnimations.end() ? nullptr : &*found;
}

std::uint64_t catalog_metadata_bytes_locked() noexcept {
  std::uint64_t total = 0;
  for (const auto& shard : g_catalog.shards) {
    if (!checked_add(total, shard.residentMetadataBytes,
                     kCatalogMetadataCacheBudgetBytes)) {
      return (std::numeric_limits<std::uint64_t>::max)();
    }
  }
  return total;
}

std::uint64_t resource_metadata_bytes(
    const std::vector<Resource>& resources) noexcept {
  std::uint64_t total = 0;
  auto add = [&](std::uint64_t bytes) {
    return checked_add(total, bytes, kCatalogMetadataCacheBudgetBytes);
  };
  if (!add(static_cast<std::uint64_t>(resources.size()) * sizeof(Resource))) {
    return (std::numeric_limits<std::uint64_t>::max)();
  }
  for (const auto& resource : resources) {
    if (!add(static_cast<std::uint64_t>(resource.frames.size()) *
                 sizeof(Frame)) ||
        !add(static_cast<std::uint64_t>(resource.cycles.size()) *
             sizeof(std::vector<std::uint32_t>))) {
      return (std::numeric_limits<std::uint64_t>::max)();
    }
    for (const auto& cycle : resource.cycles) {
      if (!add(static_cast<std::uint64_t>(cycle.size()) *
               sizeof(std::uint32_t))) {
        return (std::numeric_limits<std::uint64_t>::max)();
      }
    }
  }
  return total;
}

void invalidate_catalog_shard_caches_locked(
    std::uint32_t shardIndex) noexcept {
  std::erase_if(g_lazyIndexCache, [&](const LazyIndexCacheEntry& entry) {
    return entry.handle.catalogShardIndex == shardIndex;
  });
  std::erase_if(g_compositePixelCache,
                [&](const CompositePixelCacheEntry& entry) {
                  for (std::size_t layer = 0; layer < entry.layerCount;
                       ++layer) {
                    if (entry.layers[layer].frame.catalogShardIndex ==
                        shardIndex) {
                      return true;
                    }
                  }
                  return false;
                });
  // Engine texture ids cannot be destroyed safely without the draw API. Their
  // old generation makes them impossible cache hits; put only victim entries
  // at the front of the reuse LRU and preserve every unrelated live entry.
  for (auto& entry : g_textureCache) {
    if (entry.handle.catalogShardIndex == shardIndex) entry.lastUse = 0;
  }
}

void evict_catalog_shard_locked(std::uint32_t shardIndex) noexcept {
  if (shardIndex >= g_catalog.shards.size()) return;
  auto& shard = g_catalog.shards[shardIndex];
  invalidate_catalog_shard_caches_locked(shardIndex);
  for (const auto resourceIndex : shard.resourceIndices) {
    if (resourceIndex < g_resources.size()) g_resources[resourceIndex] = {};
  }
  shard.residentMetadataBytes = 0;
  ++shard.generation;
  if (shard.status != CatalogShardEntry::Status::Quarantined) {
    shard.status = shard.directory.empty()
                       ? CatalogShardEntry::Status::Unprobed
                       : CatalogShardEntry::Status::DirectoryReady;
  }
  if (shardIndex < g_lazyShards.size()) {
    g_lazyShards[shardIndex].identity = {};
    g_lazyShards[shardIndex].lease.reset();
  }
}

void quarantine_catalog_component_locked(std::uint32_t componentIndex,
                                         const char* reason) noexcept {
  if (componentIndex >= g_catalog.components.size()) return;
  auto& component = g_catalog.components[componentIndex];
  component.quarantined = true;
  for (std::uint32_t offset = 0; offset < component.shardCount; ++offset) {
    const auto shardIndex = component.shardStart + offset;
    if (shardIndex >= g_catalog.shards.size()) continue;
    auto& shard = g_catalog.shards[shardIndex];
    evict_catalog_shard_locked(shardIndex);
    shard.status = CatalogShardEntry::Status::Quarantined;
  }
  if (!component.failureLogged) {
    component.failureLogged = true;
    LOG_WARN(
        "Creature sprite catalog component {} quarantined: {}; other validated "
        "components remain available and native rendering is retained",
        componentIndex, reason ? reason : "unknown component failure");
  }
}

bool make_catalog_metadata_room_locked(std::uint32_t incomingShard,
                                       std::uint64_t incomingBytes) noexcept {
  if (incomingBytes == 0 ||
      incomingBytes > kCatalogMetadataCacheBudgetBytes) {
    return false;
  }
  auto resident = catalog_metadata_bytes_locked();
  while (resident > kCatalogMetadataCacheBudgetBytes ||
         incomingBytes > kCatalogMetadataCacheBudgetBytes - resident) {
    auto victim = g_catalog.shards.end();
    for (auto candidate = g_catalog.shards.begin();
         candidate != g_catalog.shards.end(); ++candidate) {
      const auto index = static_cast<std::uint32_t>(
          std::distance(g_catalog.shards.begin(), candidate));
      if (index == incomingShard ||
          candidate->status != CatalogShardEntry::Status::Resident) {
        continue;
      }
      if (victim == g_catalog.shards.end() ||
          candidate->lastUse < victim->lastUse) {
        victim = candidate;
      }
    }
    if (victim == g_catalog.shards.end()) return false;
    const auto freed = victim->residentMetadataBytes;
    const auto victimIndex = static_cast<std::uint32_t>(
        std::distance(g_catalog.shards.begin(), victim));
    evict_catalog_shard_locked(victimIndex);
    if (freed > resident) return false;
    resident -= freed;
  }
  return true;
}

const CatalogDirectoryEntry* find_catalog_directory_entry_locked(
    std::uint16_t animationId, const std::array<char, 8>& resref) noexcept {
  const auto found = std::lower_bound(
      g_catalog.directory.begin(), g_catalog.directory.end(),
      std::tie(animationId, resref),
      [](const CatalogDirectoryEntry& entry, const auto& key) {
        return std::tie(entry.animationId, entry.resref) < key;
      });
  return found != g_catalog.directory.end() &&
                 found->animationId == animationId && found->resref == resref
             ? &*found
             : nullptr;
}

bool catalog_resident_resource_locked(
    std::uint16_t animationId, const std::array<char, 8>& resref,
    std::uint32_t& shardIndex, std::uint32_t& resourceOrdinal,
    std::size_t& resourceIndex) noexcept {
  const auto* animation = find_catalog_animation_locked(animationId);
  if (!animation) return false;
  if (g_catalog.version == kRegistryCatalogDirectoryVersion) {
    const auto* entry =
        find_catalog_directory_entry_locked(animationId, resref);
    if (!entry || entry->shardIndex >= g_catalog.shards.size()) return false;
    auto& shard = g_catalog.shards[entry->shardIndex];
    if (shard.status != CatalogShardEntry::Status::Resident ||
        entry->resourceOrdinal >= shard.resourceIndices.size()) {
      return false;
    }
    shardIndex = entry->shardIndex;
    resourceOrdinal = entry->resourceOrdinal;
    resourceIndex = shard.resourceIndices[resourceOrdinal];
    shard.lastUse = ++g_catalogMetadataUseCounter;
    return resourceIndex < g_resources.size() &&
           g_resources[resourceIndex].resref == resref;
  }
  for (std::uint32_t offset = 0; offset < animation->membershipCount;
       ++offset) {
    const auto componentIndex =
        g_catalog.memberships[animation->membershipStart + offset];
    if (componentIndex >= g_catalog.components.size() ||
        g_catalog.components[componentIndex].quarantined) {
      continue;
    }
    const auto& component = g_catalog.components[componentIndex];
    for (std::uint32_t shardOffset = 0;
         shardOffset < component.shardCount; ++shardOffset) {
      const auto candidateIndex = component.shardStart + shardOffset;
      auto& shard = g_catalog.shards[candidateIndex];
      if (shard.status != CatalogShardEntry::Status::Resident) continue;
      const auto found =
          std::find(shard.directory.begin(), shard.directory.end(), resref);
      if (found == shard.directory.end()) continue;
      resourceOrdinal = static_cast<std::uint32_t>(
          std::distance(shard.directory.begin(), found));
      if (resourceOrdinal >= shard.resourceIndices.size()) return false;
      shardIndex = candidateIndex;
      resourceIndex = shard.resourceIndices[resourceOrdinal];
      shard.lastUse = ++g_catalogMetadataUseCounter;
      return resourceIndex < g_resources.size() &&
             g_resources[resourceIndex].resref == resref;
    }
  }
  return false;
}

void queue_catalog_load_locked(std::uint16_t animationId,
                               const std::array<char, 8>& resref) {
  constexpr std::size_t kMaximumPendingRequests = 256;
  const auto* animation = find_catalog_animation_locked(animationId);
  if (!g_catalog.active || !animation) return;
  bool needsWorker = false;
  if (g_catalog.version == kRegistryCatalogDirectoryVersion) {
    const auto* entry = find_catalog_directory_entry_locked(animationId, resref);
    needsWorker = entry && entry->componentIndex < g_catalog.components.size() &&
                  !g_catalog.components[entry->componentIndex].quarantined;
  } else {
    // Once every V1 member shard has been probed, an absent resref is a cheap
    // synchronous negative lookup. Do not retain an unbounded cache of native
    // game resrefs that are intentionally outside this catalog.
    for (std::uint32_t offset = 0;
         !needsWorker && offset < animation->membershipCount; ++offset) {
      const auto componentIndex =
          g_catalog.memberships[animation->membershipStart + offset];
      if (componentIndex >= g_catalog.components.size() ||
          g_catalog.components[componentIndex].quarantined) {
        continue;
      }
      const auto& component = g_catalog.components[componentIndex];
      for (std::uint32_t shardOffset = 0;
           shardOffset < component.shardCount; ++shardOffset) {
        const auto& shard =
            g_catalog.shards[component.shardStart + shardOffset];
        if (shard.status == CatalogShardEntry::Status::Unprobed ||
            shard.status == CatalogShardEntry::Status::Loading ||
            std::find(shard.directory.begin(), shard.directory.end(), resref) !=
                shard.directory.end()) {
          needsWorker = true;
          break;
        }
      }
    }
  }
  if (!needsWorker) return;
  const auto key = std::make_pair(animationId, resref);
  if (g_catalogPendingRequests.contains(key) ||
      g_catalogLoadQueue.size() >= kMaximumPendingRequests) {
    return;
  }
  g_catalogPendingRequests.insert(key);
  g_catalogLoadQueue.push_back({.animationId = animationId, .resref = resref});
  g_catalogWorkChanged.notify_one();
}

bool catalog_shard_matches(const ParsedRegistry& parsed,
                           const CatalogShardEntry& expected,
                           std::uint32_t scale) noexcept {
  const bool identityMatches =
      expected.identity.bytes == 0 || parsed.identity == expected.identity;
  return (parsed.version == kXnRegistryVersion ||
          parsed.version == kXnCompressedRegistryVersion) &&
         parsed.scale == scale &&
         parsed.animationId == kCatalogShardAnimationSentinel &&
         parsed.resourceCount == expected.resourceCount &&
         parsed.frameCount == expected.frameCount &&
         parsed.indexBytes == expected.indexBytes &&
         parsed.registryBytes == expected.registryBytes &&
         parsed.checksum == expected.checksum &&
         parsed.sha256 == expected.sha256 && identityMatches;
}

bool load_catalog_shard_for_request(std::uint64_t epoch,
                                    std::uint32_t shardIndex,
                                    const CatalogLoadRequest& request,
                                    std::uint32_t expectedOrdinal) {
  CatalogShardEntry expected;
  std::uint32_t scale = 0;
  std::uint32_t catalogVersion = 0;
  {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) || !g_catalog.active ||
        g_catalog.epoch != epoch || shardIndex >= g_catalog.shards.size()) {
      return false;
    }
    auto& shard = g_catalog.shards[shardIndex];
    if (shard.status == CatalogShardEntry::Status::Resident) {
      if (expectedOrdinal < shard.resourceIndices.size() &&
          shard.resourceIndices[expectedOrdinal] < g_resources.size() &&
          g_resources[shard.resourceIndices[expectedOrdinal]].resref ==
              request.resref) {
        return true;
      }
      quarantine_catalog_component_locked(
          shard.componentIndex,
          "resident shard differs from the catalog directory target");
      return false;
    }
    if (shard.status == CatalogShardEntry::Status::Quarantined) return false;
    shard.status = CatalogShardEntry::Status::Loading;
    expected = shard;
    scale = g_catalog.scale;
    catalogVersion = g_catalog.version;
  }
  try {
    auto parsed = parse_registry(expected.path, RegistryFormat::Xn, true,
                                 shardIndex, true, true);
    if ((parsed.version == kXnCompressedRegistryVersion &&
         catalogVersion != kRegistryCatalogDirectoryVersion) ||
        !catalog_shard_matches(parsed, expected, scale) ||
        expectedOrdinal >= parsed.resources.size() ||
        parsed.resources[expectedOrdinal].resref != request.resref) {
      throw std::runtime_error(
          "catalog directory target differs from its V3/V5 shard");
    }
    const auto metadataBytes = resource_metadata_bytes(parsed.resources);
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) || !g_catalog.active ||
        g_catalog.epoch != epoch || shardIndex >= g_catalog.shards.size()) {
      return false;
    }
    auto& shard = g_catalog.shards[shardIndex];
    if (shard.status == CatalogShardEntry::Status::Quarantined) return false;
    if (!catalog_identity_matches_locked()) return false;
    if (!make_catalog_metadata_room_locked(shardIndex, metadataBytes)) {
      quarantine_catalog_component_locked(
          shard.componentIndex,
          "one shard exceeds the bounded metadata cache");
      return false;
    }
    if (!shard.directory.empty()) {
      if (shard.directory.size() != parsed.resources.size()) {
        quarantine_catalog_component_locked(
            shard.componentIndex,
            "catalog shard directory changed before validation");
        return false;
      }
      for (std::size_t index = 0; index < shard.directory.size(); ++index) {
        if (shard.directory[index] != parsed.resources[index].resref) {
          quarantine_catalog_component_locked(
              shard.componentIndex,
              "catalog shard directory differs from validated resources");
          return false;
        }
      }
    } else {
      shard.directory.reserve(parsed.resources.size());
      for (const auto& resource : parsed.resources) {
        shard.directory.push_back(resource.resref);
      }
    }
    if (shard.resourceIndices.empty()) {
      if (g_resources.size() > g_catalog.resourceCount ||
          parsed.resources.size() >
              g_catalog.resourceCount - g_resources.size()) {
        quarantine_catalog_component_locked(
            shard.componentIndex, "catalog resource slot bound exceeded");
        return false;
      }
      shard.resourceIndices.reserve(parsed.resources.size());
      for (std::size_t index = 0; index < parsed.resources.size(); ++index) {
        shard.resourceIndices.push_back(g_resources.size());
        g_resources.emplace_back();
      }
    }
    if (shard.resourceIndices.size() != parsed.resources.size()) {
      quarantine_catalog_component_locked(
          shard.componentIndex, "catalog resource slot count changed");
      return false;
    }
    for (std::size_t index = 0; index < parsed.resources.size(); ++index) {
      g_resources[shard.resourceIndices[index]] =
          std::move(parsed.resources[index]);
    }
    shard.identity = parsed.identity;
    if (shardIndex < g_lazyShards.size()) {
      g_lazyShards[shardIndex].identity = parsed.identity;
      g_lazyShards[shardIndex].lease = std::move(parsed.lease);
    }
    shard.residentMetadataBytes = metadataBytes;
    shard.lastUse = ++g_catalogMetadataUseCounter;
    ++shard.generation;
    shard.status = CatalogShardEntry::Status::Resident;
    LOG_INFO(
        "Creature sprite catalog shard {} ready on demand for animation "
        "0x{:04X}, resref {}: {} resources, {} metadata bytes",
        shardIndex, request.animationId, resref_name(request.resref),
        shard.resourceCount, metadataBytes);
    return true;
  } catch (const std::exception& error) {
    std::lock_guard lock(g_mutex);
    if (g_catalog.active && g_catalog.epoch == epoch &&
        shardIndex < g_catalog.shards.size()) {
      quarantine_catalog_component_locked(
          g_catalog.shards[shardIndex].componentIndex, error.what());
    }
  } catch (...) {
    std::lock_guard lock(g_mutex);
    if (g_catalog.active && g_catalog.epoch == epoch &&
        shardIndex < g_catalog.shards.size()) {
      quarantine_catalog_component_locked(
          g_catalog.shards[shardIndex].componentIndex,
          "unknown on-demand shard validation failure");
    }
  }
  return false;
}

void process_catalog_load_request(std::uint64_t epoch,
                                  const CatalogLoadRequest& request) {
  std::vector<std::uint32_t> candidates;
  bool directDirectory = false;
  std::uint32_t directOrdinal = 0;
  {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) || !g_catalog.active ||
        g_catalog.epoch != epoch ||
        !find_catalog_animation_locked(request.animationId)) {
      return;
    }
    if (g_catalog.version == kRegistryCatalogDirectoryVersion) {
      const auto* entry = find_catalog_directory_entry_locked(
          request.animationId, request.resref);
      if (!entry || entry->componentIndex >= g_catalog.components.size() ||
          g_catalog.components[entry->componentIndex].quarantined) {
        return;
      }
      candidates.push_back(entry->shardIndex);
      directOrdinal = entry->resourceOrdinal;
      directDirectory = true;
    } else {
      const auto* animation = find_catalog_animation_locked(request.animationId);
      for (std::uint32_t offset = 0; offset < animation->membershipCount;
           ++offset) {
        const auto componentIndex =
            g_catalog.memberships[animation->membershipStart + offset];
        if (componentIndex >= g_catalog.components.size() ||
            g_catalog.components[componentIndex].quarantined) {
          continue;
        }
        const auto& component = g_catalog.components[componentIndex];
        for (std::uint32_t shardOffset = 0;
             shardOffset < component.shardCount; ++shardOffset) {
          candidates.push_back(component.shardStart + shardOffset);
        }
      }
    }
  }
  if (directDirectory) {
    (void)load_catalog_shard_for_request(epoch, candidates.front(), request,
                                         directOrdinal);
    return;
  }

  std::vector<std::pair<std::uint32_t, std::uint32_t>> matches;
  for (const auto shardIndex : candidates) {
    bool mustProbe = false;
    CatalogShardEntry expected;
    std::uint32_t scale = 0;
    {
      std::lock_guard lock(g_mutex);
      if (!g_catalog.active || g_catalog.epoch != epoch ||
          shardIndex >= g_catalog.shards.size()) {
        return;
      }
      auto& shard = g_catalog.shards[shardIndex];
      if (shard.status == CatalogShardEntry::Status::Quarantined) continue;
      if (shard.status == CatalogShardEntry::Status::Unprobed) {
        shard.status = CatalogShardEntry::Status::Loading;
        expected = shard;
        scale = g_catalog.scale;
        mustProbe = true;
      }
    }
    if (mustProbe) {
      try {
        auto probed = probe_catalog_registry_directory(expected, scale);
        std::lock_guard lock(g_mutex);
        if (!g_catalog.active || g_catalog.epoch != epoch ||
            shardIndex >= g_catalog.shards.size()) {
          return;
        }
        auto& shard = g_catalog.shards[shardIndex];
        if (shard.status != CatalogShardEntry::Status::Quarantined) {
          shard.identity = probed.identity;
          shard.directory = std::move(probed.resrefs);
          shard.status = CatalogShardEntry::Status::DirectoryReady;
        }
      } catch (const std::exception& error) {
        std::lock_guard lock(g_mutex);
        if (g_catalog.active && g_catalog.epoch == epoch &&
            shardIndex < g_catalog.shards.size()) {
          quarantine_catalog_component_locked(
              g_catalog.shards[shardIndex].componentIndex, error.what());
        }
        continue;
      }
    }
    std::lock_guard lock(g_mutex);
    if (!g_catalog.active || g_catalog.epoch != epoch ||
        shardIndex >= g_catalog.shards.size()) {
      return;
    }
    const auto& shard = g_catalog.shards[shardIndex];
    if (shard.status == CatalogShardEntry::Status::Quarantined) continue;
    const auto found =
        std::find(shard.directory.begin(), shard.directory.end(), request.resref);
    if (found != shard.directory.end()) {
      matches.emplace_back(
          shardIndex, static_cast<std::uint32_t>(
                          std::distance(shard.directory.begin(), found)));
    }
  }
  if (matches.size() == 1) {
    (void)load_catalog_shard_for_request(epoch, matches.front().first, request,
                                         matches.front().second);
  } else if (matches.size() > 1) {
    std::lock_guard lock(g_mutex);
    for (const auto& match : matches) {
      if (match.first < g_catalog.shards.size()) {
        quarantine_catalog_component_locked(
            g_catalog.shards[match.first].componentIndex,
            "duplicate resref discovered in V1 animation mapping");
      }
    }
  }
}

void catalog_worker_loop(std::stop_token stopToken) noexcept {
  while (!stopToken.stop_requested()) {
    CatalogLoadRequest request;
    std::uint64_t epoch = 0;
    {
      std::unique_lock lock(g_mutex);
      g_catalogWorkChanged.wait(lock, stopToken, [] {
        return !g_catalogLoadQueue.empty();
      });
      if (stopToken.stop_requested()) break;
      if (g_catalogLoadQueue.empty()) continue;
      request = g_catalogLoadQueue.front();
      g_catalogLoadQueue.pop_front();
      epoch = g_catalog.epoch;
    }
    try {
      process_catalog_load_request(epoch, request);
    } catch (...) {
      // All parser/commit failures are normally handled at component scope.
      // The worker must never terminate the host process.
    }
    {
      std::lock_guard lock(g_mutex);
      const auto key = std::make_pair(request.animationId, request.resref);
      g_catalogPendingRequests.erase(key);
    }
  }
}

void stop_catalog_worker() noexcept {
  if (!g_catalogWorker.joinable()) return;
  g_catalogWorker.request_stop();
  g_catalogWorkChanged.notify_all();
  g_catalogWorker.join();
}

void activate_registry_catalog(CatalogState&& catalog) {
  stop_catalog_worker();
  {
    std::lock_guard lock(g_mutex);
    g_resources.clear();
    g_packAnimations.clear();
    g_catalog = std::move(catalog);
    g_catalog.epoch = ++g_catalogEpochCounter;
    g_lazyShards.clear();
    g_lazyShards.reserve(g_catalog.shards.size());
    for (const auto& shard : g_catalog.shards) {
      g_lazyShards.push_back({.path = shard.path, .identity = {}});
    }
    g_catalogLoadQueue.clear();
    g_catalogPendingRequests.clear();
    g_catalogMetadataUseCounter = 0;
    g_lazyPackLoaded = true;
    g_lazyPackFailureLogged = false;
    clear_texture_cache_locked();
    clear_lazy_index_cache_locked();
    close_frame_decompressor_locked();
    reset_diagnostics_locked();
    const auto uniqueAnimationId =
        g_catalog.animations.size() == 1
            ? g_catalog.animations.front().animationId
            : static_cast<std::uint16_t>(0);
    const bool targetsCharacter = std::any_of(
        g_catalog.animations.begin(), g_catalog.animations.end(),
        [](const CatalogAnimation& animation) {
          return animation.owner == kCatalogCharacterOwner;
        });
    const bool targetsMonsterIcewind = std::any_of(
        g_catalog.animations.begin(), g_catalog.animations.end(),
        [](const CatalogAnimation& animation) {
          return animation.owner == kCatalogMonsterIcewindOwner;
        });
    const bool targetsMonster = std::any_of(
        g_catalog.animations.begin(), g_catalog.animations.end(),
        [](const CatalogAnimation& animation) {
          return animation.owner == kCatalogMonsterOwner;
        });
    g_targetAnimationId.store(uniqueAnimationId, std::memory_order_release);
    g_loadedScale.store(g_catalog.scale, std::memory_order_release);
    g_targetsCharacter.store(targetsCharacter, std::memory_order_release);
    g_targetsMonster.store(targetsMonster, std::memory_order_release);
    g_targetsMonsterIcewind.store(targetsMonsterIcewind,
                                  std::memory_order_release);
    g_ready.store(true, std::memory_order_release);
  }
  g_catalogWorker = std::jthread(catalog_worker_loop);
}

void activate_loaded_pack(LoadedPack&& loaded) {
  stop_catalog_worker();
  std::lock_guard lock(g_mutex);
  g_catalog = {};
  g_catalogLoadQueue.clear();
  g_catalogPendingRequests.clear();
  g_resources = std::move(loaded.resources);
  g_packAnimations.clear();
  CatalogAnimation animation{
      .animationId = loaded.animationId,
      .owner = legacy_owner_for_animation(loaded.animationId),
      .loaded = true,
  };
  animation.resourceIndices.reserve(g_resources.size());
  for (std::size_t index = 0; index < g_resources.size(); ++index) {
    animation.resourceIndices.push_back(index);
  }
  g_packAnimations.push_back(std::move(animation));
  g_lazyShards = std::move(loaded.lazyShards);
  g_lazyPackLoaded = loaded.lazyPayloads;
  g_lazyPackFailureLogged = false;
  clear_texture_cache_locked();
  clear_lazy_index_cache_locked();
  close_frame_decompressor_locked();
  reset_diagnostics_locked();
  g_targetAnimationId.store(loaded.animationId, std::memory_order_release);
  g_loadedScale.store(loaded.scale, std::memory_order_release);
  g_targetsCharacter.store(
      legacy_owner_for_animation(loaded.animationId) == kCatalogCharacterOwner,
      std::memory_order_release);
  g_targetsMonster.store(
      legacy_owner_for_animation(loaded.animationId) == kCatalogMonsterOwner,
      std::memory_order_release);
  g_targetsMonsterIcewind.store(
      legacy_owner_for_animation(loaded.animationId) ==
          kCatalogMonsterIcewindOwner,
      std::memory_order_release);
  g_ready.store(true, std::memory_order_release);
}
}  // namespace

bool prepare(const std::filesystem::path& assetsDirectory) noexcept {
  try {
    const auto catalogPath = assetsDirectory / kRegistryCatalogFilename;
    const auto setPath = assetsDirectory / kRegistrySetFilename;
    const auto xnPath = assetsDirectory / kXnRegistryFilename;
    const auto legacyPath = assetsDirectory / kLegacyRegistryFilename;
    if (file_exists(catalogPath, "creature-sprite registry catalog")) {
      auto catalog = load_registry_catalog(assetsDirectory, catalogPath);
      const auto scale = catalog.scale;
      const auto catalogVersion = catalog.version;
      const auto animationCount = catalog.animations.size();
      const auto componentCount = catalog.components.size();
      const auto resourceCount = catalog.resourceCount;
      const auto frameCount = catalog.frameCount;
      const auto indexBytes = catalog.indexBytes;
      const auto shardCount = catalog.shards.size();
      const auto directoryCount = catalog.directory.size();
      activate_registry_catalog(std::move(catalog));
      LOG_INFO(
          "Creature sprite xBR catalog ready: scale=x{}, {} animations, {} "
          "components, {} resources, {} frames, {} index bytes across {} lazy "
          "content-addressed shards; catalog-version=V{}; {} authenticated directory "
          "entries; source={}; "
          "filter={}; index cache budget={} MiB; metadata cache budget={} MiB; "
          "shard validation=background-on-demand",
          scale, animationCount, componentCount, resourceCount,
          frameCount, indexBytes, shardCount, catalogVersion, directoryCount,
          kRegistryCatalogFilename,
          sampling_filter_name(),
          kLazyIndexCacheBudgetBytes / (1024ull * 1024ull),
          kCatalogMetadataCacheBudgetBytes / (1024ull * 1024ull));
      return true;
    }
    if (file_exists(setPath, "creature-sprite registry-set")) {
      auto loaded = load_registry_set(assetsDirectory, setPath);
      const auto scale = loaded.scale;
      const auto animationId = loaded.animationId;
      const auto resourceCount = loaded.resources.size();
      const auto frameCount = loaded.frameCount;
      const auto indexBytes = loaded.indexBytes;
      const auto shardCount = loaded.lazyShards.size();
      activate_loaded_pack(std::move(loaded));
      LOG_INFO(
          "Creature sprite xBR pack ready: animation 0x{:04X}, scale=x{}, {} resources, "
          "{} frames, {} index bytes across {} lazy shards; source={}; filter={}; "
          "index cache budget={} MiB",
          animationId, scale, resourceCount, frameCount, indexBytes, shardCount,
          kRegistrySetFilename, sampling_filter_name(),
          kLazyIndexCacheBudgetBytes / (1024ull * 1024ull));
      return true;
    }
    const bool xnExists = file_exists(xnPath, "creature-sprite xN registry");
    const auto& registryPath = xnExists ? xnPath : legacyPath;
    auto loaded = load_monolithic_registry(
        registryPath, xnExists ? RegistryFormat::Xn : RegistryFormat::Legacy);
    const auto scale = loaded.scale;
    const auto animationId = loaded.animationId;
    const auto resourceCount = loaded.resources.size();
    const auto frameCount = loaded.frameCount;
    const auto indexBytes = loaded.indexBytes;
    activate_loaded_pack(std::move(loaded));
    LOG_INFO(
        "Creature sprite xBR pack ready: animation 0x{:04X}, scale=x{}, {} resources, {} "
        "frames, {} index bytes; source={}; filter={}; registry budget={} MiB",
        animationId, scale, resourceCount, frameCount, indexBytes,
        registryPath.filename().string(), sampling_filter_name(),
        maximum_registry_bytes_for_scale(scale) / (1024ull * 1024ull));
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("Creature sprite xBR pack disabled: {}", error.what());
  } catch (...) {
    LOG_WARN("Creature sprite xBR pack disabled by an unknown error");
  }
  release();
  return false;
}

void configure_linear_filtering(bool enabled) noexcept {
  g_linearFiltering.store(enabled, std::memory_order_release);
}

void release() noexcept {
  stop_catalog_worker();
  std::lock_guard lock(g_mutex);
  g_ready.store(false, std::memory_order_release);
  g_targetAnimationId.store(0, std::memory_order_release);
  g_loadedScale.store(0, std::memory_order_release);
  g_targetsCharacter.store(false, std::memory_order_release);
  g_targetsMonster.store(false, std::memory_order_release);
  g_targetsMonsterIcewind.store(false, std::memory_order_release);
  g_resources.clear();
  g_packAnimations.clear();
  g_catalog = {};
  g_catalogLoadQueue.clear();
  g_catalogPendingRequests.clear();
  g_catalogMetadataUseCounter = 0;
  g_lazyShards.clear();
  g_lazyPackLoaded = false;
  g_lazyPackFailureLogged = false;
  clear_texture_cache_locked();
  clear_lazy_index_cache_locked();
  close_frame_decompressor_locked();
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

bool contains_animation(std::uint16_t animationId) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || animationId == 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) ||
        !catalog_identity_matches_locked()) {
      return false;
    }
    if (g_catalog.active) return find_catalog_animation_locked(animationId) != nullptr;
    return find_pack_animation_locked(animationId) != nullptr;
  } catch (...) {
    return false;
  }
}

bool animation_targets_character(std::uint16_t animationId) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || animationId == 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) ||
        !catalog_identity_matches_locked()) {
      return false;
    }
    const auto* animation = g_catalog.active
                                ? find_catalog_animation_locked(animationId)
                                : find_pack_animation_locked(animationId);
    return animation && animation->owner == kCatalogCharacterOwner;
  } catch (...) {
    return false;
  }
}

bool animation_targets_monster(std::uint16_t animationId) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || animationId == 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) ||
        !catalog_identity_matches_locked()) {
      return false;
    }
    const auto* animation = g_catalog.active
                                ? find_catalog_animation_locked(animationId)
                                : find_pack_animation_locked(animationId);
    return animation && animation->owner == kCatalogMonsterOwner;
  } catch (...) {
    return false;
  }
}

bool animation_targets_monster_icewind(std::uint16_t animationId) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || animationId == 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) ||
        !catalog_identity_matches_locked()) {
      return false;
    }
    const auto* animation = g_catalog.active
                                ? find_catalog_animation_locked(animationId)
                                : find_pack_animation_locked(animationId);
    return animation && animation->owner == kCatalogMonsterIcewindOwner;
  } catch (...) {
    return false;
  }
}

bool targets_character() noexcept {
  if (!g_ready.load(std::memory_order_acquire)) return false;
  try {
    std::lock_guard lock(g_mutex);
    return g_ready.load(std::memory_order_acquire) &&
           catalog_identity_matches_locked() &&
           g_targetsCharacter.load(std::memory_order_acquire);
  } catch (...) {
    return false;
  }
}

bool targets_monster() noexcept {
  if (!g_ready.load(std::memory_order_acquire)) return false;
  try {
    std::lock_guard lock(g_mutex);
    return g_ready.load(std::memory_order_acquire) &&
           catalog_identity_matches_locked() &&
           g_targetsMonster.load(std::memory_order_acquire);
  } catch (...) {
    return false;
  }
}

bool targets_monster_icewind() noexcept {
  if (!g_ready.load(std::memory_order_acquire)) return false;
  try {
    std::lock_guard lock(g_mutex);
    return g_ready.load(std::memory_order_acquire) &&
           catalog_identity_matches_locked() &&
           g_targetsMonsterIcewind.load(std::memory_order_acquire);
  } catch (...) {
    return false;
  }
}

bool contains_resource(std::uint16_t animationId,
                       const std::array<char, 8>& resref) noexcept {
  if (!g_ready.load(std::memory_order_acquire)) return false;
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) ||
        !catalog_identity_matches_locked()) {
      return false;
    }
    if (g_catalog.active) {
      if (!find_catalog_animation_locked(animationId)) return false;
      std::uint32_t shardIndex = 0;
      std::uint32_t resourceOrdinal = 0;
      std::size_t resourceIndex = 0;
      if (catalog_resident_resource_locked(animationId, resref, shardIndex,
                                           resourceOrdinal, resourceIndex)) {
        return true;
      }
      queue_catalog_load_locked(animationId, resref);
      if (g_catalog.version != kRegistryCatalogDirectoryVersion) return false;
      const auto* entry =
          find_catalog_directory_entry_locked(animationId, resref);
      return entry && entry->componentIndex < g_catalog.components.size() &&
             !g_catalog.components[entry->componentIndex].quarantined;
    }
    const auto* animation = find_pack_animation_locked(animationId);
    if (!animation) return false;
    return std::find_if(
               animation->resourceIndices.begin(),
               animation->resourceIndices.end(), [&](std::size_t index) {
                 return index < g_resources.size() &&
                        g_resources[index].resref == resref;
               }) != animation->resourceIndices.end();
  } catch (...) {
    return false;
  }
}

bool contains_resource(const std::array<char, 8>& resref) noexcept {
  const auto animationId = target_animation_id();
  return animationId != 0 && contains_resource(animationId, resref);
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

bool resolve_frame(std::uint16_t animationId,
                   const std::array<char, 8>& resref, int sequence,
                   int currentFrame, FrameHandle& out) noexcept {
  out = {};
  if (!g_ready.load(std::memory_order_acquire) || sequence < 0 || currentFrame < 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) ||
        !catalog_identity_matches_locked()) {
      return false;
    }
    std::size_t resourceIndex = 0;
    std::uint32_t catalogShardIndex = kResidentFrameShard;
    std::uint32_t resourceOrdinal = 0;
    std::uint64_t catalogGeneration = 0;
    if (g_catalog.active) {
      if (!find_catalog_animation_locked(animationId) ||
          !catalog_resident_resource_locked(
              animationId, resref, catalogShardIndex, resourceOrdinal,
              resourceIndex)) {
        queue_catalog_load_locked(animationId, resref);
        return false;
      }
      catalogGeneration = g_catalog.shards[catalogShardIndex].generation;
    } else {
      const auto* animation = find_pack_animation_locked(animationId);
      if (!animation) return false;
      const auto mapped = std::find_if(
          animation->resourceIndices.begin(), animation->resourceIndices.end(),
          [&](std::size_t index) {
            return index < g_resources.size() &&
                   g_resources[index].resref == resref;
          });
      if (mapped == animation->resourceIndices.end()) return false;
      resourceIndex = *mapped;
    }
    auto& resource = g_resources[resourceIndex];
    if (static_cast<std::size_t>(sequence) >= resource.cycles.size()) {
      return false;
    }
    const auto& cycle = resource.cycles[static_cast<std::size_t>(sequence)];
    if (static_cast<std::size_t>(currentFrame) >= cycle.size()) return false;
    const FrameHandle resolved{
        .resourceIndex = resourceIndex,
        .frameIndex = cycle[static_cast<std::size_t>(currentFrame)],
        .animationId = animationId,
        .catalogShardIndex = catalogShardIndex,
        .catalogGeneration = catalogGeneration,
    };
    if (resolved.frameIndex >= resource.frames.size() ||
        !validate_lazy_frame_source_locked(resolved)) {
      return false;
    }
    out = resolved;
    return true;
  } catch (...) {
    return false;
  }
}

bool resolve_frame(const std::array<char, 8>& resref, int sequence,
                   int currentFrame, FrameHandle& out) noexcept {
  const auto animationId = target_animation_id();
  if (animationId == 0) {
    out = {};
    return false;
  }
  return resolve_frame(animationId, resref, sequence, currentFrame, out);
}

bool ensure_frame_payload_available(FrameHandle handle) noexcept {
  if (!g_ready.load(std::memory_order_acquire)) return false;
  try {
    std::lock_guard lock(g_mutex);
    return g_ready.load(std::memory_order_acquire) &&
           frame_indices_locked(handle) != nullptr;
  } catch (...) {
    return false;
  }
}

std::uint64_t resident_index_bytes() noexcept {
  try {
    std::lock_guard lock(g_mutex);
    if (g_lazyPackLoaded) return lazy_index_cache_bytes_locked();
    std::uint64_t total = 0;
    for (const auto& resource : g_resources) {
      for (const auto& frame : resource.frames) {
        if (!checked_add(total, static_cast<std::uint64_t>(frame.indices.size()),
                         kMaximumRegistryBytes)) {
          return (std::numeric_limits<std::uint64_t>::max)();
        }
      }
    }
    return total;
  } catch (...) {
    return (std::numeric_limits<std::uint64_t>::max)();
  }
}

std::uint64_t resident_catalog_metadata_bytes() noexcept {
  try {
    std::lock_guard lock(g_mutex);
    return g_catalog.active ? catalog_metadata_bytes_locked() : 0;
  } catch (...) {
    return (std::numeric_limits<std::uint64_t>::max)();
  }
}

std::size_t pending_catalog_loads() noexcept {
  try {
    std::lock_guard lock(g_mutex);
    return g_catalogPendingRequests.size();
  } catch (...) {
    return (std::numeric_limits<std::size_t>::max)();
  }
}

std::uint64_t filesystem_access_count() noexcept {
  return g_filesystemAccessCounter.load(std::memory_order_relaxed);
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
    auto* resource = resource_for_handle_locked(handle);
    if (!g_ready.load(std::memory_order_acquire) || !resource ||
        handle.frameIndex >= resource->frames.size()) {
      return false;
    }
    const auto physicalScale = g_loadedScale.load(std::memory_order_acquire);
    if (!supported_physical_scale(physicalScale)) return false;
    const auto& frame = resource->frames[handle.frameIndex];
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
      for (auto& cachedResource : g_resources) {
        cachedResource.compositionLogged.clear();
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
    if (resource->compositionLogged.insert(handle.animationId).second) {
      LOG_INFO(
          "Composing creature sprite {} animation=0x{:04X} frame {:03}: scale=x{}, "
          "BAM logical {}x{}, "
          "upscaled content {}x{}, bordered texture {}x{} ({})",
          resref_name(resource->resref), handle.animationId, handle.frameIndex,
          physicalScale,
          frame.logicalWidth, frame.logicalHeight,
          static_cast<std::int64_t>(frame.logicalWidth) * physicalScale,
          static_cast<std::int64_t>(frame.logicalHeight) * physicalScale,
          physical_texture_extent(frame.logicalWidth, physicalScale),
          physical_texture_extent(frame.logicalHeight, physicalScale), sampling_filter_name());
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
    std::array<std::uint32_t, kMaximumCompositeLayers> validatedSources{};
    validatedSources.fill(kResidentFrameShard);
    std::size_t validatedSourceCount = 0;
    NativePixelEncoding encoding{};
    for (std::size_t index = 0; index < layerCount; ++index) {
      const auto& layer = layers[index];
      const auto* resource = resource_for_handle_locked(layer.frame);
      if (!resource || layer.frame.frameIndex >= resource->frames.size() ||
          !supported_native_pixel_encoding(layer.palette.encoding)) {
        return false;
      }
      if (index == 0) {
        encoding = layer.palette.encoding;
      } else if (layer.palette.encoding.externalFormat != encoding.externalFormat ||
                 layer.palette.encoding.type != encoding.type) {
        return false;
      }
      const auto& frame = resource->frames[layer.frame.frameIndex];
      if (frame.lazyShardIndex != kResidentFrameShard) {
        const bool alreadyValidated =
            std::find(validatedSources.begin(),
                      validatedSources.begin() +
                          static_cast<std::ptrdiff_t>(validatedSourceCount),
                      frame.lazyShardIndex) !=
            validatedSources.begin() +
                static_cast<std::ptrdiff_t>(validatedSourceCount);
        if (!alreadyValidated && !validate_lazy_frame_source_locked(layer.frame)) {
          return false;
        }
        if (!alreadyValidated) {
          validatedSources[validatedSourceCount++] = frame.lazyShardIndex;
        }
      }
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
        resource.compositionLogged.clear();
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
        api.DrawGenTexture(sampling_filter(), 0, 0, 0);
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
      auto* resource = resource_for_handle_locked(layer.frame);
      if (!resource || layer.frame.frameIndex >= resource->frames.size()) {
        return false;
      }
      if (!resource->compositionLogged.insert(layer.frame.animationId).second) {
        continue;
      }
      const auto& frame = resource->frames[layer.frame.frameIndex];
      LOG_INFO(
          "Composing creature sprite {} animation=0x{:04X} frame {:03} as "
          "Character composite layer {}/{}: scale=x{}, BAM logical {}x{}, final "
          "bordered texture {}x{} physical {}x{} via transient replacement id {} "
          "({}, delete-pending after queued draw)",
          resref_name(resource->resref), layer.frame.animationId,
          layer.frame.frameIndex, index + 1, layerCount, physicalScale,
          frame.logicalWidth, frame.logicalHeight, logicalWidth, logicalHeight,
          static_cast<std::int64_t>(logicalWidth) * physicalScale,
          static_cast<std::int64_t>(logicalHeight) * physicalScale,
          transientTextureId, sampling_filter_name());
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
    resource.compositionLogged.clear();
  }
}
}  // namespace iee::creature_sprite_x2
