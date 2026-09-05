# Experimental Renderer Candidate Transaction

## Scope

`tools/install_renderer_candidate.py` owns exactly two game-root files for one local experiment:

- `InfinityEngine-Enhancer.dll`;
- `InfinityEngine-Enhancer.ini`.

It does not own logs, `iee-textures/`, EEex files, override shaders, animation/sprite registries,
maps, release staging or manifests. The release renderer lifecycle remains managed by the frozen
eight-file BG2HD helper.

The candidate directory must be new and contain exactly the two canonical names above. The DLL is
validated as an x64 PE32+ DLL and the INI must be non-empty UTF-8 text with at least one section.
Neither file may be a symbolic link.

## Preflight and installation

Keep the game and InfinityLoader closed. Always run the read-only preflight first:

```powershell
python tools/install_renderer_candidate.py install <candidate-dir> --verify-only
```

The real installation is explicit:

```powershell
python tools/install_renderer_candidate.py install <candidate-dir>
```

Before changing the game, the tool creates a unique directory under `backups/renderer/` containing:

```text
<transaction>/
  renderer-install-receipt.json
  candidate/
    InfinityEngine-Enhancer.dll
    InfinityEngine-Enhancer.ini
  before/
    # only the two files that existed before installation
```

The staged candidate and backups are hash-verified before the receipt is published with status
`prepared`. Publication uses temporary files plus atomic replacement. A partial failure triggers a
rollback to the exact initial hashes; if that rollback cannot complete, the receipt becomes
`recovery-required` and retains enough state for a later restore.

## Verification and restoration

The original candidate/build directory is not required after the receipt has been created:

```powershell
python tools/install_renderer_candidate.py verify <receipt-or-transaction-dir>
python tools/install_renderer_candidate.py restore <receipt-or-transaction-dir>
```

Restore accepts only targets matching either the recorded initial state or the recorded candidate.
Any third-party modification is left untouched and causes a refusal. Files absent before the
transaction are deleted only when they still match the installed candidate hash. An interrupted
restore remains in `restoring` or `recovery-required` and the same command can converge it to
`restored`.

The receipt, staged payload and backups must be retained until restoration has been verified. Do
not edit them. A `rolled-back`, `restored` or merely observed local candidate is never equivalent to
`validated-installed` and cannot be promoted to the release manifest.

## Required sequence for a new engine experiment

1. Build Debug and Release from the reviewed source tree and run native tests.
2. Validate `BaldurReal.exe` against `src/iee/game/build_manifest.*` with
   `tools/validate_build.py`.
3. Create a new two-file candidate directory and record its DLL/INI hashes in the experiment note.
4. Run `install ... --verify-only`.
5. Install with a new transaction and immediately verify its receipt.
6. Run the targeted ingame protocol and archive the bounded log.
7. Close the game and InfinityLoader, restore from the same receipt, then verify again.

Never reuse the four historical raw `map-page-prewarm-*` snapshots as an installation mechanism.
They remain evidence only.
