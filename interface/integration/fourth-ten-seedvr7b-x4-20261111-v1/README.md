# Lot 4 UI SeedVR2 7B x4 — installation réversible

- Dix ressources, 18 images ; guide : `../../experiments/fourth-ten-seedvr7b-x4-20261111-v1/TEST_INGAME.md`.
- 12 pages : 103/104/131/132/133/162/163/176/179/180/252/253.
- Pages180/253 : base installée conservée et rectangles du lot initial protégés ; inventaire/journal validés inchangés.
- Autres pages : fallback natif x4 sans perte ; patch DXT5 des seuls rectangles du lot ; tous les autres blocs byte-identiques à leur base.
- `alpha-verification.json` : alpha décodé après compression DXT5 identique au natif nearest x4 pour toutes les 18 frames, dont DONATE.
- Test : 44 pages gameplay / 7 sélecteur, isolation, format/taille/hash et désactivation vérifiés.
- Jeu/InfinityLoader fermés ; 14 fichiers installés (DLL/INI + 12 atlas), SHA256 vérifiés ; anciennes pages non remplacées vérifiées inchangées.
- Reçu : `installed-20261111-v1.json` ; sauvegarde : `backups/20261111T010126Z/receipt.json`.
- État : candidats installés, QA ingame en attente ; release inchangée.

Retour au lot précédent, jeu/InfinityLoader fermés :

```powershell
python -B interface/integration/fourth-ten-seedvr7b-x4-20261111-v1/install.py --restore interface/integration/fourth-ten-seedvr7b-x4-20261111-v1/backups/20261111T010126Z/receipt.json
```

Refus si les fichiers ont changé depuis le reçu ; restauration de la DLL et pages180/253 précédentes,
suppression seulement des nouveaux fichiers absents avant ce lot.
