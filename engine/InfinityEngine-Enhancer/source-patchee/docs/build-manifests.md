# Build Manifests

## Purpose

The manifest layer isolates build-specific facts from feature logic. Adding a build should mean adding data, not changing the tile-upscale algorithm or the hook flow.

## Schema

Each manifest carries:

- Build identifier
- Executable file version
- Supported executable product names
- Pattern strings for `LoadArea` and `RenderTexture`
- Reference RVAs for validation and diagnostics
- Runtime offsets
- Render callsite descriptors
- Creature-sprite owner layouts and renderer/texture offsets when that feature is enabled

Keep executable compatibility separate from asset compatibility. Build manifests prove addresses,
layouts and callsites; [`the sprite inventory`](../../../../sprite/index/README.md) proves which
animation IDs, prefixes, BAM variants and ITM mappings exist in the installed game. Neither source
may substitute for the other.

## Callsite Descriptor

Each render callsite records:

- Symbol name
- Offset from `CVidTile::RenderTexture`
- Instruction kind
- Expected opcode
- Displacement offset
- Instruction size
- Whether the target is required

That format is what allows `renderer.cpp` to resolve both `CALL rel32` and `JMP rel32`.

## Current Manifests

Build id: `BGEE 2.7.3.x` (offline-validated; in-game gates pending — see
[validation/bgee-2.7.3-evidence.md](validation/bgee-2.7.3-evidence.md)):

- Executable version `2.7.3.x` (any revision)
- Same signatures and runtime offsets as 2.6.6.x
- Reference RVAs: `LoadArea = 0x27EBD0`, `RenderTexture = 0x4257C0`

Build id: `BG2EE 2.7.3.x` (offline-validated; in-game gates pending — see
[validation/bg2ee-2.7.3-evidence.md](validation/bg2ee-2.7.3-evidence.md)):

- Executable version `2.7.3.x` (any revision)
- Supported product names: `Baldur's Gate II: Enhanced Edition`, `Baldur's Gate II`
- Beamdog ships a unified engine image (the game is chosen at runtime by
  `engine.lua`'s `engine_mode`), so this build shares BGEE 2.7.3's signatures,
  runtime offsets, callsite offsets **and reference RVAs** exactly
- Reference RVAs: `LoadArea = 0x27EBD0`, `RenderTexture = 0x4257C0`
- Area-animation `CGameStatic` offsets: resref `0x1C0`, current frame `0x1C8`, current sequence
  `0x1CA`, world X `0x0C`, drawing Y `0x10`, height `0x14`. Runtime observation on AR0900 proves
  `drawingY = ARE.y + height`; the hook resolves registry-v3 variants with
  `ARE.y = drawingY - height`. The three position offsets are optional: a manifest that omits them
  cannot select bound variants and falls back to unbound resources or the native BAM.
- Optional read-only native-occlusion probe target:
  `CInfinity::FXRenderClippingPolys = 0x29E4C0`, guarded by its exact prologue signature. The RVA
  and signature form an all-or-none pair and do not enable the probe by themselves; see
  [native-occlusion-phase0.md](native-occlusion-phase0.md).
- Optional phase-1 FX surface evidence: staging-pool data `0x2F74050` and its RIP-relative
  reference at `0x42CB1B`. The reference signature and decoded `LEA` must resolve to that exact
  writable non-executable span; partial evidence invalidates the area-animation runtime manifest.
  See [native-occlusion-phase1.md](native-occlusion-phase1.md).

Because BGEE and BG2EE share fixed version `2.7.3`, identity selection matches
on version **and** product name (`find_manifest_for_identity`). Selecting on
version alone would always return the BGEE entry and then fail the product-name
check, leaving BG2EE unsupported.

Build id: `BGEE 2.6.6.x`

Supported executable product names (normalized for punctuation/case):

- `Baldur's Gate Enhanced Edition`
- `Baldur's Gate`

Reference RVAs (not runtime fallbacks):

- `LoadArea = 0x27E710`
- `RenderTexture = 0x4247E0`

Runtime offsets:

- `CVidTile::pRes = 0x100`
- `TIS linear-tiles flag = 0x1DC`
- `TIS header tileDimension = 0x14`

Runtime caveats for the current manifest:

- `CResTileSet::h` is not guaranteed to be populated for every tileset instance.
- Standard tilesets may expose only the PVR entry table via `CRes::pData`.
- Because of that, deterministic runtime classification for this build is header-first, then table-derived.

## Adding Another Build

Use the evidence and validation checklist in
[new-build-validation.md](new-build-validation.md). At minimum:

1. Confirm the hook target RVAs or patterns.
2. Record the executable file version and verify each signature is unique in executable sections.
3. Revalidate the render callsites and instruction kinds.
4. Revalidate every runtime offset, including active-area fields.
5. Add the new manifest entry and host tests.
6. Complete the Windows build and in-game smoke gates before claiming support.

If a new build cannot satisfy those checks, do not guess. Leave it unsupported and fail early.

## Version Gating And Self-Scanning

The runtime identifies the executable by its fixed four-component file version
and version-resource product name, then refuses to install hooks unless that
identity has a known manifest and both hook signatures are unique within the
executable's code sections. The current `2.6.6.x` manifest uses an explicit
revision wildcard; future manifests can pin the fourth component. This is the
intended default for unknown builds (e.g. BGEE 2.7): detect, report as
unsupported, and leave the game untouched.

The runtime cannot safely infer structure offsets and render callsites from an
arbitrary future executable — a byte pattern can be present but semantically
wrong. Supporting a new build therefore stays a two-stage process:

- automatic probe: executable version, signature match counts, target
  prologues, and render-callsite opcode validation;
- reviewed manifest: accept the build only after those results and an in-game
  smoke test agree.

A useful future feature is a `CompatibilityReport` probe-only mode (or
companion CLI) that emits one JSON/Markdown report for an unknown build without
installing hooks. Remotely downloaded manifests are not acceptable unless
signed; otherwise a compromised manifest becomes arbitrary code execution
inside the game process.
