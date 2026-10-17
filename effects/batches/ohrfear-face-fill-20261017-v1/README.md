# OHRFEAR — trou central comblé

- Retour utilisateur :12corrigé, lot26validé ; [acceptation finale](../lot26-accepted-20261017-v1/acceptance.json). Preuves de production historiques inchangées.

- Demande : «12 : une transparence au milieu du visage à supprimer».
- Parent `ohrfear-apollo30-retimed-strict-20261017-v1` ; nouveau run `ohrfear-apollo30-facefill-20261017-v1`, pack `ohrfear-7b-x4-apollo30-facefill-20261017-v1`.
- Comblement des petits trous enclavés au centre de la bouche avant interpolation alpha/feather12 ; ROI sourcex1=[35,38,55,58], surface≤256pixelsx4 par trou. Contours externes/autres trous conservés exactement ; RGB des pixels déjà visibles identiques ; nouveaux pixels par extension du matériau opaque proche.
-90phases/3s, géométrie/carrier/timing identiques ; unicité RGB/RGBA conservée. Aucune inférence, aucun changement sur les8SDF.
- `production.json` : trous natifs et pixels modifiés par phase ; `comparison.png` : avant/après phases20/45/60. QA ingame en attente.
- Recette `pipeline/recipes/effects-lot26-face-visibility-20261017-v1/repair.py` ; installation distincte `effects/installations/lot26-face-visibility-20261017-v1/installation.json`.
