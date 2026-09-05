#pragma once

#include <cstdint>

namespace iee::core {

// Process-wide GL counters for the current area load window. These describe
// calls observed at the OpenGL boundary; compressed uploads can also belong
// to BAM V2 or MOS V2 resources and are therefore not labeled as map PVRZ.
struct GlTextureTelemetryStats {
  std::uint64_t textureGenerationCalls{};
  std::uint64_t generatedTextureNames{};
  std::uint64_t textureGenerationNanoseconds{};
  std::uint64_t uncompressedUploadCalls{};
  std::uint64_t uncompressedKnownBytes{};
  std::uint64_t uncompressedUnknownByteCalls{};
  std::uint64_t compressedUploadCalls{};
  std::uint64_t compressedUploadBytes{};
  std::uint64_t compressedUploadNanoseconds{};
  std::uint64_t maximumCompressedUploadNanoseconds{};
  std::uint64_t compressedBaseLevelCalls{};
  std::uint64_t largeS3tcBaseLevelCalls{};
  std::uint64_t largeS3tcBaseLevelBytes{};
  std::uint64_t deleteCalls{};
  std::uint64_t deletedTextureNames{};
};

void reset_gl_texture_telemetry() noexcept;
void record_gl_texture_generation(int count, std::uint64_t nanoseconds) noexcept;
void record_gl_uncompressed_upload(std::uint64_t knownBytes) noexcept;
void record_gl_compressed_upload(int level, unsigned internalFormat, int width, int height,
                                 int imageSize,
                                 std::uint64_t nanoseconds = 0) noexcept;
void record_gl_texture_delete(int count) noexcept;
[[nodiscard]] GlTextureTelemetryStats gl_texture_telemetry_snapshot() noexcept;

// LoadArea can be followed by same-area calls that return almost immediately.
// Treat them as telemetry no-ops while failing open when timing is unavailable.
[[nodiscard]] bool is_meaningful_load_area_call(bool areaChanged, bool timingAvailable,
                                                std::int64_t engineTicks,
                                                std::int64_t performanceFrequency) noexcept;

}  // namespace iee::core
