# Pipeline cartes

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

`areas.csv` est l'autorité pour l'état d'une carte, le run et le build retenus. Les dossiers de run,
captures et projections ne permettent aucune promotion implicite.

## Parcours courant

| Étape | Commande ou autorité |
|---|---|
| Maître x1 | `python pipeline/scripts/validate_x1_masters.py --area ARxxxx` |
| Préflight | `python pipeline/scripts/audit_area_preflight.py ARxxxx <rapport.json>` |
| Audit eau | `python pipeline/scripts/audit_water_area.py ARxxxx <rapport.json>` |
| Exécution SeedVR | `python pipeline/scripts/run_seedvr_comfyui.py ...` |
| Reconstruction | `python pipeline/scripts/build_upscaled_area.py ARxxxx <principale-x4.png> <build-dir> [secondaire-x4.png]` |
| Audit technique | `python pipeline/scripts/verify_upscaled.py ARxxxx <build-dir> <principale-x4.png>` |
| Installation/retour arrière | `python pipeline/scripts/inject_build.py ...` |
| État métier | édition explicite de `areas.csv` après décision QA |

Pour les entrées `argparse`, consulter l'aide avant un run :

```powershell
python pipeline/scripts/run_seedvr_comfyui.py --help
```

Les anciens splitters manuels sont archivés ; ils ne doivent pas être réintroduits dans le parcours
courant.

## Contrats

- La recette et les entrées d'un run sont figées avant exécution.
- Les sorties techniques sont contrôlées avant toute installation.
- Le jeu et InfinityLoader sont fermés avant `inject_build.py install` ou `restore`.
- Une installation vérifiée ne vaut ni QA ni intégration release.
- Les overlays de release suivent `overlay-sources.json`; voir l'ambiguïté WTLAVA-D dans
  [`PROBLEMES_A_RESOUDRE.md`](PROBLEMES_A_RESOUDRE.md).
- Les chemins machine sont résolus par `config://...` et `WorkspacePaths.ps1`/`workspace_paths.py`.

## Installation transactionnelle

```powershell
python pipeline/scripts/inject_build.py install ARxxxx <build-dir> --verify-only
python pipeline/scripts/inject_build.py install ARxxxx <build-dir>
python pipeline/scripts/inject_build.py verify <backup-dir>
python pipeline/scripts/inject_build.py restore <backup-dir>
```

Le dossier exact de sauvegarde et les hashes sont produits par le script ; ne pas maintenir une
seconde procédure de copie manuelle dans la documentation.

## Mise à jour des projections

Préparer sans exécuter :

```powershell
python pipeline/scripts/workspace.py refresh --changed
```

Demander ensuite « scopes ciblés / toutes / aucune ». Exécuter seulement avec les `--scope`
proposés et `--run`; voir [`../docs/WORKSPACE_INTEGRITY.md`](../docs/WORKSPACE_INTEGRITY.md).

## Guides spécialisés

| Besoin | Document |
|---|---|
| Qualification | [`AREA_PREFLIGHT.md`](AREA_PREFLIGHT.md) |
| Variantes jour/nuit | [`DAY_NIGHT_MAP_PIPELINE.md`](DAY_NIGHT_MAP_PIPELINE.md) |
| Découpe selon dimensions | [`MAP_SPLITTING_POLICY.md`](MAP_SPLITTING_POLICY.md) |
| Eau | [`WATER_MAP_PIPELINE.md`](WATER_MAP_PIPELINE.md) |
| Liquides et overlays | [`OTHER_LIQUID_MAP_PIPELINE.md`](OTHER_LIQUID_MAP_PIPELINE.md) |
| Alpha | [`ALPHA_MAP_PIPELINE.md`](ALPHA_MAP_PIPELINE.md) |
| Tuiles secondaires | [`SECONDARY_TILE_PIPELINE.md`](SECONDARY_TILE_PIPELINE.md) |
| Masques polygonaux | [`GEOMETRIC_ALPHA_MASK_CLEANUP.md`](GEOMETRIC_ALPHA_MASK_CLEANUP.md) |
| Masques spline | [`SPLINE_ALPHA_MASK_PIPELINE.md`](SPLINE_ALPHA_MASK_PIPELINE.md) |
| Référence Topaz | [`TOPAZ_GIGAPIXEL_CLI_REFERENCE.md`](TOPAZ_GIGAPIXEL_CLI_REFERENCE.md) |
| Animations | [`ANIMATION_UPSCALE_PIPELINE.md`](ANIMATION_UPSCALE_PIPELINE.md) |
| Vidéos | [`VIDEO_UPSCALE_PIPELINE.md`](VIDEO_UPSCALE_PIPELINE.md) |
| Interpolation vidéo | [`VIDEO_INTERPOLATION_PIPELINE.md`](VIDEO_INTERPOLATION_PIPELINE.md) |
| Scripts disponibles | [`scripts/README.md`](scripts/README.md) |

## Tests légers

```powershell
python pipeline/scripts/test_changed.py --targeted
```

La commande planifie sans exécuter. Une modification maps cible les modules maps, jamais les tests
sprites. Après le choix obligatoire « ciblés / tous / aucun », utiliser respectivement
`--targeted --run`, `--full --run`, ou ne rien lancer. Voir
[`../docs/TEST_SELECTION.md`](../docs/TEST_SELECTION.md).

Ne pas lancer SeedVR, Topaz, un build complet ou un packaging pour une modification documentaire.
