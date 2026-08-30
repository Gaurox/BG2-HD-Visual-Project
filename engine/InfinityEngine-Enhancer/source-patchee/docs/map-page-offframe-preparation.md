# Map Page Off-Frame Preparation Contract

## Status and purpose

This note defines the next reversible prototype for `MAP-PERF-001`. It is a design and validation
contract, not evidence that asynchronous PVR materialization is already implemented.

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

## Required evidence before a consuming prototype

Phase 3e-B may consume prepared bytes on the render thread only after all of the following are
documented for the exact manifested BG2EE 2.7.3 build:

- the precise native boundary between zlib/PVR preparation and GL upload;
- the allocator and owner of every buffer retained or released across that boundary;
- texture-name creation, filtering, format and size field semantics;
- success, failure, release and eviction behavior in the 128-entry native PVR table;
- a render-thread-only publication method that either preserves native bookkeeping or abandons the
  prepared result and calls native synchronous `Demand` unchanged.

If no safe supported boundary exists, the consuming prototype is rejected. A second decompression
followed by ordinary `Demand` is valid only as shadow telemetry and must not be presented as an
optimization.

## Validation gates

Phase 3e-A must pass unit tests for envelope/header validation, size and memory limits, queue
coalescing, generation cancellation, stale-result discard, clean shutdown and failure isolation.
Debug and Release native suites must remain green. Installation must use a new
`renderer-install-receipt.json` transaction.

The first ingame gate is AR0900 only:

- no error, crash, deadlock, GL call or native object write from the worker;
- zero stale result accepted after area/context changes;
- bounded queues and memory at all times;
- enough pages prepared before native materialization to justify Phase 3e-B;
- unchanged visual output and unchanged synchronous fallback behavior.

Only after that gate passes may the four-zone protocol be replayed. A shadow result, an installed
candidate or a successful local test does not create a `validated-installed` release element.
