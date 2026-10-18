# SPDEATH3 — nouveau comparatif Bézier/alpha continu

- Retour : le SDF garde des contours pixelisés sur certaines phases. **Nouvel aperçu seulement**, source et installation conservées ; aucune QA acquise.
- [`result.json`](result.json), [`summary.json`](summary.json), [`comparatif animé`](review/index.html), [`vue entière`](review/full-comparison.png), [`détail phase19`](review/detail.png). Trois vues synchronisées : installé / ancien SDF / Bézier+alpha continu.
-30masques natifs vectorisés Potrace1.334/opttol0.1/turdsize0, rasterisation x4 SS8 ; puis mélange des masques lissés par les fractions temporelles originales.124phases,2profils62phases/2.066667s. Reconstruction de l'ancienne interpolation alpha exacte avant remplacement ; aucun nearest/enveloppe de l'ancien masque ne rebloque le nouveau contour.
- RGB existants visibles et timing inchangés ; extension de matériau sur nouveaux bords≤4x4. Alpha gradué présent sur124/124phases (minimum206pixels) ; composantes source toutes encore couvertes, pas de promesse sur le nombre de composantes à tous les seuils.
- Arrondi plus marqué : masse alpha93.22–100.05% selon phase, aucun inset imposé ; certains détails de silhouette peuvent varier. Source seule inchangée plutôt que forcer une conservation de support qui recrée les escaliers.
- Marge commune4x4 uniquement pour l'aperçu224×384 ; carrier/centres installés inchangés. Si installation demandée, produire une dérivation distincte avec géométrie adaptée. Source/production/QA/install/release actuelles conservées ; dernier `Z33T33` reste témoin installé.
- [`Recette`](../../../pipeline/recipes/effects-spdeath3-bezier-preview-20261018-v1/README.md). Ancien aperçu `../spdeath3-sdf-ankheg-preview-20261018-v1/` conservé.
