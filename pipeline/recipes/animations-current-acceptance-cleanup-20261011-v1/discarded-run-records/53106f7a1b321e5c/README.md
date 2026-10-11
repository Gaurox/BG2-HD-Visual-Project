# AR0406 — lot animation (2026-09-18)

Lot : `AM0406A`, `AM0406B` (SeedVR) ; `FLIESS` sorti du lot (natif probable, partagé par 12 maps, xBR = source ×4).

| Resref | Lookup source | Timeline 30 fps | Alpha |
|---|---|---|---|
| `AM0406A` | `[0,1,2,3,4,5,5,6,7,8]` — frame 5 doublée (maintien isolé) | `--segment-transition-phases 2,2,2,2,2,4,2,2,2` : mouvement étalé sur le maintien, 10 slots → 20 phases, 0,667 s conservées | fade contour intérieur 8 px x4, bords canvas ouverts |
| `AM0406B` | chaque pose ×2 (uniforme) | `--collapse-uniform-duplicate-holds`, 9 poses → 36 phases, 1,2 s | idem |

- A (x 985–1090) et B (x 1090–1233) se touchent exactement à x=1090 (57 rangées). SeedVR séparé cassait le raccord (marche RGB 27–30 contre 9 à l'intérieur). Correctif : SeedVR sur mosaïque monde `ar0406-ab-mosaic-x1-20260918` (frame i de A + frame i de B), puis découpe → run `ar0406-decor-mosaic-seedvr7b-lab-x4-20260918` (marche au raccord 9–11).
- Fade : 36 px x4 (recette `AM3017A–D`) mangeait 29 % de l'alpha sur ces bandes fines de ~45 px et effaçait le raccord (alpha 0 sur la colonne de contact) ; 8 px x4 + `--inner-contour-open-canvas-edges` (alpha source conservé sur les bords coupés par le canvas). Alpha au raccord : 244 / 240.
- Vérifs : pas de doublon identique, pas de pas nul dans la timeline, boucle fermée (écart max 3,5 pour une moyenne 2,5 sur A ; 2,5 / 1,5 sur B).
- Runs finaux : `animations/ressources/AM0406A/runs/ar0406-am0406a-mosaic-innerfade8-open-20260918`, idem `AM0406B`.
- Pack zone installé : `animations/packs-par-zone/ar0406-complete-map-lot-20260918/AR0406` = `FIRE_4` (accepté lot4) + `FPIT1S` (accepté J) + A + B.
- Aperçus : `review/AR0406-final-on-map.png`, `review/AR0406-final-seam-crop.png`, `review/AR0406-fade-variants-on-map.png`.
- Non fait : QA ingame, registre/sélection, commit.
