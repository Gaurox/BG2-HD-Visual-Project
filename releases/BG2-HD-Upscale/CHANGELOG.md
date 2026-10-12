# Changelog

## 0.1.0-alpha.7 — acquired Q3m sprites, local test package

- Replaces the historical 173-ID xBR catalogue with the acquired 331-ID,
  15-family Q3m x2 catalogue, using Nearest and mixed V6/V7/V9 leaves.
- Adds component 4210: 81 acquired P7 inventory packs, covering body 0x6110
  and 77 shared equipment resrefs. Other inventory bodies remain native.
- Component 4200 owns world sprite activation/filter; component 4210 owns
  paperdoll activation and disables its development probe. Each restores its
  own prior INI values, preserving unrelated settings.
- Preserves maps, animations, effects, native sources, renderer alpha.9 and
  pinned live shaders. Character SDF V10 remains an uninstalled reserve.
- Local tests only; combined clean-game/save/uninstall qualification and
  public contact/provenance conditions remain open. No new visual QA claimed.

## 0.1.0-alpha.6 — validated maps and area animations

- Consolidates all 399 packaged map variants in the explicit candidate register,
  with acquired QA and exact file inventories in `map-release-assemblies.json`.
- Replaces 63 legacy water assemblies with the final accepted decor, contours,
  WED and 188 dry/rain runtime identities; preserves the accepted AR3003 portal
  patch and the independent AR0516 animation WED contract.
- Activates `Shaders.EnableWaterOverlayRoute2=true` and
  `WaterOverlayStrength=1.00`, with exact prior INI restoration.
- Pins the final AR0413 oil stack accepted on September 28 (22 files), replacing
  the historical August-only contract. OH6460 continues to share OH8100.
- Preserves animation/sprite/effect payloads and renderer alpha.9 byte for byte.

- Packages the complete current animation composition of 234 areas, with exact
  runtime registries and immutable QA evidence for the 246 accepted BAM assets.
- Includes FIRE_3 at 30 FPS with a 4 px alpha fade, the accepted AR0205 pods and
  AR0604 fountain, restored AR3021 assets and the four AR5000 fish.
- Freezes the accepted current renderer as alpha.9, preserving SPHINCT world
  masks and the validated tree lighting/night corrections. Core activation now
  writes EnableAreaAnimationX4 in the Shaders section consumed by this renderer.
- Preserves existing QA decisions and resolves the historical alpha-catalogue
  hash through its committed snapshot.
- Preserves UTF-8 and UTF-16 INI encodings when activating renderer options.
- Builds local ZIP archives without compression until project finalization.
- Remains a local alpha: clean-game install, save and full-uninstall lifecycle
  tests and public provenance/contact records still gate public distribution.

## 0.1.0-alpha.4 — consolidated validated asset build

- Projects every approved area-animation candidate, including AR0411, AR2201,
  AR3011 and AR3021, from immutable QA evidence.
- Adds the approved SPMAGMIS, SPMINDAT and SPFEAREF x4 effect pack.
- Adds the playable-only 78-animation x2 creature catalogue with Catmull-Rom
  filtering; the unapproved 0xE400 family remains excluded.
- Packages the validated AR0046N, AR0204, AR0300N, AR0404, AR0900N, AR1000,
  AR1600, AR1607 and AR1800 water/WED corrections and their exact runtime aliases.
- Freezes renderer alpha.8 with the complete shader suite required by maps,
  effects and sprites. Automated install/rollback validation passes; clean-game
  lifecycle validation remains a publication blocker.

## 0.1.0-alpha.3 — in-place save-compatible test installer

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
- Selects the cache-safe AR2300 build for release: its PVRZ atlas was reduced
  from 122 to 93 pages and validated in game. The water-color mismatch remains
  a documented known issue.
- Restores the complete validated AR0413 result: canonical 16-page map build,
  12-sentinel TIS contour delta and a rebuilt renderer that classifies the
  stock `WTOIL` overlay as `Oil`. Packaging now rejects stale renderer DLLs
  that omit the required liquid classifiers.
- Pins AR0413 as a permanent 17-file packaging contract and consolidates local
  installer output under the neutral name `BG2HD-Installer-Windows.zip`.
- Packages the approved area-animation candidates with their pinned renderer,
  QA and runtime manifests.

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
