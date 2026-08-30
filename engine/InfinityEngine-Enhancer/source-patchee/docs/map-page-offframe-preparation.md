# Map Page Off-Frame Preparation Contract

## Status and purpose

This note defines and records the reversible Phase 3e-A prototype for `MAP-PERF-001`. The CPU-only
shadow preparer was qualified offline and ingame on AR0900 on 2026-08-30. This is not evidence that
asynchronous native PVR materialization is implemented: the prepared bytes are deliberately never
consumed by the engine or OpenGL. The result establishes feasibility and readiness timing only.
The subsequent Phase 3e-B0 static audit identified and manifested a safe decoded-PVR handoff.
Phase 3e-B1 implemented that consumer as a separate default-off, one-page-per-generation canary
and passed its offline and AR0900 ingame gates on 2026-08-30. One prepared page was consumed, the
native cache/upload/free continuation remained active, rendering stayed correct, and the exact
pre-test renderer was restored. Phase 3e-B2 replaced that canary gate with a fixed maximum of four
ready claims per area generation. Its offline gates and transaction preflight passed, but its
AR0900 ingame gate crashed after three successful consumptions and before the fourth outcome. B1
therefore remains the last ingame-proven boundary. Phase 3e-B2a then repeated AR0900 with exactly
three possible claims and native `CRes::Demand` entry/return telemetry. `A090010` used native
fallback with no active claim; native resource loading returned null/false before the same crash.
Phase 3e-B2b then passed the same AR0900 gate with one and exactly two claims. After two prepared
substitutions, `A090009`, `A090010` and every later page loaded natively; the complete map remained
correct and stable and the game exited cleanly. The failure transition is therefore after the third
successful substitution, before the following native load completes. The attempted `nCount`
observation produced impossible values and is not a valid ownership signal.
Phase 3e-B2c replaced those guessed fields with exact cache/release/file-open boundaries. Its
two-claim control passed again. The three-claim replay proves that `A090010` fails first in the
native file-open helper with `ERROR_SHARING_VIOLATION` while its shadow identity is known but not
ready and the worker owns the in-flight job. Cache occupancy is only 36/128 and no cache release
occurs. The source is returned to two claims pending an explicit in-flight retirement handshake.

The measured bottleneck is the indivisible native `CResPVR::Demand` call. Repacking AR0900 with
zlib level 0 reduced its worst call from 43.97 ms to 12.77 ms but increased the PVRZ payload by
264.30 MiB. Block-exact 2112-square repaging reduced it to 15.22 ms without increasing the payload,
but the 8 ms gate still failed. A smaller uniform page cannot fit the 5,752 tiles in the existing
96-page prewarm limit.

The next experiment must therefore determine whether the read and zlib preparation can be
completed before a page is needed by the render thread, without moving OpenGL or mutable engine
state to a worker.

## Proven current boundary

The current `map_page_prewarm` scheduler runs in `on_post_swap`, with the engine WGL context still
owned by the render thread. It validates the area, tileset, tile wrapper and PVR resref immediately
before and after calling the exact manifested `CResPVR::Demand` entry. The native call remains
synchronous and authoritative.

Static and ingame evidence for BG2EE 2.7.3 shows that `CResPVR::Demand` performs several coupled
operations before returning:

- resource lookup/read and PVRZ preparation;
- native resource and residency bookkeeping;
- OpenGL texture creation/binding and compressed upload;
- publication of the resulting texture name in `CResPVR::texture`.

Consequently, calling native `Demand` from a worker is forbidden. Directly writing `CRes::pData`,
`bLoaded`, `CResPVR::texture` or another native field is also forbidden until allocation,
ownership, release and cache interactions have been proven for the manifested build.

## Phase 3e-A: shadow preparation probe

The first implementation milestone performs no native-object or OpenGL mutation. It may only
prepare immutable CPU data and telemetry:

1. The render thread publishes a bounded job containing copied identities, never borrowed mutable
   engine pointers: area generation, area resref, tileset resref, page resref and expected page
   number.
2. One owned worker resolves only an explicitly supported on-disk PVRZ source. The first candidate
   is restricted to the local experimental map payload; an unresolved KEY/BIFF or other resource
   source is a clean miss and retains native fallback.
3. The worker reads the complete file with size limits, validates the PVRZ envelope, inflates zlib,
   validates the decoded-size field and PVR v3 header, then publishes an immutable result tagged
   with the same generation and identities.
4. The render thread observes and retires results but does not upload them or alter the native
   `CResPVR`. Ordinary synchronous `Demand` remains unchanged. The probe records prepare latency,
   queue latency, bytes, cache hits/misses, invalidations and whether the result was ready before
   the corresponding native materialization.
5. Area reset, WGL-context change, feature disable and shutdown increment or invalidate the
   generation. Stale queued and completed work is discarded without dereferencing engine memory.

This shadow milestone cannot improve frame time by itself. Its purpose is to prove that the
expensive CPU portion can be ready early enough, under a bounded memory and scheduling policy,
before any native publication path is attempted.

### Implemented boundary

`EnableMapPageOffframeProbe=false` is the fail-closed default. The probe starts only when both this
switch and `PerformanceLogs=true` are present. The existing render-thread plan submits copied
identities for pages that were not already resident when the plan was built, after its configured
delay; one process-lifetime Win32 worker reads only the matching `override/<page-resref>.PVRZ`
regular file. A missing KEY/BIFF-only resource is a clean miss. Excluding initially resident pages
prevents unobservable results from filling the completed handoff ahead of pages that can still
cross native `Demand`.

The production parser accepts the closed PVRZ representation used by the current maps: a declared
decoded size followed by exactly one zlib stream and one PVR v3 DXT1 or DXT5 surface, with no mip
chain. It validates the exact DXT block payload before publishing the immutable CPU buffer. zlib
v1.3.2 is built statically from the full commit
`da607da739fa6047df13e66a2af6b8bec7c2a498`.

Immediately before an otherwise-required native `CResPVR::Demand`, the render thread records
whether the matching shadow result is ready and retires it. It never passes the buffer to native
code, never changes the native object and never issues a GL call. Pending or active work that loses
the race is cancelled by identity; an area generation reset discards stale jobs and results. A
one-shot summary is emitted when all submitted pages have crossed this observation boundary, so a
normal process exit is not required to retain the evidence.

## Ownership and bounds

The implementation must preserve these limits from its first commit:

- one joinable worker owned by the feature; no detached thread;
- fixed-capacity pending and completed queues, with duplicate page identities coalesced;
- explicit maximum compressed bytes, decoded bytes, page count and aggregate resident bytes;
- immutable byte buffers transferred by ownership, never raw pointers into engine objects;
- no OpenGL, WGL, native `Demand`, engine allocator, resource-manager call or logger callback that
  can cross into engine code from the worker;
- no exception crossing a hook or thread entry boundary;
- prompt bounded shutdown, with queued work cancelled and the worker joined before hook teardown.

Initial limits must be derived from the AR0900 4096-page evidence and kept configurable only if the
configuration parser already provides the same fail-closed range validation used by the prewarm
scheduler. Raising the native 128-entry pool or the current 96-page planning ceiling is outside
Phase 3e-A.

The implemented fixed limits are 32 MiB compressed and 20 MiB decoded per page, 96 pending jobs,
four completed pages and 72 MiB of aggregate completed buffers. The worker blocks when the
completed handoff is full. Stop and generation changes wake it and release all buffers.

## Required evidence before a consuming prototype

Phase 3e-B0 required all of the following to be documented for the exact manifested BG2EE 2.7.3
build before any consumer could be implemented:

- the precise native boundary between zlib/PVR preparation and GL upload;
- the allocator and owner of every buffer retained or released across that boundary;
- texture-name creation, filtering, format and size field semantics;
- success, failure, release and eviction behavior in the 128-entry native PVR table;
- a render-thread-only publication method that either preserves native bookkeeping or abandons the
  prepared result and calls native synchronous `Demand` unchanged.

If no safe supported boundary exists, the consuming prototype is rejected. A second decompression
followed by ordinary `Demand` is valid only as shadow telemetry and must not be presented as an
optimization.

Phase 3e-B0 completed this audit on 2026-08-30. The exact evidence and the Phase 3e-B1 contract are
recorded in
[`validation/map-page-offframe-phase3b0.md`](validation/map-page-offframe-phase3b0.md). The selected
boundary is the native zlib-wrapper call at `CResPVR::Demand+0x15F`: a render-thread detour may copy
an exactly matching prepared decoded PVR into the destination already allocated by the engine,
then resume native code at `Demand+0x164`. Native resource loading, the 128-entry cache, texture
creation/binding, PVR field publication, compressed upload, eviction and release all remain
unchanged. Every mismatch must call original zlib.

## Validation gates

Phase 3e-A must pass unit tests for envelope/header validation, size and memory limits, queue
coalescing, generation cancellation, stale-result discard, clean shutdown and failure isolation.
Debug and Release native suites must remain green. Installation must use a new
`renderer-install-receipt.json` transaction.

Offline qualification on 2026-08-30 passed all of those unit cases, 2/2 CTest targets in Debug and
Release, and 207/207 common Python tests. The build manifest validation passed against the installed
BG2EE 2.7.3 `BaldurReal.exe` (`b51093a4...a14d57`). The Release preflight ran the production parser
against all 26 AR0900 day pages: 26/26 ready, 151.73 MiB read and 416.00 MiB decoded, with 971.40 ms
total preparation, 39.38 ms median, 18.05 ms minimum and 41.94 ms maximum per page. This sequential
tool result validates parsing and sizing only; it does not predict readiness relative to native
demands in the game.

The first ingame gate was AR0900 only:

- no error, crash, deadlock, GL call or native object write from the worker;
- zero stale result accepted after area/context changes;
- bounded queues and memory at all times;
- enough pages prepared before native materialization to justify Phase 3e-B;
- unchanged visual output and unchanged synchronous fallback behavior.

The corrected Release candidate passed this gate on 2026-08-30. The plan contained 26 pages, seven
of which were already resident and therefore not submitted. Of the 19 submitted pages, 16 were
ready before native materialization and three lost the race (`84.21%` versus `15.79%`). There were
zero missing files, I/O failures, invalid results, rejections, stale accepted results and unplanned
demands. The worker prepared 95.63 MiB compressed / 256.00 MiB decoded in 616.52 ms total, with a
42.81 ms maximum preparation. Peak handoff occupancy was four results / 64.00 MiB, below the
72 MiB bound. Visual output was unchanged and the bounded session contained no error, crash or
deadlock; its sole warning was the already documented EEex `RenderTexture` prologue recovery.

The test transaction was restored after exit. Phase 3e-A is therefore ingame-qualified, but it did
not optimize any frame: every CPU buffer was retired without native or GL consumption, and native
`Demand` remained authoritative. Phase 3e-B0 proved the exact render-thread boundary listed above,
and the separate default-off Phase 3e-B1 consumer validated it for one page. Phase 3e-B2 preserved
the same intended ownership boundary and raised only the generation gate to four ready claims. Its
Debug/Release tests, DLL build, exact executable validator and transaction preflight passed, but
its ingame run crashed in native `CResPVR::Demand+0x13D` on `A090010`, after three logged
consumptions and before the fourth outcome; see
[`validation/map-page-offframe-phase3b2.md`](validation/map-page-offframe-phase3b2.md). The next gate
was Phase 3e-B2a, which fixed the claim limit at three and manifested/instrumented the exact nested
`CRes::Demand` call. It reproduced the same crash after logging `A090010` as
`native-fallback-claim-limit`, `activeClaim=false`, then a native null/false return; see
[`validation/map-page-offframe-phase3b2a.md`](validation/map-page-offframe-phase3b2a.md). This
eliminates a fourth prepared copy as the immediate mechanism, but not a cumulative earlier side
effect. Phase 3e-B2b therefore ran a one-claim telemetry control followed by a two-claim
discriminator with native resource count/ownership observations. Both runs passed; see
[`validation/map-page-offframe-phase3b2b.md`](validation/map-page-offframe-phase3b2b.md). They prove
one and two claims stable and isolate the failure onset to the first native load after the third
successful claim. The modelled `nCount` values are not reliable and must not be interpreted or
written. The next B2c gate compares two versus three claims using only manifested function
boundaries, pointer identities, PVR-cache movements, paired release calls and bounded memory
telemetry. Phase 3e-B2c completed that comparison; see
[`validation/map-page-offframe-phase3b2c.md`](validation/map-page-offframe-phase3b2c.md). It
manifests the 128-entry cache and native release/file-open boundaries and isolates the first
failure to `A090010` file open returning error 32 while the same not-ready identity is still owned
by the shadow worker. B2d must add an explicit in-flight identity and wait for file-handle
relinquishment before entering native fallback, then pass the three-claim AR0900 gate. The
four-zone performance protocol is blocked. A shadow result, a prepared or installed candidate, or
a successful local test does not create a `validated-installed` release element.
