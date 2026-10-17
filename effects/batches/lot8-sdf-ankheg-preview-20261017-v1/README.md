# Huit effets — adaptation SDF Ankheg / aperçu

- Retour utilisateur : SplineFit1 insuffisant ; chercher une formule antérieure validée, exemple Ankheg.
- QA acquise Ankheg : `sprite/index/qa-decisions/monster_ankheg/2026-10-04-accepted-full-ankheg-q3m-v9-sdf-stable-x2-catmullrom-v1.json` ; essai spline rejeté : fichier `2026-10-04-rejected-spline-fit1-q3m-x2-catmullrom-v1.json`.
- Référence de calcul réutilisée directement : `docs/measurements/q3m-ankheg-sdf-offline-x2-20261004-v1/sdf_trial.py` (`reconstruct`, `sdf_alpha`). Distance signée EDT ; sigma2 en grillex2, déplacement du champ borné±1 ; coeur2/voisinage3 pour petits éléments ; FG8/BG4 conservés aux centres x2 ; pad6 ; quantification1/16 ; intégration8×8.
- Adaptation x4 : masque nearest v2 réduit exactement d’un facteur2 vers la grillex2 ; formule originale, puis couverture à zoom2 et recadrage de la marge12x4. Équivalents sigma4/biais±2/coeur4/voisinage6 en pixelsx4. Les contraintes topologiques sont celles du champ x2, pas une garantie du nombre de composantes de tout seuil alpha rendu.
- Cause probable de l’essai spline peu convaincant : ajustement puis multiplication par le masque nearest, donc Anew≤Aold ; impossible de reconstruire la bordure hors escaliers. SDF autorise expansion/érosion locale bornée, avec matériau voisin pour ne pas créer un bord noir.
- RGB des pixels déjà couverts strictement conservé ; RGB extrudé depuis le premier plan uniquement dans les nouveaux pixels de bord (distance observée≤2x4). Opacité temporelle conservée comme enveloppe de matériau ; aucun modèle neuronal relancé.
- 8assets/404phases : `result.json`, `summary.json`, `assets/*.json`. Galerie `review/index.html` : alpha v2 /SplineFit1 v3 /SDF proposé, animation à durée inchangée, fonds, taille réelle et détails alpha.
- **Aperçu hors jeu uniquement** ; aucune autorité de production/sélection/QA/installation/release modifiée. Validation Ankheg non transférée aux8effets. Pas de registre V9/shader/moteur ajouté aux effets ; adaptation raster à zoom fixéx4.
- Recette : `python -B pipeline/recipes/effects-lot8-sdf-ankheg-preview-20261017-v1/preview.py` ; résultat final immuable.
