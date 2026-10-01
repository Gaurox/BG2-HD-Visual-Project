#pragma once
#include <array>
#include <filesystem>
#include <span>
#include <vector>
#include "iee/core/palette_fraction.h"
#include "iee/item_icon_x2.h"

namespace iee::paperdoll_q3m {
struct Frame {
  int width{}, height{}, centerX{}, centerY{};
  std::vector<std::uint8_t> indices, fractions;
  core::palette_fraction::Dependencies dependencies{};
};
using Frames = std::array<Frame, 2>;
// Strict CHFF1INV-only, raw V6 x2 reader. No global creature catalog state.
bool parse(std::span<const std::uint8_t> bytes, Frames& out) noexcept;
bool decode(const Frame& frame, core::palette_fraction::Palette palette,
             std::vector<std::uint32_t>& pixels) noexcept;
bool prepare(const std::filesystem::path& directory) noexcept;
bool ready() noexcept;
void release() noexcept;
void forget_engine_textures() noexcept;
struct TextureApi {
  item_icon_x2::EngineTextureApi engine{};
  const std::byte* glTextureTable{};
  void (*DrawFlushGl)(){};
};
bool bind(int sequence, int slot, int width, int height,
           core::palette_fraction::Palette palette, const TextureApi& api,
           int& previousTexture, std::uint32_t& pixelCrc, bool& uploaded) noexcept;
} // namespace iee::paperdoll_q3m
