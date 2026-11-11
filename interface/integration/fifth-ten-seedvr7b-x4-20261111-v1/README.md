# Lot 5 — création/personnalisation installé

- Dix PNG 7B x4 retenus : `../../experiments/fifth-ten-seedvr7b-x4-20261111-v1/preview-accepted-20261111-v1.json`.
- Ressources : GUIGDB, GUIAPB, GUISMF, GUISMDB, GUILUPB, GUISMS, GUIHSBS, GUIMPB, GU3MPB, GUISMDA.
- Guide : `../../experiments/fifth-ten-seedvr7b-x4-20261111-v1/TEST_INGAME.md`.
- 15 atlas : pages110/111/112/133/134/136/137/145/146/151/152/158/159/160/161.
- Pages133/136 : bases installées conservées, rectangles GUIERR7/GUIHSB protégés. Hors zones du lot : blocs DXT5 byte-identiques à leur base.
- Autres pages : fallback DXT5 natif x4 sans perte, puis seuls rectangles des fonds sélectionnés.
- Même flag `EnableGameplayMenusX4` ; sélecteur et géométrie logique x1 inchangés ; aucun BAM/MOS/PVRZ natif remplacé.
- Test : 57 pages gameplay / 7 sélecteur ; hash/format/taille/config, isolation/off vérifiés.
- 17 fichiers installés avec sauvegarde et contrôle SHA256 : DLL/INI + 15 atlas ; anciennes pages non remplacées vérifiées inchangées.
- Reçu : `installed-20261111-v1.json` ; sauvegarde : `backups/20261111T012107Z/receipt.json`.
- État : images acceptées hors jeu, installé pour QA ingame ; release inchangée.

Retour exact, jeu et InfinityLoader fermés :

```powershell
python -B interface/integration/fifth-ten-seedvr7b-x4-20261111-v1/install.py --restore interface/integration/fifth-ten-seedvr7b-x4-20261111-v1/backups/20261111T012107Z/receipt.json
```

Refus si les fichiers ont changé depuis le reçu ; restaure DLL/pages133/136 précédentes, retire seulement les fichiers absents avant ce lot.
