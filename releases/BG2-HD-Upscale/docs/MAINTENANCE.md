# Maintenance workflow

Start with the [installer and upscale integration contract](INSTALLER_AND_UPSCALE_WORKFLOW.md)
for the required edit order and installer invariants. This document expands its
maintenance and release gates.

## Adding or changing content

1. Complete the area/UI QA in its production run. Do not publish a pending-QA
   build or an x2 comparison asset by accident.
2. Close every content task by asking the user whether the elements validated
   by that task should be integrated into the release manifest. This is a
   separate, blocking choice: absent an explicit affirmative answer, do not
   change `$mapSpecs`, regenerate `content.json`, stage a payload or rebuild an
   archive. Say explicitly when there is no `validated-installed` candidate;
   pending-QA content remains ineligible. Record a refusal or deferral in the
   task report.
3. After approval, add one explicit canonical source to the content-manifest register and keep
   the component ID/label stable. A previously published ID is never reused.
4. Regenerate, stage and validate from the release root:

```powershell
& .\tools\New-BG2HD-ContentManifest.ps1
& .\tools\New-BG2HD-ComponentManifest.ps1
& .\tools\Sync-BG2HD-PackageMetadata.ps1
& .\tools\Generate-BG2HD-Tp2.ps1
& .\tools\Stage-BG2HDPayload.ps1
& .\tools\Test-BG2HD-Phase2.ps1
& .\tools\Test-BG2HD-Phase4.ps1
```

5. Run the Phase 5A suite, then build and validate a fresh archive. Test the
resulting archive, not the source tree. Record its size and SHA-256.

```powershell
& .\tools\Build-BG2HD-LocalReproducible.ps1 -WeiDUExecutable <path-to-Weidu.exe>
& .\tools\Test-BG2HD-Phase6BPackage.ps1 -ArchivePath <path-to-release.zip>
```

The local reproducible builder deliberately requires `release_status: blocked`.
It is a pre-publication artifact generator, not a publish command.

### Area-animation exception

Use the area-animation candidate register instead of adding runtime frames by
hand. One `area-animation` component maps to one `iee-assets/areas/<AREA>`
directory and depends on Core. A candidate must stay out of `content.json`
until explicit user approval; validate it with
`Test-BG2HD-AreaAnimationPilot.ps1` and a renderer built from the same source
tree before promotion. The clean-game AR0602 -> no-pack-area fallback remains
a required runtime gate.

## Core or compatibility changes

Any game, EEex, loader, helper or renderer change requires a new compatibility
record, rollback tests and graphical gates. Unknown game builds stay refused.
Do not weaken a hash check to make an installation pass.

The frozen renderer DLL must contain the `WTSEW` and `WTOIL` classifiers.
AR0413 is a two-part contract: its canonical 16 PVRZ pages plus 12-sentinel
TIS delta are necessary, but the result is incomplete unless the runtime log
reports overlay 1 as `Oil` (`liquidOverlayMask=0x02`). The freeze, Phase 4 and
test-package gates reject a stale DLL that lacks these classifiers.

`Test-BG2HD-AR0413Contract.ps1` pins the complete AR0413 result independently
of the generated content manifest: canonical run, component 1300, exact sizes
and SHA-256 for all 16 PVRZ pages and the corrected TIS, absence of rejected
page `A041316.PVRZ`, and the `WTOIL` marker in the renderer DLL. Every current
installer build and archive validation must pass this contract. Build the
neutral Windows artifact with:

```powershell
& .\tools\Build-BG2HD-Installer.ps1
```

The line `EEex_Debug_DisableExtraCreatureMarshalling = true` in the bundled
`M_IEEE.lua` is a compatibility invariant, not an optional debug preference.
Any change to that file requires a renderer-manifest refresh, the automated
future-save contract test and a native HD -> full uninstall -> vanilla cycle.

For an EEex release change, update `dependency-bootstrap.json` only after
validating its official archive, complete runtime file set, WeiDU components,
Steam lifecycle and renderer launch. Then run:

```powershell
& .\tools\Test-BG2HD-DependencyContract.ps1 -EEexInstallerPath <official-EEex-installer.exe>
```

Do not add EEex or InfinityLoader to the BG2HD payload without explicit
redistribution permission from its author.

## Release hygiene

Keep source assets, generated archive, test evidence and user state separate.
Never include executables from the game, Steam files, EEex/InfinityLoader,
backups, captures, logs, x2 assets or unapproved source material in a release.
Before public packaging, update the changelog, licenses, checksums and user
documentation in the same change.
