# Manifests and validation

This document applies during explicit finalization. Daily asset work follows
[`../../../docs/PRODUCTION_RAPIDE.md`](../../../docs/PRODUCTION_RAPIDE.md).

The compiled release manifests are the only authority for a package. Candidate registries are the
small daily-write authorities; `areas.csv` is a production catalogue and the development
`override` is a test environment.

| File | Purpose |
|---|---|
| `release.json` | version, target platform, release status and package scope |
| `runtime-compatibility.json` | accepted game/EEex/loader hashes, Steam shim and future-save contracts |
| `dependency-bootstrap.json` | pinned EEex installer, dependency states, ownership and bootstrap order |
| `components.json` | permanent component IDs, labels and dependencies |
| `content.json` | source, destination, component, byte count and SHA-256 per payload file |
| `map-release-candidates.csv` | accepted map variants and selected source directories |
| `map-release-assemblies.json` | exact acquired QA, source-layer provenance, final water stacks and runtime guards |
| `animation-release-candidates.json` | approved per-area v2/v3 animation packs and renderer contract |
| `effect-release-candidates.json` | approved shared x4/30 FPS effect packs, QA and renderer contract |
| `sprite-release-candidates.json` | v2 acquired flat Q3m world/UI selection, exact inventories, immutable family QA and pinned renderer |
| `sprite-inventories/*.json` | exact Q3m world catalogue/leaves and scoped P7 paperdoll files, sizes and SHA-256 |
| `overlay-sources.json` | authoritative stock/x2/x4 decision and hashes for shared liquid resrefs |
| `renderer-bundle.json` | frozen renderer candidate inventory |
| `licenses-and-exclusions.json` | provenance status and forbidden payload classes |

During finalization, every content entry must have a canonical source, normalized destination,
component ID, install order, byte count, SHA-256 and approved QA status. A destination collision is
accepted only when explicitly ordered and validated.

Sprite component 4200 selects 331 acquired world IDs (V6/V7/V9, x2 Nearest).
Component 4210 selects 81 V6 P7 paperdolls (0x6110 body plus 77 equipment packs).
The verifier checks physical files against the sealed catalog and acquired QA.
Projection into `content.json` remains separate from clean-game qualification
and public publication. Configuration owners restore only their own INI keys.

`map-release-candidates.csv` selects all 399 variants; the historical compiler bootstrap has been
migrated into data without changing component IDs. `catalog_source_path` preserves the acquired
decor run in `areas.csv`; `source_path` may identify its exact frozen final assembly.
`map-release-assemblies.json` pins every file and existing QA; 63 liquid WEDs include local dry/rain
overlay TIS/PVRZ in the same map component. `verify_map_release_candidates.py` rejects missing
layers, changed QA/bytes, wrong catalog runs, runtime guard mismatches and incomplete projections.
The installed game is a read-only continuity witness; all packaged files come from retained sources.

Une animation dont `occlusion_contract.mode` vaut `native-wed-bridge-v1` impose simultanément :

- le WED versionné et hashé sous `maps/wed-corrections/` dans le composant map déclaré ;
- la dépendance du composant animation vers ce composant map ;
- `Shaders.EnableNativeOcclusionBridge=true` possédé par `core-steam` ;
- un bundle renderer contenant `EnableNativeOcclusionBridge` et `FXRenderClippingPolys`.

AR0516 est le témoin initial ; l'alpha.6 locale conserve son rattachement QA acquis et son WED exact.
La publication reste bloquée par les essais de cycle complet sur jeu propre.

`New-BG2HD-ContentManifest.ps1` accepts the fixed x4 source register, plus only the overlays
declared as `package` by `overlay-sources.json`; `stock` entries are forbidden from the payload.
Shared overlay selections remain governed independently; local final water overlays are x4 and
travel with their map. Core owns `Shaders.EnableWaterOverlayRoute2=true` and
`WaterOverlayStrength=1.00`, the configuration used for the final acquired review.
`Stage-BG2HDPayload.ps1` copies from that manifest and
rechecks hashes; x2 is rejected for every other content kind.
`Generate-BG2HD-Tp2.ps1` emits explicit `COPY_LARGE` operations. These global projections are
compiled together by `Compile-BG2HD-Release.ps1`; do not hand-edit generated payload lists or
select files from a live game installation.

`dependency-bootstrap.json` is a contract, not an embedded EEex payload. It
records the only accepted official archive and the no-write actions for every
EEex state. `Test-BG2HD-DependencyContract.ps1` validates it and can also
verify a supplied official EEex archive by SHA-256.

`steam_launch_contract` describes the in-place `Baldur.exe` shim and verified
full restoration. `save_compatibility_contract` pins the save-neutral scope,
guard path, forbidden `X-BIV1.0` signature and mandatory native-vanilla gate.
