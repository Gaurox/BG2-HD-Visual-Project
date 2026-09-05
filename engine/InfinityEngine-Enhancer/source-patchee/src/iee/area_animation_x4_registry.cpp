#include "area_animation_x4_registry.h"

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
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

namespace iee::area_animation_x4 {
namespace {
constexpr std::array<char, 8> kRegistryMagic{{'I', 'E', 'E', 'A', 'A', 'X', '4', '\0'}};
constexpr std::uint32_t kLegacyRegistryVersion = 1;
constexpr std::uint32_t kRegistryVersion = 2;
constexpr std::uint32_t kScale = 4;
constexpr std::size_t kTextureCacheLimit = 64;
constexpr std::uint32_t kMaxResources = 512;
constexpr std::uint32_t kMaxFramesPerResource = 4096;
constexpr std::uint32_t kMaxCyclesPerResource = 256;
constexpr std::uint32_t kMaxCycleSlots = 65536;
constexpr std::uint32_t kMaxRateComponent = 1000;
constexpr std::uint64_t kMaxRawBytes = 512ull * 1024ull * 1024ull;
constexpr std::size_t kCacheBudgetSimulationMaxFrames = 16384;
constexpr std::uint64_t kMiB = 1024ull * 1024ull;
struct CacheBudgetSimulationProfileConfig {
  std::uint64_t cpuBudgetBytes{};
  std::uint64_t gpuBudgetBytes{};
  std::size_t gpuEntryLimit{};
};
constexpr std::array<CacheBudgetSimulationProfileConfig,
                     kCacheBudgetSimulationProfileCount>
    kCacheBudgetSimulationProfiles{{
        {.cpuBudgetBytes = 64ull * kMiB,
         .gpuBudgetBytes = 96ull * kMiB,
         .gpuEntryLimit = 128},
        {.cpuBudgetBytes = 128ull * kMiB,
         .gpuBudgetBytes = 128ull * kMiB,
         .gpuEntryLimit = 128},
        {.cpuBudgetBytes = 128ull * kMiB,
         .gpuBudgetBytes = 128ull * kMiB,
         .gpuEntryLimit = 192},
        {.cpuBudgetBytes = 128ull * kMiB,
         .gpuBudgetBytes = 256ull * kMiB,
         .gpuEntryLimit = 192},
        {.cpuBudgetBytes = 192ull * kMiB,
         .gpuBudgetBytes = 256ull * kMiB,
         .gpuEntryLimit = 192},
    }};
// v3 keeps every v2 field and appends the optional world position that binds a resource to one
// occurrence. v1 and v2 stay loadable: packs already installed must not stop working.
constexpr std::uint32_t kPositionRegistryVersion = 3;

enum class PlaybackMode : std::uint32_t { Native = 0, TimedTimeline = 1 };

struct Frame {
  int logicalWidth{};
  int logicalHeight{};
  std::vector<std::byte> replacement;
};

struct Cycle {
  std::vector<std::uint32_t> nativeFrames;
  std::vector<std::uint32_t> timelineFrames;
};

struct Resource {
  std::array<char, 8> resref{};
  // A variant bound to a world position serves exactly one occurrence of its resref; an unbound
  // variant serves every other one. Several bound variants may share a resref, which is the whole
  // point: two occurrences of the same BAM can need different pixels when the decor in front of
  // them differs.
  bool positionBound{};
  std::int32_t worldX{};
  std::int32_t worldY{};
  // Disambiguates the asset filenames of several variants sharing one resref. Declared by the
  // registry rather than inferred from load order, so a writer that emits them in another order
  // is caught instead of silently reading the wrong bytes.
  std::uint32_t variantIndex{};
  std::size_t cacheBudgetSimulationFrameOffset{};
  std::string displayName;
  std::vector<Frame> frames;
  PlaybackMode playbackMode{PlaybackMode::Native};
  std::uint32_t nativeFpsNumerator{};
  std::uint32_t nativeFpsDenominator{};
  std::uint32_t targetFpsNumerator{};
  std::uint32_t targetFpsDenominator{};
  std::vector<Cycle> cycles;
  std::vector<bool> compositionLogged;
};

struct TextureCacheEntry {
  FrameHandle handle{};
  int textureId{};
  std::uint64_t lastUse{};
  std::uint64_t baseLevelBytes{};
};

struct PositionMiss {
  std::array<char, 8> resref{};
  int worldX{};
  int worldY{};
};

struct CacheBudgetSimulationState {
  bool attempted{};
  bool active{};
  std::uint64_t frameCapacity{};
  std::array<core::HierarchicalCacheBudgetSimulator,
             kCacheBudgetSimulationProfileCount>
      profiles;
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

  [[nodiscard]] bool at_end() const noexcept { return offset_ == bytes_.size(); }

 private:
  std::vector<std::byte> bytes_;
  std::size_t offset_{};
};

std::mutex g_mutex;
std::atomic<bool> g_ready{false};
std::vector<Resource> g_resources;
std::vector<PositionMiss> g_positionMisses;
std::vector<TextureCacheEntry> g_textureCache;
std::uint64_t g_textureUseCounter{};
TextureCacheTelemetryStats g_textureCacheTelemetry{.capacity = kTextureCacheLimit};
CacheBudgetSimulationState g_cacheBudgetSimulation;
bool g_creationFailureLogged = false;
// Engine texture names whose owning context is still alive but which no longer back a
// resident frame. Only the GL thread may delete them, so they wait here.
std::vector<int> g_retiredTextureIds;
std::atomic<bool> g_hasRetiredTextures{false};
std::filesystem::path g_areaPacksRoot;
bool g_perAreaPacks = false;
std::string g_residentArea;
std::uint64_t g_residentRawBytes{};
#ifdef _WIN32
HGLRC g_textureContext{};
HGLRC g_retiredContext{};
#endif

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

std::string frame_asset_name_v0(const std::string& resref, std::size_t frameIndex) {
  char name[64]{};
  const auto written = std::snprintf(name, sizeof(name), "AAX4-%s-frame%03zu.rgba",
                                     resref.c_str(), frameIndex);
  if (written <= 0 || static_cast<std::size_t>(written) >= sizeof(name)) {
    throw std::runtime_error("runtime frame asset name is too long");
  }
  return name;
}

// Variant 0 keeps the historical name, so every pack ever produced still resolves. Only the
// extra variants a v3 registry may declare need a suffix, and they need one: two variants of one
// resref must not read the same bytes, which is the entire reason they exist.
std::string frame_asset_name(const std::string& resref, std::size_t frameIndex,
                             std::uint32_t variantIndex) {
  if (variantIndex == 0) return frame_asset_name_v0(resref, frameIndex);
  char name[64]{};
  const auto written = std::snprintf(name, sizeof(name), "AAX4-%s-v%u-frame%03zu.rgba",
                                     resref.c_str(), variantIndex, frameIndex);
  if (written <= 0 || static_cast<std::size_t>(written) >= sizeof(name)) {
    throw std::runtime_error("runtime frame asset name is too long");
  }
  return name;
}

int logical_texture_id(const EngineTextureApi& api) noexcept {
  if (!api.glTextureState) return 0;
  std::uint32_t state = 0;
  if (!core::safe_read(api.glTextureState, state)) return 0;
  return static_cast<int>((state >> 21u) & 0x1FFu);
}

void refresh_texture_cache_residency_locked() noexcept {
  std::uint64_t residentBytes = 0;
  for (const TextureCacheEntry& entry : g_textureCache) {
    residentBytes += entry.baseLevelBytes;
  }
  g_textureCacheTelemetry.residentTextureNames =
      static_cast<std::uint64_t>(g_textureCache.size());
  g_textureCacheTelemetry.residentBaseLevelBytes = residentBytes;
  g_textureCacheTelemetry.peakResidentBaseLevelBytes =
      (std::max)(g_textureCacheTelemetry.peakResidentBaseLevelBytes, residentBytes);
}

TextureCacheTelemetryStats texture_cache_telemetry_snapshot_locked() noexcept {
  auto stats = g_textureCacheTelemetry;
  stats.active = g_ready.load(std::memory_order_relaxed);
  return stats;
}

void reset_texture_cache_telemetry_locked() noexcept {
  g_textureCacheTelemetry = {.capacity = kTextureCacheLimit};
  refresh_texture_cache_residency_locked();
}

void reset_cache_budget_simulation_locked() noexcept {
  g_cacheBudgetSimulation = {};
}

CacheBudgetSimulationSnapshot cache_budget_simulation_snapshot_locked() noexcept {
  CacheBudgetSimulationSnapshot snapshot{
      .active = g_cacheBudgetSimulation.active,
      .frameCapacity = g_cacheBudgetSimulation.frameCapacity,
  };
  if (!snapshot.active) return snapshot;
  for (std::size_t index = 0; index < snapshot.profiles.size(); ++index) {
    snapshot.profiles[index] = g_cacheBudgetSimulation.profiles[index].snapshot();
  }
  return snapshot;
}

bool initialise_cache_budget_simulation_locked() {
  if (g_cacheBudgetSimulation.attempted) return g_cacheBudgetSimulation.active;
  g_cacheBudgetSimulation.attempted = true;
  std::size_t frameCount = 0;
  for (const Resource& resource : g_resources) {
    if (resource.frames.size() > kCacheBudgetSimulationMaxFrames - frameCount) {
      LOG_WARN(
          "Area-animation cache budget simulation skipped: frame count exceeds bounded "
          "diagnostic capacity {}",
          kCacheBudgetSimulationMaxFrames);
      return false;
    }
    frameCount += resource.frames.size();
  }
  if (frameCount == 0) return false;

  for (std::size_t index = 0; index < g_cacheBudgetSimulation.profiles.size(); ++index) {
    const auto& config = kCacheBudgetSimulationProfiles[index];
    g_cacheBudgetSimulation.profiles[index].reset(
        frameCount, config.cpuBudgetBytes, config.gpuBudgetBytes,
        config.gpuEntryLimit);
  }
  g_cacheBudgetSimulation.frameCapacity = static_cast<std::uint64_t>(frameCount);
  g_cacheBudgetSimulation.active = true;
  return true;
}

void record_cache_budget_simulation_locked(FrameHandle handle,
                                           std::uint64_t frameBytes) noexcept {
  try {
    if (!initialise_cache_budget_simulation_locked() ||
        handle.resourceIndex >= g_resources.size()) {
      return;
    }
    const Resource& resource = g_resources[handle.resourceIndex];
    if (handle.frameIndex >= resource.frames.size()) return;
    const auto flatIndex = resource.cacheBudgetSimulationFrameOffset + handle.frameIndex;
    for (auto& profile : g_cacheBudgetSimulation.profiles) {
      profile.observe(flatIndex, frameBytes);
    }
  } catch (...) {
    // Diagnostics must never turn an otherwise valid x4 frame into a native
    // fallback. Disable only the shadow models for the resident area.
    reset_cache_budget_simulation_locked();
    g_cacheBudgetSimulation.attempted = true;
    LOG_WARN("Area-animation cache budget simulation disabled after an internal failure");
  }
}

void clear_cache_budget_simulation_gpu_locked() noexcept {
  if (!g_cacheBudgetSimulation.active) return;
  for (auto& profile : g_cacheBudgetSimulation.profiles) {
    profile.clear_gpu_residency();
  }
}

// Abandons the cached names. Callers must be certain the names are already invalid
// (context recreated, hooks torn down); otherwise use retire_texture_cache_locked().
void clear_texture_cache_locked(bool recordTelemetry = false) noexcept {
  if (recordTelemetry) {
    g_textureCacheTelemetry.contextInvalidatedTextureNames +=
        static_cast<std::uint64_t>(g_textureCache.size());
  }
  g_textureCache.clear();
  g_textureUseCounter = 0;
  refresh_texture_cache_residency_locked();
  clear_cache_budget_simulation_gpu_locked();
}

// Parks the cached names for deletion by the GL thread. Used when the pack is swapped
// while the owning context is still current, which is what an area transition does.
void retire_texture_cache_locked() noexcept {
  for (const TextureCacheEntry& entry : g_textureCache) {
    if (entry.textureId > 0) g_retiredTextureIds.push_back(entry.textureId);
  }
#ifdef _WIN32
  // Names belong to the context that created them. If that context is gone the names
  // may already have been reissued, so flushing must not delete them blindly.
  g_retiredContext = g_textureContext;
#endif
  g_hasRetiredTextures.store(!g_retiredTextureIds.empty(), std::memory_order_release);
  g_textureCache.clear();
  g_textureUseCounter = 0;
  refresh_texture_cache_residency_locked();
}

void drop_retired_textures_locked() noexcept {
  g_retiredTextureIds.clear();
  g_hasRetiredTextures.store(false, std::memory_order_release);
#ifdef _WIN32
  g_retiredContext = nullptr;
#endif
}

struct ReleaseSummary {
  std::string outgoingArea;
  std::uint64_t outgoingRawBytes{};
  std::uint64_t outgoingTextureNames{};
  std::uint64_t deferredTextureNames{};
  TextureCacheTelemetryStats outgoingTextureCache{};
  CacheBudgetSimulationSnapshot outgoingCacheBudgetSimulation{};
};

ReleaseSummary release_locked() {
  ReleaseSummary summary{
      .outgoingArea = g_residentArea,
      .outgoingRawBytes = g_residentRawBytes,
      .outgoingTextureNames = static_cast<std::uint64_t>(g_textureCache.size()),
      .outgoingTextureCache = texture_cache_telemetry_snapshot_locked(),
      .outgoingCacheBudgetSimulation = cache_budget_simulation_snapshot_locked(),
  };
  g_ready.store(false, std::memory_order_release);
  retire_texture_cache_locked();
#ifdef _WIN32
  g_textureContext = nullptr;
#endif
  g_resources.clear();
  g_resources.shrink_to_fit();
  g_positionMisses.clear();
  g_residentArea.clear();
  g_residentRawBytes = 0;
  g_creationFailureLogged = false;
  summary.deferredTextureNames = static_cast<std::uint64_t>(g_retiredTextureIds.size());
  reset_texture_cache_telemetry_locked();
  reset_cache_budget_simulation_locked();
  return summary;
}

using TelemetryClock = std::chrono::steady_clock;

double elapsed_milliseconds(TelemetryClock::time_point start,
                            TelemetryClock::time_point end) noexcept {
  return std::chrono::duration<double, std::milli>(end - start).count();
}

void log_texture_cache_telemetry(std::string_view area, std::string_view reason,
                                 const TextureCacheTelemetryStats& stats) {
  LOG_INFO(
      "Area-animation GPU cache telemetry: area={}, reason={}, capacity={}, requests={}, "
      "hits={}, misses={}, textureNameCreations={}, textureNameCreationFailures={}, "
      "uploadAttempts={}, successfulUploads={}, failedUploads={}, lruEvictions={}, "
      "failedUploadTextureDeletes={}, contextInvalidatedTextureNames={}, "
      "uploadedBaseLevelBytes={}, residentTextureNames={}, residentBaseLevelBytes={}, "
      "peakResidentBaseLevelBytes={}",
      area, reason, stats.capacity, stats.requests, stats.hits, stats.misses,
      stats.textureNameCreations, stats.textureNameCreationFailures, stats.uploadAttempts,
      stats.successfulUploads, stats.failedUploads, stats.lruEvictions,
      stats.failedUploadTextureDeletes, stats.contextInvalidatedTextureNames,
      stats.uploadedBaseLevelBytes, stats.residentTextureNames, stats.residentBaseLevelBytes,
      stats.peakResidentBaseLevelBytes);
}

void log_cache_budget_simulation(std::string_view area, std::string_view reason,
                                 const CacheBudgetSimulationSnapshot& snapshot) {
  if (!snapshot.active) return;
  for (const auto& profile : snapshot.profiles) {
    LOG_INFO(
        "Area-animation cache budget simulation: area={}, reason={}, frameCapacity={}, "
        "cpuBudgetBytes={}, gpuBudgetBytes={}, gpuEntryLimit={}, requests={}, "
        "distinctFrames={}, predictedFrameReadBytes={}, predictedUploadBytes={}, "
        "cpuRequests={}, cpuHits={}, cpuMisses={}, cpuEvictions={}, "
        "cpuUncacheableRequests={}, cpuResidentEntries={}, cpuResidentBytes={}, "
        "cpuPeakResidentBytes={}, gpuHits={}, gpuMisses={}, gpuEvictions={}, "
        "gpuUncacheableRequests={}, gpuResidentEntries={}, gpuResidentBytes={}, "
        "gpuPeakResidentBytes={}",
        area, reason, snapshot.frameCapacity, profile.cpu.budgetBytes,
        profile.gpu.budgetBytes, profile.gpu.entryLimit, profile.requests,
        profile.distinctFrames, profile.predictedFrameReadBytes,
        profile.predictedUploadBytes, profile.cpu.requests, profile.cpu.hits,
        profile.cpu.misses, profile.cpu.evictions, profile.cpu.uncacheableRequests,
        profile.cpu.residentEntries, profile.cpu.residentBytes,
        profile.cpu.peakResidentBytes, profile.gpu.hits, profile.gpu.misses,
        profile.gpu.evictions, profile.gpu.uncacheableRequests,
        profile.gpu.residentEntries, profile.gpu.residentBytes,
        profile.gpu.peakResidentBytes);
  }
}

void log_pack_process_resource_telemetry(std::string_view area,
                                         const PackPreparationStats& stats) {
  const bool memoryAvailable = stats.processBefore.memoryAvailable &&
                               stats.processAtCoexistence.memoryAvailable &&
                               stats.processAfterSwap.memoryAvailable;
  const bool ioAvailable =
      stats.processBefore.ioAvailable && stats.processAfterSwap.ioAvailable;
  const auto workingSetDelta =
      memoryAvailable
          ? core::signed_resource_delta(stats.processBefore.workingSetBytes,
                                        stats.processAfterSwap.workingSetBytes)
          : 0;
  const auto privateDelta =
      memoryAvailable
          ? core::signed_resource_delta(stats.processBefore.privateBytes,
                                        stats.processAfterSwap.privateBytes)
          : 0;
  const auto pageFaultsDelta =
      memoryAvailable
          ? core::monotonic_resource_delta(stats.processBefore.pageFaults,
                                           stats.processAfterSwap.pageFaults)
          : 0;
  const auto readOperationsDelta =
      ioAvailable
          ? core::monotonic_resource_delta(stats.processBefore.readOperations,
                                           stats.processAfterSwap.readOperations)
          : 0;
  const auto readTransferBytesDelta =
      ioAvailable
          ? core::monotonic_resource_delta(stats.processBefore.readTransferBytes,
                                           stats.processAfterSwap.readTransferBytes)
          : 0;
  const auto writeOperationsDelta =
      ioAvailable
          ? core::monotonic_resource_delta(stats.processBefore.writeOperations,
                                           stats.processAfterSwap.writeOperations)
          : 0;
  const auto writeTransferBytesDelta =
      ioAvailable
          ? core::monotonic_resource_delta(stats.processBefore.writeTransferBytes,
                                           stats.processAfterSwap.writeTransferBytes)
          : 0;
  LOG_INFO(
      "Area-animation process resource telemetry: area={}, reason=pack-load, "
      "memoryAvailable={}, workingSetBeforeBytes={}, workingSetAtCoexistenceBytes={}, "
      "workingSetAfterSwapBytes={}, workingSetDeltaBytes={}, privateBeforeBytes={}, "
      "privateAtCoexistenceBytes={}, privateAfterSwapBytes={}, privateDeltaBytes={}, "
      "peakWorkingSetAfterBytes={}, pageFaultsDelta={}, ioAvailable={}, "
      "readOperationsDelta={}, readTransferBytesDelta={}, writeOperationsDelta={}, "
      "writeTransferBytesDelta={}",
      area, memoryAvailable, stats.processBefore.workingSetBytes,
      stats.processAtCoexistence.workingSetBytes,
      stats.processAfterSwap.workingSetBytes, workingSetDelta,
      stats.processBefore.privateBytes, stats.processAtCoexistence.privateBytes,
      stats.processAfterSwap.privateBytes, privateDelta,
      stats.processAfterSwap.peakWorkingSetBytes, pageFaultsDelta, ioAvailable,
      readOperationsDelta, readTransferBytesDelta, writeOperationsDelta,
      writeTransferBytesDelta);
}

std::string normalised_area_name(std::string_view value) {
  std::string result;
  for (const char character : value) {
    if (character == '\0') break;
    if (!(static_cast<unsigned char>(character) < 128) ||
        !(std::isalnum(static_cast<unsigned char>(character)) != 0)) {
      return {};
    }
    result.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(character))));
  }
  return (result.empty() || result.size() > 8) ? std::string{} : result;
}

void delete_texture_entry_locked(const EngineTextureApi& api, std::size_t entryIndex,
                                 bool recordTelemetry) noexcept {
  if (entryIndex >= g_textureCache.size()) return;
  const int textureId = g_textureCache[entryIndex].textureId;
  if (textureId > 0 && api.DrawDeleteTexture) {
    api.DrawDeleteTexture(textureId);
    if (recordTelemetry) ++g_textureCacheTelemetry.failedUploadTextureDeletes;
  }
  g_textureCache.erase(g_textureCache.begin() + static_cast<std::ptrdiff_t>(entryIndex));
  refresh_texture_cache_residency_locked();
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
  if (expectedBytes != frame.replacement.size()) return false;

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

  api.DrawBindTexture(textureId);
  api.TexImage(frame.logicalWidth, frame.logicalHeight, nullptr, 0);
  int boundTexture = 0;
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &boundTexture);
  if (boundTexture <= 0 || gl.glGetError() != game::gl::GL_NO_ERROR) {
    restoreState();
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
  restoreState();
  return success;
}

bool ensure_texture_locked(FrameHandle handle, const EngineTextureApi& api,
                           int previousTextureId, int& textureId,
                           bool recordTelemetry) noexcept {
  textureId = 0;
  if (recordTelemetry) ++g_textureCacheTelemetry.requests;
  const auto& resource = g_resources[handle.resourceIndex];
  const auto& frame = resource.frames[handle.frameIndex];
  if (recordTelemetry) {
    record_cache_budget_simulation_locked(
        handle, static_cast<std::uint64_t>(frame.replacement.size()));
  }
  const auto existing = std::find_if(
      g_textureCache.begin(), g_textureCache.end(),
      [&](const TextureCacheEntry& entry) { return entry.handle == handle; });
  if (existing != g_textureCache.end()) {
    if (recordTelemetry) ++g_textureCacheTelemetry.hits;
    existing->lastUse = ++g_textureUseCounter;
    textureId = existing->textureId;
    return textureId > 0;
  }
  if (recordTelemetry) ++g_textureCacheTelemetry.misses;

  std::size_t entryIndex = 0;
  bool newTexture = g_textureCache.size() < kTextureCacheLimit;
  if (newTexture) {
    const int generated = api.DrawGenTexture(static_cast<int>(game::gl::LINEAR), 0, 0, 0);
    if (generated <= 0) {
      if (recordTelemetry) ++g_textureCacheTelemetry.textureNameCreationFailures;
      return false;
    }
    if (recordTelemetry) ++g_textureCacheTelemetry.textureNameCreations;
    g_textureCache.push_back(
        {.handle = handle, .textureId = generated, .lastUse = 0, .baseLevelBytes = 0});
    entryIndex = g_textureCache.size() - 1;
  } else {
    const auto lru = std::min_element(
        g_textureCache.begin(), g_textureCache.end(),
        [](const TextureCacheEntry& left, const TextureCacheEntry& right) {
          return left.lastUse < right.lastUse;
        });
    entryIndex = static_cast<std::size_t>(std::distance(g_textureCache.begin(), lru));
    lru->handle = handle;
    if (recordTelemetry) ++g_textureCacheTelemetry.lruEvictions;
  }

  auto& entry = g_textureCache[entryIndex];
  if (recordTelemetry) ++g_textureCacheTelemetry.uploadAttempts;
  if (!upload_frame_locked(frame, entry.textureId, api, previousTextureId)) {
    if (recordTelemetry) ++g_textureCacheTelemetry.failedUploads;
    delete_texture_entry_locked(api, entryIndex, recordTelemetry);
    api.DrawBindTexture(previousTextureId);
    return false;
  }
  entry.baseLevelBytes = static_cast<std::uint64_t>(frame.replacement.size());
  if (recordTelemetry) {
    ++g_textureCacheTelemetry.successfulUploads;
    g_textureCacheTelemetry.uploadedBaseLevelBytes += entry.baseLevelBytes;
  }
  refresh_texture_cache_residency_locked();
  entry.lastUse = ++g_textureUseCounter;
  textureId = entry.textureId;
  LOG_DEBUG("Area animation x4 texture {}: {} frame {:03}, logical {}x{}, physical {}x{}{}",
            textureId, resource.displayName, handle.frameIndex, frame.logicalWidth,
            frame.logicalHeight, frame.logicalWidth * kScale, frame.logicalHeight * kScale,
            newTexture ? "" : " (LRU reuse)");
  return true;
}
}  // namespace

bool prepare(const std::filesystem::path& assetsDirectory,
             PackPreparationStats* stats) noexcept {
  if (stats) {
    *stats = {};
    stats->processBefore = core::capture_process_resource_snapshot();
  }
  const auto totalStarted = stats ? TelemetryClock::now() : TelemetryClock::time_point{};
  try {
    const auto registryReadStarted =
        stats ? TelemetryClock::now() : TelemetryClock::time_point{};
    auto registryPayload = read_file(assetsDirectory / "AreaAnimations-X4.registry");
    if (stats) {
      stats->registryReadMilliseconds =
          elapsed_milliseconds(registryReadStarted, TelemetryClock::now());
      stats->registryBytes = static_cast<std::uint64_t>(registryPayload.size());
    }
    BinaryReader reader(std::move(registryPayload));
    std::array<char, 8> magic{};
    std::uint32_t version = 0;
    std::uint32_t scale = 0;
    std::uint32_t resourceCount = 0;
    std::uint32_t reserved = 0;
    if (!reader.read(magic) || !reader.read(version) || !reader.read(scale) ||
        !reader.read(resourceCount) || !reader.read(reserved) || magic != kRegistryMagic ||
        (version != kLegacyRegistryVersion && version != kRegistryVersion &&
         version != kPositionRegistryVersion) || scale != kScale ||
        reserved != 0 || resourceCount == 0 || resourceCount > kMaxResources) {
      throw std::runtime_error("invalid AreaAnimations-X4.registry header");
    }

    std::vector<Resource> loaded;
    loaded.reserve(resourceCount);
    std::uint64_t totalRawBytes = 0;
    std::size_t totalFrames = 0;
    std::size_t timedResources = 0;
    for (std::uint32_t resourceIndex = 0; resourceIndex < resourceCount; ++resourceIndex) {
      Resource resource;
      std::uint32_t frameCount = 0;
      std::uint32_t cycleCount = 0;
      if (!reader.read(resource.resref) || !reader.read(frameCount) || !reader.read(cycleCount) ||
          frameCount == 0 || frameCount > kMaxFramesPerResource || cycleCount == 0 ||
          cycleCount > kMaxCyclesPerResource) {
        throw std::runtime_error("invalid area-animation resource header");
      }
      if (version == kRegistryVersion || version == kPositionRegistryVersion) {
        std::uint32_t playbackMode = 0;
        if (!reader.read(playbackMode) || !reader.read(resource.nativeFpsNumerator) ||
            !reader.read(resource.nativeFpsDenominator) ||
            !reader.read(resource.targetFpsNumerator) ||
            !reader.read(resource.targetFpsDenominator) ||
            playbackMode > static_cast<std::uint32_t>(PlaybackMode::TimedTimeline)) {
          throw std::runtime_error("invalid area-animation playback header");
        }
        resource.playbackMode = static_cast<PlaybackMode>(playbackMode);
        const bool nativeMode = resource.playbackMode == PlaybackMode::Native;
        const bool emptyRate = resource.nativeFpsNumerator == 0 &&
                               resource.nativeFpsDenominator == 0 &&
                               resource.targetFpsNumerator == 0 &&
                               resource.targetFpsDenominator == 0;
        const bool validTimedRate = resource.nativeFpsNumerator > 0 &&
                                    resource.nativeFpsNumerator <= kMaxRateComponent &&
                                    resource.nativeFpsDenominator > 0 &&
                                    resource.nativeFpsDenominator <= kMaxRateComponent &&
                                    resource.targetFpsNumerator > 0 &&
                                    resource.targetFpsNumerator <= kMaxRateComponent &&
                                    resource.targetFpsDenominator > 0 &&
                                    resource.targetFpsDenominator <= kMaxRateComponent;
        if ((nativeMode && !emptyRate) || (!nativeMode && !validTimedRate)) {
          throw std::runtime_error("invalid area-animation playback rate");
        }
      }
      if (version == kPositionRegistryVersion) {
        std::uint32_t positionMode = 0;
        if (!reader.read(positionMode) || !reader.read(resource.worldX) ||
            !reader.read(resource.worldY) || !reader.read(resource.variantIndex) ||
            positionMode > 1 || resource.variantIndex >= kMaxResources) {
          throw std::runtime_error("invalid area-animation position header");
        }
        resource.positionBound = positionMode == 1;
        // An unbound variant must not smuggle a position: it would read as meaningful later.
        if (!resource.positionBound && (resource.worldX != 0 || resource.worldY != 0)) {
          throw std::runtime_error("unbound area-animation resource carries a position");
        }
      }
      resource.displayName = resref_name(resource.resref);
      // A resref may now appear several times, but each appearance must be distinguishable:
      // at most one unbound variant, and no two bound variants on the same spot. Anything else
      // would make resolution depend on load order, which is not a contract we can keep.
      if (resource.displayName.empty() ||
          std::any_of(loaded.begin(), loaded.end(), [&](const Resource& candidate) {
            if (candidate.resref != resource.resref) return false;
            if (candidate.variantIndex == resource.variantIndex) return true;
            if (candidate.positionBound != resource.positionBound) return false;
            if (!resource.positionBound) return true;
            return candidate.worldX == resource.worldX && candidate.worldY == resource.worldY;
          })) {
        throw std::runtime_error("empty or duplicate area-animation resref");
      }

      resource.cacheBudgetSimulationFrameOffset = totalFrames;
      resource.frames.reserve(frameCount);
      for (std::uint32_t frameIndex = 0; frameIndex < frameCount; ++frameIndex) {
        std::uint32_t logicalWidth = 0;
        std::uint32_t logicalHeight = 0;
        if (!reader.read(logicalWidth) || !reader.read(logicalHeight) || logicalWidth == 0 ||
            logicalHeight == 0 || logicalWidth > 8192 || logicalHeight > 8192) {
          throw std::runtime_error("invalid area-animation frame dimensions");
        }
        const auto physicalWidth = static_cast<std::uint64_t>(logicalWidth) * kScale;
        const auto physicalHeight = static_cast<std::uint64_t>(logicalHeight) * kScale;
        const auto rawBytes = physicalWidth * physicalHeight * 4ull;
        if (rawBytes > kMaxRawBytes || totalRawBytes > kMaxRawBytes - rawBytes) {
          throw std::runtime_error("area-animation runtime pack exceeds memory limit");
        }
        const auto frameReadStarted =
            stats ? TelemetryClock::now() : TelemetryClock::time_point{};
        auto pixels = read_file(
            assetsDirectory /
                frame_asset_name(resource.displayName, frameIndex, resource.variantIndex),
            rawBytes);
        if (stats) {
          stats->frameReadMilliseconds +=
              elapsed_milliseconds(frameReadStarted, TelemetryClock::now());
          ++stats->frameFiles;
          stats->frameBytes += rawBytes;
        }
        totalRawBytes += rawBytes;
        resource.frames.push_back({.logicalWidth = static_cast<int>(logicalWidth),
                                   .logicalHeight = static_cast<int>(logicalHeight),
                                   .replacement = std::move(pixels)});
      }

      resource.cycles.reserve(cycleCount);
      for (std::uint32_t cycleIndex = 0; cycleIndex < cycleCount; ++cycleIndex) {
        std::uint32_t slotCount = 0;
        if (!reader.read(slotCount) || slotCount == 0 || slotCount > kMaxCycleSlots) {
          throw std::runtime_error("invalid area-animation cycle length");
        }
        Cycle cycle;
        cycle.nativeFrames.resize(slotCount);
        for (auto& frameIndex : cycle.nativeFrames) {
          if (!reader.read(frameIndex) || frameIndex >= frameCount) {
            throw std::runtime_error("invalid area-animation cycle frame index");
          }
        }
        if (version == kRegistryVersion || version == kPositionRegistryVersion) {
          std::uint32_t timelineCount = 0;
          if (!reader.read(timelineCount) || timelineCount > kMaxCycleSlots) {
            throw std::runtime_error("invalid area-animation timeline length");
          }
          cycle.timelineFrames.resize(timelineCount);
          for (auto& frameIndex : cycle.timelineFrames) {
            if (!reader.read(frameIndex) || frameIndex >= frameCount) {
              throw std::runtime_error("invalid area-animation timeline frame index");
            }
          }
          if (resource.playbackMode == PlaybackMode::Native && timelineCount != 0) {
            throw std::runtime_error("native area-animation contains a timed timeline");
          }
          if (resource.playbackMode == PlaybackMode::TimedTimeline) {
            if (timelineCount == 0) {
              throw std::runtime_error("timed area-animation has an empty timeline");
            }
            const std::uint64_t timelineDurationLeft =
                static_cast<std::uint64_t>(timelineCount) * resource.nativeFpsNumerator *
                resource.targetFpsDenominator;
            const std::uint64_t nativeDurationRight =
                static_cast<std::uint64_t>(slotCount) * resource.targetFpsNumerator *
                resource.nativeFpsDenominator;
            if (timelineDurationLeft != nativeDurationRight) {
              throw std::runtime_error("timed area-animation duration mismatch");
            }
          }
        }
        resource.cycles.push_back(std::move(cycle));
      }
      if (resource.playbackMode == PlaybackMode::TimedTimeline) ++timedResources;
      resource.compositionLogged.assign(frameCount, false);
      totalFrames += frameCount;
      loaded.push_back(std::move(resource));
    }
    if (!reader.at_end()) throw std::runtime_error("trailing bytes in area-animation registry");

    if (stats) {
      stats->processAtCoexistence = core::capture_process_resource_snapshot();
    }
    const auto swapStarted = stats ? TelemetryClock::now() : TelemetryClock::time_point{};
    {
      std::lock_guard lock(g_mutex);
      if (stats) {
        stats->outgoingRawBytes = g_residentRawBytes;
        stats->residentRawBytes = totalRawBytes;
        stats->peakRawBytes = g_residentRawBytes + totalRawBytes;
        stats->resourceCount = static_cast<std::uint64_t>(resourceCount);
        stats->timedResourceCount = static_cast<std::uint64_t>(timedResources);
        stats->frameCount = static_cast<std::uint64_t>(totalFrames);
        stats->outgoingTextureNames =
            static_cast<std::uint64_t>(g_textureCache.size());
        stats->outgoingTextureCache = texture_cache_telemetry_snapshot_locked();
        stats->outgoingCacheBudgetSimulation =
            cache_budget_simulation_snapshot_locked();
      }
      g_ready.store(false, std::memory_order_release);
      g_resources = std::move(loaded);
      g_positionMisses.clear();
      // A reload happens while the render context is live, so the outgoing textures are
      // parked for the GL thread rather than abandoned. At first load the cache is empty
      // and this is a no-op.
      retire_texture_cache_locked();
      reset_texture_cache_telemetry_locked();
      reset_cache_budget_simulation_locked();
      g_residentRawBytes = totalRawBytes;
      if (stats) {
        stats->deferredTextureNames =
            static_cast<std::uint64_t>(g_retiredTextureIds.size());
      }
      g_creationFailureLogged = false;
#ifdef _WIN32
      g_textureContext = nullptr;
#endif
      g_ready.store(true, std::memory_order_release);
    }
    if (stats) {
      stats->processAfterSwap = core::capture_process_resource_snapshot();
      const auto finished = TelemetryClock::now();
      stats->swapMilliseconds = elapsed_milliseconds(swapStarted, finished);
      stats->totalMilliseconds = elapsed_milliseconds(totalStarted, finished);
      stats->parseAndAllocateMilliseconds =
          std::max(0.0, stats->totalMilliseconds - stats->registryReadMilliseconds -
                            stats->frameReadMilliseconds - stats->swapMilliseconds);
    }
    LOG_INFO(
             "Prepared area-animation x4 runtime pack v{}: {} BAM, {} timed, {} frames, "
             "{:.2f} MiB raw",
             version, g_resources.size(), timedResources, totalFrames,
             static_cast<double>(totalRawBytes) / (1024.0 * 1024.0));
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("Area-animation x4 runtime pack disabled: {}", error.what());
  } catch (...) {
    LOG_WARN("Area-animation x4 runtime pack disabled by an unknown loading error");
  }
  // prepare() may also be used for a guarded reload. Never leave a previously
  // loaded pack active after a malformed replacement was presented.
  release();
  return false;
}

void release() noexcept {
  std::lock_guard lock(g_mutex);
  (void)release_locked();
}

bool ready() noexcept { return g_ready.load(std::memory_order_acquire); }

bool resolve_frame(const std::array<char, 8>& resref, int worldX, int worldY, int sequence,
                   int currentFrame, FrameResolution& out) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || sequence < 0 || currentFrame < 0) return false;
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire)) return false;

    // Selection order is the contract: a variant bound to this exact occurrence wins, and only
    // when none matches does the unbound variant answer for it. Positions are compared exactly,
    // never within a tolerance — a position is a key here, not a measurement, and an approximate
    // match would silently serve one occurrence the pixels meant for another.
    const auto select = [&](bool wantBound) -> std::size_t {
      for (std::size_t index = 0; index < g_resources.size(); ++index) {
        const Resource& candidate = g_resources[index];
        if (candidate.resref != resref || candidate.positionBound != wantBound) continue;
        if (wantBound && (candidate.worldX != worldX || candidate.worldY != worldY)) continue;
        return index;
      }
      return g_resources.size();
    };

    const bool positionKnown = worldX != kAnyWorldPosition && worldY != kAnyWorldPosition;
    std::size_t resourceIndex = positionKnown ? select(true) : g_resources.size();
    if (resourceIndex == g_resources.size()) resourceIndex = select(false);
    if (resourceIndex == g_resources.size()) {
      const bool registeredResref =
          std::any_of(g_resources.begin(), g_resources.end(),
                      [&](const Resource& candidate) { return candidate.resref == resref; });
      const bool alreadyLogged =
          std::any_of(g_positionMisses.begin(), g_positionMisses.end(),
                      [&](const PositionMiss& miss) {
                        return miss.resref == resref && miss.worldX == worldX && miss.worldY == worldY;
                      });
      // A bounded sample makes a bad offset observable without turning RenderBam into a log flood.
      // These values are diagnostic only; matching remains exact and fail-closed.
      if (registeredResref && !alreadyLogged && g_positionMisses.size() < 16) {
        g_positionMisses.push_back({.resref = resref, .worldX = worldX, .worldY = worldY});
        LOG_WARN("Area-animation position miss: resref={}, read=({}, {}), no unbound fallback",
                 resref_name(resref), worldX, worldY);
      }
      return false;
    }

    const Resource& resource = g_resources[resourceIndex];
    if (sequence >= static_cast<int>(resource.cycles.size())) return false;
    const auto& cycle = resource.cycles[static_cast<std::size_t>(sequence)];
    if (currentFrame >= static_cast<int>(cycle.nativeFrames.size())) return false;
    const auto frameIndex = cycle.nativeFrames[static_cast<std::size_t>(currentFrame)];
    if (frameIndex >= resource.frames.size()) return false;
    out = {};
    out.nativeFrame = {.resourceIndex = resourceIndex, .frameIndex = frameIndex};
    if (resource.playbackMode == PlaybackMode::TimedTimeline) {
      out.timeline = {.enabled = true,
                      .nativeFpsNumerator = resource.nativeFpsNumerator,
                      .nativeFpsDenominator = resource.nativeFpsDenominator,
                      .targetFpsNumerator = resource.targetFpsNumerator,
                      .targetFpsDenominator = resource.targetFpsDenominator,
                      .phaseCount = static_cast<std::uint32_t>(cycle.timelineFrames.size())};
    }
    return true;
  } catch (...) {
  }
  return false;
}

bool resolve_timeline_frame(const FrameResolution& resolution, int sequence,
                            std::uint32_t phase, FrameHandle& out) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || !resolution.timeline.enabled || sequence < 0) {
    return false;
  }
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) ||
        resolution.nativeFrame.resourceIndex >= g_resources.size()) {
      return false;
    }
    const auto& resource = g_resources[resolution.nativeFrame.resourceIndex];
    if (resource.playbackMode != PlaybackMode::TimedTimeline ||
        sequence >= static_cast<int>(resource.cycles.size())) {
      return false;
    }
    const auto& timeline = resource.cycles[static_cast<std::size_t>(sequence)].timelineFrames;
    if (phase >= timeline.size()) return false;
    const auto frameIndex = timeline[phase];
    if (frameIndex >= resource.frames.size()) return false;
    out = {.resourceIndex = resolution.nativeFrame.resourceIndex, .frameIndex = frameIndex};
    return true;
  } catch (...) {
  }
  return false;
}

bool has_baked_occurrence_occlusion(FrameHandle handle) noexcept {
  if (!g_ready.load(std::memory_order_acquire)) return false;
  try {
    std::lock_guard lock(g_mutex);
    return g_ready.load(std::memory_order_acquire) &&
           handle.resourceIndex < g_resources.size() &&
           handle.frameIndex < g_resources[handle.resourceIndex].frames.size() &&
           g_resources[handle.resourceIndex].positionBound;
  } catch (...) {
  }
  // Unknown metadata must preserve existing pack pixels.
  return true;
}

bool bind_frame_texture(FrameHandle handle, const EngineTextureApi& api,
                        int& previousTextureId, bool enablePerformanceLogging) noexcept {
  previousTextureId = 0;
  if (!g_ready.load(std::memory_order_acquire) || !api.DrawGenTexture ||
      !api.DrawBindTexture || !api.DrawDeleteTexture || !api.TexImage ||
      !api.DrawGetRenderer || !api.glTextureState) {
    return false;
  }
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) || handle.resourceIndex >= g_resources.size() ||
        handle.frameIndex >= g_resources[handle.resourceIndex].frames.size()) {
      return false;
    }
    if (api.DrawGetRenderer() == 1) {
      if (!g_creationFailureLogged) {
        g_creationFailureLogged = true;
        LOG_WARN("Area-animation x4 skipped: active renderer is not OpenGL");
      }
      return false;
    }
#ifdef _WIN32
    const auto context = game::gl::current_context();
    if (!context) return false;
    if (g_textureContext != context) {
      clear_texture_cache_locked(enablePerformanceLogging);
      g_textureContext = context;
      for (auto& resource : g_resources) {
        std::fill(resource.compositionLogged.begin(), resource.compositionLogged.end(), false);
      }
    }
#endif
    previousTextureId = logical_texture_id(api);
    if (previousTextureId <= 0) return false;
    int replacementTexture = 0;
    if (!ensure_texture_locked(handle, api, previousTextureId, replacementTexture,
                               enablePerformanceLogging)) {
      if (!g_creationFailureLogged) {
        g_creationFailureLogged = true;
        LOG_WARN("Area-animation x4 texture creation failed; delegating to original BAM");
      }
      return false;
    }
    api.DrawBindTexture(replacementTexture);
    auto& resource = g_resources[handle.resourceIndex];
    if (!resource.compositionLogged[handle.frameIndex]) {
      resource.compositionLogged[handle.frameIndex] = true;
      const auto& frame = resource.frames[handle.frameIndex];
      LOG_DEBUG("Composing area animation {} frame {:03}: logical {}x{}, physical {}x{}",
                resource.displayName, handle.frameIndex, frame.logicalWidth, frame.logicalHeight,
                frame.logicalWidth * kScale, frame.logicalHeight * kScale);
    }
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("Area-animation x4 composition failed: {}", error.what());
  } catch (...) {
    LOG_WARN("Area-animation x4 composition failed with an unknown error");
  }
  return false;
}

void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept {
  if (api.DrawBindTexture && previousTextureId > 0) api.DrawBindTexture(previousTextureId);
}

TextureCacheTelemetryStats texture_cache_telemetry_snapshot() noexcept {
  try {
    std::lock_guard lock(g_mutex);
    return texture_cache_telemetry_snapshot_locked();
  } catch (...) {
    return {.capacity = kTextureCacheLimit};
  }
}

CacheBudgetSimulationSnapshot cache_budget_simulation_snapshot() noexcept {
  try {
    std::lock_guard lock(g_mutex);
    return cache_budget_simulation_snapshot_locked();
  } catch (...) {
    return {};
  }
}

void forget_engine_textures() noexcept {
  std::lock_guard lock(g_mutex);
  clear_texture_cache_locked();
  // Anything parked for deletion belonged to a context that is going away too.
  drop_retired_textures_locked();
#ifdef _WIN32
  g_textureContext = nullptr;
#endif
  for (auto& resource : g_resources) {
    std::fill(resource.compositionLogged.begin(), resource.compositionLogged.end(), false);
  }
}

bool has_retired_textures() noexcept {
  return g_hasRetiredTextures.load(std::memory_order_acquire);
}

void flush_retired_textures(const EngineTextureApi& api,
                            bool enablePerformanceLogging) noexcept {
  if (!g_hasRetiredTextures.load(std::memory_order_acquire) || !api.DrawDeleteTexture) return;
  try {
    std::lock_guard lock(g_mutex);
    if (g_retiredTextureIds.empty()) {
      drop_retired_textures_locked();
      return;
    }
#ifdef _WIN32
    // Deleting into a different context would target names this pack never owned.
    const auto context = game::gl::current_context();
    if (!context || (g_retiredContext != nullptr && g_retiredContext != context)) {
      drop_retired_textures_locked();
      return;
    }
#endif
    const auto count = g_retiredTextureIds.size();
    for (const int textureId : g_retiredTextureIds) {
      if (textureId > 0) api.DrawDeleteTexture(textureId);
    }
    drop_retired_textures_locked();
    if (enablePerformanceLogging) {
      LOG_INFO("Area-animation GPU retirement telemetry: deletedTextureNames={}", count);
    } else {
      LOG_DEBUG("Area animation x4: released {} engine texture(s) after a pack swap", count);
    }
  } catch (...) {
    // Reclaiming names is best-effort; never let it disturb the render pass.
  }
}

bool configure_area_packs(const std::filesystem::path& assetsDirectory) noexcept {
  try {
    std::error_code error;
    auto root = assetsDirectory / "areas";
    const bool present = std::filesystem::is_directory(root, error) && !error;
    std::lock_guard lock(g_mutex);
    g_perAreaPacks = present;
    g_areaPacksRoot = present ? std::move(root) : std::filesystem::path{};
    g_residentArea.clear();
    if (present) {
      LOG_INFO("Area-animation x4: per-area packs enabled from {}", g_areaPacksRoot.string());
    }
    return present;
  } catch (...) {
    std::lock_guard lock(g_mutex);
    g_perAreaPacks = false;
    g_areaPacksRoot.clear();
    return false;
  }
}

bool per_area_packs_active() noexcept {
  std::lock_guard lock(g_mutex);
  return g_perAreaPacks;
}

bool prepare_for_area(std::string_view areaResref, bool enablePerformanceLogging) noexcept {
  std::filesystem::path packDirectory;
  std::string outgoingArea;
  TextureCacheTelemetryStats outgoingTextureCache{};
  CacheBudgetSimulationSnapshot outgoingCacheBudgetSimulation{};
  const auto area = normalised_area_name(areaResref);
  {
    std::lock_guard lock(g_mutex);
    if (!g_perAreaPacks) return false;
    if (area.empty()) {
      LOG_DEBUG("Area-animation x4: unusable area resref; keeping the resident pack");
      return false;
    }
    // Re-entering the same area (or a LoadArea that resolves to it) must not pay for a
    // reload, and must not retire textures that are about to be needed again.
    if (g_ready.load(std::memory_order_acquire) && g_residentArea == area) return true;
    outgoingArea = g_residentArea;
    outgoingTextureCache = texture_cache_telemetry_snapshot_locked();
    outgoingCacheBudgetSimulation = cache_budget_simulation_snapshot_locked();
    packDirectory = g_areaPacksRoot / area;
  }

  std::error_code error;
  if (!std::filesystem::is_directory(packDirectory, error) || error) {
    const auto releaseStarted = enablePerformanceLogging ? TelemetryClock::now()
                                                         : TelemetryClock::time_point{};
    ReleaseSummary releaseSummary{};
    {
      std::lock_guard lock(g_mutex);
      releaseSummary = release_locked();
    }
    if (enablePerformanceLogging) {
      if (!releaseSummary.outgoingArea.empty()) {
        log_texture_cache_telemetry(releaseSummary.outgoingArea, "area-release",
                                    releaseSummary.outgoingTextureCache);
        log_cache_budget_simulation(releaseSummary.outgoingArea, "area-release",
                                    releaseSummary.outgoingCacheBudgetSimulation);
      }
      LOG_INFO(
          "Area-animation pack telemetry: area={}, outcome=native, outgoingRawBytes={}, "
          "residentRawBytes=0, outgoingTextureNames={}, deferredTextureNames={}, "
          "release={:.2f}ms",
          area, releaseSummary.outgoingRawBytes, releaseSummary.outgoingTextureNames,
          releaseSummary.deferredTextureNames,
          elapsed_milliseconds(releaseStarted, TelemetryClock::now()));
    }
    LOG_INFO("Area-animation x4: no pack for area {}; the engine renders its own BAM", area);
    return false;
  }
  PackPreparationStats stats{};
  if (!prepare(packDirectory, enablePerformanceLogging ? &stats : nullptr)) {
    if (enablePerformanceLogging && !outgoingArea.empty()) {
      log_texture_cache_telemetry(outgoingArea, "pack-load-failure", outgoingTextureCache);
      log_cache_budget_simulation(outgoingArea, "pack-load-failure",
                                  outgoingCacheBudgetSimulation);
    }
    LOG_WARN("Area-animation x4: pack for area {} refused; falling back to the engine BAM", area);
    return false;
  }
  if (enablePerformanceLogging) {
    if (!outgoingArea.empty()) {
      log_texture_cache_telemetry(outgoingArea, "pack-swap", stats.outgoingTextureCache);
      log_cache_budget_simulation(outgoingArea, "pack-swap",
                                  stats.outgoingCacheBudgetSimulation);
    }
    LOG_INFO(
        "Area-animation pack telemetry: area={}, outcome=loaded, registryBytes={}, "
        "frameFiles={}, frameBytes={}, outgoingRawBytes={}, residentRawBytes={}, "
        "peakRawBytes={}, resources={}, timedResources={}, frames={}, "
        "outgoingTextureNames={}, deferredTextureNames={}, registryRead={:.2f}ms, "
        "frameRead={:.2f}ms, parseAllocate={:.2f}ms, swap={:.2f}ms, total={:.2f}ms",
        area, stats.registryBytes, stats.frameFiles, stats.frameBytes,
        stats.outgoingRawBytes, stats.residentRawBytes, stats.peakRawBytes,
        stats.resourceCount, stats.timedResourceCount, stats.frameCount,
        stats.outgoingTextureNames, stats.deferredTextureNames,
        stats.registryReadMilliseconds, stats.frameReadMilliseconds,
        stats.parseAndAllocateMilliseconds, stats.swapMilliseconds, stats.totalMilliseconds);
    log_pack_process_resource_telemetry(area, stats);
  }
  std::lock_guard lock(g_mutex);
  g_residentArea = area;
  return true;
}
}  // namespace iee::area_animation_x4
