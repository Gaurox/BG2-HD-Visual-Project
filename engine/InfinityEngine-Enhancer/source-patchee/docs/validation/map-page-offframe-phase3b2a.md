# Map Page Off-Frame Phase 3e-B2a Diagnostic

## Status and purpose

Phase 3e-B2a is a default-off diagnostic candidate for the positively identified BG2EE 2.7.3
`BaldurReal.exe` (`b51093a4...a14d57`). It was built and tested on 2026-08-30 after the Phase 3e-B2
four-claim candidate crashed in `CResPVR::Demand+0x13D` on `A090010`, following three successful
prepared-buffer consumptions but before a fourth outcome was logged.

B2a was designed to answer one narrow question: did B2 fail while attempting a fourth prepared
claim, or did native fallback fail after the cumulative effects of the first three claims? It makes
no release claim, remains disabled by default and changes neither `areas.csv` nor a release
manifest.

## Diagnostic contract

B2a preserves the B1/B2 decoded-PVR handoff and every strict validation. It changes or adds only:

1. the compile-time claim limit is three, matching the three B2 consumptions that returned;
2. every matching page demand logs its queue state and selected action, including an explicit
   `native-fallback-claim-limit` decision once the third claim has been used;
3. the manifest identifies the exact `CRes::Demand` call at `CResPVR::Demand+0xDC` and its target
   RVA `0x402A00`, with a validated direct-call edge;
4. a transparent diagnostic detour logs the native resource immediately before and after that
   call: active-claim identity, claim ordinal, `pData`, `nSize`, `bLoaded`, texture and return value;
5. the detour never substitutes raw resource data and never changes the native return value or
   resource fields.

The worker, memory and completed-queue bounds are unchanged. The engine still owns resource
loading, its 128-entry PVR cache, texture creation/binding, allocation, field publication, upload
and release.

## Offline gates completed on 2026-08-30

- Debug CTest: 2/2 passed.
- Release CTest: 2/2 passed.
- Windows x64 Release DLL: built successfully.
- Python project suite: 207/207 passed.
- `tools/validate_build.py`: exact executable identity, `CResPVR::Demand`, the new
  `CRes::Demand` call edge, zlib boundary, all native phase callsites and post-decode window passed.
- Unit gate: the limit is exactly three, claims 1 through 3 succeed, claim 4 fails closed, foreign
  generations are rejected and an explicit reset rearms the counter.
- Candidate transaction preflight: passed for exactly DLL + INI, with no game-root write.

Prepared candidate outside the repository data plane:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2a-20260830\candidate-b2a-three-claim-diagnostic-v1
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.dll` | 1,516,032 | `B720C6F3DC45C35ED85232CA6B1FB9AA6A5DCF2AB63CE6E123CC2876180090B2` |
| `InfinityEngine-Enhancer.ini` | 2,461 | `BB4EE37E468FC9E55B8CEC9799C9039CB29F69D24FEC97B0B1BA2DB41A2A1876` |

The read-only preflight left the game root exactly on DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` and INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

## AR0900 diagnostic result

The candidate was installed transactionally while the game and InfinityLoader were closed. The
receipt is:

```text
G:\AI\BG2_Upscale\backups\renderer\20260830T153716160757Z-2b5576dd\renderer-install-receipt.json
```

InfinityLoader launched the game and loaded the Shadows of Amn single-player save `AR0900`. The
plan discovered and planned 26 pages, seven of which were initially resident. The first relevant
page, `A090000`, was not ready and completed ordinary native fallback. The next three pages used
all three diagnostic claims:

| Claim | Page | `CRes::Demand` | Native raw bytes | CRC | Copy | Native PVR `Demand` |
|---:|---|---|---:|---:|---:|---:|
| 1/3 | `A090001` | `true` | 7,172,686 | 1.00 ms | 2.20 ms | 9.75 ms |
| 2/3 | `A090008` | `true` | 6,874,805 | 0.96 ms | 2.35 ms | 10.37 ms |
| 3/3 | `A090009` | `true` | 6,489,575 | 0.89 ms | 2.38 ms | 6.80 ms |

Each claim logged `outcome=consumed` and stated that the native cache/upload/free continuation
returned. The next page produced this decisive sequence:

```text
page=A090010, queueStatus=not-ready, action=native-fallback-claim-limit, claims=3/3
page=A090010, activeClaim=false, claim=0/3,
  preData=false, preSize=0, preLoaded=false, preTexture=0
page=A090010, activeClaim=false, claim=0/3, result=false,
  postData=false, postSize=0, postLoaded=false, postTexture=0
```

The process then raised `0xC0000005`. Direct parsing of the small dump's exception stream records
thread 18832, exception address `0x1403F6EFD`, read access at address zero. With image base
`0x140000000`, this is the same `BaldurReal.exe` RVA `0x3F6EFD`, or
`CResPVR::Demand+0x13D`, seen in B2.

## Conclusion

B2a answers its diagnostic question:

- `A090010` did **not** receive a fourth prepared claim;
- no prepared buffer was active during its `CRes::Demand` call;
- native `CRes::Demand` returned null/false before the decoded allocation at `+0x143` and before
  the zlib handoff at `+0x15F`;
- `CResPVR::Demand` then dereferenced the null raw-resource pointer at `+0x13D`.

Therefore the B2 crash is not a failure inside a fourth prepared-buffer copy. The remaining causal
set is narrower but not yet resolved: a cumulative effect exposed by the earlier substitutions,
the diagnostic/timing environment, or another native resource-accounting interaction makes the
later native load fail. B2a does not prove which earlier claim crosses the threshold and does not
authorize a fix that writes native resource fields.

The B2a ingame gate fails: the full map and stable exit were not validated. At that point B1 was the
last ingame-proven consumption boundary; B2b subsequently extended the stable diagnostic boundary
to exactly two claims. B2/B2a remain rejected for release.

## Archived evidence and restoration

The complete evidence is outside the repository at:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2a-20260830\ingame-ar0900-three-claim-diagnostic
```

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.log` | 15,662,426 | `2F6CBFE019F3907003239B41C2AF29D12AEF123E7A2D80F4CC1116D885C7C965` |
| `InfinityLoader_Crash_2_big.dmp` | 1,487,612,074 | `DE8A668A109FC2A0745E3BBFAD74771C77562103E19157FC4A6951E282131671` |
| `InfinityLoader_Crash_2_small.dmp` | 94,164,875 | `4374C0A63ED9F6832A5DBF2A2F7094300160C43C0FF28E97F133D4516F8FFF0E` |
| `InfinityLoader_Crash_2.log` | 124 | `050677A996DF052E2E22B32367A6E1B798DD562ABD8763E33C36B48AC4D7393F` |
| `renderer-install-receipt.json` (installed state) | 1,916 | `319C6EE096DA7738B9A5E5630CEE15F2F2DB54D4CABFDA28B5EE4552EC89E4C1` |
| `renderer-install-receipt-restored.json` | 1,915 | `DA9CCA9C92F9CDDA420E8B44A2C36EBA1D6F8322DC8E82328DB68D2F1398180D` |

After the crash dialog closed, no `Baldur`, `BaldurReal` or `InfinityLoader` process remained.
Restoration and receipt verification passed. The game root returned exactly to DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` and INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

## Next gate

The two bounded discriminator candidates were subsequently completed; see
[`map-page-offframe-phase3b2b.md`](map-page-offframe-phase3b2b.md):

1. the B1 one-claim replay proved the added `CRes::Demand` diagnostic transparent;
2. exactly two claims also passed, including the later native `A090010` load, full-map display and
   stable exit.

The failure therefore first appears after the third successful substitution. The added `nCount`
read is unusable because the passing one-claim session exposed impossible values on successful
resources; it must not drive or receive a correction. Phase B2c must compare two and three claims
through validated demand/release and PVR-cache function boundaries without changing native fields
or returns. Every run remains AR0900-only, transactional and default-off. Do not attempt a
four-zone run or patch around the native null dereference before a corrected three-claim run passes.
