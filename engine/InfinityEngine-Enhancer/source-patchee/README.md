# InfinityEngine-Enhancer

`InfinityEngine-Enhancer` is an EEex-loaded Windows DLL that extends Infinity Engine rendering
without changing ARE/WED coordinates. The validated targets are BGEE `2.6.6.x` and `2.7.3.x` plus
BG2EE `2.7.3.x` for the features covered by the current build manifests and validation evidence
([BG2EE evidence](docs/validation/bg2ee-2.7.3-evidence.md)). A new hook, registry schema or binary
still requires its own gates. Other executables are rejected by product/version identity.

## What It Does

The first supported feature is higher-resolution TIS/PVRZ tile rendering, with an optional WED-masked water shader. BG2EE 2.7.3 also has a validated event-driven local video overlay for AR1300/BRIDGE01: the final WED tile selection drives bidirectional playback and live reversal, while composition in the active map render pass keeps all HUD and full-screen menus above it. The current media is a classic 2048-square resize; SeedVR2 7B x4 media QA remains pending. Scale detection is header-first:

- `TIS header + 0x14` is the authored tile dimension
- explicit `64`, `128`, `256`, and `512` dimensions map to `1x`, `2x`, `4x`, and `8x`

Some standard tilesets legitimately have no live header pointer. In those cases the runtime classifies scale from the PVR entry table before considering the old UV / texture-id heuristic fallback.

Runtime tileset decisions and configured GL textures are cached only for the
current area, with fixed capacities, so visiting more maps does not accumulate
cache state. Set `PerformanceLogs = true` in the `[Core]` section to emit
five-second CPU timing windows (including per-frame p95), shader-feed work,
safe-read cache, GL texture-configuration counters, registry-backed area-animation timing, and
per-area map telemetry. The latter records `LoadArea` duration, distinct PVR table pages and source
texture names observed by the tile hook, plus global GL image/subimage/compressed-upload and delete
counters. Compressed GL calls are correlation data rather than exact map-PVRZ attribution because
the same resource path also serves BAM V2 and MOS V2 assets. Same-area `LoadArea` calls measured
below one millisecond are folded into the active generation and reported as ignored no-ops; timing
failures and actual area changes fail open. Negative PVR table-page samples and non-negative page
numbers above the bounded observation capacity are reported separately.
The same opt-in mode detects an expansion of both world-view dimensions by at least 1.25x against
the most recent qualifying observation in a fixed sixteen-presentation-frame history. This covers
both abrupt and stepped in-game area-map dezooms without retaining an unbounded baseline. It
buffers the trigger frame and the next seven presentation frames before emitting one INFO record
containing per-frame presentation time, `RenderTexture` CPU time, tile draws, newly observed table
pages/source texture names and compressed-upload/delete deltas. The pre-expansion history is
discarded when capture begins, and the detector remains disarmed until both world-view dimensions
contract below the same threshold relative to the pre-expansion view. A stepped dezoom therefore
cannot retrigger after the eight-frame output window, while closing and reopening the map can start
a new event. This diagnostic changes neither tile demand nor rendering, and the GL upload fields
remain correlation signals rather than proof that every upload is a map page.
On the positively identified unified 2.7.3 executable, the same opt-in mode also validates and
hooks `CResPVR::Demand` at its manifested RVA. It records only timings and process I/O deltas: total
demand duration, nested GL texture-name generation, nested compressed upload, and the remaining
resource/read/zlib/engine residual. The residual is deliberately not labeled as pure decompression.
The eight-frame map capture reports these phases per presentation frame and retains only the
slowest materializing PVR resref in each of sixteen bounded frame slots. The native 128-page engine
cache, demand order, formats and upload calls are unchanged. Builds without exact target evidence
simply omit this diagnostic while keeping all rendering behavior.
Per-area animation-pack telemetry additionally splits registry reads, raw-frame reads,
parse/allocation work and the resident-pack swap. It reports exact raw RGBA bytes for the incoming
and outgoing packs, their temporary coexistence peak, and texture names deferred to the next GL
world pass. These are runtime-owned payload counts, not allocator overhead, process working set or
exact GPU bytes.
Per-frame area-animation composition traces are DEBUG-only. Normal INFO logging therefore does not
flush once for every frame first encountered after each area-pack swap.
Area-animation GPU-cache telemetry is also gated by `PerformanceLogs`. Its cumulative per-area
snapshots distinguish requests, hits, misses, engine texture-name creation, successful/failed
uploads, LRU evictions and context invalidations. They report uploaded, resident and peak RGBA8
base-level bytes every five seconds and once when the pack leaves residency. An LRU eviction
reuses its engine texture name; it is therefore not reported as a GL deletion. Byte counts exclude
driver allocation overhead.
The same real frame-request stream feeds five passive hierarchical cache models when
`PerformanceLogs` is enabled. Their CPU/GPU MiB/texture-limit profiles are 64/96/128,
128/128/128, 128/128/192, 128/256/192 and 192/256/192. The first two preserve the initial controls;
the third isolates the texture-count limit, the fourth is the candidate balanced policy, and the
last isolates the CPU budget. Every model starts empty for the area, retains an independent CPU
byte-LRU, and predicts raw frame-read and base-level upload bytes. These models never read a file,
allocate a texture or change the production 64-entry cache. Their metadata is bounded to 16,384
frames, discarded on an area swap, and their simulated GPU residency alone is cleared after a
GL-context loss. Periodic and final summaries are diagnostic projections rather than hardware
timings or exact process/driver memory measurements.
Opt-in process-resource telemetry complements those modelled byte counts on Windows. Each
area-animation pack load samples the process immediately before loading, while the outgoing and
incoming packs coexist, and after the resident-pack swap. Five-second reports also publish current
Working Set, peak Working Set and private commit, plus window deltas for page faults and process
read/write operations and transfer bytes. The I/O counters cover all operations attributed to the
process; they are not file-specific and do not distinguish file-cache service from physical disk
activity. They also do not report
driver VRAM allocation; unsupported counters fail closed with explicit availability flags.
For an external cross-check without modifying the render thread,
[`tools/Capture-BG2HD-ProcessResources.ps1`](tools/Capture-BG2HD-ProcessResources.ps1) waits for a
`Baldur` or `BaldurReal` process under the selected game root and samples persistent Windows
performance counters from a separate process. Its CSV records WDDM process/adapter memory,
logical-volume reads, system cache/standby state and the sampler's own duration, then closes after
the game exits. Prefer an output path on another volume. GPU Process Memory counters are suitable
for trends and internal-telemetry cross-checks, not formal leak certification; Microsoft documents
[a legacy over-reporting limitation](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/gpu-process-memory-counters-report-wrong-value).
TimedTimeline v2 drives the pause-aware visual frame selection; registry v3 additionally routes
variants by exact ARE occurrence. The release currently accepts v2 only, so v3 promotion remains a
separate gate.

The bundled `M_IEEE.lua` also disables EEex extended creature marshalling.
This renderer is graphics-only and has no save payload; suppressing EEex's
private `X-BIV1.0` records keeps new save chains compatible with the vanilla
engine. Existing saves are not migrated.

### Creature sprite xN test runtime

BG2EE 2.7.3 exposes an opt-in registry-backed x2/x4 path for creature sprites. The current hook
owners are `MonsterIcewind 0xE000` and `Character 0x5000/0x6000`; every other animation class
fails closed to native rendering. Character composition covers body, weapon, offhand/shield and
helmet while preserving runtime palette realization and x1 geometry.

The scalable layout is a V2 routing catalog with content-addressed V5 shards. Startup authenticates
the catalog only; shard metadata loads through one bounded worker and frame payloads are cached
within bounded resident budgets. The first payload read/hash/decompression is currently synchronous
on the rendering thread. Do not claim full-bestiary robustness without the stress and telemetry
gates in the scalable architecture.

For code changes, derive coverage and blockers from the repository-wide normalized inventory,
not from resref guesses or extracted asset folders:

- [sprite agent entry point](../../../sprite/README.md)
- [inventory schema](../../../sprite/index/README.md)
- [family append runbook](../../../sprite/FAMILY_APPEND.md)
- [workspace layout](../../../sprite/FOLDER_LAYOUT.md)

`EnableCreatureSpriteX2Test` is a QA switch. A family marked `pipeline_ready` in the inventory is
not release-validated until the external job pipeline completes reversible installation and
in-game QA.

`EnableCreatureSpriteLinearFiltering` is an opt-in display-only A/B switch for xN creature
sprites: `false` is the required `NEAREST` baseline and `true` selects `LINEAR`. It never changes
sprite assets and a `LINEAR` session is not eligible for formal sprite QA. Apply the procedure in
[`sprite/README.md`](../../../sprite/README.md).

## Requirements

- Windows game runtime
- Baldur's Gate: Enhanced Edition, or Baldur's Gate II: Enhanced Edition `2.7.3.x`
- EEex (`v1.1.5`+ for BG2EE `2.7`)
- OpenGL-capable renderer

## Installation

1. Install [EEex](https://github.com/Bubb13/EEex).
2. Download the release bundle from [Releases](../../../releases).
3. Copy `InfinityEngine-Enhancer.dll` and `iee-textures/` into the game root.
4. Copy the contents of `override/` (the EEex loader script and shader) into the game's `override` directory.
5. Optionally copy [InfinityEngine-Enhancer.sample.ini](tools/InfinityEngine-Enhancer.sample.ini) to the game root as `InfinityEngine-Enhancer.ini` and customize it.

The runtime writes `InfinityEngine-Enhancer.ini` and `InfinityEngine-Enhancer.log` next to the game
executable. The synchronous log rotates at 16 MiB and retains three backups
(`InfinityEngine-Enhancer.1.log` through `.3.log`), bounding new diagnostic output to about 64 MiB.
Optional BC1, BC3, BC5, or BC7 DDS water-texture overrides can be placed in
`iee-textures/`; supported layouts and format guidance are documented in
[`assets/game-textures/README.md`](assets/game-textures/README.md).

### Experimental local candidates

Do not copy a locally built DLL or its test INI into the game by hand. Prepare a new directory
containing exactly `InfinityEngine-Enhancer.dll` and `InfinityEngine-Enhancer.ini`, then use the
fail-closed transaction described in
[`docs/renderer-candidate-transaction.md`](docs/renderer-candidate-transaction.md):

```powershell
python tools/install_renderer_candidate.py install <candidate-dir> --verify-only
python tools/install_renderer_candidate.py install <candidate-dir>
python tools/install_renderer_candidate.py verify <receipt-or-transaction-dir>
python tools/install_renderer_candidate.py restore <receipt-or-transaction-dir>
```

The game and InfinityLoader must be closed for install and restore. The receipt stages immutable
copies of both candidate files and every previous file, so recovery never depends on the original
build directory. This tool is for local experiments only; it does not stage or promote the frozen
eight-file release renderer bundle.

## Development

Use WSL for analysis and host-side tests. The actual DLL build is Windows-only.

- WSL host tests:
  `cmake -S . -B cmake-build-debug -DBUILD_TESTING=ON`
  `cmake --build cmake-build-debug --target iee_tests`
  `ctest --test-dir cmake-build-debug --output-on-failure`
- Windows DLL build:
  `cmake -S . -B build -G "Visual Studio 17 2022" -A x64 -DIEE_BUILD_WINDOWS_DLL=ON -DBUILD_TESTING=ON`
  `cmake --build build --config Release --target release_bundle`

The build-only `iee_map_page_shadow_preflight` target applies the production Phase 3e-A parser to
one PVRZ without starting or changing the game:
`build\Release\iee_map_page_shadow_preflight.exe <override-page.PVRZ>`.

For the unified 2.7.3 executable, `tools/validate_build.py` also gates the Phase 3e-B0 decoded-PVR
boundary: the unique zlib wrapper, all nine native `CResPVR::Demand` phase calls and the
post-decode field/upload/release window. The consuming prototype requires both
`PerformanceLogs=true` and the separate default-off `EnableMapPageOffframeConsume=true` option.
Phase 3e-B1 proved one prepared page ingame on AR0900. Phase 3e-B2 raised the fixed limit
to four claims per area generation after exact return-address, resource, source, size and
compressed-CRC checks; every failure calls the original zlib wrapper and consumes one of the four
bounded slots. Its offline gates and transactional candidate preflight passed on 2026-08-30, but
the AR0900 ingame gate crashed in native `CResPVR::Demand+0x13D` on `A090010` after three logged
consumptions and before the fourth outcome. Phase 3e-B2a then capped the same path at three claims
and instrumented the exact nested `CRes::Demand`. It reproduced the crash after proving that
`A090010` selected native fallback with no active prepared claim and that `CRes::Demand` itself
returned null/false. Phase 3e-B2b then passed AR0900 with the same telemetry at one and exactly two
claims. With two claims, `A090009`, `A090010` and all later pages returned successfully through the
native path; the full map stayed correct and stable before a clean exit. The observed failure
threshold therefore starts after the third successful substitution. The attempted `nCount`
observation is not usable: successful resources exposed impossible values in the one-claim run and
zero in the two-claim run, so neither it nor `bWasMalloced` may drive a fix. Phase 3e-B2c then
manifested the 128-entry cache, its native release routine and the exact file-open helper nested in
`CRes::Demand`. Its two-claim control rendered and exited cleanly. In the three-claim trace,
`A090009` still completed successfully, but the immediately following not-ready `A090010` native
fallback failed at file open with Win32 error 32 (`ERROR_SHARING_VIOLATION`) before
`CRes::Demand=false` and the crash. Cache occupancy was only 36/128 and no release occurred. The
source limit first returned to the qualified two-claim control. Phase 3e-B2d then added explicit
in-flight shadow-reader retirement and a deterministic concurrency test. Its three-claim AR0900
gate exercised the race on `A090000`: the render thread waited 42.04 ms for the worker to close,
the native file open succeeded, three prepared claims were consumed, all later native fallbacks
succeeded and the complete map stayed stable before a clean exit. Phase 3e-B2e then raised only
the bound to four claims with the handshake unchanged. Its AR0900 gate consumed `A090001`,
`A090008`, `A090009` and `A090010`; two in-flight native fallbacks waited for reader retirement,
every native demand succeeded, the full map stayed stable for more than 30 seconds and the game
exited cleanly. The four-zone performance campaign is now reopened. This remains default-off and
non-release-qualified work. See
[`docs/validation/map-page-offframe-phase3b2e.md`](docs/validation/map-page-offframe-phase3b2e.md).

`cmake --install build --config Release --prefix <directory>` produces the
same game-root layout as `release_bundle`.

C++ changes follow the repository's Google-derived [`.clang-format`](.clang-format).

GitHub Dependabot maintains workflow actions. Commit-pinned CMake
`FetchContent` dependencies are described by [`renovate.json`](renovate.json);
install the Renovate GitHub App for the repository to enable those update PRs
while keeping builds reproducibly pinned to full commit SHAs.

## Docs

- [docs/architecture.md](docs/architecture.md)
- [docs/threading-model.md](docs/threading-model.md)
- [docs/renderer-candidate-transaction.md](docs/renderer-candidate-transaction.md)
- [docs/map-page-offframe-preparation.md](docs/map-page-offframe-preparation.md)
- [docs/reverse-engineering.md](docs/reverse-engineering.md)
- [docs/area-animation-clock-probe.md](docs/area-animation-clock-probe.md)
- [docs/native-occlusion-phase0.md](docs/native-occlusion-phase0.md)
- [docs/native-occlusion-phase1.md](docs/native-occlusion-phase1.md)
- [docs/validation/native-occlusion-phase1-validation.md](docs/validation/native-occlusion-phase1-validation.md)
- [docs/event-video-overlay-assets.md](docs/event-video-overlay-assets.md) — LLM procedure for adding a local event-driven video asset
- [docs/build-manifests.md](docs/build-manifests.md)
- [docs/new-build-validation.md](docs/new-build-validation.md)
- [docs/tile-upscale.md](docs/tile-upscale.md)
- [../../../sprite/README.md](../../../sprite/README.md) — creature/Character asset inventory and x2 pipeline routing

## Notes

- Unsupported experiments live under `docs/archive/prototypes/`; they are historical context, not
  an implementation route.
- Build-specific offsets and callsites live in the manifest layer under [src/iee/game/build_manifest.cpp](src/iee/game/build_manifest.cpp).

## License

See [LICENSE](LICENSE).
