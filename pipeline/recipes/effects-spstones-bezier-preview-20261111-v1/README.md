# SPSTONES — comparaison de contours, aperçu autonome

- Commande : `python -B pipeline/recipes/effects-spstones-bezier-preview-20261111-v1/preview.py`.
- Sortie nouvelle uniquement : `effects/batches/spstones-bezier-preview-20261111-v1/{index.html,comparison.webp,contact-sheet.jpg,result.json}`.
- Base : `spstones-apollo30-retimed-strict-20261017-v2` ; 35 poses natives 175–209, 70 phases, 30 FPS, 7/3 s. RGB droits lus dans les compagnons `*-straight.rgba`.
- Trois vues synchronisées : actuelle / Potrace Bézier seul / Bézier + fondu alpha local sigma0.5–1px x4 adapté à l'épaisseur. Potrace alphamax1.334, opttolerance0.1, turdsize0, SS8/BOX, sans intersection avec ancien support nearest. Tracé avant mélange temporel ; fractions existantes conservées.
- Canevas commun, marge transparente16px x4 pour aperçu ; couleurs nouvelles extrudées du premier plan voisin. Couleurs visibles existantes conservées.
- Contrôles : reconstruction exacte des70alphas actuels ; aucune composante native entièrement perdue ; bord du canevas transparent ; hashes BAM source, manifeste de production, manifeste installé et carrier installé inchangés quand présents.
- Aucun pack/carrier, changement de sélection/QA, installation ou release. `index.html` autonome : lecture/pause, phase, fond, alpha seul, zoom. WebP à cadence moyenne30FPS (horodatages milliseconde).
- Réemploi : `effects-spdeath3-bezier-preview-20261018-v1` et `effects-lot31-corrections-20261018-v1/masks.py`. Validation visuelle SPSTONES encore à obtenir.
