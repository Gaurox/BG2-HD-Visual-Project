# Area-animation clock probe

This is gate 0 of the interpolated area-animation prototype. It measures the
real `CGameStatic::RenderBam` cadence before any runtime animation clock is
introduced. The probe does not alter frame selection, texture binding, BAM
geometry, or gameplay timing.

## Enable the probe

Install a DLL built from this source tree together with a valid
`iee-assets/AreaAnimations-X4.registry` pack, then set:

```ini
[Core]
PerformanceLogs = true

[Shaders]
EnableAreaAnimationX4 = true
```

Leave Baldur.lua's `Maximum Frame Rate` at its normal gameplay value. With
EEex, that setting controls logic/AI speed rather than the uncapped render
presentations being measured here.

The regular five-second `Frame presentation perf` line gives the actual swap
cadence. Each visible registry-backed resource and sequence also emits an
`Area animation clock probe` line every five seconds.

## Capture sequence

Use `PORTL1A` in AR0602 (world position approximately `3904,2375`) as the
first clock subject. Keep it visible and run:

1. 30 seconds of ordinary unpaused rendering.
2. A pause held for at least 10 seconds, followed by 10 seconds resumed.
3. Move the animation off-screen, wait 10 seconds, then bring it back.
4. Save/load once and change area once before returning.

Keep `InfinityEngine-Enhancer.log`; do not infer cadence from visual inspection
alone.

## Log interpretation

- `calls`: raw `RenderBam` calls for the resref/sequence in the window.
- `occurrenceEpochs`: distinct presentation epochs counted per animation
  occurrence. This is the relevant proof that EEex light render ticks revisit
  the animation.
- `sameEpochCalls`: repeated calls that occurred inside one presentation; they
  do not provide an extra opportunity to display an interpolated frame.
- `slots`: completed native sequence-slot visits.
- `epochsPerSlot`: average and range of distinct presentation epochs available
  during a native slot.
- `slotMs`: native slot duration, excluding visits over 250 ms. A normal 15 Hz
  clock should cluster near 66.7 ms.
- `stalledSlots` / `longGaps`: pause, culling or hitch candidates kept out of
  the nominal slot-duration average.
- `transitions`: sequential advances, skipped slots, wraps, backward moves and
  sequence resets.
- `worldActive`: observations of `CTimerWorld::m_active`. This is a candidate
  pause signal only; the capture must validate its meaning before it can drive
  the future scheduler.
- `nonMonotonic`, `droppedOccurrences`, `droppedGroups`, `invalidSamples`:
  diagnostic failures. All must remain zero for a valid gate.

## Gate for the 30 fps proof-of-clock

Proceed to timed frame selection only when all of the following hold:

- presentation cadence is stable at 60 fps or above;
- `PORTL1A` averages at least four distinct epochs per native slot;
- normal `slotMs` clusters around 66.7 ms;
- skips and backward transitions are absent or explained by the test action;
- pause/off-screen gaps are quarantined rather than contaminating nominal slot
  timing;
- the candidate `worldActive` signal has an unambiguous pause/resume relation;
- probe capacity/input diagnostics remain zero.

If `PORTL1A` exposes only about two distinct epochs per 66.7 ms slot,
`RenderBam` is effectively tied to the 30 Hz logic clock and the proposed
runtime interpolation route is a no-go.

## First live result

The 2026-08-23 BG2EE capture passed the gate:

- stable presentation cadence averaged 163.93 fps, with 154.9 fps as the
  lowest complete post-warm-up window and a 6.31 ms average p95;
- normal `PORTL1A` windows averaged 10.95 presentation epochs per 66.71 ms
  native slot;
- skips, backward transitions, non-monotonic QPC samples and capacity failures
  remained zero;
- a fully paused window recorded 825 RenderBam epochs, zero slot transitions
  and `worldActive={on:0, off:825}`;
- rendering continued when the subject was moved off-screen, and the area
  generation boundary was observed on load.

Result: **GO for the PORTL1A 30 fps proof-of-clock**. `worldActive` is validated
as the pause gate for this prototype; the scheduler must shift its QPC origin
by the paused duration so the held slot resumes without phase drift.
