#include <iostream>
#include <memory>
#include "iee/core/effect_presentation_trace.h"

using iee::core::EffectPresentationTrace;

int main() {
  auto trace = std::make_unique<EffectPresentationTrace>();
  // 60Hz swaps of a 30fps sequence: two presentations per content phase.
  for (int frame = 0; frame < 8; ++frame) {
    trace->owner(1, 1, 0, frame / 4, frame);
    trace->draw(1, 1, 0, frame, frame / 4, frame / 2, frame / 2,
                120, 100, 7, true, false, 1000 + frame * 100);
    trace->swap(frame, 1050 + frame * 100, 6000, 1, true);
  }
  auto& c = trace->capture(0);
  if (c.rowCount != 8 || c.rows[1].phase != 0 || c.rows[2].phase != 1 ||
      c.rows[7].backing != 3 || !c.rows[7].swapOk || !c.rows[7].hd) return 1;
  // Multiple draws in a swap must not masquerade as multiple presentations.
  trace->owner(1, 1, 0, 2, 8);
  trace->draw(1, 1, 0, 8, 2, 4, 4, 120, 100, 8, true, true, 1801);
  trace->draw(1, 1, 0, 8, 2, 5, 5, 120, 100, 9, true, true, 1802);
  trace->swap(8, 1850, 6000, 1, false);
  if (c.rows[8].draws != 2 || !c.rows[8].conflictingDraws ||
      c.rows[8].swapOk || !c.rows[8].masked) return 1;
  // A seen owner that never submits a draw is explicitly distinct from a hold.
  trace->owner(1, 1, 0, 3, 9);
  trace->swap(9, 1950, 6000, 1, true);
  if (!c.rows[9].ownerSeen || c.rows[9].draws || c.rows[9].phase != -1) return 1;
  trace->owner(1, 1, 0, 3, 10);
  trace->draw(1, 1, 0, 10, 4, -1, -1, 120, 100, 2, false, false, 1990);
  trace->swap(10, 2050, 6000, 1, true);
  if (c.rows[10].hd || c.rows[10].nativeSlot != 4) return 1;
  // Pausing does not end the capture; no stale draw leaks into an absent frame.
  trace->swap(11, 10000, 6000, 0, true);
  if (c.complete || c.rows[11].draws || c.rows[11].ownerSeen) return 1;
  trace->swap(12, 11000, 6000, 1, true);
  if (!c.complete || !trace->ready_to_publish(11000, 6000)) return 1;
  // Same engine address reused by a subsequent cast gets a distinct capture.
  trace->owner(1, 1, 0, 0, 13);
  trace->swap(13, 12000, 6000, 1, true);
  if (trace->count() != 2 || trace->capture(1).id != 2) return 1;
  // A new area generation cannot inherit a previous instance's pending row.
  trace->owner(1, 2, 0, 0, 14);
  trace->swap(14, 12100, 6000, 1, true);
  if (trace->count() != 3 || trace->capture(2).rows[0].draws) return 1;
  auto bounded = std::make_unique<EffectPresentationTrace>();
  for (std::size_t i = 0; i <= iee::core::EffectPresentationCapture::kRows; ++i) {
    bounded->owner(9, 1, 0, 1, i);
    bounded->swap(i, 1000 + i, 6000, 0, true);
  }
  if (!bounded->capture(0).overflow ||
      bounded->capture(0).rowCount != iee::core::EffectPresentationCapture::kRows) return 1;
  std::cout << "post-swap cadence capture, pause, fallback, multi-draw and bounds passed\n";
  return 0;
}
