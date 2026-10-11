# AR0500 — inventaire animation complet

- Campagne : `SoA`
- Map : `AR0500` — Bridge (Athkatla, 80x60 tuiles)
- Inventaire canonique : `54` occurrences BAM, `5` resrefs distincts, `0` WBM, `0` PVRZ ; palettes toutes embarquées
- Lot : `2` resrefs `non-traité` (`FLAME2L`, `FLIESS`), `29` occurrences AR0500, `27` frames source
- Hors lot : `CHIMSMK` (`validé-x4`), `FIRE_3` (`validé-x4`), `FLIESL` (`validé-natif`)
- Sources : `animations/index/zones.csv`, `occurrences.csv`, `animation_upscale_registry.csv`, `ressources/<RESREF>/source.bam`
- Scan de travail antérieur : aucune trace pour `FLAME2L` (ni run, batch, pack, rétention). `FLIESS` : essai xBR2 + nearest2 du 2026-09-18 (run supprimé), identique à la source agrandie ; sorti du lot AR0406, natif probable.

| Resref | Statut | Frames | Taille max x1 | Occ. AR0500 | Flags ARE | Autres maps | Frame montrée |
|---|---|---:|---:|---:|---|---|---:|
| `CHIMSMK` | `validé-x4` | 12 | 64x64 | 19 | `0x1043` | AR0300, AR0400, AR1100, AR2000 | 8 |
| `FIRE_3` | `validé-x4` | 14 | 24x40 | 2 | `0x1043` | AR0202, AR0331, AR0526, AR0906, AR3001, AR5000, OH4200, OH4210, OH4220 | 2 |
| `FLAME2L` | `non-traité` | 9 | 13x29 | 13 (11 `0x1043` + 2 `0x1143`) | `0x1043` / `0x1143` | AR0512, OH4220, OH7000 | 0 |
| `FLIESL` | `validé-natif` | 18 | 64x64 | 4 | `0x1005` | 19 maps (AR0201, AR0206, AR0400, AR0406, AR0502, AR1302, AR2000…) | 1 |
| `FLIESS` | `non-traité` | 18 | 12x13 | 16 | `0x1005` | AR0201, AR0206, AR0400, AR0406, AR0502, AR1302, AR2000, AR5000, AR6300, AR6400, OH6400 | 2 |

Planche : [`review/AR0500-one-frame-per-animation.png`](review/AR0500-one-frame-per-animation.png). PNG x1 individuels : `review/representative-frames/`.

Frame représentative = maximum de pixels visibles (alpha BAM binaire).

- `FLAME2L` : flamme 13x29, 9 frames, **Blended** (bit 1 posé : `0x1043`/`0x1143` sur AR0500, `0x1003` AR0512/OH4220, `0x1043` OH7000). Partagé avec `AR0512` (map dont c'est la seule animation : le traiter la termine), `OH7000`, `OH4220`. Deux occurrences AR0500 en `0x1143` (bit `0x100` de plus) : sans effet sur le pack (par ressource), à observer en QA.
- `FLIESS` : 4 px visibles au plus (frame montrée : 4 px). Décision du 2026-09-18 : natif probable comme `FLIESL` ; `finalize` exige la QA des 12 zones qui le portent.
- Map complète après le lot : `AR0500` sans animation vanilla restante ; `AR0512` complète par extension de signature `FLAME2L`.

## Recette validée (2026-09-21)

Aucun run produit ; recette choisie par analogie mesurée (`FLAME2M`, `FLAME2S`), pas encore exécutée.

| Resref | Recette | Analogues `validé-x4` / `validé-natif` |
|---|---|---|
| `FLAME2L` | `run_animation_upscale.py --prepare-only` → ReboutCX x4 (`run_animation_reboutcx_x4.py`, alpha source nearest x4) → `build_animation_runtime_pack.py`, **cadence native** (9 frames, lookup 0..8, 9 uniques, aucun maintien) → découpe par zone → `build_blended_rgb_neutral_pack.py --mode premultiply --inner-feather-x4 16` | `FLAME2M` (rayon 12), `FLAME2S` (rayon 20) |
| `FLIESS` | `validé-natif` : BAM conservé, aucun run ni pack | `FLIESL` |

- Mesures source (sat / σ lum / lum moy.) : `FLAME2L` 58,6 % / 85,5 / 105,8 ; `FLAME2M` 56,7 / 84,6 / 94,9 (ReboutCX) ; `FLAME2S` 72,9 / 50,8 / 61,3 ; `FIRE_4` 77,0 / 67,6 / 71,5 (SeedVR). SeedVR écarté : `FLAME2L` sort de la grappe « flamme saturée sombre » et `FLAME2S` en SeedVR a été jugé trop dur (lame à arêtes nettes).
- Rayon 16 : **hérité et partiellement mesuré**. Anneau intra-masque sombre identique aux frères (lum. 30 à 1 px, 67 à 2 px, 213 au cœur), rayon inscrit 5,92 px x1 (`FLAME2S` 6,0) → règle 0,83 x rayon inscrit x4 = 20. Simulation sur nearest x4 : cœur -3,6 % à 16, -10 % à 20, -24 % à 24. Retenu 16 ; balayage 12/16/20 à refaire sur la sortie ReboutCX réelle (coins ≈ 0, cœur ≥ -5 %).
- Pas de spline (< 64 px logique), pas d'Apollo 30 fps (aucune flamme Blended de la famille ne l'utilise), pas de padding canvas (`--gaussian-preserve-geometry` non applicable : aucun flou).
- Zones du pack : `AR0500`, `AR0512`, `OH4220`, `OH7000` (signature identique). `AR0512` en `0x1003` (couvert par les murs) : surveiller l'occlusion.

## Traitement et installation (2026-09-21)

- Run : `animations/ressources/FLAME2L/runs/flame2l-reboutcx-x4-20260921` (prepare-only → ReboutCX x4 → `03_runtime_pack`, 9 frames, 13x29 → 52x116, alpha strictement 0/255).
- Balayage sur la sortie ReboutCX réelle (AR0500, premultiply, part. lum. du cœur p95 / bord 4 px / lumière totale vs alpha binaire) : R=12 +0,4 % / 0,31 / -21,7 % ; **R=16 -2,6 % / 0,18 / -33,0 %** ; R=20 -9,7 % / 0,12 / -44,6 % (frange verdâtre au bas du cœur à 20). Retenu 16 : plus grand rayon avec cœur ≥ -5 %, halo rectangulaire du binaire supprimé (rendu additif sur sol sombre contrôlé).
- Packs : split `packs-par-zone/flame2l-reboutcx-x4-split-20260921` → final `flame2l-reboutcx-x4-innerfeather16-premul-20260921` (signature `9cf8e8eea5c5` identique sur `AR0500`, `AR0512`, `OH4220`, `OH7000`). Fusions : `flame2l-ar0500-merged-20260921` (CHIMSMK + FIRE_3 + FLAME2L), `flame2l-oh4220-merged-20260921` (FIRE_3 + FLAME2L).
- Installé (AreaTest, sauvegardes `backups/animations/area-tests/{AR0500,AR0512,OH4220,OH7000}-20260921T1926*`) ; `area_pack_state.py status --deep` : 192/192 conformes, signatures CHIMSMK `0c17449089e0` et FIRE_3 `c2cebb655fd3` inchangées. `AR0512` et `OH7000` n'étaient pas servies avant.
- `FLIESS` : rien à installer (natif). Décision `validé-natif` à sceller par `finalize` après QA.
- Non fait : QA ingame, `finalize`/registre, commit.
