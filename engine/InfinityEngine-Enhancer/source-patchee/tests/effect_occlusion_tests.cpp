#include <array>
#include <cstdint>
#include <iostream>
#include <vector>

#include "iee/core/native_occlusion_probe.h"

int main() {
  using namespace iee::core;
  int failures = 0;
  const auto check = [&](bool condition, const char* reason) {
    if (!condition) { ++failures; std::cerr << reason << '\n'; }
  };
  const auto effect = NativeOcclusionReplacement::EffectAnimation;
  check(native_effect_occlusion_fallback_required(effect, 1, false, false, false),
        "Unavailable transfer must retain the clipped native effect");
  check(native_effect_occlusion_fallback_required(effect, 1, true, true, false),
        "Failed GPU composition must retain the clipped native effect");
  check(!native_effect_occlusion_fallback_required(effect, 1, true, true, true),
        "A composed WED mask keeps the HD effect");
  check(!native_effect_occlusion_fallback_required(effect, 1, true, false, false),
        "A polygon that changes no pixels must keep the original HD colour");
  check(!native_effect_occlusion_fallback_required(effect, 0, false, false, false),
        "Effects without native occlusion must remain visible in HD");
  check(!native_effect_occlusion_fallback_required(
            NativeOcclusionReplacement::CreatureSprite, 1, false, true, false),
        "The effect fallback must not change creature routing");

  for (auto owner : {NativeOcclusionOwner::VvcEffect, NativeOcclusionOwner::ProjectileBam}) {
    NativeOcclusionCorrelation scope{owner, 0x1000, 0x4144414D};
    scope.record_clipping({.infinity = 0x2000, .x = 20, .y = 30, .result = 1});
    const auto sample = scope.correlate_draw({.logicalWidth = 2, .logicalHeight = 2,
                                            .replacement = effect});
    check(sample && sample->owner == owner && sample->successfulClippingCallCount == 1 &&
              sample->draw.replacement == effect,
          "Both effect owners must correlate their own native WED pass");
    NativeOcclusionCorrelation nested{owner, 0x3000, 0x4244414D};
    const auto child = nested.correlate_draw({.replacement = effect});
    check(child && !child->clipping_seen(), "A nested effect must not inherit parent clipping");
  }

  // Repeated/interpolated draws and changed geometry get independent captures.
  for (int width : {2, 3}) {
    for (int phase = 0; phase < 2; ++phase) {
      std::array<std::uint32_t, 3> pixels{{0x00102030u, 0xC0603018u, 0xFF804020u}};
      NativeFxSurfaceView surface{reinterpret_cast<const std::byte*>(pixels.data()),
                                 12, width, 1};
      NativeOcclusionMaskCapture capture;
      check(capture.begin_call(surface), "Effect capture must accept variable logical geometry");
      pixels[0] = 0;              // Additive light can exist with zero source alpha.
      pixels[1] = 0x60603018u;    // Native partial visibility; keep source alpha separate.
      capture.finish_call(surface, 1);
      std::vector<std::uint8_t> transfer;
      bool changed = false;
      check(capture.build_transfer(width, 1, transfer, changed) && changed &&
                transfer.size() == static_cast<std::size_t>(width) * 4 &&
                transfer[0] == 0 && transfer[4] == 128,
            "WED transfer must hide zero-alpha light and retain fractional visibility");
      if (width == 3 && transfer.size() == 12)
        check(transfer[8] == 255, "Unoccluded light must keep full visibility");
    }
  }
  if (failures) return 1;
  std::cout << "Effect occlusion contracts passed\n";
  return 0;
}
