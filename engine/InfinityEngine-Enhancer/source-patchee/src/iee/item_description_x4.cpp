#include "iee/item_description_x4.h"

#include <intrin.h>
#include <zlib.h>

#include <algorithm>
#include <array>
#include <fstream>
#include <string_view>
#include <utility>
#include <vector>

#include "iee/app_context.h"
#include "iee/core/hooking.h"
#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/opengl_types.h"
#include "iee/game/runtime_types_x64.h"
#include "iee/item_icon_x2.h"

namespace iee::item_description_x4 {
namespace {

using Resref = std::array<char, 8>;
using Rect = std::array<int, 4>;
using Point = std::array<int, 2>;
using DrawItemFn = bool (*)(const void*, const void*, const void*, int, const void*);
using RenderPvrFn = int (*)(game::CVidCell*, int, int, const Rect*, const Rect*, std::uint32_t, int);
using DrawQuadFn = void (*)(const Rect*, const Rect*, const Point*, const Rect*);

constexpr std::uintptr_t kDrawItem = 0x3D1210;
constexpr std::uintptr_t kLabelRenderCall = 0x3D1F62;
constexpr std::uintptr_t kRenderPvrCall = 0x424845;
constexpr std::uintptr_t kRenderPvr = 0x4250D0;
constexpr std::uintptr_t kDrawQuad = 0x415320;
constexpr std::uintptr_t kDrawEnable = 0x4132B0;
constexpr std::uintptr_t kDrawBlendFunc = 0x413160;
constexpr Rect kDescriptionLabel{66, 210, 280, 327};
constexpr std::size_t kCacheCapacity = 8;
constexpr int kScale = 4;
constexpr int kFilter = static_cast<int>(game::gl::LINEAR);

struct Frame {
  Resref resref{};
  std::uint16_t slot{}, width{}, height{};
  std::uint32_t compressedBytes{};
  std::uint64_t offset{};

  auto key() const noexcept { return std::pair{resref, slot}; }
};

struct Texture {
  std::size_t frame{};
  int id{};
};

struct FrameSize {
  std::uint16_t width{}, height{};
};

static_assert(offsetof(game::CVidCell, m_nCurrentFrame) == 0x118);
static_assert(offsetof(game::CVidCell, m_nCurrentSequence) == 0x11a);
static_assert(offsetof(game::CVidCell, m_pFrame) == 0x128);

std::vector<Frame> frames;
std::filesystem::path registryPath;
std::vector<Texture> textures;
HGLRC textureContext{};
item_icon_x2::EngineTextureApi textureApi{};
game::DrawApi draw{};
DrawQuadFn drawQuad{};
void (*drawEnable)(int){};
void (*drawBlendFunc)(int, int){};
core::Hook<DrawItemFn> drawItemHook;
core::Hook<RenderPvrFn> renderPvrHook;
std::uintptr_t labelRenderReturn{}, renderPvrReturn{};
std::size_t resrefOffset{};
thread_local bool insideLabel{};
thread_local void* activeCell{};
unsigned uploadsLogged{};

template <typename T>
bool read(std::istream& source, T& out) {
  return bool(source.read(reinterpret_cast<char*>(&out), sizeof(out)));
}

bool matches(const core::ModuleSpan& module, std::uintptr_t rva, std::string_view signature) {
  std::vector<std::byte> bytes;
  std::vector<bool> mask;
  if (!core::parse_ida_pattern(signature, bytes, mask) || rva > module.size ||
      bytes.size() > module.size - rva)
    return false;
  return core::find_pattern({module.base + rva, bytes.size()}, bytes, mask) == module.base + rva;
}

bool detour_draw_item(const void* item, const void* origin, const void* clip,
                      int alpha, const void* state) {
  const bool previous = insideLabel;
  Rect area{};
  insideLabel = item && core::safe_read(static_cast<const std::byte*>(item) + 0x40, area) &&
      area == kDescriptionLabel;
  const bool drawn = drawItemHook.original()(item, origin, clip, alpha, state);
  insideLabel = previous;
  return drawn;
}

int get_texture(const Frame& frame, int previous) {
  const auto context = game::gl::current_context();
  if (!context || textureApi.DrawGetRenderer() == 1) return 0;
  if (textureContext != context) {
    forget_textures();
    textureContext = context;
  }
  const auto index = static_cast<std::size_t>(&frame - frames.data());
  const auto cached = std::find_if(textures.begin(), textures.end(),
      [index](const Texture& texture) { return texture.frame == index; });
  if (cached != textures.end()) {
    std::rotate(cached, cached + 1, textures.end());
    return textures.back().id;
  }

  std::ifstream input(registryPath, std::ios::binary);
  std::vector<std::uint8_t> compressed(frame.compressedBytes);
  if (!input.seekg(static_cast<std::streamoff>(frame.offset)) ||
      !input.read(reinterpret_cast<char*>(compressed.data()), frame.compressedBytes))
    return 0;
  const int width = frame.width * kScale;
  const int height = frame.height * kScale;
  std::vector<std::uint8_t> rgba(static_cast<std::size_t>(width) * height * 4);
  auto size = static_cast<uLongf>(rgba.size());
  if (uncompress(rgba.data(), &size, compressed.data(), frame.compressedBytes) != Z_OK ||
      size != rgba.size())
    return 0;

  if (textures.size() == kCacheCapacity) {
    textureApi.DrawDeleteTexture(textures.front().id);
    textures.erase(textures.begin());
  }
  const int id = textureApi.DrawGenTexture(kFilter, 0, 0, 0);
  if (id <= 0) return 0;
  if (!item_icon_x2::upload_rgba_texture(id, frame.width, frame.height,
                                        width, height, rgba.data(), textureApi, previous)) {
    textureApi.DrawDeleteTexture(id);
    return 0;
  }
  textures.push_back({index, id});
  if (uploadsLogged < 24) {
    ++uploadsLogged;
    const auto end = std::find(frame.resref.begin(), frame.resref.end(), '\0');
    LOG_INFO("Item description x4 uploaded: {} frame {} ({}x{} -> {}x{})",
             std::string_view(frame.resref.data(), end - frame.resref.begin()),
             frame.slot, frame.width, frame.height, width, height);
  }
  return id;
}

bool render_description(game::CVidCell* cell, int left, int top, const Rect* clip,
                        const Rect* render, std::uint32_t flags, int alpha) {
  if (!clip || cell->m_nCurrentSequence != 0 || cell->m_nCurrentFrame < 0) return false;
  Resref resref{};
  FrameSize size{};
  std::uint32_t state{}, tint{};
  const auto* bytes = reinterpret_cast<const std::byte*>(cell);
  if (!core::safe_read(bytes + resrefOffset, resref) ||
      !core::safe_read(cell->m_pFrame, size) ||
      !core::safe_read(textureApi.glTextureState, state) ||
      !core::safe_read(bytes + 0x38, tint))
    return false;

  const auto key = std::pair{resref, static_cast<std::uint16_t>(cell->m_nCurrentFrame)};
  const auto frame = std::lower_bound(frames.begin(), frames.end(), key,
      [](const Frame& entry, const auto& wanted) { return entry.key() < wanted; });
  if (frame == frames.end() || frame->key() != key ||
      frame->width != size.width || frame->height != size.height)
    return false;

  const bool scaled = (flags & 0x8000) != 0;
  int width = frame->width;
  int height = frame->height;
  Point scale{};
  if (scaled) {
    Rect bounds{};
    if (!core::safe_read(render, bounds)) return false;
    width = bounds[2] - bounds[0];
    height = bounds[3] - bounds[1];
    if (width <= 0 || height <= 0) return false;
    scale = {frame->width, frame->height};
  }
  const int previous = static_cast<int>((state >> 21u) & 0x1FFu);
  const int texture = get_texture(*frame, previous);
  if (!texture) return false;

  // Match CVidCell::RenderPVR's native state, destination and clipping.
  const Rect dest{left, top, left + width, top + height};
  const Rect source{0, 0, frame->width, frame->height};
  textureApi.DrawBindTexture(texture);
  drawEnable(0xBE2);
  drawBlendFunc(6, 7);
  draw.DrawColor((tint & 0xFFFFFFu) | (static_cast<std::uint32_t>(alpha) << 24));
  draw.DrawColorTone((flags & 0x80000) ? 1 : (flags & 0x2000000) ? 2 : 0);
  drawQuad(&dest, &source, &scale, clip);
  draw.DrawColorTone(0);
  textureApi.DrawBindTexture(previous);
  cell->m_pFrame = nullptr;
  return true;
}

int detour_render_pvr(game::CVidCell* cell, int left, int top, const Rect* clip,
                      const Rect* render, std::uint32_t flags, int alpha) {
  if (cell && cell == activeCell &&
      reinterpret_cast<std::uintptr_t>(_ReturnAddress()) == renderPvrReturn) {
    try {
      if (render_description(cell, left, top, clip, render, flags, alpha)) return 1;
    } catch (...) {
      // The native draw remains available if an image could not be loaded.
    }
  }
  return renderPvrHook.original()(cell, left, top, clip, render, flags, alpha);
}

}  // namespace

CellScope::CellScope(void* cell, std::uintptr_t caller) noexcept : previous_(activeCell) {
  activeCell = insideLabel && caller == labelRenderReturn ? cell : nullptr;
}

CellScope::~CellScope() { activeCell = previous_; }

bool prepare(const std::filesystem::path& directory) noexcept {
  frames.clear();
  try {
    const auto path = directory / "ItemDescriptions-X4.registry";
    std::ifstream source(path, std::ios::binary | std::ios::ate);
    if (!source || source.tellg() <= 0) return false;
    const auto fileSize = static_cast<std::uint64_t>(source.tellg());
    source.seekg(0);
    constexpr std::array<char, 8> magic{'I', 'E', 'E', 'I', 'D', 'X', '4', 0};
    std::array<char, 8> header{};
    std::uint32_t count{};
    if (!read(source, header) || header != magic || !read(source, count) || !count || count > 4096)
      return false;
    std::uint64_t offset = 12 + count * 26;
    std::vector<Frame> index;
    index.reserve(count);
    std::size_t assetCount = 0;
    for (std::uint32_t i = 0; i < count; ++i) {
      auto& entry = index.emplace_back();
      if (!read(source, entry.resref) || !read(source, entry.slot) || !read(source, entry.width) ||
          !read(source, entry.height) || !read(source, entry.compressedBytes) || !read(source, entry.offset) ||
          !entry.width || !entry.height || entry.width > 512 || entry.height > 512 ||
          !entry.compressedBytes || entry.offset != offset || offset > fileSize ||
          entry.compressedBytes > fileSize - offset || (i && index[i - 1].key() >= entry.key()))
        return false;
      offset += entry.compressedBytes;
      if (!i || entry.resref != index[i - 1].resref) ++assetCount;
    }
    if (offset != fileSize) return false;
    registryPath = path;
    textures.reserve(kCacheCapacity);
    LOG_INFO("Item description x4 registry loaded: {} illustrations, {} frames", assetCount, count);
    frames = std::move(index);
    return true;
  } catch (...) {
    return false;
  }
}

bool ready() noexcept { return !frames.empty(); }

void install(const AppContext& ctx) noexcept {
  if (!ready() || !ctx.cfg.enableItemDescriptionX4 || !ctx.manifest) return;
  try {
    const auto module = core::get_module_span(nullptr);
    if (!module || !ctx.draw.DrawBindTexture || !ctx.draw.DrawColor || !ctx.draw.DrawColorTone ||
        !matches(*module, kDrawItem, "40 55 53 57 41 55 41 57 48 8D AC 24 C0 FC FF FF") ||
        !matches(*module, kLabelRenderCall, "E8 19 28 05 00 41 83 3F 09 75 44") ||
        !matches(*module, kRenderPvrCall, "E8 86 08 00 00 85 C0 0F 85 61 02 00 00") ||
        !matches(*module, kRenderPvr, "4C 8B DC 55 41 55 41 57 49 8D 6B B9 48 81 EC 00 01 00 00") ||
        !matches(*module, kDrawQuad, "48 89 5C 24 10 48 89 6C 24 18 41 56 48 83 EC 40") ||
        !matches(*module, kDrawEnable, "83 3D F9 76 31 00 01 0F 84 E3 52 01 00") ||
        !matches(*module, kDrawBlendFunc, "83 3D 49 78 31 00 01 0F 84 B3 4C 01 00"))
      throw std::runtime_error("native draw signature mismatch");
    const auto base = reinterpret_cast<std::uintptr_t>(module->base);
    const auto& runtime = ctx.manifest->areaAnimations;
    textureApi = {
        reinterpret_cast<item_icon_x2::EngineTextureApi::DrawGenTextureFn>(base + runtime.drawGenTexture),
        ctx.draw.DrawBindTexture,
        reinterpret_cast<item_icon_x2::EngineTextureApi::DrawDeleteTextureFn>(base + runtime.drawDeleteTexture),
        reinterpret_cast<item_icon_x2::EngineTextureApi::TexImageFn>(base + runtime.texImage),
        reinterpret_cast<item_icon_x2::EngineTextureApi::DrawGetRendererFn>(base + runtime.drawGetRenderer),
        reinterpret_cast<const std::uint32_t*>(base + runtime.glTextureState)};
    draw = ctx.draw;
    drawQuad = reinterpret_cast<DrawQuadFn>(base + kDrawQuad);
    drawEnable = reinterpret_cast<decltype(drawEnable)>(base + kDrawEnable);
    drawBlendFunc = reinterpret_cast<decltype(drawBlendFunc)>(base + kDrawBlendFunc);
    resrefOffset = ctx.manifest->itemIcons.vidCellResref;
    labelRenderReturn = base + kLabelRenderCall + 5;
    renderPvrReturn = base + kRenderPvrCall + 5;
    renderPvrHook.create(reinterpret_cast<void*>(base + kRenderPvr),
                         reinterpret_cast<void*>(&detour_render_pvr));
    drawItemHook.create(reinterpret_cast<void*>(base + kDrawItem),
                        reinterpret_cast<void*>(&detour_draw_item));
    renderPvrHook.enable();
    drawItemHook.enable();
    LOG_INFO("Item description x4 hooks installed: ITEM_DESCRIPTION BAM label");
  } catch (const std::exception& error) {
    remove();
    LOG_WARN("Item description x4 path unavailable: {}", error.what());
  } catch (...) {
    remove();
  }
}

void disable() noexcept {
  (void)drawItemHook.disable();
  (void)renderPvrHook.disable();
}

void remove() noexcept {
  (void)drawItemHook.remove();
  (void)renderPvrHook.remove();
  forget_textures();
}

void forget_textures() noexcept {
  textures.clear();
  textureContext = nullptr;
}

}  // namespace iee::item_description_x4
