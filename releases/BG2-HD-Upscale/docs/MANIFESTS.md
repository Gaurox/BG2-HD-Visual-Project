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
| `animation-release-candidates.json` | approved per-area v2/v3 animation packs and renderer contract |
| `effect-release-candidates.json` | approved shared x4/30 FPS effect packs, QA and renderer contract |
| `sprite-release-candidates.json` | approved sprite scope, sealed generation, QA and runtime contract |
| `overlay-sources.json` | authoritative stock/x2/x4 decision and hashes for shared liquid resrefs |
| `renderer-bundle.json` | frozen renderer candidate inventory |
| `licenses-and-exclusions.json` | provenance status and forbidden payload classes |

During finalization, every content entry must have a canonical source, normalized destination,
component ID, install order, byte count, SHA-256 and approved QA status. A destination collision is
accepted only when explicitly ordered and validated.

Sprite candidates remain `approved`, not `integrated`, until a scoped catalogue excludes every
unapproved animation and its files are projected into `content.json`.

`map-release-candidates.csv` is the inclusion register for newly accepted maps. Adding a row performs
no scan or hash. Historical map specifications embedded in `New-BG2HD-ContentManifest.ps1` are a
compatibility bootstrap only. During finalization, the generator combines both sources and computes
the final inventory; `New-BG2HD-ComponentManifest.ps1` derives the matching components.

Une animation dont `occlusion_contract.mode` vaut `native-wed-bridge-v1` impose simultanément :

- le WED versionné et hashé sous `maps/wed-corrections/` dans le composant map déclaré ;
- la dépendance du composant animation vers ce composant map ;
- `Shaders.EnableNativeOcclusionBridge=true` possédé par `core-steam` ;
- un bundle renderer contenant `EnableNativeOcclusionBridge` et `FXRenderClippingPolys`.

AR0516 est le témoin initial. Alpha.5 et alpha.6 précèdent ce contrat et restent non promouvables.

`New-BG2HD-ContentManifest.ps1` accepts the fixed x4 source register, plus only the overlays
declared as `package` by `overlay-sources.json`; `stock` entries are forbidden from the payload.
The current policy keeps the validated water set x2 and the lava family x4.
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
