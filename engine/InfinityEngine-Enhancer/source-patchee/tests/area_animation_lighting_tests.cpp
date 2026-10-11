#include "iee/core/area_animation_lighting.h"
#include <cstdlib>
#include <iostream>
#include <vector>

using namespace iee::core::area_lighting;
void require(bool value) { if (!value) std::abort(); }
int main() {
  Palette source{}, day{}, night{}, rgbaNight{};
  for (unsigned i = 0; i < 256; ++i) {
    source[i] = i * 0x010101u;
    day[i] = 0xff000000u | source[i];
    const unsigned r = i * 110 / 255, g = i * 100 / 255, b = i * 145 / 255;
    night[i] = 0xff000000u | r << 16 | g << 8 | b;
    rgbaNight[i] = 0xff000000u | b << 16 | g << 8 | r;
  }
  const auto daylight = derive(source, day, true);
  const auto dark = derive(source, night, true);
  const auto darkRgba = derive(source, rgbaNight, false);
  require(daylight.valid && dark.valid && darkRgba.valid);
  require(dark.fingerprint == darkRgba.fingerprint && daylight.fingerprint != dark.fingerprint);
  for (unsigned i = 0; i < 256; ++i) for (unsigned c = 0; c < 3; ++c) require(daylight.rgb[c][i] == i);
  std::vector<std::byte> pixels{std::byte{180},std::byte{160},std::byte{140},std::byte{176},
                              std::byte{0},std::byte{0},std::byte{0},std::byte{0}};
  iee::core::area_lighting::apply(pixels, dark);
  require(pixels[0] == std::byte{77} && pixels[1] == std::byte{62} && pixels[2] == std::byte{79});
  require(pixels[3] == std::byte{176} && pixels[7] == std::byte{0});
  // Native per-index recolouring cannot be represented by a channel transfer.
  source[200] = source[100];
  require(!derive(source, night, true).valid);
  require(!derive(source, night, true, 4).valid);
  require(enabled({'1','4','0','0','T','0','0','5'}));
  require(!enabled({'A','M','1','4','0','0','A','\0'}));
  require(!enabled({'1','4','0','0','T','0','0','6'}));
  const std::array<char,8> tree5{'1','4','0','0','T','0','0','5'};
  const std::array<char,8> tree4{'1','4','0','0','T','0','0','4'};
  require(tree_night_scene("AR1400","AR1400N"));
  require(tree_night_scene("AR1404","AR1404"));
  require(!tree_night_scene("AR1400","AR1400"));
  require(!tree_night_scene("AR1400",""));
  require(!tree_night_scene("AR1401","AR1400N"));
  auto day5 = daylight;
  require(!customize_tree_night(day5,tree5,false));
  require(day5.rgb == daylight.rgb && day5.fingerprint == daylight.fingerprint);
  auto night4 = dark;
  require(!customize_tree_night(night4,tree4,true));
  require(night4.rgb == dark.rgb && night4.fingerprint == dark.fingerprint);
  auto night5 = dark;
  require(customize_tree_night(night5,tree5,true));
  require(night5.fingerprint != dark.fingerprint);
  require(night5.rgb[0][128] == 33 && night5.rgb[1][128] == 28 && night5.rgb[2][128] == 61);
  for (const char digit : {'2','3','5'}) {
    const std::array<char,8> ref{'1','4','0','0','T','0','0',digit};
    auto dayTree = daylight;
    require(!customize_tree_night(dayTree,ref,false));
    require(dayTree.rgb == daylight.rgb && dayTree.fingerprint == daylight.fingerprint);
    auto nightTree = dark;
    require(customize_tree_night(nightTree,ref,true));
    require(nightTree.rgb == night5.rgb && nightTree.fingerprint == night5.fingerprint);
  }
  auto night1 = dark;
  require(!customize_tree_night(night1,{'1','4','0','0','T','0','0','1'},true));
  require(night1.rgb == dark.rgb && night1.fingerprint == dark.fingerprint);
  auto correctedPixels = pixels;
  iee::core::area_lighting::apply(correctedPixels,night5);
  require(correctedPixels[3] == pixels[3] && correctedPixels[7] == pixels[7]);
  std::cout << "Native day/night palette transfer, encoding, alpha, cache identity and scope passed\n";
  std::cout << "T002/T003/T005 same night correction: day exact, T001/T004 exact, T005 preserved, live WED gate and alpha passed\n";
}
