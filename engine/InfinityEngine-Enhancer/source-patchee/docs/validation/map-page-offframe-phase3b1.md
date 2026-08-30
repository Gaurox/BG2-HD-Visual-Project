# Map Page Off-Frame Phase 3e-B1 Qualification

## Status and scope

Phase 3e-B1 is implemented and qualified offline and ingame for the positively identified BG2EE
2.7.3 `BaldurReal.exe` (`b51093a4...a14d57`). The one-page AR0900 canary gate passed on 2026-08-30
and the exact pre-test renderer was restored afterward. The feature remains disabled by default.
This evidence proves the narrow decoded-PVR handoff and native continuation for one page; it does
not yet prove a multi-page frame-time improvement or release eligibility.

The new option is:

```ini
[Core]
PerformanceLogs = true

[Rendering]
EnableMapPageOffframeConsume = true
```

`EnableMapPageOffframeConsume` defaults to `false`. With `PerformanceLogs=false`, the consumer is
explicitly inactive. `EnableMapPageOffframeProbe` remains the independent read-only 3e-A mode.

## Implemented ownership boundary

The worker still does only override-file I/O, zlib decode and PVR v3 DXT1/DXT5 validation. It now
also records CRC32 over the exact compressed stream after the four-byte PVRZ size prefix. A ready
result can be moved, not copied, out of the bounded four-page/72 MiB completed queue.

The outer `CResPVR::Demand` detour may claim exactly one ready page per area generation. While the
original native `Demand` runs, a scoped thread-local value binds that buffer to the exact
`CResPVR*`. A nested `Demand` replaces the scope, including with an empty candidate, and therefore
cannot consume its caller's page.

The global zlib-wrapper detour substitutes only when all of these checks pass:

- `_ReturnAddress() == moduleBase + 0x3F6F24`;
- the active and claimed `CResPVR*` are identical;
- the native owner, length pointer, source range and destination range are readable/writable with
  non-executable data-page protections;
- `source == CRes::pData + 4` and `sourceLength + 4 == CRes::nSize`;
- native resource bytes equal the prepared file bytes and remain below 32 MiB;
- declared size, native destination capacity and prepared decoded size are identical and remain
  below 20 MiB;
- render-thread CRC32 of the native compressed stream equals the worker CRC32;
- a fresh post-CRC snapshot still has the same native `pData` and `nSize`.

Only then does it copy decoded bytes into the destination already allocated by the engine, write
the exact 32-bit produced length and return `Z_OK`. Native code resumes at `Demand+0x164`, parses
and publishes the PVR fields, uploads the DXT payload and frees its own destination. The prototype
does not edit the 128-entry cache, resource fields, texture name, format, dimensions or GL state.

Missing, late, stale, nested, mismatched and unexpected calls invoke the original embedded zlib
wrapper with the original arguments. A failed claimed canary is not retried in that generation.
Teardown disables/removes the zlib detour before the outer `Demand` detour and worker state.

## Telemetry

The bounded per-area summary now records claims, successful consumptions, original fallbacks,
unexpected return addresses, resource/source/size/CRC mismatches, rejected memory ranges, internal
errors, absent wrapper calls, CRC time and copy time. The one-page record also includes total native
`Demand` time and the exact area/page/generation. Existing `CResPVR::Demand` telemetry continues to
record native upload/texture activity.

## Offline gates completed on 2026-08-30

- Debug CTest: 2/2 passed.
- Release CTest: 2/2 passed.
- Windows x64 Release DLL: built successfully.
- Python project suite: 207/207 passed.
- `tools/validate_build.py`: exact executable identity, unique `Demand` and zlib signatures, nine
  native phase callsites and post-decode window passed.
- Unit coverage: configuration default/parse/round-trip, compressed CRC identity, move-only queue
  claim, generation canary, inactive scope, unexpected caller, owner, source, size and CRC fallback.
- Candidate transaction preflight: passed for exactly DLL + INI, with no game-root write.

Prepared candidate, outside the repository data plane:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b1-20260830\candidate-b1-offline-v1
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.dll` | 1,508,352 | `DAE3173054F0A7BCBCD168B6361551EE96706A2CE61EBD3A36702F51797C1111` |
| `InfinityEngine-Enhancer.ini` | 2,450 | `8C20DF91B6A991F6716A92C42A6D439DCE74088EC351D65397BB89C4FB842B5A` |

The game root remained on DLL `9FCE57D1...FCC98E` and INI `B7B39153...EDE8B5` after the
read-only preflight.

## Ingame gate completed on 2026-08-30

The exact offline candidate above was installed through the renderer transaction while the game
and InfinityLoader were closed. The receipt is:

```text
G:\AI\BG2_Upscale\backups\renderer\20260830T140726573407Z-93391f5e\renderer-install-receipt.json
```

InfinityLoader launched the game, the Shadows of Amn single-player save `AR0900` was loaded, and
the 30-frame delayed prewarm completed. The canary consumed exactly one prepared page:

```text
area=AR0900, page=A090001, generation=3, outcome=consumed,
compressedMiB=6.84, decodedMiB=16.00, crcMs=1.09, copyMs=2.12,
nativeDemandMs=9.89; native cache/upload/free path retained
```

The completed area summary recorded 19 submitted jobs, 18 prepared before demand and one not ready.
There was exactly one claim and one consumption. All fallback/error families were zero:
`originalFallbacks`, `unexpectedReturn`, `resourceMismatch`, `sourceMismatch`, `sizeMismatch`,
`crcMismatch`, `memoryRejected`, `internalError` and `uncompressNotReached`. Peak completed handoff
occupancy remained four pages / 64.00 MiB, below the 72 MiB bound. The native prewarm then reported
19 `Demand` calls and 19 materializations; its total was 709.90 ms and its maximum call 43.69 ms.

The first periodic native area telemetry after the handoff recorded 35 materializations, 35 texture
creations and 35 compressed uploads, while the canary record explicitly confirmed that native
cache/upload/free continued after the substituted decode. The world view and the fully opened
AR0900 area map rendered correctly, without visible seam, corruption, crash or deadlock. The
411-line bounded session contained no error and one warning only: the already documented EEex
`RenderTexture` prologue recovery.

The full journal and a copy of the receipt are archived outside the repository at:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b1-20260830\ingame-ar0900-one-page
```

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.log` | 15,602,022 | `7CBB269CCFD2CB79B2D3DA1FC3B3733E5EE92A7F83EADB49F6F70AA133006C12` |
| `renderer-install-receipt.json` | 1,899 | `26487BA801A065ECB1E41F8784BBBE8A7C02E05F260DDAB78CAFB5610D81330C` |

After the game exited, no `Baldur`, `BaldurReal` or `InfinityLoader` process remained. Restoration
and receipt verification both passed. The game root returned exactly to DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` and INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

## Next gate

Phase 3e-B1 is complete and remains the last ingame-proven consumption boundary. Phase 3e-B2
subsequently implemented a separate default-off candidate with a fixed limit of four ready claims
per area generation and passed its offline gates, but its AR0900 run crashed after three successful
consumptions and before the fourth outcome; see
[`map-page-offframe-phase3b2.md`](map-page-offframe-phase3b2.md). The four-zone performance protocol
is blocked until a corrected bounded candidate passes AR0900 with a fully opened map and stable
exit. These prototypes produced no `validated-installed` element and changed neither `areas.csv`
nor a release manifest.
