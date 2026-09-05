# BG2 HD Upscale — user guide

## Status and requirements

The exact version and status are authoritative in
[`manifests/release.json`](manifests/release.json). The current build is a blocked local alpha.

- Steam BG2EE 2.7.3.0 on Windows x64;
- game, Steam, and InfinityLoader closed during install or restore;
- compatible EEex/InfinityLoader installed separately or through the guided official bootstrap;
- enough space for the payload and WeiDU backups.

Linux, Steam Deck, Proton, macOS, other stores, and unknown builds are unsupported. The package
does not redistribute the game, EEex, or InfinityLoader.

## Install

1. Verify the published archive SHA-256.
2. Extract its contents into the root containing `Baldur.exe`, `chitin.key`, and `WeiDU.log`, never
   into `override`.
3. Run `Install-BG2HD.exe`; follow the official EEex bootstrap when offered.
4. In WeiDU, select a language, mandatory Core, and the desired components.

The exact scope comes from `manifests/content.json` and `components.json`: validated x4 maps,
approved UI, selected overlays, and approved area-animation packs. Pending-QA maps, development
builds, backups, and captures are excluded.

Core installs the verified `Baldur.exe → InfinityLoader → BaldurReal.exe` path, renderer, and
save-neutral `M_IEEE.lua` guard. The guard prevents new vanilla-compatible save chains from
receiving EEex `X-BIV1.0` records; it does not repair old saves that already contain them.

## Launch, update, and remove

- Launch through Steam **Play** or the HD shortcut.
- To update, close the game, replace the archive source files, run `Install-BG2HD.exe`, and let
  WeiDU reinstall components.
- To remove, uninstall optional components in reverse order, then Core through
  `Uninstall-BG2HD.exe`.

The uninstaller either removes BG2HD while retaining EEex or performs a double-confirmed full
vanilla restore. Removing Core directly through `setup-bg2hd.exe` always retains EEex. Never copy
or rename executables manually; after Steam Verify, use the Repair flow in
[`docs/STEAM_INTEGRATION.md`](docs/STEAM_INTEGRATION.md).

For support, read [`docs/RECOVERY.md`](docs/RECOVERY.md) and
[`KNOWN_ISSUES.md`](KNOWN_ISSUES.md). Share only sanitized `WeiDU.log` and relevant renderer-log
excerpts.
