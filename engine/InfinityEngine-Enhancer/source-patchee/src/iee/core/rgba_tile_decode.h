#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <span>

namespace iee::core {

struct RgbaTileRectangle {
  std::uint32_t width, height, x, y, w, h;
};

// Expand row-major packed pixels from the beginning of a full RGBA canvas.
inline bool expand_rgba_tiles(const RgbaTileRectangle& rect, unsigned edge,
                              std::span<const unsigned char> bitmap, std::size_t remaining,
                              std::span<std::byte> destination) {
  if (!rect.width || !rect.height || rect.x > rect.width || rect.y > rect.height ||
      rect.w > rect.width - rect.x || rect.h > rect.height - rect.y ||
      (!rect.w != !rect.h) || remaining > destination.size() ||
      destination.size() != std::uint64_t{rect.width} * rect.height * 4) return false;
  const auto bits = edge ? ((std::uint64_t{rect.w} + edge - 1) / edge) *
                          ((std::uint64_t{rect.h} + edge - 1) / edge) : 0;
  if (bitmap.size() != (bits + 7) / 8) return false;
  if (!edge && rect.w == rect.width && rect.h == rect.height)
    return remaining == destination.size();
  std::size_t writeEnd = destination.size();
  const auto move = [&](std::size_t start, std::size_t bytes) {
    if (bytes > remaining || start < remaining - bytes || start + bytes > writeEnd) return false;
    remaining -= bytes;
    std::memmove(destination.data() + start, destination.data() + remaining, bytes);
    std::fill(destination.begin() + start + bytes, destination.begin() + writeEnd, std::byte{});
    writeEnd = start;
    return true;
  };
  if (rect.w) {
    if (!edge) {
      for (auto y = rect.h; y-- > 0;) {
        const auto start = (std::size_t{rect.y + y} * rect.width + rect.x) * 4;
        if (!move(start, std::size_t{rect.w} * 4)) return false;
      }
    } else {
      const auto columns = (rect.w + edge - 1) / edge;
      if (bits % 8 && (bitmap.back() >> (bits % 8))) return false;
      for (auto y = rect.h; y-- > 0;) {
        const auto row = (y / edge) * columns;
        const auto active = [&](unsigned x) {
          const auto bit = row + x;
          return (bitmap[bit / 8] >> (bit % 8)) & 1;
        };
        for (auto x = columns; x;) {
          if (!active(x - 1)) { --x; continue; }
          const auto right = std::min(rect.w, x * edge);
          do { --x; } while (x && active(x - 1));
          const auto left = x * edge;
          const auto start = (std::size_t{rect.y + y} * rect.width + rect.x + left) * 4;
          if (!move(start, std::size_t{right - left} * 4)) return false;
        }
      }
    }
  }
  if (remaining) return false;
  std::fill(destination.begin(), destination.begin() + writeEnd, std::byte{});
  return true;
}

}  // namespace iee::core
