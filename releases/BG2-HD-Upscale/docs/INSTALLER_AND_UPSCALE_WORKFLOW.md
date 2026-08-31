# Installer and upscale integration contract

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

Operational reference for agents. Manifests are authoritative.

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
3. Regenerate only the manifest tier and run its static gate:

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
`qa-approval.json`, manifest/registry hashes, resrefs and renderer contract in
`animation-release-candidates.json`. The `approval_status` field is authoritative; do not infer it
from the pack or live game.

Validate only the changed candidate:

```powershell
& .\tools\Test-BG2HDAreaAnimationCandidate.ps1 -Area ARxxxx
```

The gate constructs temporary area-scoped manifests/staging and verifies registry v2/v3,
TimedTimeline, frames, hashes, component and TP2. Run the global pilot only at package tier or after
a shared renderer/format/generator/Core change.

## Package tier

Requires separate authorization because it rebuilds staging and archives. Increment
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
