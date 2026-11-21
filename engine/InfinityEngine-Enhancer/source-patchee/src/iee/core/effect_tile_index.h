#pragma once

#include "iee/core/effect_crop_index.h"
#include "iee/core/rgba_tile_decode.h"

#include <cstring>
#include <limits>
#include <memory>
#include <string_view>

namespace iee::core {

// The fixed records and bitmaps stay on disk. A decoder owns only the current
// bitmap, and expands packed pixels backwards inside the cache's RGBA buffer.
class EffectTileIndex {
public:
  EffectTileIndex(std::shared_ptr<const EffectCropIndex> crop, std::filesystem::path index,
                  std::filesystem::path pixels, const EffectCropIndex::Digest& cropHash,
                  std::size_t logicalCount, std::uint64_t pixelBytes)
      : crop_(std::move(crop)), index_(std::move(index)), pixels_(std::move(pixels)),
        pixelBytes_(pixelBytes), bitmapBase_(kHeader + kRecord * crop_->count()) {
    std::ifstream input(index_, std::ios::binary);
    const auto indexBytes = std::filesystem::file_size(index_);
    std::array<unsigned char, kHeader> header{};
    if (indexBytes < bitmapBase_ || indexBytes - bitmapBase_ > std::numeric_limits<std::uint32_t>::max() ||
        !read_bytes(input, header.data(), header.size()) ||
        std::string_view(reinterpret_cast<const char*>(header.data()), 8) != "IEETILE1" ||
        number(header.data() + 8, 4) != crop_->count() || number(header.data() + 12, 4) != logicalCount ||
        std::memcmp(header.data() + 16, cropHash.data(), cropHash.size()) != 0) {
      throw std::runtime_error("invalid effect tile index header or crop binding");
    }
    bitmapBytes_ = indexBytes - bitmapBase_;
    Record current{};
    if (crop_->count() && (!read_record(input, current) || current.offset || current.bitmap))
      throw std::runtime_error("invalid first effect tile record");
    for (std::size_t pos = 0; pos < crop_->count(); ++pos) {
      Record next{pixelBytes_, bitmapBytes_, 0};
      if ((pos + 1 < crop_->count() && !read_record(input, next)) ||
          !valid_frame(crop_->record(pos), current, next)) {
        throw std::runtime_error("invalid effect tile offsets or rectangle");
      }
      maxBitmapBytes_ = std::max(maxBitmapBytes_, static_cast<std::size_t>(next.bitmap - current.bitmap));
      current = next;
    }
    if (!crop_->count() && (bitmapBytes_ || pixelBytes_)) throw std::runtime_error("unexpected effect tile data");
  }

  [[nodiscard]] std::size_t max_bitmap_bytes() const noexcept { return maxBitmapBytes_; }

  bool read(std::size_t id, std::span<std::byte> destination) const {
    const auto pos = crop_->find(id);
    if (pos == crop_->count()) return false;
    const auto rect = crop_->record(pos);
    if (destination.size() != std::uint64_t{rect.width} * rect.height * 4) return false;
    std::ifstream index(index_, std::ios::binary);
    Record current{}, next{pixelBytes_, bitmapBytes_, 0};
    if (!index.seekg(static_cast<std::streamoff>(kHeader + kRecord * pos)) || !read_record(index, current) ||
        (pos + 1 < crop_->count() && !read_record(index, next)) || !valid_frame(rect, current, next) ||
        next.bitmap - current.bitmap > maxBitmapBytes_) return false;

    std::vector<unsigned char> bitmap(static_cast<std::size_t>(next.bitmap - current.bitmap));
    if (!bitmap.empty() && (!index.seekg(static_cast<std::streamoff>(bitmapBase_ + current.bitmap)) ||
        !read_bytes(index, bitmap.data(), bitmap.size()))) return false;
    auto remaining = static_cast<std::size_t>(next.offset - current.offset);
    if (remaining) {
      std::ifstream source(pixels_, std::ios::binary);
      if (!source.seekg(static_cast<std::streamoff>(current.offset)) ||
          !read_bytes(source, destination.data(), remaining)) return false;
    }

    return expand_rgba_tiles({rect.width, rect.height, rect.x, rect.y, rect.w, rect.h},
                             current.edge, bitmap, remaining, destination);
  }

private:
  struct Record { std::uint64_t offset, bitmap; std::uint32_t edge; };
  static constexpr std::size_t kHeader = 48, kRecord = 16;
  std::shared_ptr<const EffectCropIndex> crop_;
  std::filesystem::path index_, pixels_;
  std::uint64_t pixelBytes_, bitmapBase_, bitmapBytes_{};
  std::size_t maxBitmapBytes_{};

  static bool read_bytes(std::ifstream& input, void* data, std::size_t bytes) {
    return static_cast<bool>(input.read(reinterpret_cast<char*>(data), static_cast<std::streamsize>(bytes)));
  }

  static std::uint64_t number(const unsigned char* data, unsigned size) {
    std::uint64_t value = 0;
    for (unsigned i = 0; i < size; ++i) value |= std::uint64_t{data[i]} << (8 * i);
    return value;
  }

  static bool read_record(std::ifstream& input, Record& record) {
    std::array<unsigned char, kRecord> bytes{};
    if (!read_bytes(input, bytes.data(), bytes.size()) || number(bytes.data() + 13, 3)) return false;
    record = {number(bytes.data(), 8), number(bytes.data() + 8, 4), bytes[12]};
    return true;
  }

  bool valid_frame(const EffectCropIndex::Rectangle& rect, Record current, Record next) const {
    if (next.offset > pixelBytes_ || current.offset > next.offset ||
        next.bitmap > bitmapBytes_ || current.bitmap > next.bitmap) return false;
    const auto dense = std::uint64_t{rect.w} * rect.h * 4;
    const auto pixels = next.offset - current.offset;
    const auto bitmap = next.bitmap - current.bitmap;
    const auto edge = current.edge;
    if (!edge) return pixels == dense && !bitmap;
    if (edge < 4 || edge > 64 || (edge & (edge - 1)) || !rect.w || !pixels || pixels > dense || pixels % 4)
      return false;
    return bitmap == (((rect.w + edge - 1) / edge) * ((rect.h + edge - 1) / edge) + 7) / 8;
  }
};

}  // namespace iee::core
