#pragma once

#include <filesystem>

namespace iee::am3000a_x4 {
struct ReplacementUpload {
  int width{};
  int height{};
  const void* data{};
};

// Loads the raw RGBA x4 prototype before the renderer begins. A missing or
// invalid asset leaves every game upload untouched.
bool prepare(const std::filesystem::path& assetsDirectory) noexcept;
void release() noexcept;

// This first visual prototype is deliberately constrained to AM3000A's
// unique 248x221 source-frame geometry. It replaces every frame with frame 0
// so that geometry scaling can be tested before animation handling is added.
bool try_replacement(unsigned target, int level, int internalFormat, int width, int height,
                     int border, unsigned format, unsigned type, const void* originalData,
                     ReplacementUpload& out) noexcept;
}  // namespace iee::am3000a_x4
