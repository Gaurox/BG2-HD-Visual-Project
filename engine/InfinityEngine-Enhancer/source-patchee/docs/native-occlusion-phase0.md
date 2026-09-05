# Native occlusion — phase 0 read-only probe

Status: implemented and host-validated on 2026-08-27. Probe neutrality and owner correlation are
validated in game on AR0516 for `CGameStatic` x4 and `Character` xN; the complete representative
matrix, including MonsterIcewind, remains pending. See the
[Phase-1 validation record](validation/native-occlusion-phase1-validation.md).

This phase does not fix occlusion. It establishes the runtime evidence needed before changing the
composition path. It observes whether a registry-backed xN object reaches
`CInfinity::FXRenderClippingPolys`, then correlates that call with the final
`CVidCell::RenderTexture` draw where the replacement texture is bound.

## Safety contract

- `EnableNativeOcclusionProbe = false` by default.
- The probe is available only when an xN area-animation or creature-sprite path is active.
- The only accepted target is the positively identified `BG2EE 2.7.3.x` manifest.
- The target RVA and prologue signature must both match. A missing or different signature disables
  the probe while leaving the existing xN and native paths available.
- The detour forwards all eight arguments unchanged, calls the native routine exactly once, and
  returns its result unchanged.
- It performs no texture readback, surface copy, stencil operation, framebuffer operation, asset
  lookup, allocation proportional to a map, or pixel modification.
- Logging is bounded to 256 deduplication keys per render thread. The fixed upper bound is small
  enough to be immaterial beside the project's 512 MiB pack limit.
- The feature is graphics-only and adds no save payload.

## Validated executable evidence

Official local executable:

- file: `BaldurReal.exe` (Steam BG2EE)
- fixed version: `2.7.3.0`
- SHA-256: `b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57`
- `CInfinity::FXRenderClippingPolys` RVA: `0x29E4C0`
- prologue:
  `40 57 41 55 48 81 EC 18 01 00 00 48 8B 05 ?? ?? ?? ?? 48 33 C4`
- occurrences of that wildcarded signature in the executable: exactly one

The x64 callsites pass:

1. `CInfinity*`;
2. X;
3. Y (drawing Y for `CGameStatic`);
4. vertical reference Z (`-height` for `CGameStatic`);
5. FX rectangle pointer;
6. clipping rectangle pointer;
7. dither selector byte;
8. render flags.

The function returns an integer/boolean result. The probe records this metadata after the native
call. It does not infer polygon coverage from the return value alone.

## Correlation boundary

An observation scope is created only for an xN target:

- area animation: one `CGameStatic::RenderBam` invocation, subject identified by its resref;
- generic monster: one `CGameAnimationTypeMonster::Render` invocation;
- Icewind monster: one `CGameAnimationTypeMonsterIcewind::Render` invocation;
- layered character: one `CGameAnimationTypeCharacter::Render` invocation, including its body,
  weapon, offhand/shield and helmet composition.

Nested non-target objects mask the outer scope. This prevents a clipping call from another world
object being attributed to the xN draw. A sample is emitted only after an external xN texture was
actually bound. A zero-call sample is significant: it distinguishes a native `NoWall`/unclipped
path from a failed correlation.

The log entry contains the owner class, instance address, resref or animation ID encoded as the
subject, native clipping call count and arguments, native result, final draw geometry and flags,
the displaced native texture ID, and the replacement family. It contains no pixel data.

## Enabling a future QA build

The source option is written in the `[Shaders]` section:

```ini
EnableNativeOcclusionProbe = true
```

At least one target path must also be enabled (`EnableAreaAnimationX4`, the AM0205E prototype, or
the creature-sprite xN switch). Changing the option requires a restart. Phase 0 does not authorize
copying a DLL into the game; installation remains a separate explicit decision.

## Automated gates

Before any in-game session:

1. manifest validation accepts the complete RVA/signature pair and rejects either half alone;
2. configuration default remains false and round-trips explicitly;
3. an inactive owner emits no sample;
4. a replaced draw with no clipping call emits an explicit `native_clip=absent` sample;
5. one or more native calls correlate with the final draw and retain the displaced native texture;
6. equivalent frames deduplicate and the fixed key store can be cleared;
7. the native C++ suite and the repository Python suite pass.

## In-game phase-0 matrix

Run two otherwise identical sessions, first with the probe off and then on. Capture the log and
pixel-identical screenshots; the probe must not change the defect or its appearance.

| Case | Purpose | Expected evidence |
|---|---|---|
| AR0900 mirrored occurrences | Same resref, distinct foreground geometry | One owner-scoped sample per replaced occurrence; native clipping call present when the ARE flag permits it |
| AR0517 SPHINCT | Known arch/foreground overlap | Native clipping call correlated before the final x4 draw |
| AR0516 SPHINCT variants | Mixed polygon coverage | Calls/absence agree with the native flags and WED data; no claim based only on polygon existence |
| Registered MonsterIcewind sprite behind foreground | Creature owner path | Native call correlated with the creature replacement draw |
| Registered layered Character behind foreground | Body/equipment composite path | One final replacement sample, with no leakage from nested or foreign cells |
| x1 map or unregistered object | Native fallback | No replacement sample and no behavioral change |
| Save, reload, area transition, pause, fullscreen/resize | Neutrality and lifetime | No save payload, stale owner scope, unbounded log growth, crash, or shutdown error |

## Exit criteria before phase 1

All of the following are required before modifying composition:

- exact executable identity and hook signature recorded in the QA evidence;
- probe-off/probe-on screenshots are visually identical;
- logs prove `FXRenderClippingPolys` occurs inside the owner scope before the final xN draw for at
  least one area animation, one MonsterIcewind sprite and one layered Character;
- `native_clip=absent` is explained by an ARE/render flag or a verified native path, not silently
  treated as success;
- area transitions and shutdown pass with no stale correlation;
- memory remains bounded and the existing x1/x2/x4 pack limits are unchanged.

Only then may phase 1 introduce a visual correction. The preferred experiment remains a global
engine-side bridge at the object-local FX composition boundary, reusing native WED coverage. No
per-animation painted mask is part of this phase or accepted as the general solution.

## Local validation record

- Debug host build: `iee_tests` and `iee_bridge_worker_tests` built successfully.
- CTest: 2/2 passed.
- Full Debug DLL target: built successfully in the isolated CMake directory; not installed.
- Common Python suite: 166/166 passed.
- No game asset, installed INI, installed DLL, registry key, save, or release manifest was changed.

## Rollback

Runtime rollback is the single INI change `EnableNativeOcclusionProbe = false` followed by a
restart. Source rollback is isolated to the optional manifest pair, the bounded correlator, the
hook and the documentation. No asset, registry schema, save, release manifest, or game executable
is migrated by phase 0.
