# Lot de 15 assets — AR6200 + AR4500 + AR5202

- Campagne : `ToB` (les trois maps ; `areas.csv` : `validated-installed`, pas de variante nuit)
- Demande : 15 assets `non-traité` sur un minimum de maps. Minimum = 3 maps : le plus gros couple (`AR6200` 9 assets + `AR4500` 5) plafonne à 14, aucune paire n'atteint 15.
- Choix : `AR6200` (9) + `AR4500` (5) + `AR5202` (1, `AM5202B`) = **15 assets, 3 maps, 15 occurrences**. Chaque asset n'apparaît que dans sa map (aucune extension par signature, aucune autre zone à QA). Après le lot, les trois maps n'ont plus aucune animation `non-traité` (`AR5202` garde `FIRE_4` et `FPIT1S`, déjà validés).
- Alternative écartée : `AR6200` + `AR5502` (4) + `AR5500` (2) = 15, mais `AM5508C/D` sont partagés avec `AR5501`, `AR5506`, `AR5507`, `AR5508` (5 maps touchées).
- Scan de travail antérieur : aucune trace pour les 15 (runs, batches, packs, rétention, dossiers de ressources) ; seul un dossier d'inventaire `ar6200-complete-map-inventory-20260918/review` existe.
- Sources : `animations/index/zones.csv`, `occurrences.csv`, `animation_upscale_registry.csv`, `ressources/<RESREF>/source.bam`

| Resref | Map | Frames | Taille max x1 | Occ. | Flags ARE | Blended | Couvert par murs | sat / σ lum / lum moy. / écart frames | Frame montrée |
|---|---|---:|---:|---:|---|---|---|---|---:|
| `AM6200A` | AR6200 | 20 | 149x179 | 1 | `0x1243` | oui | non | 15,8 / 50,7 / 213,2 / 22,1 | 5 |
| `AM6200B` | AR6200 | 20 | 149x179 | 1 | `0x1242` | oui | non | 15,5 / 51,1 / 214,3 / 21,8 | 5 |
| `AM6200E` | AR6200 | 5 | 110x95 | 1 | `0x1103` | oui | oui | 36,1 / 77,5 / 151,5 / 30,7 | 4 |
| `AM6200F` | AR6200 | 5 | 94x86 | 1 | `0x1103` | oui | oui | 34,5 / 81,0 / 151,8 / 35,3 | 0 |
| `AM6200G` | AR6200 | 5 | 87x76 | 1 | `0x1103` | oui | oui | 36,7 / 60,5 / 177,1 / 20,0 | 3 |
| `AM6200H` | AR6200 | 9 | 164x116 | 1 | `0x1101` | non | oui | 32,4 / 27,1 / 220,1 / 1,9 | 0 |
| `AM6200I` | AR6200 | 9 | 159x107 | 1 | `0x1101` | non | oui | 34,4 / 16,9 / 225,4 / 2,2 | 7 |
| `AM6200J` | AR6200 | 9 | 158x99 | 1 | `0x1101` | non | oui | 17,0 / 11,6 / 243,4 / 1,8 | 4 |
| `MMELSPIN` | AR6200 | 20 | 63x96 | 1 | `0x1211` | non | oui | 32,5 / 23,8 / 15,6 / 17,5 | 7 |
| `AM4500A` | AR4500 | 8 | 105x144 | 1 | `0x1003` | oui | oui | 31,6 / 36,9 / 71,5 / 17,7 | 7 |
| `AM4500B` | AR4500 | 8 | 96x134 | 1 | `0x1103` | oui | oui | 33,6 / 37,4 / 71,8 / 19,2 | 7 |
| `AM4500C` | AR4500 | 8 | 61x142 | 1 | `0x1003` | oui | oui | 23,5 / 36,5 / 66,5 / 17,6 | 0 |
| `AM4500D` | AR4500 | 8 | 130x142 | 1 | `0x1003` | oui | oui | 28,3 / 34,8 / 68,2 / 20,3 | 7 |
| `AM4500E` | AR4500 | 8 | 76x145 | 1 | `0x1003` | oui | oui | 23,2 / 34,5 / 65,3 / 17,3 | 0 |
| `AM5202B` | AR5202 | 15 | 52x109 | 1 | `0x1003` | oui | oui | 36,3 / 88,9 / 144,6 / 20,5 | 11 |

Planche : [`review/LOT15-one-frame-per-animation.png`](review/LOT15-one-frame-per-animation.png). PNG x1 individuels : `review/representative-frames/`.

Frame représentative = maximum de pixels visibles (alpha BAM binaire). Toutes les frames de chaque asset sont uniques (hash RGBA) ; 15 assets à 1 occurrence.

## Familles visuelles (pour regrouper les recettes)

- **Énergie verte, colonnes de lumière** : `AM6200A`, `AM6200B` (20 frames, 149x179, Blended, `0x124x`), `AM5202B` (15 frames, 52x109, colonne verte à cœur blanc) ; frères directs.
- **Énergie verte, plaques déchirées** : `AM6200E/F/G` (5 frames, Blended, écart 20-35 = mouvement fort).
- **Disques verts** : `AM6200H/I/J` (9 frames, 158-164 px, non Blended, presque statiques : écart 1,8-2,2, 69-78 % de couverture) ; silhouette elliptique aux bords dentelés, cousins des portails/bassins (`PORTL*`, `LIQUIDE-*`).
- **Cristaux violets** : `AM4500A-E` (8 frames chacun, Blended, sombres : lum 65-72), même géométrie de lames inclinées, 5 variantes.
- **Silhouette sombre** : `MMELSPIN` (63x96, 20 frames, lum moy. 15,6, non Blended, `0x1211`) : personnage noir à liseré rouge ; cas à part (SeedVR sur sujet sombre et fin).

## Points d'attention avant de choisir les recettes

- 10 assets `Blended` sur 15 : la neutralisation RGB (premultiply) s'applique ; `AM6200A/B` ont des moyennes très claires (213-214) avec faible saturation, profil des feux pâles où SeedVR invente (`FIRE`, `FPIT1M`) : essai comparatif ReboutCX/SeedVR.
- `AM6200H/I/J` : non Blended, quasi statiques (écart ≈ 2) : Apollo-8 apporte peu ; candidats au natif 15 fps ou à une timeline directe ; silhouette à traiter par spline + feather si le bord est crénelé.
- 5 cristaux `AM4500*` de même famille : une recette, un run par ressource, `--mode premultiply` ; mouvement fort (17-20).
- Occlusion : `AM6200A/B` non couverts par les murs (bit 6) ; les 13 autres le sont (`0x1103`, `0x1101`, `0x1003`, `0x1211`) : les Blended n'ont pas de pont d'occlusion fonctionnel, à observer en QA sur `AR6200`, `AR4500`, `AR5202` (masques peints à prévoir seulement si l'animation passe par-dessus un mur).
- Volume : plus gros asset `AM6200A/B` 20 frames x 149x179 en x4 (~2,3 Mo/phase x 40 phases si 30 fps) ; budget par zone 512 Mio largement respecté.

## Traitement et installation (2026-09-22, nuit ; `AM5202B` exclu à la demande, lot = 14 assets sur `AR6200` + `AR4500`)

Aucune validation utilisateur avant installation : QA prévue le lendemain. Rien de finalisé (`finalize`, registre, commit non faits). Runs sous `animations/ressources/<RESREF>/runs/*-20260922` ; packs sous `animations/packs-par-zone/` (`lot14-ar4500-merged-20260922`, `lot14-ar6200-merged-20260922`, finals et splits par asset) ; sauvegardes `backups/animations/area-tests/{AR4500,AR6200}-20260921T2246*`.

| Assets | Spatial | Temporel | Bord / neutralisation |
|---|---|---|---|
| `AM4500A-E` (cristaux) | ReboutCX x4 : SeedVR crée des motifs de circuit et des lignes (HF x3), ReboutCX garde le halo violet en lissant les paillettes | Apollo-8 15→30, 8→16 phases, 0,533 s, `nearest-opaque-dilate` | `premultiply --inner-feather-x4 16` |
| `AM6200A`, `AM6200B` (colonnes) | ReboutCX x4 (SeedVR ≈ équivalent sur zone blanche saturée, HF x3,6) | Apollo-8 avec `--collapse-uniform-duplicate-holds` (10 poses x2 slots, cycles 0 et 1 : 40 phases, 1,333 s chacun) | `premultiply --inner-feather-x4 16` |
| `AM6200E`, `AM6200F` (plaques) | SeedVR2 7B/LAB x4 : veines d'énergie nettes, couleur conservée ; ReboutCX les lisse et ternit le vert | Apollo-8 avec `--collapse-uniform-duplicate-holds` (5 poses x2, 20 phases, 0,667 s) | `premultiply --inner-feather-x4 16` |
| `AM6200G` (plaque) | SeedVR2 7B/LAB x4 (cohérence avec E/F) | Apollo-8 direct, 5→10 phases, 0,333 s | `premultiply --inner-feather-x4 16` (balayage sur la silhouette seule) |
| `AM6200H/I/J` (disques) | ReboutCX x4 : disque quasi statique (écart 1,9), SeedVR le fait scintiller (écart 5,2, HF x4) | Apollo-8 direct 9→18 phases, 0,6 s (sans effet visible attendu, sert d'outillage V2) | `derive_animation_visual_treatment.py --inner-contour-fade-x4 4 --rgb-policy preserve` (non Blended) |
| `MMELSPIN` | ReboutCX x4 | **natif** (20 frames, 9 cycles identiques : un Apollo par cycle x9 non rentable, alpha qui change de 40 % par frame) | aucune (non Blended, alpha nearest x4) |

- Audit des doublons (`plan`) : `AM6200A/B/E/F` = maintiens uniformes x2 (`collapse_eligible=true`, cycles 0 et 1 pour A/B), tous les autres = aucun maintien. Contrôle des packs 30 fps : frames toutes distinctes, aucun pas nul (min 0,35 à 4,2), couture dernier → premier de 0,8 à 5,5, teinte des intermédiaires proche des ancres (écart < 2,5 sauf `AM6200G` +4,8 % plus clair).
- Rayon 16 = plafond du balayage {4, 8, 12, 16} : le critère « cœur p99 ≥ -5 % et lumière de la silhouette ≥ -35 % » est satisfait partout (cœur ±0,1 %, lumière -14 à -22 %), donc rayon non discriminant ; à réduire (8 ou 4) si les bords paraissent trop dilués en jeu.
- Hérité, non balayé : `inner-contour-fade` 4 (discs), Apollo sur `AM6200H/I/J`, choix SeedVR/ReboutCX par famille sur un représentant (`AM4500A`, `AM6200A`, `AM6200E`, `AM6200H`).
- `AM6200A/B` : cycle 1 (frames 10-19) jamais joué (sequence 0) mais interpolé et installé ; pack `AR6200` 359 Mo (plafond 512 Mio) ; à élaguer si la charge de zone pose problème.
- Occlusion : seuls `AM6200A/B` ne sont pas couverts par les murs ; les 12 autres le sont (Blended : pont natif sans effet).

## Correctif contour crénelé sur les disques (2026-09-22)

Signalé par l'utilisateur en jeu (AR6200) : `AM6200H/I/J` avaient un contour en escalier visible. Cause : `derive_animation_visual_treatment.py --inner-contour-fade-x4 4` adoucit l'intensité du bord mais ne change pas sa forme, qui reste l'escalier de 4 px du nearest-neighbour. Remplacé par la recette des portails (`PORTAIL-SEEDVR-SPLINE8`) : `build_per_frame_spline_alpha_30fps_v2.py --fit-error 1.0 --sample-spacing 1.5 --supersample 4 --padding-x4 32 --inner-feather-x4 8 --rgb-policy preserve`, appliqué sur le run 30 fps (`*-reboutcx-apo8-x4-30fps-v2-20260922`).

- Les 3 sont `fitted`, 1 composant par frame (2 sur 2 frames d'`AM6200J`, cf. la fine encoche sombre visible en haut à gauche de sa silhouette). RGB identique octet pour octet. IoU contre le binaire d'origine : `H` 0,969, `I` 0,954, `J` 0,936 (fondu 8 px, cohérent avec les autres spline).
- Comparatif avant/après : contour lisse et net sur les trois, escalier disparu (zoom conservé, non versionné).
- Signatures : `AM6200H` `2bb252332035`, `AM6200I` `f23ebadda164`, `AM6200J` `612a44ccca6b` (les 6 autres assets d'`AR6200` inchangés). Pack `packs-par-zone/lot14-ar6200-merged-v2-discfix-20260922`. Réinstallé (sauvegarde `backups/animations/area-tests/AR6200-20260922T0514*`).
- Toujours en attente de QA complète, `finalize` et commit.
