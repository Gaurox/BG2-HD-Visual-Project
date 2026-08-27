#pragma once

#include <filesystem>

namespace iee::biglogo {
struct ReplacementUpload {
  int width{};
  int height{};
  int byteCount{};
  const void* data{};
};

// Loads the selected pre-compressed x4 DXT5 atlases before rendering begins.
// Each missing or invalid asset leaves only that original game upload untouched.
bool prepare(const std::filesystem::path& assetsDirectory, int scale, bool includeBigLogo,
             bool includeMainMenu) noexcept;
void release() noexcept;

// Matches registered PVRZ pages by dimensions, DXT5 payload size, and fingerprint.
// The original upload remains the fallback for every mismatch.
bool try_replacement(unsigned target, int level, unsigned internalFormat, int width, int height,
                     int byteCount, const void* originalData,
                     ReplacementUpload& out) noexcept;
}  // namespace iee::biglogo
