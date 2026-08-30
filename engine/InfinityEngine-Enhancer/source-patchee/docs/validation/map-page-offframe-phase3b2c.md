# Map Page Off-Frame Phase 3e-B2c Lifecycle Trace

## Status and purpose

Phase 3e-B2c compared the passing two-claim boundary with the rejected three-claim boundary on
2026-08-30. Both candidates targeted the positively identified BG2EE 2.7.3
`BaldurReal.exe` (`B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`),
were default-off, and changed no native return value, cache slot or resource field.

The trace identifies the first failing native operation. After the third prepared substitution,
the following `A090010` fallback reaches the native file-open helper and returns `false` with
Win32 error 32 (`ERROR_SHARING_VIOLATION`). `CRes::Demand` then propagates `false` with null data,
and `CResPVR::Demand` never returns before InfinityLoader records `0xC0000005`. Cache exhaustion,
eviction, allocation failure and a fourth prepared copy are excluded at that boundary.

The source tree is returned to the ingame-qualified maximum of two claims. This remains a
diagnostic control, not a release-qualified optimization. No `validated-installed` element was
produced, and neither `areas.csv` nor a release manifest was changed.

## Exact manifested lifecycle boundary

The build manifest and offline validator now require all of the following exact 2.7.3 edges:

| Boundary | Exact evidence |
|---|---|
| PVR cache array | RVA `0x721B70`, 128 pointer entries |
| `CResPVR::Demand` cache reference | `Demand+0x19`, RIP-relative target `0x721B70` |
| PVR cache release | RVA `0x3F70B0`, signature-qualified |
| cache-release array reference | `release+0x0C`, RIP-relative target `0x721B70` |
| `CRes::Demand` | RVA `0x402A00`, already manifested by B2a |
| nested resource file-open edge | `CRes::Demand+0xE2`, relative call to RVA `0x408430` |

Runtime installation fails closed unless the signatures, both cache references, the relative
file-open call and readable 128-entry array all match. B2c observes only stable boundaries and
already validated fields: resource identity, raw data pointer/size, loaded flag, texture id,
cache pointer membership, queue occupancy, process memory, I/O counters and handle count. The
rejected guessed `nCount` and `bWasMalloced` fields are not used.

Before the ingame runs, Debug and Release CTest passed 2/2, the Windows x64 Release DLL and its
CTest passed 2/2, all 207 Python tests passed, and the exact executable validator and renderer
transaction preflight passed.

## Two-claim lifecycle control

Prepared candidate:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2c-20260830\candidate-b2c-two-claim-control-v1
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.dll` | 1,541,120 | `62370A36B651335785BD66276722516E01188BCF6671A9442826BC54CA31255A` |
| `InfinityEngine-Enhancer.ini` | 2,461 | `BB4EE37E468FC9E55B8CEC9799C9039CB29F69D24FEC97B0B1BA2DB41A2A1876` |

AR0900 rendered completely and remained visually stable for more than 25 seconds. The bounded
session contains 19 paired `CResPVR::Demand` entry/returns and 19 successful file opens. It
consumes `A090001` and `A090008`; `A090009`, `A090010` and all later pages return successfully
through native fallback. The summary records 19 submissions, 18 ready results, one not-ready
result, `consumeClaims=2`, `claimLimit=2`, `consumed=2`, and zero failure families. No cache release
is expected or observed because occupancy remains far below 128.

Evidence and transaction:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2c-20260830\ingame-ar0900-two-claim-control
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2c-20260830\ingame-ar0900-two-claim-control\20260830T165734652462Z-f7c84bbf
```

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.log` | 16,203,445 | `3FEC6247DCB4905CD70FFF136BE891A852C1960529B747BB813DC5FC9CE92DBB` |
| `renderer-install-receipt.json` | 1,987 | `B69DECF065C8A5EB93AD3C805CB9C5516952736171C5937FA1816A4B1D105465` |
| `renderer-install-receipt-restored.json` | 1,986 | `BF30868121F53B21D20B85A104065FFA831D07E6271F6235D2AE3B9657DA2FEB` |

## Three-claim failure trace

Prepared candidate:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2c-20260830\candidate-b2c-three-claim-trace-v1
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.dll` | 1,541,120 | `FC401F7402F9695349638EA20FFDD868CBEB8AD44048116DA71FCD8BAD6DA4EE` |
| `InfinityEngine-Enhancer.ini` | 2,461 | `BB4EE37E468FC9E55B8CEC9799C9039CB29F69D24FEC97B0B1BA2DB41A2A1876` |

The first four planned page boundaries are decisive:

| Page | Decision | File open | `CRes::Demand` | PVR result |
|---|---|---|---|---|
| `A090000` | not-ready native fallback | `true`, error 0 | `true`, 7,015,358 bytes | `true`, texture 39 |
| `A090001` | prepared claim 1/3 | `true`, error 0 | `true`, 7,172,686 bytes | `true`, texture 40 |
| `A090008` | prepared claim 2/3 | `true`, error 0 | `true`, 6,874,805 bytes | `true`, texture 41 |
| `A090009` | prepared claim 3/3 | `true`, error 0 | `true`, 6,489,575 bytes | `true`, texture 42 |
| `A090010` | not-ready native fallback after limit | **`false`, error 32** | **`false`, null/0** | no return before crash |

At `A090010`, the cache contains only 36/128 entries, the resource appears exactly once at slot
127 after native insertion, and no cache-release entry occurred. Handles remain at 795; working
set and private bytes have already fallen from the preceding peak to 656,314,368 and
1,117,528,064 bytes. The first failure is therefore the native file open, not resource allocation,
cache eviction, handle exhaustion or prepared-buffer validation.

The queue state explains the timing. `A090010` is known but not ready while the single shadow
worker has removed it from the pending deque and is still preparing it; 14 later jobs remain
pending. The current queue retires that known identity and immediately enters native fallback,
without waiting for the in-flight worker to release its file handle. The worker is the only new
reader introduced by the prototype, and the native helper rejects the overlap with
`ERROR_SHARING_VIOLATION`. This is the first demonstrated violated invariant. It is not evidence
that the decoded copy, native cache or texture publication is corrupt.

Evidence and transaction:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2c-20260830\ingame-ar0900-three-claim-trace
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2c-20260830\ingame-ar0900-three-claim-trace\20260830T170403558956Z-69b47fc8
```

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.log` | 16,282,666 | `DECFF22C44F449846BEFFCE31488F87C5CDE70C0706E1733B29C2B90606D6B85` |
| `InfinityLoader_Crash_3.log` | 124 | `050677A996DF052E2E22B32367A6E1B798DD562ABD8763E33C36B48AC4D7393F` |
| `InfinityLoader_Crash_3_small.dmp` | 94,176,143 | `777EAEB52AC785977A2305DA23407134EB4749A46D6322BB4667C936494D6D1F` |
| `renderer-install-receipt.json` | 1,987 | `F50757BB630676C218B9F38F74E221D6D3ED00694297D9BE90C16565557F1450` |
| `renderer-install-receipt-restored.json` | 1,986 | `97CB330D725A02250D12FA8495B78FAE4E54B0F482AF3D458AE68B3B47F66822` |

The full 1,509,459,687-byte dump remains in the game crash directory with SHA-256
`034C85A9B74BD10390F465FE72B273D4B1C95343F7826A1B8A7494DDD89BD672`; the smaller archived dump
is sufficient to preserve the test evidence without duplicating 1.5 GB.

## Restoration and next gate

Both tests were installed and restored only with the game and InfinityLoader closed. Each receipt
was verified in installed state before restoration and again in restored state. The game root is
back exactly to:

- DLL SHA-256 `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E`;
- INI SHA-256 `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

Phase 3e-B2d must correct only the proven overlap. The queue needs an explicit in-flight identity
and a cancellation/retirement acknowledgement: if native fallback targets the page currently
owned by the worker, the render thread must not enter native file open until that worker has
closed the file and relinquished the identity. Pending-but-not-started jobs can still be removed
without waiting. The fix must be covered by a deterministic queue concurrency test, keep all
native return values authoritative, and then pass the three-claim AR0900 route with a complete
map, stable idle interval and clean exit. Only after that proof may a larger claim limit or the
four-zone performance campaign be reconsidered.
