# Huit effets — SDF resserré / aperçu

- Demande : SDF mieux apprécié ; resserrer le masque pour cacher les liserés, refaire un test.
- Comparatif : SDF actuel /retrait1pxx4 /retrait2pxx4, soit0 /0,25 /0,5pixel natif. 8assets×404phases par variante ; même géométrie/RGB/timings.
- Formule : couverture8×8 du signe de `bilinear(SDF_x2 - retrait_x4/2)` ; soustraction du champ AVANT intégration, sans fondu supplémentaire. SDF Ankheg identique au test précédent. Monotonie A2≤A1≤A0 vérifiée sur chaque phase ; SHA RGBA du témoin0 exact par rapport à l’aperçu précédent.
- Source v2 +SDF de `lot8-sdf-ankheg-preview-20261017-v1`, aucun nouveau modèle. Comparatif WebP RGBA sans perte, fonds et taille réelle ; détails alpha.
- Résultats : `result.json`, `summary.json`, `assets/*.json`. Le retrait amincit réellement : masse alpha moyenne TRAPGR73% à1px/49% à2px ; TRSPEART58%/43%, 1phase complètement effacée dans les2variantes. SPHANDAT : 1phase effacée à2px seulement. Petits îlots SPHEART/SPHANDAT/SPRAISED supprimés par l’érosion ; aucune protection silencieuse ajoutée qui fausserait la distance demandée.
- Aperçu seulement ; aucune autorité de production, QA, installation ou release modifiée. Pas d’acceptation ingame déduite du retour positif sur le SDF.
- Recette : `pipeline/recipes/effects-lot8-sdf-inset-preview-20261017-v1/preview.py`. Galerie8788 ; témoin SDF précédent8787 conservé.
