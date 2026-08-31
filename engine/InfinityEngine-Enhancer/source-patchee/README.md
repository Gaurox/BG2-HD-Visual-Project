# InfinityEngine-Enhancer

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

DLL Windows chargée par EEex pour étendre le rendu sans modifier les coordonnées ARE/WED. Les
builds acceptés et les capacités par build viennent exclusivement de
`src/iee/game/build_manifest.*`; une identité inconnue échoue fermée.

## Fonctions

| Fonction | Périmètre |
|---|---|
| Tuiles TIS/PVRZ xN | échelle lue dans le header TIS, puis table PVR, heuristique en dernier recours |
| Liquides | masque WED, teinte auteur, textures DDS facultatives, shader `fpSEAM.glsl` |
| Animations de zone | registres v1/v2/v3, TimedTimeline, packs par zone et variantes par occurrence |
| Sprites créature xN | chemin QA opt-in, baseline `NEAREST`, pour propriétaires/classes explicitement manifestés |
| Transition vidéo | AR1300/BRIDGE01 uniquement, désactivée par défaut |
| UI | essais ciblés explicitement activés |
| Diagnostics | télémétrie bornée avec `PerformanceLogs=true` |

Le profil est neutre pour les sauvegardes : `tools/M_IEEE.lua` désactive le marshalling étendu de
créatures EEex. Il ne migre pas les sauvegardes existantes.

## État expérimental important

La préparation hors frame des pages de carte est à la phase B2f : un slot JIT, quatre
revendications, désactivée par défaut. Un passage quatre zones a réussi, mais les campagnes A/B
répétées et cache froid manquent ; la fonctionnalité n'est pas qualifiée release. Voir
[`docs/map-page-offframe-preparation.md`](docs/map-page-offframe-preparation.md) et la
[`preuve B2f`](docs/validation/map-page-offframe-phase3b2f.md).

La régression locale des tooltips à FPS EEex élevés et son contournement sont documentés dans
[`docs/validation/eeex-tooltip-uncapped-fps.md`](docs/validation/eeex-tooltip-uncapped-fps.md).

## Build et tests

Avant toute commande de test, demander « ciblés / tous / aucun » conformément à
[`../../../docs/TEST_SELECTION.md`](../../../docs/TEST_SELECTION.md). Si les tests moteur ciblés
sont choisis :

```powershell
cmake -S . -B cmake-build-debug -DBUILD_TESTING=ON
cmake --build cmake-build-debug --target iee_tests
ctest --test-dir cmake-build-debug --output-on-failure
```

DLL Windows et bundle :

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 `
  -DIEE_BUILD_WINDOWS_DLL=ON -DBUILD_TESTING=ON
cmake --build build --config Release --target release_bundle
```

`cmake --install build --config Release --prefix <directory>` produit le même layout game-root.
Le validateur d'exécutable et les gates sont décrits dans
[`docs/new-build-validation.md`](docs/new-build-validation.md). Les dépendances `FetchContent`
restent épinglées à des commits complets.

## Candidat local

Ne jamais copier une DLL de test à la main :

```powershell
python tools/install_renderer_candidate.py install <candidate-dir> --verify-only
python tools/install_renderer_candidate.py install <candidate-dir>
python tools/install_renderer_candidate.py verify <receipt-or-transaction-dir>
python tools/install_renderer_candidate.py restore <receipt-or-transaction-dir>
```

Le dossier candidat contient exactement `InfinityEngine-Enhancer.dll` et
`InfinityEngine-Enhancer.ini`. Jeu et InfinityLoader doivent être fermés. Cette transaction ne
modifie pas le bundle release scellé.

## Documentation

| Sujet | Référence |
|---|---|
| Modules et limites | [`docs/architecture.md`](docs/architecture.md) |
| Threads et OpenGL | [`docs/threading-model.md`](docs/threading-model.md) |
| Manifests de build | [`docs/build-manifests.md`](docs/build-manifests.md) |
| Reverse engineering | [`docs/reverse-engineering.md`](docs/reverse-engineering.md) |
| Types runtime | [`docs/runtime-types.md`](docs/runtime-types.md) |
| Tuiles xN | [`docs/tile-upscale.md`](docs/tile-upscale.md) |
| Timeline animation | [`docs/area-animation-timed-timeline.md`](docs/area-animation-timed-timeline.md) |
| Sonde d'horloge historique | [`docs/area-animation-clock-probe.md`](docs/area-animation-clock-probe.md) |
| Occlusion native | [`docs/native-occlusion-phase1.md`](docs/native-occlusion-phase1.md) |
| Transition AR1300 | [`docs/event-video-overlay-assets.md`](docs/event-video-overlay-assets.md) |
| Transaction renderer | [`docs/renderer-candidate-transaction.md`](docs/renderer-candidate-transaction.md) |
| Sprites | [`../../../sprite/README.md`](../../../sprite/README.md) |

Licence : [`LICENSE`](LICENSE).
