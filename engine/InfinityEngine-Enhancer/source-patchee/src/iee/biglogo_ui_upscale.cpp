#include "biglogo_ui_upscale.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <exception>
#include <fstream>
#include <mutex>
#include <sstream>
#include <string>
#include <vector>

#include <windows.h>

#include "iee/core/logger.h"
#include "iee/game/opengl_types.h"

namespace iee::biglogo {
namespace {
struct AtlasReplacement {
  std::string sourceName;
  std::string assetStem;
  int sourceWidth;
  int sourceHeight;
  int sourceByteCount;
  std::uint64_t sourceFingerprint;
  bool mainMenu;
  bool selector{false};
  bool gameplayMenus{false};
  std::vector<std::byte> replacement;
  std::atomic<bool> ready{false};
  std::atomic<bool> logged{false};
};

// Fingerprints make this an opt-in, exact-page replacement: a same-sized upload
// from any other UI surface is always forwarded to the game unchanged.
std::array<AtlasReplacement, 83> g_atlases{{
    {"MOS0017.PVRZ", "BIGLOGO-MOS0017", 1024, 1024, 1024 * 1024,
     0x9AB16B5693C4F1EAull, false},
    {"MOS0181.PVRZ", "MAINMENU-MOS0181", 1024, 1024, 1024 * 1024,
     0xA35AC19FF6FD4C10ull, true, true, true},
    {"MOS0182.PVRZ", "SELECTOR-MOS0182", 512, 512, 512 * 512,
     0xBC13C466CDC91E6Cull, true, true},
    {"MOS0183.PVRZ", "SELECTOR-MOS0183", 512, 512, 512 * 512,
     0x4917CA8A551C8566ull, true, true},
    {"MOS0184.PVRZ", "SELECTOR-MOS0184", 512, 512, 512 * 512,
     0xF28D45053A121C32ull, true, true},
    {"MOS0185.PVRZ", "SELECTOR-MOS0185", 512, 512, 512 * 512,
     0x69EC1ACC79F26FA6ull, true, true},
    {"MOS0140.PVRZ", "HUD-MOS0140", 1024, 1024, 1024 * 1024,
     0xB28D170B09DC019Eull, true, false, true},
    {"MOS0141.PVRZ", "HUD-MOS0141", 512, 512, 512 * 512,
     0xBB32351E53E5DDF4ull, true},
    {"MOS0257.PVRZ", "MAINMENU-MOS0257", 1024, 1024, 1024 * 1024,
     0x3CA5B769541C382Aull, true, false, true},
    {"MOS0258.PVRZ", "MAINMENU-MOS0258", 1024, 1024, 1024 * 1024,
     0x8AE1AE34D56DF1EFull, true, true},
    {"MOS0259.PVRZ", "SELECTOR-MOS0259", 512, 512, 512 * 512,
     0xB3CABD9947A268DEull, true, true},
    {"MOS0261.PVRZ", "MAINMENU-MOS0261", 1024, 1024, 1024 * 1024,
     0x6C7D2BC9DFDB4991ull, true},
    {"MOS0262.PVRZ", "MAINMENU-MOS0262", 512, 512, 512 * 512,
     0xDD7BEA6F3D59BE0Full, true},
    {"MOS0265.PVRZ", "MAINMENU-MOS0265", 512, 512, 512 * 512,
     0x5D70F0CB50989250ull, true},
    {"MOS0266.PVRZ", "MAINMENU-MOS0266", 512, 512, 512 * 512,
     0x767D769A9564FAA8ull, true},
    {"MOS0155.PVRZ", "GAMEPLAY7B-MOS0155", 512, 512, 262144,
     0x6156C86DAEC6BD41ull, false, false, true},
    {"MOS0156.PVRZ", "GAMEPLAY7B-MOS0156", 1024, 1024, 1048576,
     0x6149DBB936586A94ull, false, false, true},
    {"MOS0180.PVRZ", "GAMEPLAY7B-MOS0180", 512, 512, 262144,
     0xA3391759DF2485E9ull, false, false, true},
    {"MOS0253.PVRZ", "GAMEPLAY7B-MOS0253", 512, 512, 262144,
     0x3E61001D272210DCull, false, false, true},
    {"MOS0254.PVRZ", "GAMEPLAY7B-MOS0254", 1024, 1024, 1048576,
     0x65152CE9B2A57770ull, false, false, true},
    {"MOS0263.PVRZ", "GAMEPLAY7B-MOS0263", 1024, 1024, 1048576,
     0x190F6A9EFC856BF3ull, false, false, true},
    {"MOS0264.PVRZ", "GAMEPLAY7B-MOS0264", 512, 512, 262144,
     0x66ACBF1162FC8B7Cull, false, false, true},
    {"MOS0255.PVRZ", "GAMEPLAY7B-MOS0255", 512, 512, 262144,
     0xFD9AAB6691721074ull, false, false, true},
    {"MOS0115.PVRZ", "GAMEPLAY7B-MOS0115", 1024, 1024, 1048576,
     0x008E9DEB92E5EC94ull, false, false, true},
    {"MOS0116.PVRZ", "GAMEPLAY7B-MOS0116", 1024, 1024, 1048576,
     0x2057D7029ED5B332ull, false, false, true},
    {"MOS0125.PVRZ", "GAMEPLAY7B-MOS0125", 1024, 1024, 1048576,
     0x2B0C2875CFE45430ull, false, false, true},
    {"MOS0126.PVRZ", "GAMEPLAY7B-MOS0126", 512, 512, 262144,
     0xD3793FB1C5527829ull, false, false, true},
    {"MOS0138.PVRZ", "GAMEPLAY7B-MOS0138", 1024, 1024, 1048576,
     0xD114EB0613D85155ull, false, false, true},
    {"MOS0139.PVRZ", "GAMEPLAY7B-MOS0139", 512, 512, 262144,
     0x2464E99333406EADull, false, false, true},
    {"MOS0148.PVRZ", "GAMEPLAY7B-MOS0148", 1024, 1024, 1048576,
     0x5B2DA9962700990Eull, false, false, true},
    {"MOS0149.PVRZ", "GAMEPLAY7B-MOS0149", 1024, 1024, 1048576,
     0xF3D5E3D46B446689ull, false, false, true},
    {"MOS0150.PVRZ", "GAMEPLAY7B-MOS0150", 512, 512, 262144,
     0x7622C17A50FCD240ull, false, false, true},
    {"MOS0154.PVRZ", "GAMEPLAY7B-MOS0154", 1024, 1024, 1048576,
     0xF46DD8C2BA42EB61ull, false, false, true},
    {"MOS0168.PVRZ", "GAMEPLAY7B-MOS0168", 512, 512, 262144,
     0xA2593ABD8E41F19Bull, false, false, true},
    {"MOS0169.PVRZ", "GAMEPLAY7B-MOS0169", 1024, 1024, 1048576,
     0x1C800B0CB51827DBull, false, false, true},
    {"MOS0107.PVRZ", "GAMEPLAY7B-MOS0107", 1024, 1024, 1048576,
     0x24A73F80DCF9F8E4ull, false, false, true},
    {"MOS0113.PVRZ", "GAMEPLAY7B-MOS0113", 512, 512, 262144,
     0xE0E11381814506F5ull, false, false, true},
    {"MOS0114.PVRZ", "GAMEPLAY7B-MOS0114", 1024, 1024, 1048576,
     0xB21FA8EA3D25CFDFull, false, false, true},
    {"MOS0124.PVRZ", "GAMEPLAY7B-MOS0124", 512, 512, 262144,
     0xDEB86947483EAE64ull, false, false, true},
    {"MOS0135.PVRZ", "GAMEPLAY7B-MOS0135", 1024, 1024, 1048576,
     0x93562AD435C68804ull, false, false, true},
    {"MOS0136.PVRZ", "GAMEPLAY7B-MOS0136", 512, 512, 262144,
     0x23708CCBA28DAE0Eull, false, false, true},
    {"MOS0147.PVRZ", "GAMEPLAY7B-MOS0147", 1024, 1024, 1048576,
     0x5AB5E03C4DCE68BDull, false, false, true},
    {"MOS0157.PVRZ", "GAMEPLAY7B-MOS0157", 1024, 1024, 1048576,
     0x9263EF75AA48959Cull, false, false, true},
    {"MOS0164.PVRZ", "GAMEPLAY7B-MOS0164", 1024, 1024, 1048576,
     0x2805DABD4EEA715Eull, false, false, true},
    {"MOS0165.PVRZ", "GAMEPLAY7B-MOS0165", 1024, 1024, 1048576,
     0x07C0761E37767165ull, false, false, true},
    {"MOS0166.PVRZ", "GAMEPLAY7B-MOS0166", 1024, 1024, 1048576,
     0xCB5CD8BED661DD9Full, false, false, true},
    {"MOS0167.PVRZ", "GAMEPLAY7B-MOS0167", 512, 512, 262144,
     0x95ACECC1C832416Cull, false, false, true},
    {"MOS0103.PVRZ", "GAMEPLAY7B-MOS0103", 512, 512, 262144,
     0xCC0066D80B1991A0ull, false, false, true},
    {"MOS0104.PVRZ", "GAMEPLAY7B-MOS0104", 512, 512, 262144,
     0x5ED5DFCF37879B3Full, false, false, true},
    {"MOS0131.PVRZ", "GAMEPLAY7B-MOS0131", 1024, 1024, 1048576,
     0x219D78EB2A07DDBCull, false, false, true},
    {"MOS0132.PVRZ", "GAMEPLAY7B-MOS0132", 512, 512, 262144,
     0xFD29002504B7D359ull, false, false, true},
    {"MOS0133.PVRZ", "GAMEPLAY7B-MOS0133", 1024, 1024, 1048576,
     0xFC8E9674F9CDBBE6ull, false, false, true},
    {"MOS0162.PVRZ", "GAMEPLAY7B-MOS0162", 1024, 1024, 1048576,
     0x62BB8834490B73DCull, false, false, true},
    {"MOS0163.PVRZ", "GAMEPLAY7B-MOS0163", 1024, 1024, 1048576,
     0xD25F30F8ECE7FD3Aull, false, false, true},
    {"MOS0176.PVRZ", "GAMEPLAY7B-MOS0176", 1024, 1024, 1048576,
     0x8E777F27AEB3EA6Dull, false, false, true},
    {"MOS0179.PVRZ", "GAMEPLAY7B-MOS0179", 1024, 1024, 1048576,
     0x3BFC5CA429FE0453ull, false, false, true},
    {"MOS0252.PVRZ", "GAMEPLAY7B-MOS0252", 512, 512, 262144,
     0x5AEE3D9E7B0EC059ull, false, false, true},
    {"MOS0110.PVRZ", "GAMEPLAY7B-MOS0110", 512, 512, 262144,
     0x56E88BD762205662ull, false, false, true},
    {"MOS0111.PVRZ", "GAMEPLAY7B-MOS0111", 1024, 1024, 1048576,
     0x18AF3ED79F0F58DDull, false, false, true},
    {"MOS0112.PVRZ", "GAMEPLAY7B-MOS0112", 1024, 1024, 1048576,
     0x31B23EE65C268AA6ull, false, false, true},
    {"MOS0134.PVRZ", "GAMEPLAY7B-MOS0134", 512, 512, 262144,
     0xAC4E6A825A6D1CC7ull, false, false, true},
    {"MOS0137.PVRZ", "GAMEPLAY7B-MOS0137", 1024, 1024, 1048576,
     0xD43699FC25027D84ull, false, false, true},
    {"MOS0145.PVRZ", "GAMEPLAY7B-MOS0145", 512, 512, 262144,
     0xFA77CDFB9E024085ull, false, false, true},
    {"MOS0146.PVRZ", "GAMEPLAY7B-MOS0146", 1024, 1024, 1048576,
     0x9E24CD40E753091Eull, false, false, true},
    {"MOS0151.PVRZ", "GAMEPLAY7B-MOS0151", 1024, 1024, 1048576,
     0xA903D4319C0AA8C0ull, false, false, true},
    {"MOS0152.PVRZ", "GAMEPLAY7B-MOS0152", 1024, 1024, 1048576,
     0x630C2D60D6DCDD0Dull, false, false, true},
    {"MOS0158.PVRZ", "GAMEPLAY7B-MOS0158", 1024, 1024, 1048576,
     0x8BF7E4ACE989A70Aull, false, false, true},
    {"MOS0159.PVRZ", "GAMEPLAY7B-MOS0159", 1024, 1024, 1048576,
     0x283292FF07972748ull, false, false, true},
    {"MOS0160.PVRZ", "GAMEPLAY7B-MOS0160", 1024, 1024, 1048576,
     0xAE9176ABC3987532ull, false, false, true},
    {"MOS0161.PVRZ", "GAMEPLAY7B-MOS0161", 1024, 1024, 1048576,
     0xC72AC149713F1CBDull, false, false, true},
    {"MOS0106.PVRZ", "GAMEPLAY7B-MOS0106", 1024, 1024, 1048576,
     0x313FEA267A66A204ull, false, false, true},
    {"MOS0118.PVRZ", "GAMEPLAY7B-MOS0118", 512, 512, 262144,
     0x481FBF8F1DF75D84ull, false, false, true},
    {"MOS0119.PVRZ", "GAMEPLAY7B-MOS0119", 512, 512, 262144,
     0x3F60E39ED66F0104ull, false, false, true},
    {"MOS0120.PVRZ", "GAMEPLAY7B-MOS0120", 512, 512, 262144,
     0xCD69AB27786C306Aull, false, false, true},
    {"MOS0128.PVRZ", "GAMEPLAY7B-MOS0128", 1024, 1024, 1048576,
     0x9BA957766A78DC66ull, false, false, true},
    {"MOS0129.PVRZ", "GAMEPLAY7B-MOS0129", 1024, 1024, 1048576,
     0xD69C2E8C2E0E839Eull, false, false, true},
    {"MOS0130.PVRZ", "GAMEPLAY7B-MOS0130", 1024, 1024, 1048576,
     0x3DC73BE0709A9381ull, false, false, true},
    {"MOS0256.PVRZ", "GAMEPLAY7B-MOS0256", 1024, 1024, 1048576,
     0xD19D7A1D23E9EF4Dull, false, false, true},
    {"MOS0105.PVRZ", "GAMEPLAY7B-MOS0105", 1024, 1024, 1048576,
     0x8E54A1ECA6D1C3CBull, false, false, true},
    {"MOS0108.PVRZ", "GAMEPLAY7B-MOS0108", 1024, 1024, 1048576,
     0x4809E6BE6B12D289ull, false, false, true},
    {"MOS0122.PVRZ", "GAMEPLAY7B-MOS0122", 1024, 1024, 1048576,
     0xEEEA82CBB035A6A1ull, false, false, true},
    {"MOS0123.PVRZ", "GAMEPLAY7B-MOS0123", 512, 512, 262144,
     0x5997CC749BF676C7ull, false, false, true},
    {"MOS0127.PVRZ", "GAMEPLAY7B-MOS0127", 1024, 1024, 1048576,
     0xF37212620431DE7Bull, false, false, true},
}};

std::mutex g_mutex;
std::deque<AtlasReplacement> g_uiPack;
int g_scale{};

void read_ui_pack(const std::filesystem::path& directory) {
  std::ifstream manifest(directory / "ui-review-atlases.txt");
  std::string line;
  while (std::getline(manifest, line)) {
    std::istringstream row(line);
    int number{}, width{}, height{};
    std::uint64_t fingerprint{};
    auto valid_size = [](int side) {
      return side >= 64 && side <= 1024 && (side & (side - 1)) == 0;
    };
    if (!(row >> number >> width >> height >> std::hex >> fingerprint) ||
        number < 7000 || number > 9999 || !valid_size(width) || !valid_size(height) ||
        fingerprint == 0 || (row >> std::ws && !row.eof())) {
      LOG_WARN("Invalid UI review atlas entry: {}", line);
      continue;
    }
    const auto name = "MOS" + std::to_string(number);
    bool duplicate = false;
    for (const auto& atlas : g_uiPack) {
      duplicate |= atlas.sourceName == name + ".PVRZ" ||
          (width == atlas.sourceWidth && height == atlas.sourceHeight &&
           fingerprint == atlas.sourceFingerprint);
    }
    if (!duplicate) {
      g_uiPack.emplace_back(name + ".PVRZ", "UIREVIEW-" + name, width, height,
                            width * height, fingerprint, false, false, true);
    }
  }
}

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
             bool includeMainMenu, bool includeSelector, bool includeGameplayMenus) noexcept {
  try {
    if (scale != 2 && scale != 4) {
      LOG_WARN("Menu texture replacement disabled: unsupported scale x{}", scale);
      return false;
    }
    bool preparedAny = false;
    std::lock_guard lock(g_mutex);
    g_scale = 0;
    g_uiPack.clear();
    if (includeGameplayMenus && scale == 4) read_ui_pack(assetsDirectory);
    auto prepareAtlas = [&](AtlasReplacement& atlas, bool requested) {
      atlas.ready.store(false, std::memory_order_release);
      atlas.logged.store(false, std::memory_order_release);
      atlas.replacement.clear();
      if (!requested) return;

      const auto assetPath = assetsDirectory /
                             (std::string(atlas.assetStem) + "-x" + std::to_string(scale) + ".dxt5");
      const int replacementByteCount = atlas.sourceByteCount * scale * scale;
      std::ifstream file(assetPath, std::ios::binary | std::ios::ate);
      if (!file) {
        LOG_WARN("{} x{} replacement skipped: missing {}", atlas.sourceName, scale, assetPath.string());
        return;
      }
      const auto byteCount = file.tellg();
      if (byteCount != replacementByteCount) {
        LOG_WARN("{} x{} replacement skipped: {} has {} bytes (expected {})", atlas.sourceName,
                 scale, assetPath.string(), static_cast<long long>(byteCount), replacementByteCount);
        return;
      }
      file.seekg(0);
      std::vector<std::byte> loaded(replacementByteCount);
      if (!file.read(reinterpret_cast<char*>(loaded.data()), loaded.size())) {
        LOG_WARN("{} x{} replacement skipped: could not read {}", atlas.sourceName, scale,
                 assetPath.string());
        return;
      }
      atlas.replacement = std::move(loaded);
      atlas.ready.store(true, std::memory_order_release);
      preparedAny = true;
      LOG_INFO("Prepared reversible {} x{} atlas: {}", atlas.sourceName, scale, assetPath.string());
    };
    for (auto& atlas : g_atlases) {
      const bool requested = (atlas.gameplayMenus && !atlas.mainMenu) ? includeGameplayMenus :
          ((atlas.mainMenu ? includeMainMenu : includeBigLogo) ||
           (includeSelector && atlas.selector) || (includeGameplayMenus && atlas.gameplayMenus));
      prepareAtlas(atlas, requested);
    }
    for (auto& atlas : g_uiPack) prepareAtlas(atlas, true);
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
  g_uiPack.clear();
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
  auto match = [&](AtlasReplacement& atlas) {
    if (!atlas.ready.load(std::memory_order_acquire) || width != atlas.sourceWidth ||
        height != atlas.sourceHeight || byteCount != atlas.sourceByteCount ||
        fingerprint != atlas.sourceFingerprint) {
      return false;
    }
    const int replacementByteCount = atlas.sourceByteCount * g_scale * g_scale;
    if (static_cast<int>(atlas.replacement.size()) != replacementByteCount) return false;
    out = {atlas.sourceWidth * g_scale, atlas.sourceHeight * g_scale, replacementByteCount,
           atlas.replacement.data()};
    if (!atlas.logged.exchange(true, std::memory_order_acq_rel)) {
      LOG_INFO("Replacing {} with x{} atlas; UI geometry stays unchanged", atlas.sourceName, g_scale);
    }
    return true;
  };
  for (auto& atlas : g_atlases) if (match(atlas)) return true;
  for (auto& atlas : g_uiPack) if (match(atlas)) return true;
  return false;
}
}  // namespace iee::biglogo
