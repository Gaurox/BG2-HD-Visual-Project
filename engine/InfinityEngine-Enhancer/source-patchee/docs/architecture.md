# Architecture

## Scope

The supported runtime is intentionally narrow: one EEex-loaded Windows DLL and reviewed manifests
for BGEE `2.6.6.x`/`2.7.3.x` and BG2EE `2.7.3.x`. Features remain explicitly gated per build. The
runtime covers tile upscaling plus registry-backed area animations, the BG2EE AR1300 transition and
the opt-in BG2EE creature-sprite x2 QA path. Additional game/build support is a manifest and
validation expansion, not an inferred fallback.

The runtime is save-neutral. `tools/M_IEEE.lua` sets
`EEex_Debug_DisableExtraCreatureMarshalling = true` before binding the DLL, so
the graphics-only profile does not emit EEex `X-BIV1.0` pseudo-effects that a
vanilla executable cannot unmarshal. This is a forward-compatibility contract;
it does not rewrite existing save resources.

## Runtime Modules

`src/iee/game/build_manifest.*`

- Declares the executable version, build-specific patterns, reference RVAs, runtime offsets, and verified render callsites.
- Current reviewed identities are BGEE `2.6.6.x`/`2.7.3.x` and BG2EE `2.7.3.x`; individual
  features still require their own manifest fields and gates.

`src/iee/game/game_addrs.*`

- Resolves `CInfGame::LoadArea` and `CVidTile::RenderTexture`.
- Scans executable PE sections and accepts only one match for each required signature.
- Reference RVAs are diagnostic evidence only; missing or ambiguous signatures abort initialization.

`src/iee/game/renderer.*`

- Resolves draw API entry points from `CVidTile::RenderTexture`.
- Handles opcode-aware rel32 decoding, including the `DrawPopState` tail jump.
- Applies GL texture parameter upgrades and keeps a bounded 512-entry,
  deletion-aware configuration cache. Successful hits avoid driver queries;
  periodic sentinel validation covers deletion paths that bypass the observed
  GL entry point. Failed configurations are latched only until an area,
  deletion, or context reset.

`src/iee/game/tis_runtime.*`

- Provides explicit runtime views for `CRes`, `CResTile`, `CResTileSet`, `CResPVR`, and the authored TIS header.
- Reads build-specific offsets from the manifest instead of hardcoding them throughout hooks.

`src/iee/game/tis_palette.*`

- Decodes classic palette-tile transparency and derives authored liquid tint.
- Converts each palette entry to linear light once, weights area tint by opaque
  pixel count, and avoids treating a sparsely painted tile like a full tile;
  the water shader grades in the same space and re-encodes the affected result.
- A matching RGBA-page average supports GPU-decompressed PVRZ liquid overlays;
  transparent atlas padding is excluded from their authored tint.
- Exact-resref authored presets provide an opt-in fallback when a driver does
  not permit the PVRZ texture readback or its page is not ready during the WED
  refresh. The preset is captured from WED metadata before runtime texture
  sampling, so load order cannot silently restore the neutral tint. Presets
  cover the processed `WTLAK*`, `WTPOOL`, `WTSWAM`, `WTSEW`, and `WTOIL`
  families, each from its own measured asset. Unknown overlays remain neutral
  rather than inheriting an unrelated liquid palette.

`src/iee/game/runtime_types_x64.h`

- Holds the curated x64 type surface used for rapid reverse-engineering around tiles, sprites, and renderer-adjacent engine state.
- Small PODs are modeled directly; larger engine objects keep exact offsets for selected named fields and leave the rest opaque.

`src/iee/game/file_formats.h`

- Holds exact on-disk / loaded resource layout definitions mirrored from EEex docs for `TIS`, `WED`, `BAM`, and `PVRZ`-adjacent structures.

`src/iee/game/eeex_doc_layouts_x64.h`

- Holds exact EEex field maps for large runtime classes where mirroring every nested type as hand-written C++ would be brittle and low signal.
- This keeps the full documented field surface for `CInfGame`, `CInfinity`, `CGameSprite`, and shader-adjacent types in-repo.

`src/iee/game/tile_upscale.*`

- Encapsulates scale detection.
- TIS header metadata is authoritative.
- Headerless PVR tables are classified from same-page coordinate deltas, not raw atlas origins.
- UV / texture-id heuristics remain fallback only.

`src/iee/hooks.*`

- Owns the runtime hook lifecycle as a thin detour -> dispatch layer.
- `LoadArea` resets area-scoped feature state; `RenderTexture` dispatches into
  the tile render feature and delegates unsupported resources to the engine.
- A frame-boundary retry makes shader-probe recovery independent of tile
  dispatch and transient RenderTexture decode failures.

`src/iee/area_state.*`

- Active-area resolution (manifest-driven CInfGame offsets), view-transform reads, and
  the post-LoadArea WED cache refresh plus render-thread area-texture queue.
- Refresh publication is generation-checked; an older load/render callback
  cannot overwrite the newest immutable WED snapshot.
- GL objects are recreated when the current WGL context changes.
- Classic liquid tint is still resolved on the loading side. PVRZ tint
  candidates are published with the immutable snapshot and read back once from
  their already-decompressed GL pages by the render thread, avoiding PVRZ
  decompression and OpenGL work in `LoadArea`.
- A PVRZ tint candidate is accepted only when its mutable runtime wrapper still
  names the exact WED tileset and tile index requested **and** its PVR pointer
  names the page derived from that tileset and its TIS table entry. During area
  transitions, a recycled base-area wrapper or PVR pointer must fail closed and
  leave the exact-resref liquid fallback active.

`src/iee/features/tile_render.*`

- The tile upscale render path and its per-area, fixed-capacity tileset cache,
  moved out of hooks/AppContext. Scale and linear-mode decisions are kept per
  observed tileset; the whole cache is discarded on area change.
- Publishes the final primary/secondary WED tile index used as the AR1300
  `BRIDGE01` transition signal; input clicks are deliberately not observed.

`src/iee/bridge_transition.*`

- Validated BG2EE 2.7.3 local event-video overlay for AR1300/BRIDGE01.
- Media Foundation worker decodes a bounded BGRA frame queue; MCI plays the
  independently seekable forward/reverse WAV streams.
- Logical-frame mapping supports opening, closing, and live direction reversal
  without a native-door-state flash; lossless endpoint frames cover decoder seek.
- The original `CGameArea::Render` is followed by `DrawFlush_GL`, then the raw GL
  overlay is drawn into the active map render target. `DrawEndScaled` and the
  owning screen compose every HUD/menu afterward. This ordering is required:
  SwapBuffers would put the asset above UI, while omitting the flush lets deferred
  native map commands cover it.
- Current media is a classic 2048-square Lanczos resize. SeedVR2 7B x4 media QA
  remains pending; see [event-video-overlay-assets.md](event-video-overlay-assets.md).

`src/iee/creature_sprite_x2.*`

- Loads the external V2 palette-index registry for one target animation ID and keeps native BAM
  geometry, centers, cycles and palette semantics at x1.
- Materializes x2 frames with nearest sampling. Character mode composes body, weapon,
  offhand/shield and helmet after runtime palette realization; any missing or inconsistent layer
  falls back to the complete native character.
- Supports only the hook owners selected in `hooks.cpp`: `MonsterIcewind 0xE000` and
  `Character 0x5000/0x6000`. Do not infer additional animation-class support from the presence of
  BAM resources.
- Asset coverage, registry estimates and automated blockers are external inputs generated by
  [the sprite inventory](../../../../sprite/index/README.md). Keep scanner classification and this
  runtime contract synchronized when adding a class, suffix family or registry capability.

`src/iee/diagnostics.*`

- TIS header / pointer dump logging used by detection fallbacks.

`src/iee/game/shader_override.*`

- Host-safe shader name extraction and interface-contract checks for the
  delivered `fpSEAM.glsl` game override. Unit-tested in WSL/macOS.
- Shader source delivery is performed by the game's `override` directory; this
  module does not maintain a runtime replacement registry.

`src/iee/shader_probe.*`

- Thin Windows GL detours (source/compile/link/use/delete + ARB), diagnostics,
  program classification, uniform-feed dispatch, and hook lifecycle.
- Compile/link failures are logged, but the production path does not resubmit a
  fallback shader source. The engine-owned override loading path remains the
  source of the compiled shader.
- Probe entry points and program classifications are discarded and reinstalled
  when the current WGL context changes.
- Water assets are decoded during DLL initialization, while render-thread GL
  upload stays lazy; probe hooks are queued and enabled in one MinHook batch.

`src/iee/shader_uniform_bridge.*`

- Owns atomic uniform inputs, location resolution, and render-thread
  uniform/texture binding. A state revision avoids repeating unchanged GL
  queries, sampler writes, and enhancer texture binds.

`src/iee/shader_diagnostics.*`

- Owns optional caller-symbol resolution and engine-shader dump file I/O.

`src/iee/frame_hook.*`

- Frame boundary via `SDL_GL_SwapWindow`, with `gdi32!SwapBuffers` as the
  validated statically-linked-SDL fallback; drives the probe's per-frame tick.

`src/iee/game/area_texture.*`

- Host-safe packing of WED per-cell liquid modes into the R8 unit-2 mask texture.
- The compact cell mask is an outer bound; base-tile alpha supplies the authored contour.

`src/iee/game/dds_texture.*`

- Host-safe, bounded parsing for single 2D BC1/BC3/BC5/BC7 DDS assets.
- Separates format validation and mip layout from the Windows/OpenGL upload path,
  so malformed-input behavior is testable without a game or GL context.

`src/iee/water_textures.*`

- Selects optional DDS assets ahead of the bundled IRGB fallback and owns their
  current-context GL objects.
- Uploads authored compressed mip chains directly and reports driver/format
  failures once per context instead of retrying on every draw.
- Discards stale GL errors immediately before its own upload sequence so an
  unrelated engine error cannot permanently block water textures for a context.

## Build Layout

The CMake graph is split on purpose:

- `iee_common` is host-safe and can be compiled in WSL for tests.
- `InfinityEngine-Enhancer` is Windows-only and links MinHook, `psapi`, and `opengl32`.
- `release_bundle` packages the DLL, EEex loader script, sample INI, shader
  assets, game override, water textures, and optional bridge-transition media
  into one directory.
- `cmake --install` mirrors the same game-root directory layout.
- `renovate.json` teaches Renovate's regex manager to update the human-readable
  spdlog/MinHook tags and their immutable `FetchContent` commit pins together.

This keeps reverse-engineering and parsing code testable without requiring a Windows toolchain for every edit.

## Operational Boundaries

- Use WSL for code analysis, docs, and host tests.
- Use Windows or CI for final DLL validation.
- Unknown or incompatible builds should fail during manifest/address/callsite resolution instead of reaching gameplay with bad hooks.
- A loader that calls `FreeLibrary` must invoke exported `ShutdownBindings`
  first; MinHook, logging, and GL teardown are deliberately never run from
  `DllMain` under the Windows loader lock.
- [threading-model.md](threading-model.md) defines callback ownership and exception boundaries.

## Archival Code

[docs/archive/prototypes](archive/prototypes/README.md) preserves unsupported experiments. Nothing
in that directory is part of the build or a source of truth for runtime behavior.
