# AR3000 — inventaire animation complet

- Campagne : `SoA`
- Map : `AR3000` — Watcher's Keep (entrée)
- Inventaire canonique : `16` occurrences BAM, `9` resrefs distincts, `0` WBM, `0` PVRZ
- Nouveau lot : `8` resrefs (`7` `non-traité` + `1` `à-compléter`), `13` occurrences AR3000, `151` frames source
- Hors lot : `BUTRFLY` (`validé-x4`, 3 occurrences, ressource partagée par 14 maps)
- Sources : `animations/index/zones.csv`, `occurrences.csv`, `animation_upscale_registry.csv`, `ressources/<RESREF>/source.bam`

| Resref | Statut | Frames | Taille max x1 | Occ. AR3000 | Flags ARE | Autres maps | Frame montrée |
|---|---|---:|---:|---:|---|---|---:|
| `AM3000A` | `à-compléter` | 16 | 248x221 | 1 | `0x1044` | — | 0 |
| `AM3000E` | `non-traité` | 24 | 39x68 | 5 | `0x1403` | — | 8 |
| `AM3000H` | `non-traité` | 15 | 114x119 | 1 | `0x1045` | — | 0 |
| `FISH1L` | `non-traité` | 24 | 64x64 | 2 | `0x1005` | AR5000 | 5 |
| `FISH1S` | `non-traité` | 18 | 32x32 | 1 | `0x1005` | — | 6 |
| `FISH2L` | `non-traité` | 18 | 64x64 | 1 | `0x1005` | AR5000 | 6 |
| `FISH2S` | `non-traité` | 18 | 32x32 | 1 | `0x1005` | AR5000 | 6 |
| `FISH3S` | `non-traité` | 18 | 32x32 | 1 | `0x1005` | AR5000 | 6 |

Planche : [`review/AR3000-one-frame-per-animation.png`](review/AR3000-one-frame-per-animation.png). PNG x1 individuels : `review/representative-frames/`.

Frame représentative = maximum de pixels visibles (alpha BAM binaire).

- `AM3000A` : coupole ; seule la frame 000 avait été traitée en x4, prototype mis de côté (registre). Reprendre à zéro.
- `FISH1L/2L/2S/3S` partagés avec `AR5000` : traiter une fois profite aux deux maps ; `AR5000` hors périmètre de ce lot.
- Bit 1 (Blended) posé uniquement sur `AM3000E` (`0x1403`) ; absent des sept autres.

## Recettes retenues et upscales produits (2026-09-18)

Aucun pack, timeline 30 fps, masque ni installation produits : étage spatial x4 uniquement.

| Resref | Recette | Analogues `validé-x4` | Run spatial |
|---|---|---|---|
| `AM3000A` | `MECANIQUE-SEEDVR-ALPHA-NATIVE` : SeedVR2 7B/LAB x4 → Apollo-8 → alpha source nearest, RGB caché nearest-opaque, sans spline/feather | `AM3017A–D`, `AM3016T`, `AM0603C1/C2` | `ar3000-decor-seedvr7b-lab-x4-20260918` |
| `AM3000H` | Silhouette organique fermée, alpha binaire, non Blended : SeedVR2 7B/LAB x4 → Apollo-8 → Spline Fit 1 + feather intérieur `4 px x4` (règle du catalogue) | `AM3016E/G` (bassins), `AM3011A` (forme) | `ar3000-decor-seedvr7b-lab-x4-20260918` |
| `AM3000E` | **Hors pipeline** : 5 occurrences `DoorMist01–05` en palette externe `PLT_MAGE` ; `run_animation_upscale.py` refuse (`external-palette-PLT_MAGE`) ; le chemin x4 ne reçoit pas la palette réalisée. Reste vanilla. | — (`AMSTEAM1/2`, `CHIMSMK` ont une palette embarquée) | — |
| `FISH1L/1S/2L/2S/3S` | Deux tests comparatifs, pas de SeedVR : (a) `xBR2 → nearest2` sans blend (recette `BUTRFLY`) ; (b) ReboutCX x4, alpha nearest x4 | `BUTRFLY`, `FLIESL` | `ar3000-fish-xbr2x-nearest2-x4-20260918`, `ar3000-fish-reboutcx-x4-20260918` |

- Mesures source (sat / σ lum / lum moy.) : `AM3000A` 33 % / 51 / 100 ; `AM3000H` 53 % / 52 / 102 ; fish 24–32 % / 54–59 / 102–153.
- Runner ReboutCX animation ajouté : `pipeline/scripts/run_animation_reboutcx_x4.py` (Python chaiNNer, fp16, RGB rempli nearest-opaque, alpha nearest).
- `AM3000H` : le x4 SeedVR 7B crée des hachures anguleuses dans la mousse (précédent `AM0602C/D/E/G` : 7B rejeté, 3B retenu). Repli à tester : SeedVR2 3B.
- Fish : cycles avec maintien terminal long (ex. `FISH1S` : frame 17 répétée) → audit du lookup avant Apollo.

Planches : `review/AR3000-upscale-decor-seedvr.png`, `review/AR3000-upscale-fish-xbr-vs-reboutcx.png`.

## Traitement complet (2026-09-18) — pack `AR3000` prêt pour essai ingame

Pack feuille : `animations/packs-par-zone/ar3000-complete-map-lot-20260918/AR3000` (8 ressources, 217 505 024 octets < 512 Mio, `-VerifyOnly` OK). Il représente l'état complet de la zone : `BUTRFLY` repris du master `combined-20260904-fpit1s-contour-fondu-J` + les 7 nouvelles. `AM3000E` absent (vanilla, palette externe).

| Resref | Chaîne exécutée | Run / pack source |
|---|---|---|
| `AM3000A` | SeedVR2 7B/LAB x4 → Apollo-8 15→30 fps (cycles 1/2 interpolés, cycles 0/3 statiques) → fade contour intérieur `36 px x4`, RGB droit dilaté sous alpha nul, alpha final ≤ source | `ar3000-decor-seedvr7b-lab-x4-20260918` → `ar3000-decor-apo8-x4-30fps-v2-20260918` → `ar3000-am3000a-innerfade36-straightrgb-20260918` |
| `AM3000H` | SeedVR2 7B/LAB x4 → Apollo-8 (15→30 phases) → Spline Fit 1 multi-contour + feather intérieur `4 px x4`, `--rgb-policy preserve` | idem → `animations/ressources/AM3000H/runs/ar3000-am3000h-spline-fit1-feather4-20260918` |
| `FISH1L/1S/2L/2S/3S` | xBR2 sans blend → nearest2 x4 (xBR retenu, ReboutCX écarté) → Apollo-8 `--preserve-segmented-holds` (poses de saut interpolées, pause vide finale/initiale référencée à l'identique, durées 5,6–8,4 s conservées), RGB Topaz `nearest-opaque-dilate`, alpha binaire xBR inchangé, aucun masque | `ar3000-fish-xbr2x-nearest2-x4-20260918` → `ar3000-fish-xbr-apo8-x4-30fps-v2-20260918` |

- Choix `AM3000A` : recette « alpha strict + fade contour 36 » = état final accepté ingame sur `AM3017A–D` (le plan initial alpha-natif pur a été supplanté à la QA AR3017). Variante alpha-native non dégradée disponible dans `ar3000-decor-apo8-x4-30fps-v2-20260918/03_runtime_pack`.
- Non-Blended (`0x1044`, `0x1045`, `0x1005`) : aucune neutralisation RGB ; `BUTRFLY` garde sa neutralisation historique.
- Correctif outil : `run_animation_upscale_30fps_v2.py` — une frame entièrement transparente (pause vide des fish) empruntait auparavant `RuntimeError` ; elle reprend maintenant le RGB dilaté de sa voisine visible dans le lookup (alpha inchangé). Comportement identique pour tout run qui aboutissait avant.
- Planche de phases : `review/AR3000-final-pack-timeline-phases.png`. Vidéos : `work/*/cycle_*/review-30fps-*.mp4` dans chaque run 30 fps.
- Non fait : installation, QA ingame, registre/sélection, release.

## Révision AM3000H — fade de contour (2026-09-18)

Demande utilisateur : fondu de transparence sur le contour pour mieux intégrer `AM3000H` à la map. Ajout, par-dessus le spline : `derive_animation_visual_treatment.py --inner-contour-fade-x4 36 --rgb-policy preserve` → `animations/ressources/AM3000H/runs/ar3000-am3000h-spline-fit1-innerfade36-20260918` (alpha somme −16 %, alpha final ≤ source). Pack zone : `animations/packs-par-zone/ar3000-complete-map-lot-v2-am3000h-fade-20260918/AR3000` (remplace le pack `…-lot-20260918`). Comparatif : `review/AM3000H-avant-apres-fade36.png`.
