#include "am3000a_frame_x4_test.h"

#include <atomic>
#include <cstddef>
#include <exception>
#include <fstream>
#include <mutex>
#include <vector>

#include "iee/core/logger.h"
#include "iee/game/opengl_types.h"

namespace iee::am3000a_x4 {
namespace {
constexpr int kSourceWidth = 248;
constexpr int kSourceHeight = 221;
constexpr int kScale = 4;
constexpr int kReplacementWidth = kSourceWidth * kScale;
constexpr int kReplacementHeight = kSourceHeight * kScale;
constexpr int kReplacementBytes = kReplacementWidth * kReplacementHeight * 4;
constexpr char kAssetName[] = "AM3000A-frame000-x4.rgba";

std::mutex g_mutex;
std::vector<std::byte> g_replacement;
std::atomic<bool> g_ready{false};
std::atomic<bool> g_logged{false};
}  // namespace

bool prepare(const std::filesystem::path& assetsDirectory) noexcept {
  try {
    const auto assetPath = assetsDirectory / kAssetName;
    std::ifstream file(assetPath, std::ios::binary | std::ios::ate);
    if (!file) {
      LOG_WARN("AM3000A x4 test skipped: missing {}", assetPath.string());
      return false;
    }
    if (file.tellg() != kReplacementBytes) {
      LOG_WARN("AM3000A x4 test skipped: {} has {} bytes (expected {})", assetPath.string(),
               static_cast<long long>(file.tellg()), kReplacementBytes);
      return false;
    }

    file.seekg(0);
    std::vector<std::byte> loaded(kReplacementBytes);
    if (!file.read(reinterpret_cast<char*>(loaded.data()), loaded.size())) {
      LOG_WARN("AM3000A x4 test skipped: could not read {}", assetPath.string());
      return false;
    }

    std::lock_guard lock(g_mutex);
    g_ready.store(false, std::memory_order_release);
    g_replacement = std::move(loaded);
    g_logged.store(false, std::memory_order_release);
    g_ready.store(true, std::memory_order_release);
    LOG_INFO("Prepared reversible AM3000A frame 000 x4 texture: {}", assetPath.string());
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("AM3000A x4 test disabled: {}", error.what());
    return false;
  } catch (...) {
    LOG_WARN("AM3000A x4 test disabled by an unknown loading error");
    return false;
  }
}

void release() noexcept {
  std::lock_guard lock(g_mutex);
  g_ready.store(false, std::memory_order_release);
  g_replacement.clear();
  g_replacement.shrink_to_fit();
  g_logged.store(false, std::memory_order_release);
}

bool try_replacement(unsigned target, int level, int internalFormat, int width, int height,
                     int border, unsigned format, unsigned type, const void* originalData,
                     ReplacementUpload& out) noexcept {
  // AM3000A is the sole examined area object with this frame geometry. The
  // format constraints exclude indexed/mask uploads and render targets. This
  // is a reversible geometry test, not yet the final per-frame fingerprint.
  if (target != game::gl::TEXTURE_2D || level != 0 || border != 0 || width != kSourceWidth ||
      height != kSourceHeight || !originalData ||
      (internalFormat != static_cast<int>(game::gl::RGBA) &&
       internalFormat != static_cast<int>(game::gl::RGBA8))) {
    return false;
  }
  (void)format;
  (void)type;

  std::lock_guard lock(g_mutex);
  if (!g_ready.load(std::memory_order_acquire) ||
      static_cast<int>(g_replacement.size()) != kReplacementBytes) {
    return false;
  }

  out = {kReplacementWidth, kReplacementHeight, g_replacement.data()};
  if (!g_logged.exchange(true, std::memory_order_acq_rel)) {
    LOG_INFO("Replacing AM3000A 248x221 upload with frame 000 x4; draw geometry stays native");
  }
  return true;
}
}  // namespace iee::am3000a_x4
