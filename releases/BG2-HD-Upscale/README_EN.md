# Baldur's Gate II: Enhanced Edition HD Upscale — user guide

## Status

`0.1.0-alpha.2` is a locally tested Windows alpha, not a public release. Do
not redistribute its archive until the licensing and provenance gate has been
cleared.

## Requirements

- Steam BG2EE 2.7.3.0 on 64-bit Windows;
- compatible EEex/InfinityLoader already installed, or Internet access / the
  official EEex 1.2.0 archive for the guided flow;
- Steam, the game and the loader closed while installing;
- free disk space for roughly 1.1 GB of payload plus WeiDU backups.

Linux, Steam Deck, Proton, macOS, other stores and unknown Steam builds are not
supported. The package does not redistribute the game, EEex or InfinityLoader.
The BG2HD renderer is included in this local alpha, but still needs its clean
installation lifecycle test before any public distribution.

The adopted policy for a future public alpha is free and non-commercial: it
requires a legitimate game copy and redistribution of the intact archive with
its notices, while excluding game executables, EEex and InfinityLoader. See the
[distribution policy](docs/DISTRIBUTION_POLICY.md).

## Install

1. Check the published archive SHA-256 with `Get-FileHash <archive> -Algorithm SHA256`.
2. Extract the archive contents into the game root — the folder containing
   `Baldur.exe`, `chitin.key` and `WeiDU.log`; never extract it into `override`.
3. Close Steam and the game, then run `Install-BG2HD.exe` from that folder.
4. If EEex is missing, authorize the official download or provide its local
   archive. Its installer opens: select the game root and install its two
   required components.
5. After revalidation, BG2HD automatically opens WeiDU. Pick a language, then
   choose Core and the desired components.

Core is mandatory. The package includes the x4 main menu, x4 game selector,
and **every map marked `validated-installed` in `areas.csv`**: 143 variants in
135 map components. Each map is a separate WeiDU component; day/night pairs
remain atomic. Pending-QA maps, x2 builds and development sources stay
excluded.
Installing the x4 main-menu component automatically enables the renderer UI
replacement; the x4 selector component then adds its selector-specific atlases.

WeiDU backs up files it replaces. Core records the launcher and renderer state,
merges only its owned settings and creates a desktop `... - HD` shortcut.

### Future save compatibility

Core installs a byte-verified `M_IEEE.lua` which sets
`EEex_Debug_DisableExtraCreatureMarshalling = true` before renderer startup.
This prevents new saves from receiving the private `X-BIV1.0` records that the
vanilla 2.7.3.0 engine cannot read. Installation fails closed if this guard is
missing or changed. The contract applies to new save chains derived from a
vanilla-compatible state; it does not repair older saves that already contain
`X-BIV1.0`.

## Launch, update and uninstall

Use Steam's normal **Play** button after installation. Steam still starts
`Baldur.exe`; BG2HD makes it a shim to InfinityLoader and retains the original
Steam executable as `BaldurReal.exe`. The HD desktop shortcut follows the same
route.

For an update, close the game, extract the newer archive into the game root and
run `Install-BG2HD.exe` again. To remove it, uninstall optional components in
reverse order, then run `Uninstall-BG2HD.exe` with Core last. It offers two
explicit paths: the normal path removes BG2HD while retaining EEex and its
working Steam shim; the full-vanilla path, after two confirmations, also uses
the official EEex uninstaller and restores Steam's original executable. It
warns first when EEex pre-dated BG2HD or its origin is unknown, since other mods
may rely on it. Direct Core removal through `setup-bg2hd.exe` always retains
EEex. EEex source files and its installer remain as ordinary WeiDU mod sources,
but its active components and launch guard are removed by the full-vanilla path.
On the next BG2HD run this known inactive state is recognized and the official
EEex installer is offered again instead of reporting a partial installation.
Each reinstall starts a fresh BG2HD transaction and recreates the renderer
configuration when the full-vanilla path removed it; stale journals are not
treated as proof that their files are still active.
Never copy an executable by hand; if Steam Verify restores vanilla `Baldur.exe`,
use the documented Repair flow in [Steam integration](docs/STEAM_INTEGRATION.md).

For support, read [Recovery](docs/RECOVERY.md) and [Known issues](KNOWN_ISSUES.md).
Share sanitized `WeiDU.log` and relevant renderer-log excerpts only — never a
save game, account data or unredacted personal paths.
