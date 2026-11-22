#include "iee/ground_icon_x2.h"

#include <algorithm>
#include <fstream>
#include <vector>

#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/opengl_types.h"

namespace iee::ground_icon_x2 {
namespace {

constexpr int kGroundSampler = static_cast<int>(game::gl::NEAREST);

struct Asset {
  std::array<char, 8> resref{};
  std::uint16_t width{}, height{};
  std::vector<std::uint8_t> body, outline;
};

struct Texture {
  int id{};
  int width{}, height{};
  std::vector<std::uint8_t> pixels;
};

std::vector<Asset> assets;
std::vector<Texture> textures;
HGLRC textureContext{};

template <typename T>
bool read(std::istream& source, T& out) {
  return bool(source.read(reinterpret_cast<char*>(&out), sizeof(out)));
}

int logical_texture(const item_icon_x2::EngineTextureApi& api) noexcept {
  std::uint32_t state{};
  return api.glTextureState && core::safe_read(api.glTextureState, state)
      ? static_cast<int>((state >> 21u) & 0x1FFu) : 0;
}

void over(std::uint8_t* target, const std::uint8_t* pixel,
          const core::area_lighting::Transfer* lighting = nullptr) noexcept {
  const unsigned a = pixel[3], b = target[3];
  if (!a) return;
  const unsigned retained = b * (255 - a);
  const unsigned combined = a * 255 + retained;
  for (int c = 0; c < 3; ++c) {
    const unsigned color = lighting && lighting->valid ? lighting->rgb[c][pixel[c]] : pixel[c];
    target[c] = static_cast<std::uint8_t>((color * a * 255 + target[c] * retained + combined / 2) / combined);
  }
  target[3] = static_cast<std::uint8_t>((combined + 127) / 255);
}

bool upload(Texture& entry, const item_icon_x2::EngineTextureApi& api, int previous) noexcept {
  auto& gl = game::gl::get_gl_functions();
  if ((!gl.valid && !gl.initialize()) || !gl.glGetIntegerv || !gl.glTexImage2D ||
      !gl.glTexParameteri || !gl.glPixelStorei || !gl.glGetError ||
      !gl.glGetTexLevelParameteriv || !gl.glGetTexParameteriv)
    return false;

  constexpr std::array<unsigned, 4> names{
      game::gl::UNPACK_ALIGNMENT, game::gl::UNPACK_ROW_LENGTH,
      game::gl::UNPACK_SKIP_ROWS, game::gl::UNPACK_SKIP_PIXELS};
  std::array<int, 4> values{};
  int unpackBuffer{};
  gl.glGetIntegerv(game::gl::PIXEL_UNPACK_BUFFER_BINDING, &unpackBuffer);
  if (unpackBuffer) return false;
  for (std::size_t i = 0; i < names.size(); ++i) gl.glGetIntegerv(names[i], &values[i]);
  game::gl::discard_errors();
  for (std::size_t i = 0; i < names.size(); ++i) gl.glPixelStorei(names[i], i == 0 ? 1 : 0);

  api.DrawBindTexture(entry.id);
  api.TexImage(entry.width, entry.height, nullptr, 0);
  int bound{};
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &bound);
  bool ok = bound > 0 && gl.glGetError() == game::gl::GL_NO_ERROR;
  if (ok) {
    gl.glTexImage2D(game::gl::TEXTURE_2D, 0, static_cast<int>(game::gl::RGBA8),
                    entry.width * 2, entry.height * 2, 0, game::gl::RGBA,
                    game::gl::UNSIGNED_BYTE, entry.pixels.data());
    for (auto parameter : {game::gl::TEXTURE_WRAP_S, game::gl::TEXTURE_WRAP_T})
      gl.glTexParameteri(game::gl::TEXTURE_2D, parameter, static_cast<int>(game::gl::CLAMP_TO_EDGE));
    for (auto parameter : {game::gl::TEXTURE_MIN_FILTER, game::gl::TEXTURE_MAG_FILTER})
      gl.glTexParameteri(game::gl::TEXTURE_2D, parameter, kGroundSampler);
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAX_LEVEL, 0);
    int w{}, h{}, minFilter{}, magFilter{};
    gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_WIDTH, &w);
    gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_HEIGHT, &h);
    gl.glGetTexParameteriv(game::gl::TEXTURE_2D, game::gl::TEXTURE_MIN_FILTER, &minFilter);
    gl.glGetTexParameteriv(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER, &magFilter);
    ok = w == entry.width * 2 && h == entry.height * 2 && minFilter == kGroundSampler &&
         magFilter == kGroundSampler && gl.glGetError() == game::gl::GL_NO_ERROR;
  }
  for (std::size_t i = 0; i < names.size(); ++i) gl.glPixelStorei(names[i], values[i]);
  api.DrawBindTexture(previous);
  return ok;
}

}  // namespace

bool prepare(const std::filesystem::path& directory) noexcept {
  assets.clear();
  try {
    std::ifstream source(directory / "GroundItems-X2.registry", std::ios::binary);
    constexpr std::array<char, 8> magic{'I', 'E', 'E', 'G', 'I', 'X', '2', 0};
    std::array<char, 8> header{};
    std::uint32_t count{};
    if (!read(source, header) || header != magic || !read(source, count) || !count || count > 256)
      return false;
    std::vector<Asset> entries;
    entries.reserve(count);
    for (std::uint32_t i = 0; i < count; ++i) {
      auto& asset = entries.emplace_back();
      if (!read(source, asset.resref) || !read(source, asset.width) || !read(source, asset.height) ||
          !asset.width || !asset.height || asset.width > 128 || asset.height > 128 ||
          (i && entries[i - 1].resref >= asset.resref))
        return false;
      const auto bytes = static_cast<std::size_t>(asset.width) * asset.height * 16;
      asset.body.resize(bytes);
      asset.outline.resize(bytes);
      for (auto* rgba : {&asset.body, &asset.outline})
        if (!source.read(reinterpret_cast<char*>(rgba->data()), static_cast<std::streamsize>(bytes)))
          return false;
    }
    if (source.peek() != std::char_traits<char>::eof()) return false;
    assets = std::move(entries);
    LOG_INFO("Ground icon x2 registry loaded: {} assets", count);
    return true;
  } catch (...) {
    return false;
  }
}

bool ready() noexcept { return !assets.empty(); }

void forget_textures() noexcept {
  textures.clear();
  textureContext = nullptr;
}

bool resolve(const std::array<char, 8>& resref, int width, int height,
             std::size_t& asset) noexcept {
  const auto found = std::lower_bound(assets.begin(), assets.end(), resref,
      [](const Asset& current, const auto& wanted) { return current.resref < wanted; });
  if (found == assets.end() || found->resref != resref ||
      found->width != width || found->height != height)
    return false;
  asset = static_cast<std::size_t>(found - assets.begin());
  return true;
}

bool bind(std::span<const Layer> layers, int width, int height,
          std::span<const std::uint8_t> visibility,
          const item_icon_x2::EngineTextureApi& api, int& previous) noexcept {
  try {
    if (width <= 0 || height <= 0 || width > 160 || height > 160 || layers.empty() ||
        !api.DrawGenTexture || !api.DrawBindTexture || !api.DrawDeleteTexture ||
        !api.TexImage || !api.DrawGetRenderer || api.DrawGetRenderer() == 1) return false;
    if (!visibility.empty() && visibility.size() != static_cast<std::size_t>(width) * height * 4)
      return false;
    const auto context = game::gl::current_context();
    if (!context) return false;
    if (textureContext != context) {
      forget_textures();
      textureContext = context;
      textures.reserve(24);
    }
    previous = logical_texture(api);
    if (previous <= 0) return false;
    Texture candidate{0, width, height,
        std::vector<std::uint8_t>(static_cast<std::size_t>(width) * height * 16)};
    const int stride = width * 2;
    for (const auto& layer : layers) {
      if (layer.asset >= assets.size()) return false;
      const auto& asset = assets[layer.asset];
      if (layer.x < 0 || layer.y < 0 || layer.x + asset.width > width || layer.y + asset.height > height)
        return false;
      const int layerWidth = asset.width * 2;
      for (int y = 0; y < asset.height * 2; ++y) {
        for (int x = 0; x < layerWidth; ++x) {
          auto* target = candidate.pixels.data() + ((layer.y * 2 + y) * stride + layer.x * 2 + x) * 4;
          const auto offset = (y * layerWidth + x) * 4;
          if (layer.highlighted) over(target, asset.outline.data() + offset);
          over(target, asset.body.data() + offset, &layer.lighting);
        }
      }
    }
    if (!visibility.empty()) {
      for (int y = 0; y < height * 2; ++y) {
        for (int x = 0; x < width * 2; ++x) {
          auto* pixel = candidate.pixels.data() + (y * stride + x) * 4;
          const auto* mask = visibility.data() + ((y / 2) * width + x / 2) * 4;
          if (mask[1]) {
            pixel[0] = pixel[1] = pixel[2] = 0;
            pixel[3] = mask[1];
          } else {
            pixel[3] = mask[2] ? 0 : static_cast<std::uint8_t>((pixel[3] * mask[0] + 127) / 255);
          }
        }
      }
    }
    auto found = std::find_if(textures.begin(), textures.end(), [&](const Texture& entry) {
      return entry.width == width && entry.height == height && entry.pixels == candidate.pixels;
    });
    if (found != textures.end()) {
      std::rotate(found, found + 1, textures.end());
    } else {
      candidate.id = api.DrawGenTexture(kGroundSampler, 0, 0, 0);
      if (candidate.id <= 0) return false;
      if (!upload(candidate, api, previous)) {
        api.DrawDeleteTexture(candidate.id);
        return false;
      }
      if (textures.size() == 24) {
        api.DrawDeleteTexture(textures.front().id);
        textures.erase(textures.begin());
      }
      textures.push_back(std::move(candidate));
    }
    api.DrawBindTexture(textures.back().id);
    return true;
  } catch (...) {
    return false;
  }
}

}  // namespace iee::ground_icon_x2
