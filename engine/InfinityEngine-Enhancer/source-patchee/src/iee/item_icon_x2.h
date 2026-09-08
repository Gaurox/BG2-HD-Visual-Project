#pragma once

#include <array>
#include <cstdint>
#include <filesystem>

namespace iee::item_icon_x2 {

struct FrameHandle {
  std::uint32_t recordIndex{};
  [[nodiscard]] constexpr bool operator==(const FrameHandle&) const noexcept = default;
};

struct EngineTextureApi {
  using DrawGenTextureFn = int (*)(int, unsigned char, int, unsigned char);
  using DrawBindTextureFn = void (*)(int);
  using DrawDeleteTextureFn = void (*)(int);
  using TexImageFn = void (*)(int, int, const void*, unsigned char);
  using DrawGetRendererFn = int (*)();
  DrawGenTextureFn DrawGenTexture{};
  DrawBindTextureFn DrawBindTexture{};
  DrawDeleteTextureFn DrawDeleteTexture{};
  TexImageFn TexImage{};
  DrawGetRendererFn DrawGetRenderer{};
  const std::uint32_t* glTextureState{};
};

bool prepare(const std::filesystem::path& assetsDirectory) noexcept;
void release() noexcept;
[[nodiscard]] bool ready() noexcept;
bool resolve_frame(const std::array<char, 8>& resref, int sequence, int currentFrame,
                   int playbackMode, int logicalWidth, int logicalHeight,
                   FrameHandle& out) noexcept;
bool bind_frame_texture(FrameHandle handle, int logicalWidth, int logicalHeight,
                        const EngineTextureApi& api, int& previousTextureId) noexcept;
void restore_texture(const EngineTextureApi& api, int previousTextureId) noexcept;
void forget_engine_textures() noexcept;

}  // namespace iee::item_icon_x2
