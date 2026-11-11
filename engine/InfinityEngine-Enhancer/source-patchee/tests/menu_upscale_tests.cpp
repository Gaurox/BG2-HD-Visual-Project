#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

#include "iee/biglogo_ui_upscale.h"
#include "iee/core/config.h"
#include "iee/game/opengl_types.h"

// Fixtures are the native DXT5 payloads extracted read-only from the user's BIFs.
// argv[1] is a disposable directory containing them; no live GL/game is needed.
int main(int argc, char** argv) {
  if (argc != 2) return 2;
  const std::filesystem::path root = argv[1];
  struct Page { const char* name; const char* stem; int side; bool selector; bool gameplay{false}; };
  const std::array<Page, 78> pages{{
      {"MOS0181", "MAINMENU-MOS0181", 1024, true, true},
      {"MOS0182", "SELECTOR-MOS0182", 512, true},
      {"MOS0183", "SELECTOR-MOS0183", 512, true},
      {"MOS0184", "SELECTOR-MOS0184", 512, true},
      {"MOS0185", "SELECTOR-MOS0185", 512, true},
      {"MOS0258", "MAINMENU-MOS0258", 1024, true},
      {"MOS0259", "SELECTOR-MOS0259", 512, true},
      {"MOS0017", "BIGLOGO-MOS0017", 1024, false},
      {"MOS0140", "HUD-MOS0140", 1024, false, true},
      {"MOS0257", "MAINMENU-MOS0257", 1024, false, true},
      {"MOS0155", "GAMEPLAY7B-MOS0155", 512, false, true},
      {"MOS0156", "GAMEPLAY7B-MOS0156", 1024, false, true},
      {"MOS0180", "GAMEPLAY7B-MOS0180", 512, false, true},
      {"MOS0253", "GAMEPLAY7B-MOS0253", 512, false, true},
      {"MOS0254", "GAMEPLAY7B-MOS0254", 1024, false, true},
      {"MOS0263", "GAMEPLAY7B-MOS0263", 1024, false, true},
      {"MOS0264", "GAMEPLAY7B-MOS0264", 512, false, true},
      {"MOS0255", "GAMEPLAY7B-MOS0255", 512, false, true},
      {"MOS0115", "GAMEPLAY7B-MOS0115", 1024, false, true},
      {"MOS0116", "GAMEPLAY7B-MOS0116", 1024, false, true},
      {"MOS0125", "GAMEPLAY7B-MOS0125", 1024, false, true},
      {"MOS0126", "GAMEPLAY7B-MOS0126", 512, false, true},
      {"MOS0138", "GAMEPLAY7B-MOS0138", 1024, false, true},
      {"MOS0139", "GAMEPLAY7B-MOS0139", 512, false, true},
      {"MOS0148", "GAMEPLAY7B-MOS0148", 1024, false, true},
      {"MOS0149", "GAMEPLAY7B-MOS0149", 1024, false, true},
      {"MOS0150", "GAMEPLAY7B-MOS0150", 512, false, true},
      {"MOS0154", "GAMEPLAY7B-MOS0154", 1024, false, true},
      {"MOS0168", "GAMEPLAY7B-MOS0168", 512, false, true},
      {"MOS0169", "GAMEPLAY7B-MOS0169", 1024, false, true},
      {"MOS0107", "GAMEPLAY7B-MOS0107", 1024, false, true},
      {"MOS0113", "GAMEPLAY7B-MOS0113", 512, false, true},
      {"MOS0114", "GAMEPLAY7B-MOS0114", 1024, false, true},
      {"MOS0124", "GAMEPLAY7B-MOS0124", 512, false, true},
      {"MOS0135", "GAMEPLAY7B-MOS0135", 1024, false, true},
      {"MOS0136", "GAMEPLAY7B-MOS0136", 512, false, true},
      {"MOS0147", "GAMEPLAY7B-MOS0147", 1024, false, true},
      {"MOS0157", "GAMEPLAY7B-MOS0157", 1024, false, true},
      {"MOS0164", "GAMEPLAY7B-MOS0164", 1024, false, true},
      {"MOS0165", "GAMEPLAY7B-MOS0165", 1024, false, true},
      {"MOS0166", "GAMEPLAY7B-MOS0166", 1024, false, true},
      {"MOS0167", "GAMEPLAY7B-MOS0167", 512, false, true},
      {"MOS0103", "GAMEPLAY7B-MOS0103", 512, false, true},
      {"MOS0104", "GAMEPLAY7B-MOS0104", 512, false, true},
      {"MOS0131", "GAMEPLAY7B-MOS0131", 1024, false, true},
      {"MOS0132", "GAMEPLAY7B-MOS0132", 512, false, true},
      {"MOS0133", "GAMEPLAY7B-MOS0133", 1024, false, true},
      {"MOS0162", "GAMEPLAY7B-MOS0162", 1024, false, true},
      {"MOS0163", "GAMEPLAY7B-MOS0163", 1024, false, true},
      {"MOS0176", "GAMEPLAY7B-MOS0176", 1024, false, true},
      {"MOS0179", "GAMEPLAY7B-MOS0179", 1024, false, true},
      {"MOS0252", "GAMEPLAY7B-MOS0252", 512, false, true},
      {"MOS0110", "GAMEPLAY7B-MOS0110", 512, false, true},
      {"MOS0111", "GAMEPLAY7B-MOS0111", 1024, false, true},
      {"MOS0112", "GAMEPLAY7B-MOS0112", 1024, false, true},
      {"MOS0134", "GAMEPLAY7B-MOS0134", 512, false, true},
      {"MOS0137", "GAMEPLAY7B-MOS0137", 1024, false, true},
      {"MOS0145", "GAMEPLAY7B-MOS0145", 512, false, true},
      {"MOS0146", "GAMEPLAY7B-MOS0146", 1024, false, true},
      {"MOS0151", "GAMEPLAY7B-MOS0151", 1024, false, true},
      {"MOS0152", "GAMEPLAY7B-MOS0152", 1024, false, true},
      {"MOS0158", "GAMEPLAY7B-MOS0158", 1024, false, true},
      {"MOS0159", "GAMEPLAY7B-MOS0159", 1024, false, true},
      {"MOS0160", "GAMEPLAY7B-MOS0160", 1024, false, true},
      {"MOS0161", "GAMEPLAY7B-MOS0161", 1024, false, true},
      {"MOS0106", "GAMEPLAY7B-MOS0106", 1024, false, true},
      {"MOS0118", "GAMEPLAY7B-MOS0118", 512, false, true},
      {"MOS0119", "GAMEPLAY7B-MOS0119", 512, false, true},
      {"MOS0120", "GAMEPLAY7B-MOS0120", 512, false, true},
      {"MOS0128", "GAMEPLAY7B-MOS0128", 1024, false, true},
      {"MOS0129", "GAMEPLAY7B-MOS0129", 1024, false, true},
      {"MOS0130", "GAMEPLAY7B-MOS0130", 1024, false, true},
      {"MOS0256", "GAMEPLAY7B-MOS0256", 1024, false, true},
      {"MOS0105", "GAMEPLAY7B-MOS0105", 1024, false, true},
      {"MOS0108", "GAMEPLAY7B-MOS0108", 1024, false, true},
      {"MOS0122", "GAMEPLAY7B-MOS0122", 1024, false, true},
      {"MOS0123", "GAMEPLAY7B-MOS0123", 512, false, true},
      {"MOS0127", "GAMEPLAY7B-MOS0127", 1024, false, true},
  }};
  const auto assets = root / "test-assets";
  std::filesystem::create_directories(assets);
  for (const auto& page : pages) {
    std::ofstream file(assets / (std::string(page.stem) + "-x4.dxt5"), std::ios::binary);
    file.seekp(page.side * page.side * 16 - 1);
    file.put('\0');
    if (!file) return 1;
  }
  auto check = [&](const Page& page, bool expected) {
    std::ifstream file(root / (std::string(page.name) + ".dxt5"), std::ios::binary);
    const std::vector<char> data((std::istreambuf_iterator<char>(file)), {});
    if (data.size() != static_cast<std::size_t>(page.side * page.side)) return false;
    iee::biglogo::ReplacementUpload replacement{};
    auto upload = [&](unsigned format, int side, int bytes, const void* input) {
      return iee::biglogo::try_replacement(iee::game::gl::TEXTURE_2D, 0, format,
                                         side, page.side, bytes, input, replacement);
    };
    const auto format = iee::game::gl::COMPRESSED_RGBA_S3TC_DXT5_EXT;
    const bool matched = upload(format, page.side, static_cast<int>(data.size()), data.data());
    if (matched != expected) return false;
    if (matched && (replacement.width != page.side * 4 || replacement.height != page.side * 4 ||
                    replacement.byteCount != page.side * page.side * 16)) return false;
    auto changed = data;
    changed[0] ^= 1;
    return !upload(format, page.side, static_cast<int>(changed.size()), changed.data()) &&
           !upload(iee::game::gl::COMPRESSED_RGBA_S3TC_DXT1_EXT, page.side,
                   static_cast<int>(data.size()), data.data()) &&
           !upload(format, page.side - 1, static_cast<int>(data.size()), data.data());
  };
  if (!iee::biglogo::prepare(assets, 4, false, false, true)) return 1;
  for (const auto& page : pages) if (!check(page, page.selector)) {
    std::cerr << "Selector isolation or exact-byte matching failed: " << page.name << '\n';
    return 1;
  }
  iee::biglogo::release();
  for (const auto& page : pages) if (!check(page, false)) return 1;
  if (iee::biglogo::prepare(assets, 4, false, false, false)) return 1;
  if (!iee::biglogo::prepare(assets, 4, false, false, false, true)) return 1;
  for (const auto& page : pages) if (!check(page, page.gameplay)) {
    std::cerr << "Gameplay isolation or exact matching failed: " << page.name << '\n';
    return 1;
  }
  iee::biglogo::release();
  iee::core::EngineConfig cfg;
  if (cfg.enableSelectorX4 || cfg.enableGameplayMenusX4) return 1;
  const auto ini = root / "selector-test.ini";
  { std::ofstream file(ini); file << "[Shaders]\nEnableSelectorX4=true\n"; }
  if (!iee::core::ConfigManager::load(ini, cfg) || !cfg.enableSelectorX4 ||
      cfg.enableMainMenuX4Test || cfg.enableBigLogoX4Test || cfg.enableMenuX2Test) return 1;
  { std::ofstream file(ini); file << "[Shaders]\nEnableGameplayMenusX4=true\n"; }
  iee::core::EngineConfig gameplayConfig;
  if (!iee::core::ConfigManager::load(ini, gameplayConfig) || !gameplayConfig.enableGameplayMenusX4 ||
      gameplayConfig.enableSelectorX4 || gameplayConfig.enableMainMenuX4Test || gameplayConfig.enableMenuX2Test) return 1;
  std::size_t gameplayCount = 0;
  for (const auto& page : pages) if (page.gameplay) ++gameplayCount;
  std::cout << gameplayCount << " gameplay payloads accepted in isolation; dedicated config checked; ";
  std::cout << "7 native selector payloads accepted; BIGLOGO/HUD/other-menu excluded; "
               "wrong hash/format/dimensions rejected; release/off and isolated INI checked\n";
  return 0;
}
