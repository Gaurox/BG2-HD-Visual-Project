# Map Page Off-Frame Phase 3e-B2b Threshold Qualification

## Status and purpose

Phase 3e-B2b qualified two default-off AR0900 discriminator candidates on 2026-08-30 for the
positively identified BG2EE 2.7.3 `BaldurReal.exe` (`b51093a4...a14d57`):

1. B2b1 replayed the proven one-claim boundary with the B2a native `CRes::Demand` detour plus
   additional `nCount`/`bWasMalloced` observations.
2. B2b2 permitted exactly two prepared-page claims with otherwise identical code and telemetry.

Both candidates passed. Together with the rejected three-claim B2a run, they locate the observed
failure transition: two prepared substitutions are stable, while the first native resource load
after a third successful substitution returns null/false and crashes. This locates a threshold; it
does not yet prove the underlying ownership, allocation or cache mechanism.

The option remains disabled by default. These diagnostics produce no `validated-installed`
element and change neither `areas.csv` nor a release manifest.

## Shared qualification gates

Before each installation, the relevant candidate passed:

- Debug CTest: 2/2;
- Release CTest: 2/2;
- Windows x64 Release DLL build and its Release CTest: 2/2;
- Python project suite: 207/207;
- exact BG2EE 2.7.3 build/signature/call-edge validation;
- read-only DLL + INI transaction preflight.

The only intentional B2b1/B2b2 difference was the compile-time claim limit, respectively one and
two. The decoded-PVR copy, CRC/source/size/owner checks, native-zlib fallback and native
cache/upload/free continuation were unchanged.

## B2b1: one-claim telemetry control

Prepared candidate:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2b1-20260830\candidate-b2b1-one-claim-control-v1
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.dll` | 1,518,592 | `E1F64468761F2C8097A38906CF7D24E0469CB18A04D95C30BF3A065004FD53B5` |
| `InfinityEngine-Enhancer.ini` | 2,461 | `BB4EE37E468FC9E55B8CEC9799C9039CB29F69D24FEC97B0B1BA2DB41A2A1876` |

Installation receipt:

```text
G:\AI\BG2_Upscale\backups\renderer\20260830T160813344051Z-eebc94d0\renderer-install-receipt.json
```

InfinityLoader loaded the Shadows of Amn single-player save `AR0900`. `A090001` consumed the only
claim (`crcMs=0.98`, `copyMs=2.10`, `nativeDemandMs=9.69`). `A090008` and every later observed map
page followed native fallback; their nested `CRes::Demand` and outer `CResPVR::Demand` calls all
returned true. The summary recorded `consumeClaims=1`, `claimLimit=1`, `consumed=1` and zero error
families. The full map rendered correctly, remained stable for more than 22 seconds and the game
exited cleanly. The added detour is therefore transparent at the B1 boundary.

Evidence:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2b1-20260830\ingame-ar0900-one-claim-control
```

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.log` | 15,876,770 | `8E2D6B36B47E9EFB632D550FCA9A0BE92D1B2BBA272C204114E36935BF77BDDF` |
| `renderer-install-receipt.json` (installed state) | 1,913 | `75FADD89B13659978BECC1613C6476D31641379C5B44C1FF394D4301278267DF` |
| `renderer-install-receipt-restored.json` | 1,912 | `EBEDDE40A00621EC1D77E52FB295642E1EF21B970743C7F43DDA54B45F84856C` |

The log is append-only and contains older sessions; the B2b1 conclusion uses the bounded session
beginning at `2026-08-30 18:13:48`.

## B2b2: exactly two claims

Prepared candidate:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2b2-20260830\candidate-b2b2-two-claim-discriminator-v1
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.dll` | 1,518,592 | `AE1A8CBA9A2C94EB7D370584B275F3B1A2AD3E09966F447C25F6951A2CCDBE35` |
| `InfinityEngine-Enhancer.ini` | 2,461 | `BB4EE37E468FC9E55B8CEC9799C9039CB29F69D24FEC97B0B1BA2DB41A2A1876` |

Installation receipt:

```text
G:\AI\BG2_Upscale\backups\renderer\20260830T162136628713Z-f06e0dde\renderer-install-receipt.json
```

The same AR0900 route produced exactly two successful claims:

| Claim | Page | `CRes::Demand` | Native raw bytes | CRC | Copy | Native PVR `Demand` |
|---:|---|---|---:|---:|---:|---:|
| 1/2 | `A090001` | `true` | 7,172,686 | 1.03 ms | 2.13 ms | 9.99 ms |
| 2/2 | `A090008` | `true` | 6,874,805 | 1.08 ms | 2.08 ms | 9.68 ms |

`A090009`, `A090010` and every remaining planned page then selected
`native-fallback-claim-limit`. Each nested `CRes::Demand` and outer `CResPVR::Demand` returned true;
in particular the exact `A090010` load that failed after three B2a claims succeeded here. The area
summary recorded 19 submissions, 18 prepared results, one not-ready result, `consumeClaims=2`,
`claimLimit=2`, `consumed=2` and zero mismatch/error families. The full map rendered correctly,
remained stable for more than 22 seconds and the game exited cleanly.

Evidence:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2b2-20260830\ingame-ar0900-two-claim-discriminator
```

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.log` | 16,035,204 | `DAF0C67ABF3417A0D5507A74753385A723599A9BB8F8A088D286FD41269F140D` |
| `renderer-install-receipt.json` (installed state) | 1,919 | `BB11CC2EABFA1CBD3B50B3C60E52CC928B8795EAA36E18BEBA1E089E45226088` |
| `renderer-install-receipt-restored.json` | 1,918 | `BFAF8ABF386F242F70E48BDF85ACE579B1EED962872BC9317A312D910504170D` |

The bounded B2b2 session begins at `2026-08-30 18:25:16` in the append-only log.

## Restoration

Both runs used the renderer transaction with the game and InfinityLoader closed before install and
restore. After each run no game/loader process remained, the receipt status was `restored`, and the
game root returned exactly to:

- DLL SHA-256 `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E`;
- INI SHA-256 `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

## Threshold conclusion and telemetry limitation

The controlled matrix is now decisive:

| Maximum prepared claims | Last prepared page | First following native page | Result |
|---:|---|---|---|
| 1 | `A090001` | `A090008` | native loads succeed; stable full map |
| 2 | `A090008` | `A090009` (including later `A090010`) | native loads succeed; stable full map |
| 3 | `A090009` | `A090010` | native `CRes::Demand=false`, then null dereference |

Thus the failure first becomes observable immediately after the third successful prepared
substitution. The third copy itself returned successfully; the next ordinary native resource load
is the first failing boundary. This does not justify calling the copy itself corrupt, and it does
not justify patching around the native null dereference.

The proposed `nCount` diagnostic is not trustworthy. During B2b1, otherwise successful PVR loads
reported impossible persistent values such as `538976288`, `1213408043`, `1717989152` and
`1969448306`; B2b2 happened to report zero for the same family. The currently modelled field cannot
be used as a reference count or as evidence of ownership. `bWasMalloced` looks plausible, but its
layout/lifetime has not been independently established either. Neither field may drive a fix or be
written by the prototype.

## Next gate: Phase 3e-B2c

B2c must compare the passing two-claim and failing three-claim cases with field-free lifecycle
telemetry. It must remain AR0900-only, default-off and transactional, and must not change a native
return value or resource field.

The bounded work is:

1. manifest and validate the exact resource-demand/release and 128-entry PVR-cache call edges used
   by this `CResPVR::Demand` path;
2. log only stable identities and function boundaries: page resref, `CResPVR*`, raw `pData` pointer
   and size, prepared-buffer pointer/size, zlib original-versus-substitution decision, cache-slot
   pointer movements, texture id, paired release calls, queue bytes and process committed/private
   bytes;
3. replay max-two and max-three candidates and stop analysis at the first divergence preceding the
   `A090010` native failure;
4. correct only the first proven missing lifecycle operation or violated invariant, then re-run
   max-three on AR0900 before considering a larger limit.

If the lifecycle trace shows no divergence before `CRes::Demand=false`, the next instrumented
boundary is the native allocation/read failure path inside `CRes::Demand`, still observational and
without bypassing its return. No four-zone performance campaign is authorized until a corrected
three-claim run renders the full map and exits stably.
