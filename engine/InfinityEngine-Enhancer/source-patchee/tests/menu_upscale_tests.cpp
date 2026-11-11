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
  const std::array<Page, 18> pages{{
      {"MOS0181", "MAINMENU-MOS0181", 1024, true, true},
      {"MOS0182", "SELECTOR-MOS0182", 512, true},
      {"MOS0183", "SELECTOR-MOS0183", 512, true},
      {"MOS0184", "SELECTOR-MOS0184", 512, true},
      {"MOS0185", "SELECTOR-MOS0185", 512, true},
      {"MOS0258", "MAINMENU-MOS0258", 1024, true},
      {"MOS0259", "SELECTOR-MOS0259", 512, true},
      {"MOS0017", "BIGLOGO-MOS0017", 1024, false},
      {"MOS0140", "HUD-MOS0140", 1024, false},
      {"MOS0257", "MAINMENU-MOS0257", 1024, false},
      {"MOS0155", "GAMEPLAY7B-MOS0155", 512, false, true},
      {"MOS0156", "GAMEPLAY7B-MOS0156", 1024, false, true},
      {"MOS0180", "GAMEPLAY7B-MOS0180", 512, false, true},
      {"MOS0253", "GAMEPLAY7B-MOS0253", 512, false, true},
      {"MOS0254", "GAMEPLAY7B-MOS0254", 1024, false, true},
      {"MOS0263", "GAMEPLAY7B-MOS0263", 1024, false, true},
      {"MOS0264", "GAMEPLAY7B-MOS0264", 512, false, true},
      {"MOS0255", "GAMEPLAY7B-MOS0255", 512, false, true},
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
  std::cout << "9 gameplay payloads accepted in isolation; dedicated config checked; ";
  std::cout << "7 native selector payloads accepted; BIGLOGO/HUD/other-menu excluded; "
               "wrong hash/format/dimensions rejected; release/off and isolated INI checked\n";
  return 0;
}
