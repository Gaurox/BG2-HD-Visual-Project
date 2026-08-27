# Steam integration and Repair

The complete installer ownership and content-integration rules are in the
[installer and upscale integration contract](INSTALLER_AND_UPSCALE_WORKFLOW.md).

## Normal state

After Core installation, the original verified Steam executable is preserved as
`BaldurReal.exe`. `Baldur.exe` contains the exact, accepted InfinityLoader
binary. InfinityLoader is configured to run `BaldurReal.exe` when Steam invokes
`Baldur.exe`. Steam therefore remains the normal launch path.

The helper backs up `InfinityLoader.ini`, merges its two owned mappings and
records a transaction in `bg2hd/state/steam-launcher.json`. It creates a desktop
shortcut only if it can identify it as its own. It does not overwrite an
unrelated shortcut of the same name.

## Steam Verify Files

Steam Verify may restore the original `Baldur.exe`. This is expected. Do not
rename or copy files manually.

1. Close Steam, BG2EE and InfinityLoader.
2. Run `Setup-BG2HD.exe` from the game root.
3. Select the Core repair option provided by the installer flow.
4. Start the game from Steam and confirm that it reaches the menu.

Repair is intentionally allowed only when the state journal, preserved
`BaldurReal.exe` and vanilla `Baldur.exe` have the exact expected hashes. Any
other layout is foreign and must be diagnosed first.

## Removing BG2HD or returning to vanilla

Uninstall optional content first, then remove Core. A direct WeiDU Core removal
restores BG2HD-owned files, renderer configuration and its shortcut, but keeps
the verified `Baldur.exe` InfinityLoader shim and `BaldurReal.exe`. It also
updates the loader mapping so Steam continues to launch EEex normally. This is
the safe default: EEex may be shared with other mods.

To choose the full-vanilla path, run `Uninstall-BG2HD.exe` from the game root
instead. Select option 2 and confirm twice. It first performs the safe BG2HD
removal, then invokes the official `setup-EEex.exe` uninstaller for components
1 and 0, validates their removal, removes the EEex launch guard and atomically
restores original `Baldur.exe`. When the game uses a language not translated by
EEex WeiDU, it temporarily selects `en_US` in `weidu.conf` solely for that
uninstall and restores the original configuration immediately afterwards.

The launcher records EEex provenance when possible. A pre-existing or unknown
EEex installation triggers an additional warning and confirmation before full
removal. If any file has changed outside BG2HD, or EEex cannot be removed and
verified, the helper stops rather than guessing which executable or
configuration should survive.

The full-vanilla path is also the supported save-compatibility test boundary:
create the new save while BG2HD is installed, close the game, run the confirmed
full uninstall, then load/save/reload through Steam. Renaming `Baldur.exe` or
launching `BaldurReal.exe` directly is not an equivalent supported test.
