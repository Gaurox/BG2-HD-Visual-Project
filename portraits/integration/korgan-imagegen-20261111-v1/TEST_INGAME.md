# Korgan — test portraits régénérés

**REJETÉ / RESTAURÉ 2026-11-11** : crash au chargement. `crash-rejection.json` : `DrawFlush_GL` déborde son tampon atlas 1024×1024 avec M 676×1064. Trois overrides retirés via le reçu ; ne pas réinstaller ce lot sans adapter le rendu. Rechargement après restauration non observé.

- Maître : `portraits/experiments/korgan-imagegen-large-20261111-v2/NKORGANL-regenerated-7x11.png`.
- Installation : `config://bg2ee_game_root/override/` ; BMP RGB 24 bits, BI_RGB.
- `NKORGANL.bmp` : 791×1243 ; pixels du maître inchangés.
- `NKORGANM.bmp` : 676×1064 = natif 169×266 ×4.
- `NKORGANS.bmp` : 216×336 = natif 54×84 ×4.
- M/S : crop centré minimal + Lanczos uniforme ; aucune déformation anisotrope.
- `KORGAN8/9/11/12/15.CRE` natifs : petit = `NKORGANM`, grand = `NKORGANL`. S fourni ; usage runtime non présumé.
- Installation vérifiée : `backups/20261111T012820119199Z/receipt.json` ; aucun des trois BMP n'existait auparavant dans l'override.
- QA ingame : rejet utilisateur (crash). Sources natives, moteur, autres portraits et release non modifiés.

Test : relancer avec InfinityLoader ; charger une partie avec Korgan dans le groupe ; observer son portrait dans la colonne droite, puis ouvrir sa fiche/inventaire et un dialogue. Vérifier image entière, proportions et netteté. Installation seule vérifiée ; affichage HD à confirmer en jeu.

Depuis la racine du dépôt, jeu et InfinityLoader fermés :

```powershell
python -B portraits/integration/korgan-imagegen-20261111-v1/install.py restore --receipt portraits/integration/korgan-imagegen-20261111-v1/backups/20261111T012820119199Z/receipt.json
```

Restauration : supprime uniquement ces trois overrides après vérification de leurs empreintes ; les ressources natives du BIF reprennent effet.
