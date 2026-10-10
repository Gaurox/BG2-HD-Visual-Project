# Prison planaire : extension Spline Fit1 nette

- Autorisation : toutes cellules AR0517-AR0521 ; AR0516 explicitement incluse via clarification.
- Référence : AR0517 crisp-v5 acceptée utilisateur ; masque/cycle/49 frames/install inchangés.
- Cellules : ARE distincts, WED AR0517 SHA34b74eeaa612… commun ; positions501,451 /500,451 /501,451 /499,451. Masque recalé en coordonnées monde, jamais copié tel quel depuis la position497,452.
- AR0516 : WED actif SHA8a0aa3ca4c5d… ;49 phases analysées ; positions1520,1287(P46),1529,1447(P48+49),2948,1776(P89). Aucun polygone actif sur2263,1103 ni SPHINCT2@1933,1017 : inchangés.
- Recette identique : spline périodique complète Fit1 en x4, resample1.5, SS4/BOX ; garde0/fondu0 ; pas de clamp x1.
- Mémoire : tentative v6 avec3 variantes RGBA ajoutées =562262720B >512MiB moteur. v7 conserve les194 frames AR0516 et applique3 masques RLE embarqués dans la DLL, uniquement AreaRegistry/SPHINCT/AR0516/positions exactes/160x120/non-dither. +3.52MiB CPU ; limite moteur intacte. Modes0/1/2 GLSL byte-identiques ; nouveau mode3 RGB droit/alpha×coverage x4.
- Audit : `animations/batches/planar-sphinct-wed-crisp-20261010-v6/{analysis,analysis-all-phases}.json` ; diagnostics et contours sur chaque occurrence.
- Production : `animations/ressources/SPHINCT/runs/planar-sphinct-wed-crisp-20261010-v7/`, `animations/packs-par-zone/planar-sphinct-wed-crisp-20261010-v7/` (4 cellules).
- Contrôles : 196 frames cellules +147 draws GPU AR0516 ; RGB/centres/cadence conservés ; toutes phases native/masque fixe ; tests scope/C++ ; BDFORCEW2 fixtures exactes ; autres sources snapshot et headers générés identiques.
- Installation : `install.py`, renderer transactionnel + packs par zone transactionnels ; reçus `animations/batches/planar-sphinct-wed-crisp-20261010-v7/installation.json`. ARE/WED/DLL/INI/4 zones protégées contrôlés.
- QA finale : acceptation explicite utilisateur 2026-10-10 sur AR0516-AR0521 ; `animations/index/selections/SPHINCT.json`, décision `animations/index/qa-decisions/SPHINCT/2026-10-10-accepted-sphinct-planar-final-v1.json`.
- État scellé : `animations/ressources/SPHINCT/runs/sphinct-planar-accepted-20261010-v1/manifest.json` ; packs/DLL installés identiques ; procédure `../planar-sphinct-validation-20261010-v1/accept.py` et reçu `acceptance.json`. Aucune release.
