# Installer and upscale integration contract

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

Finalization reference. Daily production follows
[`../../../docs/PRODUCTION_RAPIDE.md`](../../../docs/PRODUCTION_RAPIDE.md).

Release authoring and gates require PowerShell 7 (`pwsh`); installer runtime helpers invoked by
WeiDU remain compatible with Windows PowerShell.

Release gates run only when finalization or the corresponding validation is explicitly requested.

## Source of truth

| State | Authority |
|---|---|
| Version, target, blockers | `manifests/release.json` |
| Components | `manifests/components.json` |
| Payload files | generated `manifests/content.json` |
| Map candidates | `manifests/map-release-candidates.csv` |
| Animation candidates | `manifests/animation-release-candidates.json` |
| Effect candidates | `manifests/effect-release-candidates.json` |
| Sprite candidates | `manifests/sprite-release-candidates.json` |
| Shared overlays | `manifests/overlay-sources.json` |
| Runtime/bootstrap | `runtime-compatibility.json`, `dependency-bootstrap.json`, `renderer-bundle.json` |
| Rights/exclusions | `licenses-and-exclusions.json` |

Generated TP2, package manifests, staging and archives are never hand-edited.

## Installer invariants

- BG2EE Steam 2.7.3.0, Windows x64 only; unknown hashes fail closed.
- Only the transactional Core helper publishes/restores `Baldur.exe` and `BaldurReal.exe`.
- The renderer bundle must include the exact save-neutral `override/M_IEEE.lua`.
- BG2HD does not redistribute EEex or InfinityLoader.
- Normal uninstall retains EEex; full vanilla removal requires explicit confirmation.

## Accept validated content

QA, candidate acceptance and package compilation are separate decisions. Daily work records only
the accepted candidate. It does not edit global generator selections, regenerate `content.json`,
stage or package.

For a map accepted by the user:

Add one row to `manifests/map-release-candidates.csv` with `area`, permanent `component_id`, selected
`source_path`, `include_wed` and `model`. This performs no command, hash or projection. Other domains
write their own candidate authority. Global compilation is deferred.

## Compile accepted candidates

Only during explicit finalization, compile all accepted candidate authorities in one operation:

```powershell
& .\tools\Compile-BG2HD-Release.ps1
& .\tools\Test-BG2HD-Phase2.ps1
```

Compilation is an explicit mutating action. The second command is an independent final gate. This
tier does not build the full staging or archive.

## Renderer prerequisite

An asset candidate relying on a renderer fix must not be integrated against a rejected or
different bundled DLL. Stage the exact fifteen-file `iee-0.1.0-alpha.8` candidate from a source
`release-bundle`, with a `git:<commit>:<source-root>` provenance value, then validate it before
promotion. The promotion must atomically replace `bg2hd/renderer` and both copies of
`renderer-bundle.json`; `runtime-compatibility.json` must pin the same DLL hash/bytes. Keep the
release blocked until the clean-game and lifecycle gates are recorded.

For the AR2300 multi-cycle TimedTimeline fix, the candidate gate must cover
`resolve_timeline_subframe` and the host regression before the area candidate is integrated.

## Area-animation candidate

One component owns one immutable per-area pack. Register its component, exact source pack,
versioned area QA, manifest/registry hashes, direct final runs, carried byte-identical resources,
resrefs and renderer contract in `animation-release-candidates.json` and its QA approval. The
`approval_status` field is authoritative; do not infer it from the pack or live game.

For new QA, do not hand-edit the candidate. Run `animation_workflow.py finalize` for every changed
resref, then plan and apply the scoped transaction:

```powershell
python pipeline/scripts/animation_release.py --area ARxxxx --approve
python pipeline/scripts/animation_release.py --area ARxxxx --approve --run
```

The command validates the changed decision, selection, pack, registry and run hashes. By default it
writes only the area QA and candidate authority; it does not inspect every other candidate or
regenerate global projections. Compilation and focused diagnostics are separate explicit commands.
Finalization and promotion share one advisory lock. A durable ignored journal restores every
published manifest before a retry if the preceding process stopped mid-transaction.
Manifest generators, validators, staging and package builders hold the same lock for their full
execution and fail closed while either recovery journal exists. Phase 2 requires byte-identical
package mirrors and an exact pack-to-`content.json` animation projection.
An interrupted `Sync-BG2HD-PackageMetadata.ps1` keeps
`bg2hd/manifests/.package-metadata-sync.partial`; rerun that script to replace and revalidate all
mirrors. Every other release command refuses the marker.
Unchanged resrefs may reuse the current approved area QA only when the old and new runtime resource
groups and their physical assets are byte-identical under the same registry/runtime/renderer
contract. The immutable QA v3 records that carry-forward explicitly; any mismatch requires a new
ingame decision. Legacy candidates and approvals remain readable and are not rewritten.

Si un candidat déclare `occlusion_contract`, la prépublication vérifie la spécification, le WED, la
preuve QA, leurs hashes et leur rattachement à la zone. Le manifeste final doit sélectionner ce WED
exact, exposer le composant map attendu et ajouter sa dépendance au composant animation. Le Core doit
posséder l'activation du bridge ; aucun bundle antérieur aux marqueurs
`EnableNativeOcclusionBridge` et `FXRenderClippingPolys` n'est promouvable.

When a focused diagnostic is requested, validate only the changed candidate:

```powershell
& .\tools\Test-BG2HDAreaAnimationCandidate.ps1 -Area ARxxxx
```

The gate constructs temporary area-scoped manifests/staging and verifies registry v2/v3,
TimedTimeline, frames, hashes, component and TP2. Run the global pilot only at package tier or after
a shared renderer/format/generator/Core change.

## Package tier

This finalization step rebuilds staging and archives. Increment
`release.json` when the user-facing package changes, sync metadata, then run:

```powershell
& .\tools\Stage-BG2HDPayload.ps1
& .\tools\Test-BG2HD-Phase4.ps1
& .\tools\Test-BG2HD-AreaAnimationPilot.ps1
& .\tools\Test-BG2HD-Phase5A.ps1 `
  -WeiDUExecutable <Weidu.exe> -ArchivePath <previous.zip>
& .\tools\Build-BG2HD-LocalReproducible.ps1 `
  -WeiDUExecutable <Weidu.exe> -OutputRoot <empty-output>
& .\tools\Test-BG2HD-Phase6BPackage.ps1 -ArchivePath <new.zip>
```

Build twice in distinct empty directories and require identical archive SHA-256. Do not publish
while `release_status` is `blocked` or `payload_status` is not buildable.

Detailed manifest and gate semantics: [`MANIFESTS.md`](MANIFESTS.md),
[`TESTING.md`](TESTING.md), [`LOCALIZATION.md`](LOCALIZATION.md).
