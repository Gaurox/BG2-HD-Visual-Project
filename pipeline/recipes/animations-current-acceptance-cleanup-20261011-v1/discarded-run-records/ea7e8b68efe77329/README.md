# OH7200 — inventaire animation complet

- Campagne : `SoA`
- Map : `OH7200` — Hexxat, quartier bas droit (Zakhara), 44x32 tuiles
- Inventaire canonique : `29` occurrences BAM, `1` resref, `0` WBM, `0` PVRZ ; palette embarquée
- Lot : `FLMM` (`non-traité`), `29` occurrences OH7200, `6` frames source ; la map n'a aucune autre animation
- Sources : `animations/index/zones.csv`, `occurrences.csv`, `animation_upscale_registry.csv`, `ressources/FLMM/source.bam`
- Scan de travail antérieur : aucune trace (runs, batches, packs, rétention, dossier de ressource).
- Choisi parce que la recette est quasi certaine (analogue direct `FLAME2M`, 8x16) et sans risque d'occlusion : toutes les occurrences sont en `0x1043` (bit 6 posé = non couvert par les murs). Les autres maps SoA à un seul `non-traité` : `OH5300` `FPIT1L` (4 occurrences toutes couvertes par les murs, masques peints probables), `OH4101`/`AR0203` `FIRE_3GS`/`FIRE_3GR` (flammes sombres désaturées, sat 32-36 %), `AR0902`, `AR1101`, `AR3019/3020/3022`, `AR1512/1516`, `AR0502`, `AR2903`.

| Resref | Statut | Frames | Taille max x1 | Occ. OH7200 | Flags ARE | Autres maps | Frame montrée |
|---|---|---:|---:|---:|---|---|---:|
| `FLMM` | `non-traité` | 6 | 8x15 | 29 | `0x1043` (Blended) | OH7300 (28 occ., ToB) | 0 |

Planche : [`review/OH7200-one-frame-per-animation.png`](review/OH7200-one-frame-per-animation.png). PNG x1 individuel : `review/representative-frames/`.

Frame représentative = maximum de pixels visibles (alpha BAM binaire).

- Positions x1 (échantillon) : (567,470), (715,354), (802,259), (1024,259), (522,818), (381,818), (382,977), (756,795).
- Mesures source (sat / σ lum / lum moy. / écart inter-frames / lum. à 1 px du bord) : `FLMM` 81,1 % / 61,4 / 118,9 / 43,6 / 74 ; 6 frames uniques, un seul composant connexe. Frères `Blended` validés en ReboutCX : `FLAME2S` 72,9 / 50,8 / 61,3, `FLAME2M` 56,7 / 84,6 / 94,9.
- Écart inter-frames élevé (43,6, `FLAME2L` en était à ~30) : l'interpolation 30 fps est à juger (les flammes de la famille `FLAME2*` sont en cadence native).
- Recette probable : `PETITE-FLAMME-REBOUTCX-PREMUL` (ReboutCX x4, `build_blended_rgb_neutral_pack.py --mode premultiply`, rayon par balayage, `FLAME2M` = 12). Complète `OH7200` ; `OH7300` (ToB) par extension de signature, mais il garde `AMOH7300`, `OHHNECR`, `FIRE`… autres.

## Recette analysée (2026-09-21)

Essais x1 (aucun pack de production, rien d'installé) : `review/` non alimenté ; runs `animations/ressources/FLMM/runs/flmm-reboutcx-x4-20260921` (réutilisable, runtime pack construit, split `packs-par-zone/flmm-reboutcx-x4-split-20260921`) et `flmm-seedvr7b-lab-x4-20260921` (comparatif, jetable).

| Resref | Recette | Analogues |
|---|---|---|
| `FLMM` | ReboutCX x4 (alpha nearest x4) → **cadence native** (6 frames uniques, lookup 0..5, aucun maintien) → découpe par zone (`OH7200`, `OH7300`) → `build_blended_rgb_neutral_pack.py --mode premultiply --inner-feather-x4 6` | `FLAME2M` (8x16, rayon 12), `FLAME2S`, `FLAME2L` |

- SeedVR 7B écarté : il dessine des visages et des personnages à la place de la flamme (6 frames sur 6). ReboutCX reste une flamme lisse et cohérente.
- Apollo-8 30 fps impossible en l'état : Topaz plante sur le canevas x4 32x60 (`tvai_fi`, assertion OpenCV `roi`), le plan (aucun maintien, `collapse_eligible=false`, 12 phases, 0,4 s) passe mais le build échoue. Avec un canevas rembourré (64x96 ou 96x128, bord répliqué) Topaz sort 13 frames, mais les intermédiaires dépendent du remplissage (écart moyen jusqu'à 14 entre les deux tailles) et montrent des artefacts de bord (ph1, ph7). Non retenu ; un 30 fps demanderait une option rembourrage/recadrage sur l'entrée Topaz dans `run_animation_upscale_30fps_v2.py` (outil à écrire, résultat à juger). La famille `FLAME2S/M/L` est en cadence native, acceptée.
- Rayon 6 : **mesuré, partiellement hérité**. Le masque de `FLMM` touche le bord du canevas (luminance 19,0 à 3 px du bord du canevas en binaire : contour rectangulaire) et son rayon inscrit x4 moyen est 11,1 contre 24 pour `FLAME2S`/`FLAME2L`, donc le rayon des frères (12/16/20) l'éteint. Balayage sur la sortie ReboutCX réelle (cœur p95 / lumière totale / bord 3 px) : R=4 -0,1 % / -24,7 % / 3,4 ; **R=6 -1,3 % / -35,8 % / 1,7** ; R=8 -5,6 % / -46,8 % / 1,0 ; R=12 -29,1 % / -65,9 % / 0,5. Retenu 6 (plus grand rayon mesuré gardant le cœur à -5 % ou mieux) ; la proportion 0,83 × rayon inscrit donnerait 8 (limite). À reconfirmer en jeu.
- Occlusion : `OH7200` et `OH7300` en `0x1043` (non couvert par les murs), aucun masque.
- Fusion prévue : `OH7300` porte déjà `FPIT1S` et `FIRE` (fusionner sans changer leurs signatures) ; `OH7200` n'est pas servie.

## Traitement et installation (2026-09-21)

- Rayon 6 retenu (demande « go reboutcx et installe » sur la recette analysée). Pack final `packs-par-zone/flmm-reboutcx-x4-innerfeather6-premul-20260921`, signature `f371fb37301f` sur `OH7200` et `OH7300`, cadence native (6 frames).
- Fusion `OH7300` : `packs-par-zone/oh7300-lot-flmm-merged-20260921` = `FPIT1S` + `FIRE` + `FLMM`, signatures `FPIT1S` `8f02b1171edc` et `FIRE` `119f5fae0d9f` inchangées. `OH7200` servie pour la première fois.
- Installé (AreaTest, sauvegardes `backups/animations/area-tests/{OH7300,OH7200}-20260921T2047*`) ; `status --deep` : 194/194 conformes.
- Non fait : QA ingame, `finalize`/registre, commit.
