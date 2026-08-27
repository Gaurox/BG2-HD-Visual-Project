#pragma once

#include <filesystem>

namespace iee::am0700a_x4 {
struct ReplacementUpload {
  int width{};
  int height{};
  const void* data{};
};

// Loads all seven AM0700A x4 frames before any renderer hook can run. A
// missing, truncated, or inconsistent asset disables the complete test.
bool prepare(const std::filesystem::path& assetsDirectory) noexcept;
void release() noexcept;

// Matches an original AM0700A frame with the extracted BAM pixel fingerprint,
// then replaces only that matching upload. The x1 draw geometry is unchanged.
bool try_replacement(unsigned target, int level, int internalFormat, int width, int height,
                     int border, unsigned format, unsigned type, const void* originalData,
                     ReplacementUpload& out) noexcept;
}  // namespace iee::am0700a_x4
