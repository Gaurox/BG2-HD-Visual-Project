#pragma once

#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <filesystem>
#include <mutex>
#include <span>
#include <string>
#include <unordered_set>
#include <vector>

namespace iee::core {

inline constexpr std::size_t kShadowMaximumCompressedBytes = 32u * 1024u * 1024u;
inline constexpr std::size_t kShadowMaximumDecodedBytes = 20u * 1024u * 1024u;
inline constexpr std::size_t kShadowMaximumPendingPages = 96;
inline constexpr std::size_t kShadowMaximumCompletedPages = 4;
inline constexpr std::size_t kShadowMaximumCompletedBytes = 72u * 1024u * 1024u;

enum class PvrzPrepareStatus : std::uint8_t {
  Ready,
  Missing,
  IoError,
  CompressedLimit,
  InvalidEnvelope,
  InflateError,
  InvalidPvr,
};

struct PvrzPrepareLimits {
  std::size_t maximumCompressedBytes{kShadowMaximumCompressedBytes};
  std::size_t maximumDecodedBytes{kShadowMaximumDecodedBytes};
  std::uint32_t maximumDimension{4096};
};

struct PvrzPreparedPage {
  PvrzPrepareStatus status{PvrzPrepareStatus::IoError};
  std::uint64_t compressedBytes{};
  std::uint64_t decodedBytes{};
  std::uint64_t prepareNanoseconds{};
  std::uint32_t width{};
  std::uint32_t height{};
  std::uint32_t pixelFormat{};
  std::vector<std::byte> decoded{};
};

// Phase 3e-A accepts only the closed override PVRZ format used by the current
// map builds: u32 decoded size, one zlib stream, then one DXT1/DXT5 PVR v3
// surface with no mip chain. No native resource or GL object is involved.
[[nodiscard]] PvrzPreparedPage prepare_pvrz_bytes(
    std::span<const std::byte> fileBytes,
    const PvrzPrepareLimits& limits = {}) noexcept;
[[nodiscard]] PvrzPreparedPage prepare_pvrz_file(
    const std::filesystem::path& path,
    const PvrzPrepareLimits& limits = {}) noexcept;

struct ShadowPageIdentity {
  std::uint64_t generation{};
  std::string areaResref{};
  std::string tilesetResref{};
  std::string pageResref{};
  std::int32_t pageNumber{-1};

  friend bool operator==(const ShadowPageIdentity&, const ShadowPageIdentity&) = default;
};

struct ShadowPageIdentityHash {
  [[nodiscard]] std::size_t operator()(const ShadowPageIdentity& value) const noexcept;
};

struct ShadowPageJob {
  ShadowPageIdentity identity{};
  std::filesystem::path path{};
  std::uint64_t submittedNanoseconds{};
};

struct ShadowPreparedResult {
  ShadowPageIdentity identity{};
  PvrzPreparedPage page{};
};

struct ShadowQueueLimits {
  std::size_t maximumPendingPages{kShadowMaximumPendingPages};
  std::size_t maximumCompletedPages{kShadowMaximumCompletedPages};
  std::size_t maximumCompletedBytes{kShadowMaximumCompletedBytes};
};

enum class ShadowObservationStatus : std::uint8_t { Ready, NotReady, Unplanned };

struct ShadowObservation {
  ShadowObservationStatus status{ShadowObservationStatus::Unplanned};
  std::uint64_t compressedBytes{};
  std::uint64_t decodedBytes{};
  std::uint64_t prepareNanoseconds{};
};

struct ShadowQueueStats {
  std::uint64_t generation{};
  std::uint64_t submitted{};
  std::uint64_t coalesced{};
  std::uint64_t queueRejected{};
  std::uint64_t started{};
  std::uint64_t prepared{};
  std::uint64_t missing{};
  std::uint64_t ioFailures{};
  std::uint64_t invalid{};
  std::uint64_t discarded{};
  std::uint64_t readyBeforeDemand{};
  std::uint64_t notReadyBeforeDemand{};
  std::uint64_t unplannedDemands{};
  std::uint64_t compressedBytes{};
  std::uint64_t decodedBytes{};
  std::uint64_t prepareNanoseconds{};
  std::uint64_t maximumPrepareNanoseconds{};
  std::uint64_t queueNanoseconds{};
  std::uint64_t maximumQueueNanoseconds{};
  std::size_t pendingPages{};
  std::size_t completedPages{};
  std::size_t completedBytes{};
  std::size_t peakPendingPages{};
  std::size_t peakCompletedPages{};
  std::size_t peakCompletedBytes{};
};

// Thread-safe bounded handoff. The render thread submits/observes, while one
// worker blocks in wait_take() and publish(). Results are private immutable
// buffers and are retired as soon as the corresponding native Demand is seen.
class MapPageShadowQueue {
 public:
  explicit MapPageShadowQueue(ShadowQueueLimits limits = {});
  MapPageShadowQueue(const MapPageShadowQueue&) = delete;
  MapPageShadowQueue& operator=(const MapPageShadowQueue&) = delete;

  void restart() noexcept;
  [[nodiscard]] std::uint64_t begin_generation() noexcept;
  [[nodiscard]] std::uint64_t generation() const noexcept;
  [[nodiscard]] bool submit(ShadowPageJob job) noexcept;
  [[nodiscard]] bool wait_take(ShadowPageJob& job) noexcept;
  [[nodiscard]] bool publish(ShadowPreparedResult result) noexcept;
  [[nodiscard]] ShadowObservation observe(const ShadowPageIdentity& identity) noexcept;
  [[nodiscard]] ShadowQueueStats snapshot() const noexcept;
  void request_stop() noexcept;

 private:
  struct Completed {
    ShadowPageIdentity identity{};
    PvrzPreparedPage page{};
  };

  [[nodiscard]] bool identity_known_locked(const ShadowPageIdentity& identity) const;
  void clear_generation_locked() noexcept;

  const ShadowQueueLimits limits_;
  mutable std::mutex mutex_;
  std::condition_variable changed_;
  bool stopping_{true};
  std::uint64_t generation_{};
  std::deque<ShadowPageJob> pending_;
  std::deque<Completed> completed_;
  std::unordered_set<ShadowPageIdentity, ShadowPageIdentityHash> known_;
  std::size_t completedBytes_{};
  ShadowQueueStats stats_{};
};

}  // namespace iee::core
