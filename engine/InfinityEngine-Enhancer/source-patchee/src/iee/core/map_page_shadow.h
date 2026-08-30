#pragma once

#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <filesystem>
#include <mutex>
#include <optional>
#include <span>
#include <string>
#include <unordered_set>
#include <vector>

namespace iee::core {

inline constexpr std::size_t kShadowMaximumCompressedBytes = 32u * 1024u * 1024u;
inline constexpr std::size_t kShadowMaximumDecodedBytes = 20u * 1024u * 1024u;
inline constexpr std::size_t kShadowMaximumPendingPages = 96;
// Phase 3e-B2f keeps at most one decoded page ready. Four pages may still be
// consumed sequentially, but the worker cannot build a multi-page backlog.
inline constexpr std::size_t kShadowMaximumCompletedPages = 1;
inline constexpr std::size_t kShadowMaximumCompletedBytes = 20u * 1024u * 1024u;
// B2e qualified four sequential prepared claims. B2f retains that bounded
// consumer gate while changing only how each page is scheduled.
inline constexpr std::uint32_t kMapPageConsumeMaximumClaimsPerGeneration = 4;

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
  // CRC32 of the zlib stream only (the bytes after the four-byte PVRZ size
  // prefix). The bounded consumer rechecks it against the native CRes buffer
  // before a prepared page may replace the engine's uncompress call.
  std::uint32_t compressedCrc32{};
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
  std::uint64_t nativeFallbackWaitNanoseconds{};
};

struct ShadowClaim {
  ShadowObservationStatus status{ShadowObservationStatus::Unplanned};
  PvrzPreparedPage page{};
  std::uint64_t nativeFallbackWaitNanoseconds{};
};

// A fixed diagnostic number of successful handoff claims is permitted per
// area generation. Each ready page consumes one slot even when the later
// render-thread validation falls back; malformed attempts cannot make the
// experiment unbounded.
class MapPageConsumeGate {
 public:
  void reset(std::uint64_t generation) noexcept;
  [[nodiscard]] bool try_claim(std::uint64_t generation) noexcept;
  [[nodiscard]] bool exhausted(std::uint64_t generation) const noexcept;
  [[nodiscard]] std::uint32_t claims(std::uint64_t generation) const noexcept;

 private:
  std::uint64_t generation_{};
  std::uint32_t claims_{};
};

enum class PvrConsumeValidationStatus : std::uint8_t {
  Ready,
  InactiveScope,
  UnexpectedReturnAddress,
  ResourceMismatch,
  SourceMismatch,
  SizeMismatch,
  CrcMismatch,
};

// Host-testable portion of the consume contract. Readability/writability is
// checked by the Windows detour before constructing this evidence.
struct PvrConsumeEvidence {
  bool scopeActive{};
  std::uintptr_t expectedReturnAddress{};
  std::uintptr_t actualReturnAddress{};
  std::uintptr_t expectedResource{};
  std::uintptr_t activeResource{};
  std::uintptr_t nativeData{};
  std::uintptr_t source{};
  std::size_t nativeResourceBytes{};
  std::size_t sourceBytes{};
  std::size_t preparedCompressedBytes{};
  std::size_t declaredDecodedBytes{};
  std::size_t destinationCapacity{};
  std::size_t preparedDecodedBytes{};
  std::uint32_t expectedCompressedCrc32{};
  std::uint32_t actualCompressedCrc32{};
};

[[nodiscard]] PvrConsumeValidationStatus validate_pvr_consume(
    const PvrConsumeEvidence& evidence) noexcept;

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
  std::uint64_t nativeFallbackWaits{};
  std::uint64_t nativeFallbackWaitNanoseconds{};
  std::uint64_t maximumNativeFallbackWaitNanoseconds{};
  std::uint64_t cancelledPendingPages{};
  std::uint64_t cancelledCompletedPages{};
  std::size_t pendingPages{};
  std::size_t inFlightPages{};
  std::size_t nativeFallbackWaiters{};
  std::size_t completedPages{};
  std::size_t completedBytes{};
  std::size_t peakPendingPages{};
  std::size_t peakCompletedPages{};
  std::size_t peakCompletedBytes{};
};

struct ShadowCancellation {
  std::size_t pendingPages{};
  std::size_t completedPages{};
  std::size_t completedBytes{};
  bool inFlight{};
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
  // Non-retiring readiness check used by the render-thread scheduler. It does
  // not wait for or take ownership from the worker.
  [[nodiscard]] ShadowObservationStatus inspect(
      const ShadowPageIdentity& identity) const noexcept;
  [[nodiscard]] ShadowObservation observe(const ShadowPageIdentity& identity) noexcept;
  // Identical retirement semantics to observe(), but moves a ready immutable
  // buffer to the render thread instead of destroying it under the queue lock.
  [[nodiscard]] ShadowClaim claim(const ShadowPageIdentity& identity) noexcept;
  [[nodiscard]] ShadowQueueStats snapshot() const noexcept;
  // Rejects new work and releases queued/ready buffers. An active reader keeps
  // its identity until publish() acknowledges file-handle retirement, so a
  // concurrent native fallback cannot bypass the B2d safety handshake.
  [[nodiscard]] ShadowCancellation cancel_remaining() noexcept;
  void request_stop() noexcept;

 private:
  struct Completed {
    ShadowPageIdentity identity{};
    PvrzPreparedPage page{};
  };

  [[nodiscard]] bool identity_known_locked(const ShadowPageIdentity& identity) const;
  [[nodiscard]] std::uint64_t retire_not_ready_locked(
      std::unique_lock<std::mutex>& lock, const ShadowPageIdentity& identity);
  void clear_generation_locked() noexcept;

  const ShadowQueueLimits limits_;
  mutable std::mutex mutex_;
  std::condition_variable changed_;
  bool stopping_{true};
  bool acceptingWork_{true};
  std::uint64_t generation_{};
  std::deque<ShadowPageJob> pending_;
  std::optional<ShadowPageIdentity> inFlight_;
  std::size_t nativeFallbackWaiters_{};
  std::deque<Completed> completed_;
  std::unordered_set<ShadowPageIdentity, ShadowPageIdentityHash> known_;
  std::size_t completedBytes_{};
  ShadowQueueStats stats_{};
};

}  // namespace iee::core
