# AR0801 / AR0808 — lot animation (2026-09-18)

`AM0801A` (bassin de sang 181x108, 390,815), `AM0801B1`/`AM0801B2` (moitiés gauche/droite d'un bassin pentagonal, contact exact à x=2848, 163 rangées), tous à la même position dans `AR0801` et sa variante `AR0808`. Non Blended (`0x1101`), palette embarquée, 1 cycle x 7 slots à 1 slot. Scan de travail antérieur : aucune trace.

Analogues validés : `AM0803A–E` (mares de sang, AR0803/AR0809 : SeedVR 7B/LAB → Apollo-8 7→14 → spline fit 1 + feather 4), `AM0033AB` (bassin, contour touchant le canvas).

Chaîne :
1. Doublons : aucun maintien, aucune frame identique, pas uniformes (A 1,9 ; B 0,6–0,7), boucle fermée du même ordre → interpolation directe.
2. SeedVR2 7B/LAB x4 : `ar0801-seedvr7b-lab-x4-20260918` ; `B1|B2` sur mosaïque monde (`ar0801-b1b2-mosaic-x1-20260918`, marche au raccord 1,1 → 0,3) → `ar0801-seedvr7b-lab-x4-b1b2mosaic-20260918`. Pas de billes « warm-patch » sur A (reflets lisses).
3. Apollo-8 15→30 fps, `nearest-opaque-dilate`, 7→14 phases, 0,467 s : `ar0801-apo8-x4-30fps-v2-20260918` (plan `0df099fe`).
4. Spline fit 1 multi-contour par frame, **feather 16** (pas 4 : le fin liseré brun du BAM source devient une dentelure sombre/claire sur le liseré de pierre clair d'A ; 8 insuffisant, 16 la supprime, 24 = même résultat plus mou), RGB préservé. `B1` : raccord droit restauré 8+16 px x4 ; `B2` : raccord gauche 8+16 px x4 (option ajoutée à `build_per_frame_spline_alpha_30fps_v2.py`, test inclus). Runs : `animations/ressources/AM0801A/runs/ar0801-am0801a-spline-fit1-feather16-20260918`, `…AM0801B1/runs/ar0801-am0801b1-spline-fit1-feather16-seamR-20260918`, `…AM0801B2/runs/ar0801-am0801b2-spline-fit1-feather16-seamL-20260918`.
5. Vérifs : alpha final ≤ source, 0 frame non ajustée, pas de pas nul, boucle sans à-coup (A 0,74–1,05 ; B 0,26–0,4), alpha au raccord conservé (652/676 rangées opaques des deux côtés), rendu sur la map sans cassure (`review/AR0801-final-on-map.png`).

Packs zone installés : `animations/packs-par-zone/ar0801-complete-map-lot-20260918/AR0801` et `ar0808-complete-map-lot-20260918/AR0808` = `FIRE_4` (accepté lot4) + A + B1 + B2. `FLAME2S` non servi (aucun pack).
Non fait : QA ingame, registre/sélection, commit (dont modif outil spline + test).

## Révision AM0801A — ReboutCX (2026-09-18)

Demande utilisateur : `AM0801A` en 7B jugé faible. Comparatif 7B / 3B / ReboutCX : `review/AM0801A-comparatif-upscale.png` (3B = cellules hexagonales, écarté). Retenu pour essai : ReboutCX x4 (`ar0801-am0801a-reboutcx-x4-20260918`, runner `run_animation_reboutcx_x4.py`, alpha nearest) → Apollo-8 7→14 (`…-reboutcx-apo8-x4-30fps-v2-20260918`, plan `dee19554`) → spline fit 1 feather 16, RGB préservé (`…-reboutcx-spline-fit1-feather16-20260918`). Vérifs : aucun doublon (contrôle source inchangé), 0 frame non ajustée, alpha ≤ source, pas de pas nul, boucle sans à-coup (0,34–0,53). `B1`/`B2` inchangés.
Packs installés : `ar0801-complete-map-lot-v2-a-reboutcx-20260918/AR0801` et `ar0808-…/AR0808`. Sauvegardes (état 7B) : `AR0801-20260918T205925590144Z-04b241b1`, `AR0808-20260918T205927568396Z-60613d66`.
