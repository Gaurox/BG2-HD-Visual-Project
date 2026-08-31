# Agent entry point — InfinityEngine-Enhancer

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

1. Read [`README.md`](README.md), then only the document for the subsystem being changed.
2. Build identities and offsets live in `src/iee/game/build_manifest.*`; never scatter offsets in
   hooks.
3. Hooks must fail closed on an unknown executable, invalid manifest, capacity overflow or malformed
   registry.
4. Preserve x1 game geometry and save neutrality. Runtime texture scaling must not mutate ARE/WED
   coordinates or serialized game state.
5. Do not use `cmake-build-*`, `build-filter-*`, DLLs, logs or runtime captures as source files.

Never run tests automatically. Ask the user to choose targeted tests, all tests, or no tests as
defined in [`../../../docs/TEST_SELECTION.md`](../../../docs/TEST_SELECTION.md). For targeted host
tests:

```powershell
cmake -S . -B cmake-build-test -DBUILD_TESTING=ON
cmake --build cmake-build-test --target iee_tests
ctest --test-dir cmake-build-test --output-on-failure
```

Windows release build:

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 `
  -DIEE_BUILD_WINDOWS_DLL=ON -DBUILD_TESTING=ON
cmake --build build --config Release --target release_bundle
```

For sprite assets read `../../../sprite/README.md`; for area animations read
`../../../animations/README.md`. Ingame QA does not authorize release-manifest integration.
