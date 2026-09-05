# Map Page Off-Frame Phase 3e-B2d In-Flight Retirement Handshake

## Status and purpose

Phase 3e-B2d corrects only the file-reader lifetime collision proved by B2c. The shadow queue now
publishes the identity currently owned by its single worker. When native fallback targets that
same identity, the render thread retires it and waits until the worker has closed the PVRZ and
acknowledged relinquishment. A pending job that has not started is still removed without waiting.

The correction is default-off, bounded to three prepared claims per area generation and changes
no native return value, cache slot or resource field. It passed the AR0900 three-claim gate on
2026-08-30 with a complete map, more than 30 seconds of stable idle time and a clean exit. This is
an ingame-qualified diagnostic boundary, not a release-qualified optimization. No
`validated-installed` element was produced, and neither `areas.csv` nor a release manifest was
changed.

## Queue contract

`MapPageShadowQueue` now distinguishes three ownership states for an identity:

- pending in the deque: native fallback removes it immediately;
- in flight on the worker: native fallback cancels the identity, waits on the queue condition
  variable, then proceeds only after the worker clears `inFlight_`;
- completed: the prepared result may be claimed subject to the bounded consumer contract.

The worker clears and notifies its in-flight identity before publishing or discarding the result.
If the render thread retired that identity while it was being prepared, publication is rejected
and the private buffer is destroyed. The observation and summary telemetry record current
in-flight ownership, fallback waiters, wait count and total/maximum wait duration.

A deterministic concurrency test holds `A090010` on the worker, starts native observation on a
second thread, proves one waiter is blocked, releases the worker, then proves the fallback returns
only after the prepared result is discarded and all pending/in-flight/waiter state is zero.

The common C++ suite passes 2/2 in Debug and Release. The Windows x64 Release DLL builds and its
CTest passes 2/2. All 207 common Python tests pass, `git diff --check` is clean, and the exact
executable validator accepts the manifested demand, decode, cache-release and file-open edges.

## Ingame candidate and transaction

The candidate targeted the positively identified BG2EE 2.7.3 `BaldurReal.exe`
(`B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`).

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2d-20260830\candidate-b2d-three-claim-handshake-v1
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.dll` | 1,544,192 | `3DB2FA2BD9F3931F0803860BC3E488192F5C0132771AC57D28E5174488222C8B` |
| `InfinityEngine-Enhancer.ini` | 2,461 | `BB4EE37E468FC9E55B8CEC9799C9039CB29F69D24FEC97B0B1BA2DB41A2A1876` |

Evidence and transaction:

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2d-20260830\ingame-ar0900-three-claim-handshake
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2d-20260830\ingame-ar0900-three-claim-handshake\20260830T172426281878Z-6f05d3dc
```

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `InfinityEngine-Enhancer.log` | 16,471,311 | `43DCB44C90C419FD7E68183B3E1F292EABEC184F3EA00D3FBCDAFFDA628B828E` |
| `renderer-install-receipt.json` | 1,995 | `37B463EAE2AF42571B268648B4DA97E8AE4EB84B5C44DDC6F3676AE74CD548F0` |
| `renderer-install-receipt-restored.json` | 1,994 | `8162A76C9D03D68F5B96629BED41795AF181C614ADB89EFA95537CA196034A34` |

## AR0900 result

The first planned page exercised the corrected race directly. `A090000` was already owned by the
worker when the render thread needed it. The decision waited 42.04 ms, retired the shadow result,
then entered native fallback with no worker file handle left open:

| Boundary | Result |
|---|---|
| queue decision | `not-ready`, `native-fallback-not-ready`, `fallbackWaitMs=42.04` |
| post-wait queue state | `queueInFlight=0`, `nativeFallbackWaits=1` |
| native file open | `true`, `GetLastError=0` |
| `CRes::Demand` | `true`, 7,015,358 bytes |
| `CResPVR::Demand` | `true`, texture 39 |

The bounded prepared consumer then completed its three claims:

| Claim | Page | Decision |
|---:|---|---|
| 1/3 | `A090001` | prepared claim |
| 2/3 | `A090008` | prepared claim |
| 3/3 | `A090009` | prepared claim |

`A090010` and every later planned page used the native claim-limit fallback successfully. Across
the bounded section there are zero failed file opens, zero false `CRes::Demand` returns and zero
false `CResPVR::Demand` returns. The map rendered completely and remained visually stable for
more than 30 seconds before the game was closed cleanly.

The final shadow summary records 19 submitted jobs, 18 prepared, one cancelled/discarded in-flight
result, 18 ready-before-demand and one not-ready-before-demand. It records exactly one native
fallback wait (`42.04 ms`), three consumed claims, zero original fallbacks from an active claim,
zero mismatch/error families, and no residual pending, in-flight, waiter or completed state.

## Restoration and next gate

The receipt was verified in installed state before restoration and again in restored state. The
game and InfinityLoader were closed first, and the game root is back exactly to:

- DLL SHA-256 `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E`;
- INI SHA-256 `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

B2d closes the B2c correctness blocker at the three-claim boundary. The next controlled gate is a
four-claim AR0900 candidate using the unchanged handshake, still default-off and transactionally
installed. It must prove four successful prepared consumptions, all later native fallbacks, a
complete stable map and a clean restoration before the four-zone performance campaign is
reopened.
