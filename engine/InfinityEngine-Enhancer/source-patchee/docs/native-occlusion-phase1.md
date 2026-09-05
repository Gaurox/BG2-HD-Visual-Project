# Native occlusion — phase 1 structural bridge

Status: source prototype implemented and host-validated on 2026-08-27; the local Phase-1 milestone
is validated in game for an AR0516 `CGameStatic` x4 animation and a `Character` xN creature.
The xN edge-support correction is validated on `BUBBLES2` in AR0411, AR0602 and AR0603 on
2026-09-05. The option remains disabled by default and release-wide QA is pending. See the
[Phase-1 record](validation/native-occlusion-phase1-validation.md) and the
[BUBBLES2 record](validation/native-occlusion-bubbles2-edge-clear-20260905.md).

Phase 1 does not add masks to BAMs or maps. It transfers the visibility operation already
rasterized by the native WED path from the engine's logical x1 FX surface to the external x2/x4
texture immediately before the existing final `CVidCell::RenderTexture` draw.

## Why the bridge captures pre/post FX pixels

The final native texture cannot be used as an occlusion mask by itself. Its alpha already contains
the BAM's own transparency, palette realization, object translucency and dither. Multiplying that
alpha into the xN frame would apply some of those terms twice.

The exact transfer is instead measured on the same CPU FX allocation:

```text
native FXRender result before WED clipping
  -> CInfinity::FXRenderClippingPolys
native FX result after WED clipping
  -> per-pixel visibility transfer
  -> xN GPU backing
  -> original CVidCell::RenderTexture
```

For an ordinary clipped/dithered pixel whose RGB is unchanged, phase 1 stores
`postAlpha / preAlpha`. Thus the BAM's original alpha cancels. The two other operations proved in
the executable are represented explicitly: complete-pixel clear becomes zero visibility, and the
fixed-black dither operation `0x4F000000` retains its exact alpha. A third transfer channel marks
an x1-transparent logical cell only when it touches an exact complete clear; the shader then
removes xN edge pixels introduced inside that cell. Any other RGB mutation is not approximated:
it invalidates the object-local capture and retains the existing xN draw.

## Verified executable evidence

Official local `BaldurReal.exe`:

- fixed version `2.7.3.0`;
- SHA-256 `b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57`;
- `CInfinity::FXRenderClippingPolys = 0x29E4C0`;
- OpenGL FX staging-pool data `0x2F74050`;
- pool reference `0x42CB1B`:
  `48 8D 05 2E 75 B4 02 48 03 D8 44 8B 43 28 41 C1 E0 15`;
- the RIP-relative `LEA` resolves exactly to `0x2F74050`.

Disassembly proves that the two OpenGL FX allocators are 0x30 bytes apart. Their current CPU
allocation pointer, pitch, X/Y allocation origin and engine texture ID are read without calling an
extra engine allocator function. The pool reference, target data span, three texture-table
references and secondary-name field are all checked before activation.

The native small-polygon path at `0x29DA40` reads `CInfinity::m_RasterizedPolys` at `+0x2B8`, gets
the current 32-bit FX pixel buffer and dispatches the clipping kernels. The observed kernels either
halve alpha, clear the complete pixel, or write the fixed black-alpha value `0x4F000000`. The
large-polygon path at `0x29D6E0` uses the downsampled/rasterized WED data at `+0x2D0`. This confirms
that the WED polygons affect the locked logical FX composition, before unlock/blit and before the
final GL draw displaced by the xN hook.

## Runtime contract

The option remains off unless explicitly enabled under `[Shaders]`:

```ini
EnableNativeOcclusionBridge = true
```

Activation additionally requires:

- a registry-backed area-animation or creature xN path;
- the exact BG2EE manifest, clipping signature and FX pool evidence;
- OpenGL with the shader/FBO entry points used by the existing renderer;
- one stable object-local FX allocation for the owner scope;
- a successful native clipping call and an actual supported pixel change;
- final logical dimensions equal to the captured FX dimensions;
- an external backing whose physical dimensions are exactly x2 or x4;
- no active diagnostic full-frame SSAA2x viewport hook;
- a transient physical RGBA target no larger than 64 MiB.

The CPU capture is limited to 2,097,152 logical pixels. It keeps two 32-bit snapshots only during
one owner render. The transfer texture is logical x1; the output texture is transient and marked
delete-pending immediately after the queued engine draw. These allocations do not change the
512 MiB pack format or its resident-payload limit.

## Coverage and compatibility

- Registry v1 and v2 area packs: eligible without conversion.
- Registry v3 unbound resources: eligible.
- Registry v3 position-bound variants: deliberately bypassed because that format's existing
  contract carries occurrence-specific baked foreground masks; applying a native partial dither a
  second time would change those validated pixels.
- Creature x2/x4 Monster, MonsterIcewind and Character scopes: eligible; a multi-call allocation
  mismatch fails closed and must be resolved from in-game evidence.
- AM0205E historical prototype: excluded; it is not a production registry path.
- x1 maps, unregistered objects, effects outside the three modeled creature owners, WBM/PVRZ area
  animations and screen/UI overlays: unchanged.
- Saves: no schema, serialized state, resource identity or gameplay data is added.
- Blended x4 edge expansion: validated on all 28 `BUBBLES2` occurrences in AR0411, AR0602 and
  AR0603; a complete clear writes transparent black so additive RGB cannot survive outside the
  native support.

The correction is therefore engine-global for every eligible runtime object. It is not authored
map by map. A map can still lack a relevant native polygon, set the ARE `No Wall` flag, or use an
unmodeled object class; those cases correctly retain their existing rendering and are QA outcomes,
not requests for painted per-animation masks.

## Automated gates

The host suite verifies:

Execution requires the explicit targeted/all/none choice from
[`../../../../docs/TEST_SELECTION.md`](../../../../docs/TEST_SELECTION.md). The list below defines
the evidence required to claim the host suite passed; it does not authorize automatic execution.

1. the manifest rejects partial clipping or FX-pool evidence;
2. the bridge and probe default off and round-trip independently;
3. successful clipping calls are counted separately from calls returning zero;
4. pre/post pixels produce exact complete clear and half-alpha visibility;
5. the fixed-black native dither operation is retained;
6. transparent source pixels do not invent a factor;
7. an x1-transparent cell adjacent to a complete clear receives the exact xN edge-clear marker;
8. geometry or surface-identity changes invalidate the capture;
9. a native call reporting no processed polygon cannot enable composition;
10. v1/v2/unbound v3 resources remain structurally eligible while bound v3 masks are preserved;
11. the complete Debug DLL and both CTest targets build and pass.

## In-game A/B gates

Phase 0 remains a prerequisite for claiming the visual correction validated. After its neutrality
matrix passes, compare bridge off/on with identical saves, camera position, zoom and frame:

| Case | Required result |
|---|---|
| AR0517 SPHINCT arch | xN pixels pass behind the same foreground as native x1; no halo or double alpha |
| AR0516 mixed SPHINCT occurrences | WED/ARE differences are respected without per-occurrence authoring |
| AR0900 mirrored occurrences | unbound/native bridge behavior is global; bound v3 legacy pixels remain unchanged |
| MonsterIcewind behind branch/arch | creature is clipped at the native boundary; animation and palette remain unchanged |
| Layered Character with equipment | one coherent final composite is clipped; weapon/shield/helmet do not desynchronize |
| Partial/dither polygon | native half-alpha/fixed-black pattern matches x1 when enlarged with nearest sampling |
| AR0411/AR0602/AR0603 BUBBLES2 | no Blended RGB or xN-smoothed edge survives outside the native foreground boundary |
| ARE `No Wall` / no polygon | no transfer draw and no visual change |
| x1 map / unregistered object | no bridge allocation and pixel-identical native fallback |
| Save/reload, area transition, pause, zoom, resize/fullscreen | no stale capture, crash, GL-state leak or save change |

Record logs for activation, dimension mismatch, 64 MiB rejection and fail-closed paths. Measure GPU
frame time and peak process/GPU memory in a crowded area with creatures before widening coverage.

## Rollback and promotion criteria

Runtime rollback is `EnableNativeOcclusionBridge = false` followed by a restart. No pack, BAM,
WED, ARE, save, registry key, release manifest or game executable needs restoration.

Do not promote this prototype to release until all of the following are true. An explicitly
authorized local QA installation may exercise a smaller milestone, but its exact coverage and
remaining gates must be recorded:

- phase-0 probe off/on neutrality and owner correlation are recorded;
- every representative A/B case above passes, including partial dither and layered Character;
- bridge-off screenshots remain identical to the current released runtime;
- v1/v2/v3 pack compatibility is demonstrated with hashes unchanged;
- no unsupported RGB transfer, surface mismatch or GL error occurs in the representative matrix;
- process and GPU memory stay within the documented transient bounds and the pack remains within
  its existing 512 MiB limit;
- shutdown, context recreation and area transitions are clean;
- the user explicitly approves installation or a release-manifest change.
