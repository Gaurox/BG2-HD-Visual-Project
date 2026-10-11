# FLM2PUR / OH4210 / PLT_PURP — essais de contour, 2026-10-11

- Demande : contours pixélisés dans OH4210, screenshot `E:/Steam/userdata/5536307/760/remote/257350/screenshots/20261011162646_1.jpg` ; proposer solution. AR1008 hors périmètre.
- Source : `animations/batches/lot45-final-20261011-v1/final-FLM2PUR-PLT_PURP` ; BMP PLT_PURP réalisée avant ReboutCX x4, Apollo8, RGB déjà prémultiplié. Ancien inner2 : petites composantes perdues100%, énergie moyenne−9,82% ; aucun inner initialement retenu.
- Solution : filtre RGBA prémultiplié limité au contour, noyau inchangé ; sigma1,25 ou2px x4. Petites composantes alpha≤48pixels physiques : filtre distinct sigma0,8, normalisation du flux par canal plafonnée au pic initial, fondu canvas1px x4. Aucune seconde prémultiplication ; aucun contour unique supprimant les étincelles.
- Géométrie : dimensions/centres exacts, aucun padding ;16frames natives contrôlées directement contre `source.bam`,32rectangles et centres identiques à l'entrée.32hashes distincts par variante, lookup natif inversé15..0 et32phases conservés,30FPS/1,066667s.
- Mesures32frames : soft125 énergie additive moyenne−1,167%, max absolu1,960% ; soft2 moyenne−1,239%, max2,287%.12petites composantes traitées/protégées par variante ; métriques par frame dans manifeste.
- Producteur : `python pipeline/recipes/flm2pur-oh4210-contour-20261011-v1/build.py` ; sorties `animations/batches/flm2pur-oh4210-contour-20261011-v1/{soft125,soft2,comparison.png,comparison.gif,manifest.json}` ; résumé `result.json`.
- Comparatif : gauche actuel, milieu soft125, droite soft2 recommandé pour bords plus fondus ; zoomx3 pour inspection,4phases/GIF cycle entier à ancre fixe.
- État courant : **soft2 (droite) accepté ingame sur OH4210**, AR1008 embarqué inchangé également accepté ;13occurrences/2cartes. Soft125 seulement en essai. Release non sélectionnée. Manifestes trial/result.json initiaux immuables, leur état décrit la date de production.

## Installation soft2

- Demande : « ok installe celui de droite ingame » ; `install.py`, jeu/InfinityLoader arrêtés.
- Pack OH4210 produit : `animations/packs-par-zone/flm2pur-oh4210-soft2-20261011-v1/OH4210` ; index famille courant `animations/packs-par-zone/flm2pur-palette-selection-soft2-20261011-v1` contient OH4210 modifié et AR1008 embarqué conservé à l'identique. **Seul OH4210 a été installé**.
- Wrapper : `animations/ressources/FLM2PUR/runs/flm2pur-palette-selection-soft2-20261011-v1` ; CSV `à-valider`, verrou OH4210 actualisé ; reçu batch `installation.json`, sauvegarde transactionnelle liée, ancien pack conservé.
- Vérification :32frames/30FPS/1,066667s, dimensions/centres/cycles exacts ;16frames natives vérifiées directement au BAM ; registre OH4210 byte-identique, payload installé exact, signatures verrou conformes. AR1008 byte-identique ;5frères OH4210 AM5204C/FIREBRN/FIRE_3/FIRE_4/FIRE_4GS byte-identiques ; DLL/INI/ARE inchangés.
- CLUA : `C:MoveToArea("OH4210")`, `C:Eval('JumpToPoint([1522.962])',0)` ; coordonnées logiques x1, portrait0 ; fermer la console/reprendre le jeu.

## QA finale

- Utilisateur : « ok je valide tout le lot. maj le suivi et committe. » ; `../lot5-acceptance-20261011-v1/acceptance.json`.
- Run final `flm2pur-lot5-accepted-20261011-v1` ; décision `animations/index/qa-decisions/FLM2PUR/2026-10-11-accepted-flm2pur-lot5-final-v1.json` ; sélection `animations/index/selections/FLM2PUR.json`, CSV `validé-x4`.
- Payloads AR1008/OH4210 installés et signatures de verrou conformes ; lineage final vérifié ; aucune réinstallation/régénération lors de l'acceptation.
