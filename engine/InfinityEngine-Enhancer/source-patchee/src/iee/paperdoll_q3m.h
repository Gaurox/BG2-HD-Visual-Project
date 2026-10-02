#pragma once
#include <array>
#include <filesystem>
#include <span>
#include <vector>
#include "iee/core/palette_fraction.h"
#include "iee/item_icon_x2.h"
#include "iee/paperdoll_q3m_scope.h"

namespace iee::paperdoll_q3m {
struct Frame {
  int width{}, height{}, centerX{}, centerY{};
  std::vector<std::uint8_t> indices, fractions;
  core::palette_fraction::Dependencies dependencies{};
};
using Frames = std::vector<Frame>;
enum class ResourceId : std::size_t { Unarmored = 0, Leather = 1 };
// Explicit compiled allowlist; source hashes/geometry, independent frame tables and palettes.
bool resource_for_resref(const std::array<char, 8>& resref, ResourceId& body) noexcept;
const NativeGeometry* native_geometry(ResourceId resource, int slot) noexcept;
bool parse(std::span<const std::uint8_t> bytes, Frames& out,
           ResourceId body = ResourceId::Unarmored) noexcept;
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
           int& previousTexture, std::uint32_t& pixelCrc, bool& uploaded,
           ResourceId body = ResourceId::Unarmored) noexcept;
} // namespace iee::paperdoll_q3m
