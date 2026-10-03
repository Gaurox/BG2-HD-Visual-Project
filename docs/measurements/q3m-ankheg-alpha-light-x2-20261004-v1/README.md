# Ankheg — essai alpha léger x2

- Périmètre : `monster_ankheg`, `0x3000`, owner 9, 12 BAM / 516 frames / 1485 slots. CLUA `C:CreateCreature("ANKHEG01")`.
- Parent : `../q3m-monster-ankheg-full-x2-20261003-v1/current-generation.json`, Q3m V7 K6, I/F/profil/couleurs/centres/cycles inchangés ; aucune inférence ni réencodage Q3m.
- Recette : `pipeline/scripts/sprite_alpha_coverage.py`, gaussien sigma 0,65 pixel x2, intensité 0,8, couverture minimale 176/255, bande intérieure 2 pixels, protection parties fines rayon 1,5. Pas d'expansion ; aucune suppression de pixel visible, de trou ou de composant ; RGB positif inchangé. Ombres et classes spéciales inchangées. Les fragments préexistants du parent restent présents.
- Déduplication masque : recette + SHA processor + dimensions + indices classés `min(I,3)` ; indépendante des couleurs. 431 calculs, 85 réutilisations. 494 frames adoucies / 22 identiques ; 696732 pixels atténués / **0 effacé**.
- Format V8 : multiplicateur alpha optionnel ; même DLL générique V8, aucun changement du moteur pour cette recette. Compatibilité V7 acquise conservée par identité DLL/source/writer dans `verification.json` ; nouveau test natif : 12/516, K6 × 3 encodages, 241492248 pixels. Support visible et RGB contrôlés sur toutes les frames K6 ; 6 tests alpha.
- Spline Fit 1 précédent rejeté ingame : `sprite/index/qa-decisions/monster_ankheg/2026-10-04-rejected-spline-fit1-q3m-x2-catmullrom-v1.json` ; catalogue/DLL parent restaurés avant cette production. Preuves historiques conservées.
- `production.json` / `verification.json` / `current-generation.json` : production et vérification hôte ; `installation-verification.json` : installation, **QA ingame en attente**, aucune promotion release. CatmullRom conservé ; 87 autres animations, 84 assets shader/UI et INI inchangés.
- Installation : `install.ps1` ; sauvegardes locales `work/before/`, jeu/InfinityLoader fermés, contrôle SHA, publication atomique DLL/catalogue ; échec ⇒ restauration parent. `restore.ps1` revient au Q3m V7 original avec CatmullRom.
- Visuel PNG sans perte : `comparison.png`, original gauche / alpha léger droite ; ne simule pas le filtrage CatmullRom ingame.
