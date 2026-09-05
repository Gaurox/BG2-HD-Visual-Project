#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace iee::native_occlusion_bridge {
struct EngineTextureApi {
  using DrawGenTextureFn = int (*)(int filter, unsigned char formatKind, int wrapMode,
                                   unsigned char secondaryTexture);
  using DrawBindTextureFn = void (*)(int textureId);
  using DrawDeleteTextureFn = void (*)(int textureId);
  using TexImageFn = void (*)(int width, int height, const void* pixels,
                              unsigned char secondaryTexture);

  DrawGenTextureFn DrawGenTexture{};
  DrawBindTextureFn DrawBindTexture{};
  DrawDeleteTextureFn DrawDeleteTexture{};
  TexImageFn TexImage{};
  const std::uint32_t* glTextureState{};
  std::byte* glTextureTable{};
};

// The caller has already bound an external x2/x4 backing. This function
// creates one transient engine texture, applies the exact logical x1 WED
// visibility mask on the GPU, and binds the result for the original final
// CVidCell draw. Every failure rebinds replacementTextureId and returns false.
bool bind_masked_texture(const std::vector<std::uint8_t>& visibilityTransfer,
                         int logicalWidth, int logicalHeight,
                         int replacementTextureId, const EngineTextureApi& api,
                         int& transientTextureId) noexcept;

void finish_masked_texture(const EngineTextureApi& api, int nativeTextureId,
                           int transientTextureId) noexcept;

// Deletes persistent shader/FBO/mask resources when their WGL context is
// current. A lost context is simply forgotten because its names are already
// invalid in the replacement context.
void shutdown() noexcept;
}  // namespace iee::native_occlusion_bridge
