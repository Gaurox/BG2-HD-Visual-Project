#include "am0700a_animation_x4_test.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <fstream>
#include <mutex>
#include <vector>

#include "iee/core/logger.h"
#include "iee/game/opengl_types.h"

namespace iee::am0700a_x4 {
namespace {
constexpr int kSourceWidth = 178;
constexpr int kSourceHeight = 163;
constexpr int kScale = 4;
constexpr int kReplacementWidth = kSourceWidth * kScale;
constexpr int kReplacementHeight = kSourceHeight * kScale;
constexpr int kReplacementBytes = kReplacementWidth * kReplacementHeight * 4;
constexpr int kSourceBytes = kSourceWidth * kSourceHeight * 4;
constexpr unsigned kBgra = 0x80E1;
constexpr unsigned kUnsignedInt8888Rev = 0x8367;

struct Frame {
  const char* assetName;
  // The BAM exporter gives RGBA. The EE renderer has historically exposed
  // either RGBA or BGRA here, and some paths clear transparent RGB first. The
  // four fingerprints cover those byte-exact representations only.
  std::array<std::uint64_t, 4> originalFingerprints;
  std::vector<std::byte> replacement;
};

std::array<Frame, 7> g_frames{{
    {"AM0700A-frame000-x4.rgba",
     {0xC75FB8A076E9037Cull, 0x6D1A62545673DC8Dull, 0x899D08248DCB4DD8ull,
      0x432FA51353185A81ull}, {}},
    {"AM0700A-frame001-x4.rgba",
     {0xA0D9D2189AFC359Aull, 0xCDB607A1926D7692ull, 0x02290A8C79373472ull,
      0x3FFB1777CEC683A2ull}, {}},
    {"AM0700A-frame002-x4.rgba",
     {0x22EAA7C6E02522D5ull, 0xFB794072149CB5C9ull, 0x280B36958881F419ull,
      0xA40B88AAC9299815ull}, {}},
    {"AM0700A-frame003-x4.rgba",
     {0x22825BBBE2D3CA1Full, 0xEA852D0E88211E5Eull, 0x1D2FD2551EB5C417ull,
      0x8F49A65439529046ull}, {}},
    {"AM0700A-frame004-x4.rgba",
     {0x27D1A63E3E76098Dull, 0x38AFA791048A0750ull, 0x07EB76021838DBC9ull,
      0x8AFA791048A0750ull}, {}},
    {"AM0700A-frame005-x4.rgba",
     {0xD0E7B2083C842C19ull, 0xA56CA4FA7D9AC15Dull, 0xB602FCFD9469CD4Dull,
      0x9346FD34B81B39B9ull}, {}},
    {"AM0700A-frame006-x4.rgba",
     {0x6229DBB8F530C3EBull, 0x599A9796A4850C9Eull, 0xEBBFF9198EFD2C4Full,
      0xACC365D498BC4522ull}, {}},
}};

std::mutex g_mutex;
std::atomic<bool> g_ready{false};
std::array<std::atomic<bool>, 7> g_loggedFrames{};
std::atomic<bool> g_unmatchedCandidateLogged{false};

std::uint64_t fnv1a64(const void* data, int byteCount) noexcept {
  if (!data || byteCount != kSourceBytes) return 0;
  const auto* bytes = static_cast<const unsigned char*>(data);
  std::uint64_t value = 14695981039346656037ull;
#ifdef _WIN32
  __try {
#endif
    for (int index = 0; index < byteCount; ++index) {
      value ^= bytes[index];
      value *= 1099511628211ull;
    }
#ifdef _WIN32
  } __except (EXCEPTION_EXECUTE_HANDLER) {
    return 0;
  }
#endif
  return value;
}

void reset_logs() noexcept {
  for (auto& logged : g_loggedFrames) logged.store(false, std::memory_order_release);
  g_unmatchedCandidateLogged.store(false, std::memory_order_release);
}
}  // namespace

bool prepare(const std::filesystem::path& assetsDirectory) noexcept {
  try {
    std::array<std::vector<std::byte>, 7> loaded;
    for (std::size_t index = 0; index < g_frames.size(); ++index) {
      const auto assetPath = assetsDirectory / g_frames[index].assetName;
      std::ifstream file(assetPath, std::ios::binary | std::ios::ate);
      if (!file) {
        LOG_WARN("AM0700A x4 test skipped: missing {}", assetPath.string());
        return false;
      }
      if (file.tellg() != kReplacementBytes) {
        LOG_WARN("AM0700A x4 test skipped: {} has {} bytes (expected {})", assetPath.string(),
                 static_cast<long long>(file.tellg()), kReplacementBytes);
        return false;
      }
      file.seekg(0);
      loaded[index].resize(kReplacementBytes);
      if (!file.read(reinterpret_cast<char*>(loaded[index].data()), loaded[index].size())) {
        LOG_WARN("AM0700A x4 test skipped: could not read {}", assetPath.string());
        return false;
      }
    }

    std::lock_guard lock(g_mutex);
    g_ready.store(false, std::memory_order_release);
    for (std::size_t index = 0; index < g_frames.size(); ++index) {
      g_frames[index].replacement = std::move(loaded[index]);
    }
    reset_logs();
    g_ready.store(true, std::memory_order_release);
    LOG_INFO("Prepared reversible AM0700A animation x4 textures (7 frames): {}",
             assetsDirectory.string());
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("AM0700A x4 test disabled: {}", error.what());
    return false;
  } catch (...) {
    LOG_WARN("AM0700A x4 test disabled by an unknown loading error");
    return false;
  }
}

void release() noexcept {
  std::lock_guard lock(g_mutex);
  g_ready.store(false, std::memory_order_release);
  for (auto& frame : g_frames) {
    frame.replacement.clear();
    frame.replacement.shrink_to_fit();
  }
  reset_logs();
}

bool try_replacement(unsigned target, int level, int internalFormat, int width, int height,
                     int border, unsigned format, unsigned type, const void* originalData,
                     ReplacementUpload& out) noexcept {
  // BG2EE uploads area-animation pixels either as bytes (0x1401) or as its
  // native BGRA/RGBA packed 8:8:8:8-reversed representation (0x8367). Both
  // have exactly four bytes per pixel, so they can be fingerprinted before
  // substituting. Reject every other packing and every non-colour upload.
  if (target != game::gl::TEXTURE_2D || level != 0 || border != 0 || width != kSourceWidth ||
      height != kSourceHeight || !originalData ||
      (type != game::gl::UNSIGNED_BYTE && type != kUnsignedInt8888Rev) ||
      (format != game::gl::RGBA && format != kBgra) ||
      (internalFormat != static_cast<int>(game::gl::RGBA) &&
       internalFormat != static_cast<int>(game::gl::RGBA8))) {
    return false;
  }

  const auto fingerprint = fnv1a64(originalData, kSourceBytes);
  std::lock_guard lock(g_mutex);
  if (!g_ready.load(std::memory_order_acquire)) return false;
  for (std::size_t index = 0; index < g_frames.size(); ++index) {
    const auto& frame = g_frames[index];
    bool matches = false;
    for (const auto candidate : frame.originalFingerprints) matches = matches || fingerprint == candidate;
    if (!matches) continue;
    if (static_cast<int>(frame.replacement.size()) != kReplacementBytes) return false;
    out = {kReplacementWidth, kReplacementHeight, frame.replacement.data()};
    if (!g_loggedFrames[index].exchange(true, std::memory_order_acq_rel)) {
      LOG_INFO("Replacing AM0700A frame {:03} 178x163 upload with x4; draw geometry stays native",
               index);
    }
    return true;
  }
  if (!g_unmatchedCandidateLogged.exchange(true, std::memory_order_acq_rel)) {
    LOG_WARN("AM0700A x4 candidate 178x163 did not match the extracted source fingerprints: "
             "fnv1a64=0x{:016X}",
             fingerprint);
  }
  return false;
}
}  // namespace iee::am0700a_x4
