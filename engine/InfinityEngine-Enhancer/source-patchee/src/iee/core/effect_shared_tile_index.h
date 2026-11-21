#pragma once

#include "iee/core/effect_crop_index.h"

#include <cstring>
#include <limits>
#include <memory>
#include <windows.h>

namespace iee::core {

// Read-only views keep the dictionary, stream and indexes file-backed.
class EffectTileFile {
 public:
  EffectTileFile(const std::filesystem::path& path, std::uint64_t limit) {
    const auto file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
                                  OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) throw std::runtime_error("missing shared effect file");
    LARGE_INTEGER size{};
    const bool valid = GetFileSizeEx(file, &size) && size.QuadPart >= 0 &&
                       static_cast<std::uint64_t>(size.QuadPart) <= limit &&
                       static_cast<std::uint64_t>(size.QuadPart) <=
                           (std::numeric_limits<std::size_t>::max)();
    const auto mapping = valid && size.QuadPart
        ? CreateFileMappingW(file, nullptr, PAGE_READONLY, 0, 0, nullptr) : nullptr;
    if (mapping) {
      data_ = static_cast<const std::byte*>(MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0));
      CloseHandle(mapping);
    }
    CloseHandle(file);
    if (!valid || (size.QuadPart && !data_))
      throw std::runtime_error("cannot map shared effect file");
    bytes_ = static_cast<std::size_t>(size.QuadPart);
  }

  ~EffectTileFile() { if (data_) UnmapViewOfFile(data_); }
  EffectTileFile(const EffectTileFile&) = delete;
  EffectTileFile& operator=(const EffectTileFile&) = delete;
  std::span<const std::byte> bytes() const { return {data_, bytes_}; }

 private:
  const std::byte* data_{};
  std::size_t bytes_{};
};

class EffectSharedTileIndex {
 public:
  template<class Hash>
  EffectSharedTileIndex(std::shared_ptr<const EffectCropIndex> crop,
                        const std::filesystem::path& directory, const EffectCropIndex::Digest& cropHash,
                        std::size_t logicalCount, std::uint64_t limit, Hash hash)
      : crop_(std::move(crop)),
        tiles_(directory / "EffectTiles-X4.index", limit),
        shared_(directory / "EffectSharedTiles-X4.index", limit - tiles_.bytes().size()),
        pixels_(directory / "EffectSharedTiles-X4.bin", limit - tiles_.bytes().size() - shared_.bytes().size()),
        dictionary_(directory / "EffectSharedTiles-X4.dictionary.rgba",
                    limit - tiles_.bytes().size() - shared_.bytes().size() - pixels_.bytes().size()),
        tileBase_(kHeader + kTileRecord * crop_->count()),
        sharedBase_(kHeader + kShareRecord * crop_->count()) {
    if (tiles_.bytes().size() < tileBase_ || shared_.bytes().size() < sharedBase_ ||
        !header(tiles_.bytes(), "IEETILE1", logicalCount, cropHash) ||
        !header(shared_.bytes(), "IEETSHR1", logicalCount, hash(tiles_.bytes())) ||
        dictionary_.bytes().size() % 4) {
      throw std::runtime_error("invalid effect dictionary or index binding");
    }
    if (tile_record(0).mask || share_record(0).mask || share_record(0).offset ||
        (!crop_->count() && !dictionary_.bytes().empty()))
      throw std::runtime_error("invalid initial shared effect offsets");
    for (std::size_t pos = 0; pos < crop_->count(); ++pos) {
      if (!valid_frame(pos, crop_->record(pos)))
        throw std::runtime_error("invalid shared effect frame layout");
    }
  }

  std::size_t dictionary_bytes() const { return dictionary_.bytes().size(); }

  bool read(std::size_t id, std::span<std::byte> canvas) const {
    const auto pos = crop_->find(id);
    if (pos == crop_->count()) return false;
    const auto rect = crop_->record(pos);
    if (canvas.size() != std::uint64_t{rect.width} * rect.height * 4) return false;
    const auto current = share_record(pos), next = share_record(pos+1);
    auto payload = pixels_.bytes().subspan(current.offset, next.offset-current.offset);
    const auto tile = tile_record(pos);
    const auto stride = std::size_t{rect.width} * 4;
    if (!tile.edge && rect.w == rect.width && rect.h == rect.height) {
      std::memcpy(canvas.data(), payload.data(), payload.size());
      return true;
    }
    std::fill(canvas.begin(), canvas.end(), std::byte{});
    const auto copy_tile = [&](const std::byte* src, unsigned x, unsigned y, unsigned w, unsigned h) {
      const auto bytes = std::size_t{w} * 4;
      auto* out = canvas.data() + (rect.y+y)*stride + std::size_t{rect.x+x}*4;
      for (unsigned row = 0; row < h; ++row)
        std::memcpy(out + row*stride, src + row*bytes, bytes);
    };
    if (!tile.edge) {
      if (rect.w) copy_tile(payload.data(), 0, 0, rect.w, rect.h);
      return true;
    }
    const auto activeMask = tiles_.bytes().subspan(tileBase_ + tile.mask, tile_record(pos+1).mask - tile.mask);
    const auto shareMask = shared_.bytes().subspan(sharedBase_ + current.mask, next.mask-current.mask);
    const auto edge = tile.edge;
    const auto cells = ((rect.w+edge-1)/edge) * ((rect.h+edge-1)/edge);
    if (!padding_zero(activeMask, cells) || (current.shared && !padding_zero(shareMask, current.tiles)))
      return false;
    unsigned cell = 0, seen = 0, references = 0;
    for (unsigned y = 0; y < rect.h; y += edge) {
      for (unsigned x = 0; x < rect.w; x += edge, ++cell) {
        if (!bit(activeMask, cell)) continue;
        if (seen >= current.tiles) return false;
        const auto w = std::min(edge, rect.w - x), h = std::min(edge, rect.h - y);
        const auto bytes = std::size_t{w} * h * 4;
        const bool reuse = current.shared && bit(shareMask, seen);
        ++seen;
        const auto used = reuse ? 4u : bytes;
        if (used > payload.size()) return false;
        const auto* source = payload.data();
        if (reuse) {
          const auto address = number(payload, 0, 4);
          if (!address) return false;
          const auto offset = (address-1)*4;
          const auto dictionary = dictionary_.bytes();
          if (offset > dictionary.size() || bytes > dictionary.size()-offset) return false;
          source = dictionary.data()+offset;
          ++references;
        }
        copy_tile(source, x, y, w, h);
        payload = payload.subspan(used);
      }
    }
    return payload.empty() && seen == current.tiles && references == current.shared;
  }

 private:
  struct TileRecord { std::size_t mask; unsigned edge; };
  struct ShareRecord { std::size_t offset, mask; unsigned tiles, shared; };
  static constexpr std::size_t kHeader = 48, kTileRecord = 16, kShareRecord = 24;
  std::shared_ptr<const EffectCropIndex> crop_;
  EffectTileFile tiles_, shared_, pixels_, dictionary_;
  std::size_t tileBase_, sharedBase_;

  bool header(std::span<const std::byte> data, const char* magic, std::size_t logicalCount,
              const EffectCropIndex::Digest& hash) const {
    return std::memcmp(data.data(), magic, 8) == 0 &&
           number(data, 8, 4) == crop_->count() && number(data, 12, 4) == logicalCount &&
           std::memcmp(data.data()+16, hash.data(), hash.size()) == 0;
  }

  static std::uint64_t number(std::span<const std::byte> data, std::size_t offset, unsigned size) {
    std::uint64_t value = 0;
    for (unsigned i = 0; i < size; ++i)
      value |= std::uint64_t{std::to_integer<unsigned char>(data[offset+i])} << (8*i);
    return value;
  }

  TileRecord tile_record(std::size_t pos) const {
    const auto data = tiles_.bytes();
    if (pos == crop_->count()) return {data.size()-tileBase_, 0};
    const auto offset = kHeader + kTileRecord * pos;
    return {static_cast<std::size_t>(number(data, offset+8, 4)),
            static_cast<unsigned>(number(data, offset+12, 4))};
  }

  ShareRecord share_record(std::size_t pos) const {
    const auto data = shared_.bytes();
    if (pos == crop_->count()) return {pixels_.bytes().size(), data.size()-sharedBase_, 0, 0};
    const auto offset = kHeader + kShareRecord * pos;
    return {static_cast<std::size_t>(number(data, offset, 8)),
            static_cast<std::size_t>(number(data, offset+8, 8)),
            static_cast<unsigned>(number(data, offset+16, 4)),
            static_cast<unsigned>(number(data, offset+20, 4))};
  }

  bool valid_frame(std::size_t pos, const EffectCropIndex::Rectangle& rect) const {
    const auto tile = tile_record(pos), tileNext = tile_record(pos+1);
    const auto current = share_record(pos), next = share_record(pos+1);
    if (tile.mask > tileNext.mask || tileNext.mask > tiles_.bytes().size()-tileBase_ ||
        current.mask > next.mask || next.mask > shared_.bytes().size()-sharedBase_ ||
        current.offset > next.offset || next.offset > pixels_.bytes().size() ||
        current.shared > current.tiles) return false;
    const auto size = next.offset-current.offset;
    const auto dense = std::uint64_t{rect.w} * rect.h * 4;
    if (!tile.edge) return size == dense && !current.tiles &&
                           current.mask == next.mask && tile.mask == tileNext.mask;
    const auto edge = tile.edge;
    if (edge < 4 || edge > 64 || (edge & (edge-1)) || !rect.w || !size || size%4 ||
        size > dense || size < std::uint64_t{current.tiles}*4) return false;
    const auto cells = ((rect.w+edge-1)/edge) * ((rect.h+edge-1)/edge);
    const auto flagBytes = current.shared ? (std::uint64_t{current.tiles}+7)/8 : 0;
    return current.tiles <= cells && tileNext.mask-tile.mask == (cells+7)/8 &&
           next.mask-current.mask == flagBytes;
  }

  static bool bit(std::span<const std::byte> mask, unsigned i) {
    return (std::to_integer<unsigned char>(mask[i/8]) >> (i%8)) & 1;
  }

  static bool padding_zero(std::span<const std::byte> mask, unsigned count) {
    return count%8 == 0 || !(std::to_integer<unsigned char>(mask.back()) >> (count%8));
  }
};

}  // namespace iee::core
