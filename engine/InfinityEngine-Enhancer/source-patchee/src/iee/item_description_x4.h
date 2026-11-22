#pragma once

#include <cstdint>
#include <filesystem>

namespace iee {
struct AppContext;

namespace item_description_x4 {
bool prepare(const std::filesystem::path& directory) noexcept;
bool ready() noexcept;
void install(const AppContext& ctx) noexcept;
void remove() noexcept;
void disable() noexcept;
void forget_textures() noexcept;

struct CellScope {
  CellScope(void* cell, std::uintptr_t caller) noexcept;
  ~CellScope();
  CellScope(const CellScope&) = delete;
  CellScope& operator=(const CellScope&) = delete;

 private:
  void* previous_{};
};
}  // namespace item_description_x4
}  // namespace iee
