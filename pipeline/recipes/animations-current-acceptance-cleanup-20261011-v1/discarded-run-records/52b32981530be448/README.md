# AR2000 — lot animation (2026-09-18)

`AM2000A` (eau turquoise) / `AM2000B` (eau bleu nuit) : deux versions de la fontaine centrale de Trademeet au même point (1769,1223). Chaque BAM est une **animation quadrant** : ses 4 cycles sont les 4 quadrants d'une même image affichés ensemble (phase j = frames `2j`, `2j+1`, `14+2j`, `15+2j`). Canvas monde 379x297 autour de l'ancre. Non Blended (`0x1355`, bit 1 absent), palette embarquée.

Historique : un premier essai existe (2026-09-11/12, commit `508e9d30`, packs `ar2000-am2000ab-*-ingame-test-20260912`, outil `build_cross_cycle_seam_30fps_v2.py`) sans décision QA ni ligne de registre. Ce lot le reprend.

Analogues validés : `FALL1B` (quadrant, eau, 7B/LAB + alpha safe-boundary), `AM0033AB` (bassin, spline fit 1 + feather 6, contour touchant le canvas), `AM1400A/N` (paire jour/nuit, 7B/LAB + Apollo-8).

Chaîne :
1. Vérif doublons (sources) : 4 cycles x 7 slots, tous à 1 slot, aucune frame identique, aucune paire quasi statique, boucle fermée du même ordre que les autres transitions (écart 3–5 partout) → interpolation directe, pas de condensation.
2. SeedVR2 7B/LAB x4 sur mosaïques de phase (`ar2000-quad-mosaic-x1-20260918`) : le SeedVR par quadrant laissait une croix (marche RGB 7–20 contre ~1) ; sur mosaïque 2,8–8,7. Run `ar2000-water-quadmosaic-seedvr7b-lab-x4-20260918`.
3. Apollo-8 15→30 fps, `nearest-opaque-dilate`, 7→14 phases par cycle (0,467 s) : `ar2000-water-quadmosaic-apo8-x4-30fps-v2-20260918` (plan `978ff2bf`).
4. `build_cross_cycle_seam_30fps_v2.py` : spline fit 1 conjointe sur la croix reconstruite (padding 32, feather 6), alpha source restauré 8 px + transition 16 px sur les deux axes, RGB gaussien sigma 2 / profondeur 12 / 55 % confiné à la croix → `ar2000-am2000ab-quadmosaic-cross-spline6-rgb-g2d12s55-20260918`.
5. Vérifs finales : pas de pas nul, boucle sans à-coup (pas moyen 1,1–2,0, max 2,7), rendu sur le rendu x1 de la map sans cassure (`review/AR2000-final-on-map.png`, `review/AR2000-cross-zoom.png`).

Pack zone installé : `animations/packs-par-zone/ar2000-complete-map-lot-20260918/AR2000` = `BUTRFLY` + `CHIMSMK` (acceptés, master `combined-20260904-fpit1s-contour-fondu-J`) + A + B. `FLIESS` hors lot.
Non fait : QA ingame, registre/sélection, commit.
