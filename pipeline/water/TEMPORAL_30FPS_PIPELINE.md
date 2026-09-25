# Eau WED à 30 FPS réels — procédé commun aux familles

Recette **validée ingame** sur AR1600 (`lake`), AR0408/AR0703 (`pool`), AR2100 (`sewage`) et
AR0500/AR0500N (`swamp`, sec jour+nuit ; pluie q0 validée AR0500), AR5200 (`lava`, méthode `seedvr-torus`),
AR0503 (`oil`, `seedvr-torus` 1×1 + filtres temporels), AR5000 (`brown_flow`, `seedvr-torus` 2×2 + filtres + décrêtage), AR6300 (`lake_teal`, `seedvr-torus` 2×2 + filtres).
Référence fondatrice AR1600 :
[`AR1600_WATER_30FPS_V2_20260923.md`](AR1600_WATER_30FPS_V2_20260923.md),
QA [`manifests/ar1600-water-30fps-user-qa-20260923-v2.json`](manifests/ar1600-water-30fps-user-qa-20260923-v2.json).
Pour les autres familles : **proposition ou blocage explicite**, chaque map garde sa propre QA. Déroulé agent
(ordre, STOP, installation, reçus) : [WATER_MAP_RUNBOOK.md](WATER_MAP_RUNBOOK.md).

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
| Pool : force route2 0,70 matériau 1 sur le groupe sec (`approved_strength` du contrat) | WTPOOL bilinéaire quasi plat (σ 5,5/255) : la timeline seule paraît figée (AR1000 v3, AR0408 v1) ; la DLL donne le mode liquide du matériau aux alias `YF…` d'une identité à force > 0 |
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

Plan (JSON) — écrit automatiquement dans `<run>/temporal-plan.json` par `plan_water_map.py plan` pour les maps
de la chaîne standard ([SPATIAL_X4_PIPELINE.md](SPATIAL_X4_PIPELINE.md)) ; à la main pour les témoins du lot :

```json
{"spatial_run": "maps/water-batches/runs/liquid-families-x4-20260923-v1", "wed": "AR1607",
 "selection": "<optionnel>", "source_wed": "<optionnel>",
 "groups": [{"id": "swamp", "aliases": {"WTSWAM": "QCSWM0"}, "material_id": 5},
            {"id": "swamp_rain", "rain_of": "swamp", "aliases": {"WTSWAMR": "QCSWM0R"}, "material_id": 5}]}
```

`cycle_seconds` est à fixer par groupe sec lorsque les vitesses WED divergent (voir tableau).
`approved_strength` (groupe sec, contrat famille) → force route2 du registre ; > 0 sur un groupe pluie refusé
sauf matériau 5 (seul matériau qualifié par la DLL pour la passe pluie fpTone). Pluie : q0 pour toutes les familles
(`swamp` compris depuis AR0500 2026-09-25 : q0,70 efface les flaques). Pluie x4 visible seulement avec une DLL ≥
`ar0500-rain-q0-20260925-v2` (page PVRZ pluie liée par le hook ; avant, page sèche affichée) ; le runtime n'essaie que
la variante dessinée (`CInfinity::nCurrentRainLevel` ≠ 0 et bit météo de la zone).
`base_registry` optionnel : par défaut, registre compilé dans la DLL installée, lu dans
[`route2-registry-current.json`](route2-registry-current.json) (le producteur refuse si la DLL live n'est pas celle
du pointeur). Les entrées de la même WED sont remplacées, les autres conservées. Copier le nouveau registre sous
`pipeline/water/requests/<run>/` ; `Install-WaterRuntime.ps1` installe la DLL et met le pointeur à jour.

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
- Installation, jeu fermé : `Install-AreaOverrideAssets.ps1 -SourceRoot RUN/candidate -BackupRoot backups/water/<run>/override`
  puis `Install-WaterRuntime.ps1 -Dll … -Registry pipeline/water/requests/<run>/registry-v3.json -Label <run>` ;
  reçu : `record_water_decision.py install --kind temporal-30fps` (commandes : [runbook](WATER_MAP_RUNBOOK.md)).

## Familles — état des données (témoins du lot spatial)

État live vérifié le 2026-09-23 : AR1600 → `QBLKV0` 72 phases ; AR1000/AR1607/AR0404/AR0413/AR3000/
AR0011/AR5203 → alias `Q9*` du lot spatial, lookup native 6/8/12, hors registre route2 (q0).

Vitesse = octet `tilemap+7` des slots ; valeur observée = nombre de clés sur le premier slot, 0 ailleurs.
Sa sémantique n'est pas confirmée : la durée AR1600 (6×6/15 = 2,4 s) est validée visuellement, pas prouvée.

| Groupe | Témoin | Clés | Vitesses | Cycle proposé | Phases | x4 | Collier | Point ouvert |
|---|---|---:|---|---|---:|---|---|---|
| lake WTLAKE | AR1600 | 6 | 6 | 2,4 s | 72 | seedvr | non | **validé** |
| pool WTPOOL | AR0408 | 6 | 6 (0 : AR1004, AR1601, AR2012) | **2,4 s figé** | 72 | bilinear | non | **validé ingame AR0408** (q0,70 matériau 1 sec) ; pluie q0 non observée |
| swamp WTSWAM | AR0500 / AR0500N | 6 | 6 | **2,4 s figé** | 72 | seedvr | non | **validé ingame sec jour+nuit**, q0,70 matériau 5 sec ; **pluie q0 validée AR0500** |
| sewage WTSEW | AR2100 | 6 | 6 | **2,4 s figé** | 72 | seedvr | oui | **validé ingame** ; ratios 1,269 / 1,682 acceptés après review |
| oil WTOIL | AR0503 | 6 | 6 | 2,4 s natif | 72 | seedvr-torus + filtres | non | **validé ingame AR0503** ; AR0413 (contrat alpha0 historique) hors standard |
| lake_teal WTLAKA–D | AR6300 | 8 | 0/0/0/0 (AR3000 : 8/0/0/0) | **4,27 s figé** | 128 | seedvr-torus + filtres | non | **validé ingame AR6300** |
| brown_flow WT5000A–D | AR5000 | 8 | 8/0/0/0 | **4,27 s figé** | 128 | seedvr-torus + filtres + décrêtage | non | **validé ingame AR5000** |
| lava WTLAVA–D | AR5200 | 12 (`keyframes`, pas la lookup `[0…9,11]`) | 11/11/0/0 | **7,2 s figé** | 216 | seedvr-torus | non | **validé ingame AR5200** ; autres maps lave : tore à vérifier |

### Validations par map

| Map | Famille | Phases / cycle | Run | QA en jeu | Réserve de production |
|---|---|---|---|---|---|
| AR2100 | sewage | 72 / 2,4 s | `ar2100-water-30fps-20260923-v1` | validée — `ar2100-temporal-30fps-user-qa-20260923-v1.json` | ratios 1,269 / 1,682 acceptés après vidéo de review |
| AR0408 | pool | 72 / 2,4 s | `ar0408-water-30fps-20260923-v1` | **rejetée** — `ar0408-temporal-30fps-user-qa-20260923-v1.json` | eau figée ; animation d’eau qui coule absente |
| AR0408 | pool | 72 / 2,4 s, q0,70 | `ar0408-water-30fps-20260923-v2` | validée — `ar0408-temporal-30fps-user-qa-20260923-v2.json` | candidat = octets v1 ; seuls registre (q0,70 sec) et DLL changent |
| AR0703 | pool | 72 / 2,4 s, q0,70 | `ar0703-water-30fps-20260923-v1` | validée — `ar0703-temporal-30fps-user-qa-20260923-v1.json` | pluie q0 non observée (intérieur) |
| AR0500 | swamp | 72 / 2,4 s, q0,70 sec, pluie q0 | `ar0500-water-30fps-20260924-v1` ; registre `requests/ar0500-rain-q0-20260925-v1` | validée jour — `ar0500-temporal-30fps-user-qa-20260924-v1.json` ; pluie validée — `ar0500-temporal-30fps-user-qa-20260925-v1.json` | ratios 1,20/1,43 sec et 1,37/1,34 pluie ; essai pluie q0,70 (`requests/ar0500-rain-q070-test-20260925-v1`) rejeté : « on ne voit plus les flaques » |
| AR0500N | swamp | 72 / 2,4 s, q0,70 sec, pluie q0 | `ar0500n-water-30fps-20260924-v1` ; registre `requests/ar0500-rain-q0-20260925-v1` | validée nuit — `ar0500n-temporal-30fps-user-qa-20260924-v1.json` | mêmes ratios hors seuil acceptés avant installation ; pluie q0 installée, non observée |
| AR5000 | brown_flow | 128 / 4,27 s, `seedvr-torus`, σ périodique 8 | `ar5000-water-30fps-20260924-v1` | non installée | bouclage 1,85/1,50 (texture lisse) |
| AR5000 | brown_flow | 128 / 4,27 s, σ 2 | `ar5000-water-30fps-20260924-v2` | remplacée par v3 | lignes aux bords de cellules : cause surtout bases A/C (interfaces, `central_water`), voir SPATIAL/CONTOUR |
| AR5000 | brown_flow | 128 / 4,27 s, σ 2 + décrêtage x1 | `ar5000-water-30fps-20260924-v3` | validée — `ar5000-temporal-30fps-user-qa-20260925-v1.json` | netteté ≤ 1,11, pas ≤ 1,16 ; raccord natif hors tore conservé (cellules 41–45, rangées 33/34) ; pluie non observée |
| AR6300 | lake_teal | 128 / 4,27 s, σ 8 | `ar6300-water-30fps-20260925-v1` | non installée | bouclage 1,85/1,49 |
| AR6300 | lake_teal | + décrêtage x1 | `ar6300-water-30fps-20260925-v2` | **rejetée avant installation** | grille visible : le décrêtage retire du contenu (0,47) sur texture contrastée |
| AR6300 | lake_teal | σ 2, même inférence que v1 | `ar6300-water-30fps-20260925-v3` | validée — `ar6300-temporal-30fps-user-qa-20260925-v1.json` | netteté ≤ 1,20, pas ≤ 1,23 ; petits cercles SeedVR répétés acceptés ; pluie non observée |
| AR5200 | lava | 220 / 7,3 s, bilinéaire, lookup 11 | `ar5200-water-30fps-20260924-v1` | **rejetée** — `ar5200-temporal-30fps-user-qa-20260924-v1.json` | lag 12 → 2,8 FPS : scan DLL par draw (corrigé, voir plus bas) |
| AR0503 | oil | 72 / 2,4 s, `seedvr-torus`, q0 | `ar0503-water-30fps-20260924-v1` | remplacée par v2 (jugée « pas terrible ») | bouillonnement SeedVR + cadence 4 phases 0,73 ; netteté 1,34 |
| AR0503 | oil | 72 / 2,4 s, `seedvr-torus` + harmoniques ≤ 9 + égalisation, q0 | `ar0503-water-30fps-20260924-v2` | validée — `ar0503-temporal-30fps-user-qa-20260924-v1.json` | même inférence que v1 ; pas médian 1,02 → 0,42, netteté 1,34 → 1,15 ; pluie non observée |
| AR5200 | lava | 216 / 7,2 s, `seedvr-torus`, q0 | `ar5200-lava-torus-30fps-20260924-v1` | validée — `ar5200-temporal-30fps-user-qa-20260924-v2.json` | pas max/médian 1,53 (fondu de boucle) accepté ; 60 FPS mesurés ; pluie non observée |

## Méthode `seedvr-torus` (pavages A–D, lave AR5200 ; tuile unique, huile AR0503)

Condition : adjacences WED ⊆ tore du layout (`torus_pairs`), sinon `prepare` refuse ; un layout 1×1 remplace
le collier de bord (bande lissée ~10 px par tuile, détail horizontal < 0,6 × médiane sur AR0503). Mesures AR5200 :
raccords natifs x1 1,16/1,13 × pas médian ; SeedVR sur les 12 clés brutes les amplifiait en grille (1,56).

| Étape | Paramètre (`TORUS_DEFAULTS`) | Résultat AR5200 |
|---|---|---|
| Recollage x1 des bords de tuile 64 px, avant interpolation | bande 4, σ 3 le long du bord, gain 0,8 | 0,90 / 1,03 |
| SeedVR 7B, un chunk, motif 128 + marge enroulée 32 px x1 (192 → 768) | `seedvr_margin_x1` 32 | 249 frames, 10 Go VRAM |
| Périodique + lisse (Moisan), saut de bord passe-bas | `periodic_sigma_x4` 8 (σ 0 = ligne floue 0,37) | bouclage 1,01/1,11 ; tuiles 1,03/1,12 |
| Marges d'atlas | voisin réel du tore (`torus_tiles`) | — |

Plan : `method: seedvr-torus`, `keyframes`, `cycle_seconds` sur le groupe sec (écrits par `plan_water_map.py`
depuis le standard) ; la pluie hérite. Pluie à clés identiques : sortie SeedVR du sec réutilisée.
Reprise post-traitement sans ré-inférence : `seedvr-prompt.json` identique + `seedvr-out` complet.
Nouveau run sur la même inférence : `torus.reuse_seedvr_from` = dossier groupe d'un run antérieur ; refus si
entrées `seedvr-in` ou graphe (hors chemins) diffèrent.

Filtres de boucle optionnels (off par défaut ; activés pour l'huile par le standard) :

| Paramètre | Effet | Mesure AR0503 v1 → v2 |
|---|---|---|
| `temporal_harmonics` (1,5 × clés) | FFT temporelle : garde les harmoniques de boucle ≤ n ; la trig x1 n'en porte que ≤ clés/2, le reste = bouillonnement SeedVR + cadence latente 4 images | pas médian 1,02 → 0,42 ; cadence 1,05/1,03/1,07/0,73 → 1,05/1,06/1,03/1,02 |
| `equalize_detail` | détail haute fréquence (σ 3) de chaque phase ramené à la médiane (gain 0,8–1,25) | netteté max/min 1,34 → 1,15 |

Autres paramètres `seedvr-torus` (standard famille) :

| Paramètre | Effet | Cas |
|---|---|---|
| `heal_gain` 0 | pas de recollage quand les bords natifs sont déjà plus doux que l'intérieur | rivière brune (0,69/0,74) |
| `max_non_torus_share` | tolère des adjacences WED hors tore (raccord natif conservé, listé dans `plan.json`) | AR5000 : 0,4 % (cellules 41–45, rangées 33/34) |
| `periodic_sigma_x4` 2 | texture lisse : σ 8 laissait le bouclage à 1,85 | AR5000 → 1,21/0,95 |
| `deridge_band_x1` 2, `deridge_sigma_x1` 6 | efface en x1 la ligne claire des rangées de bord natives (SeedVR en fait une bande 4 px) | WT5000A–D 1,11 → 0,14 ; **refusé sur WTLAKA–D** (grille) ; autres familles : ligne ≤ contenu, non appliqué |

`seedvr.json` : `loop_before_temporal_filters` / `loop_after_temporal_filters`. Autres familles SeedVR (lac, égouts,
marais, lave) : même symptôme probable, non mesuré ni requalifié.

## Runtime : correspondance overlay par draw

`route2_water_overlay_match` (DLL) relisait toutes les tuiles de tous les slots et météos à chaque batch fpSEAM
(AR5200 : 4 × 220 × 2) → ~6,5 M `safe_read`/image. Correctif (build `ar5200-lava-torus-30fps-20260924-v1`) :
rejet immédiat si la taille de texture n'est pas une page overlay du registre de la WED (`has_overlay_page`),
cache positif revalidé à chaque draw, cache négatif expirant après 256 appels, dédoublonnage par page PVR.
Mesuré : AR5200 60 FPS, `safe_read` ~10⁵ / 5 s (4·10⁸ avant).

Hors producteur : shader multi-slots (A–D = 4 identités sur une même WED) vérifié en jeu sur AR5200 (q0) ;
lave émissive procédurale route2 non qualifiée (non utilisée : q0) ; écume/art fixe peint dans le TIS de base (AR1600) non animé ;
surfaces ARE/BAM → timeline 30 FPS du pack d'animation, même durée.
