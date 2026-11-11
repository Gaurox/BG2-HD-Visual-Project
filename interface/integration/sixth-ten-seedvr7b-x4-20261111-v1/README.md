# Lot 6 — menus généraux/multijoueurs installés

- Dix ressources : GMPCARBD, GUWPKPC0, GUIINVHB, GUICONNB, GUICONN1, GUIDCX, GUIDLC, GUIMOVB, GUISMBM, START.
- PNG retenus : `../../experiments/sixth-ten-seedvr7b-x4-20261111-v1/selected-20261111-v1.json` ; recette 7B x4/LAB inchangée.
- Guide : `../../experiments/sixth-ten-seedvr7b-x4-20261111-v1/TEST_INGAME.md`.
- 17 atlas : pages106/107/118/119/120/128/129/130/137/138/150/151/157/158/179/256/257.
- Pages107/137/138/150/151/157/158/179 : bases installées conservées ; rectangles précédemment traités protégés.
- Page257 : entrée MAINMENU existante rendue accessible au flag gameplay, empreinte recalculée sur DXT5 natif ; hors START : fallback natif exact, pas de réactivation des anciens boutons HD.
- Autres pages : natif x4 sans perte puis patch des seuls rectangles sélectionnés ; aucun BAM/MOS/PVRZ natif modifié, géométrie logique x1.
- Tests : 66 pages gameplay / 7 sélecteur ; isolation, hash/format/taille/config/off ; blocs non sélectionnés byte-identiques à leur base.
- Jeu/InfinityLoader fermés ; 19 fichiers installés, SHA256 vérifiés ; anciennes pages non remplacées vérifiées inchangées.
- Reçu : `installed-20261111-v1.json` ; sauvegarde : `backups/20261111T133435Z/receipt.json`.
- QA ingame en attente ; GUIDLC limité à la route tactile native, non exposée sur PC. Release inchangée.

Retour exact, jeu/InfinityLoader fermés :

```powershell
python -B interface/integration/sixth-ten-seedvr7b-x4-20261111-v1/install.py --restore interface/integration/sixth-ten-seedvr7b-x4-20261111-v1/backups/20261111T133435Z/receipt.json
```

Refus si les fichiers ont changé depuis ce reçu ; restaure les fichiers antérieurs, retire uniquement
les nouveaux fichiers absents avant le lot. Archives/QA précédentes et sauvegardes conservées.
