# Compatibility

| Item | Supported scope |
|---|---|
| Game | BG2EE Steam 2.7.3.0 |
| Platform | Windows x64 |
| Steam app | 257350 |
| Runtime | exact hashes in `runtime-compatibility.json` |
| Launch | Steam Play or BG2HD shortcut |
| Content | exact entries in `content.json`, overlays in `overlay-sources.json` |
| Animations | approved entries in `animation-release-candidates.json` |

Unsupported: other stores/builds/platforms, manual executable layouts, missing/changed EEex,
x2-only maps, HUD, pending-QA content and development payloads.

Compatibility is exact, not best-effort. A Steam update requires a new offline and runtime
validation before its identity can enter the manifest.

Map inclusion requires the exact `areas.csv` run/build selected by the generator. Animation
inclusion requires the exact per-area pack, QA snapshot and renderer contract. No list is duplicated
here.

The save-neutral contract applies to new save chains derived from a vanilla-compatible state after
installation of the guard. Existing saves containing `X-BIV1.0` are detected but not rewritten.
