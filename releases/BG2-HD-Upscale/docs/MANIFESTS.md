# Manifests and validation

For the implementation sequence that changes these manifests, use the
[installer and upscale integration contract](INSTALLER_AND_UPSCALE_WORKFLOW.md).

The release manifests are the only authority for a package. `areas.csv` is a
production catalogue and the development `override` is a test environment;
neither is a release source.

| File | Purpose |
|---|---|
| `release.json` | version, target platform, release status and package scope |
| `runtime-compatibility.json` | accepted game/EEex/loader hashes, Steam shim and future-save contracts |
| `dependency-bootstrap.json` | pinned EEex installer, dependency states, ownership and bootstrap order |
| `components.json` | permanent component IDs, labels and dependencies |
| `content.json` | source, destination, component, byte count and SHA-256 per payload file |
| `animation-release-candidates.json` | approved per-area v2/v3 animation packs and renderer contract |
| `overlay-sources.json` | authoritative stock/x2/x4 decision and hashes for shared liquid resrefs |
| `renderer-bundle.json` | frozen renderer candidate inventory |
| `licenses-and-exclusions.json` | provenance status and forbidden payload classes |

Every content entry must have a canonical source, normalized destination,
component ID, install order, byte count, SHA-256 and approved QA status. A
destination collision is accepted only when explicitly ordered and validated.

`areas.csv` is the inclusion register for maps. For every `validated-installed`
day/night variant, `New-BG2HD-ContentManifest.ps1` requires exactly one
reviewed source run. It refuses both missing validated variants and stale
manifest variants. `New-BG2HD-ComponentManifest.ps1` then derives the matching
map components from the content manifest.

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
`Generate-BG2HD-Tp2.ps1` emits explicit `COPY_LARGE` operations. Run the
validation scripts after any regeneration; do not hand-edit generated payload
lists or select files from a live game installation.

`dependency-bootstrap.json` is a contract, not an embedded EEex payload. It
records the only accepted official archive and the no-write actions for every
EEex state. `Test-BG2HD-DependencyContract.ps1` validates it and can also
verify a supplied official EEex archive by SHA-256.

`steam_launch_contract` describes the in-place `Baldur.exe` shim and verified
full restoration. `save_compatibility_contract` pins the save-neutral scope,
guard path, forbidden `X-BIV1.0` signature and mandatory native-vanilla gate.
