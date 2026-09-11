# Corrections alpha des animations BAM

Une correction alpha dérive un nouveau run et ne peut qu'abaisser l'alpha. RGB, géométrie,
timeline et run source restent inchangés.

Avant toute correction, vérifier le flag ARE `Blended`. Si le défaut vient du RGB visible sous
alpha nul, suivre [`ANIMATION_BLENDED_RGB_NEUTRALISATION.md`](ANIMATION_BLENDED_RGB_NEUTRALISATION.md).

## Choix

| Défaut | Outil |
|---|---|
| Bord dur de silhouette | `build_alpha_feather.py --inner-radius-x4` |
| Rectangle du canvas | `--canvas-radius-x4` ; `--canvas-edges top right left` pour préserver le bas ; `--canvas-bottom-radius-x4` pour y conserver un fondu distinct |
| Fond sombre distinct du sujet | `--luminance-low` + `--luminance-high` |
| Halo ovale | `--radial-outer-x-x4`, `--radial-outer-y-x4` |
| Foyer `Blended` : contour fondu + halo borné | `build_animation_contour_aura_pack.py` ; paramètres FPIT1S : 12 / sigma 5 / gain 0,9 / marge 14, RGB opaque le plus proche dans le halo puis prémultiplié |
| Raccord haut binaire / ilots de pixels | `--top-gaussian-sigma-x4` + `--top-gaussian-full-height-x4` |
| Contours Fit 1 + raccord haut reconstruit | `build_spline_top_reconstructed_alpha.py` |
| Masque peint | `build_manual_alpha_mask_30fps_v2.py` |
| Trajectoire crénelée | [`SPLINE_ALPHA_MASK_PIPELINE.md`](SPLINE_ALPHA_MASK_PIPELINE.md) |

Ne cumuler que des corrections justifiées par une comparaison ciblée.

## Production

```powershell
python pipeline/scripts/build_alpha_feather.py `
  --resref <RESREF> --run <run-source> --output-run <nouveau-run> `
  --inner-radius-x4 <rayon>

# Flou gaussien local : alpha seulement, zone haute puis raccord vertical.
python pipeline/scripts/build_alpha_feather.py `
  --resref <RESREF> --run <run-source> --output-run <nouveau-run> `
  --top-gaussian-sigma-x4 <sigma> `
  --top-gaussian-full-height-x4 <hauteur-exclusive> `
  --top-gaussian-transition-x4 <hauteur-raccord>

# Silhouette principale Fit 1, puis remplacement 2D de la bande haute.
python pipeline/scripts/build_spline_top_reconstructed_alpha.py `
  --resref <RESREF> --run <run-source> --output-run <nouveau-run> `
  --fit-error 1.0 --sample-spacing 1.5 --supersample 4 --padding-x4 32 `
  --top-gaussian-sigma-x4 <sigma> --top-height-x4 <hauteur-exclusive> `
  --top-left-x-x4 <x-gauche> --top-minimum-alpha <seuil>

python pipeline/scripts/build_manual_alpha_mask_30fps_v2.py `
  --temporal-run <run-30fps> --resref <RESREF> `
  --mask <masque.png> --run <nouveau-run>
```

Les identifiants de sortie sont routés sous
`animations/ressources/<RESREF>/runs/<run-id>/`; plusieurs resrefs utilisent
`animations/batches/<run-id>/`. `--output` et `--runs-root` restent des échappatoires de reprise
legacy. Le builder refuse d'écraser la sortie.

## Gates

- `alpha_final <= alpha_source` pour chaque pixel ;
- flou gaussien : aucune expansion hors silhouette ; `full-height + transition <= hauteur frame` ;
- reconstruction spline + bande haute : l'alpha peut occuper des trous de la région explicitement
  bornée ; comparaison PNG/RGBA obligatoire avant installation ;
- RGB byte pour byte identique, sauf passage explicite par le pipeline `Blended` ;
- dimensions, centres, frames, cycles et timeline inchangés ;
- comparaison vidéo puis QA ingame explicite ;
- correctif accepté enregistré dans `animations/index/animation_alpha_corrections.csv` ;
- composition et installation via un nouveau pack, jamais copie manuelle de `.rgba`.

Un correctif techniquement sain reste `pending-qa` jusqu'à la décision utilisateur.
