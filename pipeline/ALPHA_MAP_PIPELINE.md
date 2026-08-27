# Pipeline alpha — conservation des masques de zone

Ce pipeline est requis lorsque le préflight détecte des tuiles non opaques dans la primaire ou la
secondaire. L'alpha est un masque technique distinct du RGB : les pixels noirs peuvent être du
décor noir ou une transparence, donc aucune déduction ne doit être faite depuis leur couleur.

1. Conserver les deux rendus x1 et vérifier leur intégrité.
2. Upcaler le RGB uniquement ; ne jamais inclure l'alpha dans l'inférence.
3. Construire avec `build_upscaled_area.py` actuel : il restaure l'alpha de la source x1 sur les
   tuiles primaires et secondaires, puis adoucit **tous les masques non opaques** en bilinéaire.
   C'est le comportement par défaut, appliqué indifféremment aux rives, fontaines, huile, trous
   et silhouettes ; il remplace l'ancien lissage limité aux seules cellules liquides.
4. Garder le build en DXT5 (PVR `11`) dès qu'une zone porte un alpha non opaque.
5. Compter les familles d'alpha du build (opaque, transparent, graduel) avant la QA.

Si le bilinéaire global demeure visiblement crénelé, un essai contrôlé peut ajouter un flou
gaussien léger sur tous les masques avec `--alpha-contour-feather 0.25`. Ce rayon est exprimé en
pixels x1 ; commencer à `0.25`, ne l'augmenter qu'après comparaison en jeu et conserver un build
sans feather comme point de retour.

Si ce feather reste sans effet parce que l'escalier est géométrique, ne pas augmenter le flou à
l'aveugle : suivre la correction post-build
[`GEOMETRIC_ALPHA_MASK_CLEANUP.md`](GEOMETRIC_ALPHA_MASK_CLEANUP.md). Elle reconstruit les
masques primaire et secondaire sur le canvas WED, lisse leur forme, puis ne modifie que l'alpha.

Si cette correction suit encore trop les gros pixels d'origine, l'essai spline
explicitement demandé est décrit dans
[`SPLINE_ALPHA_MASK_PIPELINE.md`](SPLINE_ALPHA_MASK_PIPELINE.md). Il reste séparé
du build standard et ne s'installe jamais automatiquement.

Si un overlay liquide est présent, [WATER_MAP_PIPELINE.md](WATER_MAP_PIPELINE.md) remplace cette
procédure générale pour les règles de contour et de réutilisation d'overlay.
