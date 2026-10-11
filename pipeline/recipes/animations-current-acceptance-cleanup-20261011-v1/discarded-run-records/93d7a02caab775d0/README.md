# OH4000 — inventaire animation complet

- Campagne : `SoA`
- Map : `OH4000` — Abandoned Amphitheater (80x60 tuiles, variante nuit)
- Inventaire canonique : `14` occurrences BAM, `3` resrefs distincts, `0` WBM, `0` PVRZ ; palettes toutes embarquées
- Lot : `2` resrefs `non-traité` (`FIRE`, `FPIT1M`), `6` occurrences OH4000, `15` frames source
- Hors lot : `BUTRFLY` (`validé-x4`, 8 occurrences, ressource partagée par 14 maps)
- Seule map SoA à porter deux `non-traité` distincts après le lot AR0500 (toutes les autres n'en ont qu'un).
- Sources : `animations/index/zones.csv`, `occurrences.csv`, `animation_upscale_registry.csv`, `ressources/<RESREF>/source.bam`
- Scan de travail antérieur : aucune trace pour `FIRE` ni `FPIT1M` (runs, batches, packs, rétention ; les noms `ar0700-fire-*`, `ar3016-*-fire-*` concernent `FIRE_1/FIRE_4`).

| Resref | Statut | Frames | Taille max x1 | Occ. OH4000 | Flags ARE | Autres maps | Frame montrée |
|---|---|---:|---:|---:|---|---|---:|
| `BUTRFLY` | `validé-x4` | 18 | 64x64 | 8 | `0x1005` | 13 autres maps | 15 |
| `FIRE` | `non-traité` | 9 | 14x57 | 5 | `0x1043` | OH4200 (8 occ.), OH7300 (51 occ.) | 4 |
| `FPIT1M` | `non-traité` | 6 | 48x42 | 1 | `0x1043` | AR6111, OH4200, OH6100 | 2 |

Planche : [`review/OH4000-one-frame-per-animation.png`](review/OH4000-one-frame-per-animation.png). PNG x1 individuels : `review/representative-frames/`.

Frame représentative = maximum de pixels visibles (alpha BAM binaire).

- Positions x1 : `FIRE` (3486,1293), (3680,1315), (3764,737), (4076,1033), (4155,780) ; `FPIT1M` (4694,3304).
- `FIRE` : flamme haute 14x57, Blended (bit 1 posé), 9 frames uniques. Sat / σ lum / lum moy. = 64,1 % / 51,7 / 151,0 : entre la grappe ReboutCX (`FLAME2M` 56,7 / 84,6 / 94,9) et SeedVR (`FIRE_4` 77,0 / 67,6 / 71,5) ; recette à trancher par essai comparatif.
- `FPIT1M` : lit de braises, Blended, 6 frames uniques. 53,6 % / 48,3 / 174,9 = profil de `FPIT1S` (54,1 / 44,2 / 173,2) où SeedVR invente des volutes ; `FPIT1S` a fini en SeedVR + xBR2x sur l'alpha + fondu de contour + halo + premultiply, avec 16 masques d'occlusion peints (le pont natif ne marche pas sur Blended). Analogue direct aussi `FPIT1L` (78x67, non traité, AR5203/OH5300).
- Complétions par extension de signature : `OH6100` (SoA) avec `FPIT1M` ; `OH4200`, `OH7300`, `AR6111` (ToB) en partie.

## Recette analysée (2026-09-21)

Essais comparatifs sur x1 (aucun pack, rien d'installé) : `review/FIRE-nearest-reboutcx-seedvr.png`, `review/FPIT1M-nearest-reboutcx-seedvr.png` (additif sur sol sombre, alpha binaire). Runs conservés : `animations/ressources/{FIRE,FPIT1M}/runs/{fire,fpit1m}-reboutcx-x4-20260921` (réutilisables) et `…-seedvr7b-lab-x4-20260921` (comparatif, jetables).

| Resref | Recette | Analogues |
|---|---|---|
| `FIRE` | ReboutCX x4 (alpha nearest x4) → **cadence native** (9 frames uniques, lookup 0..8) → découpe par zone → `build_blended_rgb_neutral_pack.py --mode premultiply --inner-feather-x4 2` | `FIRE_3`/`FIRE_4` (feather 2 + premultiply), `FLAME2*` (ReboutCX), `FIRE_1` (natif) |
| `FPIT1M` | ReboutCX x4 → Apollo-8 15→30 (6→12 phases, `nearest-opaque-dilate`) → découpe → `build_animation_contour_aura_pack.py --inner-feather-x4 12 --aura-sigma-x4 5 --aura-gain 0.9 --border-margin-x4 14` (premultiply inclus) | `FPIT1S` (mêmes paramètres, spatial SeedVR) |

- SeedVR écarté sur les deux : `FPIT1M` f0/f4 = billes et volutes inventées (défaut connu de `FPIT1S`) ; `FIRE` f4 = filaments rouges parasites et blob sur les braises ; ReboutCX reste cohérent (langues lisses, cuvette conservée). Sat / σ lum / lum moy. : `FIRE` 64,1 / 51,7 / 151,0 ; `FPIT1M` 53,6 / 48,3 / 174,9 ; référence SeedVR réussie `FIRE_4` 77,0 / 67,6 / 71,5.
- `FIRE` : pas d'anneau sombre (lum. 104 à 1 px du bord, 156 à 2 px) → pas de rectangle à effacer, donc pas le fondu large de `FLAME2*` ; braises détachées de 1 px x1 (4x4 px x4) qu'un rayon > ~4 éteindrait. Écart inter-frames 24–43 (`FIRE_4` : 8) : Apollo ferait fantômer les braises → natif.
- `FPIT1M` : pas d'anneau sombre non plus (130 à 1 px) → halo type `FPIT1S` plutôt que `FLAME2*`.
- Hérité, non mesuré : feather 2 (FIRE_3/4), paramètres d'aura 12 / 5 / 0,9 / 14 (FPIT1S, canevas 2x plus petit) et 12 phases. À balayer sur la sortie réelle : `FIRE` feather 0 (`--mode zero`) / 2 / 4, critères cœur p95 et braises conservées ; `FPIT1M` feather 12/16/24.
- Alpha de `FPIT1S` agrandi par xBR2x deux fois (pas d'outil dédié, issu du runner `run_animation_small_subject_xbr2.py`) ; ici alpha nearest x4 + fondu 12 : à comparer seulement si l'escalier de 4 px du contour reste visible.
- Occlusion : `OH4000` et `OH4200` en `0x1043` (bit 6 posé = non couvert par les murs) → aucun masque peint. `OH6100` (`0x1013`) et `AR6111` (`0x1003`) sont couverts par les murs : à observer en QA (le pont natif ne marche pas sur Blended, `FPIT1S` a exigé 16 masques peints).
- Interpolation 30 fps de `FIRE` : repli possible si tu veux la fluidité ; non retenu par défaut.

## Traitement et installation (2026-09-21)

Demande utilisateur : interpolations 30 fps sur les deux (FIRE n'est donc plus en cadence native), avec les précautions habituelles contre les doubles frames.

- Audit (`plan`) : `duplicate_hold_analysis` = aucun maintien, runs de 1 slot, `collapse_eligible=false` → interpolation directe, sans `--collapse-uniform-duplicate-holds`. Frames x1 toutes distinctes en RGBA (FIRE 9/9, FPIT1M 6/6), écart consécutif ≥ 23. Build Apollo-8 (`nearest-opaque-dilate`) : `FIRE` 9→18 phases, `FPIT1M` 6→12 phases (0,4 s conservées).
- Contrôle du pack 30 fps : 18/18 et 12/12 frames distinctes, aucun pas nul (MAE de phase à phase 4,8–17,0 et 10,9–20,8), boucle dernière → première non nulle (14,2 et 17,3), pas de contamination de couleur (bleu > rouge < 1 %).
- Runs : `animations/ressources/{FIRE,FPIT1M}/runs/*-reboutcx-apo8-x4-30fps-v2-20260921` (non approuvés, `qa-approval` à faire à la QA vidéo).
- `FIRE` : balayage `--mode zero` / feather 2 / feather 4 sur les 18 phases : lumière totale 0 / -10,9 / -18,0 %, braises conservées 36 / 30 / 28 sur 44, cœur p95 inchangé. Retenu 2 (bord adouci sans éteindre les braises, précédent `FIRE_3`/`FIRE_4`). Pack `fire-reboutcx-apo8-x4-30fps-v2-innerfeather2-premul-20260921`, signature `119f5fae0d9f`.
- `FPIT1M` : aura sur les 12 phases, `--inner-feather-x4` 12 / 16 / 24 avec sigma 5, gain 0,9, marge 14 : lumière totale -26,6 / -33,0 / -43,9 %, cœur -0,8 / -1,1 / -2,2 %, halo +25 / +22 / +17 % de surface ; 12 laisse des rayons fins autour des franges. Référence `FPIT1S` validé : lumière -56 %, cœur -15 %, surface +37 % (canevas 92 px contre 192 ici : rayon 12/92 ≈ 24/192). Retenu 24 (proportionnel à `FPIT1S`), 16 en repli. Pack `fpit1m-reboutcx-apo8-x4-30fps-v2-aura24-20260921`, signature `d64836e30571`.
- Fusions (`packs-par-zone/oh4000-lot-fire-fpit1m-merged-20260921`, `oh4200-…`, `oh7300-lot-fire-merged-…`, `oh6100-lot-fpit1m-merged-…`) : signatures `BUTRFLY`, `FIRE_3`, `FIRE_4`, `FPIT1S` inchangées. `AR6111` servie pour la première fois.
- Installé (AreaTest, sauvegardes `backups/animations/area-tests/{OH4000,OH4200,OH7300,OH6100,AR6111}-20260921T2009*`) ; `status --deep` : 193/193 conformes.
- Non fait : QA ingame, `approve`/`finalize`, commit.
