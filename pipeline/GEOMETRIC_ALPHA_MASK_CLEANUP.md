# Nettoyage géométrique d'un alpha de carte

Correction post-build pour un contour qui reste en escalier après restauration et lissage normal
de l'alpha. Elle n'est jamais automatique. Si le flou conserve la trajectoire en marches, utiliser
la variante spline : [`SPLINE_ALPHA_MASK_PIPELINE.md`](SPLINE_ALPHA_MASK_PIPELINE.md).

## Invariants

- Partir d'un build DXT5 techniquement valide et créer un nouveau run/build.
- Préserver RGB, TIS, ordre des tuiles et layout d'atlas.
- Reconstruire le canvas complet ; ne pas filtrer tuile par tuile.
- Traiter primaire et secondaire séparément.
- Ne jamais déduire l'alpha depuis du RGB noir ni modifier l'overlay global.
- Refuser le prototype si une tuile est réutilisée à plusieurs positions avec un résultat différent.

## Recette

```text
alpha > 127 ? 255 : 0
→ GaussianBlur(sigma)
→ alpha > 127 ? 255 : 0
→ érosion ou dilatation opaque facultative
```

Le résultat reste binaire. Une érosion agrandit la transparence ; une dilatation la réduit. Ne
changer qu'un paramètre par essai.

Référence AR0604, conservée comme point de comparaison : seuil `127`, sigma `3` px x4, érosion
opaque `2` px x4. Le prototype reproductible reste scellé avec son run :

```powershell
python maps/AR0604/runs/ar0604-geometric-alpha-sigma3-20260823/build_geometric_alpha_sigma3.py `
  <build-reference> <nouveau-build> --sigma 3 --opaque-erosion-x4 2
```

Ce script est une preuve locale, pas un outil générique du pipeline.

## Validation

```powershell
python pipeline/scripts/verify_upscaled.py `
  ARxxxx <nouveau-build> <rendu-primaire-x4.png>
python pipeline/scripts/inject_build.py install ARxxxx <nouveau-build> --verify-only
```

Exiger `0 OOB`, tuiles x4, DXT5, RGB inchangé et provenance complète. Après prévalidation, installer
avec `inject_build.py install`, conserver le reçu, tester chaque état WED en jeu, puis restaurer au
besoin avec `inject_build.py restore <backup-dir>`. L'état dans `areas.csv` ne change qu'après QA
explicite.
