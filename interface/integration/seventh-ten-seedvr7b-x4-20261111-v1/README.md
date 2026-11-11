# Lot 7 — dix variantes historiques installées

- Ressources : GMPCARBB, GMWMSGA0, GMWMSGA9, GMWMSGB0, GUICGPR, GUIAPBR, GUICHISE, GUICPORB, GUICUSTP, GUICUSTX.
- Acceptation des PNG affichés : `../../experiments/seventh-ten-seedvr7b-x4-20261111-v1/selected-20261111-v1.json` ; SeedVR2 7B x4 LAB.
- Installation : `installed-20261111-v1.json`, 16 fichiers (DLL/INI +14 atlas), SHA256 vérifiés ; 57 anciens fichiers non remplacés vérifiés inchangés.
- Sauvegarde : `backups/20261111T135143Z/receipt.json` ; jeu/InfinityLoader fermés, remplacement transactionnel et vérification avant/après.
- Pages105/106/107/108/112/114/115/116/122/123/124/126/127/128. Neuf pages partagées : bases installées conservées, pas de chevauchement avec les compositions des lots précédents.
- Hors rectangles : blocs DXT5 inchangés. Alpha : blocs natifs x4 conservés. Icônes GMPCARBB / poignées GMWMSGA0/9 : blocs natifs exacts remis après encodage DDS.
- Renderer : 5 empreintes ajoutées, entrées précédentes conservées ; flag gameplay existant. Tests : 71 pages gameplay / 7 sélecteur ; isolation, empreintes, format/dimensions, config/off vérifiés.
- Accès ingame : `TEST_INGAME.md` ; aucune de ces ressources référencée dans UI.menu courant ni par nom exact dans les exécutables racine. Remplacement prêt si texture chargée, aucun nouvel accès forcé.
- Validation hors jeu acquise ; aucune observation ingame/release déduite. Payload/staging/TP2/manifeste release inchangés.

Retour exact, jeu et InfinityLoader fermés :

```powershell
python -B interface/integration/seventh-ten-seedvr7b-x4-20261111-v1/install.py --restore interface/integration/seventh-ten-seedvr7b-x4-20261111-v1/backups/20261111T135143Z/receipt.json
```

Refus si fichiers live modifiés depuis le reçu ; sauvegardes précédentes conservées.
