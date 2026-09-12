# Préflight d'une zone — routeur extensible

Routeur local à utiliser avant une nouvelle inférence SeedVR lorsque la structure de la zone n'est
pas déjà qualifiée. Il lit les ressources du jeu, ne modifie rien et écrit la décision dans le run :

```powershell
python pipeline/scripts/audit_area_preflight.py ARxxxx <run>/00_preflight/ARxxxx-preflight.json
```

Pour une inférence qui consomme ce manifeste, `blockers` doit être vide. Consulter seulement la
route liée au problème rencontré ; la liste `required` indexe des recettes, pas un ordre de lecture.

`run_seedvr_comfyui.py` exige ce manifeste avec `--preflight` et refuse de soumettre une
inférence lorsque le rapport est bloquant, y compris pour la seconde variante avec `--append`.

## Décisions produites

| Détection | Preuve dans le manifeste | Procédure à suivre |
|---|---|---|
| Toujours | `core-upscale` | [UPSCALE_MAP_PIPELINE.md](UPSCALE_MAP_PIPELINE.md) |
| Alpha non opaque en primaire ou secondaire | `alpha-<variante>` | [ALPHA_MAP_PIPELINE.md](ALPHA_MAP_PIPELINE.md) |
| Au moins une cellule avec tuile secondaire | `secondary-<variante>` | [SECONDARY_TILE_PIPELINE.md](SECONDARY_TILE_PIPELINE.md) |
| Overlay liquide WED, y compris `WTSWAM`, `WTSEW` et `WTOIL` | `water-<variante>` | [WATER_MAP_PIPELINE.md](WATER_MAP_PIPELINE.md) |
| Overlay `WT*`/`YS*` non classé eau | `other-liquid-<variante>` | [OTHER_LIQUID_MAP_PIPELINE.md](OTHER_LIQUID_MAP_PIPELINE.md) — bloque jusqu'à validation |
| WED `ARxxxxN` présent | `day-night` | [DAY_NIGHT_MAP_PIPELINE.md](DAY_NIGHT_MAP_PIPELINE.md) |

Contrôler les maîtres x1 lorsqu'une nouvelle inférence les consomme ou lorsque leur identité est
incertaine :

```powershell
python pipeline/scripts/validate_x1_masters.py --area ARxxxx
```

## Règle d'extension

Une future méthode peut s'ajouter en trois éléments :

1. une condition factuelle et sérialisée par `audit_area_preflight.py` ;
2. une ligne dans la table ci-dessus qui pointe vers son document d'entrée ;
3. un document de procédure atteignable depuis ici et depuis `pipeline/README.md`.

Une route inconnue peut rester `validation-required` pour bloquer uniquement l'inférence concernée.
Elle ne bloque ni une correction locale indépendante, ni l'acceptation d'un build déjà qualifié.
