#include "map_texture_telemetry.h"

#include <atomic>

namespace iee::core {
namespace {
constexpr unsigned kCompressedRgbS3tcDxt1 = 0x83F0;
constexpr unsigned kCompressedRgbaS3tcDxt1 = 0x83F1;
constexpr unsigned kCompressedRgbaS3tcDxt5 = 0x83F3;
constexpr unsigned kCompressedSrgbAlphaS3tcDxt1 = 0x8C4D;
constexpr unsigned kCompressedSrgbAlphaS3tcDxt5 = 0x8C4F;
constexpr int kLargeTextureDimension = 2048;

struct AtomicGlTextureTelemetry {
  std::atomic<std::uint64_t> textureGenerationCalls{};
  std::atomic<std::uint64_t> generatedTextureNames{};
  std::atomic<std::uint64_t> textureGenerationNanoseconds{};
  std::atomic<std::uint64_t> uncompressedUploadCalls{};
  std::atomic<std::uint64_t> uncompressedKnownBytes{};
  std::atomic<std::uint64_t> uncompressedUnknownByteCalls{};
  std::atomic<std::uint64_t> compressedUploadCalls{};
  std::atomic<std::uint64_t> compressedUploadBytes{};
  std::atomic<std::uint64_t> compressedUploadNanoseconds{};
  std::atomic<std::uint64_t> maximumCompressedUploadNanoseconds{};
  std::atomic<std::uint64_t> compressedBaseLevelCalls{};
  std::atomic<std::uint64_t> largeS3tcBaseLevelCalls{};
  std::atomic<std::uint64_t> largeS3tcBaseLevelBytes{};
  std::atomic<std::uint64_t> deleteCalls{};
  std::atomic<std::uint64_t> deletedTextureNames{};
};

AtomicGlTextureTelemetry g_stats;

bool is_s3tc(unsigned internalFormat) noexcept {
  switch (internalFormat) {
    case kCompressedRgbS3tcDxt1:
    case kCompressedRgbaS3tcDxt1:
    case kCompressedRgbaS3tcDxt5:
    case kCompressedSrgbAlphaS3tcDxt1:
    case kCompressedSrgbAlphaS3tcDxt5:
      return true;
    default:
      return false;
  }
}

void reset(std::atomic<std::uint64_t>& value) noexcept {
  value.store(0, std::memory_order_relaxed);
}
}  // namespace

void reset_gl_texture_telemetry() noexcept {
  reset(g_stats.textureGenerationCalls);
  reset(g_stats.generatedTextureNames);
  reset(g_stats.textureGenerationNanoseconds);
  reset(g_stats.uncompressedUploadCalls);
  reset(g_stats.uncompressedKnownBytes);
  reset(g_stats.uncompressedUnknownByteCalls);
  reset(g_stats.compressedUploadCalls);
  reset(g_stats.compressedUploadBytes);
  reset(g_stats.compressedUploadNanoseconds);
  reset(g_stats.maximumCompressedUploadNanoseconds);
  reset(g_stats.compressedBaseLevelCalls);
  reset(g_stats.largeS3tcBaseLevelCalls);
  reset(g_stats.largeS3tcBaseLevelBytes);
  reset(g_stats.deleteCalls);
  reset(g_stats.deletedTextureNames);
}

void record_gl_texture_generation(int count, std::uint64_t nanoseconds) noexcept {
  g_stats.textureGenerationCalls.fetch_add(1, std::memory_order_relaxed);
  if (count > 0) {
    g_stats.generatedTextureNames.fetch_add(static_cast<std::uint64_t>(count),
                                             std::memory_order_relaxed);
  }
  g_stats.textureGenerationNanoseconds.fetch_add(nanoseconds,
                                                  std::memory_order_relaxed);
}

void record_gl_uncompressed_upload(std::uint64_t knownBytes) noexcept {
  g_stats.uncompressedUploadCalls.fetch_add(1, std::memory_order_relaxed);
  if (knownBytes == 0) {
    g_stats.uncompressedUnknownByteCalls.fetch_add(1, std::memory_order_relaxed);
  } else {
    g_stats.uncompressedKnownBytes.fetch_add(knownBytes, std::memory_order_relaxed);
  }
}

void record_gl_compressed_upload(int level, unsigned internalFormat, int width, int height,
                                 int imageSize, std::uint64_t nanoseconds) noexcept {
  g_stats.compressedUploadCalls.fetch_add(1, std::memory_order_relaxed);
  const auto bytes = imageSize > 0 ? static_cast<std::uint64_t>(imageSize) : 0;
  g_stats.compressedUploadBytes.fetch_add(bytes, std::memory_order_relaxed);
  g_stats.compressedUploadNanoseconds.fetch_add(nanoseconds,
                                                 std::memory_order_relaxed);
  auto maximum = g_stats.maximumCompressedUploadNanoseconds.load(
      std::memory_order_relaxed);
  while (nanoseconds > maximum &&
         !g_stats.maximumCompressedUploadNanoseconds.compare_exchange_weak(
             maximum, nanoseconds, std::memory_order_relaxed,
             std::memory_order_relaxed)) {
  }
  if (level != 0) return;

  g_stats.compressedBaseLevelCalls.fetch_add(1, std::memory_order_relaxed);
  if (width < kLargeTextureDimension || height < kLargeTextureDimension ||
      !is_s3tc(internalFormat)) {
    return;
  }
  g_stats.largeS3tcBaseLevelCalls.fetch_add(1, std::memory_order_relaxed);
  g_stats.largeS3tcBaseLevelBytes.fetch_add(bytes, std::memory_order_relaxed);
}

void record_gl_texture_delete(int count) noexcept {
  g_stats.deleteCalls.fetch_add(1, std::memory_order_relaxed);
  if (count > 0) {
    g_stats.deletedTextureNames.fetch_add(static_cast<std::uint64_t>(count),
                                          std::memory_order_relaxed);
  }
}

GlTextureTelemetryStats gl_texture_telemetry_snapshot() noexcept {
  return {
      .textureGenerationCalls =
          g_stats.textureGenerationCalls.load(std::memory_order_relaxed),
      .generatedTextureNames =
          g_stats.generatedTextureNames.load(std::memory_order_relaxed),
      .textureGenerationNanoseconds =
          g_stats.textureGenerationNanoseconds.load(std::memory_order_relaxed),
      .uncompressedUploadCalls =
          g_stats.uncompressedUploadCalls.load(std::memory_order_relaxed),
      .uncompressedKnownBytes = g_stats.uncompressedKnownBytes.load(std::memory_order_relaxed),
      .uncompressedUnknownByteCalls =
          g_stats.uncompressedUnknownByteCalls.load(std::memory_order_relaxed),
      .compressedUploadCalls = g_stats.compressedUploadCalls.load(std::memory_order_relaxed),
      .compressedUploadBytes = g_stats.compressedUploadBytes.load(std::memory_order_relaxed),
      .compressedUploadNanoseconds =
          g_stats.compressedUploadNanoseconds.load(std::memory_order_relaxed),
      .maximumCompressedUploadNanoseconds =
          g_stats.maximumCompressedUploadNanoseconds.load(std::memory_order_relaxed),
      .compressedBaseLevelCalls =
          g_stats.compressedBaseLevelCalls.load(std::memory_order_relaxed),
      .largeS3tcBaseLevelCalls =
          g_stats.largeS3tcBaseLevelCalls.load(std::memory_order_relaxed),
      .largeS3tcBaseLevelBytes =
          g_stats.largeS3tcBaseLevelBytes.load(std::memory_order_relaxed),
      .deleteCalls = g_stats.deleteCalls.load(std::memory_order_relaxed),
      .deletedTextureNames = g_stats.deletedTextureNames.load(std::memory_order_relaxed),
  };
}

bool is_meaningful_load_area_call(bool areaChanged, bool timingAvailable,
                                  std::int64_t engineTicks,
                                  std::int64_t performanceFrequency) noexcept {
  if (areaChanged) return true;
  if (!timingAvailable || engineTicks < 0 || performanceFrequency <= 0) return true;
  const auto oneMillisecond = (performanceFrequency / 1000) > 0
                                  ? performanceFrequency / 1000
                                  : std::int64_t{1};
  return engineTicks >= oneMillisecond;
}

}  // namespace iee::core
