# AR3017 — plan de recettes animation

Statut : plan uniquement ; aucun upscale, interpolation, masque, pack ou installation lancé.

## Décisions communes

- Spatial génératif : `SeedVR2 7B INT8/LAB x4`, padding `32 px x1`, sauf indication contraire.
- Temporel : `TimedTimeline v2 Apollo-8`, `15 → 30 fps`, couture dernière → première.
- RGB transparent d'entrée Apollo : `nearest-opaque-dilate` pour les BAM à chroma vert ; alpha traité séparément.
- Conserver dimensions logiques, centres, cycles, séquences et lookups BAM.
- Aucun `collapse-uniform-duplicate-holds` : A–D ont plusieurs cycles incompatibles avec une condensation globale ; `AMSTEAM2` contient des répétitions intentionnelles non uniformes.
- `Blended` : prémultiplier le RGB dès qu'un masque/fade crée un alpha intermédiaire.
- Flou RGB : aucun par défaut. SeedVR couvre le lissage spatial ; un flou supplémentaire détruirait les détails mécaniques/liquides. Seule exception conditionnelle : `FIRE_2B`, sigma `0,45` au plus si Apollo crée des franges, selon le précédent `FOUNT1`.

## Matrice complète

| Assets | Type / preuve | Upscale | Interpolation | Masque / fade | RGB final | Recette retenue |
|---|---|---|---|---|---|---|
| `AM3017A–D` | Quatre grands fragments rigides de la machine ; alpha stable, géométrie uniforme, 4 cycles identiques entre resrefs | SeedVR2 7B/LAB x4 | Apollo-8 direct par lookup ; cycles 1/14/6/28 slots → 2/28/12/56 phases ; maintiens conservés | Alpha source nearest ; **aucun** spline, feather, fade canvas ou flou | Non-Blended : RGB droit ; hidden RGB nearest-opaque | `MECANIQUE-SEEDVR-ALPHA-NATIVE` |
| `AM3017E–H` | Roues/poulies rigides 50–72 px ; 8 poses, 1 cycle | SeedVR2 7B/LAB x4 | Apollo-8 direct, 8 → 16 phases | Alpha source nearest ; aucun spline/feather/fade/flou | Non-Blended : RGB droit ; hidden RGB nearest-opaque | `MECANIQUE-SEEDVR-ALPHA-NATIVE` ; précédent `AM307TT1`, `AM3016P/Q/R` |
| `AM3017Z` | Surface liquide large, 2 composantes stables, 10 poses | SeedVR2 7B/LAB x4 | Apollo-8 direct, 10 → 20 phases | Spline Fit 1 multi-contours par frame, padding 32, spacing 1,5, supersample 4, feather intérieur `4 px x4` ; pas de fade canvas | Non-Blended : `rgb-policy preserve` | `LIQUIDE-SEEDVR-SPLINE4` ; précédent `AM3021D/E/F` |
| `AMSTEAM1` | Vapeur diffuse Blended, 24 géométries, 1–5 composantes | SeedVR2 7B/LAB x4 | Apollo-8 direct, 24 → 48 phases | Spline Fit 1 multi-contours par frame + feather `4 px x4` + Oval Edge Fade `20/6` | Prémultiplier par alpha final | `FUMEE-SEEDVR-SPLINE4-EDGEFADE` ; précédent `CHIMSMK` |
| `AMSTEAM2` | Vapeur diffuse Blended, 24 géométries, 4 cycles avec répétitions centrales intentionnelles | SeedVR2 7B/LAB x4 | Apollo-8 direct sans condensation ; 24/33/51/60 slots → 48/66/102/120 phases | Spline Fit 1 multi-contours par frame + feather `4 px x4` + Oval Edge Fade `20/6` | Prémultiplier par alpha final | `FUMEE-SEEDVR-SPLINE4-EDGEFADE` ; précédent `CHIMSMK` |
| `FIRE_2B` | Feu Blended 70×70 ; 15 poses ; alpha source **100 % opaque** : le contour/aura standard est inapplicable | SeedVR2 7B/LAB x4, pas xBR : sujet large et texturé | Apollo-8 direct, cycle actif 15 → 30 phases ; supprimer seulement les 4 cycles terminaux vides | Reconstruire une rampe alpha depuis le fond noir (`luminance-low/high`, base provisoire `0/16`, à mesurer sur le x4), puis fade canvas `8 px x4`; pas de spline | Prémultiplier par alpha final ; RGB nul sous alpha nul | Adaptation `fire-seedvr7b-x4-dark-background-fade`, fondée sur `FIRE_3/FIRE_4` et la règle luminance des corrections alpha |
| `AMWRPGT1` | Portail partagé ; recette existante déjà rendue correctement dans AR3016 | **Réutiliser les octets existants**, ne pas ré-upscaler | Réutiliser le run 12 → 24 phases | Safe Boundary `8/6` + Gaussian `3`, déjà inclus | Non-Blended : RGB inchangé | `amwrpgt1-timeline30-apo8-safe8x6-gauss3-20260906` |

## Points de contrôle avant production

- `AM3017A/C` : leurs emprises se touchent exactement à `y=1965`. Vérifier la couture RGB assemblée après SeedVR ; appliquer `build_joint_animation_rgb_seam.py` seulement si une jointure devient visible. Ne pas modifier l'alpha rigide.
- `AM3017A–D` : vérifier chaque cycle séparément ; le cycle 3 porte des maintiens doublés volontaires.
- `AMSTEAM1/2` : vérifier fond clair/sombre, disparition aux bords et addition des paires co-localisées ; ne pas fusionner les deux ressources.
- `FIRE_2B` : valider la rampe luminance sur les 15 ancres et les 15 phases Apollo. Si `0/16` mange les flammes rouges sombres, réduire `high`; si un carré subsiste, augmenter uniquement le fade canvas. Le flou RGB `sigma 0,45` reste un correctif conditionnel, jamais automatique.
- `AMWRPGT1` : les assets du pack AR3016 sont byte-identiques au run `amwrpgt1-timeline30-apo8-safe8x6-gauss3-20260906`. Le liseré cyan connu vient du PVRZ BC1 de la map, pas de l'animation ; aucun correctif alpha/RGB supplémentaire.
- Pack final AR3017 : état complet des 13 resrefs. `FIRE_2B` est aussi utilisé par `OH8100`; une validation globale du resref exigera une QA séparée dans cette zone.

## Références

- `animations/ANIMATION_RECIPE_CATALOG.md`
- `pipeline/ANIMATION_UPSCALE_PIPELINE.md`
- `pipeline/ANIMATION_UPSCALE_30FPS_V2.md`
- `pipeline/ANIMATION_SMALL_SUBJECT_XBR2_30FPS.md`
- `pipeline/ANIMATION_PER_FRAME_SPLINE_ALPHA_30FPS_V2.md`
- `pipeline/ANIMATION_ALPHA_CORRECTIONS.md`
- `pipeline/ANIMATION_BLENDED_RGB_NEUTRALISATION.md`
- `animations/index/animation_upscale_registry.csv`
- `animations/index/animation_alpha_corrections.csv`
