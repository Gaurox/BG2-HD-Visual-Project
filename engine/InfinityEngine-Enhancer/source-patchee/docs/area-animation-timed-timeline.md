# Area-animation TimedTimeline runtime

Registry v2 adds an opt-in visual timeline while preserving the BAM-owned
native cycle. Registry v1 remains supported and always uses native playback.

The `PORTL1A` 15-to-30 fps proof passed live pause/resume and visual QA on
2026-08-23. The production asset workflow, approval gate, pack format and
reversible installer are documented in
[`../../../../pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](../../../../pipeline/ANIMATION_UPSCALE_30FPS_V2.md).

Each v2 resource declares one of two modes:

- `Native`: zero timing fields and an empty visual timeline per cycle.
- `TimedTimeline`: rational native/target rates and one visual phase table per
  native cycle. Native and visual durations must be exactly equal.

The render hook first resolves the exact native frame. That handle remains the
fail-closed result. A timed frame is selected only when the presentation
boundary, integer QPC clock, `CTimerWorld::m_active` pause signal and complete
timeline metadata are all available.

The render-thread-owned scheduler is keyed by `CGameStatic*` plus resref. It:

- returns one stable phase for every presentation epoch;
- re-anchors on every native slot or sequence transition;
- clamps elapsed time to the observed native slot;
- freezes the current phase while the world is inactive;
- shifts the slot origin on resume to remove paused wall time;
- clears pointer history on every `LoadArea` generation.

For the first proof, `PORTL1A` retains its native cycle `[0..5]` at 15 fps and
uses the 30 fps visual table `[0,6,1,7,2,8,3,9,4,10,5,11]`. The six even
phases reuse exact existing runtime anchors. Only the six odd frames are new.

The registry v2 resource payload is:

```text
resref[8]
frameCount, cycleCount
playbackMode
nativeFpsNumerator, nativeFpsDenominator
targetFpsNumerator, targetFpsDenominator
frame logical dimensions[]
for each cycle:
  nativeFrameCount, nativeFrameIndices[]
  timelineFrameCount, timelineFrameIndices[]
```

`Native` uses playback mode 0, zero rate fields and empty timelines.
`TimedTimeline` uses playback mode 1 and positive rational rates. Parsing fails
closed unless each visual cycle has exactly the same rational duration as its
native cycle.

The deterministic test suite covers exact 2:1 selection, same-presentation
deduplication, pause/resume, area reset, missing pause-signal fallback, a
rational 15-to-20 fps schedule, v2 parsing and v1 backward compatibility.

The accepted Topaz output has a small visible loop-seam irregularity. A cyclic
multi-context interpolation attempt was rejected during visual QA, so the
production workflow deliberately uses one appended first frame and does not
encode that rejected strategy.
