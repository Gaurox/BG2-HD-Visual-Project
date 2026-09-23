# Eau WED à 30 FPS réels — procédé commun aux familles

Recette **validée ingame sur AR1600 (WTLAKE) le 2026-09-23** :
[`AR1600_WATER_30FPS_V2_20260923.md`](AR1600_WATER_30FPS_V2_20260923.md),
QA [`manifests/ar1600-water-30fps-user-qa-20260923-v2.json`](manifests/ar1600-water-30fps-user-qa-20260923-v2.json).
Pour les autres familles : **proposition**, chaque map garde sa propre QA. Aide facultative, pas un ordre imposé.

## Règles acquises

| Règle | Pourquoi |
|---|---|
| Interpoler **avant** l'upscale, sur les clés natives x1 | des ancres x4 SeedVR image par image varient ×3 en détail → pulsation 2,5 Hz |
| Interpolation trigonométrique périodique (FFT temporelle, Nyquist scindé) | clés exactes, boucle fermée lisse ; les liquides natifs miroitent, le flux (DIS) n'explique que ~25 % |
| **Pas d'Apollo / interpolateur par flux** pour les overlays liquides | `apo-8` : clés 1–5 non restituées, doublons, plafond 8× (doublons à 12×) |
| SeedVR : **toute la boucle en un seul chunk temporel** | chunks ou images séparées = marches de détail |
| Raccord de boucle : tête/queue enroulées, fondu **à variance préservée** (16 phases) | coupe franche 4,6 vs pas 1,7 ; fondu linéaire −25 % de netteté |
| Phases = 30 × durée du cycle, arrondi au multiple du nombre de clés | 30 FPS réels, clés exactes |
| Registre `source_fps = target_fps = 30` | aucun demi-fondu shader (il floutait) |
| Une page PVRZ 4096 par ressource (15×15 = 225 phases max) | timeline shader = une page ; 4096 déjà prouvé ([DECISIONS](../../docs/DECISIONS.md)) |
| WED : slot → alias isolé, lookup séquentielle 0…M−1, vitesse 1 | repli sans shader = 2× plus lent, jamais faux ; autres maps intactes |
| Alias pluie = alias sec + `R` | routage pluie natif du moteur |
| Nom de page = `alias[0] + alias[2:] + "00"` ≤ 8 et **unique** | `QZLKV0` et `QBLKV0` donnent tous deux `QLKV000` : le producteur refuse |

## Producteur

[`pipeline/scripts/build_liquid_temporal_30fps.py`](../scripts/build_liquid_temporal_30fps.py) — une map par run.
Pré-requis (refus explicite sinon) :

- groupes préparés par `build_liquid_periodic_x4_trial.py` sous `<spatial_run>/overlays/groups/<id>/`
  (contextes x1 3×3, alpha, lookup, adjacences) ;
- sélection spatiale : `selection` du plan, défaut `<spatial_run>/overlays-selected-v3/selection.json`
  (méthode seedvr/bilinear et collier de bords du build retenu) ;
- WED source : `source_wed`, défaut `<spatial_run>/override-candidate-v3/<WED>.WED` ;
- base x4 de la map **déjà installée** : le registre hache le `<WED>.TIS` live ;
- même lookup pour tous les membres d'un groupe ; alpha identique entre clés ;
- groupe sec listé avant son `rain_of` ; noms de page uniques dans le plan et absents de `override`.
Régression : reproduit AR1600 v2 à l'octet près (TIS, PVRZ, interpolation ; WED au nom d'alias près).
Tests : `pipeline/tests/test_liquid_temporal_30fps.py`, `test_water_wed.py`.

Plan (JSON) :

```json
{"spatial_run": "maps/water-batches/runs/liquid-families-x4-20260923-v1", "wed": "AR1607",
 "selection": "<optionnel>", "source_wed": "<optionnel>",
 "base_registry": "pipeline/water/requests/ar1600-water-30fps-20260923-v2/registry-v3.json",
 "groups": [{"id": "swamp", "aliases": {"WTSWAM": "QCSWM0"}, "material_id": 5},
            {"id": "swamp_rain", "rain_of": "swamp", "aliases": {"WTSWAMR": "QCSWM0R"}, "material_id": 5}]}
```

`cycle_seconds` est à fixer par groupe sec lorsque les vitesses WED divergent (voir tableau).
`base_registry` = registre compilé dans la DLL installée (actuellement
`pipeline/water/requests/ar1600-water-30fps-20260923-v2/registry-v3.json`, AR0900 + AR1600) ;
les entrées de la même WED sont remplacées, les autres conservées. Reporter le nouveau registre
sous `pipeline/water/requests/<run>/` avec le reçu d'installation.

```powershell
$plan = '<plan.json>'
$run = 'maps/water-batches/runs/<map>-water-30fps-<date>-v1'   # nouveau dossier à chaque essai
foreach ($s in 'prepare','interpolate','upscale','build','review') {
  $extra = if ($s -eq 'prepare') { @('--plan', $plan) } else { @() }
  python -B pipeline/scripts/build_liquid_temporal_30fps.py --output $run --stage $s @extra
}
```

- `upscale` : ComfyUI lancé, file vide. `--frames-per-chunk <4n+1> --chunk-overlap <k>` = repli VRAM
  seulement (marches de détail possibles aux frontières).
- `build` : candidat `RUN/candidate/` + `RUN/registry-v3.json` ; métriques post-BC3 dans `RUN/build.json`
  (cibles AR1600 : netteté max/min ≤ 1,25, pas max/médian ≤ 1,4).
- DLL : build neuf avec le registre du run. **Sans `-DIEE_WATER_ROUTE2_REGISTRY`, CMake compile
  `assets/water-route2/registry-v2.json` (AR0900 seul) et perd les identités 30 FPS installées.**

```powershell
Set-Location engine/InfinityEngine-Enhancer/source-patchee
$b = 'build-<map>-water-30fps-<date>-v1'; $deps = "$PWD/build-cache128/_deps"
& 'C:/Program Files/CMake/bin/cmake' -S . -B $b -G 'Visual Studio 16 2019' -A x64 `
  -DIEE_BUILD_WINDOWS_DLL=ON -DFETCHCONTENT_FULLY_DISCONNECTED=ON -DFETCHCONTENT_UPDATES_DISCONNECTED=ON `
  "-DFETCHCONTENT_SOURCE_DIR_MINHOOK=$deps/minhook-src" "-DFETCHCONTENT_SOURCE_DIR_SPDLOG=$deps/spdlog-src" `
  "-DFETCHCONTENT_SOURCE_DIR_ZLIB=$deps/zlib-src" "-DIEE_WATER_ROUTE2_REGISTRY=<RUN absolu>/registry-v3.json"
& 'C:/Program Files/CMake/bin/cmake' --build $b --config Release -- -m
& 'C:/Program Files/CMake/bin/ctest' --test-dir $b -C Release -R '^iee_tests$' --output-on-failure
```
- Installation, jeu fermé : `Install-AreaOverrideAssets.ps1 -SourceRoot RUN/candidate -BackupRoot <chemin absolu>`
  + copie DLL avec reçu (modèle : `backups/water/ar1600-water-30fps-20260923-v2/runtime/install-backup.json`).

## Familles — état des données (témoins du lot spatial)

État live vérifié le 2026-09-23 : AR1600 → `QBLKV0` 72 phases ; AR1000/AR1607/AR0404/AR0413/AR3000/
AR0011/AR5203 → alias `Q9*` du lot spatial, lookup native 6/8/12, hors registre route2 (q0).

Vitesse = octet `tilemap+7` des slots ; valeur observée = nombre de clés sur le premier slot, 0 ailleurs.
Sa sémantique n'est pas confirmée : la durée AR1600 (6×6/15 = 2,4 s) est validée visuellement, pas prouvée.

| Groupe | Témoin | Clés | Vitesses | Cycle proposé | Phases | x4 | Collier | Point ouvert |
|---|---|---:|---|---|---:|---|---|---|
| lake WTLAKE | AR1600 | 6 | 6 | 2,4 s | 72 | seedvr | non | **validé** |
| pool WTPOOL | AR1000 jour | 6 | 6 | 2,4 s | 72 | bilinear | non | — |
| swamp WTSWAM | AR1607 | 6 | 6 | 2,4 s | 72 | seedvr | non | opacité native 100 |
| sewage WTSEW | AR0404 | 6 | 6 | 2,4 s | 72 | seedvr | oui | AR2100 stock6 hors run |
| oil WTOIL | AR0413 | 6 | 6 | 2,4 s | 72 | seedvr | oui | contrat alpha0 historique |
| lake_teal WTLAKA–D | AR3000 | 8 | 8/0/0/0 | explicite (8×8/15 = 4,27 s ?) | 128 | seedvr 1536² | oui | durée ; VRAM chunk unique |
| brown_flow WT5000A–D | AR5203 | 8 | 8/0/0/0 | explicite (4,27 s ?) | 128 | seedvr 1536² | oui | durée ; VRAM |
| lava WTLAVA–D | AR0011 | 12 | 12/0/0/12 | explicite (12×12/15 = 9,6 s ?) | 288 > 225 | bilinear | non | capacité page ; lookup 11 d'AR5200 |

Hors producteur : shader multi-slots (A–D = 4 identités sur une même WED) non vérifié en jeu ;
lave émissive non qualifiée route2 ; écume/art fixe peint dans le TIS de base (AR1600) non animé ;
surfaces ARE/BAM → timeline 30 FPS du pack d'animation, même durée.
