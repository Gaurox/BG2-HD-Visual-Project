#include "biglogo_ui_upscale.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <fstream>
#include <mutex>
#include <string>
#include <vector>

#include <windows.h>

#include "iee/core/logger.h"
#include "iee/game/opengl_types.h"

namespace iee::biglogo {
namespace {
struct AtlasReplacement {
  const char* sourceName;
  const char* assetStem;
  int sourceWidth;
  int sourceHeight;
  int sourceByteCount;
  std::uint64_t sourceFingerprint;
  bool mainMenu;
  std::vector<std::byte> replacement;
  std::atomic<bool> ready{false};
  std::atomic<bool> logged{false};
};

// Fingerprints make this an opt-in, exact-page replacement: a same-sized upload
// from any other UI surface is always forwarded to the game unchanged.
std::array<AtlasReplacement, 15> g_atlases{{
    {"MOS0017.PVRZ", "BIGLOGO-MOS0017", 1024, 1024, 1024 * 1024,
     0x9AB16B5693C4F1EAull, false},
    {"MOS0181.PVRZ", "MAINMENU-MOS0181", 1024, 1024, 1024 * 1024,
     0xA35AC19FF6FD4C10ull, true},
    {"MOS0182.PVRZ", "SELECTOR-MOS0182", 512, 512, 512 * 512,
     0x4A6C0F19556FF84Aull, true},
    {"MOS0183.PVRZ", "SELECTOR-MOS0183", 512, 512, 512 * 512,
     0x3FEAAA2B11115E8Cull, true},
    {"MOS0184.PVRZ", "SELECTOR-MOS0184", 512, 512, 512 * 512,
     0xAFFAC5742D9338B4ull, true},
    {"MOS0185.PVRZ", "SELECTOR-MOS0185", 512, 512, 512 * 512,
     0x5D8AB0391325C7C2ull, true},
    {"MOS0140.PVRZ", "HUD-MOS0140", 1024, 1024, 1024 * 1024,
     0xB28D170B09DC019Eull, true},
    {"MOS0141.PVRZ", "HUD-MOS0141", 512, 512, 512 * 512,
     0xBB32351E53E5DDF4ull, true},
    {"MOS0257.PVRZ", "MAINMENU-MOS0257", 1024, 1024, 1024 * 1024,
     0x3CA5B769541C382Aull, true},
    {"MOS0258.PVRZ", "MAINMENU-MOS0258", 1024, 1024, 1024 * 1024,
     0x8AE1AE34D56DF1EFull, true},
    {"MOS0259.PVRZ", "SELECTOR-MOS0259", 512, 512, 512 * 512,
     0xCADBE0DA29AC3001ull, true},
    {"MOS0261.PVRZ", "MAINMENU-MOS0261", 1024, 1024, 1024 * 1024,
     0x6C7D2BC9DFDB4991ull, true},
    {"MOS0262.PVRZ", "MAINMENU-MOS0262", 512, 512, 512 * 512,
     0xDD7BEA6F3D59BE0Full, true},
    {"MOS0265.PVRZ", "MAINMENU-MOS0265", 512, 512, 512 * 512,
     0x5D70F0CB50989250ull, true},
    {"MOS0266.PVRZ", "MAINMENU-MOS0266", 512, 512, 512 * 512,
     0x767D769A9564FAA8ull, true},
}};

std::mutex g_mutex;
int g_scale{};

std::uint64_t fnv1a64(const void* data, int byteCount) noexcept {
  if (!data || byteCount <= 0) return 0;
  const auto* bytes = static_cast<const unsigned char*>(data);
  std::uint64_t value = 14695981039346656037ull;
  __try {
    for (int index = 0; index < byteCount; ++index) {
      value ^= bytes[index];
      value *= 1099511628211ull;
    }
  } __except (EXCEPTION_EXECUTE_HANDLER) {
    return 0;
  }
  return value;
}
}  // namespace

bool prepare(const std::filesystem::path& assetsDirectory, int scale, bool includeBigLogo,
             bool includeMainMenu) noexcept {
  try {
    if (scale != 2 && scale != 4) {
      LOG_WARN("Menu texture replacement disabled: unsupported scale x{}", scale);
      return false;
    }
    bool preparedAny = false;
    std::lock_guard lock(g_mutex);
    g_scale = 0;
    for (auto& atlas : g_atlases) {
      const bool requested = atlas.mainMenu ? includeMainMenu : includeBigLogo;
      atlas.ready.store(false, std::memory_order_release);
      atlas.logged.store(false, std::memory_order_release);
      atlas.replacement.clear();
      if (!requested) continue;

      const auto assetPath = assetsDirectory /
                             (std::string(atlas.assetStem) + "-x" + std::to_string(scale) + ".dxt5");
      const int replacementByteCount = atlas.sourceByteCount * scale * scale;
      std::ifstream file(assetPath, std::ios::binary | std::ios::ate);
      if (!file) {
        LOG_WARN("{} x{} replacement skipped: missing {}", atlas.sourceName, scale, assetPath.string());
        continue;
      }
      const auto byteCount = file.tellg();
      if (byteCount != replacementByteCount) {
        LOG_WARN("{} x{} replacement skipped: {} has {} bytes (expected {})", atlas.sourceName,
                 scale, assetPath.string(), static_cast<long long>(byteCount), replacementByteCount);
        continue;
      }
      file.seekg(0);
      std::vector<std::byte> loaded(replacementByteCount);
      if (!file.read(reinterpret_cast<char*>(loaded.data()), loaded.size())) {
        LOG_WARN("{} x{} replacement skipped: could not read {}", atlas.sourceName, scale,
                 assetPath.string());
        continue;
      }
      atlas.replacement = std::move(loaded);
      atlas.ready.store(true, std::memory_order_release);
      preparedAny = true;
      LOG_INFO("Prepared reversible {} x{} atlas: {}", atlas.sourceName, scale, assetPath.string());
    }
    if (preparedAny) g_scale = scale;
    return preparedAny;
  } catch (const std::exception& error) {
    LOG_WARN("BIGLOGO x4 test disabled: {}", error.what());
    return false;
  } catch (...) {
    LOG_WARN("BIGLOGO x4 test disabled by an unknown loading error");
    return false;
  }
}

void release() noexcept {
  std::lock_guard lock(g_mutex);
  for (auto& atlas : g_atlases) {
    atlas.ready.store(false, std::memory_order_release);
    atlas.replacement.clear();
    atlas.replacement.shrink_to_fit();
  }
  g_scale = 0;
}

bool try_replacement(unsigned target, int level, unsigned internalFormat, int width, int height,
                     int byteCount, const void* originalData, ReplacementUpload& out) noexcept {
  if (target != game::gl::TEXTURE_2D || level != 0 ||
      internalFormat != game::gl::COMPRESSED_RGBA_S3TC_DXT5_EXT) {
    return false;
  }

  const auto fingerprint = fnv1a64(originalData, byteCount);

  std::lock_guard lock(g_mutex);
  if (g_scale <= 0) return false;
  for (auto& atlas : g_atlases) {
    if (!atlas.ready.load(std::memory_order_acquire) || width != atlas.sourceWidth ||
        height != atlas.sourceHeight || byteCount != atlas.sourceByteCount ||
        fingerprint != atlas.sourceFingerprint) {
      continue;
    }
    const int replacementByteCount = atlas.sourceByteCount * g_scale * g_scale;
    if (static_cast<int>(atlas.replacement.size()) != replacementByteCount) return false;
    out = {atlas.sourceWidth * g_scale, atlas.sourceHeight * g_scale, replacementByteCount,
           atlas.replacement.data()};
    if (!atlas.logged.exchange(true, std::memory_order_acq_rel)) {
      LOG_INFO("Replacing {} with x{} atlas; UI geometry stays unchanged", atlas.sourceName, g_scale);
    }
    return true;
  }
  return false;
}
}  // namespace iee::biglogo
