# SHAREA palettes natives — V8

- Installé, QAingame attendue : [cinq tests](../../../projectiles/analysis/sharea-palettes-preparation-20261028-v1/README.md). DLL SHA FEAE6EB5EEA0D0E6EDBEC32006B9DC71B469E96E3F11062A01B6FC0BFEB0DC76 ;538ressources inchangées.
- Moteur seul ;22imagesSHAREA vérifiées inchangées ; aucunPRO,métadonnée,INI,shader,personnage oufichier release modifié. Palette/coloration appliquée uniquement à la copie temporaire d’uploadGPU.
- `tests.log` :5/5suites passantes,4,18s ;1785points natifs,7palettes,identité/alpha/noir/encodages etisolationGPU ; pasQAingame. Interpolation de couleur des pixelsHD inédits explicitée dansla préparation.
- Recette `pipeline/recipes/projectiles-sharea-palettes-20261028-v8/install.py prepare|install`, déjà exécutée,ne pas écraser les reçus. `before.json`, `installation.json`, `backups/` : restauration transactionnelleDLL/INI via le reçu d’installation. AncienneDLLV7 sauvegardée.
- Généralisation à toutes les palettes effectives deSHAREA sous Blended ; pas aux BAM voisins,ni aux modes/compositions sans contrat confirmé. Valeursalpha non uniformes/absencepalette gardent le natif.
