# Troisième lot UI 7B x4 — installé pour test

- Dix MOS : boutiques, temple, auberge, monde, sauvegarde (2 couches), couleurs (2 couches), butin.
- Sources et recette : `../../experiments/third-ten-seedvr7b-x4-20261111-v1/README.md`.
- Accès par numéro : `../../experiments/third-ten-seedvr7b-x4-20261111-v1/TEST_INGAME.md`.
- Reçu : `installed-20261111-v1.json`, backup `backups/20261111T004744Z/receipt.json`.
- 16 fichiers installés : DLL/INI + 14 atlas. Flag existant `EnableGameplayMenusX4`, sélecteur indépendant inchangé.
- Pages107/113/114/124/125/135/136/147/148/157/164/165/166/167.
- Pages125/148 : base installée conservée ; rectangles des assets précédemment validés explicitement protégés.
- Autres pages : fallback natif x4 sans perte DXT5 ; hors rectangles modifiés byte-identique à la base.
- Aucun BAM/MOS/PVRZ natif modifié, géométrie x1 conservée ; boutons/icônes hors nouvelle production.
- Test runtime : 34 pages gameplay / 7 sélecteur ; isolation, hash/format/dimensions, défaut/off et INI vérifiés.
- Copie transactionnelle jeu/InfinityLoader fermés ; SHA256 des nouveaux fichiers et des anciennes pages non remplacées vérifiés.
- État : candidats installés, QA ingame en attente ; aucune intégration release déduite.

Retour au lot précédent, jeu et InfinityLoader fermés :

```powershell
python -B interface/integration/third-ten-seedvr7b-x4-20261111-v1/install.py --restore interface/integration/third-ten-seedvr7b-x4-20261111-v1/backups/20261111T004744Z/receipt.json
```

Refus si les fichiers ont changé depuis ce reçu. Restaure la DLL et les pages125/148 précédentes,
et retire uniquement les nouveaux fichiers absents avant ce lot ; sauvegardes antérieures conservées.

Validation utilisateur 2026-11-11 : « validé » ; `qa-accepted-20261111-v1.json`. Dix ressources acceptées sur le rendu observé.
