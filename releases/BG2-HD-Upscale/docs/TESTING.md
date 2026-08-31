# Testing and evidence

Use the [installer and upscale integration contract](INSTALLER_AND_UPSCALE_WORKFLOW.md)
to determine the required regeneration path before applying these gates.

Never execute a gate automatically. Ask the user to choose targeted tests, all tests, or no tests
as defined in [`../../../docs/TEST_SELECTION.md`](../../../docs/TEST_SELECTION.md). “Required” below
means required evidence for claiming the corresponding validation tier; if tests are declined, stop
before that claim and report the missing evidence.

## Validation tiers

After authorization, use the smallest gate that proves the change, then retain the complete package
gate before any distributable archive. A fast gate is not a release waiver.

| Tier | Trigger | Required proof |
|---|---|---|
| Animation delta | Each approved area-animation candidate | `Test-BG2HDAreaAnimationCandidate.ps1 -Area ARxxxx`: candidate manifest/registry/index, exact frames and hashes, temporary per-area staging, generated component and TP2 entries |
| Manifest integration | Each explicitly approved content integration | Regenerate manifests and TP2, then run Phase 2 static validation |
| Package | Before building, updating or validating an archive; also after a shared generator, runtime, format or Core change | Full staging, Phase 4, animation compatibility pilots, Phase 5A and Phase 6B |

The animation-delta gate creates its own temporary `content.json` and payload;
it must never use or replace `bg2hd/payload-allvalidated`. It validates only
the declared immutable area pack, so it replaces neither the full payload gate
nor clean-game runtime QA. Run the package tier immediately when a shared
contract changes or when preparing an archive.

## Required automated checks

After payload or Core changes, run the manifest/TP2 checks, asset validator,
helper lifecycle matrix, fault-injection rollback tests, WeiDU update test,
archive install/uninstall test and EEex-to-vanilla test. The Phase 5A wrapper
records this suite:

The static payload gate also proves that every `validated-installed` CSV map
variant is present and that no undeclared map file survives in the staged
payload.
It separately executes `Test-BG2HD-AR0413Contract.ps1`; changing AR0413 or its
renderer classification requires an explicit, reviewed update of the pinned
17-file contract after a new in-game validation.

```powershell
& .\tools\Test-BG2HD-Phase5A.ps1 `
  -WeiDUExecutable <path-to-Weidu.exe> `
  -ArchivePath <path-to-release.zip>
```

## Required manual checks

On an otherwise clean, supported Steam install with the external prerequisite:

- launch via Steam and via the BG2HD desktop shortcut;
- confirm that the x4 main-menu and game-selector components both install their
  renderer keys (`EnableBigLogoX4Test` and `EnableMainMenuX4Test`) as well as
  their declared atlas files;
- verify one vanilla area delegates normally and every selected x4 group keeps
  64x64 world geometry while sampling HD pages;
- inspect water, masks, tint, scrolling/zoom, doors, transitions, resize/full
  screen, save/load and clean shutdown;
- entrer dans AR0516 avec le bridge activé ; vérifier `SPHINCT`, `SPHINCT2` et le polygone WED
  local du SPHINCT inférieur, puis exiger les traces `bridge prepared`, hook
  `FXRenderClippingPolys` et `bridge active` ;
- enter AR0413 and require the renderer log to classify its stock `WTOIL`
  overlay as `Oil`, with `liquidOverlayMask=0x02`; visually confirm animated
  oil on the 283 released base cells and no black gaps at the 12 corrected
  sentinel contours;
- create a new HD save chain, scan both GAM/SAV for zero `X-BIV1.0`, perform
  the full vanilla uninstall, then load, save and reload it in native vanilla;
- Steam Verify followed by Repair; Core reinstall; normal Core removal (Steam
  launch retained); and confirmed full-vanilla removal through
  `Uninstall-BG2HD.exe`;
- after full-vanilla removal, verify that normal WeiDU EEex source residues are
  classified `inactive`, that reinstall is offered, and that a mixed runtime
  residue is still rejected as `partial`;
- preserve the old renderer journals while removing
  `InfinityEngine-Enhancer.ini`, then verify that a second Core + main-menu
  cycle recreates the INI, starts a fresh transaction and rolls back twice
  without a secondary missing-file exception;
- check logs for manifest selection, successful hooks, renderer errors/retries,
  failed uploads and recurring configuration warnings.

Evidence must name archive hash, game hash/version, EEex/loader hashes, selected
components, test date and result. Do not commit raw local logs or screenshots
with personal information.

The exact player protocol is in
[TEST_SAVE_COMPATIBILITY_FR.md](TEST_SAVE_COMPATIBILITY_FR.md).

## Reproducible-package gate

`Build-BG2HD-LocalReproducible.ps1` packages only the staged WeiDU mod and the
public documentation. It fixes ZIP timestamps, orders entries, writes an
in-package SHA-256 inventory and emits an archive `.sha256` sidecar.
`Test-BG2HD-Phase6BPackage.ps1` validates that inventory, the public-document
set, exclusions and fixed timestamp contract. Build twice in distinct output
directories and require identical archive hashes before promoting a candidate.
