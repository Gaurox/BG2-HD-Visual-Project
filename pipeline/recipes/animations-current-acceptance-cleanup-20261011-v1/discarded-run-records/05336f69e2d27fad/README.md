# OH4101 — inventaire animation complet

- Campagne : `SoA`
- Map : `OH4101` — Rasaad, intérieur du temple des Hérétiques de la Lune Sombre (40x30 tuiles)
- Inventaire canonique : `42` occurrences BAM, `1` resref, `0` WBM, `0` PVRZ ; palette embarquée
- Lot : `FIRE_3GS` (`non-traité`), `42` occurrences OH4101, `14` frames source ; la map n'a aucune autre animation
- Sources : `animations/index/zones.csv`, `occurrences.csv`, `animation_upscale_registry.csv`, `ressources/FIRE_3GS/source.bam`
- Scan de travail antérieur : aucune trace (runs, batches, packs, rétention, dossier de ressource).
- Choisi : le plus grand nombre d'occurrences visibles parmi les maps SoA à un seul `non-traité` (42), map complète après le lot. Frère `FIRE_3GR` (`AR0203`, 1 occurrence, même géométrie 30x40) : recette commune, à traiter avec ou juste après.

| Resref | Statut | Frames | Taille max x1 | Occ. OH4101 | Flags ARE | Autres maps | Frame montrée |
|---|---|---:|---:|---:|---|---|---:|
| `FIRE_3GS` | `non-traité` | 14 | 30x40 | 42 (36 `0x1043` + 6 `0x1003`) | `0x1043` / `0x1003` (Blended) | — | 0 |

Planche : [`review/OH4101-one-frame-per-animation.png`](review/OH4101-one-frame-per-animation.png). PNG x1 individuel : `review/representative-frames/`.

Frame représentative = maximum de pixels visibles (alpha BAM binaire) : ici toutes les frames sont **100 % opaques** (rectangle 30x40 plein), donc frame 0 par défaut.

- Positions x1 : `0x1043` (32,365), (211,193), (566,265), (544,571), (638,493), (832,690) ; `0x1003` (718,985), (678,880), (926,1361), (1638,1362), (1848,987), (1886,880).
- Particularité : l'alpha ne porte aucune silhouette (rectangle opaque), la flamme n'existe que par le RGB sur fond noir, l'effet `Blended` additionnant le RGB (noir = transparent). Corollaire : les statistiques source brutes (sat 31,5 / σ 62,8 / lum 38,9) sont faussées par le noir ; sur les pixels allumés (lum > 20, 38 % du rectangle) : `FIRE_3GS` 60,2 % / 66,8 / 98,6 ; `FIRE_3GR` 74,3 / 62,8 / 100,7 ; référence `FIRE_3` (SeedVR validé) 75,2 / 69,2 / 80,3.
- Conséquence pour la recette : les correctifs alpha n'atteignent rien, la neutralisation `--mode zero` ne fait rien (alpha partout 255) ; le rectangle noir doit être neutralisé côté RGB (fondu de bord ou masque dérivé de la luminance) avant tout upscale génératif, sinon SeedVR y invente du bruit qui s'ajoute à la scène.
- Six occurrences en `0x1003` (couvertes par les murs) : occlusion à contrôler en QA ; les 36 autres sont non couvertes.

## Recette analysée (2026-09-21)

Essais x1 (aucun pack de production, rien d'installé) : `review/FIRE_3GS-nearest-reboutcx-seedvr.png`, `review/FIRE_3GR-nearest-reboutcx-seedvr.png` (additif sur noir). Runs : `animations/ressources/{FIRE_3GS,FIRE_3GR}/runs/*-reboutcx-x4-20260921` (runtime pack construit, split `packs-par-zone/fire-3g{s,r}-reboutcx-x4-split-20260921`, réutilisables) et `*-seedvr7b-lab-x4-20260921` (comparatif, jetables).

| Resref | Recette | Analogues |
|---|---|---|
| `FIRE_3GS` (OH4101), `FIRE_3GR` (AR0203) | ReboutCX x4 → Apollo-8 15→30 (14→28 phases, 0,933 s, `--base-runtime-only --base-pack <03_runtime_pack>` car le BAM porte 4 cycles vides terminaux) → découpe par zone → `build_blended_rgb_neutral_pack.py --mode premultiply --inner-feather-x4 8` | `FIRE` (ReboutCX + Apollo-8 + premultiply), `FIRE_3` (même mouvement, SeedVR) |

- SeedVR non retenu : trame f0 de `FIRE_3GS` = un visage ; écart entre frames consécutives +36 % (11,3 contre 8,3 en nearest) et énergie haute fréquence x2 (11,0 contre 5,1) → scintillement, aggravé par l'interpolation. ReboutCX garde la cohérence temporelle (7,3 contre 8,3) et l'aspect flamme lisse, mais perd les volutes fines du haut de la fumée. Repli documenté : SeedVR avec une autre graine (précédent `FIRE_3` : graine 573983441 essayée).
- Écarts de la source : rectangle 30x40 opaque (alpha 255 partout), flamme = RGB sur noir. ReboutCX laisse un voile de luminance ~3-4 sur les bords du canevas (source 0-0,9) : rectangle faiblement visible en additif. `build_blended_rgb_neutral_pack.py` traite le canevas comme frontière de l'alpha : le fondu intérieur devient un fondu de bord de canevas.
- Balayage 4 / 8 / 12 sur la sortie ReboutCX (bord 4 px / cœur p99 / lumière totale / 16 rangées du bas) : `FIRE_3GS` 1,48 / 0 % / -0,7 % / -3,3 % ; **8 : 0,42 / 0 % / -1,5 % / -8,4 %** ; 12 : 0,12 / -0,1 % / -2,7 % / -17,8 % (référence sans fondu 3,91). `FIRE_3GR` identique à 0,1 près. Retenu 8 : bord sous 0,5, cœur intact ; à reconfirmer sur la sortie Apollo.
- Boucle : couture dernier → premier 10,4 contre 8,1 en moyenne (x1,28, identique à `FIRE_3` 13,2 contre 10,3, dont la réserve « cycle à reprendre ») : l'interpolation bouclée devrait l'adoucir. 14 frames uniques, lookup 0..13, aucun maintien, aucun doublon.
- Hérité, non mesuré : Apollo-8 (mouvement doux, écart 7-10, canevas x4 120x160 bien au-dessus du seuil où Topaz plante) ; l'absence de dérive de couleur des intermédiaires est à contrôler après build.
- Occlusion : 36 occurrences OH4101 en `0x1043` (non couvertes) ; 6 en `0x1003` (couvertes par les murs) à observer en QA, `AR0203` 1 occurrence en `0x1043`.

## Traitement et installation (2026-09-21)

- Apollo-8 (`--base-runtime-only`, plan `285975224e07` / `f480f8c58832`) : 14→28 phases, 0,933 s, aucun maintien ni doublon (`collapse_eligible=false`). Contrôle : 28/28 frames distinctes, pas de phase à phase 2,2–9,1 (`FIRE_3GS`) et 2,4–8,4 (`FIRE_3GR`), aucun pas nul, couture dernier → premier adoucie de 10,4/10,5 (natif) à 2,2/2,4, teinte hors gamme < 0,1 % des pixels allumés.
- Balayage 4/8/12 reconfirmé sur les 28 phases : bord 4 px 3,73→1,44 / 0,41 / 0,12 (`FIRE_3GS`), coeur p99 inchangé, 16 rangées du bas -3,1 / -8,1 / -17,5 %. Rayon 8 retenu.
- Packs finaux `packs-par-zone/fire-3g{s,r}-reboutcx-apo8-x4-30fps-v2-innerfeather8-premul-20260921` : `FIRE_3GS` signature `cfa0d460eaef` (OH4101), `FIRE_3GR` `88ca56b1572d` (AR0203). Les deux zones n'étaient pas servies (aucune fusion).
- Installé (AreaTest, sauvegardes `backups/animations/area-tests/{OH4101,AR0203}-20260921T2108*`) ; `status --deep` : 196/196 conformes.
- Non fait : QA ingame, `finalize`/registre, commit.
