# Water tint — engine-slot resolution — 2026-09-12

- Scope: runtime PVRZ tint readback; observed on `AR0046N` / `WLAKE00`.
- State: installed development candidate; pending ingame QA; no release integration.
- Source base: `aaefb8a294fab5af28e968188e53618d099e2a6a` plus the six-file snapshot below.

## Failure evidence

- Session: 2026-09-12 16:46:48–16:47:48 Europe/Paris.
- Logs: `build/water-tint-slot-resolution-ar0046n-20260912-v1/evidence/`.
- `AR0046N`: 8/13 transitions sampled brown `(0.055, 0.038, 0.020)`; 4 sampled blue
  `(0.061, 0.088, 0.111)`; 1 used blue fallback `(0.062, 0.089, 0.117)`.
- Correlation: brown when `CResPVR::texture` engine slot differs from live GL name, e.g.
  `engineSlot=44`, `glName=48`; blue when both happen to match, e.g. `3` / `3`.
- Cause: `read_pvrz_tint_page()` bound the engine slot directly as an OpenGL texture name.

## Correction

- Resolve every tint candidate through the manifested 512-entry native texture table.
- Validate slot range, `glName`, dimensions and `deletePending` before readback.
- Revalidate the descriptor after readback; mismatch fails closed to the family fallback.
- Publish the validated table only while hooks are installed; clear it on setup failure/shutdown.
- Snapshot: `build/water-tint-slot-resolution-ar0046n-20260912-v1/source-snapshot/`.
- Automated tests: none, per user choice. Release compilation only, `BUILD_TESTING=OFF`.

## Candidate and installation

| Item | Path / SHA256 |
|---|---|
| Build | `build/iee-water-tint-slot-resolution-20260912-vs2019/` |
| Candidate | `build/water-tint-slot-resolution-ar0046n-20260912-v1/renderer/` |
| DLL | `35A5075B1E2BD6A366F55CE9940AD5F1FA89D127FFD16098428A89F5EBC3E46F` |
| INI unchanged | `F90885D3E920E06663E0E86FC44FB6A20C0191D8B09CC0F91130169C7B29570C` |
| Receipt | `backups/renderer/20260912T145223328590Z-a42cd725/renderer-install-receipt.json` |

- Compiler: VS2019 / MSVC 19.29, x64 Release; DLL target succeeded.
- `BaldurReal.exe` offline manifest validation: passed; SHA256
  `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`.
- Game and InfinityLoader closed; preflight, installation and receipt verification succeeded.
- Map assets, registry, shaders, release manifests, payload, staging and archives unchanged.
- QA: load `AR0046`, set night repeatedly, and confirm every `Area liquid tint` is blue or the
  WTLAKE fallback; no `(0.055, 0.038, 0.020)` sample.
