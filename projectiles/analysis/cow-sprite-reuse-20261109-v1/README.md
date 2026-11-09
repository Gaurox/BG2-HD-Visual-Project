# COW188 — sprite accepté réemployé,2026-11-09

- Source : ACOWG1, Q3m V7 x2/profile8/rule3,22frames/40cycles/288slots ; feuille46E72975… du catalogue créatures actif. QA sprite ambient_static acquise, source/feuille/catalogue inchangés.
- `reuse.json` :22géométries natifs identiques,132hashes pixel/K6 exacts, duplication2× strictement inversible vers stockage effets x4 ; aucune inférence ni interpolation, pas une production modèle x4. Palette native neutre et ombre127 conservées ; autres éclairages non testés.
- `native-route.json`,`native-cow-factory.txt` : PROJECTL188/missile189, sourceACOWG1, constructeur227600, Render partagé233f20 (slot98). Aucun hook de déplacement nouveau.
- Installation : [reçu](../../../effects/installations/cow-sprite-bridge-20261109-v1/installation.json), [CLUA](../../../effects/installations/cow-sprite-bridge-20261109-v1/CLUA.md).1ressource/22backings ajoutés,743ressources/72563backings ;742anciens/72541préservés.5/5tests moteur,2304contrats candidat+installé chacun.
- **COW validé ingame2026-11-09** : [acceptation finale](../cow-accepted-20261109-v1/README.md). QA limitée au COW observé ; autres éclairages/cycles non déduits. VVCZCOWV = image isolée ; SPWI299/Player2 = vrai projectile offensif. SourceBAM/CRE/INI,3images précédemment acceptées et release conservés.
- Recette `pipeline/recipes/cow-sprite-reuse-20261109-v1/build.py` (nouveau dossier requis pour refaire) ; `install.py prepare|install|restore`, jeu/loader arrêtés avant remplacement.
