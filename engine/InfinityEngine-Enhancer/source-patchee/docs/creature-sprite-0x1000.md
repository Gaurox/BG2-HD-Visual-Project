# Creature sprites `0x1000`: structure and engine plan

Status: static investigation and initial engine implementation complete; isolated build/tests pass.
Firkraag `0x1200` / MDR1 ReboutCX x2 installed and accepted by the user on 2026-09-14.
Other owner-4/5 families are outside this validation.

## Scope

Only BG2EE `animation_type=1000` instances in these native subclasses:

| engine section | exact animation IDs | native parts |
|---|---:|---:|
| `monster_quadrant` | `1000`, `1003`, `1004`, `1100`-`1105` | 4 |
| `multi_new` | `1200`-`1208` | 9 |
| `multi_new` | `1300` | 4 |

INI section/catalog owner is not proof of the native C++ class: Firkraag `0x1200`
uses `MonsterMulti` in game (2026-09-14 trace). Owner `5` remains the serialized
contract; add a separate native hook restricted to `0x1200`. Other IDs remain on
their existing routes until tested; never replace the `MultiNew` hook globally.

Do not route the whole high nibble as one class. Do not extend any other nibble.

## Inputs read

- `sprite/README.md`
- `sprite/PROCESSING.md`
- `sprite/XBR2X_RASTER_CONTRACT.md`
- `sprite/index/README.md`
- complete render path in `src/iee/creature_sprite_x2.cpp`,
  `src/iee/creature_sprite_filter.cpp`, and `src/iee/hooks.cpp`
- `sprite/index/sprite_animations.csv`, `sprite/index/sprite_families.csv`,
  `sprite/index/family-groups.csv`, stock `chitin.key`/BIF BAM bytes
- BG2EE executable stated below; static disassembly only

## Native engine evidence

Executable:

- path: `G:/SteamLibrary/steamapps/common/Baldur's Gate II Enhanced Edition/BaldurReal.exe`
- SHA-256: `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`
- image base: `0x140000000`
- hash equals `sprite/index/manifest.json`

`CGameAnimationTypeMonsterQuadrant::Render`:

- RVA `0x3305A0`; the same vtable contains the parser referencing `[monster_quadrant]`
- unique signature:
  `40 55 53 41 54 41 55 41 57 48 8D 6C 24 F9 48 81 EC D0 00 00 00 48 8B 05 ? ? ? ?`
- current `CVidCell` array pointer: `this+0xCD8`
- part-count byte: `this+0xD59`
- `CVidCell` stride: `0x138`
- loop prepares and renders each cell separately

`CGameAnimationTypeMultiNew::Render`:

- RVA `0x32FD20`; the same vtable contains the parser referencing `[multi_new]`
- unique signature:
  `40 55 53 56 41 56 41 57 48 8D 6C 24 F9 48 81 EC C0 00 00 00 48 8B 05 ? ? ? ?`
- current `CVidCell` array pointer: `this+0xCD8`
- part-count byte: `this+0xD35`
- `CVidCell` stride: `0x138`
- loop prepares and renders each cell separately

Common validated `CVidCell` fields remain applicable: palette `+0x08`, resref `+0x110`, frame
`+0x118`, sequence `+0x11A`. The existing `CVidPalette::Realize` capture and
`CVidCell::RenderTexture` replacement boundary can therefore be reused.

`CGameAnimationTypeMonsterMulti::Render` — Firkraag correction:

- entry RVA `0x32F8D0`; signature
  `40 55 53 56 57 41 54 41 55 41 57 48 8D 6C 24 F9 48 81 EC D0 00 00 00 48 8B 05 ? ? ? ?`;
- vtable Render slot `0x5AA3A0`; same vtable parser slot `0x5AA458` → function
  `0x340890` → `[monster_multi]` reference at `0x340948`;
- current cells `+0xCD8`, count byte `+0x12F9`, stride `0x138`; native loop bound
  reads at `0x32F9A7` / `0x32FCDF`; 14-argument Render ABI, native geometry retained;
- session `2026-09-14 15:04:34–15:05:02`: palette stack
  `0x4242D3 ← 0x41D685 ← 0x29E459 ← 0x32FC10`; chained unwind maps `0x32FC10`
  to entry `0x32F8D0`; nine cells `MDR12100`…`MDR12900`, sequence `0`, slot `1`;
- `0x32FD20` / count `+0xD35` describe a different class; retain that hook.
  The earlier sequence-63 warning belonged to Character `0x6100`; remove the
  inferred inactive-cell exception. All nine frames must resolve before HD selection;
- session `15:17:52–15:18:29`: owner/frame/palette selection succeeds, `0/9` replacements;
  native packed extent `111x139` vs binder's bordered `113x141`. `MonsterMulti` must
  explicitly request `FrameTextureLayout::Unbordered` (restricted to `0x1200`, x2):
  descriptor = BAM `W×H`, GPU backing = `2W×2H`, content offset = `0`; preserve native
  draw/clip/UV arguments. Layout is part of the GPU cache key and byte accounting.
  All existing callers default to `Bordered`; Character/composite remains unchanged;
- session `15:28:30–15:29:27`: `9/9` replacements confirmed, 117 unique MDR1
  compositions x2/unbordered; user reports correct rendering except isolated frames.
  Shards `444/445` loaded at first appearance; `446/447/448` loaded on action changes;
- optimization: after installing the MonsterMulti hook, `prefetch_mdr1_metadata()`
  queues one directory resref per shard through the existing worker. Scope: V2/x2,
  `0x1200`, owner `5`, one component, all resrefs `MDR1*`, at most 8 shards (current: 5).
  SHA/identity/quarantine/epoch checks and metadata budget unchanged; no pinning,
  synchronous shard I/O, index inflation or GPU upload. Eviction can still cause later
  lazy loading; this targets metadata latency, not model flicker or every cold-frame cost;
- diagnostic v3: count actual `RenderTexture` submissions independently of successful
  palette capture. `6` submitted / `6` replaced / `9` registered is INFO, not failure.
  WARN only on observed native fallback or uncorrelated draws; do not infer clipping.
  Samples report `submittedDraws`, `nativeFallbackDraws`, `uncorrelatedDraws`;
- validation: Release build + `iee_tests` (multi-shard prefetch, deduplication, lazy
  payloads, unrelated component isolation, unsupported scope, release/cancellation).
  Runtime markers for `C:CreateCreature("FIRKRA02")`: startup `prefetch queued: 5 shards`,
  all five ready before first appearance; `9/9` replacements or all submitted draws HD.
  User accepted the optimized installed rendering on 2026-09-14: "c'est tout bon ! valide et commite".
  Scope is the user's tested encounter, not exhaustive frame/action coverage. Immutable decision:
  `sprite/index/qa-decisions/multi-new/2026-09-14-accepted-1200-mdr1-firkraag-reboutcx-x2-v1.json`;
- install via `tools/install_renderer_candidate.py`; preserve INI/catalog hashes;
  rollback via that install receipt's `restore`. No asset rebuild/catalog migration.

Decision: preserve the native 4/9 independent draw calls and replace each registered cell directly.
Never send these owners through `bind_composite_texture`.

## Stock BAM structure

All counts below come from decoded BAM headers/cycle lookup tables, not filename assumptions.

### Resource grammar

| prefix | observed stock structure | interpretation |
|---|---|---|
| `MWYV` | `G11`-`G14`, `G21`-`G24`, `G31`-`G34` | 3 groups x 4 quadrant parts |
| `MTAN` | same 12 quadrant BAMs; 38 additional IWD-style BAMs | only the 12 quadrant names belong to this renderer; prefix is shared with `0xE020`/`0xE090` |
| `MDEM` | 52 BAMs: 4 base parts plus numbered variants in `G1` and `G2` | 4 simultaneous parts; exact runtime reachability of every suffix is not proven statically |
| `MDR1`/`2`/`3` | 567 each = 7 groups x 9 directions x 9 parts | 9 simultaneous body parts; cycle tables are sparse/padded and group-specific |
| `MWDR` | no exact/prefix BAM in KEY/BIF or override | `1101`/`1105` are absent from this installation, not merely missed by `stock-prefix` |

`MWYV` inventory's 19 resources includes the 12 quadrant BAMs plus six non-quadrant
`G1/G1E/G2/G2E/G3/G3E` BAMs and `INV`; those seven are not part of the native quadrant draw loop.
`MTAN`'s prefix count similarly mixes two native animation classes and must not become a catalog
membership rule.

Representative decoded files:

- `MDR11100`: 108 frames, 9 cycles; cycle 0 contains 12 frames; other direction suffixes activate
  their corresponding cycle.
- `MDR14100`: 99 frames, 45 cycles; active cycles are sparse. `MDR14110` and `MDR14120` activate
  different cycle bands.
- `MDEMG11`: 549 frames, 54 cycles; `MDEMG111`/`MDEMG115` activate distinct cycle bands.
- `MDEMG21`: 522 frames, 63 cycles; numbered variants extend through `MDEMG216`.

The `567 BAM` dragon count is real storage structure, not 567 simultaneous layers. Runtime
composition is 9 parts selected across action/direction/resource variants.

### Simultaneous-frame geometry

Bounds align same-cycle/same-slot parts using BAM centers. Memory is one transient RGBA union at
x2 and is shown only to prove why CPU composition is invalid; direct replacement allocates one
part texture at a time.

| prefix/group | parts | maximum decoded union | largest x2 RGBA union |
|---|---:|---:|---:|
| `MWYV G1/G2/G3` | 4 | up to `248x197` | about `0.52 MiB` |
| `MTAN G1/G2/G3` | 4 | up to `216x175` | about `0.48 MiB` |
| `MDEM G1/G2` | 4 | up to `268x306` | about `1.09 MiB` |
| `MDR1 G1` | 9 | `228x579` | about `2.01 MiB` |
| `MDR1 G4` | 9 | up to `582x480` | about `4.19 MiB` |
| `MDR2 G1/G4` | 9 | up to `309x573` / `522x540` | about `2.68` / `3.88 MiB` |
| `MDR3 G1/G4` | 9 | up to `306x561` / `522x537` | about `2.59` / `3.66 MiB` |

The character-only CPU composite path has `kMaximumCompositeLayers=8` and a 512 logical-pixel
dimension bound. Dragons violate both constraints. Raising those limits would also discard the
native part-level clipping/order semantics.

## Registry/catalog impact

Add two owner codes while preserving existing values:

| owner | code | animation contract |
|---|---:|---|
| Character | 1 | existing `0x5000`/`0x6000` |
| MonsterIcewind | 2 | existing `0xE000` |
| Monster | 3 | existing `0x7000` |
| MonsterQuadrant | 4 | exact set above |
| MultiNew | 5 | exact set above |

No catalog or registry version bump is needed: owner is already a `uint32`, memberships already
map one component to multiple animation IDs, and sharding already supports these counts. An old DLL
rejects owner 4/5 and fails closed; the updated DLL remains compatible with owner 1-3 catalogs.
Legacy monolithic/set packs can derive owner 4/5 from the same exact ID sets.

Scanner/catalog rules must follow native resource grammar, not prefix alone:

- `MWYV`/`MTAN`: include the 12 `G[123][1-4]` quadrant components only.
- palette variants share component membership with their base animation ID.
- `MWDR`: keep absent until bytes exist; never fabricate an empty runtime family.
- `MDEM`/`MDR*`: retain inventory coverage until a runtime resref trace proves a smaller reachable
  set. Open-source naming is corroboration, not authority for BG2EE's proprietary suffix grammar.

## Implementation plan/status

1. [x] **Owner/catalog model**
   - add exact-ID predicates and owner 4/5 parser support;
   - expose per-animation and aggregate owner queries;
   - unit-test valid owner 4/5 catalogs, cross-owner rejection, legacy routing, and release reset.
2. [x] **Build manifest**
   - append (never insert into the positional aggregate) both Render RVAs/signatures, shared cell
     array offset/stride, and both part-count offsets;
   - validate the appended evidence as an all-or-nothing block;
   - unit-test values and partial-manifest rejection.
3. [x] **Owner scopes**
   - raise the scope's direct-cell capacity from 4 to 9; leave the character composite bound at 8;
   - detour the two Render methods with the already validated 14-argument ABI;
   - before invoking native Render, validate exact animation owner, native part count, array pointer,
     and every 4/9 `CVidCell` frame;
   - arm the scope only when the complete set resolves; otherwise render all parts natively;
   - reuse per-cell palette capture/direct bind and existing fail-closed logging.
   - residual runtime risk: a GL/palette failure after preflight can leave an individual draw native;
     emit partial-replacement diagnostics and require controlled in-game validation before promotion.
4. [x] **Isolated verification**
   - configure/build outside the source tree; run native unit tests;
   - inspect the produced DLL only as a build artifact; do not copy it to the game.
5. [ ] **Pipeline/catalog follow-up**
   - completed: `current_runtime()`, catalog codec/job validation, owner labels, exact animation-ID
     contracts, and unit tests for owners 4/5;
   - pending: encode the exact `MWYV`/`MTAN` component grammar in the family-job adapter and rebuild
     generated inventory/catalog artifacts;
   - first proof pack: one stock-present quadrant base family (`1000` is the smallest useful path),
     then `1100`; defer bulk generation.
6. [ ] **Game validation (separate authorization)**
   - `0x1200` / MDR1 ReboutCX x2: installed and user-accepted 2026-09-14 (decision above);
     other families remain unvalidated by this trial;
   - only after explicit confirmation: confirm game and InfinityLoader are closed, install one test
     DLL/catalog, launch one controlled encounter, inspect logs/render, then restore or promote.

## Effort/priority decision

Engine support is reasonable: two closely related owner scopes, no new texture format, no CPU
stitcher, no registry version migration. Full asset production is not reasonable as one batch:

- `MWYV` + `MTAN`: 24 distinct quadrant BAMs cover the stock-present base IDs and have the best
  proof/encounter return.
- dragons: three physical prefixes total about `1.2 GiB` of source inventory before x2 payload
  encoding; 20 stock CRE references across all color IDs.
- `MDEM`: about `235 MiB` inventory for one stock CRE reference.

Recommendation: land/test the generic engine framework, prove `1000`, then `1100`; explicitly
defer `MDEM` and dragons until their encounter value justifies catalog generation and QA cost.
