# Nuées — essai de particules individuelles,2026-10-27

- Demande : chaque insecte apparaît comme un carré, car alpha natif agrandi nearest4. Reprendre chaque pixel natif visible en point antialiasé, préserver SeedVR RGB et les phases Apollo.
- `result.json` :3assets `SPIPLAAI`/alias `SPIPLARI`, `SPIPLAUI`, `SPINSECT` ;4cycles bouclés,196phases,2variantes. Anciennes ressources, QA, installation et release inchangées. Aperçu [8797](http://127.0.0.1:8797/).
- `arrondi` : rayon1.60±0.11px x4 ; `affine` :1.15±0.11px x4. Couverture de cercle par suréchantillonnage8×8 dans chaque cellule4×4 ;16variations de taille/position déterministes par coordonnées de toile, identiques au fil du temps. Aucun flou global ou nouvelle inférence.
- Alpha temporel inchangé par cellule avant modulation : vérifier la constance4×4, puis multiplier par le masque de point. Chaque cellule native active conserve une couverture non nulle ; RGB préservé exactement sur les pixels conservés ; aucune extension hors alpha initial. Marge de visualisation8px x4, position native inchangée.
- Masses alpha : variante arrondie ≈50%, fine ≈26% de la source ; chaque cellule conserve un point mais la nuée devient moins opaque. À juger en animation et ingame avant toute sélection.
- Base temporelle héritée 15→30fps ; durées16/15s,12/15s,56/15s et14/15s pour les4cycles. 15fps de compatibilité pour `SPIPLAUI`/`SPINSECT` ; cadence native en jeu non mesurée. Pas de suivi d'identité d'un insecte d'une frame à l'autre : variation fixée aux coordonnées, vérifier scintillement et trame en mouvement.
- Expérience précédente rejetée : `insectes-contours-preview-20261027-v1` lissait le masque global ; elle n'est pas ce traitement par point. Recette `pipeline/recipes/effects-insectes-particules-20261027-v1/preview.py`.
