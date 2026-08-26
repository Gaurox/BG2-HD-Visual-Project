#include <algorithm>
#include <array>
#include <cmath>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <thread>
#include <utility>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#include <compressapi.h>
#endif

#include "iee/core/config.h"
#include "iee/core/area_animation_clock_probe.h"
#include "iee/core/area_animation_timeline.h"
#include "iee/area_animation_x4_registry.h"
#include "iee/creature_sprite_x2.h"
#include "iee/core/pattern_scanner.h"
#include "iee/core/performance_samples.h"
#include "iee/features/tile_render.h"
#include "iee/game/area_texture.h"
#include "iee/game/build_manifest.h"
#include "iee/game/dds_texture.h"
#include "iee/game/eeex_doc_layouts_x64.h"
#include "iee/game/file_formats.h"
#include "iee/game/runtime_types_x64.h"
#include "iee/game/shader_override.h"
#include "iee/game/tile_upscale.h"
#include "iee/game/tile_liquid.h"
#include "iee/game/tis_palette.h"
#include "iee/game/wed_runtime.h"


namespace {
int g_failures = 0;
std::uint32_t g_writableSectionProbe = 0x13579BDFu;
std::vector<int> g_creatureTextureLifecycle;

#ifdef _WIN32
std::array<std::byte, 32> test_sha256(const std::vector<std::byte>& bytes) {
  constexpr std::array<std::uint32_t, 64> constants{{
      0x428A2F98u, 0x71374491u, 0xB5C0FBCFu, 0xE9B5DBA5u, 0x3956C25Bu,
      0x59F111F1u, 0x923F82A4u, 0xAB1C5ED5u, 0xD807AA98u, 0x12835B01u,
      0x243185BEu, 0x550C7DC3u, 0x72BE5D74u, 0x80DEB1FEu, 0x9BDC06A7u,
      0xC19BF174u, 0xE49B69C1u, 0xEFBE4786u, 0x0FC19DC6u, 0x240CA1CCu,
      0x2DE92C6Fu, 0x4A7484AAu, 0x5CB0A9DCu, 0x76F988DAu, 0x983E5152u,
      0xA831C66Du, 0xB00327C8u, 0xBF597FC7u, 0xC6E00BF3u, 0xD5A79147u,
      0x06CA6351u, 0x14292967u, 0x27B70A85u, 0x2E1B2138u, 0x4D2C6DFCu,
      0x53380D13u, 0x650A7354u, 0x766A0ABBu, 0x81C2C92Eu, 0x92722C85u,
      0xA2BFE8A1u, 0xA81A664Bu, 0xC24B8B70u, 0xC76C51A3u, 0xD192E819u,
      0xD6990624u, 0xF40E3585u, 0x106AA070u, 0x19A4C116u, 0x1E376C08u,
      0x2748774Cu, 0x34B0BCB5u, 0x391C0CB3u, 0x4ED8AA4Au, 0x5B9CCA4Fu,
      0x682E6FF3u, 0x748F82EEu, 0x78A5636Fu, 0x84C87814u, 0x8CC70208u,
      0x90BEFFFAu, 0xA4506CEBu, 0xBEF9A3F7u, 0xC67178F2u,
  }};
  std::array<std::uint32_t, 8> state{{
      0x6A09E667u, 0xBB67AE85u, 0x3C6EF372u, 0xA54FF53Au,
      0x510E527Fu, 0x9B05688Cu, 0x1F83D9ABu, 0x5BE0CD19u,
  }};
  const auto rotateRight = [](std::uint32_t value, unsigned count) {
    return (value >> count) | (value << (32u - count));
  };
  const auto transform = [&](const std::uint8_t* block) {
    std::array<std::uint32_t, 64> words{};
    for (std::size_t index = 0; index < 16; ++index) {
      const auto offset = index * 4;
      words[index] = (static_cast<std::uint32_t>(block[offset]) << 24u) |
                     (static_cast<std::uint32_t>(block[offset + 1]) << 16u) |
                     (static_cast<std::uint32_t>(block[offset + 2]) << 8u) |
                     static_cast<std::uint32_t>(block[offset + 3]);
    }
    for (std::size_t index = 16; index < words.size(); ++index) {
      const auto s0 = rotateRight(words[index - 15], 7) ^
                      rotateRight(words[index - 15], 18) ^
                      (words[index - 15] >> 3u);
      const auto s1 = rotateRight(words[index - 2], 17) ^
                      rotateRight(words[index - 2], 19) ^
                      (words[index - 2] >> 10u);
      words[index] = words[index - 16] + s0 + words[index - 7] + s1;
    }
    auto a = state[0];
    auto b = state[1];
    auto c = state[2];
    auto d = state[3];
    auto e = state[4];
    auto f = state[5];
    auto g = state[6];
    auto h = state[7];
    for (std::size_t index = 0; index < words.size(); ++index) {
      const auto sum1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
      const auto temporary1 = h + sum1 + ((e & f) ^ (~e & g)) +
                              constants[index] + words[index];
      const auto temporary2 =
          (rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22)) +
          ((a & b) ^ (a & c) ^ (b & c));
      h = g;
      g = f;
      f = e;
      e = d + temporary1;
      d = c;
      c = b;
      b = a;
      a = temporary1 + temporary2;
    }
    for (std::size_t index = 0; index < state.size(); ++index) {
      state[index] += std::array<std::uint32_t, 8>{{a, b, c, d, e, f, g, h}}[index];
    }
  };
  const auto* data = reinterpret_cast<const std::uint8_t*>(bytes.data());
  std::size_t offset = 0;
  while (bytes.size() - offset >= 64) {
    transform(data + offset);
    offset += 64;
  }
  std::array<std::uint8_t, 128> tail{};
  const auto remaining = bytes.size() - offset;
  if (remaining != 0) std::memcpy(tail.data(), data + offset, remaining);
  tail[remaining] = 0x80u;
  const std::size_t tailBytes = remaining < 56 ? 64 : 128;
  const auto bitLength = static_cast<std::uint64_t>(bytes.size()) * 8u;
  for (unsigned index = 0; index < 8; ++index) {
    tail[tailBytes - 1 - index] =
        static_cast<std::uint8_t>(bitLength >> (index * 8u));
  }
  transform(tail.data());
  if (tailBytes == 128) transform(tail.data() + 64);
  std::array<std::byte, 32> digest{};
  for (std::size_t index = 0; index < state.size(); ++index) {
    for (unsigned byte = 0; byte < 4; ++byte) {
      digest[index * 4 + byte] =
          static_cast<std::byte>(state[index] >> (24u - byte * 8u));
    }
  }
  return digest;
}
#endif

void executable_section_probe() {}

void record_creature_texture_bind(int textureId) {
  g_creatureTextureLifecycle.push_back(textureId);
}

void record_creature_texture_delete(int textureId) {
  g_creatureTextureLifecycle.push_back(-textureId);
}

void expect_true(bool condition, std::string_view message) {
  if (!condition) {
    std::cerr << "FAIL: " << message << '\n';
    ++g_failures;
  }
}

template <typename T, typename U>
void expect_eq(const T& actual, const U& expected, std::string_view message) {
  if (!(actual == expected)) {
    std::cerr << "FAIL: " << message << " (actual=" << actual << ", expected=" << expected << ")\n";
    ++g_failures;
  }
}

void write_rel32_instruction(std::byte* instruction, std::uint8_t opcode,
                             std::size_t displacementOffset, std::size_t instructionSize,
                             const std::byte* target) {
  instruction[0] = static_cast<std::byte>(opcode);
  const auto displacement = static_cast<std::intptr_t>(target - (instruction + instructionSize));
  const auto rel32 = static_cast<std::int32_t>(displacement);
  std::memcpy(instruction + displacementOffset, &rel32, sizeof(rel32));
}

void test_parse_ida_pattern() {
  std::vector<std::byte> bytes;
  std::vector<bool> mask;
  expect_true(iee::core::parse_ida_pattern("48 8B ? ? 89 54 24 ??", bytes, mask),
              "IDA patterns should support wildcards");
  expect_eq(bytes.size(), std::size_t{8}, "Parsed pattern size should match token count");
  expect_true(
      mask[0] && mask[1] && !mask[2] && !mask[3] && mask[4] && mask[5] && mask[6] && !mask[7],
      "Pattern mask should mark wildcard positions");
}

void test_unique_pattern_matching() {
  const std::array<std::byte, 8> haystack{
      std::byte{0x48}, std::byte{0x8B}, std::byte{0x01}, std::byte{0x90},
      std::byte{0x48}, std::byte{0x8B}, std::byte{0x02}, std::byte{0x90},
  };
  const std::array<std::byte, 3> needle{
      std::byte{0x48},
      std::byte{0x8B},
      std::byte{0x00},
  };
  const std::vector<bool> wildcardMask{true, true, false};

  const auto ambiguous = iee::core::find_pattern_unique(haystack, needle, wildcardMask);
  expect_eq(ambiguous.count, std::size_t{2},
            "Ambiguous signatures should report two-or-more matches");
  expect_true(!ambiguous.unique(), "Ambiguous signatures must not be accepted as hook targets");

  const std::array<std::byte, 3> exactNeedle{
      std::byte{0x48},
      std::byte{0x8B},
      std::byte{0x01},
  };
  const std::vector<bool> exactMask{true, true, true};
  const auto unique = iee::core::find_pattern_unique(haystack, exactNeedle, exactMask);
  expect_eq(unique.count, std::size_t{1}, "A single signature occurrence should be reported once");
  expect_true(unique.unique() && unique.address == haystack.data(),
              "A unique signature should return its exact address");
}

void test_detour_tolerant_matching() {
  using iee::core::matches_past_prologue;

  // 21-byte RenderTexture signature; a 14-byte absolute-jump detour (FF 25 ...)
  // clobbered bytes 0..13, the rest is the original tail (see the 2.7.3 log).
  const std::array<std::uint8_t, 21> pattern{0x48, 0x8B, 0xC4, 0x44, 0x89, 0x48, 0x20,
                                             0x48, 0x83, 0xEC, 0x48, 0x48, 0x89, 0x58,
                                             0x08, 0x8B, 0xDA, 0x48, 0x89, 0x68, 0x10};
  std::array<std::uint8_t, 21> live = pattern;
  const std::array<std::uint8_t, 14> detour{0xFF, 0x25, 0x02, 0x00, 0x00, 0x00, 0x00,
                                            0x00, 0x70, 0xE7, 0x92, 0x42, 0xF9, 0x7F};
  std::copy(detour.begin(), detour.end(), live.begin());

  const auto toBytes = [](const auto& src) {
    std::vector<std::byte> out(src.size());
    for (std::size_t i = 0; i < src.size(); ++i) out[i] = std::byte{src[i]};
    return out;
  };
  const auto needle = toBytes(pattern);
  const auto haystack = toBytes(live);
  const std::vector<bool> mask(pattern.size(), true);

  expect_true(matches_past_prologue(haystack, needle, mask, 16, 4),
              "A detoured prologue with an intact tail should be accepted");

  // Corrupt a tail byte: the function is genuinely different -> reject.
  auto corrupted = haystack;
  corrupted[18] = std::byte{0xEE};
  expect_true(!matches_past_prologue(corrupted, needle, mask, 16, 4),
              "A mismatched tail byte must reject the candidate");

  // Too few verifiable tail bytes -> reject (cannot pass on prologue alone).
  expect_true(!matches_past_prologue(haystack, needle, mask, 16, 8),
              "Fewer verified tail bytes than required must reject");

  // A wholly different tail (e.g. wrong function at the RVA) -> reject.
  std::array<std::uint8_t, 21> other = live;
  for (std::size_t i = 16; i < other.size(); ++i) other[i] = 0x00;
  expect_true(!matches_past_prologue(toBytes(other), needle, mask, 16, 4),
              "An unrelated tail must reject the candidate");
}

void test_rel32_target_checked() {
  std::array<std::byte, 32> callBytes{};
  auto* callInstruction = callBytes.data() + 4;
  auto* callTarget = callBytes.data() + 24;
  write_rel32_instruction(callInstruction, 0xE8, 1, 5, callTarget);

  expect_true(iee::core::rel32_target_checked(callInstruction, 0xE8, 1, 5) == callTarget,
              "CALL rel32 decoding should return the target");
  expect_true(iee::core::rel32_target_checked(callInstruction, 0xE9, 1, 5) == nullptr,
              "Opcode validation should reject mismatched CALL instructions");

  std::array<std::byte, 32> jmpBytes{};
  auto* jmpInstruction = jmpBytes.data() + 8;
  auto* jmpTarget = jmpBytes.data() + 28;
  write_rel32_instruction(jmpInstruction, 0xE9, 1, 5, jmpTarget);

  expect_true(iee::core::rel32_target_checked(jmpInstruction, 0xE9, 1, 5) == jmpTarget,
              "JMP rel32 decoding should return the target");
}

void test_writable_non_executable_guards() {
#ifdef _WIN64
  const auto module = iee::core::get_module_span(nullptr);
  expect_true(module.has_value(), "Test executable module span should be available");
  if (!module) return;
  const auto moduleBase = reinterpret_cast<std::uintptr_t>(module->base);
  const auto writableAddress = reinterpret_cast<const void*>(&g_writableSectionProbe);
  const auto writableRva = reinterpret_cast<std::uintptr_t>(writableAddress) - moduleBase;
  expect_true(iee::core::is_read_write_non_executable_section(
                  *module, writableRva, sizeof(g_writableSectionProbe)),
              "Mutable test data should reside in a writable non-executable PE section");
  expect_true(iee::core::is_writable_non_executable_memory(
                  writableAddress, sizeof(g_writableSectionProbe)),
              "Mutable test data pages should be writable and non-executable");

  const auto executableAddress = reinterpret_cast<const void*>(&executable_section_probe);
  const auto executableRva = reinterpret_cast<std::uintptr_t>(executableAddress) - moduleBase;
  expect_true(!iee::core::is_read_write_non_executable_section(*module, executableRva, 1),
              "Executable code must be rejected as a data scratch section");
  expect_true(!iee::core::is_writable_non_executable_memory(executableAddress, 1),
              "Executable code pages must be rejected as writable scratch memory");
  expect_true(!iee::core::is_read_write_non_executable_section(*module, module->size, 1),
              "A range beyond the module image must be rejected");
#endif
}

void test_manifest_loading() {
  const auto& manifest = iee::game::current_manifest();
  expect_true(manifest.validate(), "Current build manifest should validate");
  expect_true(manifest.executableVersion.matches(2, 6, 6, 0),
              "Current manifest should require a BGEE 2.6.6 executable");
  expect_true(manifest.executableVersion.matches(2, 6, 6, 999),
              "The documented 2.6.6.x manifest should explicitly accept any revision");
  expect_true(iee::game::supports_product_name(manifest, "Baldur's Gate: Enhanced Edition"),
              "BGEE product-name punctuation should normalize safely");
  expect_true(!iee::game::supports_product_name(manifest, "Baldur's Gate II: Enhanced Edition"),
              "A sibling Infinity Engine game must not match the BGEE manifest");
  expect_eq(manifest.referenceRvas.loadArea, std::uintptr_t{0x27E710},
            "LoadArea reference RVA should match");
  expect_eq(manifest.referenceRvas.renderTexture, std::uintptr_t{0x4247E0},
            "RenderTexture reference RVA should match");

  const auto found = iee::game::find_manifest("BGEE 2.6.6.x");
  expect_true(found.has_value(), "Known build manifest should be discoverable by id");
  if (found) {
    expect_eq(found->get().offsets.tisHeaderTileDimension, std::uintptr_t{0x14},
              "Manifest should carry the TIS header tile dimension offset");
  }
  expect_true(iee::game::find_manifest_for_version(2, 6, 6, 123).has_value(),
              "BGEE 2.6.6 should resolve by executable version");

  const auto found273 = iee::game::find_manifest("BGEE 2.7.3.x");
  expect_true(found273.has_value(), "2.7.3 manifest should be discoverable by id");
  if (found273) {
    expect_true(found273->get().validate(), "2.7.3 manifest should validate");
    expect_true(!found273->get().areaAnimations.enabled,
                "Unvalidated BGEE builds must keep area-animation hooks disabled");
    expect_eq(found273->get().referenceRvas.loadArea, std::uintptr_t{0x27EBD0},
              "2.7.3 LoadArea reference RVA should match the offline scan");
    expect_eq(found273->get().referenceRvas.renderTexture, std::uintptr_t{0x4257C0},
              "2.7.3 RenderTexture reference RVA should match the offline scan");
  }
  expect_true(iee::game::find_manifest_for_version(2, 7, 3, 0).has_value(),
              "BGEE 2.7.3.0 should resolve by executable version");
  expect_true(iee::game::find_manifest_for_version(2, 7, 3, 42).has_value(),
              "BGEE 2.7.3.x should accept any revision");
  expect_true(!iee::game::find_manifest_for_version(2, 7, 2, 0).has_value(),
              "Adjacent unknown 2.7.2 must fail closed");
  expect_true(!iee::game::find_manifest_for_version(2, 7, 4, 0).has_value(),
              "Adjacent unknown 2.7.4 must fail closed");
  expect_true(!iee::game::find_manifest_for_version(2, 8, 0, 0).has_value(),
              "Unknown BGEE 2.8 builds must fail closed until validated");

  const auto bg2ee = iee::game::find_manifest("BG2EE 2.7.3.x");
  expect_true(bg2ee.has_value(), "BG2EE 2.7.3 manifest should be discoverable by id");
  if (bg2ee) {
    expect_true(bg2ee->get().validate(), "BG2EE 2.7.3 manifest should validate");
    expect_true(bg2ee->get().areaAnimations.enabled,
                "Validated BG2EE 2.7.3 area-animation hooks should be enabled");
    expect_true(bg2ee->get().worldOverlay.enabled,
                "Validated BG2EE 2.7.3 world-overlay hook should be enabled");
    expect_eq(bg2ee->get().worldOverlay.gameAreaRender, std::uintptr_t{0x189360},
              "BG2EE CGameArea::Render RVA should match the map-composition boundary");
    expect_eq(bg2ee->get().worldOverlay.drawFlushGl, std::uintptr_t{0x42B350},
              "BG2EE DrawFlush_GL RVA should match the deferred-render boundary");
    expect_eq(bg2ee->get().areaAnimations.gameStaticRenderBam, std::uintptr_t{0x1F2B50},
              "BG2EE CGameStatic::RenderBam RVA should match the validated prototype");
    expect_eq(bg2ee->get().areaAnimations.vidCellRenderTexture, std::uintptr_t{0x425790},
              "BG2EE CVidCell::RenderTexture RVA should match the validated prototype");
    expect_eq(bg2ee->get().areaAnimations.glTextureTable, std::uintptr_t{0x757040},
              "BG2EE engine texture descriptor table RVA should match TexImage");
    expect_true(
        bg2ee->get().areaAnimations.glTextureTableReferences ==
            std::array<std::uintptr_t, 3>{{0x42BBEC, 0x42D074, 0x42B037}},
        "BG2EE texture table references should cover DrawGen, TexImage, and DrawDelete");
    expect_eq(bg2ee->get().areaAnimations.glTextureSecondarySelectorReference,
              std::uintptr_t{0x42B90F},
              "BG2EE DrawFlush secondary selector should prove descriptor field +0x24");
    expect_eq(bg2ee->get().areaAnimations.realizedPalette, std::uintptr_t{0x72A1B0},
              "BG2EE realized palette RVA should target the writable Realize scratch table");
    expect_eq(bg2ee->get().areaAnimations.vidPaletteRealize, std::uintptr_t{0x421430},
              "BG2EE CVidPalette::Realize RVA should match the owner capture hook");
    expect_eq(bg2ee->get().areaAnimations.vidPaletteRealizeCallsite,
              std::uintptr_t{0x4242C1},
              "BG2EE owner Realize callsite should bind the validated palette scratch");
    expect_eq(bg2ee->get().areaAnimations.nativeTextureFormat, std::uintptr_t{0x2F7401C},
              "BG2EE native GL external-format RVA should match engine uploads");
    expect_eq(bg2ee->get().areaAnimations.nativeTextureType, std::uintptr_t{0x2F74020},
              "BG2EE native GL type RVA should follow the external-format global");
    expect_eq(bg2ee->get().areaAnimations.gameStaticResref, std::uintptr_t{0x1C0},
              "BG2EE CGameStatic resref offset should match the validated prototype");
    expect_eq(bg2ee->get().areaAnimations.gameStaticCurrentFrame, std::uintptr_t{0x1C8},
              "BG2EE CGameStatic current-frame offset should match the validated prototype");
    expect_eq(bg2ee->get().areaAnimations.gameStaticCurrentSequence, std::uintptr_t{0x1CA},
              "BG2EE CGameStatic sequence offset should match the validated prototype");
    expect_eq(bg2ee->get().areaAnimations.monsterRender, std::uintptr_t{0x32D770},
              "BG2EE CGameAnimationTypeMonster::Render RVA should match the factory "
              "vtable and offline scan");
    expect_eq(bg2ee->get().areaAnimations.monsterIcewindRender, std::uintptr_t{0x32E360},
              "BG2EE CGameAnimationTypeMonsterIcewind::Render RVA should match the factory "
              "and offline scan");
    expect_eq(bg2ee->get().areaAnimations.monsterAnimationId, std::uintptr_t{0x08},
              "BG2EE monster animation-id offset should match the offline scan");
    expect_eq(bg2ee->get().areaAnimations.monsterCurrentCell, std::uintptr_t{0xCD8},
              "BG2EE monster current-cell offset should match the offline scan");
    expect_eq(bg2ee->get().areaAnimations.characterRender, std::uintptr_t{0x32C240},
              "BG2EE CGameAnimationTypeCharacter::Render RVA should match the character "
              "factory vtable and offline scan");
    expect_eq(bg2ee->get().areaAnimations.characterCurrentCell, std::uintptr_t{0xD00},
              "BG2EE character body-cell offset should match the layered renderer");
    expect_eq(bg2ee->get().areaAnimations.characterOverlayCells[0],
              std::uintptr_t{0x1360},
              "BG2EE character weapon-cell offset should match the layered renderer");
    expect_eq(bg2ee->get().areaAnimations.characterOverlayCells[1],
              std::uintptr_t{0x1888},
              "BG2EE character offhand-cell offset should match the layered renderer");
    expect_eq(bg2ee->get().areaAnimations.characterOverlayCells[2],
              std::uintptr_t{0x1DB0},
              "BG2EE character helmet-cell offset should match the layered renderer");
    expect_eq(bg2ee->get().areaAnimations.vidCellPalette, std::uintptr_t{0x08},
              "BG2EE CVidCell palette owner offset should match the Realize callsite");
    expect_eq(bg2ee->get().areaAnimations.vidCellResref, std::uintptr_t{0x110},
              "BG2EE CVidCell resref offset should match the offline scan");
    expect_eq(bg2ee->get().areaAnimations.vidCellCurrentFrame, std::uintptr_t{0x118},
              "BG2EE CVidCell current-frame offset should match the modeled layout");
    expect_eq(bg2ee->get().areaAnimations.vidCellCurrentSequence, std::uintptr_t{0x11A},
              "BG2EE CVidCell sequence offset should match the modeled layout");
    expect_eq(bg2ee->get().referenceRvas.loadArea, std::uintptr_t{0x27EBD0},
              "BG2EE shares the BGEE 2.7.3 LoadArea RVA (unified engine image)");
    expect_eq(bg2ee->get().referenceRvas.renderTexture, std::uintptr_t{0x4257C0},
              "BG2EE shares the BGEE 2.7.3 RenderTexture RVA (unified engine image)");
    expect_true(
        iee::game::supports_product_name(*bg2ee, "Baldur's Gate II: Enhanced Edition"),
        "BG2EE product name should match its own manifest");
    expect_true(!iee::game::supports_product_name(*bg2ee, "Baldur's Gate: Enhanced Edition"),
                "BGEE must not match the BG2EE manifest");
  }

  // BGEE and BG2EE share fixed version 2.7.3, so identity selection must
  // disambiguate on product name rather than returning the first version match.
  const auto bgeeIdentity = iee::game::find_manifest_for_identity(
      2, 7, 3, 0, "Baldur's Gate: Enhanced Edition");
  expect_true(bgeeIdentity.has_value(), "BGEE 2.7.3 should resolve by identity");
  if (bgeeIdentity) {
    expect_true(bgeeIdentity->get().buildId == "BGEE 2.7.3.x",
                "BGEE identity should select the BGEE manifest");
  }
  const auto bg2eeIdentity = iee::game::find_manifest_for_identity(
      2, 7, 3, 0, "Baldur's Gate II: Enhanced Edition");
  expect_true(bg2eeIdentity.has_value(), "BG2EE 2.7.3 should resolve by identity");
  if (bg2eeIdentity) {
    expect_true(bg2eeIdentity->get().buildId == "BG2EE 2.7.3.x",
                "BG2EE identity should select the BG2EE manifest, not BGEE's");
  }
  expect_true(!iee::game::find_manifest_for_identity(2, 7, 3, 0,
                                                    "Icewind Dale: Enhanced Edition")
                   .has_value(),
              "An unvalidated sibling game must still fail closed");
  expect_true(!iee::game::find_manifest_for_identity(2, 7, 2, 0,
                                                    "Baldur's Gate II: Enhanced Edition")
                   .has_value(),
              "Adjacent unknown versions must fail closed even with a known product name");
}

void test_runtime_type_layouts() {
  using namespace iee::game;

  expect_eq(sizeof(CRes), std::size_t{0x58}, "CRes should match the curated x64 layout");
  expect_eq(sizeof(CResWED), std::size_t{0x88}, "CResWED should match the curated x64 layout");
  expect_eq(sizeof(CVidTile), std::size_t{0x110}, "CVidTile should match the curated x64 layout");
  expect_eq(sizeof(CVidCell), std::size_t{0x138}, "CVidCell should match the curated x64 layout");
  expect_eq(sizeof(CVidMode), std::size_t{0x318}, "CVidMode should match the curated x64 layout");
  expect_eq(sizeof(CVisibilityMap), std::size_t{0x70},
            "CVisibilityMap should match the curated x64 layout");
  expect_eq(sizeof(CTypedPtrListOpaque), std::size_t{0x38},
            "CTypedPtrList should match the curated x64 layout");
  expect_eq(sizeof(CInfTileSet), std::size_t{0x138},
            "CInfTileSet should match the curated x64 layout");
  expect_eq(sizeof(CInfGame), std::size_t{0x97F8}, "CInfGame should match the curated x64 layout");
  expect_eq(sizeof(CInfinity), std::size_t{0x498}, "CInfinity should match the curated x64 layout");
  expect_eq(sizeof(CGameArea), std::size_t{0x1120},
            "CGameArea should match the curated x64 layout");
  expect_eq(sizeof(CGameSprite), std::size_t{0x5388},
            "CGameSprite should match the curated x64 layout");

  expect_eq(offsetof(CRes, pData), std::size_t{0x40}, "CRes::pData offset should match EEex docs");
  expect_eq(offsetof(CRes, bLoaded), std::size_t{0x51},
            "CRes::bLoaded offset should match EEex docs");
  expect_eq(offsetof(CVidTile, pRes), std::size_t{0x100},
            "CVidTile::pRes offset should match EEex docs");
  expect_eq(offsetof(CInfGame, m_worldTime), std::size_t{0x3FA0},
            "CInfGame::m_worldTime offset should match EEex docs");
  expect_eq(offsetof(CInfGame, m_vcLocator), std::size_t{0x92C0},
            "CInfGame::m_vcLocator offset should match EEex docs");
  expect_eq(offsetof(CInfinity, m_ptCurrentPosExact), std::size_t{0x2F4},
            "CInfinity::m_ptCurrentPosExact offset should match EEex docs");
  expect_eq(offsetof(CInfinity, m_pArea), std::size_t{0x340},
            "CInfinity::m_pArea offset should match EEex docs");
  expect_eq(offsetof(CGameArea, m_resref), std::size_t{0x204},
            "CGameArea::m_resref offset should match EEex docs");
  expect_eq(offsetof(CGameArea, m_cInfinity), std::size_t{0x5C8},
            "CGameArea::m_cInfinity offset should match EEex docs");
  expect_eq(offsetof(CGameArea, m_lTiledObjects), std::size_t{0xED0},
            "CGameArea::m_lTiledObjects offset should match EEex docs");
  expect_eq(offsetof(CGameSprite, m_currentArea), std::size_t{0x3A20},
            "CGameSprite::m_currentArea offset should match EEex docs");
  expect_eq(offsetof(CGameSprite, m_spriteEffectVidCell), std::size_t{0x3C70},
            "CGameSprite::m_spriteEffectVidCell offset should match EEex docs");
  expect_eq(offsetof(CGameSprite, m_posExact), std::size_t{0x4714},
            "CGameSprite::m_posExact offset should match EEex docs");
}

void test_file_format_layouts() {
  using namespace iee::game;

  expect_eq(sizeof(PVRTextureHeaderV3), std::size_t{0x34},
            "PVRTextureHeaderV3 should match EEex docs");
  expect_eq(sizeof(ResFixedHeader_st), std::size_t{0x14},
            "ResFixedHeader_st should match EEex docs");
  expect_eq(sizeof(TisFileHeader), std::size_t{0x18},
            "TisFileHeader should carry the locally validated tile-dimension field");
  expect_eq(sizeof(WED_WedHeader_st), std::size_t{0x2C}, "WED_WedHeader_st should match EEex docs");
  expect_eq(sizeof(WED_LayerHeader_st), std::size_t{0x18},
            "WED_LayerHeader_st should match EEex docs");
  expect_eq(sizeof(WED_PolyHeader_st), std::size_t{0x14},
            "WED_PolyHeader_st should match EEex docs");
  expect_eq(sizeof(WED_PolyList_st), std::size_t{0x12}, "WED_PolyList_st should match EEex docs");
  expect_eq(sizeof(WED_PolyPoint_st), std::size_t{0x4}, "WED_PolyPoint_st should match EEex docs");
  expect_eq(sizeof(WED_ScreenSectionList), std::size_t{0x4},
            "WED_ScreenSectionList should match EEex docs");
  expect_eq(sizeof(WED_TileData_st), std::size_t{0xA}, "WED_TileData_st should match EEex docs");
  expect_eq(sizeof(WED_TiledObject_st), std::size_t{0x1A},
            "WED_TiledObject_st should match EEex docs");
  expect_eq(sizeof(bamHeader_st), std::size_t{0x18}, "bamHeader_st should match EEex docs");
  expect_eq(sizeof(BAMHEADERV2), std::size_t{0x20}, "BAMHEADERV2 should match EEex docs");
  expect_eq(sizeof(frame), std::size_t{0x18}, "frame should match EEex docs");
  expect_eq(sizeof(frameTableEntry_st), std::size_t{0xC},
            "frameTableEntry_st should match EEex docs");
  expect_eq(sizeof(st_tiledef), std::size_t{0x18}, "st_tiledef should match EEex docs");

  expect_eq(offsetof(PVRTextureHeaderV3, u32MetaDataSize), std::size_t{0x30},
            "PVRTextureHeaderV3::u32MetaDataSize offset should match EEex docs");
  expect_eq(offsetof(TisFileHeader, tileDimension), std::size_t{0x14},
            "TisFileHeader::tileDimension offset should match the validated runtime fact");
  expect_eq(offsetof(WED_WedHeader_st, dwFlags), std::size_t{0x28},
            "WED_WedHeader_st::dwFlags offset should match EEex docs");
  expect_eq(offsetof(WED_LayerHeader_st, nOffsetToTileData), std::size_t{0x10},
            "WED_LayerHeader_st::nOffsetToTileData offset should match EEex docs");
  expect_eq(offsetof(WED_TileData_st, bFlags), std::size_t{0x6},
            "WED_TileData_st::bFlags offset should match EEex docs");
  expect_eq(offsetof(bamHeader_st, nFrameListOffset), std::size_t{0x14},
            "bamHeader_st::nFrameListOffset offset should match EEex docs");
  expect_eq(offsetof(frameTableEntry_st, ___u4), std::size_t{0x8},
            "frameTableEntry_st::___u4 offset should match EEex docs");
}

void test_eeex_doc_layout_maps() {
  using namespace iee::game::eeex_doc;
  const auto find_field = [](const auto& fields, std::string_view name) -> const FieldDesc* {
    for (const auto& field : fields) {
      if (field.name == name) {
        return &field;
      }
    }
    return nullptr;
  };

  expect_eq(CInfGameLayout.size, std::uint32_t{0x97F8},
            "CInfGame doc layout size should match EEex docs");
  expect_eq(CInfGameLayout.fieldCount, std::uint32_t{128},
            "CInfGame doc layout should expose every EEex field row");
  expect_eq(CInfinityLayout.size, std::uint32_t{0x498},
            "CInfinity doc layout size should match EEex docs");
  expect_eq(CInfinityLayout.fieldCount, std::uint32_t{90},
            "CInfinity doc layout should expose every EEex field row");
  expect_eq(CGameAreaLayout.size, std::uint32_t{0x1120},
            "CGameArea doc layout size should match EEex docs");
  expect_eq(CGameAreaLayout.fieldCount, std::uint32_t{105},
            "CGameArea doc layout should expose every EEex field row");
  expect_eq(CGameSpriteLayout.size, std::uint32_t{0x5388},
            "CGameSprite doc layout size should match EEex docs");
  expect_eq(CGameSpriteLayout.fieldCount, std::uint32_t{339},
            "CGameSprite doc layout should expose every EEex field row");
  expect_eq(CGameAnimationTypeLayout.fieldCount, std::uint32_t{24},
            "CGameAnimationType doc layout should expose every EEex field row");
  expect_eq(CGameOptionsLayout.fieldCount, std::uint32_t{153},
            "CGameOptions doc layout should expose every EEex field row");
  expect_eq(CVidModeLayout.fieldCount, std::uint32_t{42},
            "CVidMode doc layout should expose every EEex field row");

  const auto* animationShaderField = find_field(CGameAnimationTypeFields, "m_bUseSpriteShader");
  expect_true(animationShaderField != nullptr,
              "CGameAnimationType should expose the sprite-shader field from EEex docs");
  if (animationShaderField) {
    expect_eq(animationShaderField->offset, std::uint32_t{0x20},
              "CGameAnimationType::m_bUseSpriteShader offset should match EEex docs");
  }

  const auto* optionShaderField = find_field(CGameOptionsFields, "m_bUseSpriteShader");
  expect_true(optionShaderField != nullptr,
              "CGameOptions should expose the sprite-shader option from EEex docs");
  if (optionShaderField) {
    expect_eq(optionShaderField->offset, std::uint32_t{0x238},
              "CGameOptions::m_bUseSpriteShader offset should match EEex docs");
  }

  const auto* areaInfinityField = find_field(CGameAreaFields, "m_cInfinity");
  expect_true(areaInfinityField != nullptr,
              "CGameArea should expose the embedded CInfinity field from EEex docs");
  if (areaInfinityField) {
    expect_eq(areaInfinityField->offset, std::uint32_t{0x5C8},
              "CGameArea::m_cInfinity offset should match EEex docs");
  }

  const auto* areaTiledObjectField = find_field(CGameAreaFields, "m_lTiledObjects");
  expect_true(areaTiledObjectField != nullptr,
              "CGameArea should expose the tiled-object list from EEex docs");
  if (areaTiledObjectField) {
    expect_eq(areaTiledObjectField->offset, std::uint32_t{0xED0},
              "CGameArea::m_lTiledObjects offset should match EEex docs");
  }

  const auto* visibleAreaField = find_field(CInfGameFields, "m_visibleArea");
  expect_true(visibleAreaField != nullptr,
              "CInfGame should expose the visible-area selector from EEex docs");
  if (visibleAreaField) {
    expect_eq(visibleAreaField->offset, std::uint32_t{0x6590},
              "CInfGame::m_visibleArea offset should match EEex docs");
  }

  const auto* gameAreasField = find_field(CInfGameFields, "m_gameAreas");
  expect_true(gameAreasField != nullptr,
              "CInfGame should expose the loaded area table from EEex docs");
  if (gameAreasField) {
    expect_eq(gameAreasField->offset, std::uint32_t{0x6598},
              "CInfGame::m_gameAreas offset should match EEex docs");
  }

  const auto* masterAreaField = find_field(CInfGameFields, "m_pGameAreaMaster");
  expect_true(masterAreaField != nullptr,
              "CInfGame should expose the master area pointer from EEex docs");
  if (masterAreaField) {
    expect_eq(masterAreaField->offset, std::uint32_t{0x65F8},
              "CInfGame::m_pGameAreaMaster offset should match EEex docs");
  }
  expect_true(CGameSpriteFields[0].name == "baseclass_0",
              "CGameSprite doc layout should begin at the documented baseclass");
  expect_true(CGameSpriteFields.back().name == "m_bOutline",
              "CGameSprite doc layout should include the final documented field");
}

void test_config_parsing() {
  const auto tempPath = std::filesystem::current_path() / "InfinityEngine-Enhancer-test.ini";
  {
    std::ofstream out(tempPath, std::ios::trunc);
    expect_true(static_cast<bool>(out), "Config test fixture should be writable");
    out << "[Core]\n";
    out << "VerboseLogs = true\n\n";
    out << "[Rendering]\n";
    out << "EnableAnisotropicFiltering = false\n";
    out << "MaxAnisotropy = 4.0\n";
    out << "LODBias = -0.5\n\n";
  }

  iee::core::EngineConfig cfg{};
  expect_true(iee::core::ConfigManager::load(tempPath, cfg),
              "ConfigManager::load should parse a valid INI");
  expect_true(cfg.enableVerboseLogging, "Verbose logging flag should parse");
  expect_true(!cfg.enableAnisotropicFiltering, "Rendering bool should parse");
  expect_eq(cfg.maxAnisotropy, 4.0f, "Floating-point values should parse");
  expect_eq(cfg.lodBias, -0.5f, "Negative float values should parse");

  std::error_code ec;
  std::filesystem::remove(tempPath, ec);
}

void test_config_numeric_bounds() {
  const auto tempPath = std::filesystem::current_path() / "InfinityEngine-Enhancer-bounds-test.ini";
  {
    std::ofstream out(tempPath, std::ios::trunc);
    out << "[Rendering]\n";
    out << "MaxAnisotropy = 1000\n";
    out << "LODBias = nan\n";
    out << "LODBias = 0.5junk\n";
  }

  iee::core::EngineConfig cfg{};
  iee::core::ConfigLoadDiagnostics diagnostics{};
  expect_true(iee::core::ConfigManager::load(tempPath, cfg, &diagnostics),
              "ConfigManager::load should accept and normalize numeric input");
  expect_eq(cfg.maxAnisotropy, 64.0f, "Anisotropy should be clamped to a safe bound");
  expect_eq(cfg.lodBias, -0.25f, "Non-finite LOD bias should use the default");
  expect_eq(diagnostics.invalidValues, std::size_t{2},
            "Invalid numeric values should be reported to the bootstrap logger");

  std::error_code error;
  std::filesystem::remove(tempPath, error);
}

void test_config_reports_malformed_values() {
  const auto tempPath =
      std::filesystem::current_path() / "InfinityEngine-Enhancer-invalid-test.ini";
  {
    std::ofstream out(tempPath, std::ios::trunc);
    out << "[Core]\n";
    out << "VerboseLogs = perhaps\n";
    out << "this line has no equals sign\n";
  }

  iee::core::EngineConfig cfg{};
  iee::core::ConfigLoadDiagnostics diagnostics{};
  expect_true(iee::core::ConfigManager::load(tempPath, cfg, &diagnostics),
              "Readable config files should keep valid/default values");
  expect_true(!cfg.enableVerboseLogging, "Invalid bool should retain its safe default");
  expect_eq(diagnostics.invalidValues, std::size_t{1},
            "Invalid bool should be counted for post-init diagnostics");
  expect_eq(diagnostics.malformedLines, std::size_t{1},
            "Malformed lines should be counted for post-init diagnostics");

  std::error_code error;
  std::filesystem::remove(tempPath, error);
}

void test_config_shader_override_defaults() {
  iee::core::EngineConfig cfg{};
  expect_true(!cfg.dumpEngineShaders, "shader dump defaults off");
  expect_true(!cfg.enableDebugHotkeys, "hotkeys default off");
  expect_true(cfg.enableWaterEffect, "water effect defaults ON");
  expect_true(!cfg.enableBamUiTextureProbe, "BAM/UI texture probe defaults off");
  expect_true(!cfg.enableAreaAnimationX4, "area-animation x4 registry defaults off");
  expect_true(!cfg.enableCreatureSpriteUpscaleTest,
              "creature-sprite xN test defaults off");
  expect_true(!cfg.enableCreatureSpriteX2Test, "creature-sprite x2 test defaults off");
  expect_true(!cfg.enableCreatureSpriteLinearFiltering,
              "creature-sprite linear filtering defaults off");
  expect_true(!cfg.creature_sprite_upscale_enabled(),
              "creature-sprite upscale helper defaults off");
  auto newKeyOnly = cfg;
  newKeyOnly.enableCreatureSpriteUpscaleTest = true;
  expect_true(newKeyOnly.creature_sprite_upscale_enabled(),
              "the xN activation key should enable creature-sprite upscaling");
  auto legacyKeyOnly = cfg;
  legacyKeyOnly.enableCreatureSpriteX2Test = true;
  expect_true(legacyKeyOnly.creature_sprite_upscale_enabled(),
              "the legacy x2 activation key should remain an upscale alias");
  expect_true(!cfg.enableBigLogoX4Test, "BIGLOGO x4 test defaults off");
  expect_true(!cfg.enableMainMenuX4Test, "main-menu x4 test defaults off");
  expect_true(!cfg.enableMenuX2Test, "complete menu x2 test defaults off");
  expect_true(!cfg.enablePerformanceLogging, "performance logs default off");
}

void test_creature_sprite_xn_native_border_geometry() {
  using namespace iee::creature_sprite_x2;
  expect_true(supported_physical_scale(2) && supported_physical_scale(4) &&
                  !supported_physical_scale(1) && !supported_physical_scale(3),
              "Creature packs should support exactly physical scales 2 and 4");
  expect_eq(logical_texture_extent(36), 38,
            "Creature texture should retain CVidCell's two-pixel logical padding");
  expect_eq(physical_texture_extent(36, 2), std::int64_t{76},
            "x2 replacement should scale the complete bordered texture");
  expect_eq(physical_texture_extent(37, 2), std::int64_t{78},
            "x2 replacement height should include both native borders");
  expect_eq(physical_texture_extent(36, 4), std::int64_t{152},
            "x4 replacement should scale the complete bordered texture");
  expect_eq(physical_texture_extent(37, 4), std::int64_t{156},
            "x4 replacement height should include both native borders");
  expect_eq(physical_content_offset(2), std::int64_t{2},
            "x2 content should begin after one scaled native logical border");
  expect_eq(physical_content_offset(4), std::int64_t{4},
            "x4 content should begin after one scaled native logical border");
  expect_eq(kMaximumCompositeLayers, std::size_t{8},
            "Character composition should retain repeated ordered layer events");

  constexpr std::array<FrameGeometry, 3> layers{{
      {.logicalWidth = 27, .logicalHeight = 63, .centerX = 17, .centerY = 50},
      {.logicalWidth = 15, .logicalHeight = 12, .centerX = 9, .centerY = 51},
      {.logicalWidth = 17, .logicalHeight = 25, .centerX = 6, .centerY = 31},
  }};
  CompositeBounds bounds{};
  expect_true(calculate_composite_bounds(layers.data(), layers.size(), bounds),
              "Character layer centers should resolve a shared composite extent");
  expect_eq(bounds.left, -17, "Composite union should retain the leftmost body pixel");
  expect_eq(bounds.top, -51, "Composite union should retain the helmet top");
  expect_eq(bounds.right, 11, "Composite union should retain the shield right edge");
  expect_eq(bounds.bottom, 13, "Composite union should retain the body bottom edge");
  expect_eq(bounds.logical_width(), 30,
            "Composite width should include both native transparent borders");
  expect_eq(bounds.logical_height(), 66,
            "Composite height should include both native transparent borders");
  const auto destinationOffset = [&](const FrameGeometry& layer, std::uint32_t scale) {
    return std::array<std::int64_t, 2>{
        physical_layer_offset(layer.centerX, bounds.left, scale),
        physical_layer_offset(layer.centerY, bounds.top, scale),
    };
  };
  expect_true(destinationOffset(layers[0], 2) ==
                  std::array<std::int64_t, 2>{2, 4},
              "x2 body placement should preserve its BAM center");
  expect_true(destinationOffset(layers[1], 2) ==
                  std::array<std::int64_t, 2>{18, 2},
              "x2 helmet placement should preserve its BAM center");
  expect_true(destinationOffset(layers[2], 2) ==
                  std::array<std::int64_t, 2>{24, 42},
              "x2 shield placement should preserve its BAM center");
  expect_true(destinationOffset(layers[0], 4) ==
                  std::array<std::int64_t, 2>{4, 8},
              "x4 body placement should preserve its BAM center");
  expect_true(destinationOffset(layers[1], 4) ==
                  std::array<std::int64_t, 2>{36, 4},
              "x4 helmet placement should preserve its BAM center");
  expect_true(destinationOffset(layers[2], 4) ==
                  std::array<std::int64_t, 2>{48, 84},
              "x4 shield placement should preserve its BAM center");

  expect_eq(overwrite_nontransparent_pixel(0xFF123456u, 0u), 0xFF123456u,
            "Transparent palette colors should leave the composite unchanged");
  expect_eq(overwrite_nontransparent_pixel(0xFF123456u, 0xFFABCDEFu), 0xFFABCDEFu,
            "Opaque palette colors should replace the composite pixel");
  expect_eq(overwrite_nontransparent_pixel(0xFF000000u, 0x80FFFFFFu), 0x80FFFFFFu,
            "Partial alpha should be preserved for the native final GPU draw");
  expect_eq(xbr_blend_pixel(0xFF000000u, 0xFFFFFFFFu, 1), 0xFF3F3F3Fu,
            "xBR 64W should reproduce Scalepix's opaque integer floor");
  expect_eq(xbr_blend_pixel(0x00010203u, 0xFFABCDEFu, 1), 0x3FABCDEFu,
            "xBR should retain source RGB when the destination is transparent");
  expect_eq(xbr_blend_pixel(0xFF123456u, 0x00000000u, 1), 0xBF123456u,
            "xBR should retain destination RGB when the source is transparent");
  expect_eq(xbr_blend_pixel(
                xbr_blend_pixel(0xFF000000u, 0xFFFFFFFFu, 3),
                0xFFFFFFFFu, 3),
            0xFFEFEFEFu,
            "Ordered xBR blends should preserve each intermediate floor");
  expect_eq(xbr_blend_pixel(0xFF123456u, 0xFFFFFFFFu, 5), 0xFF123456u,
            "An invalid xBR blend opcode should fail closed to the destination");
}

void test_creature_sprite_native_pixel_encodings() {
  using iee::creature_sprite_x2::supported_native_pixel_encoding;
  expect_true(supported_native_pixel_encoding({0x1908, 0x1401}),
              "RGBA plus unsigned-byte is a native engine encoding");
  expect_true(supported_native_pixel_encoding({0x80E1, 0x1401}),
              "BGRA plus unsigned-byte is a native engine encoding");
  expect_true(supported_native_pixel_encoding({0x80E1, 0x8367}),
              "BGRA plus reversed 8:8:8:8 is a native engine encoding");
  expect_true(!supported_native_pixel_encoding({0x1908, 0x8367}),
              "RGBA plus reversed 8:8:8:8 is not produced by the engine branch");
  expect_true(!supported_native_pixel_encoding({0, 0}),
              "Uninitialized native encoding globals must fail closed");
  expect_true(!supported_native_pixel_encoding({0x1907, 0x1401}),
              "Unknown external formats must fail closed");
}

void test_creature_sprite_transient_texture_lifecycle() {
  iee::creature_sprite_x2::EngineTextureApi api{};
  api.DrawBindTexture = &record_creature_texture_bind;
  api.DrawDeleteTexture = &record_creature_texture_delete;

  g_creatureTextureLifecycle.clear();
  iee::creature_sprite_x2::finish_composite_texture(api, 17, 42);
  expect_true(g_creatureTextureLifecycle == std::vector<int>{17, -42},
              "Character composite cleanup should restore native binding before marking "
              "the transient replacement delete-pending");

  g_creatureTextureLifecycle.clear();
  iee::creature_sprite_x2::finish_composite_texture(api, 17, 17);
  expect_true(g_creatureTextureLifecycle == std::vector<int>{17},
              "Character composite cleanup must never delete the native texture id");
}

void test_creature_sprite_registry_formats() {
#ifdef _WIN32
  const auto root = std::filesystem::current_path() / "creature-sprite-registry-format-test";
  std::error_code ec;
  std::filesystem::remove_all(root, ec);
  std::filesystem::create_directory(root);

  const auto append = [](std::vector<std::byte>& bytes, const auto& value) {
    const auto* first = reinterpret_cast<const std::byte*>(&value);
    bytes.insert(bytes.end(), first, first + sizeof(value));
  };
  const auto append_raw = [](std::vector<std::byte>& bytes, const void* value,
                             std::size_t size) {
    const auto* first = reinterpret_cast<const std::byte*>(value);
    bytes.insert(bytes.end(), first, first + size);
  };
  const auto write_file = [](const std::filesystem::path& path,
                             const std::vector<std::byte>& bytes) {
    std::ofstream output(path, std::ios::binary);
    if (!output) return false;
    output.write(reinterpret_cast<const char*>(bytes.data()),
                 static_cast<std::streamsize>(bytes.size()));
    return static_cast<bool>(output);
  };
  const auto await = [](auto&& predicate) {
    const auto deadline = std::chrono::steady_clock::now() +
                          std::chrono::seconds(5);
    do {
      if (predicate()) return true;
      std::this_thread::sleep_for(std::chrono::milliseconds(2));
    } while (std::chrono::steady_clock::now() < deadline);
    return predicate();
  };
  constexpr std::array<char, 8> legacyMagic{
      {'I', 'E', 'E', 'C', 'S', 'X', '2', '\0'}};
  constexpr std::array<char, 8> xnMagic{
      {'I', 'E', 'E', 'C', 'S', 'X', 'N', '\0'}};
  constexpr std::array<char, 8> setMagic{
      {'I', 'E', 'E', 'C', 'S', 'N', 'S', '\0'}};
  constexpr std::array<char, 8> catalogMagic{
      {'I', 'E', 'E', 'C', 'S', 'N', 'C', '\0'}};
  constexpr std::array<char, 8> target{{'T', 'E', 'S', 'T', '\0', '\0', '\0', '\0'}};
  const auto make_registry = [&](const std::array<char, 8>& magic,
                                 std::uint32_t version, std::uint32_t scale,
                                 std::uint32_t metadata,
                                 std::uint32_t resourceCount = 1,
                                 std::uint32_t payloadScale = 0,
                                 char resrefMarker = 'T') {
    std::vector<std::byte> bytes;
    append_raw(bytes, magic.data(), magic.size());
    for (const auto value :
         std::array<std::uint32_t, 4>{{version, scale, resourceCount, metadata}}) {
      append(bytes, value);
    }
    if (payloadScale == 0) payloadScale = scale;
    for (std::uint32_t resourceIndex = 0; resourceIndex < resourceCount; ++resourceIndex) {
      auto resref = target;
      resref[0] = resrefMarker;
      resref[4] = static_cast<char>(resourceIndex & 0xFFu);
      resref[5] = static_cast<char>((resourceIndex >> 8u) & 0xFFu);
      append_raw(bytes, resref.data(), resref.size());
      const std::array<std::byte, 32> sourceHash{};
      append_raw(bytes, sourceHash.data(), sourceHash.size());
      for (const auto value : std::array<std::uint32_t, 2>{{1, 1}}) append(bytes, value);
      const std::uint16_t width = 1;
      const std::uint16_t height = 1;
      const std::int16_t center = 0;
      const std::uint8_t transparent = 0;
      const std::array<std::byte, 3> reserved{};
      const std::uint32_t indexBytes = payloadScale * payloadScale;
      append(bytes, width);
      append(bytes, height);
      append(bytes, center);
      append(bytes, center);
      append(bytes, transparent);
      append_raw(bytes, reserved.data(), reserved.size());
      append(bytes, indexBytes);
      std::array<std::uint16_t, 256> representatives{};
      representatives.fill(0xFFFFu);
      representatives[1] = 0;
      append_raw(bytes, representatives.data(), sizeof(representatives));
      const std::vector<std::uint8_t> indices(indexBytes, 1);
      append_raw(bytes, indices.data(), indices.size());
      if (magic == xnMagic && version == 4) {
        std::vector<std::byte> recipes;
        const std::uint32_t recipeCount = 1;
        const std::uint32_t pixel = 0;
        const std::uint8_t operationCount = 1;
        const std::uint8_t sourceIndex = 1;
        const std::uint8_t blendCode = 2;
        append(recipes, recipeCount);
        append(recipes, pixel);
        append(recipes, operationCount);
        append(recipes, sourceIndex);
        append(recipes, blendCode);
        const auto recipeBytes = static_cast<std::uint32_t>(recipes.size());
        append(bytes, recipeBytes);
        append_raw(bytes, recipes.data(), recipes.size());
      }
      const std::uint32_t slotCount = 1;
      const std::uint32_t frameIndex = 0;
      append(bytes, slotCount);
      append(bytes, frameIndex);
    }
    return bytes;
  };

  const auto test_crc32 = [](const std::vector<std::byte>& bytes) {
    std::uint32_t value = 0xFFFFFFFFu;
    for (const auto byte : bytes) {
      value ^= std::to_integer<std::uint8_t>(byte);
      for (unsigned bit = 0; bit < 8; ++bit) {
        value = (value >> 1u) ^ (0xEDB88320u & (0u - (value & 1u)));
      }
    }
    return value ^ 0xFFFFFFFFu;
  };
  struct TestShard {
    std::vector<std::byte> registry;
    std::uint32_t resourceCount{};
    std::uint64_t frameCount{};
    std::uint64_t indexBytes{};
    std::array<std::byte, 32> sha256{};
  };
  const auto compress_xpress_huff = [](const std::vector<std::uint8_t>& logical) {
    std::vector<std::uint8_t> result;
    COMPRESSOR_HANDLE compressor{};
    if (logical.empty() ||
        !CreateCompressor(COMPRESS_ALGORITHM_XPRESS_HUFF, nullptr,
                          &compressor)) {
      return result;
    }
    SIZE_T required = 0;
    (void)Compress(compressor, logical.data(), logical.size(), nullptr, 0,
                   &required);
    if (required != 0) {
      result.resize(required);
      SIZE_T written = 0;
      if (!Compress(compressor, logical.data(), logical.size(), result.data(),
                    result.size(), &written) ||
          written == 0 || written > result.size()) {
        result.clear();
      } else {
        result.resize(written);
      }
    }
    CloseCompressor(compressor);
    return result;
  };
  const auto make_v5_shard = [&](std::uint32_t registryScale, char marker,
                                  std::uint16_t width, std::uint16_t height,
                                  std::uint8_t codec,
                                  const std::vector<std::uint8_t>& stored,
                                  std::uint32_t frameCount = 1,
                                  std::optional<std::uint32_t> declaredStoredBytes =
                                      std::nullopt,
                                  std::array<std::byte, 2> reserved = {}) {
    TestShard shard;
    append_raw(shard.registry, xnMagic.data(), xnMagic.size());
    for (const auto value : std::array<std::uint32_t, 4>{
             {5, registryScale, 1, 0xFFFFu}}) {
      append(shard.registry, value);
    }
    auto resref = target;
    resref[0] = marker;
    append_raw(shard.registry, resref.data(), resref.size());
    const std::array<std::byte, 32> sourceHash{};
    append_raw(shard.registry, sourceHash.data(), sourceHash.size());
    append(shard.registry, frameCount);
    const std::uint32_t cycleCount = 1;
    append(shard.registry, cycleCount);
    for (std::uint32_t frameIndex = 0; frameIndex < frameCount; ++frameIndex) {
      const std::int16_t center = 0;
      const std::uint8_t transparent = 0;
      append(shard.registry, width);
      append(shard.registry, height);
      append(shard.registry, center);
      append(shard.registry, center);
      append(shard.registry, transparent);
      append(shard.registry, codec);
      append_raw(shard.registry, reserved.data(), reserved.size());
      const auto payloadBytes = declaredStoredBytes.value_or(
          static_cast<std::uint32_t>(stored.size()));
      append(shard.registry, payloadBytes);
      std::array<std::uint16_t, 256> representatives{};
      representatives.fill(0xFFFFu);
      representatives[1] = 0;
      append_raw(shard.registry, representatives.data(),
                 sizeof(representatives));
      if (!stored.empty()) {
        append_raw(shard.registry, stored.data(), stored.size());
      }
    }
    append(shard.registry, frameCount);
    for (std::uint32_t frameIndex = 0; frameIndex < frameCount; ++frameIndex) {
      append(shard.registry, frameIndex);
    }
    shard.resourceCount = 1;
    shard.frameCount = frameCount;
    const auto logicalBytes = static_cast<std::uint64_t>(width) * height *
                              registryScale * registryScale;
    shard.indexBytes = logicalBytes * frameCount;
    shard.sha256 = test_sha256(shard.registry);
    return shard;
  };
  const auto make_shard = [&](std::uint32_t registryScale, char marker) {
    TestShard shard;
    shard.registry = make_registry(xnMagic, 3, registryScale, 0x6110, 1, 0, marker);
    shard.resourceCount = 1;
    shard.frameCount = 1;
    shard.indexBytes = registryScale * registryScale;
    shard.sha256 = test_sha256(shard.registry);
    return shard;
  };
  const auto make_set = [&](std::uint32_t scale,
                            const std::vector<TestShard>& shards) {
    std::vector<std::byte> bytes;
    std::uint32_t totalResources = 0;
    std::uint64_t totalFrames = 0;
    std::uint64_t totalIndexBytes = 0;
    std::uint64_t totalRegistryBytes = 0;
    for (const auto& shard : shards) {
      totalResources += shard.resourceCount;
      totalFrames += shard.frameCount;
      totalIndexBytes += shard.indexBytes;
      totalRegistryBytes += shard.registry.size();
    }
    append_raw(bytes, setMagic.data(), setMagic.size());
    for (const auto value :
         std::array<std::uint32_t, 6>{{1, scale,
                                      static_cast<std::uint32_t>(shards.size()),
                                      totalResources, 0x6110, 0}}) {
      append(bytes, value);
    }
    append(bytes, totalFrames);
    append(bytes, totalIndexBytes);
    append(bytes, totalRegistryBytes);
    for (const auto& shard : shards) {
      append_raw(bytes, shard.sha256.data(), shard.sha256.size());
      const auto checksum = test_crc32(shard.registry);
      append(bytes, checksum);
      append(bytes, shard.resourceCount);
      append(bytes, shard.frameCount);
      append(bytes, shard.indexBytes);
      const auto registryBytes = static_cast<std::uint64_t>(shard.registry.size());
      append(bytes, registryBytes);
    }
    return bytes;
  };
  const auto make_shard_entry = [&](const TestShard& shard) {
    std::vector<std::byte> bytes;
    append_raw(bytes, shard.sha256.data(), shard.sha256.size());
    const auto checksum = test_crc32(shard.registry);
    append(bytes, checksum);
    append(bytes, shard.resourceCount);
    append(bytes, shard.frameCount);
    append(bytes, shard.indexBytes);
    const auto registryBytes = static_cast<std::uint64_t>(shard.registry.size());
    append(bytes, registryBytes);
    return bytes;
  };
  const auto make_component_digest_from_entry = [&append, &append_raw](
                                                    std::uint32_t scale,
                                                    const std::byte* shardEntry,
                                                    std::size_t shardEntryBytes) {
    std::vector<std::byte> digestInput;
    constexpr std::array<char, 21> domain{{
        'I', 'E', 'E', 'C', 'S', 'N', 'C', '-', 'C', 'O', 'M', 'P', 'O',
        'N', 'E', 'N', 'T', '-', 'V', '1', '\0',
    }};
    append_raw(digestInput, domain.data(), domain.size());
    append(digestInput, scale);
    append_raw(digestInput, shardEntry, shardEntryBytes);
    return test_sha256(digestInput);
  };
  const auto make_component_digest = [&](std::uint32_t scale,
                                         const TestShard& shard) {
    const auto shardEntry = make_shard_entry(shard);
    return make_component_digest_from_entry(scale, shardEntry.data(),
                                            shardEntry.size());
  };
  struct TestCatalogAnimation {
    std::uint32_t animationId{};
    std::uint32_t owner{};
    std::vector<std::uint32_t> componentIndices;
  };
  struct TestCatalogDirectoryEntry {
    std::uint32_t animationId{};
    std::array<char, 8> resref{};
    std::uint32_t componentIndex{};
    std::uint32_t shardIndex{};
    std::uint32_t resourceOrdinal{};
  };
  const auto make_catalog = [&](std::uint32_t scale,
                                 const std::vector<TestCatalogAnimation>& animations,
                                 const std::vector<TestShard>& components) {
    std::vector<std::byte> bytes;
    std::uint32_t membershipCount = 0;
    std::uint64_t totalResources = 0;
    std::uint64_t totalFrames = 0;
    std::uint64_t totalIndexBytes = 0;
    std::uint64_t totalRegistryBytes = 0;
    for (const auto& animation : animations) {
      membershipCount += static_cast<std::uint32_t>(animation.componentIndices.size());
    }
    for (const auto& component : components) {
      totalResources += component.resourceCount;
      totalFrames += component.frameCount;
      totalIndexBytes += component.indexBytes;
      totalRegistryBytes += component.registry.size();
    }

    append_raw(bytes, catalogMagic.data(), catalogMagic.size());
    for (const auto value :
         std::array<std::uint32_t, 6>{{1, scale,
                                      static_cast<std::uint32_t>(animations.size()),
                                      static_cast<std::uint32_t>(components.size()),
                                      membershipCount,
                                      static_cast<std::uint32_t>(components.size())}}) {
      append(bytes, value);
    }
    append(bytes, totalResources);
    append(bytes, totalFrames);
    append(bytes, totalIndexBytes);
    append(bytes, totalRegistryBytes);

    std::uint32_t membershipStart = 0;
    for (const auto& animation : animations) {
      append(bytes, animation.animationId);
      append(bytes, animation.owner);
      append(bytes, membershipStart);
      const auto count = static_cast<std::uint32_t>(animation.componentIndices.size());
      append(bytes, count);
      membershipStart += count;
    }
    for (const auto& animation : animations) {
      for (const auto componentIndex : animation.componentIndices) {
        append(bytes, componentIndex);
      }
    }
    for (std::uint32_t index = 0; index < components.size(); ++index) {
      const auto& component = components[index];
      const auto digest = make_component_digest(scale, component);
      append_raw(bytes, digest.data(), digest.size());
      append(bytes, index);
      const std::uint32_t shardCount = 1;
      append(bytes, shardCount);
      append(bytes, component.resourceCount);
      const std::uint32_t reserved = 0;
      append(bytes, reserved);
      append(bytes, component.frameCount);
      append(bytes, component.indexBytes);
      const auto registryBytes = static_cast<std::uint64_t>(component.registry.size());
      append(bytes, registryBytes);
    }
    for (const auto& component : components) {
      const auto shardEntry = make_shard_entry(component);
      append_raw(bytes, shardEntry.data(), shardEntry.size());
    }
    return bytes;
  };
  const auto make_catalog_v2 = [&] (
      std::uint32_t scale,
      const std::vector<TestCatalogAnimation>& animations,
      const std::vector<TestShard>& components,
      const std::vector<TestCatalogDirectoryEntry>& directory) {
    auto bytes = make_catalog(scale, animations, components);
    const std::uint32_t version = 2;
    std::memcpy(bytes.data() + 8, &version, sizeof(version));
    std::vector<std::byte> encodedDirectory;
    for (const auto& entry : directory) {
      append(encodedDirectory, entry.animationId);
      append_raw(encodedDirectory, entry.resref.data(), entry.resref.size());
      append(encodedDirectory, entry.componentIndex);
      append(encodedDirectory, entry.shardIndex);
      append(encodedDirectory, entry.resourceOrdinal);
    }
    constexpr char domain[] = "IEECSNC-DIRECTORY-V2";
    std::vector<std::byte> digestInput;
    append_raw(digestInput, domain, sizeof(domain));
    append(digestInput, scale);
    append_raw(digestInput, encodedDirectory.data(), encodedDirectory.size());
    const auto digest = test_sha256(digestInput);
    std::vector<std::byte> extension;
    const auto directoryCount =
        static_cast<std::uint32_t>(directory.size());
    const std::uint32_t directoryEntryBytes = 24;
    append(extension, directoryCount);
    append(extension, directoryEntryBytes);
    append_raw(extension, digest.data(), digest.size());
    bytes.insert(bytes.begin() + 64, extension.begin(), extension.end());
    bytes.insert(bytes.end(), encodedDirectory.begin(), encodedDirectory.end());
    return bytes;
  };
  const auto make_grouped_component_catalog = [&](std::uint32_t scale,
                                                   std::uint32_t animationId,
                                                   std::uint32_t owner,
                                                   const std::vector<TestShard>& shards) {
    std::vector<std::byte> bytes;
    std::vector<std::byte> shardEntries;
    std::uint64_t totalResources = 0;
    std::uint64_t totalFrames = 0;
    std::uint64_t totalIndexBytes = 0;
    std::uint64_t totalRegistryBytes = 0;
    for (const auto& shard : shards) {
      const auto entry = make_shard_entry(shard);
      append_raw(shardEntries, entry.data(), entry.size());
      totalResources += shard.resourceCount;
      totalFrames += shard.frameCount;
      totalIndexBytes += shard.indexBytes;
      totalRegistryBytes += shard.registry.size();
    }
    append_raw(bytes, catalogMagic.data(), catalogMagic.size());
    for (const auto value : std::array<std::uint32_t, 6>{
             {1, scale, 1, 1, 1, static_cast<std::uint32_t>(shards.size())}}) {
      append(bytes, value);
    }
    append(bytes, totalResources);
    append(bytes, totalFrames);
    append(bytes, totalIndexBytes);
    append(bytes, totalRegistryBytes);
    append(bytes, animationId);
    append(bytes, owner);
    const std::uint32_t zero = 0;
    const std::uint32_t one = 1;
    append(bytes, zero);
    append(bytes, one);
    append(bytes, zero);
    const auto componentDigest = make_component_digest_from_entry(
        scale, shardEntries.data(), shardEntries.size());
    append_raw(bytes, componentDigest.data(), componentDigest.size());
    append(bytes, zero);
    const auto shardCount = static_cast<std::uint32_t>(shards.size());
    append(bytes, shardCount);
    const auto resourceCount = static_cast<std::uint32_t>(totalResources);
    append(bytes, resourceCount);
    append(bytes, zero);
    append(bytes, totalFrames);
    append(bytes, totalIndexBytes);
    append(bytes, totalRegistryBytes);
    append_raw(bytes, shardEntries.data(), shardEntries.size());
    return bytes;
  };
  const auto digest_filename = [](const std::array<std::byte, 32>& digest) {
    constexpr std::array<char, 16> hex{{
        '0', '1', '2', '3', '4', '5', '6', '7',
        '8', '9', 'A', 'B', 'C', 'D', 'E', 'F',
    }};
    std::string filename = "CreatureSprites-XN-";
    filename.reserve(filename.size() + digest.size() * 2 + 9);
    for (const auto byte : digest) {
      const auto value = std::to_integer<std::uint8_t>(byte);
      filename.push_back(hex[value >> 4u]);
      filename.push_back(hex[value & 0x0Fu]);
    }
    filename += ".registry";
    return filename;
  };
  const auto overwrite_u32 = [](std::vector<std::byte>& bytes, std::size_t offset,
                                std::uint32_t value) {
    std::memcpy(bytes.data() + offset, &value, sizeof(value));
  };
  const auto write_set_case = [&](std::uint32_t scale,
                                  const std::vector<TestShard>& shards) {
    write_file(root / "CreatureSprites-XN.set", make_set(scale, shards));
    for (std::size_t index = 0; index < shards.size(); ++index) {
      auto digits = std::to_string(index);
      const auto filename = "CreatureSprites-XN-" +
                            std::string(4 - digits.size(), '0') + digits + ".registry";
      write_file(root / filename, shards[index].registry);
    }
  };
  const auto write_catalog_case = [&](
      std::uint32_t scale, const std::vector<TestCatalogAnimation>& animations,
      const std::vector<TestShard>& components) {
    write_file(root / "CreatureSprites-XN.catalog",
               make_catalog(scale, animations, components));
    for (const auto& component : components) {
      write_file(root / digest_filename(component.sha256), component.registry);
    }
  };

  const auto legacyPath = root / "CreatureSprites-X2.registry";
  const auto xnPath = root / "CreatureSprites-XN.registry";
  const auto setPath = root / "CreatureSprites-XN.set";
  const auto catalogPath = root / "CreatureSprites-XN.catalog";
  expect_eq(iee::creature_sprite_x2::kMaximumRegistryBytes,
            std::uint64_t{128} * 1024u * 1024u,
            "Legacy and x2 registries should retain the 128 MiB byte bound");
  expect_eq(iee::creature_sprite_x2::maximum_registry_bytes_for_scale(4),
            std::uint64_t{512} * 1024u * 1024u,
            "An x4 registry shard should admit measured 337 MiB equipment families");
  expect_eq(iee::creature_sprite_x2::maximum_registry_bytes_for_scale(3),
            std::uint64_t{0},
            "Unsupported scales should have no registry byte allowance");
  expect_eq(iee::creature_sprite_x2::kMaximumRegistrySetShards, std::uint32_t{64},
            "Registry-sets should accept the measured complete Character inventory");
  expect_eq(iee::creature_sprite_x2::kMaximumRegistrySetBytes,
            std::uint64_t{8} * 1024u * 1024u * 1024u,
            "Registry-set aggregate bytes should be bounded at 8 GiB");
  expect_eq(iee::creature_sprite_x2::kLazyIndexCacheBudgetBytes,
            std::uint64_t{128} * 1024u * 1024u,
            "Lazy frame indices should retain a 128 MiB resident budget");
  expect_eq(iee::creature_sprite_x2::kCatalogMetadataCacheBudgetBytes,
            std::uint64_t{128} * 1024u * 1024u,
            "On-demand catalog metadata should have an independent 128 MiB LRU budget");
  expect_true(iee::creature_sprite_x2::kRegistryFrameCodecRaw == 0 &&
                  iee::creature_sprite_x2::kRegistryFrameCodecXpressHuff == 1,
              "Registry V5 frame codec ids should retain their format-level values");
  expect_eq(iee::creature_sprite_x2::kMaximumCatalogDirectoryEntries,
            std::uint32_t{1'048'576},
            "Catalog V2 should bound its authenticated resref directory");
  expect_true(
      iee::creature_sprite_x2::kMaximumCatalogAnimations == 512 &&
          iee::creature_sprite_x2::kMaximumCatalogComponents == 16'384 &&
          iee::creature_sprite_x2::kMaximumCatalogMemberships == 262'144 &&
          iee::creature_sprite_x2::kMaximumCatalogShards == 16'384 &&
          iee::creature_sprite_x2::kMaximumCatalogResources == 32'768 &&
          iee::creature_sprite_x2::kMaximumCatalogFrames == 4'194'304 &&
          iee::creature_sprite_x2::kMaximumCatalogRegistryBytes ==
              std::uint64_t{128} * 1024u * 1024u * 1024u,
      "Catalog counts and aggregate bytes should retain their bounded V1 contract");

  // A catalog owns its animation-to-component relations independently and has
  // strict priority over valid registry-set and monolithic fallbacks.
  write_file(legacyPath, make_registry(legacyMagic, 2, 2, 0xE400));
  write_file(xnPath, make_registry(xnMagic, 3, 4, 0x6220));
  const auto catalogCharacter = [&] {
    TestShard shard;
    shard.registry = make_registry(xnMagic, 3, 4, 0xFFFFu, 1, 0, 'C');
    // Keep a second palette representative valid so the later 1 -> 2 payload
    // substitution can only be rejected by the retained payload digest.
    shard.registry[92] = std::byte{0};
    shard.registry[93] = std::byte{0};
    shard.resourceCount = 1;
    shard.frameCount = 1;
    shard.indexBytes = 16;
    shard.sha256 = test_sha256(shard.registry);
    return shard;
  }();
  const auto catalogMonster = [&] {
    TestShard shard;
    shard.registry = make_registry(xnMagic, 3, 4, 0xFFFFu, 1, 0, 'M');
    shard.resourceCount = 1;
    shard.frameCount = 1;
    shard.indexBytes = 16;
    shard.sha256 = test_sha256(shard.registry);
    return shard;
  }();
  const std::vector<TestCatalogAnimation> catalogAnimations{
      {0x6110, 1, {0}},
      {0xE400, 2, {1}},
  };
  auto catalogCharacterResref = target;
  catalogCharacterResref[0] = 'C';
  auto catalogMonsterResref = target;
  catalogMonsterResref[0] = 'M';

  const auto prioritySetShard = make_shard(4, 'S');
  write_set_case(4, {prioritySetShard});
  write_catalog_case(4, catalogAnimations, {catalogCharacter, catalogMonster});
  expect_eq(make_catalog(4, catalogAnimations,
                         {catalogCharacter, catalogMonster}).size(),
            std::size_t{376},
            "A two-animation catalog should retain its exact fixed-record layout");
  expect_true(iee::creature_sprite_x2::prepare(root),
              "A valid multi-animation catalog should load atomically");
  expect_true(iee::creature_sprite_x2::loaded_scale() == 4 &&
                  iee::creature_sprite_x2::target_animation_id() == 0 &&
                  iee::creature_sprite_x2::contains_animation(0x6110) &&
                  iee::creature_sprite_x2::contains_animation(0xE400) &&
                  !iee::creature_sprite_x2::contains_animation(0x6220) &&
                  iee::creature_sprite_x2::animation_targets_character(0x6110) &&
                  !iee::creature_sprite_x2::animation_targets_monster(0x6110) &&
                  !iee::creature_sprite_x2::animation_targets_monster_icewind(0x6110) &&
                  iee::creature_sprite_x2::animation_targets_monster_icewind(0xE400) &&
                  !iee::creature_sprite_x2::animation_targets_monster(0xE400) &&
                  !iee::creature_sprite_x2::animation_targets_character(0xE400) &&
                  iee::creature_sprite_x2::targets_character() &&
                  !iee::creature_sprite_x2::targets_monster() &&
                  iee::creature_sprite_x2::targets_monster_icewind(),
              "A mixed-owner catalog should expose both owners and no ambiguous legacy id");
  expect_true(
      await([&] {
        return iee::creature_sprite_x2::contains_resource(
            0x6110, catalogCharacterResref);
      }) &&
          !iee::creature_sprite_x2::contains_resource(
              0x6110, catalogMonsterResref) &&
          await([&] {
            return iee::creature_sprite_x2::contains_resource(
                0xE400, catalogMonsterResref);
          }) &&
          !iee::creature_sprite_x2::contains_resource(
              0xE400, catalogCharacterResref),
      "Catalog membership should isolate each animation's resource mapping");
  expect_eq(iee::creature_sprite_x2::resident_index_bytes(), std::uint64_t{0},
            "Catalog prepare should leave every shard payload lazy");
  iee::creature_sprite_x2::FrameHandle characterHandle{};
  iee::creature_sprite_x2::FrameHandle monsterHandle{};
  expect_true(
      await([&] {
        return iee::creature_sprite_x2::resolve_frame(
            0x6110, catalogCharacterResref, 0, 0, characterHandle);
      }) &&
          await([&] {
            return iee::creature_sprite_x2::resolve_frame(
                0xE400, catalogMonsterResref, 0, 0, monsterHandle);
          }) &&
          iee::creature_sprite_x2::ensure_frame_payload_available(characterHandle) &&
          iee::creature_sprite_x2::ensure_frame_payload_available(monsterHandle) &&
          !iee::creature_sprite_x2::resolve_frame(
              0x6110, catalogMonsterResref, 0, 0, monsterHandle),
      "The multi-animation resolver should remain scoped to catalog membership");
  expect_eq(iee::creature_sprite_x2::resident_index_bytes(), std::uint64_t{32},
            "Resolving two x4 catalog shards should cache only their frame payloads");
  auto setOnlyResref = target;
  setOnlyResref[0] = 'S';
  expect_true(!iee::creature_sprite_x2::contains_resource(0x6110, setOnlyResref),
              "A valid catalog should take priority over a valid registry-set");

  auto changedCatalog =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  changedCatalog.push_back(std::byte{0});
  const auto changedCatalogWritten = write_file(catalogPath, changedCatalog);
  expect_true(!changedCatalogWritten &&
                  iee::creature_sprite_x2::contains_animation(0x6110) &&
                  iee::creature_sprite_x2::ready(),
              "The active catalog read lease should reject replacement and keep "
              "validated mappings stable");
  iee::creature_sprite_x2::release();

  const std::vector<TestCatalogDirectoryEntry> catalogV2Directory{
      {0x6110, catalogCharacterResref, 0, 0, 0},
      {0xE400, catalogMonsterResref, 1, 1, 0},
  };
  const auto catalogV2 = make_catalog_v2(
      4, catalogAnimations, {catalogCharacter, catalogMonster},
      catalogV2Directory);
  expect_eq(catalogV2.size(), std::size_t{464},
            "Catalog V2 should add one authenticated 40-byte directory header "
            "and two 24-byte entries");
  write_file(catalogPath, catalogV2);
  write_file(root / digest_filename(catalogMonster.sha256),
             catalogMonster.registry);
  std::filesystem::remove(root / digest_filename(catalogCharacter.sha256), ec);
  expect_true(iee::creature_sprite_x2::prepare(root) &&
                  iee::creature_sprite_x2::resident_index_bytes() == 0 &&
                  iee::creature_sprite_x2::resident_catalog_metadata_bytes() == 0,
              "Catalog V2 startup should validate only its authenticated directory "
              "and must not open every V3 shard");
  bool absentBurstRejected = true;
  constexpr std::array<char, 16> hexDigits{{
      '0', '1', '2', '3', '4', '5', '6', '7',
      '8', '9', 'A', 'B', 'C', 'D', 'E', 'F',
  }};
  for (std::uint32_t index = 0; index < 4096; ++index) {
    auto absent = target;
    absent[0] = 'N';
    absent[1] = hexDigits[(index >> 8u) & 0xFu];
    absent[2] = hexDigits[(index >> 4u) & 0xFu];
    absent[3] = hexDigits[index & 0xFu];
    iee::creature_sprite_x2::FrameHandle absentHandle{};
    absentBurstRejected &=
        !iee::creature_sprite_x2::contains_resource(0x6110, absent) &&
        !iee::creature_sprite_x2::resolve_frame(
            0x6110, absent, 0, 0, absentHandle);
  }
  expect_true(absentBurstRejected &&
                  iee::creature_sprite_x2::pending_catalog_loads() == 0 &&
                  iee::creature_sprite_x2::resident_catalog_metadata_bytes() == 0 &&
                  iee::creature_sprite_x2::resident_index_bytes() == 0,
              "Catalog V2 should reject an absent-resref burst with no queue, "
              "negative cache, shard scan, or resident growth");
  iee::creature_sprite_x2::FrameHandle v2MonsterHandle{};
  expect_true(await([&] {
                return iee::creature_sprite_x2::resolve_frame(
                    0xE400, catalogMonsterResref, 0, 0, v2MonsterHandle);
              }) &&
                  iee::creature_sprite_x2::resident_catalog_metadata_bytes() > 0 &&
                  iee::creature_sprite_x2::resident_catalog_metadata_bytes() <=
                      iee::creature_sprite_x2::kCatalogMetadataCacheBudgetBytes,
              "Catalog V2 should resolve one resref by loading only its indexed shard");
  (void)iee::creature_sprite_x2::contains_resource(
      0x6110, catalogCharacterResref);
  expect_true(await([&] {
                return iee::creature_sprite_x2::pending_catalog_loads() == 0;
              }) &&
                  !iee::creature_sprite_x2::contains_resource(
                      0x6110, catalogCharacterResref) &&
                  iee::creature_sprite_x2::resolve_frame(
                      0xE400, catalogMonsterResref, 0, 0, v2MonsterHandle) &&
                  iee::creature_sprite_x2::ready(),
              "A missing V2 component should be quarantined without disabling an "
              "already validated animation");
  iee::creature_sprite_x2::release();

  auto invalidV2Digest = catalogV2;
  invalidV2Digest[72] ^= std::byte{1};
  write_file(catalogPath, invalidV2Digest);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "Catalog V2 should reject a modified resource directory digest");
  auto invalidV2RelationEntries = catalogV2Directory;
  invalidV2RelationEntries[0].componentIndex = 1;
  invalidV2RelationEntries[0].shardIndex = 1;
  write_file(catalogPath,
             make_catalog_v2(4, catalogAnimations,
                             {catalogCharacter, catalogMonster},
                             invalidV2RelationEntries));
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "Catalog V2 should reject an authenticated directory target whose "
              "component is not a member of the animation");
  write_file(root / digest_filename(catalogCharacter.sha256),
             catalogCharacter.registry);

  // V5 keeps V3's metadata layout but stores each frame independently. The
  // authenticated V2 directory routes directly to a shard, so startup and
  // resolution never have to inflate the rest of an animation.
  const auto write_v5_catalog_case = [&](std::uint32_t scale,
                                          const TestShard& shard,
                                          char marker) {
    auto resref = target;
    resref[0] = marker;
    const std::vector<TestCatalogAnimation> animations{
        {0x6110, 1, {0}},
    };
    const std::vector<TestCatalogDirectoryEntry> directory{
        {0x6110, resref, 0, 0, 0},
    };
    write_file(catalogPath,
               make_catalog_v2(scale, animations, {shard}, directory));
    write_file(root / digest_filename(shard.sha256), shard.registry);
    return resref;
  };
  const std::vector<std::uint8_t> v5LogicalX2(32u * 32u * 4u, 1);
  const auto v5StoredX2 = compress_xpress_huff(v5LogicalX2);
  expect_true(!v5StoredX2.empty() && v5StoredX2.size() < v5LogicalX2.size(),
              "The V5 x2 test frame should have a canonical XPRESS_HUFF payload");
  const auto v5X2 = make_v5_shard(
      2, 'P', 32, 32,
      iee::creature_sprite_x2::kRegistryFrameCodecXpressHuff,
      v5StoredX2, 2);
  const auto v5X2Resref = write_v5_catalog_case(2, v5X2, 'P');
  iee::creature_sprite_x2::FrameHandle v5X2First{};
  iee::creature_sprite_x2::FrameHandle v5X2Second{};
  expect_true(
      iee::creature_sprite_x2::prepare(root) &&
          iee::creature_sprite_x2::loaded_scale() == 2 &&
          iee::creature_sprite_x2::resident_index_bytes() == 0 &&
          await([&] {
            return iee::creature_sprite_x2::resolve_frame(
                0x6110, v5X2Resref, 0, 0, v5X2First);
          }) &&
          iee::creature_sprite_x2::resident_index_bytes() == 0 &&
          iee::creature_sprite_x2::ensure_frame_payload_available(v5X2First) &&
          iee::creature_sprite_x2::resident_index_bytes() ==
              v5LogicalX2.size() &&
          iee::creature_sprite_x2::resolve_frame(
              0x6110, v5X2Resref, 0, 1, v5X2Second) &&
          iee::creature_sprite_x2::resident_index_bytes() ==
              v5LogicalX2.size() &&
          iee::creature_sprite_x2::ensure_frame_payload_available(v5X2Second) &&
          iee::creature_sprite_x2::resident_index_bytes() ==
              v5LogicalX2.size() * 2 &&
          iee::creature_sprite_x2::resident_index_bytes() <=
              iee::creature_sprite_x2::kLazyIndexCacheBudgetBytes,
      "V5 x2 should decompress exactly one requested frame into the bounded LRU");
  const auto hotFilesystemAccesses =
      iee::creature_sprite_x2::filesystem_access_count();
  bool hotFrameStayedResident = true;
  for (std::uint32_t iteration = 0; iteration < 512; ++iteration) {
    iee::creature_sprite_x2::FrameHandle hotHandle{};
    hotFrameStayedResident &=
        iee::creature_sprite_x2::contains_resource(0x6110, v5X2Resref) &&
        iee::creature_sprite_x2::resolve_frame(
            0x6110, v5X2Resref, 0, 0, hotHandle) &&
        iee::creature_sprite_x2::ensure_frame_payload_available(hotHandle);
  }
  expect_true(hotFrameStayedResident &&
                  iee::creature_sprite_x2::filesystem_access_count() ==
                      hotFilesystemAccesses,
              "A hot V5 frame should perform zero catalog stat/open or shard reread");
  iee::creature_sprite_x2::release();

  const std::vector<std::uint8_t> v5LogicalX4(16u * 16u * 16u, 1);
  const auto v5StoredX4 = compress_xpress_huff(v5LogicalX4);
  expect_true(!v5StoredX4.empty() && v5StoredX4.size() < v5LogicalX4.size(),
              "The V5 x4 test frame should have a canonical XPRESS_HUFF payload");
  const auto v5X4 = make_v5_shard(
      4, 'Q', 16, 16,
      iee::creature_sprite_x2::kRegistryFrameCodecXpressHuff,
      v5StoredX4);
  const auto v5X4Resref = write_v5_catalog_case(4, v5X4, 'Q');
  iee::creature_sprite_x2::FrameHandle v5X4Handle{};
  expect_true(
      iee::creature_sprite_x2::prepare(root) &&
          iee::creature_sprite_x2::loaded_scale() == 4 &&
          await([&] {
            return iee::creature_sprite_x2::resolve_frame(
                0x6110, v5X4Resref, 0, 0, v5X4Handle);
          }) &&
          iee::creature_sprite_x2::resident_index_bytes() == 0 &&
          iee::creature_sprite_x2::ensure_frame_payload_available(v5X4Handle) &&
          iee::creature_sprite_x2::resident_index_bytes() ==
              v5LogicalX4.size(),
      "V5 should support independently compressed x4 catalog frames");
  iee::creature_sprite_x2::release();

  const std::vector<std::uint8_t> v5RawIndices(16u * 16u * 4u, 1);
  const auto v5Raw = make_v5_shard(
      2, 'R', 16, 16,
      iee::creature_sprite_x2::kRegistryFrameCodecRaw, v5RawIndices);
  const auto v5RawResref = write_v5_catalog_case(2, v5Raw, 'R');
  iee::creature_sprite_x2::FrameHandle v5RawHandle{};
  expect_true(
      iee::creature_sprite_x2::prepare(root) &&
          await([&] {
            return iee::creature_sprite_x2::resolve_frame(
                0x6110, v5RawResref, 0, 0, v5RawHandle);
          }) &&
          iee::creature_sprite_x2::ensure_frame_payload_available(v5RawHandle) &&
          iee::creature_sprite_x2::resident_index_bytes() ==
              v5RawIndices.size(),
      "V5 codec 0 should retain an exact raw-frame fallback");
  iee::creature_sprite_x2::release();

  // Digest verification is over stored bytes, before decompression, even when
  // a same-size replacement preserves the weak file identity.
  write_v5_catalog_case(4, v5X4, 'Q');
  expect_true(iee::creature_sprite_x2::prepare(root),
              "V5 should prepare before stored-block identity testing");
  iee::creature_sprite_x2::FrameHandle changedV5Handle{};
  expect_true(await([&] {
                return iee::creature_sprite_x2::resolve_frame(
                    0x6110, v5X4Resref, 0, 0, changedV5Handle);
              }),
              "V5 metadata should resolve before its payload is materialized");
  const auto v5X4Path = root / digest_filename(v5X4.sha256);
  const auto v5X4Stamp = std::filesystem::last_write_time(v5X4Path);
  auto changedV5Registry = v5X4.registry;
  changedV5Registry[600] ^= std::byte{1};
  const auto changedV5Written = write_file(v5X4Path, changedV5Registry);
  std::filesystem::last_write_time(v5X4Path, v5X4Stamp);
  expect_true(!changedV5Written &&
                  iee::creature_sprite_x2::ensure_frame_payload_available(
                      changedV5Handle) &&
                  iee::creature_sprite_x2::ready(),
              "A resident V5 shard lease should reject payload replacement and "
              "retain its validated frame");
  iee::creature_sprite_x2::release();
  write_file(v5X4Path, v5X4.registry);

  // A fully rehashed but malformed compressed stream reaches the decoder and
  // must still fail closed; compressed palette representatives are checked on
  // the exact decompressed output.
  const std::vector<std::uint8_t> malformedV5Stored(v5StoredX4.size(), 0);
  const auto malformedV5 = make_v5_shard(
      4, 'U', 16, 16,
      iee::creature_sprite_x2::kRegistryFrameCodecXpressHuff,
      malformedV5Stored);
  auto malformedV5Resref = target;
  malformedV5Resref[0] = 'U';
  const std::vector<TestCatalogAnimation> isolatedV5Animation{
      {0x6110, 1, {0, 1}},
  };
  const std::vector<TestCatalogDirectoryEntry> isolatedV5Directory{
      {0x6110, v5X4Resref, 0, 0, 0},
      {0x6110, malformedV5Resref, 1, 1, 0},
  };
  write_file(catalogPath,
             make_catalog_v2(4, isolatedV5Animation,
                             {v5X4, malformedV5}, isolatedV5Directory));
  write_file(root / digest_filename(v5X4.sha256), v5X4.registry);
  write_file(root / digest_filename(malformedV5.sha256),
             malformedV5.registry);
  iee::creature_sprite_x2::FrameHandle survivingV5Handle{};
  iee::creature_sprite_x2::FrameHandle malformedV5Handle{};
  expect_true(
      iee::creature_sprite_x2::prepare(root) &&
          await([&] {
            return iee::creature_sprite_x2::resolve_frame(
                0x6110, v5X4Resref, 0, 0, survivingV5Handle);
          }) &&
          iee::creature_sprite_x2::ensure_frame_payload_available(
              survivingV5Handle) &&
          await([&] {
            return iee::creature_sprite_x2::resolve_frame(
                0x6110, malformedV5Resref, 0, 0, malformedV5Handle);
          }) &&
          !iee::creature_sprite_x2::ensure_frame_payload_available(
              malformedV5Handle) &&
          iee::creature_sprite_x2::resident_index_bytes() ==
              v5LogicalX4.size() &&
          iee::creature_sprite_x2::ensure_frame_payload_available(
              survivingV5Handle) &&
          iee::creature_sprite_x2::ready(),
      "Malformed XPRESS_HUFF bytes should quarantine only their shard and "
      "preserve an unrelated frame cache");
  iee::creature_sprite_x2::release();

  const std::vector<std::uint8_t> unrepresentedLogical(v5LogicalX2.size(), 2);
  const auto unrepresentedStored = compress_xpress_huff(unrepresentedLogical);
  const auto unrepresentedV5 = make_v5_shard(
      2, 'V', 32, 32,
      iee::creature_sprite_x2::kRegistryFrameCodecXpressHuff,
      unrepresentedStored);
  const auto unrepresentedResref =
      write_v5_catalog_case(2, unrepresentedV5, 'V');
  iee::creature_sprite_x2::FrameHandle unrepresentedHandle{};
  expect_true(
      iee::creature_sprite_x2::prepare(root) &&
          await([&] {
            return iee::creature_sprite_x2::resolve_frame(
                0x6110, unrepresentedResref, 0, 0,
                unrepresentedHandle);
          }) &&
          !iee::creature_sprite_x2::ensure_frame_payload_available(
              unrepresentedHandle) &&
          iee::creature_sprite_x2::ready(),
      "V5 should validate palette representatives after decompression");
  iee::creature_sprite_x2::release();

  const auto expect_v5_metadata_quarantine = [&](const TestShard& shard,
                                                  std::uint32_t scale,
                                                  char marker) {
    const auto resref = write_v5_catalog_case(scale, shard, marker);
    if (!iee::creature_sprite_x2::prepare(root)) return false;
    (void)iee::creature_sprite_x2::contains_resource(0x6110, resref);
    const auto quarantined = await([&] {
      return iee::creature_sprite_x2::pending_catalog_loads() == 0;
    }) && !iee::creature_sprite_x2::contains_resource(0x6110, resref) &&
        iee::creature_sprite_x2::ready();
    iee::creature_sprite_x2::release();
    return quarantined;
  };
  const auto unknownCodecV5 = make_v5_shard(2, 'W', 32, 32, 2,
                                             v5StoredX2);
  expect_true(expect_v5_metadata_quarantine(unknownCodecV5, 2, 'W'),
              "V5 should quarantine an unknown frame codec on demand");
  const auto reservedV5 = make_v5_shard(
      2, 'X', 32, 32,
      iee::creature_sprite_x2::kRegistryFrameCodecXpressHuff,
      v5StoredX2, 1, std::nullopt,
      {std::byte{1}, std::byte{0}});
  expect_true(expect_v5_metadata_quarantine(reservedV5, 2, 'X'),
              "V5 should reject nonzero reserved frame bytes");
  const auto noncanonicalCompressedV5 = make_v5_shard(
      2, 'Y', 32, 32,
      iee::creature_sprite_x2::kRegistryFrameCodecXpressHuff,
      v5LogicalX2);
  expect_true(expect_v5_metadata_quarantine(noncanonicalCompressedV5, 2, 'Y'),
              "V5 XPRESS_HUFF storage must be smaller than its logical frame");
  const auto shortRawV5 = make_v5_shard(
      2, 'Z', 32, 32,
      iee::creature_sprite_x2::kRegistryFrameCodecRaw, v5StoredX2);
  expect_true(expect_v5_metadata_quarantine(shortRawV5, 2, 'Z'),
              "V5 raw storage must exactly match its logical frame size");
  const auto truncatedV5 = make_v5_shard(
      2, 'J', 32, 32,
      iee::creature_sprite_x2::kRegistryFrameCodecXpressHuff,
      v5StoredX2, 1,
      static_cast<std::uint32_t>(v5StoredX2.size() + 1024));
  expect_true(expect_v5_metadata_quarantine(truncatedV5, 2, 'J'),
              "V5 should quarantine a truncated stored frame range");
  const std::vector<std::uint8_t> oneStoredByte{1};
  const auto bombV5 = make_v5_shard(
      4, 'K', 3000, 3000,
      iee::creature_sprite_x2::kRegistryFrameCodecXpressHuff,
      oneStoredByte);
  expect_true(expect_v5_metadata_quarantine(bombV5, 4, 'K'),
              "V5 should reject a decompression bomb above the frame-cache bound "
              "before allocation");
  const auto oversizedV5 = make_v5_shard(
      4, 'L', 65535, 65535,
      iee::creature_sprite_x2::kRegistryFrameCodecXpressHuff,
      oneStoredByte);
  write_v5_catalog_case(4, oversizedV5, 'L');
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "V5 logical byte totals above the scale-specific shard bound should "
              "fail at catalog validation");

  // V5 is intentionally unavailable through legacy monolith/set discovery;
  // those paths keep their V3/V4 contracts and cannot bypass Catalog V2.
  write_file(catalogPath,
             make_catalog(2, {{0x6110, 1, {0}}}, {v5X2}));
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A Catalog V1 manifest must reject compressed logical/physical totals");
  std::filesystem::remove(catalogPath, ec);
  std::filesystem::remove(setPath, ec);
  write_file(xnPath, v5Raw.registry);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A V5 registry must never activate as a monolith");
  write_set_case(2, {v5Raw});
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A V5 registry must never activate through a standard registry-set");
  std::filesystem::remove(setPath, ec);

  write_file(catalogPath,
             make_grouped_component_catalog(
                 4, 0x6110, 1, {catalogCharacter, catalogMonster}));
  write_file(root / digest_filename(catalogCharacter.sha256),
             catalogCharacter.registry);
  write_file(root / digest_filename(catalogMonster.sha256),
             catalogMonster.registry);
  expect_true(
      iee::creature_sprite_x2::prepare(root) &&
          iee::creature_sprite_x2::target_animation_id() == 0x6110 &&
          await([&] {
            return iee::creature_sprite_x2::contains_resource(
                0x6110, catalogCharacterResref);
          }) &&
          await([&] {
            return iee::creature_sprite_x2::contains_resource(
                0x6110, catalogMonsterResref);
          }),
      "One catalog component should bind multiple ordered shards to one animation");
  iee::creature_sprite_x2::release();

  const auto catalogX2 = [&] {
    TestShard shard;
    shard.registry = make_registry(xnMagic, 3, 2, 0xFFFFu, 1, 0, 'X');
    shard.resourceCount = 1;
    shard.frameCount = 1;
    shard.indexBytes = 4;
    shard.sha256 = test_sha256(shard.registry);
    return shard;
  }();
  auto catalogX2Resref = target;
  catalogX2Resref[0] = 'X';
  write_file(catalogPath,
             make_grouped_component_catalog(2, 0x6110, 1, {catalogX2}));
  write_file(root / digest_filename(catalogX2.sha256), catalogX2.registry);
  iee::creature_sprite_x2::FrameHandle catalogX2Handle{};
  expect_true(
      iee::creature_sprite_x2::prepare(root) &&
          iee::creature_sprite_x2::loaded_scale() == 2 &&
          await([&] {
            return iee::creature_sprite_x2::resolve_frame(
                0x6110, catalogX2Resref, 0, 0, catalogX2Handle);
          }) &&
          iee::creature_sprite_x2::ensure_frame_payload_available(
              catalogX2Handle) &&
          iee::creature_sprite_x2::resident_index_bytes() == 4,
      "A single-animation x2 catalog should preserve compatibility and lazy payloads");
  iee::creature_sprite_x2::release();

  const std::vector<TestCatalogAnimation> sharedComponentAnimations{
      {0x6110, 1, {0}},
      {0xE400, 2, {0}},
  };
  write_catalog_case(4, sharedComponentAnimations, {catalogCharacter});
  expect_true(
      iee::creature_sprite_x2::prepare(root) &&
          await([&] {
            return iee::creature_sprite_x2::contains_resource(
                0x6110, catalogCharacterResref);
          }) &&
          await([&] {
            return iee::creature_sprite_x2::contains_resource(
                0xE400, catalogCharacterResref);
          }),
      "Two animations should be allowed to share one immutable component");
  iee::creature_sprite_x2::FrameHandle sharedCharacterHandle{};
  iee::creature_sprite_x2::FrameHandle sharedMonsterHandle{};
  expect_true(
      await([&] {
        return iee::creature_sprite_x2::resolve_frame(
            0x6110, catalogCharacterResref, 0, 0, sharedCharacterHandle);
      }) &&
          await([&] {
            return iee::creature_sprite_x2::resolve_frame(
                0xE400, catalogCharacterResref, 0, 0,
                sharedMonsterHandle);
          }) &&
          sharedCharacterHandle.animationId == 0x6110 &&
          sharedMonsterHandle.animationId == 0xE400 &&
          sharedCharacterHandle.resourceIndex ==
              sharedMonsterHandle.resourceIndex &&
          sharedCharacterHandle.frameIndex == sharedMonsterHandle.frameIndex &&
          sharedCharacterHandle != sharedMonsterHandle,
      "A shared resref/frame should retain distinct animation-scoped handles for QA");
  iee::creature_sprite_x2::FrameHandle changedShardHandle{};
  expect_true(await([&] {
                return iee::creature_sprite_x2::resolve_frame(
                    0x6110, catalogCharacterResref, 0, 0,
                    changedShardHandle);
              }),
              "A shared catalog component should resolve before identity testing");
  const auto activeShardPath =
      root / digest_filename(catalogCharacter.sha256);
  const auto activeShardStamp = std::filesystem::last_write_time(activeShardPath);
  auto changedActiveShard = catalogCharacter.registry;
  changedActiveShard[changedActiveShard.size() - 9] = std::byte{2};
  const auto changedActiveShardWritten =
      write_file(activeShardPath, changedActiveShard);
  std::filesystem::last_write_time(activeShardPath, activeShardStamp);
  expect_true(
      !changedActiveShardWritten &&
          std::filesystem::file_size(activeShardPath) ==
              catalogCharacter.registry.size() &&
          std::filesystem::last_write_time(activeShardPath) == activeShardStamp,
      "A resident catalog shard lease should reject same-identity replacement");
  expect_true(iee::creature_sprite_x2::ensure_frame_payload_available(
                  changedShardHandle) &&
                   iee::creature_sprite_x2::ready(),
               "A blocked shard replacement should preserve the validated lazy frame");
  iee::creature_sprite_x2::release();
  write_file(activeShardPath, catalogCharacter.registry);

  // Component materialization rechecks the whole shard cryptographically,
  // even when an attacker preserves the size/mtime identity used by polling.
  expect_true(iee::creature_sprite_x2::prepare(root),
              "The catalog should prepare before the materialization mutation test");
  const auto materializationStamp =
      std::filesystem::last_write_time(activeShardPath);
  auto changedBeforeMaterialization = catalogCharacter.registry;
  changedBeforeMaterialization[32] ^= std::byte{1};
  write_file(activeShardPath, changedBeforeMaterialization);
  std::filesystem::last_write_time(activeShardPath, materializationStamp);
  (void)iee::creature_sprite_x2::contains_resource(
      0x6110, catalogCharacterResref);
  expect_true(
      await([&] {
        return iee::creature_sprite_x2::pending_catalog_loads() == 0;
      }) &&
          std::filesystem::last_write_time(activeShardPath) ==
              materializationStamp &&
          !iee::creature_sprite_x2::contains_resource(
              0x6110, catalogCharacterResref) &&
          iee::creature_sprite_x2::ready(),
      "A same-size, same-timestamp shard mutation should fail SHA-256/CRC-32 "
      "revalidation before component materialization");
  iee::creature_sprite_x2::release();
  write_file(activeShardPath, catalogCharacter.registry);

  const auto animationBytes = catalogAnimations.size() * 16;
  const auto membershipBytes = std::size_t{2} * sizeof(std::uint32_t);
  const auto componentTableOffset = std::size_t{64} + animationBytes + membershipBytes;
  const auto shardTableOffset = componentTableOffset + std::size_t{2} * 72;

  auto duplicateResrefShard = catalogCharacter;
  duplicateResrefShard.registry[32] ^= std::byte{1};
  duplicateResrefShard.sha256 = test_sha256(duplicateResrefShard.registry);
  const std::vector<TestCatalogAnimation> duplicateResrefAnimation{
      {0x6110, 1, {0, 1}},
  };
  write_catalog_case(4, duplicateResrefAnimation,
                     {catalogCharacter, duplicateResrefShard});
  expect_true(iee::creature_sprite_x2::prepare(root),
              "A V1 catalog should activate without scanning duplicate shard content");
  (void)iee::creature_sprite_x2::contains_resource(
      0x6110, catalogCharacterResref);
  expect_true(await([&] {
                return iee::creature_sprite_x2::pending_catalog_loads() == 0;
              }) &&
                  !iee::creature_sprite_x2::contains_resource(
                      0x6110, catalogCharacterResref) &&
                  iee::creature_sprite_x2::ready(),
              "A duplicate V1 resref should quarantine only its components on demand");
  iee::creature_sprite_x2::release();

  const auto catalogGenericMonster = [&] {
    TestShard shard;
    shard.registry = make_registry(xnMagic, 3, 4, 0xFFFFu, 1, 0, 'G');
    shard.resourceCount = 1;
    shard.frameCount = 1;
    shard.indexBytes = 16;
    shard.sha256 = test_sha256(shard.registry);
    return shard;
  }();
  const std::vector<TestCatalogAnimation> genericMonsterAnimation{
      {0x7F07, 3, {0}},
  };
  auto genericMonsterResref = target;
  genericMonsterResref[0] = 'G';
  write_catalog_case(4, genericMonsterAnimation, {catalogGenericMonster});
  expect_true(
      iee::creature_sprite_x2::prepare(root) &&
          iee::creature_sprite_x2::contains_animation(0x7F07) &&
          iee::creature_sprite_x2::animation_targets_monster(0x7F07) &&
          !iee::creature_sprite_x2::animation_targets_character(0x7F07) &&
          !iee::creature_sprite_x2::animation_targets_monster_icewind(0x7F07) &&
          iee::creature_sprite_x2::targets_monster() &&
          !iee::creature_sprite_x2::targets_character() &&
          !iee::creature_sprite_x2::targets_monster_icewind() &&
          await([&] {
            return iee::creature_sprite_x2::contains_resource(
                0x7F07, genericMonsterResref);
          }),
      "A 0x7000 catalog should select only the generic Monster owner scope");
  iee::creature_sprite_x2::release();
  expect_true(!iee::creature_sprite_x2::targets_monster() &&
                  !iee::creature_sprite_x2::animation_targets_monster(0x7F07),
              "Releasing a generic Monster catalog should clear its owner scope");

  auto invalidOwner =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  overwrite_u32(invalidOwner, 64 + sizeof(std::uint32_t), 4);
  write_file(catalogPath, invalidOwner);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "An unknown catalog owner should fail closed");

  auto wrongFamilyOwner =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  overwrite_u32(wrongFamilyOwner, 64 + sizeof(std::uint32_t), 2);
  write_file(catalogPath, wrongFamilyOwner);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A MonsterIcewind owner on a Character animation family should fail "
              "closed");

  auto wrongGenericMonsterFamilyOwner =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  overwrite_u32(wrongGenericMonsterFamilyOwner,
                64 + sizeof(std::uint32_t), 3);
  write_file(catalogPath, wrongGenericMonsterFamilyOwner);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A generic Monster owner on a Character animation family should fail "
              "closed");

  const std::vector<TestCatalogAnimation> reversedAnimations{
      {0xE400, 2, {1}},
      {0x6110, 1, {0}},
  };
  write_catalog_case(4, reversedAnimations,
                     {catalogCharacter, catalogMonster});
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "Catalog animation ids should be strictly increasing");

  auto permutedMembershipRanges =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  overwrite_u32(permutedMembershipRanges, 64 + 8, 1);
  overwrite_u32(permutedMembershipRanges, 64 + 16 + 8, 0);
  write_file(catalogPath, permutedMembershipRanges);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "Animation membership ranges should be one canonical ordered partition");

  const std::vector<TestCatalogAnimation> permutedMemberships{
      {0x6110, 1, {1, 0}},
  };
  write_catalog_case(4, permutedMemberships,
                     {catalogCharacter, catalogMonster});
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "Component memberships should be sorted, unique, and canonical");

  auto duplicateAnimationId =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  overwrite_u32(duplicateAnimationId, 64 + 16, 0x6110);
  write_file(catalogPath, duplicateAnimationId);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A duplicate catalog animation id should fail closed");

  auto permutedShardRanges =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  overwrite_u32(permutedShardRanges, componentTableOffset + 32, 1);
  overwrite_u32(permutedShardRanges, componentTableOffset + 72 + 32, 0);
  write_file(catalogPath, permutedShardRanges);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "Component shard ranges should form one canonical ordered partition");

  auto invalidRelation =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  overwrite_u32(invalidRelation, 64 + animationBytes, 2);
  write_file(catalogPath, invalidRelation);
  expect_true(!iee::creature_sprite_x2::prepare(root) &&
                  !iee::creature_sprite_x2::ready(),
              "An out-of-range catalog membership should fail closed without using the set");

  auto invalidComponentHash =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  invalidComponentHash[componentTableOffset] ^= std::byte{1};
  write_file(catalogPath, invalidComponentHash);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A catalog component digest mismatch should fail closed");

  auto invalidCatalogCrc =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  overwrite_u32(invalidCatalogCrc, shardTableOffset + 32,
                test_crc32(catalogCharacter.registry) ^ 1u);
  const auto crcComponentDigest = make_component_digest_from_entry(
      4, invalidCatalogCrc.data() + shardTableOffset, 64);
  std::memcpy(invalidCatalogCrc.data() + componentTableOffset,
              crcComponentDigest.data(), crcComponentDigest.size());
  write_file(catalogPath, invalidCatalogCrc);
  expect_true(iee::creature_sprite_x2::prepare(root),
              "Catalog activation must not hash a shard with a stale CRC");
  (void)iee::creature_sprite_x2::contains_resource(
      0x6110, catalogCharacterResref);
  expect_true(await([&] {
                return iee::creature_sprite_x2::pending_catalog_loads() == 0;
              }) &&
                  !iee::creature_sprite_x2::contains_resource(
                      0x6110, catalogCharacterResref) &&
                  iee::creature_sprite_x2::ready(),
              "A stale shard CRC should fail closed at component scope on demand");
  iee::creature_sprite_x2::release();

  auto changedCatalogShard = catalogCharacter.registry;
  changedCatalogShard[32] ^= std::byte{1};
  auto staleCatalogSha =
      make_catalog(4, catalogAnimations, {catalogCharacter, catalogMonster});
  overwrite_u32(staleCatalogSha, shardTableOffset + 32,
                test_crc32(changedCatalogShard));
  const auto staleShaComponentDigest = make_component_digest_from_entry(
      4, staleCatalogSha.data() + shardTableOffset, 64);
  std::memcpy(staleCatalogSha.data() + componentTableOffset,
              staleShaComponentDigest.data(), staleShaComponentDigest.size());
  write_file(catalogPath, staleCatalogSha);
  write_file(root / digest_filename(catalogCharacter.sha256), changedCatalogShard);
  expect_true(iee::creature_sprite_x2::prepare(root),
              "Catalog activation must remain independent from stale shard SHA bytes");
  (void)iee::creature_sprite_x2::contains_resource(
      0x6110, catalogCharacterResref);
  expect_true(await([&] {
                return iee::creature_sprite_x2::pending_catalog_loads() == 0;
              }) &&
                  !iee::creature_sprite_x2::contains_resource(
                      0x6110, catalogCharacterResref) &&
                  iee::creature_sprite_x2::ready(),
              "A stale shard SHA-256 should quarantine its component on demand");
  iee::creature_sprite_x2::release();

  auto noncanonicalResref = catalogCharacter;
  noncanonicalResref.registry[24 + 5] = static_cast<std::byte>('Q');
  noncanonicalResref.sha256 = test_sha256(noncanonicalResref.registry);
  write_catalog_case(4, catalogAnimations,
                     {noncanonicalResref, catalogMonster});
  expect_true(iee::creature_sprite_x2::prepare(root),
              "Catalog V1 activation should not scan resref padding");
  (void)iee::creature_sprite_x2::contains_resource(
      0x6110, catalogCharacterResref);
  expect_true(await([&] {
                return iee::creature_sprite_x2::pending_catalog_loads() == 0;
              }) &&
                  !iee::creature_sprite_x2::contains_resource(
                      0x6110, catalogCharacterResref),
              "Catalog resrefs should reject nonzero bytes after NUL padding on demand");
  iee::creature_sprite_x2::release();

  auto lowercaseResref = catalogCharacter;
  lowercaseResref.registry[24] = static_cast<std::byte>('c');
  lowercaseResref.sha256 = test_sha256(lowercaseResref.registry);
  write_catalog_case(4, catalogAnimations,
                     {lowercaseResref, catalogMonster});
  expect_true(iee::creature_sprite_x2::prepare(root),
              "Catalog V1 activation should defer resref character validation");
  (void)iee::creature_sprite_x2::contains_resource(
      0x6110, catalogCharacterResref);
  expect_true(await([&] {
                return iee::creature_sprite_x2::pending_catalog_loads() == 0;
              }) &&
                  !iee::creature_sprite_x2::contains_resource(
                      0x6110, catalogCharacterResref),
              "Catalog resrefs should use uppercase BAM characters on demand");
  iee::creature_sprite_x2::release();

  auto emptyCatalogCycle = catalogCharacter;
  emptyCatalogCycle.registry.resize(emptyCatalogCycle.registry.size() -
                                    sizeof(std::uint32_t));
  overwrite_u32(emptyCatalogCycle.registry,
                emptyCatalogCycle.registry.size() - sizeof(std::uint32_t), 0);
  emptyCatalogCycle.sha256 = test_sha256(emptyCatalogCycle.registry);
  write_catalog_case(4, catalogAnimations,
                     {emptyCatalogCycle, catalogMonster});
  expect_true(iee::creature_sprite_x2::prepare(root),
              "Catalog V1 activation should defer cycle validation");
  (void)iee::creature_sprite_x2::contains_resource(
      0x6110, catalogCharacterResref);
  expect_true(await([&] {
                return iee::creature_sprite_x2::pending_catalog_loads() == 0;
              }) &&
                  iee::creature_sprite_x2::contains_resource(
                      0x6110, catalogCharacterResref),
              "Catalog shards should preserve empty native animation cycles");
  iee::creature_sprite_x2::release();

  auto invalidSentinel = catalogCharacter;
  invalidSentinel.registry = make_registry(xnMagic, 3, 4, 0x6110, 1, 0, 'C');
  invalidSentinel.sha256 = test_sha256(invalidSentinel.registry);
  write_catalog_case(4, catalogAnimations, {invalidSentinel, catalogMonster});
  expect_true(iee::creature_sprite_x2::prepare(root),
              "Catalog V1 activation should defer V3 sentinel validation");
  (void)iee::creature_sprite_x2::contains_resource(
      0x6110, catalogCharacterResref);
  expect_true(await([&] {
                return iee::creature_sprite_x2::pending_catalog_loads() == 0;
              }) &&
                  !iee::creature_sprite_x2::contains_resource(
                      0x6110, catalogCharacterResref),
              "A V3 shard without sentinel 0xFFFF should fail closed on demand");
  iee::creature_sprite_x2::release();
  std::filesystem::remove(catalogPath, ec);

  ec.clear();
  std::filesystem::create_symlink(root / "missing-catalog-target", catalogPath,
                                  ec);
  if (!ec) {
    expect_true(!iee::creature_sprite_x2::prepare(root),
                "A dangling catalog symlink should remain present and block fallback");
    iee::creature_sprite_x2::release();
    std::filesystem::remove(catalogPath, ec);
  } else {
    // Windows may deny symlink creation outside Developer Mode. A directory at
    // the same priority path exercises the same present-but-unopenable gate.
    ec.clear();
    std::filesystem::create_directory(catalogPath, ec);
    expect_true(!ec && !iee::creature_sprite_x2::prepare(root),
                "A present non-file catalog entry should block every fallback");
    iee::creature_sprite_x2::release();
    std::filesystem::remove(catalogPath, ec);
  }

  // A valid set has strict priority over both monolithic formats and keeps
  // only metadata resident until a frame payload is requested.
  write_file(legacyPath, make_registry(legacyMagic, 2, 2, 0xE400));
  write_file(xnPath, make_registry(xnMagic, 3, 2, 0x6220));
  const auto x4ShardA = make_shard(4, 'A');
  const auto x4ShardB = make_shard(4, 'B');
  expect_eq(x4ShardA.registry.size(), std::size_t{624},
            "The synthetic x4 shard should retain its exact binary layout");
  constexpr std::array<std::byte, 32> expectedX4ShardAHash{{
      std::byte{0xE1}, std::byte{0x6E}, std::byte{0x97}, std::byte{0x54},
      std::byte{0x68}, std::byte{0xE1}, std::byte{0x3C}, std::byte{0x34},
      std::byte{0xD3}, std::byte{0xA3}, std::byte{0xDD}, std::byte{0x0F},
      std::byte{0x56}, std::byte{0x62}, std::byte{0xC8}, std::byte{0xFF},
      std::byte{0x04}, std::byte{0xBD}, std::byte{0x44}, std::byte{0x86},
      std::byte{0x68}, std::byte{0xDD}, std::byte{0x13}, std::byte{0xD7},
      std::byte{0xF5}, std::byte{0x82}, std::byte{0x7E}, std::byte{0x5A},
      std::byte{0x50}, std::byte{0x0C}, std::byte{0x69}, std::byte{0xB8},
  }};
  expect_true(x4ShardA.sha256 == expectedX4ShardAHash,
              "The registry-set test fixture should use standard SHA-256 bytes");
  expect_eq(test_crc32(x4ShardA.registry), std::uint32_t{0x10F08F54},
            "The registry-set test fixture should use standard IEEE CRC-32");
  expect_eq(make_set(4, {x4ShardA}).size(), std::size_t{120},
            "A one-shard set should be exactly 56 header plus 64 entry bytes");
  expect_eq(make_set(4, {x4ShardA, x4ShardB}).size(), std::size_t{184},
            "Set entries should remain contiguous fixed 64-byte records");
  write_set_case(4, {x4ShardA, x4ShardB});
  auto targetA = target;
  targetA[0] = 'A';
  auto targetB = target;
  targetB[0] = 'B';
  expect_true(iee::creature_sprite_x2::prepare(root),
              "A valid x4 registry-set should load atomically");
  expect_true(iee::creature_sprite_x2::target_animation_id() == 0x6110 &&
                  iee::creature_sprite_x2::loaded_scale() == 4 &&
                  iee::creature_sprite_x2::contains_resource(targetA) &&
                  iee::creature_sprite_x2::contains_resource(targetB),
              "The set should override monolithic registries and expose every shard resref");
  expect_eq(iee::creature_sprite_x2::resident_index_bytes(), std::uint64_t{0},
            "Registry-set prepare should not retain multi-gigabyte frame payloads");
  iee::creature_sprite_x2::FrameHandle lazyHandle{};
  expect_true(iee::creature_sprite_x2::resolve_frame(targetA, 0, 0, lazyHandle) &&
                  iee::creature_sprite_x2::ensure_frame_payload_available(lazyHandle),
              "A set frame should materialize lazily from its owning shard");
  expect_eq(iee::creature_sprite_x2::resident_index_bytes(), std::uint64_t{16},
            "One synthetic x4 frame should occupy only its 16-byte lazy payload");
  ec.clear();
  const auto activeSetShardRemoved =
      std::filesystem::remove(root / "CreatureSprites-XN-0000.registry", ec);
  expect_true(!activeSetShardRemoved && ec &&
                  iee::creature_sprite_x2::ensure_frame_payload_available(lazyHandle) &&
                  iee::creature_sprite_x2::ready() &&
                  iee::creature_sprite_x2::loaded_scale() == 4,
              "A retained set-shard lease should block deletion and preserve its "
              "cached frame");
  iee::creature_sprite_x2::release();
  expect_true(!iee::creature_sprite_x2::ready() &&
                  iee::creature_sprite_x2::loaded_scale() == 0 &&
                  iee::creature_sprite_x2::target_animation_id() == 0 &&
                  iee::creature_sprite_x2::resident_index_bytes() == 0,
              "Releasing a registry-set should clear identity, scale, and lazy payloads");

  write_set_case(4, {x4ShardA});
  expect_true(iee::creature_sprite_x2::prepare(root) &&
                  iee::creature_sprite_x2::resolve_frame(targetA, 0, 0, lazyHandle) &&
                  iee::creature_sprite_x2::ensure_frame_payload_available(lazyHandle),
              "A resolution failure test should materialize a valid cached payload first");
  ec.clear();
  const auto resolvedSetShardRemoved =
      std::filesystem::remove(root / "CreatureSprites-XN-0000.registry", ec);
  iee::creature_sprite_x2::FrameHandle changedSourceHandle{};
  expect_true(!resolvedSetShardRemoved && ec &&
                  iee::creature_sprite_x2::resolve_frame(
                      targetA, 0, 0, changedSourceHandle) &&
                  iee::creature_sprite_x2::ready() &&
                  iee::creature_sprite_x2::loaded_scale() == 4 &&
                  changedSourceHandle != iee::creature_sprite_x2::FrameHandle{},
              "A blocked set-shard deletion should keep new resolutions stable");
  iee::creature_sprite_x2::release();

  const auto x2ShardA = make_shard(2, 'A');
  const auto x2ShardB = make_shard(2, 'B');
  write_set_case(2, {x2ShardA, x2ShardB});
  expect_true(iee::creature_sprite_x2::prepare(root) &&
                  iee::creature_sprite_x2::loaded_scale() == 2,
              "A valid x2 registry-set should share the same atomic lazy path");
  expect_true(iee::creature_sprite_x2::resolve_frame(targetB, 0, 0, lazyHandle) &&
                  iee::creature_sprite_x2::ensure_frame_payload_available(lazyHandle) &&
                  iee::creature_sprite_x2::resident_index_bytes() == 4,
              "An x2 set frame should materialize its exact four-byte payload");
  iee::creature_sprite_x2::release();

  write_set_case(4, {x4ShardA, x4ShardB});
  std::filesystem::remove(root / "CreatureSprites-XN-0001.registry", ec);
  expect_true(!iee::creature_sprite_x2::prepare(root) &&
                  !iee::creature_sprite_x2::ready(),
              "A present set with a missing contiguous shard should fail closed");

  write_set_case(4, {x4ShardA});
  auto crcMismatch = make_set(4, {x4ShardA});
  overwrite_u32(crcMismatch, 56 + 32, test_crc32(x4ShardA.registry) ^ 1u);
  write_file(setPath, crcMismatch);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A set CRC that differs from an otherwise valid shard should fail closed");

  write_set_case(4, {x4ShardA});
  auto counterMismatch = make_set(4, {x4ShardA});
  overwrite_u32(counterMismatch, 20, 2);
  overwrite_u32(counterMismatch, 56 + 36, 2);
  write_file(setPath, counterMismatch);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A set entry count that disagrees with its shard header should fail closed");

  write_set_case(4, {x4ShardA});
  auto zeroHash = make_set(4, {x4ShardA});
  std::fill(zeroHash.begin() + 56, zeroHash.begin() + 88, std::byte{0});
  write_file(setPath, zeroHash);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "An all-zero registry-set SHA-256 should fail closed");

  const auto duplicateShard = make_shard(4, 'A');
  write_set_case(4, {x4ShardA, duplicateShard});
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A resref duplicated across two valid shards should fail closed");

  write_set_case(4, {x4ShardA, x2ShardB});
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A shard whose xN scale differs from its set should fail closed");

  // Keep the expected SHA unchanged but acknowledge the modified file in the
  // CRC field: runtime SHA verification must still reject the shard.
  write_set_case(4, {x4ShardA});
  auto shaMismatchShard = x4ShardA.registry;
  shaMismatchShard[32] ^= std::byte{2};
  auto shaMismatchSet = make_set(4, {x4ShardA});
  overwrite_u32(shaMismatchSet, 56 + 32, test_crc32(shaMismatchShard));
  write_file(setPath, shaMismatchSet);
  write_file(root / "CreatureSprites-XN-0000.registry", shaMismatchShard);
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "A shard with an adjusted CRC but stale SHA-256 should fail closed");

  std::filesystem::remove(setPath, ec);
  std::filesystem::remove(root / "CreatureSprites-XN-0000.registry", ec);
  std::filesystem::remove(root / "CreatureSprites-XN-0001.registry", ec);

  write_file(legacyPath, make_registry(legacyMagic, 2, 2, 0xE400));
  write_file(xnPath, make_registry(xnMagic, 3, 4, 0x6110));
  expect_true(iee::creature_sprite_x2::prepare(root),
              "The creature registry parser should prefer a valid v3 xN pack");
  expect_true(iee::creature_sprite_x2::target_animation_id() == 0x6110 &&
                  iee::creature_sprite_x2::loaded_scale() == 4 &&
                  iee::creature_sprite_x2::contains_resource(target),
              "A v3 x4 pack should expose its animation, scale, and registered resrefs");
  expect_eq(iee::creature_sprite_x2::resident_index_bytes(), std::uint64_t{0},
            "A monolithic xN pack should also keep its frame payloads lazy");
  iee::creature_sprite_x2::FrameHandle handle{};
  expect_true(iee::creature_sprite_x2::resolve_frame(target, 0, 0, handle) &&
                  handle.resourceIndex == 0 && handle.frameIndex == 0 &&
                  iee::creature_sprite_x2::ensure_frame_payload_available(handle) &&
                  iee::creature_sprite_x2::resident_index_bytes() == 16,
              "A v3 creature registry cycle should resolve and lazily load its frame");
  iee::creature_sprite_x2::release();
  expect_true(iee::creature_sprite_x2::loaded_scale() == 0,
              "Releasing a creature pack should clear its physical scale");

  std::filesystem::remove(xnPath, ec);
  expect_true(iee::creature_sprite_x2::prepare(root) &&
                  iee::creature_sprite_x2::target_animation_id() == 0xE400 &&
                  iee::creature_sprite_x2::loaded_scale() == 2 &&
                  iee::creature_sprite_x2::contains_resource(target) &&
                  iee::creature_sprite_x2::resident_index_bytes() == 4,
              "The parser should fall back to the legacy x2 file only when xN is absent");
  iee::creature_sprite_x2::release();

  write_file(xnPath, make_registry(xnMagic, 3, 2, 0x6110));
  expect_true(iee::creature_sprite_x2::prepare(root) &&
                  iee::creature_sprite_x2::loaded_scale() == 2,
              "The v3 xN registry should support scale x2");
  iee::creature_sprite_x2::release();

  write_file(xnPath, make_registry(xnMagic, 4, 2, 0x6102));
  expect_true(iee::creature_sprite_x2::prepare(root) &&
                  iee::creature_sprite_x2::target_animation_id() == 0x6102 &&
                  iee::creature_sprite_x2::loaded_scale() == 2 &&
                  iee::creature_sprite_x2::resident_index_bytes() == 4,
              "A V4 xBR Antialias monolith should retain its base indices resident");
  iee::creature_sprite_x2::release();

  write_file(xnPath, make_registry(xnMagic, 4, 4, 0x6102));
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "The initial V4 Antialias contract should reject unsupported x4 packs");

  write_file(xnPath, make_registry(xnMagic, 3, 3, 0x6110));
  expect_true(!iee::creature_sprite_x2::prepare(root) &&
                  !iee::creature_sprite_x2::ready() &&
                  iee::creature_sprite_x2::loaded_scale() == 0,
              "An existing xN file with an unsupported scale should fail closed instead of "
              "falling back to legacy x2");

  write_file(xnPath, make_registry(xnMagic, 3, 4, 0x6110, 1, 2));
  expect_true(!iee::creature_sprite_x2::prepare(root) &&
                  !iee::creature_sprite_x2::ready(),
              "An x4 registry carrying an x2-sized frame payload should fail closed");

  write_file(xnPath, make_registry(xnMagic, 2, 2, 0x6110));
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "The xN filename and magic should reject unsupported registry versions");

  std::filesystem::remove(xnPath, ec);
  write_file(legacyPath, make_registry(legacyMagic, 2, 2, 0x6110, 92));
  expect_true(iee::creature_sprite_x2::prepare(root) &&
                  iee::creature_sprite_x2::loaded_scale() == 2 &&
                  iee::creature_sprite_x2::contains_resource(target),
              "The legacy parser should retain the 92-resource Character armor-set path");
  iee::creature_sprite_x2::release();

  write_file(legacyPath, make_registry(legacyMagic, 1, 2, 0));
  expect_true(iee::creature_sprite_x2::prepare(root) &&
                  iee::creature_sprite_x2::target_animation_id() == 0xE400 &&
                  iee::creature_sprite_x2::loaded_scale() == 2,
              "A legacy v1 pack should remain scoped to MGO1 animation 0xE400");
  iee::creature_sprite_x2::release();

  write_file(legacyPath, make_registry(legacyMagic, 2, 4, 0x6110));
  expect_true(!iee::creature_sprite_x2::prepare(root),
              "The legacy filename and magic should reject scale x4");

  write_file(legacyPath, make_registry(legacyMagic, 2, 2, 0));
  expect_true(!iee::creature_sprite_x2::prepare(root) &&
                  !iee::creature_sprite_x2::ready(),
              "A legacy v2 pack without an animation id should fail closed");
  std::filesystem::remove_all(root, ec);
#endif
}

void test_performance_sample_summary() {
  iee::core::PerformanceSamples<4> samples;
  samples.add(4.0);
  samples.add(1.0);
  samples.add(3.0);
  samples.add(2.0);
  samples.add(99.0);

  const auto summary = samples.summarize();
  expect_eq(summary.count, std::size_t{4}, "Performance samples should stay bounded");
  expect_eq(summary.dropped, std::size_t{1}, "Overflow samples should be reported");
  expect_eq(summary.average, 2.5, "Performance sample average should be exact");
  expect_eq(summary.percentile95, 4.0, "Nearest-rank index should report the bounded p95");
  expect_eq(summary.maximum, 4.0, "Performance sample maximum should be retained");

  samples.reset();
  expect_eq(samples.summarize().count, std::size_t{0}, "Reset should clear the sample window");
}

const iee::core::AreaAnimationClockGroupSnapshot* find_clock_group(
    const iee::core::AreaAnimationClockReport& report, const std::array<char, 8>& resref,
    int sequence) {
  for (std::size_t index = 0; index < report.groupCount; ++index) {
    if (report.groups[index].resref == resref && report.groups[index].sequence == sequence) {
      return &report.groups[index];
    }
  }
  return nullptr;
}

void test_area_animation_clock_probe() {
  constexpr std::array<char, 8> portl1a{{'P', 'O', 'R', 'T', 'L', '1', 'A', '\0'}};
  iee::core::AreaAnimationClockProbe probe(1000);
  probe.begin_area(7);

  const auto observe = [&](int sequence, int slot, std::uint64_t epoch, std::int64_t ticks,
                           int worldActive = 1) {
    probe.observe({.instance = 0x1234,
                   .resref = portl1a,
                   .sequence = sequence,
                   .slot = slot,
                   .presentationEpoch = epoch,
                   .clockTicks = ticks,
                   .worldActive = worldActive});
  };

  observe(0, 0, 10, 0);
  observe(0, 0, 11, 10);
  observe(0, 0, 11, 11);
  observe(0, 0, 12, 20);
  observe(0, 1, 14, 100);
  observe(0, 2, 15, 170);
  observe(0, 0, 16, 240, 0);
  observe(1, 0, 17, 300);

  const auto report = probe.take_report();
  expect_eq(report.areaGeneration, std::uint64_t{7},
            "Clock probe should retain the current area generation");
  expect_eq(report.groupCount, std::size_t{2},
            "Clock probe should separate animation sequences");
  const auto* sequence0 = find_clock_group(report, portl1a, 0);
  const auto* sequence1 = find_clock_group(report, portl1a, 1);
  expect_true(sequence0 != nullptr && sequence1 != nullptr,
              "Clock probe reports should retain resref and sequence keys");
  if (sequence0) {
    expect_eq(sequence0->calls, std::uint64_t{7}, "Clock probe should count RenderBam calls");
    expect_eq(sequence0->occurrenceEpochs, std::uint64_t{6},
              "Clock probe should deduplicate repeated calls in one presentation epoch");
    expect_eq(sequence0->sameEpochCalls, std::uint64_t{1},
              "Clock probe should expose same-epoch calls");
    expect_eq(sequence0->completedSlots, std::uint64_t{4},
              "Slot changes and sequence resets should finalize slot visits");
    expect_eq(sequence0->slotEpochsTotal, std::uint64_t{6},
              "Completed slots should accumulate their distinct presentation epochs");
    expect_eq(sequence0->slotEpochsMinimum, std::uint32_t{1},
              "Clock probe should retain the minimum epochs per slot");
    expect_eq(sequence0->slotEpochsMaximum, std::uint32_t{3},
              "Clock probe should retain the maximum epochs per slot");
    expect_eq(sequence0->validSlotDurations, std::uint64_t{4},
              "Ordinary slot visits should contribute timing samples");
    expect_eq(sequence0->slotDurationTicksTotal, std::uint64_t{300},
              "Clock probe should accumulate raw integer clock ticks");
    expect_eq(sequence0->sequentialTransitions, std::uint64_t{2},
              "Clock probe should recognize sequential slot advances");
    expect_eq(sequence0->wraps, std::uint64_t{1},
              "Clock probe should recognize a transition back to slot zero as a wrap");
    expect_eq(sequence0->sequenceChanges, std::uint64_t{1},
              "Clock probe should reset occurrence state on a sequence change");
    expect_eq(sequence0->worldActiveCalls, std::uint64_t{6},
              "Clock probe should aggregate active-world calls");
    expect_eq(sequence0->worldInactiveCalls, std::uint64_t{1},
              "Clock probe should aggregate paused-world calls");
    expect_eq(sequence0->worldActiveTransitions, std::uint64_t{1},
              "Clock probe should expose changes in the candidate pause signal");
  }
  if (sequence1) {
    expect_eq(sequence1->calls, std::uint64_t{1},
              "The first call in a new sequence should be counted once");
    expect_eq(sequence1->occurrenceStarts, std::uint64_t{1},
              "A sequence change should start a fresh occurrence clock");
  }

  expect_eq(probe.take_report().groupCount, std::size_t{0},
            "Taking a report should reset window counters without reallocating state");

  probe.begin_area(8);
  observe(0, 0, 20, 1000);
  const auto nextArea = probe.take_report();
  expect_eq(nextArea.areaGeneration, std::uint64_t{8},
            "Beginning an area should publish the new lifecycle generation");
  const auto* restarted = find_clock_group(nextArea, portl1a, 0);
  expect_true(restarted && restarted->occurrenceStarts == 1,
              "Beginning an area should discard occurrence pointer history");

  iee::core::AreaAnimationClockProbe stalledProbe(1000);
  stalledProbe.begin_area(1);
  stalledProbe.observe({.instance = 0x5678,
                        .resref = portl1a,
                        .sequence = 0,
                        .slot = 0,
                        .presentationEpoch = 1,
                        .clockTicks = 0,
                        .worldActive = 1});
  stalledProbe.observe({.instance = 0x5678,
                        .resref = portl1a,
                        .sequence = 0,
                        .slot = 1,
                        .presentationEpoch = 2,
                        .clockTicks = 300,
                        .worldActive = 1});
  const auto stalledReport = stalledProbe.take_report();
  const auto* stalled = find_clock_group(stalledReport, portl1a, 0);
  expect_true(stalled && stalled->stalledSlots == 1 && stalled->longGaps == 1,
              "Clock probe should quarantine pause, culling or hitch gaps over 250 ms");
}

void test_area_animation_timeline_clock() {
  constexpr std::array<char, 8> portl1a{{'P', 'O', 'R', 'T', 'L', '1', 'A', '\0'}};
  iee::core::AreaAnimationTimelineClock clock;
  clock.begin_area(11);

  const auto select = [&](int slot, std::uint64_t epoch, std::int64_t ticks,
                          int worldActive = 1) {
    return clock.select({.instance = 0x1234,
                         .resref = portl1a,
                         .sequence = 0,
                         .nativeSlot = slot,
                         .presentationEpoch = epoch,
                         .clockTicks = ticks,
                         .ticksPerSecond = 1000,
                         .worldActive = worldActive,
                         .nativeFpsNumerator = 15,
                         .nativeFpsDenominator = 1,
                         .targetFpsNumerator = 30,
                         .targetFpsDenominator = 1,
                         .timelinePhaseCount = 12});
  };

  auto result = select(0, 1, 0);
  expect_true(result.valid && result.occurrenceReset && result.phase == 0,
              "A new 30 fps timeline should start on its exact native anchor");
  expect_eq(select(0, 2, 20).phase, std::uint32_t{0},
            "The first half of a native slot should retain its native phase");
  expect_eq(select(0, 3, 34).phase, std::uint32_t{1},
            "The second half of a native slot should select its interpolated phase");
  expect_eq(select(0, 3, 50).phase, std::uint32_t{1},
            "Repeated RenderBam calls in one presentation epoch should retain one phase");

  result = select(1, 4, 67);
  expect_true(result.valid && result.occurrenceReset && result.phase == 2,
              "A native slot transition should authoritatively re-anchor the 2:1 timeline");
  expect_eq(select(1, 5, 101).phase, std::uint32_t{3},
            "A 2:1 timeline should expose the intermediate phase of slot one");

  result = select(1, 6, 110, 0);
  expect_true(result.valid && result.paused && result.phase == 3,
              "Entering a world pause should freeze the currently selected phase");
  result = select(1, 7, 500, 0);
  expect_true(result.valid && result.paused && result.phase == 3,
              "A paused world should not advance an area animation timeline");
  result = select(1, 8, 600, 1);
  expect_true(result.valid && !result.paused && result.phase == 3,
              "Resuming should preserve phase without a QPC-driven jump");
  expect_eq(select(2, 9, 650).phase, std::uint32_t{4},
            "The next native slot should resume on its exact source anchor");

  clock.begin_area(12);
  expect_eq(clock.area_generation(), std::uint64_t{12},
            "A zone boundary should publish the new timeline generation");
  result = select(0, 10, 1000);
  expect_true(result.valid && result.occurrenceReset && result.phase == 0,
              "A zone boundary should discard occurrence pointer history");

  const auto unknownPause = clock.select({.instance = 0x1234,
                                          .resref = portl1a,
                                          .sequence = 0,
                                          .nativeSlot = 0,
                                          .presentationEpoch = 11,
                                          .clockTicks = 1010,
                                          .ticksPerSecond = 1000,
                                          .worldActive = -1,
                                          .nativeFpsNumerator = 15,
                                          .nativeFpsDenominator = 1,
                                          .targetFpsNumerator = 30,
                                          .targetFpsDenominator = 1,
                                          .timelinePhaseCount = 12});
  expect_true(!unknownPause.valid,
              "A missing pause signal should fail closed to the native registry frame");

  iee::core::AreaAnimationTimelineClock twentyFpsClock;
  twentyFpsClock.begin_area(1);
  constexpr std::array<std::uint32_t, 6> expectedAnchors{{0, 1, 2, 4, 5, 6}};
  for (int slot = 0; slot < 6; ++slot) {
    const auto phase = twentyFpsClock.select({.instance = 0x5678,
                                               .resref = portl1a,
                                               .sequence = 0,
                                               .nativeSlot = slot,
                                               .presentationEpoch =
                                                   static_cast<std::uint64_t>(slot + 1),
                                               .clockTicks = slot * 67,
                                               .ticksPerSecond = 1000,
                                               .worldActive = 1,
                                               .nativeFpsNumerator = 15,
                                               .nativeFpsDenominator = 1,
                                               .targetFpsNumerator = 20,
                                               .targetFpsDenominator = 1,
                                               .timelinePhaseCount = 8});
    expect_true(phase.valid && phase.phase == expectedAnchors[slot],
                "A rational 20 fps schedule should use timeline time, not integer subdivision");
  }
}

void test_area_animation_registry_formats() {
#ifdef _WIN32
  const auto root = std::filesystem::current_path() / "area-animation-registry-format-test";
  std::error_code ec;
  std::filesystem::remove_all(root, ec);
  std::filesystem::create_directory(root);

  const auto append = [](std::vector<std::byte>& bytes, const auto& value) {
    const auto* first = reinterpret_cast<const std::byte*>(&value);
    bytes.insert(bytes.end(), first, first + sizeof(value));
  };
  const auto append_raw = [](std::vector<std::byte>& bytes, const void* value,
                             std::size_t size) {
    const auto* first = reinterpret_cast<const std::byte*>(value);
    bytes.insert(bytes.end(), first, first + size);
  };
  const auto write_file = [](const std::filesystem::path& path,
                             const std::vector<std::byte>& bytes) {
    std::ofstream output(path, std::ios::binary);
    output.write(reinterpret_cast<const char*>(bytes.data()),
                 static_cast<std::streamsize>(bytes.size()));
  };
  constexpr std::array<char, 8> magic{{'I', 'E', 'E', 'A', 'A', 'X', '4', '\0'}};
  constexpr std::array<char, 8> target{{'T', 'E', 'S', 'T', 'A', '\0', '\0', '\0'}};
  const auto make_header = [&](std::uint32_t version) {
    std::vector<std::byte> bytes;
    append_raw(bytes, magic.data(), magic.size());
    for (const auto value : std::array<std::uint32_t, 4>{{version, 4, 1, 0}}) {
      append(bytes, value);
    }
    return bytes;
  };
  const std::vector<std::byte> rgba(4 * 4 * 4, std::byte{0x7f});
  write_file(root / "AAX4-TESTA-frame000.rgba", rgba);
  write_file(root / "AAX4-TESTA-frame001.rgba", rgba);

  auto v2 = make_header(2);
  append_raw(v2, target.data(), target.size());
  for (const auto value : std::array<std::uint32_t, 2>{{2, 1}}) append(v2, value);
  for (const auto value : std::array<std::uint32_t, 5>{{1, 15, 1, 30, 1}}) append(v2, value);
  for (const auto value : std::array<std::uint32_t, 4>{{1, 1, 1, 1}}) append(v2, value);
  for (const auto value : std::array<std::uint32_t, 5>{{1, 0, 2, 0, 1}}) append(v2, value);
  write_file(root / "AreaAnimations-X4.registry", v2);

  expect_true(iee::area_animation_x4::prepare(root),
              "The production registry parser should accept a valid v2 TimedTimeline");
  iee::area_animation_x4::FrameResolution resolution{};
  expect_true(iee::area_animation_x4::resolve_frame(target, 0, 0, resolution) &&
                  resolution.nativeFrame.frameIndex == 0 && resolution.timeline.enabled &&
                  resolution.timeline.phaseCount == 2,
              "A v2 native slot should expose its exact fallback and timeline timing");
  iee::area_animation_x4::FrameHandle phase{};
  expect_true(iee::area_animation_x4::resolve_timeline_frame(resolution, 0, 1, phase) &&
                  phase.frameIndex == 1,
              "A v2 timeline phase should resolve its independent visual frame");
  iee::area_animation_x4::release();

  auto v1 = make_header(1);
  append_raw(v1, target.data(), target.size());
  for (const auto value : std::array<std::uint32_t, 2>{{1, 1}}) append(v1, value);
  for (const auto value : std::array<std::uint32_t, 2>{{1, 1}}) append(v1, value);
  for (const auto value : std::array<std::uint32_t, 2>{{1, 0}}) append(v1, value);
  write_file(root / "AreaAnimations-X4.registry", v1);
  expect_true(iee::area_animation_x4::prepare(root),
              "The registry-v2 runtime should remain backward-compatible with v1 packs");
  resolution = {};
  expect_true(iee::area_animation_x4::resolve_frame(target, 0, 0, resolution) &&
                  !resolution.timeline.enabled && resolution.nativeFrame.frameIndex == 0,
              "A legacy v1 resource should remain on native playback");

  // Production payloads are deliberately split by area so the complete x4
  // inventory is never resident at once.  Exercise the same AR0602-shaped
  // layout used by the installer: loading an owned zone must work, while the
  // next zone without a pack must release it and leave the native BAM path.
  const auto assets = root / "assets";
  const auto areaPack = assets / "areas" / "AR0602";
  std::filesystem::create_directories(areaPack);
  write_file(areaPack / "AAX4-TESTA-frame000.rgba", rgba);
  write_file(areaPack / "AAX4-TESTA-frame001.rgba", rgba);
  write_file(areaPack / "AreaAnimations-X4.registry", v2);
  expect_true(iee::area_animation_x4::configure_area_packs(assets) &&
                  iee::area_animation_x4::per_area_packs_active(),
              "The runtime should enable per-area animation packs from iee-assets/areas");
  expect_true(iee::area_animation_x4::prepare_for_area("ar0602"),
              "A valid owned area pack should become resident on LoadArea");
  resolution = {};
  expect_true(iee::area_animation_x4::resolve_frame(target, 0, 0, resolution) &&
                  resolution.timeline.enabled,
              "The resident per-area v2 pack should resolve TimedTimeline frames");
  expect_true(!iee::area_animation_x4::prepare_for_area("AR0000") &&
                  !iee::area_animation_x4::ready(),
              "A zone without a pack must release the prior area and fall back to the BAM");
  iee::area_animation_x4::release();

  auto malformed = make_header(2);
  write_file(root / "AreaAnimations-X4.registry", malformed);
  expect_true(!iee::area_animation_x4::prepare(root) && !iee::area_animation_x4::ready(),
              "A malformed reload should fail closed instead of retaining an older pack");
  iee::area_animation_x4::release();

  std::filesystem::remove_all(root, ec);
#endif
}

void test_config_shader_override_roundtrip() {
  const auto tempPath = std::filesystem::current_path() / "InfinityEngine-Enhancer-shader-test.ini";
  {
    iee::core::EngineConfig orig{};
    orig.dumpEngineShaders = false;
    orig.enableDebugHotkeys = true;
    orig.enableWaterEffect = false;
    orig.enableBamUiTextureProbe = true;
    orig.enableAreaAnimationX4 = true;
    orig.enableCreatureSpriteUpscaleTest = true;
    orig.enableCreatureSpriteX2Test = true;
    orig.enableCreatureSpriteLinearFiltering = true;
    orig.enableBigLogoX4Test = true;
    orig.enableMainMenuX4Test = true;
    orig.enableMenuX2Test = true;
    orig.enablePerformanceLogging = true;

    expect_true(iee::core::ConfigManager::save(tempPath, orig),
                "ConfigManager::save should succeed");
  }

  iee::core::EngineConfig loaded{};
  expect_true(iee::core::ConfigManager::load(tempPath, loaded),
              "ConfigManager::load should parse shader config");
  expect_true(!loaded.dumpEngineShaders, "dumpEngineShaders should round-trip as false");
  expect_true(loaded.enableDebugHotkeys, "enableDebugHotkeys should round-trip as true");
  expect_true(!loaded.enableWaterEffect, "enableWaterEffect should round-trip as false");
  expect_true(loaded.enableBamUiTextureProbe,
              "enableBamUiTextureProbe should round-trip as true");
  expect_true(loaded.enableAreaAnimationX4,
              "enableAreaAnimationX4 should round-trip as true");
  expect_true(loaded.enableCreatureSpriteUpscaleTest,
              "enableCreatureSpriteUpscaleTest should round-trip as true");
  expect_true(loaded.enableCreatureSpriteX2Test,
              "enableCreatureSpriteX2Test should round-trip as true");
  expect_true(loaded.enableCreatureSpriteLinearFiltering,
              "enableCreatureSpriteLinearFiltering should round-trip as true");
  expect_true(loaded.creature_sprite_upscale_enabled(),
              "saved xN and legacy activation keys should keep the helper enabled");
  expect_true(loaded.enableBigLogoX4Test, "enableBigLogoX4Test should round-trip as true");
  expect_true(loaded.enableMainMenuX4Test, "enableMainMenuX4Test should round-trip as true");
  expect_true(loaded.enableMenuX2Test, "enableMenuX2Test should round-trip as true");
  expect_true(loaded.enablePerformanceLogging,
              "enablePerformanceLogging should round-trip as true");

  std::error_code ec;
  std::filesystem::remove(tempPath, ec);
}

void write_bytes(std::vector<std::byte>& buffer, std::size_t offset, const void* data,
                 std::size_t size) {
  if (offset + size > buffer.size()) {
    buffer.resize(offset + size);
  }
  std::memcpy(buffer.data() + offset, data, size);
}

constexpr std::uint32_t dds_four_cc(char a, char b, char c, char d) noexcept {
  return static_cast<std::uint32_t>(static_cast<unsigned char>(a)) |
         (static_cast<std::uint32_t>(static_cast<unsigned char>(b)) << 8) |
         (static_cast<std::uint32_t>(static_cast<unsigned char>(c)) << 16) |
         (static_cast<std::uint32_t>(static_cast<unsigned char>(d)) << 24);
}

void write_u32(std::vector<std::byte>& buffer, std::size_t offset, std::uint32_t value) {
  if (offset + sizeof(value) > buffer.size()) buffer.resize(offset + sizeof(value));
  for (std::size_t index = 0; index < sizeof(value); ++index) {
    buffer[offset + index] = static_cast<std::byte>((value >> (index * 8)) & 0xFF);
  }
}

std::vector<std::byte> make_legacy_dds(std::uint32_t formatCode, std::uint32_t width,
                                       std::uint32_t height, std::uint32_t mipCount,
                                       std::size_t payloadBytes,
                                       std::uint32_t additionalPixelFormatFlags = 0) {
  constexpr std::size_t headerBytes = 128;
  std::vector<std::byte> bytes(headerBytes + payloadBytes);
  constexpr char magic[] = "DDS ";
  write_bytes(bytes, 0, magic, 4);
  write_u32(bytes, 4, 124);  // DDS_HEADER::dwSize
  write_u32(bytes, 12, height);
  write_u32(bytes, 16, width);
  write_u32(bytes, 28, mipCount);
  write_u32(bytes, 76, 32);                                // DDS_PIXELFORMAT::dwSize
  write_u32(bytes, 80, 0x4 | additionalPixelFormatFlags);  // DDPF_FOURCC
  write_u32(bytes, 84, formatCode);
  for (std::size_t index = 0; index < payloadBytes; ++index) {
    bytes[headerBytes + index] = static_cast<std::byte>(index & 0xFF);
  }
  return bytes;
}

std::vector<std::byte> make_dx10_dds(std::uint32_t dxgiFormat, std::uint32_t width,
                                     std::uint32_t height, std::uint32_t mipCount,
                                     std::size_t payloadBytes) {
  constexpr std::size_t headerBytes = 148;
  auto bytes =
      make_legacy_dds(dds_four_cc('D', 'X', '1', '0'), width, height, mipCount, payloadBytes + 20);
  bytes.resize(headerBytes + payloadBytes);
  write_u32(bytes, 128, dxgiFormat);
  write_u32(bytes, 132, 3);  // D3D10_RESOURCE_DIMENSION_TEXTURE2D
  write_u32(bytes, 136, 0);  // miscFlag
  write_u32(bytes, 140, 1);  // arraySize
  write_u32(bytes, 144, 0);  // miscFlags2
  for (std::size_t index = 0; index < payloadBytes; ++index) {
    bytes[headerBytes + index] = static_cast<std::byte>((index + 17) & 0xFF);
  }
  return bytes;
}

void test_parse_dds_legacy_formats_and_mips() {
  using namespace iee::game;

  auto bytes = make_legacy_dds(dds_four_cc('D', 'X', 'T', '1'), 8, 8, 4, 56);
  DdsTexture texture;
  std::string error;
  expect_true(parse_dds_texture(bytes, texture, error),
              "Legacy BC1 DDS with a full mip chain should parse");
  if (texture.empty()) return;

  expect_true(error.empty(), "Successful DDS parsing should clear the error string");
  expect_true(texture.format == DdsBlockFormat::Bc1RgbUnorm,
              "Legacy DXT1 without alpha pixels should map to BC1 RGB");
  expect_eq(texture.width, std::uint32_t{8}, "DDS width should be preserved");
  expect_eq(texture.height, std::uint32_t{8}, "DDS height should be preserved");
  expect_eq(texture.mipLevels.size(), std::size_t{4}, "All declared DDS mips should be exposed");
  expect_eq(texture.payload.size(), std::size_t{56}, "Only the required mip payload should remain");
  const std::array<std::uint32_t, 4> dimensions{8, 4, 2, 1};
  const std::array<std::size_t, 4> offsets{0, 32, 40, 48};
  for (std::size_t index = 0; index < texture.mipLevels.size(); ++index) {
    expect_eq(texture.mipLevels[index].width, dimensions[index],
              "DDS mip width should halve to one");
    expect_eq(texture.mipLevels[index].height, dimensions[index],
              "DDS mip height should halve to one");
    expect_eq(texture.mipLevels[index].dataOffset, offsets[index],
              "DDS mip offsets should follow block-compressed sizes");
    expect_eq(texture.mipLevels[index].dataSize, index == 0 ? std::size_t{32} : std::size_t{8},
              "BC1 mip sizes should use 8-byte 4x4 blocks");
  }

  bytes = make_legacy_dds(dds_four_cc('D', 'X', 'T', '1'), 4, 4, 1, 8, 0x1);
  expect_true(parse_dds_texture(bytes, texture, error), "Legacy BC1 alpha DDS should parse");
  expect_true(texture.format == DdsBlockFormat::Bc1RgbaUnorm,
              "Legacy DXT1 with alpha pixels should map to BC1 RGBA");

  bytes = make_legacy_dds(dds_four_cc('D', 'X', 'T', '5'), 4, 4, 1, 16);
  expect_true(parse_dds_texture(bytes, texture, error), "Legacy BC3 DDS should parse");
  expect_true(texture.format == DdsBlockFormat::Bc3RgbaUnorm, "Legacy DXT5 should map to BC3 RGBA");

  bytes = make_legacy_dds(dds_four_cc('A', 'T', 'I', '2'), 4, 4, 1, 16);
  expect_true(parse_dds_texture(bytes, texture, error), "Legacy BC5 DDS should parse");
  expect_true(texture.format == DdsBlockFormat::Bc5RgUnorm, "Legacy ATI2 should map to BC5 RG");

  bytes = make_legacy_dds(dds_four_cc('B', 'C', '5', 'U'), 4, 4, 1, 16);
  expect_true(parse_dds_texture(bytes, texture, error), "Legacy BC5U DDS should parse");
  expect_true(texture.format == DdsBlockFormat::Bc5RgUnorm, "Legacy BC5U should map to BC5 RG");
}

void test_parse_dds_dx10_formats() {
  using namespace iee::game;

  struct FormatCase {
    std::uint32_t dxgiFormat;
    DdsBlockFormat expected;
    std::size_t blockBytes;
  };
  constexpr std::array<FormatCase, 7> cases{{
      {71, DdsBlockFormat::Bc1RgbaUnorm, 8},
      {72, DdsBlockFormat::Bc1RgbaSrgb, 8},
      {77, DdsBlockFormat::Bc3RgbaUnorm, 16},
      {78, DdsBlockFormat::Bc3RgbaSrgb, 16},
      {83, DdsBlockFormat::Bc5RgUnorm, 16},
      {98, DdsBlockFormat::Bc7RgbaUnorm, 16},
      {99, DdsBlockFormat::Bc7RgbaSrgb, 16},
  }};

  for (const auto& formatCase : cases) {
    auto bytes = make_dx10_dds(formatCase.dxgiFormat, 4, 4, 1, formatCase.blockBytes);
    DdsTexture texture;
    std::string error;
    expect_true(parse_dds_texture(bytes, texture, error),
                "Supported DX10 block-compressed DDS should parse");
    expect_true(texture.format == formatCase.expected,
                "DXGI compression format should map to the expected runtime format");
    expect_eq(texture.payload.size(), formatCase.blockBytes,
              "DX10 DDS should expose exactly one compressed block");
  }
}

void test_parse_dds_rejects_unsupported_or_malformed_input() {
  using namespace iee::game;

  DdsTexture texture;
  std::string error;
  auto bytes = make_legacy_dds(dds_four_cc('D', 'X', 'T', '1'), 8, 8, 1, 31);
  expect_true(!parse_dds_texture(bytes, texture, error),
              "Truncated BC1 payload should fail closed");
  expect_true(texture.empty() && !error.empty(),
              "Rejected DDS input should clear output and explain the failure");

  bytes = make_legacy_dds(dds_four_cc('D', 'X', 'T', '3'), 4, 4, 1, 16);
  expect_true(!parse_dds_texture(bytes, texture, error), "Unsupported BC2/DXT3 should be rejected");

  bytes = make_legacy_dds(dds_four_cc('D', 'X', 'T', '1'), 4, 4, 1, 8);
  write_u32(bytes, 112, 0x200);  // DDSCAPS2_CUBEMAP
  expect_true(!parse_dds_texture(bytes, texture, error), "Legacy cubemap DDS should be rejected");

  bytes = make_dx10_dds(98, 4, 4, 1, 16);
  write_u32(bytes, 140, 2);
  expect_true(!parse_dds_texture(bytes, texture, error), "DX10 texture arrays should be rejected");

  bytes = make_legacy_dds(dds_four_cc('D', 'X', 'T', '1'), 4, 4, 4, 32);
  expect_true(!parse_dds_texture(bytes, texture, error),
              "A DDS with more mips than its dimensions allow should be rejected");

  bytes = make_dx10_dds(95, 4, 4, 1, 16);  // BC6H_UF16
  expect_true(!parse_dds_texture(bytes, texture, error),
              "Unsupported DXGI compression formats should be rejected");
}

void test_load_dds_texture_file_wrapper() {
  const auto tempPath = std::filesystem::current_path() / "InfinityEngine-Enhancer-dds-test.dds";
  const auto bytes = make_dx10_dds(98, 4, 4, 1, 16);
  {
    std::ofstream file(tempPath, std::ios::binary | std::ios::trunc);
    file.write(reinterpret_cast<const char*>(bytes.data()),
               static_cast<std::streamsize>(bytes.size()));
    expect_true(static_cast<bool>(file), "Synthetic DDS fixture should be written completely");
  }

  iee::game::DdsTexture texture;
  std::string error;
  expect_true(iee::game::load_dds_texture(tempPath, texture, error),
              "DDS file wrapper should load a valid bounded file");
  expect_true(texture.format == iee::game::DdsBlockFormat::Bc7RgbaUnorm,
              "DDS file wrapper should preserve the parsed format");

  std::error_code removeError;
  std::filesystem::remove(tempPath, removeError);
  expect_true(!removeError, "Synthetic DDS fixture should be removed after the test");

  expect_true(!iee::game::load_dds_texture(tempPath, texture, error),
              "DDS file wrapper should reject a missing file");
  expect_true(texture.empty() && !error.empty(),
              "Missing DDS files should clear output and report an error");
}

void test_parse_loaded_wed() {
  using namespace iee::game;

  constexpr std::size_t headerOffset = 0x0;
  constexpr std::size_t layerOffset = sizeof(WED_WedHeader_st);
  constexpr std::size_t tilemapOffset = layerOffset + 2 * sizeof(WED_LayerHeader_st);
  constexpr std::size_t liquidTilemapOffset = tilemapOffset + 4 * sizeof(WED_TileData_st);
  constexpr std::size_t liquidLookupOffset = liquidTilemapOffset + 4 * sizeof(WED_TileData_st);

  std::vector<std::byte> bytes(liquidLookupOffset + 4 * sizeof(std::uint16_t));

  WED_WedHeader_st header{};
  header.nFileType = 0x20444557;
  header.nFileVersion = 0x332E3156;
  header.nLayers = 2;
  header.nOffsetToLayerHeaders = static_cast<std::uint32_t>(layerOffset);
  write_bytes(bytes, headerOffset, &header, sizeof(header));

  WED_LayerHeader_st baseLayer{};
  baseLayer.nTilesAcross = 2;
  baseLayer.nTilesDown = 2;
  baseLayer.rrTileSet = {'A', 'R', '0', '0', '0', '1', '0', '0'};
  baseLayer.nNumUniqueTiles = 4;
  baseLayer.nOffsetToTileData = static_cast<std::uint32_t>(tilemapOffset);
  write_bytes(bytes, layerOffset, &baseLayer, sizeof(baseLayer));

  WED_LayerHeader_st liquidLayer{};
  liquidLayer.nTilesAcross = 2;
  liquidLayer.nTilesDown = 2;
  liquidLayer.rrTileSet = {'W', 'T', 'L', 'A', 'K', 'E', '\0', '\0'};
  liquidLayer.nNumUniqueTiles = 4;
  liquidLayer.nOffsetToTileData = static_cast<std::uint32_t>(liquidTilemapOffset);
  liquidLayer.nOffsetToTileList = static_cast<std::uint32_t>(liquidLookupOffset);
  write_bytes(bytes, layerOffset + sizeof(WED_LayerHeader_st), &liquidLayer, sizeof(liquidLayer));

  std::array<WED_TileData_st, 4> tileData{};
  tileData[0].bFlags = 0x02;
  tileData[2].bFlags = 0x02;
  write_bytes(bytes, tilemapOffset, tileData.data(), sizeof(tileData));

  std::array<WED_TileData_st, 4> liquidTileData{};
  liquidTileData[0].nStartingTile = 3;
  liquidTileData[1].nStartingTile = 0;
  liquidTileData[2].nStartingTile = 2;
  liquidTileData[3].nStartingTile = 500;  // lookup entry out of bounds
  write_bytes(bytes, liquidTilemapOffset, liquidTileData.data(), sizeof(liquidTileData));

  const std::array<std::uint16_t, 4> liquidTileLookup{21, 22, 23, 24};
  write_bytes(bytes, liquidLookupOffset, liquidTileLookup.data(), sizeof(liquidTileLookup));

  CRes resource{};
  resource.pData = bytes.data();
  resource.nSize = static_cast<std::uint32_t>(bytes.size());
  resource.bLoaded = true;

  char areaResref[8] = {'A', 'R', '0', '0', '0', '1', '\0', '\0'};
  resource.resref = areaResref;

  WedAreaInfo wed{};
  expect_true(parse_loaded_wed(resource, wed), "Loaded WED blob should parse");
  expect_eq(wed.overlayCount, std::uint32_t{2}, "WED parser should expose overlay count");
  expect_eq(wed.baseWidth, std::uint16_t{2}, "WED parser should expose base width");
  expect_eq(wed.baseHeight, std::uint16_t{2}, "WED parser should expose base height");
  expect_true(wed.overlays.size() == 2, "WED parser should keep both overlays");
  expect_true(wed.overlays[1].liquidMode == TileLiquidMode::Water,
              "Liquid tileset classifier should mark water overlays");
  expect_true(liquid_tileset_fallback_tint(wed.overlays[1].tilesetResrefView()).has_value(),
              "Parsed WTLAKE WED metadata should provide its fallback before PVRZ is ready");
  expect_eq(wed.overlays[1].coverageCells, std::uint32_t{2},
            "Liquid overlay coverage should count flagged base cells");
  expect_eq(liquid_overlay_mask(wed), std::uint8_t{0x02},
            "Liquid overlay mask should expose overlay bit");

  expect_true(wed.overlays[0].tintTileCandidates.empty(),
              "Base overlay should not carry tint tile candidates");
  expect_eq(wed.overlays[1].tintTileCandidates.size(), std::size_t{3},
            "Liquid overlay should carry bounded unique tint candidates");
  expect_eq(wed.overlays[1].tintTileCandidates[0], std::uint16_t{24},
            "Cell 0 tile index should resolve through the tile-index lookup");
  expect_eq(wed.overlays[1].tintTileCandidates[1], std::uint16_t{21},
            "Cell 1 tile index should resolve through the tile-index lookup");
  expect_eq(wed.overlays[1].tintTileCandidates[2], std::uint16_t{23},
            "Cell 2 tile index should resolve through the tile-index lookup");

  auto tooManyLayers = bytes;
  auto invalidHeader = header;
  invalidHeader.nLayers = 9;
  write_bytes(tooManyLayers, headerOffset, &invalidHeader, sizeof(invalidHeader));
  resource.pData = tooManyLayers.data();
  resource.nSize = static_cast<std::uint32_t>(tooManyLayers.size());
  expect_true(!parse_loaded_wed(resource, wed),
              "WED files with more than eight layers should fail closed");
  expect_true(wed.empty(), "A rejected WED should not leave partially parsed state");

  auto excessiveDimensions = bytes;
  auto invalidBaseLayer = baseLayer;
  invalidBaseLayer.nTilesAcross = 0xFFFF;
  invalidBaseLayer.nTilesDown = 0xFFFF;
  write_bytes(excessiveDimensions, layerOffset, &invalidBaseLayer, sizeof(invalidBaseLayer));
  resource.pData = excessiveDimensions.data();
  resource.nSize = static_cast<std::uint32_t>(excessiveDimensions.size());
  expect_true(!parse_loaded_wed(resource, wed),
              "Excessive WED dimensions should be rejected before allocation");

  resource.pData = bytes.data();
  resource.nSize = static_cast<std::uint32_t>(tilemapOffset + 3 * sizeof(WED_TileData_st));
  expect_true(!parse_loaded_wed(resource, wed),
              "A truncated base tilemap should fail instead of returning partial data");
}

void test_wed_tint_candidates_are_bounded() {
  using namespace iee::game;

  constexpr std::size_t cellCount = kMaxTintTileCandidatesPerOverlay + 1;
  constexpr std::size_t layerOffset = sizeof(WED_WedHeader_st);
  constexpr std::size_t baseTilemapOffset = layerOffset + 2 * sizeof(WED_LayerHeader_st);
  constexpr std::size_t overlayTilemapOffset =
      baseTilemapOffset + cellCount * sizeof(WED_TileData_st);
  constexpr std::size_t lookupOffset = overlayTilemapOffset + cellCount * sizeof(WED_TileData_st);
  std::vector<std::byte> bytes(lookupOffset + cellCount * sizeof(std::uint16_t));

  WED_WedHeader_st header{};
  header.nFileType = 0x20444557;
  header.nFileVersion = 0x332E3156;
  header.nLayers = 2;
  header.nOffsetToLayerHeaders = static_cast<std::uint32_t>(layerOffset);
  write_bytes(bytes, 0, &header, sizeof(header));

  WED_LayerHeader_st baseLayer{};
  baseLayer.nTilesAcross = static_cast<std::uint16_t>(cellCount);
  baseLayer.nTilesDown = 1;
  baseLayer.nOffsetToTileData = static_cast<std::uint32_t>(baseTilemapOffset);
  write_bytes(bytes, layerOffset, &baseLayer, sizeof(baseLayer));

  WED_LayerHeader_st overlayLayer{};
  overlayLayer.nTilesAcross = static_cast<std::uint16_t>(cellCount);
  overlayLayer.nTilesDown = 1;
  overlayLayer.rrTileSet = {'W', 'T', 'W', 'A', 'V', 'E', '0', '1'};
  overlayLayer.nOffsetToTileData = static_cast<std::uint32_t>(overlayTilemapOffset);
  overlayLayer.nOffsetToTileList = static_cast<std::uint32_t>(lookupOffset);
  write_bytes(bytes, layerOffset + sizeof(WED_LayerHeader_st), &overlayLayer, sizeof(overlayLayer));

  std::vector<WED_TileData_st> baseTiles(cellCount);
  std::vector<WED_TileData_st> overlayTiles(cellCount);
  std::vector<std::uint16_t> lookup(cellCount);
  for (std::size_t index = 0; index < cellCount; ++index) {
    baseTiles[index].bFlags = 0x02;
    overlayTiles[index].nStartingTile = static_cast<std::uint16_t>(index);
    lookup[index] = static_cast<std::uint16_t>(index);
  }
  write_bytes(bytes, baseTilemapOffset, baseTiles.data(), baseTiles.size() * sizeof(baseTiles[0]));
  write_bytes(bytes, overlayTilemapOffset, overlayTiles.data(),
              overlayTiles.size() * sizeof(overlayTiles[0]));
  write_bytes(bytes, lookupOffset, lookup.data(), lookup.size() * sizeof(lookup[0]));

  CRes resource{};
  resource.pData = bytes.data();
  resource.nSize = static_cast<std::uint32_t>(bytes.size());
  resource.bLoaded = true;
  WedAreaInfo wed{};
  expect_true(parse_loaded_wed(resource, wed), "Bounded-candidate WED fixture should parse");
  if (wed.overlays.size() > 1) {
    expect_eq(wed.overlays[1].tintTileCandidates.size(), kMaxTintTileCandidatesPerOverlay,
              "Liquid tint candidates must stop at the fixed memory bound");
  }
}

void test_decode_palette_tile_alpha() {
  using namespace iee::game;

  std::vector<std::uint8_t> tile(kPaletteTileBytes, 0);

  // BGRA palette entries. Entry 0 is transparent by index regardless of
  // color; entry 1 is the green key; entries 2 and 3 are opaque colors,
  // with entry 3 deliberately near-green.
  const auto setEntry = [&](std::size_t i, std::uint8_t b, std::uint8_t g, std::uint8_t r) {
    tile[i * 4 + 0] = b;
    tile[i * 4 + 1] = g;
    tile[i * 4 + 2] = r;
    tile[i * 4 + 3] = 255;
  };
  setEntry(0, 255, 0, 0);
  setEntry(1, 0, 255, 0);
  setEntry(2, 255, 255, 255);
  setEntry(3, 0, 255, 1);

  std::uint8_t* indices = tile.data() + 1024;
  std::fill(indices, indices + kTilePixels * kTilePixels, std::uint8_t{2});
  indices[0] = 0;
  indices[1] = 1;
  indices[2] = 3;

  const auto alpha = decode_palette_tile_alpha(tile.data(), tile.size());
  expect_true(alpha.has_value(), "Full-size palette tile should decode");
  expect_eq(alpha->opaque[0], std::uint8_t{0}, "Palette index 0 should be transparent");
  expect_eq(alpha->opaque[1], std::uint8_t{0}, "Green-key palette entries should be transparent");
  expect_eq(alpha->opaque[2], std::uint8_t{1}, "Near-green palette entries should stay opaque");
  expect_eq(alpha->opaque[3], std::uint8_t{1}, "Ordinary palette entries should be opaque");
  expect_eq(alpha->opaque[kTilePixels * kTilePixels - 1], std::uint8_t{1},
            "Last pixel should decode like any other");

  expect_true(!decode_palette_tile_alpha(tile.data(), kPaletteTileBytes - 1).has_value(),
              "Undersized buffers should not decode as palette tiles");
  expect_true(!decode_palette_tile_alpha(nullptr, kPaletteTileBytes).has_value(),
              "Null buffers should not decode");

  // Average opaque color in linear light: half pure red, half pure blue ->
  // (0.5, 0, 0.5).
  std::vector<std::uint8_t> colorTile(kPaletteTileBytes, 0);
  colorTile[2 * 4 + 2] = 255;  // entry 2: red (BGRA)
  colorTile[3 * 4 + 0] = 255;  // entry 3: blue
  std::uint8_t* colorIndices = colorTile.data() + 1024;
  for (int i = 0; i < kTilePixels * kTilePixels; ++i) {
    colorIndices[i] = (i < kTilePixels * kTilePixels / 2) ? 2 : 3;
  }
  const auto avg = palette_tile_average_color(colorTile.data(), colorTile.size());
  expect_true(avg.has_value(), "Opaque tile should yield an average color");
  if (avg) {
    expect_true(avg->linearRgb[0] == 0.5f && avg->linearRgb[1] == 0.0f && avg->linearRgb[2] == 0.5f,
                "Average color should be the exact opaque-pixel mean");
    expect_eq(avg->opaquePixelCount, std::size_t{kTilePixels * kTilePixels},
              "Average should report its opaque-pixel weight");
  }
  // Mid-grey is encoded sRGB. A linear-light average must decode it before
  // feeding shader math rather than returning 128/255 (~0.502).
  std::vector<std::uint8_t> greyTile(kPaletteTileBytes, 0);
  greyTile[4] = 128;
  greyTile[5] = 128;
  greyTile[6] = 128;
  std::fill(greyTile.begin() + 1024, greyTile.end(), std::uint8_t{1});
  const auto grey = palette_tile_average_color(greyTile.data(), greyTile.size());
  expect_true(grey.has_value(), "Opaque grey tile should yield an average color");
  if (grey) {
    expect_true(std::abs(grey->linearRgb[0] - 0.215861f) < 0.00001f &&
                    std::abs(grey->linearRgb[1] - 0.215861f) < 0.00001f &&
                    std::abs(grey->linearRgb[2] - 0.215861f) < 0.00001f,
                "Palette averages should be decoded into linear light");
  }

  // Fully transparent tile (all indices 0) -> no average color.
  std::vector<std::uint8_t> emptyTile(kPaletteTileBytes, 0);
  emptyTile[1] = 255;  // entry 0 green just to vary the palette
  expect_true(!palette_tile_average_color(emptyTile.data(), emptyTile.size()).has_value(),
              "Fully transparent tiles should yield no average color");

  // GPU-decompressed PVRZ pages are RGBA. Transparent atlas padding must not
  // dilute the authored tint; only the two visible pixels contribute here.
  const std::array<std::uint8_t, 16> rgba{{
      255, 0, 0, 255,
      0, 0, 255, 255,
      255, 255, 255, 0,
      0, 255, 0, 0,
  }};
  const auto rgbaAverage = rgba_image_average_color(rgba.data(), 2, 2);
  expect_true(rgbaAverage.has_value(), "Visible RGBA pixels should yield an average color");
  if (rgbaAverage) {
    expect_true(rgbaAverage->linearRgb[0] == 0.5f && rgbaAverage->linearRgb[1] == 0.0f &&
                    rgbaAverage->linearRgb[2] == 0.5f,
                "RGBA averages should ignore fully transparent atlas padding");
    expect_eq(rgbaAverage->opaquePixelCount, std::size_t{2},
              "RGBA average should report visible-pixel weight");
  }
  expect_true(!rgba_image_average_color(rgba.data(), 0, 2).has_value(),
              "Zero-width RGBA images should fail closed");
  expect_true(!rgba_image_average_color(nullptr, 2, 2).has_value(),
              "Null RGBA images should fail closed");
}

void test_tile_table_detection_ignores_garbage_steps() {
  using namespace iee::game;

  TileInfo tileInfo{};
  std::array<PVRZTileEntry, 3> table{{
      {17, 2384508, 1854076},
      {17, 799324, 1333884},
      {17, 3420796, 805484},
  }};
  tileInfo.table = table.data();
  tileInfo.tileCount = static_cast<std::uint32_t>(table.size());

  const auto detection = infer_scale_from_tile_table(tileInfo);
  expect_true(!detection.has_value(),
              "Tile-table detection should ignore garbage UV steps instead of treating them as "
              "deterministic scale");
}

void test_tile_table_detection_uses_coordinate_deltas() {
  using namespace iee::game;

  TileInfo upscaledInfo{};
  std::array<PVRZTileEntry, 4> upscaledTable{{
      {7, 128, 64},
      {7, 384, 64},
      {7, 128, 320},
      {8, 129, 65},  // A different page must not affect the grid step.
  }};
  upscaledInfo.table = upscaledTable.data();
  upscaledInfo.tileCount = static_cast<std::uint32_t>(upscaledTable.size());
  const auto upscaled = infer_scale_from_tile_table(upscaledInfo);
  expect_true(upscaled.has_value(), "Translated 4x atlas coordinates should resolve");
  if (upscaled) {
    expect_eq(upscaled->scaleFactor, 4, "A 256px coordinate grid should resolve to 4x");
  }

  TileInfo standardInfo{};
  std::array<PVRZTileEntry, 3> standardTable{{
      {2, 192, 128},
      {2, 256, 128},
      {2, 192, 192},
  }};
  standardInfo.table = standardTable.data();
  standardInfo.tileCount = static_cast<std::uint32_t>(standardTable.size());
  const auto standard = infer_scale_from_tile_table(standardInfo);
  expect_true(standard.has_value(), "Translated standard atlas coordinates should resolve");
  if (standard) {
    expect_eq(standard->scaleFactor, 1, "A 64px coordinate grid should resolve to standard");
  }
}

void test_manifest_infgame_offsets() {
  const auto& m = iee::game::current_manifest();
  expect_eq(m.offsets.infGameVisibleArea, std::uintptr_t{0x6590}, "visible area offset");
  expect_eq(m.offsets.infGameAreas, std::uintptr_t{0x6598}, "areas array offset");
  expect_eq(m.offsets.infGameAreaMaster, std::uintptr_t{0x65F8}, "master area offset");
  expect_true(m.validate(), "manifest still validates");
}

iee::game::TileInfo make_tile_info(std::uint32_t tileDimension, int texId, int u, int v,
                                   bool includeHeader = true, bool* outLinearFlag = nullptr) {
  const auto& manifest = iee::game::current_manifest();

  static std::vector<std::byte> vidTileStorage;
  static std::vector<std::byte> tilesetStorage;
  static iee::game::TisFileHeader header;
  static std::array<iee::game::PVRZTileEntry, 2> table;
  static iee::game::CResTile resource;

  vidTileStorage.assign(manifest.offsets.vidTileResource + sizeof(iee::game::CResTile*),
                        std::byte{0});
  tilesetStorage.assign(manifest.offsets.tisLinearTilesFlag + sizeof(std::int32_t), std::byte{0});

  auto* tileset = reinterpret_cast<iee::game::CResTileSet*>(tilesetStorage.data());
  header = {};
  header.tileDimension = tileDimension;

  table[0] = iee::game::PVRZTileEntry{texId, 0, 0};
  table[1] = iee::game::PVRZTileEntry{texId, u, v};
  resource = {};
  resource.tis = tileset;
  resource.tileIndex = 0;

  tileset->baseclass_0.pData = table.data();
  tileset->baseclass_0.nSize = static_cast<std::uint32_t>(sizeof(iee::game::PVRZTileEntry));
  tileset->baseclass_0.nCount = static_cast<std::uint32_t>(table.size());
  tileset->h = includeHeader ? &header : nullptr;

  if (outLinearFlag) {
    const auto linearValue = *outLinearFlag ? 1 : 0;
    std::memcpy(tilesetStorage.data() + manifest.offsets.tisLinearTilesFlag, &linearValue,
                sizeof(linearValue));
  }

  auto* resourcePtr = &resource;
  std::memcpy(vidTileStorage.data() + manifest.offsets.vidTileResource, &resourcePtr,
              sizeof(resourcePtr));

  iee::game::TileInfo info{};
  const auto demand_passthrough = +[](void* p) -> void* { return p; };
  expect_true(iee::game::get_tile_info(vidTileStorage.data(), manifest, info, demand_passthrough),
              "get_tile_info should decode the synthetic CVidTile payload");
  return info;
}

void test_tis_header_dimension_decoding() {
  const auto& manifest = iee::game::current_manifest();
  auto tileInfo = make_tile_info(iee::game::TisTileDimensions::Upscaled4x, 15000,
                                 static_cast<int>(iee::game::TisTileDimensions::Upscaled4x), 0);

  const auto tileDimension = iee::game::get_tis_header_tile_dimension(tileInfo, manifest);
  expect_true(tileDimension.has_value(), "TIS header tile dimension should be readable");
  if (tileDimension) {
    expect_eq(*tileDimension, std::uint32_t{0x100},
              "4x tile dimension should decode from the header");
  }

  const auto detection = iee::game::detect_scale_from_tis_header(tileInfo, manifest);
  expect_true(detection.has_value(), "Known tile dimensions should resolve from the header");
  if (detection) {
    expect_eq(detection->scaleFactor, 4, "Header-based detection should map 0x100 to 4x scale");
    expect_true(detection->source == iee::game::ScaleDetectionSource::TisHeader,
                "Header-based detection should report the correct source");
  }
}

void test_supported_tile_dimensions_are_inferred_dynamically() {
  using namespace iee::game;

  for (const auto& [dimension, expectedScale] : std::array<std::pair<std::uint32_t, int>, 4>{{
           {TisTileDimensions::Standard, 1},
           {TisTileDimensions::Upscaled2x, 2},
           {TisTileDimensions::Upscaled4x, 4},
           {TisTileDimensions::Upscaled8x, 8},
       }}) {
    const auto scale = scale_factor_from_tile_dimension(dimension);
    expect_true(scale.has_value(), "supported power-of-two tile dimension should resolve");
    if (scale) expect_eq(*scale, expectedScale, "tile dimension should map to its scale factor");

    auto headerInfo = make_tile_info(dimension, 100, static_cast<int>(dimension), 0);
    const auto headerDetection = detect_scale_from_tis_header(headerInfo, current_manifest());
    expect_true(headerDetection.has_value(), "every supported header dimension should resolve");
    if (headerDetection) {
      expect_eq(headerDetection->scaleFactor, expectedScale,
                "header dimension should drive the same dynamic scale mapping");
    }
  }

  for (const auto dimension :
       {std::uint32_t{0}, std::uint32_t{96}, std::uint32_t{192}, std::uint32_t{1024}}) {
    expect_true(!scale_factor_from_tile_dimension(dimension).has_value(),
                "unsupported tile dimensions must fail closed");
  }

  TileInfo tableInfo{};
  std::array<PVRZTileEntry, 3> table{{
      {2, 64, 64},
      {2, 576, 64},
      {2, 64, 576},
  }};
  tableInfo.table = table.data();
  tableInfo.tileCount = static_cast<std::uint32_t>(table.size());
  const auto tableDetection = infer_scale_from_tile_table(tableInfo);
  expect_true(tableDetection.has_value(), "512px table grid should resolve dynamically");
  if (tableDetection) expect_eq(tableDetection->scaleFactor, 8, "512px grid should map to 8x");
}

void test_tis_table_entry_bounds() {
  using namespace iee::game;

  std::array<PVRZTileEntry, 1> table{{{3, 64, 128}}};
  TileInfo info{};
  info.table = table.data();
  info.tileCount = static_cast<std::uint32_t>(table.size());

  PVRZTileEntry entry{};
  expect_true(read_tis_tile_entry(info, 0, entry), "In-range TIS entries should be readable");
  expect_eq(entry.page, 3, "The requested TIS entry should be returned");
  expect_true(!read_tis_tile_entry(info, 1, entry),
              "TIS entry reads must reject indices at the count boundary");

  info.table = reinterpret_cast<const PVRZTileEntry*>((std::numeric_limits<std::uintptr_t>::max)() -
                                                      sizeof(PVRZTileEntry) + 1);
  info.tileCount = 2;
  expect_true(!read_tis_tile_entry(info, 1, entry),
              "TIS entry address arithmetic must reject integer overflow");

  auto overflowManifest = current_manifest();
  constexpr auto nearAddress = (std::numeric_limits<std::uintptr_t>::max)() - 3;
  overflowManifest.offsets.vidTileResource = 8;
  expect_true(!get_tile_info(reinterpret_cast<void*>(nearAddress), overflowManifest, info, nullptr),
              "CVidTile field address arithmetic must reject integer overflow");

  info.header = reinterpret_cast<const TisFileHeader*>(nearAddress);
  overflowManifest.offsets.tisHeaderTileDimension = 8;
  expect_true(!get_tis_header_tile_dimension(info, overflowManifest).has_value(),
              "TIS header field address arithmetic must reject integer overflow");

  overflowManifest.offsets.tisLinearTilesFlag = 8;
  expect_true(!get_tis_linear_tiles_flag(reinterpret_cast<const CResTileSet*>(nearAddress),
                                         overflowManifest),
              "TIS linear-flag address arithmetic must reject integer overflow");
}

void test_tileset_runtime_cache_is_bounded_and_resettable() {
  iee::features::TileRenderState state{};
  for (std::size_t i = 0; i < iee::features::TileRenderState::kMaxTilesetsPerArea; ++i) {
    const auto* tileset = reinterpret_cast<const iee::game::CResTileSet*>(i + 1);
    expect_true(state.find_or_add(tileset) != nullptr,
                "The bounded cache should accept its documented tileset capacity");
  }
  const auto* overflow = reinterpret_cast<const iee::game::CResTileSet*>(
      iee::features::TileRenderState::kMaxTilesetsPerArea + 1);
  expect_true(state.find_or_add(overflow) == nullptr,
              "The tileset cache must fail closed instead of growing without a bound");

  state.reset();
  expect_eq(state.tilesetCount, std::size_t{0}, "Area reset should release all cached tilesets");
  expect_true(state.find_or_add(overflow) != nullptr,
              "A reset cache should accept tilesets from the next area");
}

void test_scale_selection_precedence() {
  const auto& manifest = iee::game::current_manifest();

  auto standardInfo = make_tile_info(iee::game::TisTileDimensions::Standard, 20000,
                                     static_cast<int>(iee::game::TisTileDimensions::Standard), 0);
  const auto standardDetection = iee::game::detect_scale(standardInfo, 20000, manifest);
  expect_true(standardDetection.has_value(), "Header-first detection should produce a scale hint");
  if (standardDetection) {
    expect_eq(standardDetection->scaleFactor, 1,
              "Standard header values should win over heuristics");
    expect_true(standardDetection->source == iee::game::ScaleDetectionSource::TisHeader,
                "Standard header values should report TIS-header provenance");
  }

  auto tableOnlyInfo = make_tile_info(
      0x80, 20000, static_cast<int>(iee::game::TisTileDimensions::Upscaled4x), 0, false);
  const auto tableDetection = iee::game::detect_scale(tableOnlyInfo, 20000, manifest);
  expect_true(tableDetection.has_value(),
              "Table-derived detection should be used when the header is missing");
  if (tableDetection) {
    expect_eq(tableDetection->scaleFactor, 4, "Table-derived detection should detect 4x tiles");
    expect_true(tableDetection->source == iee::game::ScaleDetectionSource::TileTable,
                "Fallback should prefer deterministic table provenance over heuristics");
  }

  auto heuristicInfo = make_tile_info(0x80, 20000, 4096, 4096);
  heuristicInfo.header = nullptr;
  heuristicInfo.tileCount = 1;
  const auto heuristicDetection = iee::game::detect_scale(heuristicInfo, 20000, manifest);
  expect_true(heuristicDetection.has_value(), "Heuristics should still exist as a final fallback");
  if (heuristicDetection) {
    expect_eq(heuristicDetection->scaleFactor, 4,
              "Heuristic fallback should still detect upscaled tiles");
    expect_true(heuristicDetection->source == iee::game::ScaleDetectionSource::Heuristic,
                "Final fallback should report heuristic provenance");
  }

  bool linearFlag = true;
  auto linearInfo = make_tile_info(iee::game::TisTileDimensions::Upscaled4x, 12000,
                                   static_cast<int>(iee::game::TisTileDimensions::Upscaled4x), 0,
                                   true, &linearFlag);
  expect_true(iee::game::get_tis_linear_tiles_flag(linearInfo.tileset, manifest),
              "The manifest linear-tiles offset should be readable from synthetic data");
}

void test_shader_name_extraction() {
  using iee::game::extract_shader_name;
  expect_eq(extract_shader_name("// fpSEAM.glsl\nuniform float uTcScale;", "fp"),
            std::string("fpSEAM"), "extracts fp name");
  expect_eq(extract_shader_name("// vpDraw.glsl\nvoid main(){}", "vp"), std::string("vpDraw"),
            "extracts vp name");
  expect_true(extract_shader_name("// vpDraw.glsl\n", "fp").empty(), "prefix filter rejects vp");
  expect_true(extract_shader_name("no comment here", "fp").empty(), "no name -> empty");
}

void test_interface_contract() {
  const std::string_view original =
      "// fpSEAM.glsl\nuniform sampler2D sTex;\nuniform float uTcScale;\nvarying vec2 vTc;\nvoid "
      "main(){}";
  const std::string_view good =
      "#version 460 compatibility\nuniform sampler2D sTex;\nuniform float uTcScale;\nvarying vec2 "
      "vTc;\nvoid main(){}";
  const std::string_view bad = "#version 460 compatibility\nuniform sampler2D sTex;\nvoid main(){}";
  expect_true(iee::game::check_interface_contract(original, good).ok, "matching interface passes");
  const auto failed = iee::game::check_interface_contract(original, bad);
  expect_true(!failed.ok, "missing identifiers fail");
  expect_eq(failed.missingIdentifiers.size(), std::size_t{2}, "uTcScale and vTc reported");
}

// Regression: sTex is a substring of sTex1; a replacement declaring only sTex1 must NOT
// satisfy the sTex contract check (multi-texture blend shaders use both samplers).
void test_interface_contract_token_boundary() {
  const std::string_view original =
      "// fpBLEND.glsl\nuniform sampler2D sTex;\nuniform sampler2D sTex1;\nvoid main(){}";
  // Replacement that correctly declares both:
  const std::string_view good = "uniform sampler2D sTex;\nuniform sampler2D sTex1;\nvoid main(){}";
  // Replacement that omits sTex (only has sTex1 — which contains "sTex" as substring):
  const std::string_view bad_stex_only1 = "uniform sampler2D sTex1;\nvoid main(){}";
  expect_true(iee::game::check_interface_contract(original, good).ok,
              "both sTex and sTex1 present -> passes");
  const auto failed = iee::game::check_interface_contract(original, bad_stex_only1);
  expect_true(!failed.ok, "sTex1 must not satisfy sTex contract (token-boundary check)");
  expect_eq(failed.missingIdentifiers.size(), std::size_t{1}, "only sTex missing");
  expect_eq(failed.missingIdentifiers[0], std::string("sTex"), "missing identifier is sTex");
}
}  // namespace

void test_area_liquid_texture_packing() {
  iee::game::WedAreaInfo wed{};
  wed.baseWidth = 2;
  wed.baseHeight = 2;
  wed.overlays.resize(3);
  wed.overlays[1].liquidMode = iee::game::TileLiquidMode::Water;
  wed.overlays[2].liquidMode = iee::game::TileLiquidMode::Lava;
  // cell flags: bit N set = overlay N covers the cell
  wed.baseOverlayFlags = {
      0x00,  // no overlays -> mode 0
      0x02,  // overlay 1 (water) -> mode 1
      0x04,  // overlay 2 (lava) -> mode 2
      0x06,  // overlays 1+2 -> lowest overlay index wins -> mode 1
  };
  const auto packed = iee::game::pack_area_liquid_texture(wed);
  expect_true(packed.has_value(), "packs valid wed");
  if (packed) {
    expect_eq(packed->width, 2, "liquid width");
    expect_eq(packed->height, 2, "liquid height");
    expect_eq(packed->texels[0], std::uint8_t{0}, "no overlay -> 0");
    expect_eq(packed->texels[1], std::uint8_t{1}, "water overlay -> 1");
    expect_eq(packed->texels[2], std::uint8_t{2}, "lava overlay -> 2");
    expect_eq(packed->texels[3], std::uint8_t{1}, "first liquid overlay wins");
  }
}

void test_oil_liquid_classification() {
  using iee::game::TileLiquidMode;
  using iee::game::classify_liquid_tileset;
  using iee::game::tile_liquid_mode_name;

  expect_true(classify_liquid_tileset("WTOIL") == TileLiquidMode::Oil,
              "WTOIL should use the liquid shader path");
  expect_true(classify_liquid_tileset("wtoil06") == TileLiquidMode::Oil,
              "WTOIL classification should be case-insensitive");
  expect_true(tile_liquid_mode_name(TileLiquidMode::Oil) == "oil",
              "Oil liquid mode should have a stable diagnostic name");
  expect_true(classify_liquid_tileset("WTUNKNOWN") == TileLiquidMode::None,
              "Unknown WT overlays must remain unclassified");
}

void test_lava_variant_liquid_classification() {
  using iee::game::TileLiquidMode;
  using iee::game::classify_liquid_tileset;

  for (const std::string_view resref : {"WTLAVA", "WTLAVB", "WTLAVC", "WTLAVD"}) {
    expect_true(classify_liquid_tileset(resref) == TileLiquidMode::Lava,
                "Every AR2903 lava overlay must use the lava shader path");
  }
}

void test_liquid_tileset_fallback_tint() {
  using iee::game::liquid_tileset_fallback_tint;

  struct ExpectedTint {
    std::string_view resref;
    std::array<float, 3> linearRgb;
  };
  constexpr std::array expected{
      ExpectedTint{"WTLAKA", {0.067051f, 0.368126f, 0.406010f}},
      ExpectedTint{"WTLAKB", {0.067983f, 0.372867f, 0.409764f}},
      ExpectedTint{"WTLAKC", {0.066039f, 0.363237f, 0.403121f}},
      ExpectedTint{"WTLAKD", {0.067860f, 0.371557f, 0.409053f}},
      ExpectedTint{"WTLAKE", {0.062000f, 0.089000f, 0.117000f}},
      ExpectedTint{"WTPOOL", {0.089065f, 0.149378f, 0.234645f}},
      ExpectedTint{"WTSWAM", {0.036129f, 0.099635f, 0.094358f}},
      ExpectedTint{"WTSEW", {0.044581f, 0.059381f, 0.041765f}},
      ExpectedTint{"WTOIL", {0.019028f, 0.015909f, 0.020098f}},
  };
  for (const auto& expectedTint : expected) {
    const auto actual = liquid_tileset_fallback_tint(expectedTint.resref);
    expect_true(actual.has_value(),
                "Every processed liquid should have an authored fallback tint");
    if (!actual) continue;
    expect_true(std::abs((*actual)[0] - expectedTint.linearRgb[0]) < 0.000001f &&
                    std::abs((*actual)[1] - expectedTint.linearRgb[1]) < 0.000001f &&
                    std::abs((*actual)[2] - expectedTint.linearRgb[2]) < 0.000001f,
                "Processed-liquid fallback should preserve its measured linear tint");
  }
  expect_true(liquid_tileset_fallback_tint("wtlake") ==
                  liquid_tileset_fallback_tint("WTLAKE"),
              "Liquid fallback lookup should be case-insensitive");
  expect_true(!liquid_tileset_fallback_tint("WTUNKNOWN").has_value(),
              "Uncalibrated water overlays must not inherit another liquid's tint");
  expect_true(!liquid_tileset_fallback_tint("WTLAVA").has_value(),
              "Lava keeps its dedicated shader palette rather than a water fallback");
}

void test_area_liquid_texture_packing_rejects_mismatch() {
  iee::game::WedAreaInfo wed{};
  wed.baseWidth = 3;
  wed.baseHeight = 1;
  wed.baseOverlayFlags = {0x00};  // wrong size
  expect_true(!iee::game::pack_area_liquid_texture(wed).has_value(),
              "flag/dimension mismatch -> nullopt");
  iee::game::WedAreaInfo empty{};
  expect_true(!iee::game::pack_area_liquid_texture(empty).has_value(), "empty -> nullopt");
}

void test_fpseam_override_asset_contract() {
  namespace fs = std::filesystem;
  const fs::path assetPath = fs::path("assets") / "override" / "fpSEAM.glsl";
  std::ifstream file(assetPath, std::ios::binary);
  expect_true(static_cast<bool>(file), "fpSEAM override asset exists (run tests from repo root)");
  if (!file) return;
  std::ostringstream contents;
  contents << file.rdbuf();
  const std::string source = contents.str();

  // Engine interface (from the live vanilla dump) must be fully preserved.
  constexpr std::string_view vanillaInterface =
      "uniform sampler2D uTex;\n"
      "uniform vec2 uTcScale;\n"
      "uniform vec4 uColorTone;\n"
      "varying vec2 vTc;\n"
      "varying vec2 vRef;\n"
      "varying vec4 vColor;\n";
  const auto contract = iee::game::check_interface_contract(vanillaInterface, source);
  expect_true(contract.ok, "fpSEAM override preserves the engine interface");
  for (const auto& missing : contract.missingIdentifiers) {
    std::cerr << "  missing identifier: " << missing << '\n';
  }

  // Our feed contract.
  for (const std::string_view name :
       {"uIeeEnabled", "uIeeTime", "uIeeScroll", "uIeeZoom", "uIeeViewport", "uIeeWorldSizeInv",
        "uIeeWaterTint", "uIeeAreaMask", "uIeeNormalMap", "uIeeDudvMap", "uIeeFoamMap"}) {
    expect_true(source.find(name) != std::string::npos, "fpSEAM override declares feed uniform");
  }
  expect_true(source.find("#version") == std::string::npos,
              "no #version line (engine sources are ARB-era GLSL)");
  expect_true(
      source.find("ieeCoverageWithCenter") != std::string::npos &&
          source.find("ieeShoreFactor(vec2 worldPos, float centerCoverage)") != std::string::npos,
      "water shader should reuse center coverage instead of resampling it");
  expect_true(source.find("ieeSrgbToLinear") != std::string::npos &&
                  source.find("ieeLinearToSrgb") != std::string::npos,
              "water grading should explicitly cross the encoded/linear color boundary");
  expect_true(source.find("min(edgeDistance.x, edgeDistance.y) > 8.0") != std::string::npos,
              "interior land fragments should skip provably redundant coverage fetches");
  expect_true(source.find("if (ieeIsInteriorWater(worldPos, centerCoverage))") !=
                      std::string::npos &&
                  source.find("vec2(-cell, -cell)") != std::string::npos,
              "confirmed interior water should skip the shoreline filter");
  expect_true(source.find("cellMode > 3.5 && cellMode < 4.5") != std::string::npos &&
                  source.find("foamStrength = 0.18") != std::string::npos &&
                  source.find("specularStrength = 0.08") != std::string::npos,
              "sewage should keep its dedicated dirty low-reflection grade");
}

int main() {
  test_creature_sprite_xn_native_border_geometry();
  test_creature_sprite_native_pixel_encodings();
  test_creature_sprite_transient_texture_lifecycle();
  test_creature_sprite_registry_formats();
  test_parse_ida_pattern();
  test_unique_pattern_matching();
  test_detour_tolerant_matching();
  test_rel32_target_checked();
  test_writable_non_executable_guards();
  test_manifest_loading();
  test_runtime_type_layouts();
  test_file_format_layouts();
  test_eeex_doc_layout_maps();
  test_config_parsing();
  test_config_numeric_bounds();
  test_config_reports_malformed_values();
  test_config_shader_override_defaults();
  test_config_shader_override_roundtrip();
  test_performance_sample_summary();
  test_area_animation_clock_probe();
  test_area_animation_timeline_clock();
  test_area_animation_registry_formats();
  test_parse_dds_legacy_formats_and_mips();
  test_parse_dds_dx10_formats();
  test_parse_dds_rejects_unsupported_or_malformed_input();
  test_load_dds_texture_file_wrapper();
  test_parse_loaded_wed();
  test_wed_tint_candidates_are_bounded();
  test_decode_palette_tile_alpha();
  test_tis_header_dimension_decoding();
  test_supported_tile_dimensions_are_inferred_dynamically();
  test_tis_table_entry_bounds();
  test_tileset_runtime_cache_is_bounded_and_resettable();
  test_scale_selection_precedence();
  test_tile_table_detection_ignores_garbage_steps();
  test_tile_table_detection_uses_coordinate_deltas();
  test_manifest_infgame_offsets();
  test_shader_name_extraction();
  test_interface_contract();
  test_interface_contract_token_boundary();
  test_area_liquid_texture_packing();
  test_oil_liquid_classification();
  test_lava_variant_liquid_classification();
  test_liquid_tileset_fallback_tint();
  test_area_liquid_texture_packing_rejects_mismatch();
  test_fpseam_override_asset_contract();

  if (g_failures != 0) {
    std::cerr << g_failures << " test(s) failed\n";
    return 1;
  }

  std::cout << "All InfinityEngine-Enhancer native tests passed\n";
  return 0;
}
