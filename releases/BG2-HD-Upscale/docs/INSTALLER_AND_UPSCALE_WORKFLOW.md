# Installer and upscale integration contract

Audience: implementation agents. This is the short operational reference; the
manifests are authoritative.

## Installer invariants

- Target: BG2EE Steam Windows x64 only; start normally from Steam after install.
- Runtime: Steam `Baldur.exe` shim -> `InfinityLoader.exe` -> `BaldurReal.exe`
  -> EEex -> BG2HD renderer. Only the transactional Core helper may publish or
  restore `Baldur.exe`/`BaldurReal.exe`; never manipulate them manually.
- Save neutrality: the exact renderer bundle must install `override/M_IEEE.lua`
  with `EEex_Debug_DisableExtraCreatureMarshalling = true`. Missing or changed
  guard bytes are a blocking error. Legacy saves remain detect-only.
- `Install-BG2HD.exe` checks/guides EEex, runs WeiDU, then creates the HD
  desktop shortcut. `Uninstall-BG2HD.exe` offers normal removal (retain EEex,
  Steam still launches) or explicitly confirmed full-vanilla removal.
- BG2HD never redistributes EEex or InfinityLoader. Compatibility is pinned by
  hashes; an unknown game build must fail closed.

## Add validated x4 content

1. Finish production QA. Accept only canonical x4 output; never package x2,
   live-game `override`, backups, captures or temporary files.
2. At the end of **every** content-production or validation task, ask the user:
   *"Task `<name>` is complete. Do you want me to integrate the elements validated by this task
   into the release manifest?"* This is a blocking, separate decision from the catalogue update.
   If the task has no `validated-installed` candidate, say so and integrate nothing; pending-QA
   output is never eligible. Without an explicit affirmative answer, do not edit `$mapSpecs`,
   regenerate `content.json`, stage files, or rebuild an archive. Record a refusal or deferral in
   the task report.
3. Only after that explicit approval, edit `tools/New-BG2HD-ContentManifest.ps1`: add the reviewed canonical
   source run with a permanent, unused component ID. Its CSV day/night status
   must be `validated-installed`; the generator fails if the CSV and declared
   variants disagree. Regenerate `components.json` with
   `New-BG2HD-ComponentManifest.ps1`; map labels use stable area-code literals
   in WeiDU, while Core/UI remain translated through the TRA files.
4. For a UI component, declare the required renderer configuration and a
   dedicated state file in the TP2 generator. Do not share or overwrite the
   Core configuration backup. The selector depends on the main-menu component.
5. For a manifest integration that does not build an archive, regenerate only
from the release root, then run the static gate. For an area-animation
candidate, run its delta gate; it stages only that immutable area pack. Do not
stage the full payload or run Phase 4 for this tier.

```powershell
& .\tools\New-BG2HD-ContentManifest.ps1
& .\tools\New-BG2HD-ComponentManifest.ps1
& .\tools\Sync-BG2HD-PackageMetadata.ps1
& .\tools\Generate-BG2HD-Tp2.ps1
& .\tools\Test-BG2HD-Phase2.ps1
```

For an area-animation candidate, add:

```powershell
& .\tools\Test-BG2HDAreaAnimationCandidate.ps1 -Area ARxxxx
```

6. Before a user-facing package update, or after a runtime, format,
generator or Core change, increment `manifests/release.json`, sync metadata
again, regenerate TP2, then rebuild the full payload and validate the update
and archive:

```powershell
& .\tools\Stage-BG2HDPayload.ps1
& .\tools\Test-BG2HD-Phase4.ps1
& .\tools\Test-BG2HD-AreaAnimationPilot.ps1
& .\tools\Test-BG2HD-Phase5A.ps1 -WeiDUExecutable <Weidu.exe> -ArchivePath <previous.zip>
& .\tools\Build-BG2HD-LocalReproducible.ps1 -WeiDUExecutable <Weidu.exe> -OutputRoot <empty-output>
& .\tools\Test-BG2HD-Phase6BPackage.ps1 -ArchivePath <new.zip>
```

## Add validated area animations

Area animations are a distinct content type. They are never copied from the
live game, a backup, or an entire combined-pack directory. One WeiDU component
owns one area and copies only the immutable pack manifest, registry and RGBA
frames declared for that area to `iee-assets/areas/<AREA>/`.

1. Register a reviewed pack in `manifests/animation-release-candidates.json`.
   It pins the canonical directory, pack-manifest hash, registry hash, exact
   resrefs, component ID and renderer contract. Use the first free animation
   ID (3000 and above); never reuse a published ID.
2. A candidate remains `validated-awaiting-manifest-approval` until the user
   explicitly approves its inclusion. `New-BG2HD-ContentManifest.ps1` excludes
   it from the release manifest by default. The opt-in pending mode exists
   only for isolated pilot validation.
3. The generator verifies every listed frame against the pack manifest and
   against `animations/index/animation_upscale_registry.csv`; all resrefs must
   be `validé-x4` and belong to the component's exact area. It rejects unknown
   files, a registry outside v2/v3, an incomplete pack and all forbidden source paths.
4. Every animation component depends on Core. Core owns
   `EnableAreaAnimationX4=true`, transactionally restored on Core uninstall.
   Promote an area pack only with a renderer candidate whose binary is pinned
   and has passed the per-area registry-v2/v3 / TimedTimeline contract.
   After explicit approval, run `Promote-BG2HDAreaAnimationRenderer.ps1` before
   regenerating the release manifests and payload.
5. At task scope, run `Test-BG2HDAreaAnimationCandidate.ps1 -Area ARxxxx`;
it checks only the newly approved pack. Run
`Test-BG2HD-AreaAnimationPilot.ps1`, the renderer host tests and the normal
Phase 2/4/5A/6B gates only at the package tier, or immediately after a shared
runtime/format/generator/Core change. Runtime QA must enter the packaged area
and a following area without a pack; the latter must release the resident pack
and use the native BAM fallback.

AR0603 (component 3004, v2) is the backward-compatibility pilot. AR0602 (component 3000, v3)
proves the v2-to-v3 transition, and AR0900 (component 3001, v3) remains the per-occurrence pilot.
The previous `iee-0.1.0-alpha.5` manifest is rejected: four tracked auxiliary files no longer
match its frozen inventory, so neither that bundle nor the existing local payload is a valid
release source. The exact current bytes are preserved as the new `iee-0.1.0-alpha.6` candidate;
its clean-game and lifecycle gates remain required before promotion or any public release.

Build twice in separate output directories; SHA-256 must match. Promote only
the verified archive to `BG2HD-Installer-Windows-Local-Test.zip`, with its
matching `.sha256` file. Do not publish while `release_status` is `blocked`.

## Source of truth

- Package definition: `manifests/*.json`.
- Generated files: `bg2hd/manifests/*`, `bg2hd/bg2hd.tp2`, and staged payload;
  never hand-edit them.
- Deeper rules: `docs/MANIFESTS.md`, `docs/MAINTENANCE.md`,
  `docs/LOCALIZATION.md`, and `docs/TESTING.md`.
