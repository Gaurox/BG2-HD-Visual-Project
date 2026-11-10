# Planche animée lot31 —2026-10-19

- Demande :3versions animées directement pour tous les effets ; remplacer les vignettes fixes de l'index8794.
- `python -B pipeline/recipes/effects-lot31-animated-board-20261019-v1/build.py` : réutilise `review/{catalog,data,images}`, calcule cadrages communs depuis les alphas natifs+marge20px ; aucune inférence/phase/RGBA/index de production/install modifié.
- Sortie sous `effects/batches/lot31-corrections-preview-20261018-v1/review/` : `animated-v1.html`, `index.html`, `board-bounds.json`, `animated-board.json`. Ancien index conservé `index-static-v1.html`. Recette corrective précédente/hashés intacts.
-31cartes×3canvas,99palettes sélectionnables ; vanilla15/précédent30/corrigé30 sur même horloge/cadrage. Cycles/modes/palettes/mélange en ligne, pause/reprise/phase par carte ; commandes globales pause/restart/vitesse/fond/alpha.30/31 boucle par défaut.
- Lecture dans le viewport, six chargements simultanés, LRU images décodées256Mio. Pas de conversion vidéo/WebP ni perte d'alpha/durée.
- URL : `http://127.0.0.1:8794/?v=animated31`. Fiche détaillée précédente conservée.
