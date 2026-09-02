# Installer and upscale integration contract

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

Operational reference for agents. Manifests are authoritative.

Release authoring and gates require PowerShell 7 (`pwsh`); installer runtime helpers invoked by
WeiDU remain compatible with Windows PowerShell.

No test or release gate runs automatically. Before executing one, ask the user to choose targeted
tests, all tests, or no tests according to
[`../../../docs/TEST_SELECTION.md`](../../../docs/TEST_SELECTION.md). Refusal leaves the
corresponding validation unclaimed.

## Source of truth

| State | Authority |
|---|---|
| Version, target, blockers | `manifests/release.json` |
| Components | `manifests/components.json` |
| Payload files | generated `manifests/content.json` |
| Animation candidates | `manifests/animation-release-candidates.json` |
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

## Integrate validated content

QA and release are separate decisions. At the end of a task that produced a
`validated-installed` candidate, ask whether to integrate it. Without an
explicit affirmative answer, do not edit generator selections, regenerate `content.json`, stage or package. If the task
produced no eligible candidate, state that no integration is necessary.

After approval:

1. Pin the canonical source, unused permanent component ID, hashes and exact destination in the
   appropriate source manifest/generator.
2. Maps must match `areas.csv` and be x4 `validated-installed`; UI must declare its renderer keys
   and independent rollback state; overlays follow only `overlay-sources.json`.
3. Regenerate only the manifest tier. Ask the test choice separately, then run its static gate only
   if the corresponding test option was authorized:

```powershell
& .\tools\New-BG2HD-ContentManifest.ps1
& .\tools\New-BG2HD-ComponentManifest.ps1
& .\tools\Sync-BG2HD-PackageMetadata.ps1
& .\tools\Generate-BG2HD-Tp2.ps1
& .\tools\Test-BG2HD-Phase2.ps1
```

This tier must not build the full staging or archive.

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

The command validates decision, selection, pack, registry and run hashes; before writing, it
revalidates physically every candidate carried by the complete registry. It replaces only this
area's entries in the full content manifest and regenerates components/package mirrors/TP2
transactionally. It never stages or packages. `--test-delta` is allowed only after the separate
targeted-test choice.
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

After the test choice authorizes it, validate only the changed candidate:

```powershell
& .\tools\Test-BG2HDAreaAnimationCandidate.ps1 -Area ARxxxx
```

The gate constructs temporary area-scoped manifests/staging and verifies registry v2/v3,
TimedTimeline, frames, hashes, component and TP2. Run the global pilot only at package tier or after
a shared renderer/format/generator/Core change.

## Package tier

Requires separate authorization because it rebuilds staging and archives, plus the separate test
choice before its gates. Increment
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
