# Architecture

`bg2hd` separates dependency preparation, content installation and the Steam
launch lifecycle.

Implementation entry point: [installer and upscale integration contract](INSTALLER_AND_UPSCALE_WORKFLOW.md).

```text
Install-BG2HD.exe
              |
 official EEex installer (only if absent, with consent)
              |
         setup-bg2hd.exe
              |
Steam Play / HD desktop shortcut
              |
         Baldur.exe (BG2HD shim)
              |
       InfinityLoader.exe (external)
              |
       BaldurReal.exe (preserved Steam executable)
              |
 EEex -> InfinityEngine-Enhancer -> BG2EE x4 resources in override
```

WeiDU owns the map/UI files in `override` and their backups. Component 0 (Core)
uses `bg2hd-steam.ps1` to install the eight-file frozen renderer bundle,
snapshot its seven runtime targets, create or merge its configuration, preserve
the original executable, publish the known InfinityLoader shim, merge
`InfinityLoader.ini` and create its desktop shortcut. State is written under
`bg2hd/state/` inside the game directory.

The renderer bootstrap file is also a save-format boundary. Its verified
`M_IEEE.lua` disables EEex extended creature marshalling before Lua bindings
are initialized. This prevents future save chains from gaining `X-BIV1.0`
records while leaving renderer hooks active. Both the packaged and installed
guard are hash-checked; this is independent from texture upscaling.

The bootstrap and helper are fail-closed: an unsupported game, missing Visual
C++, partial or unknown EEex, unknown executable hash, open game process or
foreign launcher layout prevents writes. EEex and InfinityLoader remain owned
by EEex; BG2HD only validates them. A normal Core removal deliberately preserves
the EEex Steam shim. `Uninstall-BG2HD.exe` is a separate, confirmed full-vanilla
flow: it calls the official EEex uninstaller, verifies components 0/1 are gone,
then atomically restores `Baldur.exe`. Provenance is recorded when known and an
external or unknown EEex installation gets an additional warning.
It never changes Steam account files, launch options, appmanifest files or
`localconfig.vdf`.

The renderer is owned by BG2HD in this local alpha. On uninstall it restores a
pre-existing renderer file only when the installed file still has BG2HD's
recorded hash; a file changed by another tool is preserved and causes a safe
refusal. EEex and InfinityLoader remain external prerequisites.
