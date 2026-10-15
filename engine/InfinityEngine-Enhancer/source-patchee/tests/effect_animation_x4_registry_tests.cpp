#include <array>
#include <cstdio>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <chrono>
#include <thread>

#include "iee/effect_animation_x4_registry.h"
#include "iee/core/effect_playback_profile.h"

namespace {
constexpr std::array<char, 8> kMagic{{'I', 'E', 'E', 'E', 'F', 'X', '4', '\0'}};
constexpr std::array<char, 8> kResref{{'S', 'P', 'M', 'A', 'G', 'M', 'I', 'S'}};

void append_u32(std::vector<std::byte>& bytes, std::uint32_t value) {
  for (int shift = 0; shift < 32; shift += 8) {
    bytes.push_back(static_cast<std::byte>((value >> shift) & 0xFFu));
  }
}

bool write_fixture(const std::filesystem::path& directory, bool timeline = false, bool profiles = false) {
  std::error_code error;
  std::filesystem::create_directories(directory, error);
  if (error) return false;

  std::vector<std::byte> registry;
  registry.insert(registry.end(), reinterpret_cast<const std::byte*>(kMagic.data()),
                  reinterpret_cast<const std::byte*>(kMagic.data()) + kMagic.size());
  append_u32(registry, profiles ? 3 : (timeline ? 2 : 1));  // version
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

  if (profiles) {
    append_u32(registry, 1); // one alternate cycle
    append_u32(registry, 0); // cycle zero
    append_u32(registry, 12);
    for (std::uint32_t phase = 0; phase < 12; ++phase) append_u32(registry, 11 - phase);
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
bool streaming_contracts(const std::filesystem::path& root) {
  using namespace iee::effect_animation_x4;
  if (!write_fixture(root, true, true)) return false;
  Options options; options.streaming = true;
  if (!prepare(root, options)) return false;
  auto stats = cpu_cache_stats();
  FrameHandle loop{}, once{};
  const bool profiles = resolve_timeline_frame(kResref, 0, 0, 64, 64, loop) &&
      resolve_timeline_frame(kResref, 0, 0, 64, 64, once, true) &&
      loop.frameIndex == 0 && once.frameIndex == 11 && loop.generation &&
      loop.generation == once.generation;
  if (!profiles || stats.reads != 4 || stats.readyBytes != 4 * 64 * 64 * 64) return false;
  const auto oldSerial = occurrence_serial(0x1234);
  if (!oldSerial || end_occurrence(0x1234) != oldSerial || occurrence_serial(0x1234) == oldSerial)
    return false;
  release();
  // A table padded to 12 phases but only 2 native slots: window must wrap at 4.
  if (!write_fixture(root, true)) return false;
  auto path = root / "EffectAnimations-X4.registry";
  std::ifstream input(path, std::ios::binary | std::ios::ate);
  std::vector<std::byte> raw(static_cast<std::size_t>(input.tellg()));
  input.seekg(0); input.read(reinterpret_cast<char*>(raw.data()), raw.size()); input.close();
  constexpr std::size_t countOffset = 24 + 16 + 12 * 8;
  raw[countOffset] = std::byte{2};
  raw.erase(raw.begin() + countOffset + 4 + 2 * 4, raw.begin() + countOffset + 4 + 6 * 4);
  { std::ofstream out(path, std::ios::binary); out.write(reinterpret_cast<const char*>(raw.data()), raw.size()); }
  options.cpu.headBytes = 0;
  if (!prepare(root, options)) return false;
  prefetch_window(0x5678, kResref, 0, 3, false, false);
  const auto end = std::chrono::steady_clock::now() + std::chrono::seconds(3);
  while (cpu_cache_stats().reads < 4 && std::chrono::steady_clock::now() < end)
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  stats = cpu_cache_stats();
  release();
  if (stats.reads != 4 || stats.pinnedBytes != 4 * 64 * 64 * 64) return false;
  // >512 resources and >8GiB declared payload, without creating or reading RGBA.
  std::vector<std::byte> registry;
  registry.insert(registry.end(), reinterpret_cast<const std::byte*>(kMagic.data()),
                   reinterpret_cast<const std::byte*>(kMagic.data()) + 8);
  append_u32(registry, 1); append_u32(registry, 4);
  append_u32(registry, 1000); append_u32(registry, 0);
  for (unsigned i = 0; i < 1000; ++i) {
    char ref[9]{}; std::snprintf(ref, sizeof(ref), "F%07u", i);
    registry.insert(registry.end(), reinterpret_cast<const std::byte*>(ref),
                     reinterpret_cast<const std::byte*>(ref) + 8);
    for (auto value : {1u, 1u, 512u, 512u, 1u, 0u}) append_u32(registry, value);
  }
  { std::ofstream out(path, std::ios::binary); out.write(reinterpret_cast<const char*>(registry.data()), registry.size()); }
  const bool scalable = prepare(root, options) && cpu_cache_stats().reads == 0 &&
      contains_resource({'F','0','0','0','0','9','9','9'});
  release();
  return scalable && !prepare(root); // eager capacity remains its historical contract
}
}  // namespace

int main(int argc, char** argv) {
  const bool catalogueOnly = argc > 2 && std::string_view(argv[1]) == "--catalogue-only";
  const int first = catalogueOnly ? 2 : 1;
  if (argc == first + 1 || argc == first + 2) {
    iee::effect_animation_x4::Options options;
    options.streaming = catalogueOnly;
    if (catalogueOnly) options.cpu.headBytes = 0;
    const bool loaded = iee::effect_animation_x4::prepare(std::filesystem::path(argv[first]), options);
    if (!loaded || !iee::effect_animation_x4::ready()) {
      std::cerr << "external effect runtime pack rejected\n";
      return 1;
    }
    std::cout << "external effect runtime pack prepared and ready\n";
    if (argc == first + 2) {
      std::ifstream contracts(argv[first + 1]);
      std::string line;
      std::size_t checked = 0;
      if (!contracts) return 1;
      while (std::getline(contracts, line)) {
        if (line.empty()) continue;
        std::istringstream row(line);
        std::string name;
        int slot = -1, width = 0, height = 0, phase = -1;
        if (!(row >> name >> slot >> width >> height >> phase) || name.size() > 8) return 1;
        int sequence = 0, expectedNative = slot * 2, expectedTarget = phase;
        row >> std::ws;
        if (!row.eof() && !(row >> sequence >> expectedNative >> expectedTarget)) return 1;
        int once = 0;
        row >> std::ws;
        if (!row.eof() && (!(row >> once) || (once != 0 && once != 1))) return 1;
        if (sequence < 0 || expectedNative < 0 || expectedTarget < 0) return 1;
        std::array<char, 8> ref{};
        std::copy(name.begin(), name.end(), ref.begin());
        iee::effect_animation_x4::FrameHandle native{}, target{};
        iee::effect_animation_x4::TimelineInfo timing{};
        if (!iee::effect_animation_x4::contains_resource(ref) ||
            !iee::effect_animation_x4::timeline_info(ref, sequence, timing, once != 0) ||
            !timing.enabled || timing.targetFpsNumerator != 30 || timing.targetFpsDenominator != 1 ||
            !iee::effect_animation_x4::resolve_frame(ref, sequence, slot, width, height, native, once != 0) ||
            !iee::effect_animation_x4::resolve_timeline_frame(ref, sequence, phase, width, height, target, once != 0) ||
            target.frameIndex != static_cast<std::size_t>(expectedTarget) ||
            native.frameIndex != static_cast<std::size_t>(expectedNative)) {
          std::cerr << "external effect contract failed: " << line << '\n';
          return 1;
        }
        ++checked;
      }
      if (!checked) return 1;
      std::cout << "external native-slot/30fps phase contracts checked: " << checked << '\n';
    }
    if (catalogueOnly && iee::effect_animation_x4::cpu_cache_stats().reads != 0) return 1;
    if (catalogueOnly) std::cout << "catalogue-only: zero RGBA reads\n";
    iee::effect_animation_x4::release();
    return 0;
  }
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
                        iee::effect_animation_x4::contains_resource(kResref) &&
                        iee::effect_animation_x4::resolve_frame(kResref, 0, 5, 64, 64, frame);
  constexpr std::array<char, 8> mixed{{'s', 'P', 'm', 'a', 'g', 'M', 'i', 's'}};
  const bool mixedResolved = iee::effect_animation_x4::contains_resource(mixed) &&
      iee::effect_animation_x4::resolve_frame(mixed, 0, 5, 64, 64, frame);
  const bool diagnosticGates =
      iee::effect_animation_x4::mark_diagnostic_stage_once(kResref, 1) &&
      !iee::effect_animation_x4::mark_diagnostic_stage_once(mixed, 1) &&
      iee::effect_animation_x4::mark_geometry_observation_once(kResref, 0, 5) &&
      !iee::effect_animation_x4::mark_geometry_observation_once(mixed, 0, 5);
  const bool rejectedDimensions =
      !iee::effect_animation_x4::resolve_frame(kResref, 0, 5, 32, 64, frame);
  const bool rejectedFrame =
      !iee::effect_animation_x4::resolve_frame(kResref, 0, 6, 64, 64, frame);
  iee::effect_animation_x4::release();
  std::filesystem::remove_all(root, error);
  const bool timelineWritten = write_fixture(root, true);
  iee::effect_animation_x4::TimelineInfo timing{};
  const bool timelineLoaded = timelineWritten && iee::effect_animation_x4::prepare(root) &&
                              iee::effect_animation_x4::timeline_info(mixed, 0, timing) &&
                              timing.enabled && timing.nativeFpsNumerator == 15 &&
                              timing.targetFpsNumerator == 30 && timing.phaseCount == 12 &&
                              iee::effect_animation_x4::resolve_timeline_frame(
                                  mixed, 0, 11, 64, 64, frame);
  iee::effect_animation_x4::release();
  std::filesystem::remove_all(root, error);
  const bool profileWritten = write_fixture(root, true, true);
  const bool profileLoaded = profileWritten && iee::effect_animation_x4::prepare(root);
  const bool profileResolved = profileLoaded &&
      iee::effect_animation_x4::resolve_timeline_frame(mixed, 0, 0, 64, 64, frame, true) && frame.frameIndex == 11 &&
      iee::effect_animation_x4::resolve_frame(mixed, 0, 5, 64, 64, frame, true) && frame.frameIndex == 1 &&
      iee::effect_animation_x4::resolve_timeline_frame(mixed, 0, 0, 64, 64, frame) && frame.frameIndex == 0;
  iee::effect_animation_x4::release();
  std::filesystem::remove_all(root, error);
  const bool malformedWritten = write_fixture(root, true, true);
  bool malformedRejected = false;
  if (malformedWritten) {
    std::fstream bad(root / "EffectAnimations-X4.registry", std::ios::binary | std::ios::in | std::ios::out);
    bad.seekp(-4, std::ios::end);
    const std::uint32_t invalidBacking = 99;
    bad.write(reinterpret_cast<const char*>(&invalidBacking), sizeof(invalidBacking));
    bad.close();
    malformedRejected = !iee::effect_animation_x4::prepare(root) && !iee::effect_animation_x4::ready();
  }
  iee::effect_animation_x4::release();
  std::filesystem::remove_all(root, error);
  using iee::core::effect_once_profile;
  const bool ownerRouting = effect_once_profile(8, 0, 0, 1) &&
      !effect_once_profile(9, 0, 0, 1) && !effect_once_profile(73, 1, 0, 1) &&
      effect_once_profile(9, 1, 2, 1) && !effect_once_profile(9, 1, 2, 2) &&
      effect_once_profile(9, 1, 2, 3);
  const bool streaming = streaming_contracts(root);
  iee::effect_animation_x4::release();
  std::filesystem::remove_all(root, error);
  if (!streaming || !resolved || !mixedResolved || !diagnosticGates || !rejectedDimensions || !rejectedFrame ||
      !timelineLoaded || !profileResolved || !ownerRouting || !malformedRejected) {
    std::cerr << "effect registry resolution contract failed\n";
    return 1;
  }
  return 0;
}
