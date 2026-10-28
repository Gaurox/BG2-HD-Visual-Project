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
  // BG2EE CProjectileBAM::Render calls 2A4090 first: a clipped glow is
  // unlocked/drawn, then FXLock starts another surface for FIREBAT. An owner-
  // wide capture sees two geometries and must reject them; per-FX captures
  // must still transfer the flight's own WED cut, without inheriting the glow.
  {
    std::vector<std::uint32_t> glow(24 * 16, 0x80603018u);
    std::vector<std::uint32_t> flight(69 * 78, 0xC0603018u);
    NativeFxSurfaceView glowView{reinterpret_cast<const std::byte*>(glow.data()),
                                24 * 4, 24, 16};
    NativeFxSurfaceView flightView{reinterpret_cast<const std::byte*>(flight.data()),
                                  69 * 4, 69, 78};
    NativeOcclusionMaskCapture ownerCapture, surfaceCapture;
    NativeOcclusionCorrelation ownerScope{NativeOcclusionOwner::ProjectileBam, 0x1000, 1};
    NativeOcclusionCorrelation flightScope{NativeOcclusionOwner::ProjectileBam, 0x2000, 1};
    check(ownerCapture.begin_call(glowView), "Owner begins with the separate glow pass");
    glow[0] = 0;
    ownerCapture.finish_call(glowView, 1);
    ownerScope.record_clipping({.result = 1});
    check(!ownerCapture.begin_call(flightView) && !ownerCapture.valid(),
          "Combining glow and flight captures must fail closed");
    // FXLock resets the single-surface capture, not the enclosing owner.
    check(surfaceCapture.begin_call(flightView), "Flight begins an independent FX capture");
    flight[1] = 0;
    flight[2] = 0x60603018u;
    surfaceCapture.finish_call(flightView, 1);
    flightScope.record_clipping({.result = 1});
    // Two clipping calls within the SAME FX surface must still accumulate.
    check(surfaceCapture.begin_call(flightView), "A second polygon keeps the flight capture");
    flight[3] = 0;
    surfaceCapture.finish_call(flightView, 1);
    flightScope.record_clipping({.result = 1});
    std::vector<std::uint8_t> transfer;
    bool changed = false;
    const bool ready = surfaceCapture.build_transfer(69, 78, transfer, changed);
    check(ready && changed && transfer.size() == 69 * 78 * 4 &&
              transfer[0] == 255 && transfer[4] == 0 &&
              transfer[8] == 128 && transfer[12] == 0,
          "Flight retains both native polygon cuts, partial visibility and no glow cut");
    const auto sample = flightScope.correlate_draw({.logicalWidth=69, .logicalHeight=78,
                                                  .replacement=effect});
    check(sample && sample->successfulClippingCallCount == 2 &&
              !native_effect_occlusion_fallback_required(effect,
                  sample->successfulClippingCallCount, ready, changed, true),
          "Independent flight mask is eligible for HD composition");
    check(!surfaceCapture.build_transfer(24, 16, transfer, changed),
          "A flight mask must never be reused on the glow geometry");
    surfaceCapture = {};
    check(!surfaceCapture.build_transfer(69, 78, transfer, changed),
          "A new FX lock must not reuse the previous flight mask");
  }
  if (failures) return 1;
  std::cout << "Effect occlusion contracts passed\n";
  return 0;
}
