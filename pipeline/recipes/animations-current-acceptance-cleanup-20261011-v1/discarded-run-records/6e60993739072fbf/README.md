# AR1516 — inventaire animation complet

- Campagne : `SoA`
- Map : `AR1516` — Spellhold (niveau Soultheft), 35x28 tuiles
- Inventaire canonique : `13` occurrences BAM, `2` resrefs distincts, `0` WBM, `0` PVRZ ; palettes embarquées
- Lot : `AM1516PT` (`non-traité`), `1` occurrence, `6` frames source
- Hors lot : `FIRE_4` (`validé-x4`, 12 occurrences AR1516 : 10 en `0x1043` + 2 en `0x1003`, ressource partagée par ~75 maps)
- Sources : `animations/index/zones.csv`, `occurrences.csv`, `animation_upscale_registry.csv`, `ressources/AM1516PT/source.bam`
- Scan de travail antérieur : aucune trace (runs, batches, packs, rétention, dossier de ressource).
- Choisi : la recette existe au catalogue (`PORTAIL-SEEDVR-SPLINE8`, `PORTL1A`/`PORTL1B`/`PORTL2A` validés) et l'asset y colle presque exactement ; la map est complète après le lot. Autres maps SoA à un seul `non-traité` : `AR1512` `AM1512PA` (portail parallélogramme, lookup avec maintiens uniformes x2), `AR0811` `OHHPORT` (128x128, 24 % de couverture, très sombre), `OH5300` `FPIT1L`, `AR0902`, `AR1101`, `AR3019/3020/3022`, `AR0502`, `AR2903`, `AR1103/1104`, `AR0504`.

| Resref | Statut | Frames | Taille max x1 | Occ. AR1516 | Flags ARE | Autres maps | Frame montrée |
|---|---|---:|---:|---:|---|---|---:|
| `AM1516PT` | `non-traité` | 6 | 66x100 | 1 | `0x1101` (non Blended) | — | voir planche |
| `FIRE_4` | `validé-x4` | 14 | 14x31 | 12 | `0x1043` / `0x1003` | ~75 maps | voir planche |

Planche : [`review/AR1516-one-frame-per-animation.png`](review/AR1516-one-frame-per-animation.png). PNG x1 individuels : `review/representative-frames/`.

Frame représentative = maximum de pixels visibles (alpha BAM binaire).

- Position x1 : `AM1516PT` (2026,1411). `FIRE_4` (échantillon) (1687,620), (1577,540), (1787,1143), (1677,1223), (1602,1276).
- Mesures source de `AM1516PT` (sat / σ lum / lum moy. / couverture / écart inter-frames) : 47,0 % / 26,7 / 105,8 / 77 % / 5,0 ; un seul composant connexe, aucun trou, alpha strictement 0/255, 6 frames uniques, lookup `[0..5]` sans maintien. Analogues `validé-x4` : `PORTL1A` (64x94) 29,2 / 42,5 / 86,0 / 74 % / 5,2 ; `PORTL1B` (79x88) 47,4 / 13,2 / 72,6 / 76 % / 3,6 ; `PORTL2A` 24,1 / 36,9 / 181,3 / 78 % / 10,8. Même famille, même flags de base (`0x11C1` chez les `PORTL*`, `0x1101` ici : pas de Blended dans aucun des deux cas).
- Recette de catalogue : SeedVR2 7B INT8/LAB x4 → Apollo-8 15→30 (6→12 phases) → spline périodique Fit 1 → fondu intérieur 8 px x4, RGB inchangé. Point à vérifier : `PORTL1A` est un ovale, `AM1516PT` semble un ovale à encoche (haut droit) ; la spline suit-elle l'encoche ? Et le paramètre 8 px x4 est hérité (à balayer).
- Occlusion : `AM1516PT` en `0x1101` : bit 6 (`0x40`) absent, donc couvert par les murs (les `PORTL*` en `0x11C1` portent le bit 6). Ressource non Blended : le pont d'occlusion natif transfère la visibilité dans l'alpha et s'applique ; à contrôler en QA.

## Recette analysée (2026-09-21)

Chaîne complète exécutée jusqu'au run de contour (aucun pack de zone, rien d'installé) : `review/AM1516PT-nearest-reboutcx-seedvr.png`, `review/AM1516PT-edge-source-vs-spline-feather8.png`.

| Resref | Recette | Analogues |
|---|---|---|
| `AM1516PT` | SeedVR2 7B INT8/LAB x4 → Apollo-8 15→30 (6→12 phases, `nearest-opaque-dilate`, `--authoring-pack-for-area-split`) → `build_per_frame_spline_alpha_30fps_v2.py --fit-error 1.0 --sample-spacing 1.5 --supersample 4 --padding-x4 32 --inner-feather-x4 8 --rgb-policy preserve` → découpe `AR1516` → fusion avec `FIRE_4` → AreaTest | `PORTL1A`, `PORTL1B`, `PORTL2A` (`PORTAIL-SEEDVR-SPLINE8`) |

Runs faits : `animations/ressources/AM1516PT/runs/am1516pt-seedvr7b-lab-x4-20260921` (SeedVR), `…-seedvr7b-apo8-x4-30fps-v2-20260921` (plan `c0cb14f434ac`), `…-seedvr7b-apo8-spline-fit1-feather8-20260921` (03_runtime_pack prêt à découper) ; `…-reboutcx-x4-20260921` (comparatif, jetable).

- SeedVR conservé (contrairement aux flammes) : couleur moyenne dans le masque source 82,6 / 106,7 / 161,4, SeedVR 82,2 / 106,4 / 161,0, ReboutCX 91,9 / 104,6 / 158,0 (dérive vers le violet) ; SeedVR garde les anneaux d'eau nets et le liseré du cadre, ReboutCX les lave. Écart entre frames consécutives : nearest 6,50, ReboutCX 4,34, SeedVR 7,41 (+14 %, acceptable) ; énergie haute fréquence SeedVR 4,97 contre 3,29. Réserve visible : de faibles formes fantômes sur le bord gauche des frames 0 et 2.
- Audit des doublons : plan sans maintien ni doublon (`collapse_eligible=false`), 12/12 frames distinctes, pas de phase à phase 4,4–5,7 (uniforme), couture dernier → premier 2,4, teinte des intermédiaires identique aux ancres (82,3 / 106,4 / 161,1), alpha strictement 0/255.
- Contour : l'alpha source diffère de 0 à 3 px selon les frames ; le report donne 1 composant, contour touchant le bord du canevas (comme les `PORTL*`, padding 32 px puis recadrage), 7251 px d'alpha intermédiaire par frame. La spline suit l'encoche sombre du haut droit sans la déformer et supprime les pixels bleus isolés du bas gauche (source binaire). IoU alpha final > 127 contre source : 0,950 ; masse d'alpha 94,6 % (le fondu 8 px x4 rogne le liseré extérieur, comme sur les `PORTL*`). RGB identique octet pour octet à la sortie Apollo.
- Hérité, non balayé : fondu intérieur 8 px x4 (`PORTL*`, canevas x1 64x94 contre 66x100 ici, donc même échelle) ; spline fit-error 1,0 / spacing 1,5 / supersample 4.
- Occlusion : `0x1101`, bit 6 absent (couvert par les murs), non Blended : le pont natif agit par l'alpha ; à contrôler en QA. Position (2026,1411).

## Installation (2026-09-21)

- Split `packs-par-zone/am1516pt-seedvr7b-apo8-x4-30fps-v2-spline-fit1-feather8-20260921/AR1516` ; fusion `packs-par-zone/ar1516-lot-am1516pt-merged-20260921` = `AM1516PT` + `FIRE_4` (recette du verrou : leaf lot4 `AR1516::FIRE_4`), signature `FIRE_4` `414b3adf5fa8` inchangée, `AM1516PT` `b74c71d556a7` (12 phases).
- Installé (AreaTest, sauvegarde `backups/animations/area-tests/AR1516-20260921T2133*`) ; `status --deep` : 196/196 conformes.
- Non fait : QA ingame, `approve`/`finalize`, commit.
