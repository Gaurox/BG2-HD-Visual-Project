# Catalogue court des recettes animation

But : choisir une base par **structure visuelle et alpha**, puis adapter cycles, pauses et canvas.
Une ressemblance de couleur seule ne suffit pas.

| Modèle | Assets adaptés | Recette de base | Exemples `validé-x4` |
|---|---|---|---|
| `FX-FIN-XBR-AURA` | Feu, éclair, filament, particules lumineuses ; petit sujet, contours fins/fragmentés, souvent `Blended` | `xBR2 ×2` → TimedTimeline v2 Apollo-8 15→30 → Contour Aura `12/5/0.9/14` → dilatation RGB nearest-opaque ; prémultiplier si `Blended` | `AM3011B` |
| `BULLES-XBR2BLEND-NEAREST2-APO8-PREMUL` | Petites bulles/particules `Blended`, composantes fines de 1..3 px x1 ; alpha fragmenté | xBR2x avec blend → nearest2x (x4 final) → Apollo-8 15→30 (`nearest-opaque-dilate`) → RGB prémultiplié une fois ; alpha xBR conservé, aucun fondu supplémentaire | `BUBBLES2`, `AMOH7300` |
| `LIQUIDE-SEEDVR-SPLINE4` | Surface liquide large et organique : bassin, lave, acide, saumure ; silhouette arrondie stable | SeedVR2 7B INT8/LAB x4 → TimedTimeline v2 Apollo-8 15→30 → Spline Fit 1 multi-contours par frame → feather intérieur `4 px x4` (`6 px x4` pour un bassin ovale de maison : `AM2801A`, `AM2802A`, sans cover, la carte x4 y porte déjà l'eau) | `AM3021D`, `AM3021E`, `AM3021F`, `AM2801A`, `AM2802A` |
| `MECANIQUE-SEEDVR-ALPHA-NATIVE` | Roue, ventilateur, cuve, machine ; arêtes rigides, rayons et trous à préserver | SeedVR2 7B INT8/LAB x4 → TimedTimeline v2 Apollo-8 15→30 → alpha source nearest ; RGB caché nearest-opaque ; **sans spline/feather** | `AM307TT1`, `AM0300A` (cage de brasero, maintiens condensés), `AM3020D` |
| `FUMEE-SEEDVR-SPLINE4-EDGEFADE` | Fumée ou vapeur diffuse touchant le canvas ; multi-contours, `Blended` | SeedVR2 7B INT8/LAB x4 → TimedTimeline v2 Apollo-8 15→30 → Spline Fit 1 multi-contours par frame → feather `4 px x4` → Oval Edge Fade `20/6` → RGB prémultiplié | `CHIMSMK` ; avec flou gaussien `σ 1` à géométrie préservée : `SMOKE`, `STEAM2`, `AM5500A`, `AM6004A`, `AM6004B` |
| `PORTAIL-SEEDVR-SPLINE8` | Portail elliptique à silhouette fermée et alpha binaire | SeedVR2 7B INT8/LAB x4 → TimedTimeline v2 Apollo-8 15→30 → spline périodique Fit 1 → feather intérieur `8 px x4` ; RGB inchangé | `PORTL1A`, `PORTL1B`, `PORTL2A`, `AM1516PT` (encoche sombre suivie par la spline ; SeedVR gardé car ReboutCX dérive vers le violet) |
| `BASSIN-SUR-TROU-DE-CARTE` | Bassin posé sur un trou noir de la carte x4 bordé d'un halo clair, visible en liseré aux bords bas | `LIQUIDE-SEEDVR-SPLINE4` avec feather `6 px x4` → `Lower Edge Cover` : alpha source étendu de `5` lignes x4 vers le bas, lissé par la même spline sans feather, fusionné à `10 px` de l'anneau, RGB repoussé depuis `5 px` à l'intérieur du bord ; géométrie native conservée ; si l'arête basse d'un autre élément (jet contre une statue) ne doit pas être couverte, ajouter `--lower-edge-cover-min-row-x4 <coin gauche/droit du losange - ~8>` | `AM1004A`, `AM1003A` (min-row `190`) |
| `FOYER-SEEDVR-INNERFADE8` | Cheminée ou four dont la silhouette est découpée par d'autres éléments (mobilier, parquet) ; alpha strict, poses doublées | SeedVR2 7B INT8/LAB x4 → TimedTimeline v2 Apollo-8 15→30 `--collapse-uniform-duplicate-holds` → fondu intérieur strict `8 px x4` à bords canvas ouverts, RGB droit ; **aucun flou** sur la flamme | `AM0322A`, `AM0322B`, `AM0323A`, `AM003XA` |
| `RECTANGLE-OPAQUE-ZONE-ANIMEE` | Rectangle opaque (≥ 90 %) touchant les 4 bords, qui repeint sol et décor autour d'un petit élément animé (feu et sa lumière) ; trous de tramage dans l'alpha | Chaîne `FOYER` jusqu'à Apollo-8 → `derive_animation_visual_treatment.py --fill-alpha-holes-max-px-x4 1024 --alpha-mask <masque> --rgb-policy preserve`, masque de `build_animated_zone_mask.py` (variance temporelle x1, fondu 24 px x4 aux bords, retouchable) ; si un polygone WED « Cover animations » traverse la zone animée, lier la ressource à son occurrence (`::RESREF::X,Y`) pour couper le pont d'occlusion x1 | `AM0309A` |
| `PETITE-FLAMME-REBOUTCX-PREMUL` | Petite flamme `Blended` de la famille `FLAME2*` (≤ 13x29) : sat ~57-73 %, anneau intra-masque sombre qui dessine un rectangle une fois ajouté à la scène ; hors grappe SeedVR (`FIRE_*`, sat ≥ 75 %, lum. moy. ≤ 80) | ReboutCX x4 (`run_animation_reboutcx_x4.py`, alpha nearest x4) → **cadence native** → `build_blended_rgb_neutral_pack.py --mode premultiply --inner-feather-x4 <R>` ; R = plus grand rayon gardant le cœur ≥ -5 % (balayage sur la sortie réelle, pas la proportion : `FLAME2S` 20, `FLAME2M` 12, `FLAME2L` 16, `FLMM` 6 car rayon inscrit x4 de 11 contre 24) ; canevas x4 < ~48 px de large : Apollo-8 plante, rester natif ; sujet < ~10 px (`FLMS` 2x5) : visuel donneur réduit (`run_animation_donor_substitution_x4.py`) ; mouches ~1-4 px (`FLIESL`, `FLIESS`) : `validé-natif` | `FLAME2S`, `FLAME2M`, `FLAME2L`, `FLMM`, `FLMS` |
| `FLAMME-BRAISES-REBOUTCX-APO8-PREMUL` | Flamme haute `Blended` claire (sat ~64 %, lum. moy. ~150), alpha fragmenté avec braises détachées de 1 px x1, sans anneau sombre ; SeedVR y invente des filaments | ReboutCX x4 (alpha nearest x4) → Apollo-8 15→30 (`nearest-opaque-dilate`, plan sans maintien ni indice répété) → `build_blended_rgb_neutral_pack.py --mode premultiply --inner-feather-x4 2` (balayage 0/2/4 : au-delà de 4 les braises s'éteignent) ; cadence native possible si les braises fantôment | `FIRE` |
| `BRASERO-REBOUTCX-APO8-AURA` | Foyer/brasero/tas de braises `Blended` où SeedVR aplatit la texture en galets lisses ou invente billes et volutes | ReboutCX x4 → Apollo-8 15→30 (`nearest-opaque-dilate`, sans doublon) → `build_animation_contour_aura_pack.py --inner-feather-x4 <R> --aura-sigma-x4 5 --aura-gain 0.9 --border-margin-x4 14` ; R ≈ 0,13 × largeur du canevas x4 (`FPIT1S` 12 sur 92 px, `FPIT1M` 24 sur 192 px, `AM5204C` 16 sur ~212 px, sous la proportion car le balayage limitait déjà à -5 % de cœur) ; masque d'occlusion peint seulement si l'occurrence est couverte par les murs (bit 6 absent) | `FPIT1M`, `AM5204C` (`FPIT1S` validé en SeedVR avec réserve) |
| `FLAMME-RECTANGLE-NOIR-REBOUTCX-APO8` | Flamme `Blended` dont la frame est un rectangle **100 % opaque sur fond noir** (alpha 255 partout, la flamme n'existe que par le RGB : `FIRE_3GS`, `FIRE_3GR`) ; stats à calculer sur les pixels allumés (lum > 20) ; SeedVR y dessine un visage et scintille (+36 % d'écart entre frames) | ReboutCX x4 → Apollo-8 15→30 (`--base-runtime-only --base-pack <03_runtime_pack>` si le BAM porte des cycles vides terminaux ; couture de boucle adoucie) → `build_blended_rgb_neutral_pack.py --mode premultiply --inner-feather-x4 8` : le canevas opaque est la frontière de l'alpha, donc fondu de bord de canevas qui retire le voile de luminance 3-4 laissé par ReboutCX ; balayer 4/8/12 (bord 4 px, cœur p99, rangées du bas) | `FIRE_3GS`, `FIRE_3GR` |
| `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` | Effet `Blended` divers (cristal, colonne/plaque d'énergie, brume/fumée diffuse) sans anneau sombre caractéristique, pas assez de recul pour un modèle dédié | ReboutCX x4 (SeedVR à comparer systématiquement : hallucine des visages, circuits imprimés, motifs capillaires ou chandeliers sur des zones lisses/diffuses, sauf sur une flamme franche de type `FIRE_4`) → Apollo-8 15→30 (`--collapse-uniform-duplicate-holds` si maintiens uniformes) → `build_blended_rgb_neutral_pack.py --mode premultiply --inner-feather-x4 16` ; si le balayage {4,8,12,16} ne discrimine pas (cœur p99 quasi inchangé partout), prendre le plus grand rayon testé par prudence, pas le plus petit ; sur une brume diffuse, le rayon peut être limité par la perte de lumière totale (≥ -35 %) avant celle du cœur | `AM4500A-E`, `AM6200A`, `AM6200B`, `AM6200E-G`, `AM5502D`, `AM5502F`, `AM5201A`, `AM5201B`, `AM5503A`, `AM5503C`, `AM5503D`, `AM5508C`, `AM5508D`, `OHHNECR`, `AM5202B`, `AM5204A`, `AM3019A` (`AM5204D` en SeedVR, profil `FIRE_4`) |
| **`CONTOUR-NET`** | Objet rigide non `Blended` à alpha binaire (fontaine, statue, socle, architecture) dont la source x1 porte un **liseré sombre de 1 px** : SeedVR l'étale en bande de ~4 px x4 et en dessine l'escalier en encoches, visibles de jour même après spline/flou | `python pipeline/scripts/contour_net.py --spatial-run <run SeedVR x4> --resref <R> [--resref …] --tag <id>` : alpha x4 = Potrace du masque x1 (`--potrace-alphamax 0.8` : arêtes droites, angles vifs ; modifs ≤ 6 px x4 du bord) → RGB du liseré et des pixels gagnés = moyenne gaussienne normalisée de l'intérieur (`--edge-rgb-fill-depth-x4 6 --edge-rgb-fill-sigma-x4 2.5`, cascade 6/4/2 px pour les parties fines) → Apollo-8 15→30 `--base-runtime-only` → découpe → zones reconstruites depuis le verrou (autres ressources gardées) ; installer ensuite avec AreaTest. Diagnostic : luminance par distance intérieure au bord, 1er px x1 nettement plus sombre que l'intérieur (AM5000A : 34 contre 62) | `AM5000A`, `AM5000B` |
| `DISQUE-FERME-REBOUTCX-SPLINE8` | Silhouette fermée non `Blended`, quasi statique ou à texture mobile (contours dentelés ou elliptiques en jeu), touchant le bord du canevas | ReboutCX x4 → Apollo-8 15→30 direct → spline Fit 1 multi-contour + feather intérieur `8 px x4`, `--rgb-policy preserve` (recette portail, PAS `derive_animation_visual_treatment.py --inner-contour-fade-x4` : un simple fondu radial adoucit l'INTENSITÉ du bord mais ne change pas sa FORME, l'escalier x4 reste visible en jeu) | `AM6200H`, `AM6200I`, `AM6200J`, `AM6005A`, `AM3022D` |

## Règles de choix

- **Sujets minuscules** (décision utilisateur, 2026-10-11) : partir directement sur ReboutCX ou xBR ; aucun essai SeedVR pour quelques pixels. Juger le sujet visible et ses détails, pas seulement la taille du canevas. Cette règle prime sur les comparaisons SeedVR systématiques des recettes génériques.
- **Doublons avant interpolation** (rappel utilisateur, 2026-10-11) : dédoublonner les poses identiques ; conserver la durée cible du cycle. Maintiens uniformes ×2 : entrée15/2 FPS → sortie30 FPS, `--collapse-uniform-duplicate-holds` ; ne pas accélérer la boucle en réduisant le nombre de poses.
- **Géométrie** : une frame x4 garde exactement la taille logique de la frame BAM native. Le moteur
  compare cette taille au dessin CVidCell et retombe en vanilla **sans journaliser** si elle diffère —
  donc jamais de rembourrage de canevas (`--gaussian-padding-x4`) ; utiliser `--gaussian-preserve-geometry`.
- `Blended` : neutraliser le RGB transparent et prémultiplier par l'alpha final.
- Détails fins/branches/rayons : préférer xBR ou alpha nearest ; éviter une spline destructrice.
- Silhouette organique fermée : Spline Fit 1 + feather.
- Contour épais/crénelé sur un objet rigide non `Blended` : mesurer d'abord le liseré RGB du bord. S'il est sombre,
  c'est `CONTOUR-NET` ; aucun réglage d'alpha (spline, safe-boundary, flou, fit-error) ne l'amincit, et une
  spline arrondit les angles. Essais écartés sur `AM5000A/B` : 3 splines (surépaisseur, crénelage résiduel,
  sommet arrondi), xBR x4 du masque (pentes faibles ondulées), repoussage RGB au plus proche (stries).
- Reprise d'anciens assets par `CONTOUR-NET` : candidats = non `Blended`, alpha nearest dans le run spatial
  (`MECANIQUE-SEEDVR-ALPHA-NATIVE` : `AM307TT1`, `AM0300A`) ; le script refuse `Blended`, un alpha non nearest
  et une ressource liée à une position (fusion manuelle). Repasser `--preserve-segmented-holds` ou
  `--collapse-uniform-duplicate-holds` si le run 30 fps d'origine les utilisait.
- Timeline : grouper les indices consécutifs du lookup BAM ; ne jamais partir de l'ordre brut des frames.
- Maintiens uniformes : dédupliquer la base, réduire sa cadence pour garder la même durée, puis interpoler.
- Pauses asymétriques/intentionnelles, frames réutilisées ou maintien à la couture : conserver ou spécifier par segment.
- Bord du canvas touché : ajouter un fade/canvas seulement si la coupure est visible.
- `AMWRPGT1` : variante candidate `Safe Boundary 8/6 + Gaussian 3`; non validée. Le défaut cyan connu vient du PVRZ BC1, pas de l'asset.

Sources de décision : `index/animation_upscale_registry.csv`, `index/animation_alpha_corrections.csv`, `index/qa-decisions/`.

## Foyers Umar — validés ingame le 2026-10-09

Base `umar-foyer-seedvr-apo8` : SeedVR2 7B INT8/LAB x4 → Apollo-8 TimedTimeline 15→30, 18 phases / 0,6 s ; RGB droit, dimensions/centres natifs conservés. FIRE_4/FLAME2S préexistantes conservées dans les packs complets.

| Asset / zone | Correctif final | Autorité courante |
|---|---|---|
| AM1101A / AR1101 | Spline Fit1 feather8 ; WED15 hotte : distance analytique x4 + raccord4 ; lié à571,379 ; WED17 retiré, banc déjà peint dans l'asset restauré exact. | [Sélection](index/selections/AM1101A.json) |
| AM1104A / AR1103 | InnerFade8, bords canvas ouverts ; fondu local24 sur les deux limites sous hotte, colonnesx4 0..218 ; pas de WED intersectant. | [Sélection](index/selections/AM1104A.json) |
| AM1104B / AR1104 | InnerFade8 ; WED21 pilier : fondu24 côté visible, lié à372,246 ; bord gauche : retrait8/raccord4 x4. | [Sélection](index/selections/AM1104B.json) |

- Coupe interne crénelée inchangée après spline : recaler la capture sur le WED ; la spline du contour extérieur ne corrige pas une limite du pont natif x1.
- Une variante liée bypass le pont natif : ne pas cuire aveuglément tous les covers en nearest x1. Un meuble déjà peint dans l'animation (WED17 / AM1101A) doit garder son rendu, sinon une nouvelle frontière crénelée apparaît.

## Amkethran AR5500 — validés ingame au premier essai, 2026-10-09

Pack QA installé : `animations/packs-par-zone/ar5500-fumee-brasero-complete-20261009-v1/AR5500` ; reçu `backups/animations/area-tests/AR5500-20261009T201652920932Z-46d75921/install-backup.json`. BUTRFLY/DSTDVL1A/B/C conservés exacts ; aucune intégration release.

| Asset / modèle | Recette exacte | Autorité |
|---|---|---|
| AM5500A / `FUMEE-SEEDVR-SPLINE4-EDGEFADE` | SeedVR2 7B INT8/LAB x4 → Apollo-8 15→30, RGB transparent nearest-opaque-dilate → spline Fit1 multi-contours feather4 → Oval20/6 → RGB Gaussian σ1 sans padding. RGB prémultiplié ; géométrie native par frame. 2 cycles indépendants : 8 poses → 16 phases chacun, 0,533333 s ; AR5500 utilise le cycle0, 7 occurrences. | [Sélection](index/selections/AM5500A.json) |
| AM5500D / `BRASERO-REBOUTCX-APO8-AURA-SPARKGUARD1` | ReboutCX x4 → Apollo-8 15→30, 10 poses → 20 phases, 0,666667 s → corps Aura24/5/0,9/14 ; composantes détachées ≤128 pixels x4 (connectivité4) : Aura1/1/0,9/1 ; fusion max RGB prémultiplié/alpha, une seule prémultiplication. Dimensions/centres natifs ; occurrence1297,2386, aucun cover WED vanilla intersectant. | [Sélection](index/selections/AM5500D.json) |

- Variante brasero : les rayons uniformes16/24/28 préservent le cœur p95 mais effacent les petites composantes. Séparer leur fondu du corps ; ne pas réduire tout le brasero au rayon1. Sur AM5500D final : 110 petites composantes, pic moyen conservé92,6 %, minimum58,7 % ; cœur inchangé au balayage spatial.
- Recette reproductible exacte (copie SHA-identique du script de production) : [`pipeline/recipes/ar5500-fumee-brasero-20261009-v1/build_brasero_guard.py`](../pipeline/recipes/ar5500-fumee-brasero-20261009-v1/build_brasero_guard.py). Paramètres liés à cet asset ; recalculer taille et conservation lumineuse pour une autre source.

## AR6001 / AR6005 — validés ingame le 2026-10-09

Packs installés : `animations/packs-par-zone/ar6001-ar6005-fumee-effetvert-complete-20261009-v1/{AR6001,AR6005}`. Production/reçus : `animations/batches/ar6001-ar6005-fumee-effetvert-20261009-v1/manifest.json` (instantané pré-QA immuable) ; décisions courantes ci-dessous. Aucune intégration release.

| Asset / modèle | Recette exacte | Autorité |
|---|---|---|
| AM6004A / `FUMEE-SEEDVR-SPLINE4-EDGEFADE` | SeedVR2 7B INT8/LAB x4 → Apollo-8 15→30 par cycle → spline Fit1 multi-contours feather4 → Oval20/6 → RGB Gaussian σ1, géométrie préservée, prémultiplié. 5 cycles distincts : 8 poses → 16 phases chacun, 0,533333 s ; 80 frames. 30 occurrences : AR6001 ×9 / AR6005 ×21 ; cycle0 utilisé, centres/dimensions natifs conservés. | [Sélection](index/selections/AM6004A.json) |
| AM6005A / `DISQUE-FERME-REBOUTCX-SPLINE8` | ReboutCX x4 → Apollo-8 15→30 → spline Fit1 multi-contours feather8, RGB droit identique octet pour octet à Apollo. 12 poses → 24 phases, 0,8 s ; texture mobile, alpha fixe. AR6005 en764,420 ; non `Blended` (`0x1101`), aucun cover WED intersectant, centres/dimensions natifs conservés. | [Sélection](index/selections/AM6005A.json) |

- AM6005A : le libellé historique `pipeline_name` finit par `feather4` ; le paramètre effectif du rapport `parameters.inner_feather_x4 = 8` fait autorité.

## AR6003 / AR6004 — AM6004B validé ingame le 2026-10-09

- Autorité : [sélection AM6004B](index/selections/AM6004B.json). Packs installés : `animations/packs-par-zone/ar6003-ar6004-fumee-complete-20261009-v1/{AR6003,AR6004}` ; production/reçus : `animations/batches/ar6003-ar6004-fumee-20261009-v1/manifest.json` (instantané pré-QA immuable).
- `FUMEE-SEEDVR-SPLINE4-EDGEFADE` : SeedVR2 7B INT8/LAB x4 → Apollo-8 15→30 par cycle → spline Fit1 multi-contours feather4 → Oval20/6 → RGB Gaussian σ1 sans padding, prémultiplié. Dimensions/centres natifs conservés.
- 4 cycles indépendants : 8 poses → 16 phases chacun, 0,533333 s ; 64 frames. 19 occurrences : AR6003 ×8 / AR6004 ×11, cycle0 utilisé. QA utilisateur acceptée ; aucune intégration release.

## OH7300 — bulles et pièges validés ingame le 2026-10-10

Pack installé : `animations/packs-par-zone/oh7300-bulles-pieges-complete-20261010-v1/OH7300` ; FIRE/FLMM/FPIT1S conservés octet pour octet. Production/reçus : `animations/batches/oh7300-bulles-pieges-20261010-v1/manifest.json` (instantané pré-QA immuable) ; reçu `backups/animations/area-tests/OH7300-20261009T231122733937Z-f2805bd9/install-backup.json`. Aucune intégration release.

| Asset / modèle | Recette exacte | Autorité |
|---|---|---|
| AMOH7300 / `BULLES-XBR2BLEND-NEAREST2-APO8-PREMUL` | xBR2 blend → nearest2 x4 → Apollo-8 15→30 (`nearest-opaque-dilate`) → prémultiplication unique. Alpha xBR conservé, fondu supplémentaire0 ; 108 poses natives → 216 frames/phases, 7,2 s. Dimensions/centres natifs ; 9 occurrences. | [Sélection](index/selections/AMOH7300.json) |
| OHHNECR / `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` | ReboutCX x4 → Apollo-8 15→30 sur lookup natif aller-retour `0..10..1` → inner feather16 px x4 → prémultiplication unique. 11 frames natives / 20 poses → 31 frames runtime / 40 phases, 1,333333 s. Dimensions/centres natifs ; 14 occurrences. | [Sélection](index/selections/OHHNECR.json) |

- AMOH7300 : bulles fines, aucun inner fade ; estimation sur source d'un rayon4 x4 : perte lumineuse71,6 %. Même structure que BUBBLES2, interpolation depuis les 108 frames propres à AMOH7300.
- OHHNECR : conserver les 20 poses aller-retour, pas une boucle avant de 11 poses. Balayage sur Rebout spatial4/8/12/16 : pertes lumineuses0,42/0,91/1,65/2,67 %, cœur p99 inchangé ; rayon16 retenu. Recette connue réutilisée ; aucun comparatif SeedVR produit pour cet asset.

## Mir / camps — AM5202B, AM5204A, FPIT1L validés ingame le 2026-10-10

Packs installés : `animations/packs-par-zone/mir-camps-trois-animations-complete-20261010-v1/{AR5202,AR5204,AR5203,OH5300}`. Production/reçus : `animations/batches/mir-camps-trois-animations-20261010-v1/manifest.json` (instantané pré-QA immuable). FIRE_4 d'AR5202/OH5300 et FPIT1S d'AR5202 conservés octet pour octet ; aucune intégration release.

| Asset / modèle | Recette exacte | Autorité |
|---|---|---|
| AM5202B / `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` | ReboutCX x4 → Apollo-8 15→30 (`nearest-opaque-dilate`) → inner16 → WED0/5 anticrénelage x4 supersample4, raccord4 côté visible, liaison601,560 → prémultiplication unique. 15 poses → 30 phases, 1 s ; dimensions/centres natifs. Perte lumineuse spatiale4,37 %, cœur inchangé. | [Sélection](index/selections/AM5202B.json) |
| AM5204A / `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` | ReboutCX x4 → Apollo-8 15→30 → inner20 → prémultiplication unique. 15 poses → 30 phases, 1 s ; dimensions/centres natifs, aucun cover WED intersectant. Perte lumineuse spatiale10,03 %, perte maximale du cœur0,875 %. | [Sélection](index/selections/AM5204A.json) |
| FPIT1L / `BRASERO-REBOUTCX-APO8-AURA-SPARKGUARD1` | ReboutCX x4 → Apollo-8 15→30 → corps Aura12/5/0,9/14 ; composantes≤128 px x4, connectivité4 : Aura1/1/0,9/1, fusion max RGBA prémultiplié. WED83 raccord4 à597,1762 et552,1702 (AR5203), masque multiplié sur RGBA déjà prémultiplié ; autres occurrences sans masque. 6 poses → 12 phases, 0,4 s ; dimensions/centres natifs. | [Sélection](index/selections/FPIT1L.json) |

- FPIT1L : rayon40 proportionnel rejeté, perte moyenne du cœur jusqu'à23,68 % sur phases Apollo ; rayon12 retenu, perte maximale2,821 %, lumière totale−19,23 %. Pics des petites composantes conservés96,79 % en moyenne, minimum75,22 % (avant occlusion).
- Recettes reproductibles : [`build_fpit1l_guard.py`](../pipeline/recipes/mir-camps-20261010-v1/build_fpit1l_guard.py), [`build_fpit1l_occlusions.py`](../pipeline/recipes/mir-camps-20261010-v1/build_fpit1l_occlusions.py). Masques scellés : `masques-occlusion/{AM5202B,FPIT1L}/mir-camps-20261010-v1/` ; géométrie WED/origine/position/SHA dans les JSON adjacents.
- Suivi FPIT1L : traitement antérieur signalé par l'utilisateur ; ligne déjà présente et `non-traité` dans `b19fbd5d` (2026-08-27), `c9a8954e` (2026-09-02) et HEAD avant ce lot. Aucune ancienne décision QA trouvée localement, aucun FPIT1L dans les128 manifestes racines de l'archive `config://animation_artifacts_archive/animations/cleanup-20260907/packs-par-zone`. Cause de la non-consignation antérieure non établie ; sélection actuelle explicitement acceptée, ne pas réintroduire ce lot comme inédit.

## Tour de Garde — sceaux et mécanismes validés ingame le 2026-10-10

Pack installé : `animations/packs-par-zone/watchers-seals-trois-animations-20261010-v1-complete-v2/{AR3019,AR3020,AR3022}` ; manifeste racine SHA256 `8d1b6297db70b30f407db4420d95525bd1d4e21e780cef64dcde873d6e266fd1`. Production/contrôles/reçus : `animations/batches/watchers-seals-trois-animations-20261010-v1/{manifest,local-checks,installation}.json` (instantanés pré-QA immuables). Décisions QA et sélections courantes ci-dessous ; AMWRPGT1 reste vanilla, aucune intégration release.

| Asset / zone / modèle | Recette exacte | Autorité |
|---|---|---|
| AM3019A / AR3019 / `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` | ReboutCX x4 → Apollo8 15→30 (`nearest-opaque-dilate`) → inner8 → WED67/69 AA x4 supersample4, raccord4 côté visible, liaison2277,1802 → prémultiplication unique (`Blended`, 0x1012). 72 frames stockées ; cycle0 39 poses → 78 phases / 2,6 s, pauses exactes ; cycle1 4 poses → 8 phases / 0,266667 s, interpolation directe. Dimensions/centres natifs. | [Sélection](index/selections/AM3019A.json) |
| AM3020D / AR3020 / `MECANIQUE-SEEDVR-ALPHA-NATIVE` | SeedVR2 7B INT8/LAB x4 seed3020 → Apollo8 15→30 avec pauses/aller-retour natifs → alpha nearest → WED11 AA4 raccord4, liaison604,771. Sans spline/fondu global ; RGB droit, zéro sous alpha nul (`0x1101`). 9 frames natives / 24 poses → 25 frames stockées / 48 phases, 1,6 s. Dimensions/centres natifs. | [Sélection](index/selections/AM3020D.json) |
| AM3022D / AR3022 / `DISQUE-FERME-REBOUTCX-SPLINE8` | ReboutCX x4 → Apollo8 15→30, entrées alignées220×140 → spline Fit1 multicontour feather8 ; RGB droit identique octet pour octet à Apollo (`0x1101`). 10 poses → 20 frames/phases / 0,666667 s. Aucun WED intersectant à1550,1690 ; frame1 runtime220×136, autres220×140, centres natifs28,17 conservés. | [Sélection](index/selections/AM3022D.json) |

- AM3019A : inner8 retenu pour les faibles premières poses/détails fins ; lumière avant occlusion −2,675 % en moyenne, pire−15,916 %, cœur perte maximale0,351 % ; ne pas appliquer inner16 par défaut.
- Recette : [`build_final.py`](../pipeline/recipes/watchers-seals-20261010-v1/build_final.py), SHA256 `82a9cfb5bb07ade87ec42dcb4dc239c73471e6457dd59a28d76c86b78c1175f7`. Masques : `masques-occlusion/{AM3019A,AM3020D}/watchers-seals-trois-animations-20261010-v1/` ; WED/origine/position/SHA dans les JSON.
- Timing : `run_animation_upscale_30fps_v2.py` accepte un cycle sans doublons lorsque les autres utilisent `--preserve-segmented-holds` ; aligne toutes les frames d'inférence, y compris une frame ultérieure plus petite que la première, puis recadre aux dimensions natives. Deux régressions ajoutées ; 19 tests réussis.
- QA : une zone par asset, aucune des trois ne contient les autres. AM3020D accepté individuellement puis lot entier accepté explicitement. AM3019A masqué initialement par script ; AM3022D déjà actif, pas conditionné par une quête. Console de visualisation AM3019A :

```lua
C:MoveToArea("AR3019")
C:Eval('JumpToPoint([2277.1850])')
C:Eval('AmbientActivate("AMB_FinalSeal",1)')
C:Eval('StaticSequence("AMB_FinalSeal",0)')
C:Eval('StaticSequence("AMB_FinalSeal",1)')
```

AM3022D : `C:MoveToArea("AR3022")`, puis `C:Eval('JumpToPoint([1550.1760])')` ; nom d'animation `AM3022D`, cycle0.

## Portails — cinq assets validés ingame le 2026-10-10

| Asset / zones | Recette retenue | Autorité |
|---|---|---|
| BDFORCEW / OH8100 | ReboutCX x4 → Apollo8 15→30 → Spline Fit1 / inner16 → prémultiplication unique. Pont WED natif : garde4 / fondu16 x4 (premier correctif lissé restauré). Après masquage, translation visuelle +6 pixels x1 horizontaux des deux occurrences2286,820 /2350,866 ; état non vanilla explicitement demandé et accepté. | [Sélection](index/selections/BDFORCEW.json) |
| OHDLPORT / OH5400, OH5500 | xBR2 blend → nearest2 → Apollo8 15→30 ; sans fondu supplémentaire ; prémultiplication unique. | [Sélection](index/selections/OHDLPORT.json) |
| OHHPORT / AR0811 | xBR2 blend → nearest2 → Apollo8 15→30 ; fond noir opaque de la frame native2 rendu transparent, fond parasite runtime corrigé ; prémultiplication unique. | [Sélection](index/selections/OHHPORT.json) |
| OHRSGATE / OH4220, OH4230 | SeedVR2 7B INT8/LAB seed4220 → Apollo8 15→30 `nearest-opaque-dilate` → inner16 → prémultiplication unique. | [Sélection](index/selections/OHRSGATE.json) |
| SPDIMNDR / AR6108 | SeedVR2 7B INT8/LAB seed6108 → Apollo8 15→30 ; cycles0/2/3/4 linéaires, sans raccord fin→début ; inner2 → prémultiplication unique. | [Sélection](index/selections/SPDIMNDR.json) |

- Packs actifs : `animations/packs-par-zone/portails-deux-correctif-20261010-v1-complete/{AR0811,OH8100}` ; `portails-cinq-selection-20261010-v1-complete/{AR6108,OH4220,OH4230,OH5400,OH5500}`.
- Contrat BDFORCEW : DLL `748fe476d24ffa32007d33d34f5c6e506b56147570772ee40b810556ad317c56` ; reçu `backups/renderer/20261010T150141567331Z-182aac70/renderer-install-receipt.json`. Translation après masque WED indispensable : déplacer seulement l'ARE accentue la coupe. Centres/dimensions BAM et coordonnées ARE/sauvegardes conservés ; seul le dessin final se décale. Tests natifs et concordance du fondu C++/preview GLSL acquis.
- [Acceptation finale et recettes](../pipeline/recipes/portails-cinq-validation-20261010-v1/acceptance.json), [enregistrement reproductible](../pipeline/recipes/portails-cinq-validation-20261010-v1/record.py). Décisions/runs/reçus antérieurs conservés ; essais WED4 et SeedVR non retenus pour BDFORCEW. Aucune intégration release.

## Lot 2 — cinq petits effets validés ingame le 2026-10-11

| Asset / zone / occurrences | Recette finale | Autorité |
|---|---|---|
| AM0504SB / AR0504 / 6 | ReboutCX x4 → Apollo8 30 FPS → inner12 → prémultiplication unique. Essai SeedVR abandonné ; retour ReboutCX validé. | [Sélection](index/selections/AM0504SB.json) |
| AM4000Z / AR4000 / 10 | SeedVR2 7B INT8/LAB x4 seed20261011 → Apollo8 30 FPS ; sans fondu pour préserver les braises ; prémultiplication unique. Deux cycles12/10 → 24/20 phases. | [Sélection](index/selections/AM4000Z.json) |
| BUBBLEA / AR2903 / 3 | xBR2 blend → nearest2 → Apollo8 30 FPS `--preserve-segmented-holds` ; 3 cycles49 → 98 phases, pauses natives exactes ; prémultiplication unique. | [Sélection](index/selections/BUBBLEA.json) |
| EYESRED1 / AR0329 / 1 | SeedVR2 7B INT8/LAB x4 seed20261011 ; cadence native20 frames ; sans fondu ; prémultiplication unique. | [Sélection](index/selections/EYESRED1.json) |
| WTRBODY1 / AR0502 / 1 | xBR2 → nearest2 ; 20 frames natives → 10 poses uniques ; Apollo8 7,5→30 FPS → 40 frames distinctes, boucle20/15 s ; 10 ancres xBR identiques octet pour octet. | [Sélection](index/selections/WTRBODY1.json) |

- Total : 5 assets / 5 cartes / 21 occurrences ; dimensions/centres natifs, autres ressources conservés ; pont d'occlusion natif installé, aucun masque WED figé ajouté.
- SeedVR essayé sur les cinq assets à la demande explicite de l'utilisateur ; retenu seulement pour AM4000Z et EYESRED1. Règle générale petits sujets ReboutCX/xBR conservée.
- Reprise : [`finalize.py`](../pipeline/recipes/lot2-small-effects-20261011-v1/finalize.py) ; correctif temporel [`build.py`](../pipeline/recipes/wtrbody1-xbr-apo8-collapse-20261011-v1/build.py). Preuve finale : `animations/batches/lot2-five-effects-accepted-20261011-v1/manifest.json`. QA et reçus historiques immuables ; aucune intégration release.
