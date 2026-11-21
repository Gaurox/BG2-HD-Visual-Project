#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <span>
#include <stdexcept>
#include <utility>
#include <vector>

namespace iee::core {

// IEECROP2, canonical/logical counts, registry/storage SHA256, then sorted
// (ID, canvas width/height, x/y, rectangle width/height, pixel offset) records.
class EffectCropIndex {
public:
  using Digest = std::array<std::byte, 32>;

  template <class Dimensions>
  EffectCropIndex(std::vector<std::byte> bytes, std::size_t logicalCount,
                  std::span<const std::uint32_t> shared, const Digest& registry, const Digest& storage,
                  std::filesystem::path pixels, std::uint64_t pixelBytes, Dimensions dimensions)
      : bytes_(std::move(bytes)), pixels_(std::move(pixels)) {
    constexpr char magic[] = "IEECROP2";
    if (bytes_.size() < kHeader ||
        !std::equal(magic, magic + 8, bytes_.begin(), [](char c, std::byte b) {
          return static_cast<unsigned char>(c) == std::to_integer<unsigned char>(b);
        }) || field(12, 4) != logicalCount ||
        !std::equal(registry.begin(), registry.end(), bytes_.begin() + 16) ||
        !std::equal(storage.begin(), storage.end(), bytes_.begin() + 48) ||
        (!shared.empty() && shared.size() != logicalCount)) {
      throw std::runtime_error("effect crop registry or storage binding differs");
    }
    count_ = static_cast<std::size_t>(field(8, 4));
    if (count_ > logicalCount || bytes_.size() != kHeader + kRecord * count_) {
      throw std::runtime_error("invalid effect crop index size");
    }
    std::uint64_t cursor = 0;
    std::size_t position = 0;
    for (std::size_t id = 0; id < logicalCount; ++id) {
      if (!shared.empty() && shared[id] != id) continue;
      if (position == count_) throw std::runtime_error("missing effect crop frame");
      const auto [width, height] = dimensions(id);
      const auto rect = record(position++);
      const auto size = std::uint64_t{rect.w} * rect.h * 4;
      if (rect.id != id || rect.width != width || rect.height != height ||
          rect.x + rect.w > width || rect.y + rect.h > height || rect.offset != cursor ||
          ((!rect.w || !rect.h) && (rect.x || rect.y || rect.w || rect.h)) ||
          cursor > pixelBytes || size > pixelBytes - cursor) {
        throw std::runtime_error("invalid effect crop frame rectangle or offset");
      }
      cursor += size;
    }
    if (position != count_ || cursor != pixelBytes) {
      throw std::runtime_error("effect crop payload size differs");
    }
  }

  [[nodiscard]] std::size_t count() const noexcept { return count_; }

  bool read(std::size_t canonicalId, std::span<std::byte> destination) const {
    std::size_t first = 0, last = count_;
    while (first < last) {
      const auto middle = first + (last - first) / 2;
      if (field(kHeader + kRecord * middle, 4) < canonicalId) first = middle + 1;
      else last = middle;
    }
    if (first == count_) return false;
    const auto rect = record(first);
    if (rect.id != canonicalId || destination.size() != std::uint64_t{rect.width} * rect.height * 4) {
      return false;
    }
    if (rect.w != rect.width || rect.h != rect.height)
      std::fill(destination.begin(), destination.end(), std::byte{0});
    if (!rect.w) return true;
    std::ifstream input(pixels_, std::ios::binary);
    if (!input.seekg(static_cast<std::streamoff>(rect.offset))) return false;
    const auto rowBytes = static_cast<std::size_t>(rect.w) * 4;
    const auto stride = static_cast<std::size_t>(rect.width) * 4;
    auto* out = reinterpret_cast<char*>(destination.data()) + rect.y * stride + rect.x * 4;
    if (rect.w == rect.width)
      return static_cast<bool>(input.read(out, static_cast<std::streamsize>(rowBytes * rect.h)));
    for (std::uint32_t row = 0; row < rect.h; ++row) {
      if (!input.read(out + row * stride, static_cast<std::streamsize>(rowBytes))) return false;
    }
    return true;
  }

private:
  struct Rectangle {
    std::uint32_t id, width, height, x, y, w, h;
    std::uint64_t offset;
  };
  static constexpr std::size_t kHeader = 80;
  static constexpr std::size_t kRecord = 24;
  std::vector<std::byte> bytes_;
  std::filesystem::path pixels_;
  std::size_t count_{};

  std::uint64_t field(std::size_t offset, std::size_t size) const noexcept {
    std::uint64_t value = 0;
    for (std::size_t i = 0; i < size; ++i)
      value |= std::uint64_t{std::to_integer<unsigned char>(bytes_[offset + i])} << (8 * i);
    return value;
  }

  Rectangle record(std::size_t position) const noexcept {
    const auto off = kHeader + kRecord * position;
    return {
        static_cast<std::uint32_t>(field(off, 4)), static_cast<std::uint32_t>(field(off + 4, 2)),
        static_cast<std::uint32_t>(field(off + 6, 2)), static_cast<std::uint32_t>(field(off + 8, 2)),
        static_cast<std::uint32_t>(field(off + 10, 2)), static_cast<std::uint32_t>(field(off + 12, 2)),
        static_cast<std::uint32_t>(field(off + 14, 2)), field(off + 16, 8)};
  }
};

}  // namespace iee::core
