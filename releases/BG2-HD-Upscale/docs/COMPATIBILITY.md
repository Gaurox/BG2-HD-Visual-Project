# Compatibility

| Item | Supported alpha scope |
|---|---|
| Game | Baldur's Gate II: Enhanced Edition Steam 2.7.3.0 |
| Platform | Windows x64 |
| Steam app ID | 257350 |
| Loader | external EEex / InfinityLoader with the hashes in `runtime-compatibility.json` |
| Launch | normal Steam Play and BG2HD desktop shortcut |
| Future saves | HD -> confirmed full uninstall -> native vanilla load/save/reload; no `X-BIV1.0` |
| Content | maps/UI de `content.json`, overlays de `overlay-sources.json`, animations AR0603 v2, AR0602 v3 et AR0900 v3 |

Not supported: Linux, macOS, Steam Deck, Proton, other stores, unknown game
patches, missing/changed EEex, manual executable layouts, x2-only payloads,
HUD assets and maps marked pending QA.

Compatibility is exact, not best-effort. A Steam update must receive a new
offline/runtime validation before its hash can be admitted.

The map inclusion contract is exact: every validated day/night CSV row must resolve to the same
reviewed run/build as the release generator, and every payload file is pinned by size and SHA-256.
A new validated map therefore needs an explicit reviewed canonical source before it can be
packaged.

The future-save contract starts from a vanilla-compatible save chain after the
save-neutral guard was installed. Existing saves already written with EEex
extended marshalling are outside that contract and are not rewritten.
