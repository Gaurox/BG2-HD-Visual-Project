#pragma once

#include "iee/core/config.h"
#include "iee/core/sprite_minification.h"
#include "iee/game/opengl_types.h"

namespace iee::creature_sprite_filter {
// The caller owns the binding and unpack state. Publish ownership only after
// success. A partial/failed chain is never exposed with a mip sampler.
inline bool finish_texture_sampling(game::gl::OpenGLFunctions& gl,
                                    core::CreatureSpriteFilterMode mode,
                                    int width, int height, bool masked,
                                    int& maximumMipLevel) noexcept {
  maximumMipLevel = 0;
  if (!gl.glTexParameteri || !gl.glGetError) return false;
  const bool mips = mode == core::CreatureSpriteFilterMode::Mipmaps;
  const auto baseFilter = mode == core::CreatureSpriteFilterMode::Linear ||
      (masked && mode == core::CreatureSpriteFilterMode::Nearest)
          ? game::gl::LINEAR : game::gl::NEAREST;
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MIN_FILTER,
                     static_cast<int>(baseFilter));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER,
                     static_cast<int>(baseFilter));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAX_LEVEL, 0);
  if (!mips) return gl.glGetError() == game::gl::GL_NO_ERROR;
  const auto layout = core::sprite_minification::mip_layout(width, height);
  if (!gl.glGenerateMipmap || !gl.glGetTexLevelParameteriv ||
      layout.bytes == 0 || layout.maximumLevel == 0) return false;
  // MAX_LEVEL bounds generation itself. No draw/publication occurs until every
  // level is verified; failure restores MAX_LEVEL=0 and the base sampler.
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAX_LEVEL,
                     layout.maximumLevel);
  gl.glGenerateMipmap(game::gl::TEXTURE_2D);
  bool valid = gl.glGetError() == game::gl::GL_NO_ERROR;
  for (int level = 1; valid && level <= layout.maximumLevel; ++level) {
    width = (std::max)(1, width / 2);
    height = (std::max)(1, height / 2);
    int actualWidth = 0, actualHeight = 0;
    gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, level,
                                game::gl::TEXTURE_WIDTH, &actualWidth);
    gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, level,
                                game::gl::TEXTURE_HEIGHT, &actualHeight);
    valid = actualWidth == width && actualHeight == height &&
            gl.glGetError() == game::gl::GL_NO_ERROR;
  }
  if (valid) {
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MIN_FILTER,
                       static_cast<int>(game::gl::LINEAR_MIPMAP_LINEAR));
    valid = gl.glGetError() == game::gl::GL_NO_ERROR;
  }
  if (!valid) {
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAX_LEVEL, 0);
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MIN_FILTER,
                       static_cast<int>(baseFilter));
    return false;
  }
  maximumMipLevel = layout.maximumLevel;
  return true;
}
}  // namespace iee::creature_sprite_filter
