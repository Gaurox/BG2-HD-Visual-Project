# Agent entry point — InfinityEngine-Enhancer

La documentation moteur est un index de solutions. Lire seulement la rubrique utile ; aucun
préflight, ordre de lecture, test ou audit n'est imposé.

> **Règle documentaire : écrire pour des agents IA. Toute nouvelle documentation ou modification doit privilégier la densité d’information. Éviter la prose longue ; conserver les invariants, commandes et preuves utiles.**

## Invariants techniques

- Les identités de build et offsets restent centralisés dans `src/iee/game/build_manifest.*`.
- Un hook échoue fermé sur exécutable inconnu, manifeste invalide, capacité dépassée ou registre
  mal formé.
- Préserver la géométrie x1 et la neutralité des sauvegardes.
- Ne pas prendre `cmake-build-*`, `build-filter-*`, DLL, logs ou captures runtime comme sources.
- Fermer le jeu et InfinityLoader avant installation d'un candidat.
- Une QA ingame n'autorise jamais à elle seule une modification de release.

## Commandes disponibles, à la demande

Tests hôte ciblés :

```powershell
cmake -S . -B cmake-build-test -DBUILD_TESTING=ON
cmake --build cmake-build-test --target iee_tests
ctest --test-dir cmake-build-test --output-on-failure
```

Bundle Windows :

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 `
  -DIEE_BUILD_WINDOWS_DLL=ON -DBUILD_TESTING=ON
cmake --build build --config Release --target release_bundle
```

Ces commandes ne sont pas des étapes obligatoires : les employer seulement si elles produisent ou
contrôlent directement le résultat demandé.
