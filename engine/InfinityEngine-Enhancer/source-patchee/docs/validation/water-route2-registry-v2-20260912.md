# Water route 2 registry v2 — 2026-09-12

## Scope

- Source: `assets/water-route2/registry-v2.json`.
- Parent evidence: `pipeline/water/route2-registry-v1.json`, SHA-256 `E23E942D8E5D0E37F4E8455D9937F1009B81DBD4C98AA02B9F2499664AA5A909`.
- Approved identity: AR0900 day, overlay slot 1, WTLAKE, `q=1.00`.
- All absent, ambiguous, divergent or unapproved identities: native fallback, `q=0`.

## Engine contract

- The build generator validates the parent hash and emits an immutable compile-time table.
- The runtime validates every manifested override file size and SHA-256 before publishing an entry.
- Matching covers area, WED, variant, ordered overlay slots, tile counts, overlay coverage, PVRZ page identity and dimensions.
- Route strength is capped by both the runtime request and the registry approval.
- No map-specific branch remains in the matcher or shader hook.

## Build receipt

| Field | Value |
|---|---|
| Generator | Visual Studio 16 2019, x64 |
| Configuration | Release |
| Tests | `BUILD_TESTING=OFF`; none executed per user choice |
| Target | `InfinityEngine-Enhancer` |
| DLL | `build/iee-water-route2-registry-v2-20260912-vs2019/Release/InfinityEngine-Enhancer.dll` |
| Bytes | `1774080` |
| SHA-256 | `9823C8C8F5F5DB46523947243BEDCC8D986A6740C5F97FC91121ED6C55C608C7` |

## Boundary

- Build only; not installed.
- No game or InfinityLoader mutation.
- No release manifest, payload, staging, `content.json` or archive mutation.
