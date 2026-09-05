#pragma once

#include <cstdint>
#include <filesystem>

namespace iee::am0205e_x4 {
struct ReplacementUpload {
  int width{};
  int height{};
  const void* data{};
  int frameIndex{-1};
};

// Loads all nine AM0205E x4 frames before any renderer hook can run. A missing,
// truncated, or inconsistent asset disables the complete test.
bool prepare(const std::filesystem::path& assetsDirectory) noexcept;
void release() noexcept;
[[nodiscard]] bool ready() noexcept;

// Minimal engine bridge used by the high-level AM0205E composition hook.
// DrawGenTexture/TexImage register a 165x130 logical texture with the engine;
// the prototype then replaces only the physical GL storage with the 660x520
// pixels loaded by prepare().
struct EngineTextureApi {
  using DrawGenTextureFn = int (*)(int filter, unsigned char formatKind, int wrapMode,
                                   unsigned char secondaryTexture);
  using DrawBindTextureFn = void (*)(int textureId);
  using DrawDeleteTextureFn = void (*)(int textureId);
  using TexImageFn = void (*)(int width, int height, const void* pixels,
                              unsigned char secondaryTexture);
  using DrawGetRendererFn = int (*)();

  DrawGenTextureFn DrawGenTexture{};
  DrawBindTextureFn DrawBindTexture{};
  DrawDeleteTextureFn DrawDeleteTexture{};
  TexImageFn TexImage{};
  DrawGetRendererFn DrawGetRenderer{};
  const std::uint32_t* glTextureState{};
};

// Binds the x4 physical texture corresponding to the current BAM frame while
// returning the engine texture id that must be restored after the draw.
bool bind_frame_texture(int frameIndex, const EngineTextureApi& api,
                        int& previousTextureId) noexcept;
void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept;
void forget_engine_textures() noexcept;

// Matches an original AM0205E frame with the extracted BAM pixel fingerprint,
// then replaces only that matching upload. The x1 draw geometry is unchanged.
bool try_replacement(unsigned target, int level, int internalFormat, int width, int height,
                     int border, unsigned format, unsigned type, const void* originalData,
                     ReplacementUpload& out) noexcept;

// Area BAMs are streamed into a shared texture atlas. This matcher identifies
// the x1 rectangle supplied to glTexSubImage2D; the renderer hook is then
// responsible for promoting the complete atlas before using the x4 pixels.
bool try_subimage_replacement(unsigned target, int level, int width, int height,
                              unsigned format, unsigned type, const void* originalData,
                              ReplacementUpload& out) noexcept;

// Records the first effective atlas replacement for each animation frame.
void log_atlas_replacement(int frameIndex, unsigned texture, int xoffset, int yoffset,
                           bool atlasPromoted) noexcept;
}  // namespace iee::am0205e_x4
