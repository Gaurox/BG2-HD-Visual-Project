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
The same real frame-request stream feeds four passive hierarchical cache models when
`PerformanceLogs` is enabled: CPU/GPU byte budgets of 64/96, 128/128, 128/192 and 192/256 MiB.
Every model starts empty for the area, retains an independent CPU byte-LRU, caps its GPU byte-LRU
at 128 texture names, and predicts raw frame-read and base-level upload bytes. These models never
read a file, allocate a texture or change the production 64-entry cache. Their metadata is bounded
to 16,384 frames, discarded on an area swap, and their simulated GPU residency alone is cleared
after a GL-context loss. Periodic and final summaries are diagnostic projections rather than
hardware timings or exact process/driver memory measurements.
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

## Development

Use WSL for analysis and host-side tests. The actual DLL build is Windows-only.

- WSL host tests:
  `cmake -S . -B cmake-build-debug -DBUILD_TESTING=ON`
  `cmake --build cmake-build-debug --target iee_tests`
  `ctest --test-dir cmake-build-debug --output-on-failure`
- Windows DLL build:
  `cmake -S . -B build -G "Visual Studio 17 2022" -A x64 -DIEE_BUILD_WINDOWS_DLL=ON -DBUILD_TESTING=ON`
  `cmake --build build --config Release --target release_bundle`

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
