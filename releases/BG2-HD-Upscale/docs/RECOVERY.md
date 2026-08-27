# Recovery and support

## Installation stopped or failed

Do not start the game and do not manually edit `Baldur.exe`, `BaldurReal.exe`,
`InfinityLoader.ini` or the BG2HD state files. Close Steam and rerun
`Install-BG2HD.exe`; it will verify the prerequisites before opening WeiDU.
WeiDU and the Core helper will then either complete safely, roll back their
recorded transaction or print a refusal reason.

## Steam Verify was used

Steam may restore vanilla `Baldur.exe`. Follow the Repair flow in
[Steam integration](STEAM_INTEGRATION.md). If Repair refuses the state, stop
there: a refusal protects an executable altered by another tool or mod.

## Unknown executable, missing EEex or open process

These are intentional fail-closed checks. If EEex is absent or cleanly inactive
after a full-vanilla restore, use the guided official-install flow in
`Install-BG2HD.exe`. If it is genuinely partial or changed, use
the official EEex installer to repair it first. Restore a supported Steam build
and close `Baldur.exe`/`InfinityLoader.exe` before retrying. Never bypass a
hash check with a manually copied executable.

## EEex dialog after removing BG2HD

Do not restore `Baldur.exe` by hand. The standard BG2HD removal now retains the
verified EEex Steam shim specifically to avoid the "EEex not active" dialog.
Use `Uninstall-BG2HD.exe` only if you deliberately want the full-vanilla option;
it removes EEex components after confirmation and restores the original Steam
executable. If that operation stops, keep the displayed error and `WeiDU.log`;
do not delete `BaldurReal.exe` or `InfinityLoader.ini` manually.

## Support bundle

Provide: BG2EE store/version, BG2HD version, selected components, the final
WeiDU output, relevant renderer-log lines and the exact refusal message. Remove
Windows account names, absolute personal paths, saves, screenshots containing
private data, Steam account files and tokens before sharing.
