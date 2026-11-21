#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <future>
#include <iostream>
#include <limits>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace {
namespace fs = std::filesystem;
using Byte = std::uint8_t;
constexpr std::size_t kBuckets = 128;
constexpr std::size_t kTileBytes = 64 * 64 * 4;
constexpr char kIndex[] = "EffectSharedTiles-X4.index";
constexpr char kStream[] = "EffectSharedTiles-X4.bin";
constexpr char kDictionary[] = "EffectSharedTiles-X4.dictionary.rgba";
static_assert(std::endian::native == std::endian::little);

void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
void read(std::istream& source, void* data, std::size_t size) {
    require(static_cast<bool>(source.read(static_cast<char*>(data), size)), "short input");
}
void write(std::ostream& out, const void* data, std::size_t size) {
    require(static_cast<bool>(out.write(static_cast<const char*>(data), size)), "short output");
}

std::vector<Byte> file(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    require(static_cast<bool>(input), "missing input");
    std::vector<Byte> data(static_cast<std::size_t>(fs::file_size(path)));
    if (!data.empty()) read(input, data.data(), data.size());
    return data;
}

struct Tile { unsigned x, y, w, h; };
struct Frame {
    unsigned width, height, x, y, w, h, edge;
    std::size_t maskStart, maskBytes;
    std::vector<std::string> files;
};
struct Inputs {
    std::vector<Frame> frames;
    std::vector<Byte> bitmaps;
    std::array<Byte, 32> tileHash{};
    std::uint32_t logicalCount{};
};

bool valid_source_name(const std::string& name, bool area) {
    const auto allowed = area ? "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_./"
                              : "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.";
    if (!name.ends_with(".rgba") || name.find_first_not_of(allowed) != std::string::npos)
        return false;
    if (!area) return name.starts_with("EFX4-");
    const fs::path path(name);
    return name.starts_with("animations/") && path.filename().string().starts_with("AAX4-") &&
        std::none_of(path.begin(), path.end(), [](const fs::path& part) { return part == "." || part == ".."; });
}

Inputs load(const fs::path& work, const fs::path& tileIndex, bool area) {
    Inputs inputs;
    std::ifstream table(work / "plan.txt");
    require(static_cast<bool>(table), "missing source plan");
    std::string line;
    std::getline(table, line);
    require(line.size() == 64, "invalid tile index hash");
    for (std::size_t i = 0; i < inputs.tileHash.size(); ++i)
        inputs.tileHash[i] = static_cast<Byte>(std::stoul(line.substr(2*i, 2), nullptr, 16));
    inputs.bitmaps = file(tileIndex);
    while (std::getline(table, line)) {
        std::istringstream row(line);
        Frame frame{};
        require(static_cast<bool>(row >> frame.width >> frame.height >> frame.x >> frame.y >>
            frame.w >> frame.h >> frame.edge >> frame.maskStart >> frame.maskBytes), "invalid frame plan");
        require(frame.x + frame.w <= frame.width && frame.y + frame.h <= frame.height &&
                frame.maskStart + frame.maskBytes <= inputs.bitmaps.size(), "frame plan out of bounds");
        const auto edge = frame.edge;
        require((!edge && !frame.maskBytes) || (edge >= 4 && edge <= 64 && !(edge & (edge-1)) &&
            frame.maskBytes == (((frame.w + edge-1)/edge) * ((frame.h + edge-1)/edge) + 7)/8), "invalid tile grid");
        for (std::string name; row >> name;) {
            require(valid_source_name(name, area), "invalid original name");
            frame.files.push_back(std::move(name));
        }
        require(!frame.files.empty(), "missing frame reference");
        inputs.logicalCount += static_cast<std::uint32_t>(frame.files.size());
        inputs.frames.push_back(std::move(frame));
    }
    require(!inputs.frames.empty(), "empty plan");
    return inputs;
}

bool bit(std::span<const Byte> mask, std::size_t i) { return (mask[i/8] >> (i%8)) & 1; }
void set_bit(std::span<Byte> mask, std::size_t i) { mask[i/8] |= static_cast<Byte>(1u << (i%8)); }

template<class Visit>
void for_tiles(const Frame& frame, std::span<const Byte> bitmaps, Visit visit) {
    if (!frame.edge) return;
    const auto edge = frame.edge;
    const auto mask = bitmaps.subspan(frame.maskStart, frame.maskBytes);
    std::size_t i = 0;
    for (unsigned y = 0; y < frame.h; y += edge) {
        for (unsigned x = 0; x < frame.w; x += edge, ++i) {
            if (bit(mask, i)) visit(Tile{frame.x+x, frame.y+y, std::min(edge, frame.w-x), std::min(edge, frame.h-y)});
        }
    }
}

void gather(const Frame& frame, std::span<const Byte> canvas, Tile tile, Byte* data) {
    const auto rowBytes = std::size_t{tile.w} * 4;
    for (unsigned y = 0; y < tile.h; ++y) {
        const auto start = (std::size_t{tile.y+y} * frame.width + tile.x) * 4;
        std::memcpy(data + y*rowBytes, canvas.data() + start, rowBytes);
    }
}

void scatter(const Frame& frame, Tile tile, const Byte* data, std::span<Byte> canvas) {
    const auto rowBytes = std::size_t{tile.w} * 4;
    for (unsigned y = 0; y < tile.h; ++y) {
        const auto start = (std::size_t{tile.y+y} * frame.width + tile.x) * 4;
        std::memcpy(canvas.data() + start, data + y*rowBytes, rowBytes);
    }
}

std::vector<Byte> original_frame(const fs::path& original, const Frame& frame) {
    auto canvas = file(original / frame.files.front());
    require(canvas.size() == std::size_t{frame.width} * frame.height * 4, "incorrect original canvas size");
    return canvas;
}

std::uint64_t mix(std::uint64_t x) {
    x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ull;
    x ^= x >> 27; x *= 0x94d049bb133111ebull;
    return x ^ (x >> 31);
}

std::uint64_t hash_tile(const Byte* data, unsigned w, unsigned h) {
    std::uint64_t hash = (w << 8) | h;
    const auto bytes = w*h*4;
    unsigned i = 0;
    for (; i+8 <= bytes; i+=8) {
        std::uint64_t word;
        std::memcpy(&word, data+i, 8);
        hash = std::rotl(hash ^ word, 23) * 0x9e3779b185ebca87ull;
    }
    if (i != bytes) {
        std::uint32_t word;
        std::memcpy(&word, data+i, 4);
        hash ^= word;
    }
    return mix(hash);
}

struct SpoolRecord { std::uint32_t id; std::uint8_t w, h; std::uint16_t reserved; };
static_assert(sizeof(SpoolRecord) == 8);

fs::path bucket_path(const fs::path& work, std::size_t i) { return work / (std::to_string(i) + ".bucket"); }

std::uint32_t spool(const Inputs& inputs, const fs::path& original, const fs::path& work) {
    constexpr auto bufferSize = 1u << 20;
    std::vector<Byte> buffers(kBuckets * bufferSize);
    std::array<std::ofstream, kBuckets> buckets;
    std::array<std::size_t, kBuckets> buffered{};
    for (std::size_t i = 0; i < kBuckets; ++i) {
        buckets[i].open(bucket_path(work, i), std::ios::binary);
        require(static_cast<bool>(buckets[i]), "cannot open spool partition");
    }
    const auto flush = [&](std::size_t bucket) {
        if (buffered[bucket]) write(buckets[bucket], buffers.data()+bucket*bufferSize, buffered[bucket]);
        buffered[bucket] = 0;
    };
    std::uint32_t id = 0;
    std::size_t count = 0;
    std::array<Byte, kTileBytes> tileData{};
    for (const auto& frame: inputs.frames) {
        if (frame.edge) {
            const auto canvas = original_frame(original, frame);
            for_tiles(frame, inputs.bitmaps, [&](Tile tile) {
                require(id != std::numeric_limits<std::uint32_t>::max(), "too many tile occurrences");
                const SpoolRecord record{id++, static_cast<Byte>(tile.w), static_cast<Byte>(tile.h), 0};
                const auto bytes = tile.w*tile.h*4;
                gather(frame, canvas, tile, tileData.data());
                require(std::any_of(tileData.begin(), tileData.begin()+bytes, [](Byte byte) { return byte != 0; }),
                        "occupied tile was zero in the original file");
                if (bytes == 4) return;  // A reference would cost as many bytes as the tile.
                const auto bucket = hash_tile(tileData.data(), tile.w, tile.h) % kBuckets;
                if (buffered[bucket] + sizeof(record) + bytes > bufferSize) flush(bucket);
                auto* out = buffers.data() + bucket*bufferSize + buffered[bucket];
                std::memcpy(out, &record, sizeof(record));
                std::memcpy(out+sizeof(record), tileData.data(), bytes);
                buffered[bucket] += sizeof(record) + bytes;
            });
        }
        if (++count % 1024 == 0) std::cout << "Read original frames: " << count << '\n' << std::flush;
    }
    for (std::size_t i = 0; i < kBuckets; ++i) {
        flush(i);
        buckets[i].close();
        require(!buckets[i].fail(), "could not flush spool");
    }
    return id;
}

struct OriginalTile {
    const Byte* data;
    std::uint64_t hash;
    unsigned w, h;
    bool operator==(const OriginalTile& other) const {
        return w == other.w && h == other.h && std::memcmp(data, other.data, w*h*4) == 0;
    }
};
struct TileHash { std::size_t operator()(const OriginalTile& tile) const { return tile.hash; } };
constexpr auto kNoOccurrence = std::numeric_limits<std::uint32_t>::max();
struct Occurrence { std::uint32_t first, second{kNoOccurrence}, position{}; };
struct SharingStats { std::uint64_t groups{}, references{}, originalBytes{}; };
struct BucketResult {
    std::vector<Byte> dictionary;
    std::vector<std::pair<std::uint32_t, std::uint32_t>> assignments;
    std::uint64_t groups{}, originalBytes{};
};

BucketResult compare_bucket(const fs::path& path, std::size_t count) {
    const auto data = file(path);
    std::unordered_map<OriginalTile, Occurrence, TileHash> equal;
    equal.reserve(data.size() / (64 + sizeof(SpoolRecord)));
    BucketResult out;
    for (std::size_t pos = 0; pos < data.size();) {
        SpoolRecord record{};
        require(data.size() - pos >= sizeof(record), "truncated spool record");
        std::memcpy(&record, data.data()+pos, sizeof(record));
        pos += sizeof(record);
        const auto size = unsigned{record.w} * record.h * 4;
        require(size <= data.size()-pos && size >= 8 && record.id < count, "invalid spool record");
        const auto* tile = data.data()+pos;
        pos += size;
        const auto hash = hash_tile(tile, record.w, record.h);
        auto [entry, first] = equal.try_emplace({tile, hash, record.w, record.h}, Occurrence{record.id});
        if (first) continue;
        auto& occurrence = entry->second;
        if (!occurrence.position) {
            if (size == 8 && occurrence.second == kNoOccurrence) {
                occurrence.second = record.id;
                continue;
            }
            require(out.dictionary.size()/4 < kNoOccurrence, "dictionary offset exceeds format");
            occurrence.position = static_cast<std::uint32_t>(out.dictionary.size()/4 + 1);
            out.dictionary.insert(out.dictionary.end(), entry->first.data, entry->first.data+size);
            ++out.groups;
            out.assignments.emplace_back(occurrence.first, occurrence.position);
            out.originalBytes += size;
            if (occurrence.second != kNoOccurrence) {
                out.assignments.emplace_back(occurrence.second, occurrence.position);
                out.originalBytes += size;
            }
        }
        out.assignments.emplace_back(record.id, occurrence.position);
        out.originalBytes += size;
    }
    return out;
}

SharingStats share(const fs::path& work, const fs::path& output, std::span<std::uint32_t> references) {
    std::ofstream dictionary(output / kDictionary, std::ios::binary);
    require(static_cast<bool>(dictionary), "cannot write dictionary");
    SharingStats stats;
    std::uint64_t base = 0;
    constexpr std::size_t parallel = 6;
    for (std::size_t start = 0; start < kBuckets; start += parallel) {
        std::vector<std::future<BucketResult>> pending;
        for (std::size_t i = start; i < std::min(start+parallel, kBuckets); ++i) {
            pending.push_back(std::async(std::launch::async, compare_bucket, bucket_path(work, i), references.size()));
        }
        for (std::size_t i = 0; i < pending.size(); ++i) {
            auto bucket = pending[i].get();
            require(base + bucket.dictionary.size()/4 <= kNoOccurrence, "dictionary offset exceeds format");
            if (!bucket.dictionary.empty()) write(dictionary, bucket.dictionary.data(), bucket.dictionary.size());
            for (const auto& [id, position]: bucket.assignments) references[id] = static_cast<std::uint32_t>(base+position);
            base += bucket.dictionary.size()/4;
            stats.groups += bucket.groups;
            stats.references += bucket.assignments.size();
            stats.originalBytes += bucket.originalBytes;
            fs::remove(bucket_path(work, start+i));
            if ((start+i+1) % 16 == 0)
                std::cout << "Compared original tile partitions: " << start+i+1 << '/' << kBuckets << '\n' << std::flush;
        }
    }
    dictionary.close();
    require(!dictionary.fail(), "could not flush dictionary");
    return stats;
}

struct IndexHeader { char magic[8]; std::uint32_t physical, logical; std::array<Byte, 32> tileHash; };
struct IndexRecord { std::uint64_t offset, flags; std::uint32_t tiles, shared; };
static_assert(sizeof(IndexHeader) == 48 && sizeof(IndexRecord) == 24);

void emit(const Inputs& inputs, const fs::path& original, const fs::path& output,
          std::span<const std::uint32_t> references) {
    std::ofstream pixelStream(output / kStream, std::ios::binary);
    require(static_cast<bool>(pixelStream), "cannot write shared tile stream");
    std::vector<IndexRecord> records;
    std::vector<Byte> allFlags, payload, flags;
    std::array<Byte, kTileBytes> tileData{};
    std::size_t id = 0;
    std::uint64_t offset = 0;
    for (const auto& frame: inputs.frames) {
        IndexRecord record{offset, allFlags.size(), 0, 0};
        payload.clear(); flags.clear();
        if (frame.w) {
            const auto canvas = original_frame(original, frame);
            if (!frame.edge) {
                for (unsigned y = 0; y < frame.h; ++y) {
                    const auto begin = (std::size_t{frame.y+y} * frame.width + frame.x) * 4;
                    payload.insert(payload.end(), canvas.begin()+begin, canvas.begin()+begin+frame.w*4);
                }
            } else {
                for_tiles(frame, inputs.bitmaps, [&](Tile tile) {
                    require(id < references.size(), "tile assignment missing");
                    const auto address = references[id++];
                    const auto i = record.tiles++;
                    if (i%8 == 0) flags.push_back(0);
                    if (address) {
                        set_bit(flags, i);
                        const auto* bytes = reinterpret_cast<const Byte*>(&address);
                        payload.insert(payload.end(), bytes, bytes+sizeof(address));
                        ++record.shared;
                    } else {
                        gather(frame, canvas, tile, tileData.data());
                        payload.insert(payload.end(), tileData.begin(), tileData.begin()+tile.w*tile.h*4);
                    }
                });
            }
        }
        if (record.shared) allFlags.insert(allFlags.end(), flags.begin(), flags.end());
        if (!payload.empty()) write(pixelStream, payload.data(), payload.size());
        offset += payload.size();
        records.push_back(record);
        if (records.size() % 1024 == 0) std::cout << "Packed frames: " << records.size() << '\n' << std::flush;
    }
    require(id == references.size(), "unexpected tile assignments");
    pixelStream.close();
    require(!pixelStream.fail(), "could not flush pixel stream");
    const IndexHeader header{{'I','E','E','T','S','H','R','1'}, static_cast<std::uint32_t>(records.size()),
        inputs.logicalCount, inputs.tileHash};
    std::ofstream index(output / kIndex, std::ios::binary);
    write(index, &header, sizeof(header));
    write(index, records.data(), records.size()*sizeof(IndexRecord));
    if (!allFlags.empty()) write(index, allFlags.data(), allFlags.size());
    index.close();
    require(!index.fail(), "could not flush sharing index");
}

void verify(const Inputs& inputs, const fs::path& original, const fs::path& output) {
    const auto dictionary = file(output / kDictionary);
    const auto index = file(output / kIndex);
    const auto streamSize = fs::file_size(output / kStream);
    std::ifstream stream(output / kStream, std::ios::binary);
    require(static_cast<bool>(stream), "cannot open emitted stream");
    const auto maskBase = sizeof(IndexHeader) + inputs.frames.size()*sizeof(IndexRecord);
    require(index.size() >= maskBase, "truncated sharing index");
    IndexHeader header{};
    std::memcpy(&header, index.data(), sizeof(header));
    require(std::memcmp(header.magic, "IEETSHR1", 8) == 0 && header.physical == inputs.frames.size() &&
            header.logical == inputs.logicalCount && header.tileHash == inputs.tileHash, "sharing index binding differs");
    const auto record_at = [&](std::size_t frame) {
        IndexRecord record{streamSize, index.size()-maskBase, 0, 0};
        if (frame < inputs.frames.size())
            std::memcpy(&record, index.data() + sizeof(IndexHeader) + frame*sizeof(record), sizeof(record));
        return record;
    };
    const auto first = record_at(0);
    require(!first.offset && !first.flags, "invalid initial sharing record");
    std::vector<Byte> payload, canvas;
    std::uint32_t verified = 0;
    for (std::size_t i = 0; i < inputs.frames.size(); ++i) {
        const auto& frame = inputs.frames[i];
        const auto record = record_at(i), next = record_at(i+1);
        const auto flagsSize = record.shared ? (std::uint64_t{record.tiles}+7)/8 : 0;
        require(record.offset <= next.offset && next.offset <= streamSize && record.flags <= next.flags &&
            next.flags <= index.size()-maskBase && next.flags-record.flags == flagsSize && record.shared <= record.tiles &&
            next.offset-record.offset <= std::uint64_t{frame.w}*frame.h*4, "invalid sharing frame bounds");
        const auto flags = std::span(index).subspan(maskBase + record.flags, flagsSize);
        if (flagsSize && record.tiles%8) require((flags.back() >> (record.tiles%8)) == 0, "nonzero flag padding");
        payload.resize(static_cast<std::size_t>(next.offset-record.offset));
        if (!payload.empty()) read(stream, payload.data(), payload.size());
        canvas.assign(std::size_t{frame.width}*frame.height*4, 0);
        std::size_t position = 0, seen = 0, shared = 0;
        if (frame.edge) {
            for_tiles(frame, inputs.bitmaps, [&](Tile tile) {
                const auto bytes = tile.w*tile.h*4;
                require(seen < record.tiles, "too many tiles in reconstruction");
                const bool reuse = record.shared && bit(flags, seen);
                ++seen;
                const auto consumed = reuse ? sizeof(std::uint32_t) : bytes;
                require(consumed <= payload.size()-position, "truncated tile payload");
                const Byte* pixels = payload.data()+position;
                if (reuse) {
                    std::uint32_t address;
                    std::memcpy(&address, pixels, sizeof(address));
                    require(address != 0, "invalid dictionary reference");
                    const auto start = (std::uint64_t{address}-1)*4;
                    require(start <= dictionary.size() && bytes <= dictionary.size()-start, "dictionary reference out of bounds");
                    pixels = dictionary.data()+start;
                    ++shared;
                }
                scatter(frame, tile, pixels, canvas);
                position += consumed;
            });
        } else {
            require(payload.size() == std::size_t{frame.w}*frame.h*4, "wrong dense frame size");
            if (!payload.empty()) scatter(frame, {frame.x, frame.y, frame.w, frame.h}, payload.data(), canvas);
            position = payload.size();
        }
        require(position == payload.size() && seen == record.tiles && shared == record.shared, "incomplete frame reconstruction");
        for (const auto& name: frame.files) {
            if (canvas != file(original / name)) throw std::runtime_error("byte mismatch against original " + name);
            ++verified;
        }
        if ((i+1) % 1024 == 0) std::cout << "Original frame files checked: " << verified << '\n' << std::flush;
    }
    require(verified == header.logical, "incomplete original comparison");
    std::cout << "Byte-exact originals: " << verified << '\n';
}
} // namespace

int wmain(int argc, wchar_t** argv) {
    try {
        const bool area = argc == 8 && std::wstring_view(argv[7]) == L"--area";
        require(argc == 7 || area,
                "usage: effect_tile_sharing build|verify ORIGINAL TILED WORK OUTPUT COUNTS [--area]");
        const fs::path original(argv[2]), tiled(argv[3]), work(argv[4]), output(argv[5]);
        const auto inputs = load(work, area ? tiled : tiled / "EffectTiles-X4.index", area);
        if (std::wstring_view(argv[1]) == L"build") {
            const auto tiles = spool(inputs, original, work);
            std::vector<std::uint32_t> references(tiles);
            const auto stats = share(work, output, references);
            emit(inputs, original, output, references);
            std::ofstream counts{fs::path(argv[6])};
            counts << tiles << ' ' << stats.groups << ' ' << stats.references << ' ' << stats.originalBytes << '\n';
            counts.close();
            require(!counts.fail(), "could not write counts");
        } else require(std::wstring_view(argv[1]) == L"verify", "unknown action");
        verify(inputs, original, output);
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
