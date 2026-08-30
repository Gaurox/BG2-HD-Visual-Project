# Map Page Off-Frame Phase 3e-B2 Qualification

## Status and scope

Phase 3e-B2 is implemented and qualified offline for the positively identified BG2EE 2.7.3
`BaldurReal.exe` (`b51093a4...a14d57`) on 2026-08-30. It replaces only the Phase 3e-B1
one-claim generation gate with a compile-time maximum of four ready claims. The decoded-PVR
handoff, strict checks, native-zlib fallback, native cache/upload/free continuation, worker and
memory bounds are unchanged. The option remains disabled by default.

Its AR0900 ingame gate failed with an access violation after three successful consumptions and
before the fourth outcome could be recorded. This exact candidate is rejected and must not proceed
to the four-zone campaign or release. It produces no `validated-installed` element and changes
neither `areas.csv` nor a release manifest.

## Bounded four-page contract

`EnableMapPageOffframeConsume=true` still requires `PerformanceLogs=true` and the existing prewarm
plan. For each area generation:

1. Only a result already ready for the exact area, tileset, page and generation may be claimed.
2. Each ready claim consumes one of exactly four slots, even if the later render-thread validation
   falls back. A fifth claim is impossible until an explicit generation reset.
3. A page that is missing or late is observed/cancelled and follows ordinary synchronous native
   `Demand`; it does not consume a slot.
4. Only one claimed buffer is active during the synchronous native `Demand`. The completed queue
   remains bounded to four pages / 72 MiB, with 32 MiB compressed and 20 MiB decoded per page.
5. The global zlib detour retains every B1 check: exact return address and `CResPVR*`, native source
   identity, sizes, memory protections, compressed CRC32 and a fresh owner snapshot before copy.
   Every mismatch calls the original zlib wrapper with the original arguments.

Telemetry now records `claim=N/4` on each attempt and `consumeClaims`, `claimLimit=4`, success,
fallback families, CRC/copy times and `mode=bounded-four-page-consume` in the area summary.

## Offline gates completed on 2026-08-30

- Debug CTest: 2/2 passed.
- Release CTest: 2/2 passed.
- Windows x64 Release DLL: built successfully.
- Python project suite: 207/207 passed.
- `tools/validate_build.py`: exact executable identity, unique `Demand` and zlib signatures, nine
  native phase callsites and the post-decode field/upload/release window passed.
- Unit gate: the limit is exactly four, claims 1 through 4 succeed, claim 5 fails closed, a foreign
  generation is rejected and an explicit generation reset rearms the counter.
- Candidate transaction preflight: passed for exactly DLL + INI, with no game-root write.

Prepared candidate outside the repository data plane:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2-20260830\candidate-b2-four-page-offline-v1
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.dll` | 1,509,888 | `2030519385A9922E43A597CA290AE74FEE8533003BEA651FAB243ABF10AF8D89` |
| `InfinityEngine-Enhancer.ini` | 2,452 | `B1587B7B6164050577537A31517B88811F30DC53025CCE638C32A8D182D9C178` |

The read-only preflight left the game root exactly on DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` and INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

## AR0900 ingame gate failed on 2026-08-30

The exact candidate above was installed through the renderer transaction while the game and
InfinityLoader were closed. The receipt is:

```text
G:\AI\BG2_Upscale\backups\renderer\20260830T144214642883Z-66e1ba6f\renderer-install-receipt.json
```

InfinityLoader launched the game and the Shadows of Amn single-player save `AR0900` was loaded.
The delayed plan began with 26 discovered/planned pages, seven initially resident pages and no
invalid candidate. Three pages then completed the strict substituted-decode path:

| Claim | Page | Compressed | Decoded | CRC | Copy | Native `Demand` |
|---:|---|---:|---:|---:|---:|---:|
| 1/4 | `A090001` | 6.84 MiB | 16.00 MiB | 1.12 ms | 2.18 ms | 10.17 ms |
| 2/4 | `A090008` | 6.56 MiB | 16.00 MiB | 1.05 ms | 2.30 ms | 9.64 ms |
| 3/4 | `A090009` | 6.19 MiB | 16.00 MiB | 0.99 ms | 2.33 ms | 7.08 ms |

Each record states that the native cache/upload/free path returned. Immediately afterwards the
process raised `0xC0000005` while loading `A090010`; neither a fourth consume outcome nor an area
summary was written. The world view had appeared, but the full-map visual check and stable exit
could not be completed. The gate therefore fails regardless of whether the eventual root cause is
in the bounded handoff or in an interaction exposed by it.

The small dump makes the failure boundary precise:

- exception address: `BaldurReal.exe` RVA `0x3F6EFD`, which is
  `CResPVR::Demand+0x13D`;
- instruction: `mov ecx, dword ptr [rsi]`, with `rsi=0` and attempted read address `0`;
- active native resource: `A090010` (`rbx=0x604C1E0` in this process);
- captured resource state: `pData=0`, `nSize=0`, `bLoaded=false`;
- position in the manifested sequence: after native texture creation/bind at `+0x12E/+0x138`, but
  before decoded-buffer allocation at `+0x143` and before the selected `uncompress` handoff at
  `+0x15F`.

Consequently, the dump does not prove that a fourth prepared buffer reached the zlib substitution;
it proves that the native resource load left a null raw-data pointer immediately before that
boundary. Causality beyond this point remains open and must not be inferred from the three
successful records alone.

The complete evidence is archived outside the repository at:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2-20260830\ingame-ar0900-four-page
```

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.log` | 15,625,331 | `5CAFE3A853FD2741D00CBA803E042DE1BC9E48A71AB2DB36BA8D0A28455D833D` |
| `InfinityLoader_Crash_1_big.dmp` | 1,541,952,903 | `BB2F6C825F2758245D8371C64829D35EFD0F1D48F6263518C5677D9A5441D49A` |
| `InfinityLoader_Crash_1_small.dmp` | 94,168,846 | `AD41F082096C469C7DEF0F94CCDB0DA7A26646C30E19FF55B2D97E7958217822` |
| `InfinityLoader_Crash_1.log` | 124 | `050677A996DF052E2E22B32367A6E1B798DD562ABD8763E33C36B48AC4D7393F` |
| `renderer-install-receipt.json` (installed state) | 1,909 | `3F38EC0E5040C606168A7FD25BB3D11F9B9F31626B6ADB33C794306BF93DB241` |
| `renderer-install-receipt-restored.json` | 1,908 | `C78B5E80B4F1BF1E1AE1140C49CD2FE38B3653B815D578B91293C904562D2905` |

After the crash dialog closed, no `Baldur`, `BaldurReal` or `InfinityLoader` process remained.
Restoration and receipt verification passed. The game root returned exactly to DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` and INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

## Next gate

Phase 3e-B2a subsequently performed the required distinction; see
[`map-page-offframe-phase3b2a.md`](map-page-offframe-phase3b2a.md). With the claim limit fixed at
three, `A090010` explicitly selected `native-fallback-claim-limit`, entered without an active
prepared claim and received `false`/null from native `CRes::Demand` before crashing at the same
address. A fourth prepared copy is therefore eliminated as the immediate failure mechanism.

The required one-claim control and two-claim discriminator were subsequently completed; see
[`map-page-offframe-phase3b2b.md`](map-page-offframe-phase3b2b.md). Both passed with a correct full
map and stable exit. Combined with B2a, they locate the failure onset after the third successful
substitution. The attempted `nCount` observation is not reliable, so the next B2c gate is a
field-free two-versus-three lifecycle trace. Do not replay the four zones before a corrected
three-claim AR0900 run passes.
