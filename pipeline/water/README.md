# Lot eau BG2EE

Autorités de phase 5. Les inventaires et plans générés ne valent ni QA, ni installation, ni release.

Reprise AR0204/AR1600 : [correctif installé et QA](AR0204_AR1600_REPAIR_20260912.md).
Sélection installée courante :
`manifests/ar0204-ar1600-validated-installed-20260912-v1.json` ; raccords RGB/WED corrigés,
AR0204/AR1600/AR0900 validés0.70, interpolation30FPS conservée.

| Fichier | Rôle |
|---|---|
| `family-policy-v1.json` | Familles, méthode SeedVR et gates voie1/route2 |
| `route2-registry-v1.json` | Entrées route2 approuvées ; absence/divergence = `q=0` |
| `../../engine/InfinityEngine-Enhancer/source-patchee/assets/water-route2/registry-v2.json` | Extension append-only consommée par le moteur |
| `manifests/wtlake-timeline30-q070-20260912-v1.json` | Lot WTLAKE 14 identités, 36 phases/15 Hz, blend 30 FPS, route2 `q=0.70` |
| `../scripts/orchestrate_water_batch.py` | Plan déterministe ; `--run` seul autorise l'exécution d'une étape supportée |
| `../scripts/build_wtlake_timeline_batch.py` | Assemble le candidat WTLAKE ; aucun SeedVR/build moteur/install/release implicite |

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

Plan complet en lecture seule :

```powershell
python -B pipeline/scripts/orchestrate_water_batch.py
```

Exécution future d'une étape supportée, après accord explicite :

```powershell
python -B pipeline/scripts/orchestrate_water_batch.py --stage preflight --run --run-id <nouveau-id>
```

`--run-id` doit être neuf. Un dossier existant est toujours refusé.
