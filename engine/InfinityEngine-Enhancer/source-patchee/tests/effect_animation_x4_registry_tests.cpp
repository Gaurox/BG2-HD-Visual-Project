#include <array>
#include <cstdio>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "iee/effect_animation_x4_registry.h"

namespace {
constexpr std::array<char, 8> kMagic{{'I', 'E', 'E', 'E', 'F', 'X', '4', '\0'}};
constexpr std::array<char, 8> kResref{{'S', 'P', 'M', 'A', 'G', 'M', 'I', 'S'}};

void append_u32(std::vector<std::byte>& bytes, std::uint32_t value) {
  for (int shift = 0; shift < 32; shift += 8) {
    bytes.push_back(static_cast<std::byte>((value >> shift) & 0xFFu));
  }
}

bool write_fixture(const std::filesystem::path& directory, bool timeline = false) {
  std::error_code error;
  std::filesystem::create_directories(directory, error);
  if (error) return false;

  std::vector<std::byte> registry;
  registry.insert(registry.end(), reinterpret_cast<const std::byte*>(kMagic.data()),
                  reinterpret_cast<const std::byte*>(kMagic.data()) + kMagic.size());
  append_u32(registry, timeline ? 2 : 1);  // version
  append_u32(registry, 4);  // scale
  append_u32(registry, 1);  // resource count
  append_u32(registry, 0);  // reserved
  registry.insert(registry.end(), reinterpret_cast<const std::byte*>(kResref.data()),
                  reinterpret_cast<const std::byte*>(kResref.data()) + kResref.size());
  const auto frameCount = timeline ? 12 : 6;
  append_u32(registry, frameCount);
  append_u32(registry, 1);  // cycle count
  for (int frame = 0; frame < frameCount; ++frame) {
    append_u32(registry, 64);
    append_u32(registry, 64);
  }
  append_u32(registry, 6);
  for (std::uint32_t slot = 0; slot < 6; ++slot) {
    append_u32(registry, timeline ? slot * 2 : slot);
  }
  if (timeline) {
    append_u32(registry, 15);  // native FPS numerator
    append_u32(registry, 1);   // native FPS denominator
    append_u32(registry, 30);  // target FPS numerator
    append_u32(registry, 1);   // target FPS denominator
    append_u32(registry, 12);  // phase count
    for (std::uint32_t phase = 0; phase < 12; ++phase) append_u32(registry, phase);
  }

  std::ofstream registryStream(directory / "EffectAnimations-X4.registry", std::ios::binary);
  registryStream.write(reinterpret_cast<const char*>(registry.data()),
                       static_cast<std::streamsize>(registry.size()));
  if (!registryStream) return false;
  const std::vector<std::byte> pixels(64 * 4 * 64 * 4 * 4, std::byte{0x7F});
  for (int frame = 0; frame < frameCount; ++frame) {
    char name[64]{};
    std::snprintf(name, sizeof(name), "EFX4-SPMAGMIS-frame%03d.rgba", frame);
    std::ofstream frameStream(directory / name, std::ios::binary);
    frameStream.write(reinterpret_cast<const char*>(pixels.data()),
                      static_cast<std::streamsize>(pixels.size()));
    if (!frameStream) return false;
  }
  return true;
}
}  // namespace

int main() {
  const auto root = std::filesystem::temp_directory_path() /
                    "iee-effect-animation-x4-registry-test";
  std::error_code error;
  std::filesystem::remove_all(root, error);
  if (!write_fixture(root)) {
    std::cerr << "could not write effect registry fixture\n";
    return 1;
  }

  const bool loaded = iee::effect_animation_x4::prepare(root);
  iee::effect_animation_x4::FrameHandle frame{};
  const bool resolved = loaded && iee::effect_animation_x4::ready() &&
                        iee::effect_animation_x4::resolve_frame(kResref, 0, 5, 64, 64, frame);
  const bool rejectedDimensions =
      !iee::effect_animation_x4::resolve_frame(kResref, 0, 5, 32, 64, frame);
  const bool rejectedFrame =
      !iee::effect_animation_x4::resolve_frame(kResref, 0, 6, 64, 64, frame);
  iee::effect_animation_x4::release();
  std::filesystem::remove_all(root, error);
  const bool timelineWritten = write_fixture(root, true);
  iee::effect_animation_x4::TimelineInfo timing{};
  const bool timelineLoaded = timelineWritten && iee::effect_animation_x4::prepare(root) &&
                              iee::effect_animation_x4::timeline_info(kResref, 0, timing) &&
                              timing.enabled && timing.nativeFpsNumerator == 15 &&
                              timing.targetFpsNumerator == 30 && timing.phaseCount == 12 &&
                              iee::effect_animation_x4::resolve_timeline_frame(
                                  kResref, 0, 11, 64, 64, frame);
  iee::effect_animation_x4::release();
  std::filesystem::remove_all(root, error);
  if (!resolved || !rejectedDimensions || !rejectedFrame || !timelineLoaded) {
    std::cerr << "effect registry resolution contract failed\n";
    return 1;
  }
  return 0;
}
