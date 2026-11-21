#pragma once

#include "iee/core/rgba_tile_decode.h"

#include <array>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string_view>
#include <vector>
#include <zlib.h>

namespace iee::core {

// A per-area seek table points into stored ZIP members. Only the current
// frame's bitmap and packed pixels are read. Expansion reuses the RGBA buffer.
class AreaAnimationArchive {
 public:
  AreaAnimationArchive(const std::filesystem::path& directory,
                       const std::filesystem::path& index,
                       std::span<const std::byte> registry)
      : index_(index, std::ios::binary),
        archive_(directory / "AreaAnimations-X4.zip", std::ios::binary | std::ios::ate) {
    std::array<unsigned char, 24> header{};
    const auto archiveEnd = archive_.tellg();
    if (archiveEnd < 0 || !read_bytes(index_, header.data(), header.size()) ||
        std::string_view(reinterpret_cast<const char*>(header.data()), 8) != "AAX4RUN1" ||
        number(header.data() + 8, 8) != static_cast<std::uint64_t>(archiveEnd) ||
        number(header.data() + 16, 4) != crc(registry)) {
      throw std::runtime_error("invalid area-animation archive or registry binding");
    }
    archiveBytes_ = static_cast<std::uint64_t>(archiveEnd);
    framesRemaining_ = static_cast<std::uint32_t>(number(header.data() + 20, 4));
  }

  bool read(unsigned width, unsigned height, std::span<std::byte> pixels) {
    std::array<unsigned char, 56> row{};
    if (!framesRemaining_ || !read_bytes(index_, row.data(), row.size())) return false;
    --framesRemaining_;
    const auto value = [&](unsigned offset) {
      return static_cast<std::uint32_t>(number(row.data() + offset, 4));
    };
    const RgbaTileRectangle rect{value(0), value(4), value(8), value(12), value(16), value(20)};
    const auto pixelOffset = number(row.data() + 24, 8);
    const auto maskOffset = number(row.data() + 32, 8);
    const auto packedBytes = value(40);
    const auto edge = value(52);
    if (rect.width != width || rect.height != height ||
        rect.x > width || rect.y > height || rect.w > width - rect.x || rect.h > height - rect.y ||
        (!rect.w != !rect.h) || (!rect.w && (rect.x || rect.y || edge)) ||
        (edge && (edge < 4 || edge > 64 || (edge & (edge - 1)))) ||
        packedBytes > pixels.size() || packedBytes % 4) return false;
    const auto denseBytes = std::uint64_t{rect.w} * rect.h * 4;
    if ((!edge && packedBytes != denseBytes) ||
        (edge && (!packedBytes || packedBytes > denseBytes))) return false;
    const auto bits = edge ? ((std::uint64_t{rect.w} + edge - 1) / edge) *
                             ((std::uint64_t{rect.h} + edge - 1) / edge) : 0;
    const auto maskBytes = static_cast<std::size_t>((bits + 7) / 8);
    if (maskOffset > archiveBytes_ || maskBytes > archiveBytes_ - maskOffset ||
        pixelOffset > archiveBytes_ || packedBytes > archiveBytes_ - pixelOffset) return false;
    bitmap_.resize(maskBytes);
    if (!read_at(maskOffset, bitmap_.data(), maskBytes) ||
        !read_at(pixelOffset, pixels.data(), packedBytes) ||
        crc(pixels.first(packedBytes)) != value(44) ||
        crc(std::as_bytes(std::span(bitmap_))) != value(48) ||
        !expand_rgba_tiles(rect, edge, bitmap_, packedBytes, pixels)) return false;
    bytesRead_ += maskBytes + packedBytes;
    return true;
  }

  bool finished() { return !framesRemaining_ && index_.peek() == std::char_traits<char>::eof(); }
  std::uint64_t bytes_read() const { return bytesRead_; }
  std::size_t bitmap_capacity() const { return bitmap_.capacity(); }

 private:
  static std::uint32_t crc(std::span<const std::byte> bytes) {
    return crc32_z(0, reinterpret_cast<const unsigned char*>(bytes.data()), bytes.size());
  }

  static std::uint64_t number(const unsigned char* data, unsigned size) {
    std::uint64_t value = 0;
    for (unsigned i = 0; i < size; ++i) value |= std::uint64_t{data[i]} << (8 * i);
    return value;
  }

  static bool read_bytes(std::ifstream& input, void* data, std::size_t bytes) {
    return static_cast<bool>(input.read(reinterpret_cast<char*>(data),
                                        static_cast<std::streamsize>(bytes)));
  }

  bool read_at(std::uint64_t offset, void* data, std::size_t bytes) {
    return !bytes || (archive_.seekg(static_cast<std::streamoff>(offset)) &&
                      read_bytes(archive_, data, bytes));
  }

  std::ifstream index_, archive_;
  std::uint64_t archiveBytes_{}, bytesRead_{};
  std::uint32_t framesRemaining_{};
  std::vector<unsigned char> bitmap_;
};

}  // namespace iee::core
