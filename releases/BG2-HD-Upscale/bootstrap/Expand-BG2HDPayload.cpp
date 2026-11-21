#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <zlib.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
namespace fs = std::filesystem;
using Bytes = std::vector<unsigned char>;
using Data = std::span<const unsigned char>;
constexpr std::size_t kMaxAssetBytes = 128u << 20;

void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}

std::string hash(Data data) {
    std::array<unsigned char, 32> digest{};
    BCRYPT_ALG_HANDLE alg{};
    require(BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) >= 0,
            "cannot open SHA256");
    const auto status = BCryptHash(alg, nullptr, 0, const_cast<PUCHAR>(data.data()),
                                  static_cast<ULONG>(data.size()), digest.data(), digest.size());
    BCryptCloseAlgorithmProvider(alg, 0);
    require(status >= 0, "cannot hash payload");
    constexpr char digits[] = "0123456789ABCDEF";
    std::string result;
    for (auto v : digest) { result += digits[v >> 4]; result += digits[v & 15]; }
    return result;
}

fs::path payload_path(const std::string& value) {
    const fs::path path(value);
    require(value.starts_with("bg2hd/payload/") &&
            value.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/." ) ==
                std::string::npos, "invalid payload path");
    fs::path parent;
    for (const auto& part : path) {
        require(part != "." && part != ".." && !part.empty(), "invalid payload segment");
        parent /= part;
        const auto attributes = GetFileAttributesW(parent.c_str());
        require(attributes == INVALID_FILE_ATTRIBUTES || !(attributes & FILE_ATTRIBUTE_REPARSE_POINT),
                "reparse point in payload path");
    }
    return path;
}

Bytes read(const fs::path& path) {
    const auto n = fs::file_size(path);
    require(n && n <= kMaxAssetBytes, "invalid packed asset size");
    Bytes data(static_cast<std::size_t>(n));
    std::ifstream input(path, std::ios::binary);
    require(static_cast<bool>(input.read(reinterpret_cast<char*>(data.data()), data.size())),
            "truncated packed asset");
    return data;
}

std::uint32_t number(Data data, std::size_t offset, std::size_t count = 4) {
    require(offset <= data.size() && count <= data.size()-offset && count <= 4, "truncated field");
    std::uint32_t result{};
    for (std::size_t i = 0; i < count; ++i) result |= std::uint32_t{data[offset+i]} << (8*i);
    return result;
}

void append(Bytes& result, Data data, std::size_t offset, std::size_t size) {
    require(offset <= data.size() && size <= data.size()-offset, "truncated asset section");
    result.insert(result.end(), data.begin()+offset, data.begin()+offset+size);
}

std::size_t palette_table(Data data, std::size_t position, Bytes& result) {
    const auto mode = number(data, position++, 1);
    if (mode == 255) {
        append(result, data, position, 512);
        return position+512;
    }
    std::array<unsigned, 256> slots{};
    unsigned n = 0;
    const auto add = [&](unsigned slot) {
        require(n < slots.size() && slot < 256 && (!n || slot > slots[n-1]),
                "invalid representative slot");
        slots[n++] = slot;
    };
    if (mode == 254) {
        for (unsigned i = 0; i < 32; ++i) {
            const auto flags = number(data, position++, 1);
            for (unsigned bit = 0; bit < 8; ++bit) if ((flags >> bit) & 1) add(8*i+bit);
        }
    } else if (mode == 253) {
        const auto runs = number(data, position++, 1);
        for (unsigned i = 0; i < runs; ++i) {
            const auto start = number(data, position++, 1);
            const auto count = number(data, position++, 1)+1;
            for (unsigned j = 0; j < count; ++j) add(start+j);
        }
    } else {
        for (unsigned i = 0; i < mode; ++i) add(number(data, position++, 1));
    }
    const auto base = result.size();
    result.resize(base+512, 255);
    for (unsigned i = 0; i < n; ++i) {
        const auto value = number(data, position, 2);
        require(value != 65535, "invalid representative value");
        const auto out = base+2*slots[i];
        result[out] = static_cast<unsigned char>(value);
        result[out+1] = static_cast<unsigned char>(value >> 8);
        position += 2;
    }
    return position;
}

Bytes sprite_registry(Data packed, std::size_t expected) {
    require(packed.size() >= 44 && std::equal(packed.begin(), packed.begin()+8, "IEEREP1\0") &&
            number(packed, 8) == expected, "invalid compact sprite header");
    const auto data = packed.subspan(12);
    const auto version = number(data, 8), resources = number(data, 16);
    require(std::equal(data.begin(), data.begin()+8, "IEECSXN\0") &&
            (version == 6 || version == 7 || version == 9) && number(data, 12) == 2 &&
            resources && resources <= 65536 && number(data, 20) == 65535, "invalid sprite registry");
    Bytes result;
    result.reserve(expected);
    std::size_t cursor = 32, previous = 0;
    for (unsigned r = 0; r < resources; ++r) {
        const auto frames = number(data, cursor+40), cycles = number(data, cursor+44);
        cursor += 48 + ((version == 7 || version == 9) ? 2052u : 0u);
        for (unsigned i = 0; i < frames; ++i) {
            const auto indexBytes = number(data, cursor+12);
            const auto start = cursor+16;
            require(result.size() <= expected && start >= previous &&
                    expected-result.size() >= 512 && start-previous <= expected-result.size()-512,
                    "sprite output exceeds expected size");
            append(result, data, previous, start-previous);
            cursor = previous = palette_table(data, start, result);
            std::size_t stored = std::size_t{indexBytes}+number(data, cursor+32);
            cursor += 40;
            if (version == 9) {
                stored += number(data, cursor);
                stored += number(data, cursor+8);
                cursor += 16;
            }
            cursor += stored;
        }
        for (unsigned i = 0; i < cycles; ++i) cursor += 4+std::size_t{number(data, cursor)}*4;
    }
    require(cursor == data.size() && previous <= cursor, "sprite size differs");
    append(result, data, previous, cursor-previous);
    require(result.size() == expected, "restored sprite size differs");
    return result;
}

Bytes hex(const std::string& text) {
    require(text.size()%2 == 0 && text.find_first_not_of("0123456789abcdefABCDEF") == std::string::npos,
            "invalid PVR header hex");
    Bytes result;
    for (std::size_t i=0; i<text.size(); i+=2)
        result.push_back(static_cast<unsigned char>(std::stoul(text.substr(i, 2), nullptr, 16)));
    return result;
}

Bytes inflate_plane(Data compressed, std::size_t size) {
    Bytes result(size);
    unsigned long length = static_cast<unsigned long>(size);
    require(uncompress(result.data(), &length, compressed.data(), static_cast<unsigned long>(compressed.size())) ==
            Z_OK && length == size, "invalid compressed PVR plane");
    return result;
}

Bytes pvrz(const fs::path& rgb, const fs::path& alpha, const std::string& header) {
    auto pvr = hex(header);
    require(pvr.size() >= 52 && number(pvr, 0) == 0x03525650 && number(pvr, 8) == 11 &&
            pvr.size() == 52 + std::size_t{number(pvr, 48)}, "invalid BC3 header");
    const auto height = number(pvr, 24), width = number(pvr, 28);
    require(width && height && width <= 4096 && height <= 4096 && !(width%4) && !(height%4),
            "invalid BC3 dimensions");
    const auto plane = std::size_t{width}*height/2;
    const auto color = inflate_plane(read(rgb), plane), opacity = inflate_plane(read(alpha), plane);
    const auto start = pvr.size();
    pvr.resize(start + 2*plane);
    for (std::size_t i = 0; i < plane; i += 8) {
        std::copy_n(opacity.begin()+i, 8, pvr.begin()+start+2*i);
        std::copy_n(color.begin()+i, 8, pvr.begin()+start+2*i+8);
    }
    unsigned long size = compressBound(static_cast<unsigned long>(pvr.size()));
    Bytes out(size+4);
    for (unsigned i=0; i<4; ++i) out[i] = static_cast<unsigned char>(pvr.size() >> (8*i));
    require(compress2(out.data()+4, &size, pvr.data(), static_cast<unsigned long>(pvr.size()), 6) == Z_OK,
            "cannot reconstruct PVRZ");
    out.resize(size+4);
    return out;
}

void publish(const fs::path& target, Data bytes) {
    const auto temp = fs::path(target.wstring()+L"."+std::to_wstring(GetCurrentProcessId())+L".partial");
    const auto file = CreateFileW(temp.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
    require(file != INVALID_HANDLE_VALUE, "cannot stage payload file");
    DWORD written{};
    const bool success = WriteFile(file, bytes.data(), static_cast<DWORD>(bytes.size()), &written, nullptr)
                         && written == bytes.size();
    CloseHandle(file);
    if (!success || !MoveFileW(temp.c_str(), target.c_str())) {
        DeleteFileW(temp.c_str());
        throw std::runtime_error("cannot activate expanded payload file");
    }
}
}  // namespace

int wmain(int argc, wchar_t** argv) {
    try {
        require(argc == 2, "usage: Expand-BG2HDPayload <component-id>");
        const std::wstring component = argv[1];
        require(!component.empty() && component.size() <= 5 && component.find_first_not_of(L"0123456789") ==
                std::wstring::npos, "invalid component id");
        std::ifstream manifest(fs::path(L"bg2hd/transport") / (component + L".tsv"));
        require(static_cast<bool>(manifest), "missing transport manifest");
        std::size_t count = 0;
        for (std::string line; std::getline(manifest, line);) {
            std::istringstream row(line);
            char kind{};
            std::string name, digest, rgb, alpha, header;
            std::size_t size{};
            require(static_cast<bool>(row >> kind >> name >> size >> digest) &&
                    (kind == 'S' || kind == 'P') && size && size <= kMaxAssetBytes &&
                    digest.size() == 64, "invalid transport manifest row");
            const auto target = payload_path(name);
            if (kind == 'P') require(static_cast<bool>(row >> rgb >> alpha >> header), "missing PVR planes");
            row >> std::ws;
            require(row.eof(), "trailing transport fields");
            require(target.extension() == (kind == 'S' ? ".registry" : ".PVRZ"), "invalid restored extension");
            if (fs::exists(target)) {
                const auto existing = read(target);
                require(existing.size() == size && hash(existing) == digest, "existing payload differs");
            } else {
                const auto data = kind == 'S'
                    ? sprite_registry(read(payload_path(name+".compact")), size)
                    : pvrz(payload_path(rgb), payload_path(alpha), header);
                require(data.size() == size && hash(data) == digest, "restored payload hash differs");
                fs::create_directories(target.parent_path());
                publish(target, data);
            }
            ++count;
        }
        require(manifest.eof() && count, "cannot read transport manifest");
        std::cout << "BG2HD payload verified: " << count << " files\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BG2HD payload: " << error.what() << '\n';
        return 1;
    }
}
