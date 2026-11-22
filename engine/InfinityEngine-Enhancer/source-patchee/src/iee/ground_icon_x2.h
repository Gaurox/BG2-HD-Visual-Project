#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <span>

#include "iee/core/area_animation_lighting.h"
#include "iee/item_icon_x2.h"

namespace iee::ground_icon_x2 {

struct Layer {
  std::size_t asset{};
  int x{};
  int y{};
  bool highlighted{};
  core::area_lighting::Transfer lighting{};
};

bool prepare(const std::filesystem::path& directory) noexcept;
bool ready() noexcept;
void forget_textures() noexcept;

bool resolve(const std::array<char, 8>& resref, int width, int height,
             std::size_t& asset) noexcept;
bool bind(std::span<const Layer> layers, int width, int height,
          std::span<const std::uint8_t> visibility,
          const item_icon_x2::EngineTextureApi& api, int& previous) noexcept;

}  // namespace iee::ground_icon_x2
