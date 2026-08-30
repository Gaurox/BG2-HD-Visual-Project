# Map Page Off-Frame Phase 3e-B0 Evidence

## Scope and verdict

This is the static boundary audit required after the AR0900 Phase 3e-A shadow gate. It applies only
to the positively identified unified BG2EE 2.7.3 executable:

- file: `BaldurReal.exe`;
- size: 7,202,696 bytes;
- SHA-256: `b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57`;
- image base: `0x140000000`;
- `CResPVR::Demand`: RVA `0x3F6DC0`, runtime-function extent
  `0x3F6DC0..0x3F6F7F`.

**Verdict:** a narrow render-thread consumption boundary exists at the native zlib `uncompress`
call at `CResPVR::Demand+0x15F`. A future prototype may replace that one decompression with a copy
of an exactly matching prepared PVR buffer into the destination already allocated by the engine.
It must leave the surrounding native function in control of resource loading, the 128-entry PVR
cache, texture creation/binding, PVR field publication, compressed upload, eviction and release.

This result does not implement or validate the consumer. It makes Phase 3e-B1 eligible as a
separate fail-closed experiment.

Subsequent status: the B1 consumer was implemented and passed its offline gates later on
2026-08-30. Its separate evidence and still-pending AR0900 ingame gate are recorded in
[`map-page-offframe-phase3b1.md`](map-page-offframe-phase3b1.md). The statements below remain the
historical B0 boundary result.

## Reproducible binary gate

`tools/validate_build.py` now locates both the `CResPVR::Demand` and zlib-wrapper signatures exactly
once, decodes every phase call below and validates the native post-decode window. The command is:

```powershell
python tools/validate_build.py "<BG2EE>/BaldurReal.exe" --reference 2.7.3
```

The same evidence is carried by `PvrDemandRuntime::decodeBoundary` in the C++ build manifest. A
partial boundary fails manifest validation.

## Exact native sequence

| Native phase | Instruction RVA | Offset from `Demand` | Target RVA | Ownership consequence |
|---|---:|---:|---:|---|
| delete evicted texture | `0x3F6E69` | `+0xA9` | `0x413270` | native texture/cache policy remains authoritative |
| shift 127 cache entries | `0x3F6E81` | `+0xC1` | `0x4FA710` | native 128-entry LRU remains authoritative |
| load raw `CRes` data | `0x3F6E9C` | `+0xDC` | `0x402A00` | `CRes::pData`, `nSize`, `bWasMalloced` and `bLoaded` remain native-owned |
| create texture | `0x3F6EEE` | `+0x12E` | `0x413350` | texture name is created by the active engine renderer |
| bind texture | `0x3F6EF8` | `+0x138` | `0x413140` | binding stays on the owning render thread |
| allocate decoded destination | `0x3F6F03` | `+0x143` | `0x502678` | destination comes from the engine/CRT heap path |
| decompress PVRZ | `0x3F6F1F` | `+0x15F` | `0x4000F0` | selected substitution boundary |
| upload DXT payload | `0x3F6F58` | `+0x198` | `0x413240` | renderer-specific compressed upload remains native |
| release decoded destination | `0x3F6F60` | `+0x1A0` | `0x4FDAB8` | the engine frees exactly the buffer it allocated |

The unique wrapper at `0x4000F0` adapts the 32-bit Windows zlib length, calls the embedded zlib
1.2.11 implementation at `0x558C70`, writes the produced length back and returns the zlib status.
There are four direct callers of this wrapper (`0x3F6F1F`, `0x3F815A`, `0x3F82BA`, `0x4060E2`). A
global detour is therefore safe only when it also requires the exact return RVA `0x3F6F24` and an
active, matching `CResPVR::Demand` scope. Every other caller must invoke the original wrapper.

## Native data and cache ownership

`CResPVR::Demand` distinguishes raw resource residency from GPU residency:

- `CRes+0x40` is raw `pData`;
- `CRes+0x48` is raw `nSize`;
- `CRes+0x50` is `bWasMalloced`;
- `CRes+0x51` is `bLoaded`;
- `CResPVR+0x58` is the texture name;
- `CResPVR+0x5C` is the PVR pixel format;
- `CResPVR+0x64/+0x68` are width and height.

For an override resource, `CRes::Demand` at `0x402A00` allocates and fills `pData`, sets `nSize` and
`bWasMalloced`, and returns the raw PVRZ bytes. `CResPVR::Demand` then interprets them as:

```text
pData + 0x00  u32 decoded PVR size
pData + 0x04  zlib stream
nSize - 4     compressed source length
```

It allocates exactly the declared decoded size, passes that destination to `uncompress`, and then
reads the PVR v3 header from the decoded destination. The post-decode window starting at
`Demand+0x164` performs these operations inline:

- payload = decoded buffer + `0x34` + metadata size at PVR offset `0x30`;
- object format = PVR pixel format at offset `0x08`;
- object width = PVR width at offset `0x1C`;
- object height = PVR height at offset `0x18`;
- compressed payload bytes = decoded size minus payload offset;
- native compressed upload, followed by native decoded-buffer release.

The GPU cache is an array of 128 `CResPVR*` at RVA `0x721B70..0x721F70`. A hit is moved to the
tail. A miss deletes the first entry's texture, shifts `0x3F8` bytes (127 pointers), then writes the
new object at `0x721F68`. The release path at RVA `0x3F70B0` removes the object from this array,
deletes its texture and zeros `CResPVR+0x58`; the global cleanup at `0x3F7780` does the same for all
entries. None of this state may be reproduced or edited by the off-frame worker.

## Selected Phase 3e-B1 contract

The consumer must run only on the render thread and only inside the exact native call above:

1. The outer `CResPVR::Demand` detour claims one ready result by generation, area, tileset, page
   resref and page number, then exposes it through a scoped thread-local context while calling the
   original native `Demand`.
2. The zlib-wrapper detour substitutes only when `_ReturnAddress()` is
   `moduleBase + 0x3F6F24` and the scoped `CResPVR*` is still the current object.
3. At the handoff, a fresh safe snapshot must prove `source == pData + 4`,
   `sourceLength + 4 == nSize`, the declared decoded size equals the prepared buffer size, and all
   sizes stay within the existing Phase 3e-A bounds.
4. The worker records a CRC32 of the compressed stream. The render thread recomputes it over the
   native source and requires equality before substitution. This is an immutable-resource integrity
   check, not a security primitive. Any mismatch calls original `uncompress`.
5. The detour copies the already validated decoded PVR bytes into the native destination, writes
   the exact 32-bit produced length and returns zlib `Z_OK`. It does not retain the native pointer.
6. The original native code resumes at `0x3F6F24`, publishes format/size, uploads and frees its own
   destination. The prepared private buffer is then destroyed by the outer scope.
7. Missing, late, stale, mismatched, nested or unexpected calls use original `uncompress` without
   changing native inputs or fields. No exception may cross either detour.

The first consumer must use a separate fail-closed option, default `false`, and a one-page canary
limit per area generation. It must record claimed, consumed, CRC mismatch, size/source mismatch,
unexpected-return-address, original-fallback, copy time and total native `Demand` time. Hook teardown
must disable the uncompress detour before removing the `Demand` detour and before releasing worker
state.

## Rejected boundaries

- **Worker-side native `Demand`:** rejected because it mutates cache/resource state and performs
  renderer calls without the owning context.
- **Whole-function `Demand` replacement:** rejected because it would duplicate the 128-entry cache,
  eviction, release and renderer routing.
- **Jump into `Demand+0x164`:** rejected because it depends on native stack/register state and skips
  the engine allocation contract.
- **Publishing decoded bytes as `CRes::pData`:** rejected because `pData` owns the raw PVRZ envelope,
  not the transient decoded PVR, and its base-resource lifetime is independent of GPU residency.
- **Calling native zlib from the worker then ordinary native zlib again:** remains valid shadow
  telemetry but cannot be claimed as an optimization.

## Gates after implementation

Phase 3e-B1 must first pass pure decision tests for every fallback reason, exact return-address
gating, CRC/size/source validation, one-shot ownership transfer, nested-call rejection, generation
invalidation and teardown order. The exact build validator, Debug and Release suites must remain
green.

The first ingame run is AR0900 with one consumed page and all other pages on native fallback. It
must prove one skipped zlib call, one ordinary native upload/release, correct `CResPVR` fields,
unchanged rendering and exact restoration. Only then may a bounded multi-page AR0900 candidate be
tested. The four-zone performance campaign remains later. No Phase 3e-B0 evidence is a
`validated-installed` release element.
