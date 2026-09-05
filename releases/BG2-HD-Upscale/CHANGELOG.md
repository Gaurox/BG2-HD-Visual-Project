# Changelog

## Unreleased — in-place save-compatible test installer

- Restored the single-installation design: BG2HD transforms the supported
  Steam game in place and Steam launches HD through the verified
  InfinityLoader shim.
- Preserves the official executable as `BaldurReal.exe`; the confirmed full
  uninstall restores verified vanilla `Baldur.exe` and removes the shim layout.
- Recognizes the normal EEex WeiDU source residue after a full vanilla restore
  as inactive and offers a clean official reinstall on the next BG2HD run.
- Starts a fresh Core transaction on reinstall and revalidates/recreates the
  renderer INI instead of trusting state journals left by the previous cycle.
- Makes renderer configuration rollback idempotent when the INI was already
  removed, preventing a secondary error from masking the original failure.
- Makes the future-save compatibility guard a blocking install invariant:
  EEex extended creature marshalling is disabled before renderer startup, so
  new save chains do not receive `X-BIV1.0` records.
- Keeps legacy saves detect-only; no automatic migration is attempted.
- Regenerates the map package from `areas.csv`: every currently validated day/night variant is
  represented. Exact scope is recorded in `manifests/content.json`.
- Restores the complete validated AR0413 result: canonical 16-page map build,
  12-sentinel TIS contour delta and a rebuilt renderer that classifies the
  stock `WTOIL` overlay as `Oil`. Packaging now rejects stale renderer DLLs
  that omit the required liquid classifiers.
- Pins AR0413 as a permanent 17-file packaging contract and consolidates local
  installer output under the neutral name `BG2HD-Installer-Windows.zip`.

## 0.1.0-alpha.2 — local corrective build

- Added explicit `Uninstall-BG2HD.exe` choices: safe BG2HD-only removal that
  preserves EEex Steam launching, or a double-confirmed full-vanilla return.
- Added provenance warnings for pre-existing/unknown EEex and a French WeiDU
  language workaround that restores `weidu.conf` exactly after EEex removal.
- Fixed the x4 game-selector archive: the x4 main-menu component now enables
  its renderer keys, keeps a separate rollback state, and restores the exact
  prior configuration when removed.

## 0.1.0-alpha.1 — local validation build

- Added the WeiDU package `bg2hd`, with stable Core/UI/map component IDs.
- Added x4 UI assets and the validated SeedVR2 7B x4 map scope: AR0300,
  AR0400, AR0500, AR0602, AR0603, AR0700 and AR0703.
- Added transactional Steam launch integration, desktop shortcut creation,
  Steam Verify repair handling and conservative uninstallation.
- Added deterministic manifests, asset-format validation and lifecycle tests.
- Completed the local Steam/renderer graphical validation (Phase 5B).

### Not included

All x2 maps and overlays (including AR0800, AR0900, AR1000, WTLAKE and
WTPOOL), HUD assets, pending-QA maps, game executables, EEex, InfinityLoader,
development backups and captures.

### Release status

This is an internal local alpha. Public distribution is blocked pending rights
review and a separate clean-install end-to-end test.
