#include "iee/core/native_occlusion_feather.h"
#include "iee/core/bdforcew_visual_placement.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>

static void require(bool condition, const char* message) {
  if (!condition) throw std::runtime_error(message);
}

int main(int argc, char** argv) {
  try {
    if (argc == 5) {
      const int width = std::stoi(argv[1]), height = std::stoi(argv[2]);
      std::ifstream input(argv[3], std::ios::binary);
      require(input.good(), "fixture absent");
      std::vector<std::uint8_t> transfer((std::istreambuf_iterator<char>(input)), {});
      require(iee::core::inward_occlusion_coverage(transfer, width, height), "fixture rejected");
      std::ofstream output(argv[4], std::ios::binary);
      output.write(reinterpret_cast<const char*>(transfer.data()), transfer.size());
      require(output.good(), "fixture write failed");
      return 0;
    }
    constexpr int width = 20, height = 16;
    std::vector<std::uint8_t> transfer(width * height * 4, 0);
    for (int y = 0; y < height; ++y)
      for (int x = 0; x < width; ++x) {
        const auto i = (y * width + x) * 4;
        transfer[i] = x < 5 ? 0 : 255;
        transfer[i + 3] = 255;
      }
    const auto original = transfer;
    require(iee::core::inward_occlusion_coverage(transfer, width, height), "cut not smoothed");
    for (std::size_t i = 0; i < transfer.size(); i += 4) {
      require(transfer[i] == original[i] && transfer[i + 1] == original[i + 1] &&
              transfer[i + 2] == original[i + 2], "native RGB transfer mutated");
      if (transfer[i] == 0) require(transfer[i + 3] == 0, "occluded pixel revealed");
    }
    const auto coverage = [&](int x) { return transfer[(8 * width + x) * 4 + 3]; };
    require(coverage(5) == 0 && coverage(6) > 0 && coverage(6) < coverage(7) &&
            coverage(7) < coverage(8) && coverage(8) < coverage(9) && coverage(9) == 255,
            "restored inward 16px fade incorrect");
    auto rejected = original;
    rejected[1] = 79;
    const auto dither = rejected;
    require(!iee::core::inward_occlusion_coverage(rejected, width, height) && rejected == dither,
            "dither path changed");
    rejected = original; rejected[4] = 127;
    const auto fractional = rejected;
    require(!iee::core::inward_occlusion_coverage(rejected, width, height) && rejected == fractional,
            "fractional path changed");
    require(!iee::core::inward_occlusion_coverage(rejected, width - 1, height), "invalid size accepted");
    for (std::size_t i = 0; i < rejected.size(); i += 4) { rejected[i] = 255; rejected[i+2] = 0; }
    const auto clear = rejected;
    require(!iee::core::inward_occlusion_coverage(rejected, width, height) && rejected == clear,
            "unclipped transfer changed");
    rejected = original;
    rejected[(8 * width + 10) * 4 + 2] = 255;
    require(iee::core::inward_occlusion_coverage(rejected, width, height) &&
            rejected[(8 * width + 10) * 4 + 3] == 0, "transparent neighbour clear ignored");
    iee::core::NativeOcclusionSample sample;
    sample.owner = iee::core::NativeOcclusionOwner::AreaAnimation;
    sample.subjectId = 0x574543524F464442ull;
    sample.successfulClippingCallCount = 1;
    sample.lastClippingCall.x = 2286; sample.lastClippingCall.y = 820;
    const auto shifted = [&](std::string_view area = "OH8100", bool masked = true, int x = 100) {
      return iee::core::bdforcew_visual_draw_x(sample, area, masked, x);
    };
    require(shifted() == 106, "first occurrence not shifted");
    sample.lastClippingCall.x = 2350; sample.lastClippingCall.y = 866;
    require(shifted() == 106, "second occurrence not shifted");
    require(shifted("AR0811") == 100 && shifted("OH8100", false) == 100,
            "area or unsuccessful mask scope escaped");
    sample.lastClippingCall.y = 867;
    require(shifted() == 100, "unselected occurrence shifted");
    sample.lastClippingCall.y = 866; sample.lastClippingCall.dither = 1;
    require(shifted() == 100, "dither shifted");
    sample.lastClippingCall.dither = 0; sample.subjectId = 0;
    require(shifted() == 100, "other asset shifted");
    sample.subjectId = 0x574543524F464442ull;
    sample.owner = iee::core::NativeOcclusionOwner::Character;
    require(shifted() == 100, "creature shifted");
    sample.owner = iee::core::NativeOcclusionOwner::AreaAnimation;
    sample.draw.replacement = iee::core::NativeOcclusionReplacement::AreaPrototype;
    require(shifted() == 100, "prototype shifted");
    sample.draw.replacement = iee::core::NativeOcclusionReplacement::AreaRegistry;
    sample.successfulClippingCallCount = 0;
    require(shifted() == 100, "failed native clipping shifted");
    sample.successfulClippingCallCount = 1;
    require(shifted("OH8100", true, std::numeric_limits<int>::max()) ==
            std::numeric_limits<int>::max(), "draw coordinate overflow");
    require(shifted("OH8100", true, std::numeric_limits<int>::min()) ==
            std::numeric_limits<int>::min() + 6, "negative draw coordinate failed");
    std::cout << "inward coverage and scoped BDFORCEW placement: passed\n";
  } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
