# AR0517 / SPHINCT — SplineFit1 monde, retrait8/fondu8

- Demande2026-10-10 : utilisateur retient dernière colonne de `animations/batches/ar0517-sphinct-wed-methods-20261010-v2/edge-detail.png`, puis autorise installation. QA ingame du nouveau résultat encore ouverte.
- Run : `animations/ressources/SPHINCT/runs/ar0517-sphinct-wed-splinefit1-20261010-v3/` ; masque scellé `provenance/world-coverage.png`, SHA256 `93d8964b666bf4b8b2cd4f797c25430b7cbfa17c5c131a527cae5012a1c4d1ae`.
- Recette : spline périodique polygone3 WED AR0517 entier avant crop ; paramètre Fit1 en pixels physiques x4, espacement1.5, supersampling4 ; distance intérieure au contour, retrait8/fondu8 x4 ; clamp conservateur du masque x1 fixture. Origine monde1680,1588 x4, occurrence497,452 x1. Smoothing Fit1 = paramètre RMS, pas borne maximale certifiée.
- 49 frames : `alpha_final = round(alpha_source * coverage /255)` ; RGB, centres77,55, dimensions160×120 x1/640×480 x4, cycles/cadence exacts ; pixels coverage255 byte-identiques. Aucun pixel masqué natif révélé dans fixture ; gate résiduel n'affecte aucun pixel actif sur49 phases.
- Pack : `animations/packs-par-zone/ar0517-sphinct-wed-splinefit1-20261010-v3/AR0517` ; registre v3 position-bound497,452. `has_baked_occurrence_occlusion` bypass natif : pas de cumul avec ancien fondu renderer garde4/fondu16. Cette recette est bornée à l'arche statique identifiée ; son rendu final doit être retesté en jeu.
- DLL/INI inchangés, maps/WED/ARE inchangés. Payloads AR0516/AR0518–AR0521/AR0811/OH8100 exacts. AR0516 garde sa QA antérieure ; aucune sélection QA globale SPHINCT ni release déduite.
- Installation/rétablissement : `animations/batches/ar0517-sphinct-wed-splinefit1-20261010-v3/installation.json` référence reçu/backup ; verrou AR0517 mis à jour. Jeu et InfinityLoader fermés lors du remplacement.
- Reproduction : `build.py` depuis masque de comparaison scellé et leaf source `combined-20260917-active-plus-visual-regression-fix/AR0517`, puis `install.py`. Sorties existantes refusées ; historiques v1/v2 conservés.

```lua
C:MoveToArea("AR0517")
C:Eval('JumpToPoint([497.542])')
```
