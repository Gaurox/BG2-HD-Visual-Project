# Préflight d'une zone — routeur extensible

À lancer **avant toute inférence** et avant de choisir l'échelle. Le préflight lit les ressources
du jeu, ne modifie rien et écrit un manifeste de décision attaché au run :

```powershell
python pipeline/scripts/audit_area_preflight.py ARxxxx <run>/00_preflight/ARxxxx-preflight.json
```

Ne poursuivre que si `blockers` est vide. Lire ensuite, dans l'ordre, tous les documents marqués
`required` dans `routes`. Le manifeste est la preuve de la classification utilisée ; il évite que
la mémoire d'un cas particulier devienne une règle implicite.

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

Le contrôle d'intégrité des maîtres x1 reste ensuite obligatoire :

```powershell
python pipeline/scripts/validate_x1_masters.py --area ARxxxx
```

## Règle d'extension

Une future méthode s'ajoute en trois éléments atomiques :

1. une condition factuelle et sérialisée par `audit_area_preflight.py` ;
2. une ligne dans la table ci-dessus qui pointe vers son document d'entrée ;
3. un document de procédure atteignable depuis ici et depuis `pipeline/README.md`.

Tant que le document n'a pas de critère de passage et de référence validée, la route est marquée
`validation-required` et devient un bloqueur. Aucun agent ne doit combler ce vide en appliquant
une recette voisine.
