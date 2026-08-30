#include "map_page_shadow.h"

#include <zlib.h>

#include <algorithm>
#include <chrono>
#include <cstring>
#include <fstream>
#include <limits>
#include <system_error>

#include "iee/game/file_formats.h"

namespace iee::core {
namespace {
constexpr std::uint32_t kPvrVersion3 = 0x03525650u;
constexpr std::uint32_t kDxt1 = 7;
constexpr std::uint32_t kDxt5 = 11;

std::uint32_t read_u32_le(std::span<const std::byte> bytes) noexcept {
  if (bytes.size() < sizeof(std::uint32_t)) return 0;
  return static_cast<std::uint32_t>(bytes[0]) |
         (static_cast<std::uint32_t>(bytes[1]) << 8u) |
         (static_cast<std::uint32_t>(bytes[2]) << 16u) |
         (static_cast<std::uint32_t>(bytes[3]) << 24u);
}

bool valid_pvr(const std::vector<std::byte>& decoded,
               const PvrzPrepareLimits& limits, PvrzPreparedPage& result) noexcept {
  if (decoded.size() < sizeof(game::PVRTextureHeaderV3)) return false;
  game::PVRTextureHeaderV3 header{};
  std::memcpy(&header, decoded.data(), sizeof(header));
  if (header.u32Version != kPvrVersion3 || header.u64PixelFormathi != 0 ||
      (header.u64PixelFormatlo != kDxt1 && header.u64PixelFormatlo != kDxt5) ||
      header.u32Width == 0 || header.u32Height == 0 ||
      header.u32Width > limits.maximumDimension ||
      header.u32Height > limits.maximumDimension || header.u32Depth != 1 ||
      header.u32NumSurfaces != 1 || header.u32NumFaces != 1 ||
      header.u32MIPMapCount != 1) {
    return false;
  }

  const auto headerBytes = sizeof(header);
  if (header.u32MetaDataSize > decoded.size() - headerBytes) return false;
  const auto blocksWide = (static_cast<std::uint64_t>(header.u32Width) + 3u) / 4u;
  const auto blocksHigh = (static_cast<std::uint64_t>(header.u32Height) + 3u) / 4u;
  const auto blockBytes = header.u64PixelFormatlo == kDxt1 ? 8u : 16u;
  const auto payloadBytes = blocksWide * blocksHigh * blockBytes;
  const auto prefixBytes = static_cast<std::uint64_t>(headerBytes) +
                           static_cast<std::uint64_t>(header.u32MetaDataSize);
  if (prefixBytes > (std::numeric_limits<std::uint64_t>::max)() - payloadBytes ||
      prefixBytes + payloadBytes != decoded.size()) {
    return false;
  }

  result.width = header.u32Width;
  result.height = header.u32Height;
  result.pixelFormat = header.u64PixelFormatlo;
  return true;
}

void account_failure(ShadowQueueStats& stats, PvrzPrepareStatus status) noexcept {
  switch (status) {
    case PvrzPrepareStatus::Missing:
      ++stats.missing;
      break;
    case PvrzPrepareStatus::IoError:
      ++stats.ioFailures;
      break;
    case PvrzPrepareStatus::Ready:
      break;
    default:
      ++stats.invalid;
      break;
  }
}

std::uint64_t steady_nanoseconds() noexcept {
  return static_cast<std::uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(
          std::chrono::steady_clock::now().time_since_epoch())
          .count());
}

bool valid_resref_component(const std::string& value) noexcept {
  if (value.empty() || value.size() > 8) return false;
  return std::all_of(value.begin(), value.end(), [](unsigned char character) {
    return (character >= 'A' && character <= 'Z') ||
           (character >= 'a' && character <= 'z') ||
           (character >= '0' && character <= '9') || character == '_';
  });
}
}  // namespace

PvrzPreparedPage prepare_pvrz_bytes(std::span<const std::byte> fileBytes,
                                    const PvrzPrepareLimits& limits) noexcept {
  PvrzPreparedPage result{};
  result.compressedBytes = fileBytes.size();
  try {
    if (fileBytes.size() < 6) {
      result.status = PvrzPrepareStatus::InvalidEnvelope;
      return result;
    }
    if (fileBytes.size() > limits.maximumCompressedBytes) {
      result.status = PvrzPrepareStatus::CompressedLimit;
      return result;
    }
    const auto declaredSize = read_u32_le(fileBytes.first<4>());
    if (declaredSize < sizeof(game::PVRTextureHeaderV3) ||
        declaredSize > limits.maximumDecodedBytes) {
      result.status = PvrzPrepareStatus::InvalidEnvelope;
      return result;
    }

    const auto* compressed = reinterpret_cast<const Bytef*>(fileBytes.data() + 4);
    const auto compressedSize = static_cast<uInt>(fileBytes.size() - 4);
    result.compressedCrc32 = static_cast<std::uint32_t>(
        crc32(crc32(0L, Z_NULL, 0), compressed, compressedSize));

    result.decoded.resize(declaredSize);
    uLongf decodedSize = static_cast<uLongf>(result.decoded.size());
    uLong sourceSize = static_cast<uLong>(fileBytes.size() - 4);
    const auto* source = compressed;
    auto* destination = reinterpret_cast<Bytef*>(result.decoded.data());
    const int inflateResult =
        uncompress2(destination, &decodedSize, source, &sourceSize);
    if (inflateResult != Z_OK || decodedSize != declaredSize ||
        sourceSize != fileBytes.size() - 4) {
      result.decoded.clear();
      result.status = PvrzPrepareStatus::InflateError;
      return result;
    }
    if (!valid_pvr(result.decoded, limits, result)) {
      result.decoded.clear();
      result.status = PvrzPrepareStatus::InvalidPvr;
      return result;
    }
    result.decodedBytes = result.decoded.size();
    result.status = PvrzPrepareStatus::Ready;
    return result;
  } catch (...) {
    result.decoded.clear();
    result.status = PvrzPrepareStatus::IoError;
    return result;
  }
}

void MapPageConsumeGate::reset(std::uint64_t generation) noexcept {
  generation_ = generation;
  claims_ = 0;
}

bool MapPageConsumeGate::try_claim(std::uint64_t generation) noexcept {
  if (generation == 0 || generation != generation_ ||
      claims_ >= kMapPageConsumeMaximumClaimsPerGeneration) {
    return false;
  }
  ++claims_;
  return true;
}

bool MapPageConsumeGate::exhausted(std::uint64_t generation) const noexcept {
  return generation == 0 || generation != generation_ ||
         claims_ >= kMapPageConsumeMaximumClaimsPerGeneration;
}

std::uint32_t MapPageConsumeGate::claims(std::uint64_t generation) const noexcept {
  return generation != 0 && generation == generation_ ? claims_ : 0;
}

PvrConsumeValidationStatus validate_pvr_consume(
    const PvrConsumeEvidence& evidence) noexcept {
  if (!evidence.scopeActive) return PvrConsumeValidationStatus::InactiveScope;
  if (evidence.expectedReturnAddress == 0 ||
      evidence.actualReturnAddress != evidence.expectedReturnAddress) {
    return PvrConsumeValidationStatus::UnexpectedReturnAddress;
  }
  if (evidence.expectedResource == 0 ||
      evidence.activeResource != evidence.expectedResource) {
    return PvrConsumeValidationStatus::ResourceMismatch;
  }
  if (evidence.nativeData == 0 ||
      evidence.nativeData > (std::numeric_limits<std::uintptr_t>::max)() - 4u ||
      evidence.source != evidence.nativeData + 4u ||
      evidence.nativeResourceBytes < 4u ||
      evidence.sourceBytes != evidence.nativeResourceBytes - 4u) {
    return PvrConsumeValidationStatus::SourceMismatch;
  }
  if (evidence.preparedCompressedBytes != evidence.nativeResourceBytes ||
      evidence.preparedDecodedBytes == 0 ||
      evidence.declaredDecodedBytes != evidence.preparedDecodedBytes ||
      evidence.destinationCapacity != evidence.preparedDecodedBytes) {
    return PvrConsumeValidationStatus::SizeMismatch;
  }
  if (evidence.actualCompressedCrc32 != evidence.expectedCompressedCrc32) {
    return PvrConsumeValidationStatus::CrcMismatch;
  }
  return PvrConsumeValidationStatus::Ready;
}

PvrzPreparedPage prepare_pvrz_file(const std::filesystem::path& path,
                                   const PvrzPrepareLimits& limits) noexcept {
  const auto started = std::chrono::steady_clock::now();
  PvrzPreparedPage result{};
  try {
    std::error_code error;
    const auto status = std::filesystem::symlink_status(path, error);
    if (error || status.type() == std::filesystem::file_type::not_found) {
      result.status = PvrzPrepareStatus::Missing;
    } else if (std::filesystem::is_symlink(status) ||
               !std::filesystem::is_regular_file(status)) {
      result.status = PvrzPrepareStatus::IoError;
    } else {
      const auto fileSize = std::filesystem::file_size(path, error);
      if (error) {
        result.status = PvrzPrepareStatus::IoError;
      } else if (fileSize > limits.maximumCompressedBytes ||
                 fileSize > (std::numeric_limits<std::size_t>::max)()) {
        result.status = PvrzPrepareStatus::CompressedLimit;
        result.compressedBytes = fileSize;
      } else {
        std::vector<std::byte> bytes(static_cast<std::size_t>(fileSize));
        std::ifstream file(path, std::ios::binary);
        if (!file || (!bytes.empty() &&
                      !file.read(reinterpret_cast<char*>(bytes.data()),
                                 static_cast<std::streamsize>(bytes.size())))) {
          result.status = PvrzPrepareStatus::IoError;
        } else {
          result = prepare_pvrz_bytes(bytes, limits);
        }
      }
    }
  } catch (...) {
    result = {};
    result.status = PvrzPrepareStatus::IoError;
  }
  result.prepareNanoseconds = static_cast<std::uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(
          std::chrono::steady_clock::now() - started)
          .count());
  return result;
}

std::size_t ShadowPageIdentityHash::operator()(
    const ShadowPageIdentity& value) const noexcept {
  std::size_t seed = std::hash<std::uint64_t>{}(value.generation);
  const auto mix = [&](std::size_t hash) {
    seed ^= hash + 0x9E3779B97F4A7C15ull + (seed << 6u) + (seed >> 2u);
  };
  mix(std::hash<std::string>{}(value.areaResref));
  mix(std::hash<std::string>{}(value.tilesetResref));
  mix(std::hash<std::string>{}(value.pageResref));
  mix(std::hash<std::int32_t>{}(value.pageNumber));
  return seed;
}

MapPageShadowQueue::MapPageShadowQueue(ShadowQueueLimits limits)
    : limits_({(std::max)(std::size_t{1}, limits.maximumPendingPages),
               (std::max)(std::size_t{1}, limits.maximumCompletedPages),
               (std::max)(std::size_t{1}, limits.maximumCompletedBytes)}) {}

void MapPageShadowQueue::clear_generation_locked() noexcept {
  pending_.clear();
  completed_.clear();
  known_.clear();
  completedBytes_ = 0;
}

void MapPageShadowQueue::restart() noexcept {
  try {
    std::lock_guard lock(mutex_);
    stopping_ = false;
    acceptingWork_ = true;
    clear_generation_locked();
    generation_ = generation_ == (std::numeric_limits<std::uint64_t>::max)()
                      ? 1
                      : generation_ + 1;
    stats_ = {};
    stats_.generation = generation_;
    changed_.notify_all();
  } catch (...) {
  }
}

std::uint64_t MapPageShadowQueue::begin_generation() noexcept {
  try {
    std::lock_guard lock(mutex_);
    acceptingWork_ = true;
    clear_generation_locked();
    generation_ = generation_ == (std::numeric_limits<std::uint64_t>::max)()
                      ? 1
                      : generation_ + 1;
    stats_ = {};
    stats_.generation = generation_;
    changed_.notify_all();
    return generation_;
  } catch (...) {
    return 0;
  }
}

std::uint64_t MapPageShadowQueue::generation() const noexcept {
  try {
    std::lock_guard lock(mutex_);
    return generation_;
  } catch (...) {
    return 0;
  }
}

bool MapPageShadowQueue::identity_known_locked(
    const ShadowPageIdentity& identity) const {
  return known_.find(identity) != known_.end();
}

std::uint64_t MapPageShadowQueue::retire_not_ready_locked(
    std::unique_lock<std::mutex>& lock,
    const ShadowPageIdentity& identity) {
  const auto pending = std::find_if(pending_.begin(), pending_.end(),
                                    [&](const ShadowPageJob& value) {
                                      return value.identity == identity;
                                    });
  if (pending != pending_.end()) pending_.erase(pending);
  known_.erase(identity);
  ++stats_.notReadyBeforeDemand;

  if (!inFlight_ || *inFlight_ != identity) {
    changed_.notify_all();
    return 0;
  }

  ++stats_.nativeFallbackWaits;
  ++nativeFallbackWaiters_;
  changed_.notify_all();
  const auto started = steady_nanoseconds();
  changed_.wait(lock, [&] { return !inFlight_ || *inFlight_ != identity; });
  const auto ended = steady_nanoseconds();
  --nativeFallbackWaiters_;
  const auto waited = ended >= started ? ended - started : 0;
  stats_.nativeFallbackWaitNanoseconds += waited;
  stats_.maximumNativeFallbackWaitNanoseconds =
      (std::max)(stats_.maximumNativeFallbackWaitNanoseconds, waited);
  return waited;
}

bool MapPageShadowQueue::submit(ShadowPageJob job) noexcept {
  try {
    std::lock_guard lock(mutex_);
    if (stopping_ || !acceptingWork_ || job.identity.generation != generation_ ||
        !valid_resref_component(job.identity.areaResref) ||
        !valid_resref_component(job.identity.tilesetResref) ||
        !valid_resref_component(job.identity.pageResref) ||
        job.identity.pageNumber < 0 || job.path.empty()) {
      ++stats_.queueRejected;
      return false;
    }
    if (identity_known_locked(job.identity)) {
      ++stats_.coalesced;
      return true;
    }
    if (pending_.size() >= limits_.maximumPendingPages) {
      ++stats_.queueRejected;
      return false;
    }
    known_.insert(job.identity);
    job.submittedNanoseconds = steady_nanoseconds();
    pending_.push_back(std::move(job));
    ++stats_.submitted;
    stats_.peakPendingPages = (std::max)(stats_.peakPendingPages, pending_.size());
    changed_.notify_all();
    return true;
  } catch (...) {
    return false;
  }
}

bool MapPageShadowQueue::wait_take(ShadowPageJob& job) noexcept {
  try {
    std::unique_lock lock(mutex_);
    changed_.wait(lock, [&] { return stopping_ || !pending_.empty(); });
    if (stopping_) return false;
    job = std::move(pending_.front());
    pending_.pop_front();
    inFlight_ = job.identity;
    ++stats_.started;
    const auto now = steady_nanoseconds();
    const auto queued = now >= job.submittedNanoseconds ? now - job.submittedNanoseconds : 0;
    stats_.queueNanoseconds += queued;
    stats_.maximumQueueNanoseconds =
        (std::max)(stats_.maximumQueueNanoseconds, queued);
    return true;
  } catch (...) {
    return false;
  }
}

bool MapPageShadowQueue::publish(ShadowPreparedResult result) noexcept {
  try {
    std::unique_lock lock(mutex_);
    if (inFlight_ && *inFlight_ == result.identity) {
      inFlight_.reset();
      changed_.notify_all();
    }
    if (stopping_ || !acceptingWork_ || result.identity.generation != generation_ ||
        !identity_known_locked(result.identity)) {
      ++stats_.discarded;
      known_.erase(result.identity);
      return false;
    }
    if (result.page.status != PvrzPrepareStatus::Ready) {
      account_failure(stats_, result.page.status);
      known_.erase(result.identity);
      changed_.notify_all();
      return false;
    }

    ++stats_.prepared;
    stats_.compressedBytes += result.page.compressedBytes;
    stats_.decodedBytes += result.page.decodedBytes;
    stats_.prepareNanoseconds += result.page.prepareNanoseconds;
    stats_.maximumPrepareNanoseconds =
        (std::max)(stats_.maximumPrepareNanoseconds, result.page.prepareNanoseconds);
    const auto bytes = result.page.decoded.size();
    if (bytes > limits_.maximumCompletedBytes) {
      ++stats_.discarded;
      known_.erase(result.identity);
      return false;
    }

    changed_.wait(lock, [&] {
      const bool fits = completed_.size() < limits_.maximumCompletedPages &&
                        completedBytes_ <= limits_.maximumCompletedBytes - bytes;
      return stopping_ || result.identity.generation != generation_ ||
             !identity_known_locked(result.identity) || fits;
    });
    if (stopping_ || result.identity.generation != generation_ ||
        !identity_known_locked(result.identity)) {
      ++stats_.discarded;
      return false;
    }

    completedBytes_ += bytes;
    completed_.push_back({std::move(result.identity), std::move(result.page)});
    stats_.peakCompletedPages =
        (std::max)(stats_.peakCompletedPages, completed_.size());
    stats_.peakCompletedBytes =
        (std::max)(stats_.peakCompletedBytes, completedBytes_);
    changed_.notify_all();
    return true;
  } catch (...) {
    return false;
  }
}

ShadowObservationStatus MapPageShadowQueue::inspect(
    const ShadowPageIdentity& identity) const noexcept {
  try {
    std::lock_guard lock(mutex_);
    const auto ready = std::find_if(completed_.begin(), completed_.end(),
                                    [&](const Completed& value) {
                                      return value.identity == identity;
                                    });
    if (ready != completed_.end()) return ShadowObservationStatus::Ready;
    return identity_known_locked(identity) ? ShadowObservationStatus::NotReady
                                           : ShadowObservationStatus::Unplanned;
  } catch (...) {
    return ShadowObservationStatus::Unplanned;
  }
}

ShadowObservation MapPageShadowQueue::observe(
    const ShadowPageIdentity& identity) noexcept {
  try {
    std::unique_lock lock(mutex_);
    const auto ready = std::find_if(completed_.begin(), completed_.end(),
                                    [&](const Completed& value) {
                                      return value.identity == identity;
                                    });
    if (ready != completed_.end()) {
      ShadowObservation observation{
          .status = ShadowObservationStatus::Ready,
          .compressedBytes = ready->page.compressedBytes,
          .decodedBytes = ready->page.decodedBytes,
          .prepareNanoseconds = ready->page.prepareNanoseconds,
      };
      completedBytes_ -= ready->page.decoded.size();
      completed_.erase(ready);
      known_.erase(identity);
      ++stats_.readyBeforeDemand;
      changed_.notify_all();
      return observation;
    }
    if (identity_known_locked(identity)) {
      const auto waited = retire_not_ready_locked(lock, identity);
      return {.status = ShadowObservationStatus::NotReady,
              .nativeFallbackWaitNanoseconds = waited};
    }
    ++stats_.unplannedDemands;
    return {.status = ShadowObservationStatus::Unplanned};
  } catch (...) {
    return {.status = ShadowObservationStatus::Unplanned};
  }
}

ShadowClaim MapPageShadowQueue::claim(
    const ShadowPageIdentity& identity) noexcept {
  try {
    std::unique_lock lock(mutex_);
    const auto ready = std::find_if(completed_.begin(), completed_.end(),
                                    [&](const Completed& value) {
                                      return value.identity == identity;
                                    });
    if (ready != completed_.end()) {
      ShadowClaim claim{
          .status = ShadowObservationStatus::Ready,
          .page = std::move(ready->page),
      };
      completedBytes_ -= claim.page.decoded.size();
      completed_.erase(ready);
      known_.erase(identity);
      ++stats_.readyBeforeDemand;
      changed_.notify_all();
      return claim;
    }
    if (identity_known_locked(identity)) {
      const auto waited = retire_not_ready_locked(lock, identity);
      return {.status = ShadowObservationStatus::NotReady,
              .nativeFallbackWaitNanoseconds = waited};
    }
    ++stats_.unplannedDemands;
    return {.status = ShadowObservationStatus::Unplanned};
  } catch (...) {
    return {.status = ShadowObservationStatus::Unplanned};
  }
}

ShadowQueueStats MapPageShadowQueue::snapshot() const noexcept {
  try {
    std::lock_guard lock(mutex_);
    auto snapshot = stats_;
    snapshot.pendingPages = pending_.size();
    snapshot.inFlightPages = inFlight_ ? 1 : 0;
    snapshot.nativeFallbackWaiters = nativeFallbackWaiters_;
    snapshot.completedPages = completed_.size();
    snapshot.completedBytes = completedBytes_;
    return snapshot;
  } catch (...) {
    return {};
  }
}

ShadowCancellation MapPageShadowQueue::cancel_remaining() noexcept {
  try {
    std::lock_guard lock(mutex_);
    ShadowCancellation cancelled{
        .pendingPages = pending_.size(),
        .completedPages = completed_.size(),
        .completedBytes = completedBytes_,
        .inFlight = inFlight_.has_value(),
    };
    acceptingWork_ = false;
    stats_.cancelledPendingPages += pending_.size();
    stats_.cancelledCompletedPages += completed_.size();
    pending_.clear();
    completed_.clear();
    completedBytes_ = 0;
    known_.clear();
    // Preserve only the active identity until publish() closes its file and
    // wakes any native fallback waiter. The result itself will be discarded
    // because acceptingWork_ is false.
    if (inFlight_) known_.insert(*inFlight_);
    changed_.notify_all();
    return cancelled;
  } catch (...) {
    return {};
  }
}

void MapPageShadowQueue::request_stop() noexcept {
  try {
    std::lock_guard lock(mutex_);
    stopping_ = true;
    acceptingWork_ = false;
    clear_generation_locked();
    changed_.notify_all();
  } catch (...) {
  }
}

}  // namespace iee::core
