# Cinq arbres — SeedVR statique x4 / premier test 2026-10-11

- Cibles : 1400T001–005, AR1400 + AR1404, 10 occurrences. QA en attente ; aucune release.
- Production : `animations/batches/trees-seedvr-static-x4-20261011-v1/manifest.json` terminé ; RGB SeedVR2 7B INT8/LAB, seed20261011, pad32 x1 temporaire ; crop1020×1020.
- Alpha : T002/004 nearest natif ; T001/003/005 Potrace0.8/opttol0.1/SS8/bande2x4, protégé. Min176 dans le support, RGB nul hors alpha ; masque visible exact à seuil127. Protection des régions à distance >1.5x1 du cœur EDT>1.5, dilatation1x1 ; bords canvas2x4. Courbes/trous natifs conservés. Les champs `grown_pixels`/`shrunk_pixels` décrivent Potrace avant protection ; `outside_growth_pixels=0` décrit le résultat final.
- Aucun Apollo, fondu global, remplissage RGB du liseré. Géométrie logique255², centre(1,1), cycles natifs inchangés.
- Éclairage : AR1400LM jour et AR1404LM nuit permanente, échantillonnage monde par ancre ; pas de correction DLL. **AR1400 la nuit n'est pas corrigé dynamiquement.**
- `preparation.json` : recettes, variantes alpha, packs complets, état installé antérieur ; `installation.json` : reçu installation + hashes protégés. Fontaines AM1400A/N conservées ; DLL/INI/AR3000 inchangés.
- `finish.py` et `install.py --run` produisent des sorties neuves ; ne pas relancer sur les destinations scellées. Nouvelle version pour remplacer cet essai.
- PNG : `animations/batches/trees-seedvr-static-x4-20261011-v1/preview-{AR1400,AR1404}.png` ; commandes dans [CLUA.md](CLUA.md).
