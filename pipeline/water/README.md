# Lot eau BG2EE

Autorités de phase 5. Les inventaires et plans générés ne valent ni QA, ni installation, ni release.

Reprise AR0204/AR1600 : [correctif installé et QA](AR0204_AR1600_REPAIR_20260912.md).
Sélection installée courante :
`manifests/ar0204-ar1600-validated-installed-20260912-v1.json` ; raccords RGB/WED corrigés,
AR0204/AR1600/AR0900 validés0.70, interpolation30FPS conservée.

Pilote égouts : [WTSEW AR0404/AR2100](WTSEW_AR0404_PILOT_20260912.md), validé ingame.
AR0404 utilise la chaîne complète à `q=0.70` ; AR2100 est validée dans son état exact actuel
(WED stock, overlay WTSEW partagé, route2 absente donc `q=0`).

Pilote marais : [WTSWAM AR1607/AR1800](WTSWAM_AR1607_AR1800_PILOT_20260912.md), première QA
rejetée (tuilage, transparence, mouvement). Correctif v2 installé : alpha natif100 AR1607,
raccords RGB des deux cartes, matériau marais plus contrasté, diagnostics par WED ; `q=0.70`.
V2/v3 rejetées sous pluie : variante `WTSWAMR` omise (palette6frames face au WED36frames).
[Reprise ressource pluie v4](WTSWAM_RAIN_RESOURCE_REPAIR_20260912.md) : paire sec/pluie
isolée `WSWPIL`/`WSWPILR`, x4/36phases et route2 q0.70 ; état installé validé par l'utilisateur.
Toute autre identité WTSWAM reste absente du registre et tombe à `q=0`.

| Fichier | Rôle |
|---|---|
| `family-policy-v1.json` | Familles, méthode SeedVR et gates voie1/route2 |
| `route2-registry-v1.json` | Entrées route2 approuvées ; absence/divergence = `q=0` |
| `../../engine/InfinityEngine-Enhancer/source-patchee/assets/water-route2/registry-v2.json` | Extension append-only consommée par le moteur |
| `manifests/wtlake-timeline30-q070-20260912-v1.json` | Lot WTLAKE 14 identités, 36 phases/15 Hz, blend 30 FPS, route2 `q=0.70` |
| `manifests/wtsew-ar0404-pilot-installed-20260912-v1.json` | Pilote WTSEW AR0404 installé, reçus assets/shaders/renderer, QA en attente |
| `manifests/wtsew-ar0404-ar2100-validated-20260912-v1.json` | Décision QA ingame : AR0404 full route2 validée, AR2100 fallback courant validé |
| `manifests/wtswam-ar1607-ar1800-pilot-installed-20260912-v1.json` | Installation initiale historique, rejetée par la QA suivante |
| `manifests/wtswam-ar1607-ar1800-rejected-20260912-v1.json` | Décision utilisateur et captures du rejet |
| `manifests/wtswam-ar1607-ar1800-repair-installed-20260912-v2.json` | Assets correctifs conservés ; renderer remplacé par v3 météo |
| `manifests/wtswam-weather-installed-20260912-v3.json` | Historique fpTone, rejeté en QA |
| `manifests/wtswam-rain-installed-20260912-v4.json` | Installation v4 : assets sec/pluie isolés, registre19, reçus immuables |
| `manifests/wtswam-ar1607-ar1800-validated-20260912-v1.json` | Sélection QA courante : les deux cartes v4 validées à q0.70 |
| `../scripts/orchestrate_water_batch.py` | Plan déterministe ; `--run` seul autorise l'exécution d'une étape supportée |
| `../scripts/build_wtlake_timeline_batch.py` | Assemble le candidat WTLAKE ; aucun SeedVR/build moteur/install/release implicite |
| `../scripts/build_wtsew_route2_pilot.py` | Produit le pilote AR0404 ; plan-only par défaut, exécution avec `--run` |
| `../scripts/build_wtswam_route2_pilot.py` | Produit le pilote AR1607/AR1800 ; plan-only par défaut, exécution avec `--run` |
| `../scripts/repair_wtswam_pilot.py` | Reprise du pilote rejeté depuis identités exactes ; nouveau run, plan-only sans `--run` |

Contrats :

- nouvelle inférence SeedVR du lot : `color_correction_method=none` ;
- artefacts témoins inchangés : AR0900 jour LAB, WTLAKE périodique wavelet ;
- voie 1 par lot : `route1-policy-v1.json` et `../scripts/build_water_route1_batch.py` ;
- raccords alpha secondaires confirmés : `../scripts/repair_water_secondary_alpha_seams.py` ;
- lots QA hors ligne : `../scripts/assemble_water_qa_batches.py` et `manifests/qa-batches-20260912-v1.json` ;
- voie1 avant route2 ;
- registre route2 exact, versionné, fail-closed ;
- le build moteur génère une table C++ depuis v2 et vérifie au démarrage les hashes TIS/PVRZ live ;
- aucune installation, reconstruction moteur, QA ou release dans l'orchestrateur de phase 5.
- le registre v3 WTLAKE expérimental est complet, exact et fail-closed ; AR0900 garde son ID parent.

Lot WTLAKE, plan puis assemblage explicite :

```powershell
python -B pipeline/scripts/build_wtlake_timeline_batch.py --output maps/water-batches/runs/<run-id>
python -B pipeline/scripts/build_wtlake_timeline_batch.py --output maps/water-batches/runs/<run-id> --run
```

Pilote WTSEW, plan puis production explicite dans un nouveau run :

```powershell
python -B pipeline/scripts/build_wtsew_route2_pilot.py --output maps/technical-overlays/WTSEW/runs/<run-id>
python -B pipeline/scripts/build_wtsew_route2_pilot.py --output maps/technical-overlays/WTSEW/runs/<run-id> --run
```

Pilote WTSWAM, plan puis production explicite dans un nouveau run :

```powershell
python -B pipeline/scripts/build_wtswam_route2_pilot.py --output maps/technical-overlays/WTSWAM/runs/<run-id>
python -B pipeline/scripts/build_wtswam_route2_pilot.py --output maps/technical-overlays/WTSWAM/runs/<run-id> --run
```

Plan complet en lecture seule :

```powershell
python -B pipeline/scripts/orchestrate_water_batch.py
```

Exécution future d'une étape supportée, après accord explicite :

```powershell
python -B pipeline/scripts/orchestrate_water_batch.py --stage preflight --run --run-id <nouveau-id>
```

`--run-id` doit être neuf. Un dossier existant est toujours refusé.
