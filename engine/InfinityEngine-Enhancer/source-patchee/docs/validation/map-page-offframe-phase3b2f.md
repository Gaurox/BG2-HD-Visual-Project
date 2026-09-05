# Phase 3e-B2f — single-slot just-in-time scheduling

## Status

Phase 3e-B2f is a default-off performance prototype for `MAP-PERF-001`. It keeps the four-claim
decoded-PVR handoff and the in-flight reader retirement protocol proved by B2d/B2e, but changes when
the shadow worker is allowed to prepare pages. The four-zone ingame campaign passed for rendering,
robustness and exact restoration on 2026-08-30. Its one warm-cache pass is promising but is not a
statistical or release qualification.

No map content, `areas.csv`, release manifest or `validated-installed` element was changed.

## Problem addressed

B2e queued every missing page as soon as an area plan was created. On a large map this made the
shadow worker read and decompress dozens of pages while the render thread was already performing
the native prewarm. The worker therefore duplicated CPU and I/O work for pages that it could never
consume after the four-claim limit. On AR0700N, the first wide-view frame also contained two new
compressed calls and reached 22.46 ms.

B2f removes that eager competition:

- the completed handoff holds one page instead of four and is bounded to 20 MiB instead of 72 MiB;
- in consume mode, exactly one current missing page is submitted and awaited off-frame;
- after its native `Demand`, the scheduler advances to the next page and repeats until four claims;
- every later page follows the unchanged native path without shadow preparation;
- the worker runs below normal priority;
- the first wide-view expansion stops acceptance and cancels remaining pending/completed work;
- probe-only mode keeps the original eager behavior;
- cancellation, just-in-time submission, idle-wait and wide-view-stop counters were added.

The native resource manager, 128-entry PVR cache, texture upload, publication and release remain
authoritative. Every mismatch still falls back to the original zlib/native path.

## Exact candidate and transaction

Candidate used ingame:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2f-20260830\candidate-b2f-single-slot-idle-v1
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.dll` | 1,547,264 | `526A29106F98A6ADCD7BE9CD69FE3130AF033123C89D2F06CEDB93DC28203642` |
| `InfinityEngine-Enhancer.ini` | 2,308 | `C8100D8D098D5418B55DA5A66552F21AB6ACB6DF289427A5FFA12D0606DFC400` |

The INI enabled performance logs, map prewarm and the separate off-frame consumer, with one page
per frame, an 8 ms scheduler budget, a 96-page plan ceiling and a 30-frame delay.

The transaction and evidence are stored under:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2f-20260830\ingame-four-zone-single-slot
```

The install receipt is
`20260830T185842574243Z-dc9c5d09\renderer-install-receipt.json`, 1,982 bytes, SHA-256
`7EAAFE39F857B30671331A3A2A8BC8E7DCF0544208392754820A341C44FC6390`.
The four bounded logs and the complete session log are retained beside it.

## Ingame protocol and result

The game was launched through InfinityLoader. The four named saves were loaded in this order:
AR0900, AR0602, AR0516, then AR0700N. Each complete map rendered correctly, the first wide-view
expansion was exercised, all transitions completed and the game exited normally.

All sixteen prepared claims were consumed successfully:

| Area | Prepared pages consumed | Missing native demands | Prepared share |
|---|---|---:|---:|
| AR0900 | `A090000`, `A090001`, `A090008`, `A090009` | 19 | 4/19 |
| AR0602 | `A060200` to `A060203` | 34 | 4/34 |
| AR0516 | `A051600` to `A051603` | 32 | 4/32 |
| AR0700N | `A0700N00` to `A0700N03` | 81 | 4/81 |
| **Total** | **16 pages** | **166** | **9.64%** |

There was no prepared-claim fallback, mismatch, unexpected return, memory rejection, internal
error, crash or deadlock. The bounded B2f part of the session contains four prewarm completions,
four wide-view telemetry events, four stop events and zero `error`/`critical` line.

## Performance comparison

The comparable metric is `Map page prewarm complete: totalDemandMs`: the total time spent in the
native materializations required to make the planned map pages resident.

| Area | Historical native A (ms) | B2e eager four-claim (ms) | B2f single-slot JIT (ms) | B2f vs A | B2f vs B2e |
|---|---:|---:|---:|---:|---:|
| AR0900 | 732.45 | 655.40 | 586.94 | -19.9% | -10.4% |
| AR0602 | 196.82 | 177.95 | 179.72 | -8.7% | +1.0% |
| AR0516 | 187.26 | 173.39 | 178.38 | -4.7% | +2.9% |
| AR0700N | 828.58 | 891.74 | 837.69 | +1.1% | -6.1% |
| **Total** | **1,945.11** | **1,898.48** | **1,782.73** | **-8.3%** | **-6.1%** |

Negative percentages are improvements. The AR0700N A value is the value captured during the
earlier interactive baseline campaign; its dedicated A archive retained with the B2e evidence does
not contain the corresponding explicit prewarm-complete line. It must therefore be remeasured in
the repeated qualification campaign before any statistical conclusion.

B2f improves the aggregate despite preparing only 9.64% of the missing pages. That is consistent
with the intended mechanism: it avoids the eager shadow worker competing with native prewarm for
the remaining 150 pages. The large-map results improve strongly against B2e; the +1.0% and +2.9%
movements on the two small maps are too small to separate from run variance with one pass.

The worst native materialization in B2f was 42.35 ms on AR0900, 6.62 ms on AR0602, 10.21 ms on
AR0516 and 14.17 ms on AR0700N. This prototype therefore does not make every atomic native call fit
under the historical 8 ms target.

## First wide-view behavior

| Area | Trigger frame (ms) | New table/source pages | Compressed calls |
|---|---:|---:|---:|
| AR0900 | 5.97 | 0 | 0 |
| AR0602 | 6.02 | 0 | 0 |
| AR0516 | 6.03 | 4 | 0 |
| AR0700N | 5.92 | 7 | 0 |

For comparison, the eager B2e AR0700N trigger frame was 22.46 ms with two compressed calls / 8 MiB.
B2f reduced it to 5.92 ms with no compressed call. All four B2f stop events report zero cancellation
because the four just-in-time claims had already completed before the first wide-view trigger; the
stop path is nevertheless armed and unit-covered for an earlier trigger.

## Telemetry correction after the run

The tested candidate emitted an `all-planned-pages-observed` shadow summary after the first claim:
in JIT mode, one submitted and one observed page temporarily looked like a finished plan. The later
area-reset summaries correctly contain all four submissions and consumptions, so this is a reporting
error only and does not affect scheduling, rendering or the performance values above.

The source was corrected after the ingame run so that the summary waits until either the four-claim
gate is exhausted or the complete plan is finished. The resulting Release DLL is 1,547,264 bytes,
SHA-256 `F4DAA8D945C436250588E118EEAA0B38DCFCA59D103E3C63949E5179769DA23C`.
This post-run DLL passed the serial native test suites and exact executable validation, but was not
retested ingame because the change only delays an INFO summary. Any next ingame campaign must use
and hash a new transaction made from this final source.

## Offline validation

- common native CTest: Debug 2/2 and Release 2/2;
- Windows x64 Release `release_bundle` and DLL CTest: 2/2;
- common Python suite: 207/207 in 95.687 seconds before the reporting-only correction;
- exact BG2EE 2.7.3 `BaldurReal.exe` build validation: passed before and after that correction;
- `git diff --check`: passed before documentation consolidation.

One DLL CTest invocation was accidentally launched concurrently with an identical suite and both
used fixed sprite-test temporary directories. That concurrent invocation failed on a catalog-entry
fixture. A serial rerun passed 2/2; this was test-environment interference, not a runtime failure.

## Restoration and verdict

The candidate was removed through its transaction, then the receipt verification passed. At the
end of the controlled session, no game or InfinityLoader process remained. The installed renderer
was restored exactly to:

- DLL SHA-256 `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E`;
- INI SHA-256 `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

B2f is the first four-zone result that makes the off-frame consumer look beneficial overall while
also removing the visible B2e wide-view contention on AR0700N. It is retained as the new experimental
direction, not as a release result.

The next gate is a repeated, counterbalanced A/B campaign on all four saves using the telemetry-fixed
source, followed separately by an OS-cold-cache campaign. If AR0700N's +1.1% persists outside normal
variance, page choice or idle-window timing must be refined before increasing the four-claim limit.
Only after repeatability, no-regression and cold-cache gates pass can a release integration decision
be requested.
