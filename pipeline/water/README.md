# Lot eau BG2EE

Autorités de phase 5. Les inventaires et plans générés ne valent ni QA, ni installation, ni release.

| Fichier | Rôle |
|---|---|
| `family-policy-v1.json` | Familles, méthode SeedVR et gates voie1/route2 |
| `route2-registry-v1.json` | Entrées route2 approuvées ; absence/divergence = `q=0` |
| `../scripts/orchestrate_water_batch.py` | Plan déterministe ; `--run` seul autorise l'exécution d'une étape supportée |

Contrats :

- nouvelle inférence SeedVR du lot : `color_correction_method=none` ;
- artefacts témoins inchangés : AR0900 jour LAB, WTLAKE périodique wavelet ;
- voie1 avant route2 ;
- registre route2 exact, versionné, fail-closed ;
- aucune installation, reconstruction moteur, QA ou release dans l'orchestrateur de phase 5.

Plan complet en lecture seule :

```powershell
python -B pipeline/scripts/orchestrate_water_batch.py
```

Exécution future d'une étape supportée, après accord explicite :

```powershell
python -B pipeline/scripts/orchestrate_water_batch.py --stage preflight --run --run-id <nouveau-id>
```

`--run-id` doit être neuf. Un dossier existant est toujours refusé.
