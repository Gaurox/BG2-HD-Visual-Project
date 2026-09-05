# Map Page Off-Frame Phase 3e-B2e Four-Claim Gate

## Status and purpose

Phase 3e-B2e raises only the bounded prepared-consumer limit from three to four claims per area
generation. It retains the B2d in-flight reader retirement handshake, native return values,
resource/cache ownership, memory bounds and default-off configuration unchanged.

The AR0900 gate passed on 2026-08-30. Four prepared pages were consumed, the complete map rendered,
the game remained stable for more than 30 seconds and exited cleanly. This reopens the controlled
four-zone performance campaign, but does not qualify the prototype for release. No
`validated-installed` element was produced, and neither `areas.csv` nor a release manifest was
changed.

## Change and offline gates

The compile-time constant `kMapPageConsumeMaximumClaimsPerGeneration` is four. The bounded-gate
test expects exactly four claims before rejection and the deterministic B2d concurrency test
continues to cover retirement of an identity held by the worker.

The following gates passed:

- common C++ Debug build and CTest: 2/2;
- common C++ Release build and CTest: 2/2;
- Windows x64 Release `release_bundle` build and DLL CTest: 2/2;
- common Python tests: 207/207 in 96.793 seconds;
- exact executable validation for the demand, decode, cache-release and file-open boundaries;
- transaction verify-only preflight and installed/restored receipt verification.

The exact target executable was BG2EE 2.7.3 `BaldurReal.exe`, SHA-256
`B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`.

## Candidate and transaction

Candidate:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2e-20260830\candidate-b2e-four-claim-handshake-v1
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.dll` | 1,544,192 | `1572EC9229D3CDA6D589CE4E657E51018D757FBF437CDF36B730D2EC105CD5DC` |
| `InfinityEngine-Enhancer.ini` | 2,461 | `BB4EE37E468FC9E55B8CEC9799C9039CB29F69D24FEC97B0B1BA2DB41A2A1876` |

Evidence and transaction:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2e-20260830\ingame-ar0900-four-claim-handshake
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2e-20260830\ingame-ar0900-four-claim-handshake\20260830T174721032332Z-8eff3191
```

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.log` | 16,658,366 | `7DB3FC9BC4B22AD9647BE99E291AC018608A22151ADAEC4162AFD821CE606E59` |
| `renderer-install-receipt.json` | 1,993 | `C744B619FCDE45F3367A90693F5FC46385A555015D24C35807C2B50EDE490C37` |
| `renderer-install-receipt-restored.json` | 1,992 | `2528616630BC557A1D3FBB82BFCE6D0F4A2EA5684F1BF2EC611C2F5E73664677` |

## AR0900 result

`A090000` exercised the B2d fallback handshake before any prepared claim. The worker-owned read was
retired in 43.58 ms, the shadow result was discarded and the native resource path then completed
successfully. The four prepared claims were:

| Claim | Page | Decision |
|---:|---|---|
| 1/4 | `A090001` | prepared claim |
| 2/4 | `A090008` | prepared claim |
| 3/4 | `A090009` | prepared claim |
| 4/4 | `A090010` | prepared claim |

`A090011` was also in flight when demanded after the claim limit. Its fallback waited 24.01 ms for
reader retirement and then completed natively. Every later planned page used the native
claim-limit fallback. Across the session, 19/19 observed file opens, 51/51 `CRes::Demand` returns
and 19/19 `CResPVR::Demand` returns are successful; there are zero error/critical log records.

The final shadow summary records:

- 19 submitted and started jobs, 17 prepared and two cancelled/discarded;
- 17 ready-before-demand and two not-ready-before-demand;
- four consumed claims with `consumeClaims=4`, `claimLimit=4`, `consumed=4`;
- two native fallback waits totalling 67.59 ms, maximum 43.58 ms;
- 93.81 MiB compressed and 272.00 MiB decoded;
- 655.05 ms total preparation, maximum 45.06 ms;
- peak completed storage of four pages / 64.00 MiB;
- zero original fallbacks from active claims and zero mismatch/error families;
- zero residual pending, in-flight, fallback-waiter or completed state.

The native prewarm path discovered 26 pages, found seven already resident and materialized 19.
Its total native demand time was 675.06 ms with an 84.80 ms maximum. The map rendered completely,
remained visually stable for more than 30 seconds and the game exited through its normal
confirmation dialog without a crash.

## Restoration and next gate

The receipt was verified while installed, then restored and verified again after confirming that
the game and InfinityLoader were closed. The game root returned exactly to:

- DLL SHA-256 `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E`;
- INI SHA-256 `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

B2e closes the four-claim AR0900 correctness gate. The next step is a transactionally installed,
counterbalanced four-zone performance and robustness campaign on AR0700N, AR0516, AR0602 and
AR0900, keeping the B2d handshake and four-claim bound unchanged. It must record per-zone claim,
fallback/wait, preparation and map-opening metrics, preserve complete rendering and stable exits,
and keep any OS-cold-cache campaign separate. Promotion or release integration remains a distinct
decision after that evidence.
