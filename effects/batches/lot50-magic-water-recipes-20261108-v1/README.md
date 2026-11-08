# Formules du lot magie/eau — 2026-11-08

Plan complet : `recipes.json` ; recommandations, aucune production/QA acquise.

**Répartition : 4 SeedVR7B, 5 ReboutCX, 32 recettes xBR propres, 1 adaptation de palette xBR, 2 réemplois spatiaux à vérifier, 6 masques natifs.**

## Contrat commun

- x4 ; Apollo apo-8 vers30 FPS sur les productions animées nouvelles. 15 FPS entrée = hypothèse de compatibilité si propriétaire inconnu, pas mesure runtime. Les6masques restent natifs.
- Cycles séparés, ancres/centres/rectangles/pauses conservés. Dédupliquer pour le calcul sans redistribuer les slots ; boucle fermée et once distincts si rôle inconnu. Cycle constant : image unique durée conservée ; cycle vide : carrier seul.
- Alpha natif conservé hors dérivations listées ; prémultiplication unique. Aucun retrait/feather global. Noir sombre de WTRBODY2/RIPPLE2/3 et masques conservé.
- Alpha lumineux candidat : P=round(A_native*C/255), A_flux=max(P), C_droit=round(255*P/A_flux), zéro siA=0. P conservé, reconstruction erreur≤1. Témoin natif ; ne vaut pas preuve du blend propriétaire.
- WHIRLY : vert indexé exact connecté au bord retiré dans copie de travail, avant spatial ; source immuable.
- Réemplois TRBLOBA/BB non démontrés comme interchangeables ; adaptation testée avant nouveau spatial, repli xBR si nécessaire. BUBLES exige ses RGB propres, pas une copie des bulles vertes.

## Profils

| ID | Spatial | Alpha | Référence et repli |
|---|---|---|---|
| R-SOFT | ReboutCX x4 | Native alpha nearest4; soft premultiplied RGBA sigma2 x4, canvas edge ramp2 x4, runtime geometry unchanged | `animations/ressources/AM3000E/runs/am3000e-contour-native-accepted-20261011-v1/manifest.json` ; Native alpha, no soft2 if plume energy or fine fringes are lost. |
| R-COLUMN | ReboutCX x4 | Native alpha, inner feather16 x4 on broad column only, premultiply once; keep all detached grains. Native-alpha witness mandatory for transfer of this setting. | `animations/batches/am6200a-selection-accepted-20260922/manifest.json` ; Native-alpha feather0 if16 suppresses thin ends; SeedVR7B/LAB only if actual veins are erased as on AM6200E/F. |
| R-PORTAL | ReboutCX x4 | Native alpha nearest4, feather0; preserve opaque door frame, recess and central spiral | `pipeline/recipes/portails-deux-correctif-20261010-v1/build_fix.py` ; xBR4X, no blend, if frame ornament or spiral changes. No luminous flux conversion on stone. |
| S-GLOW | SeedVR2 7B INT8/LAB x4 | Native support nearest4, feather0; apply explicit per-asset black-matte policy after premultiplied temporal composition | `effects/batches/lot50-accepted-20261108-v1/acceptance.json` ; xBR4X if symbols, false texture, hue drift or unstable core are introduced; reduce sigma to0 if grains disappear. |
| X-STRUCT | xBR4X, blend_colors=false, scale4 | Native alpha nearest4, feather0, erosion0 | `effects/batches/lot50-xbr-small-20261108-v1/production.json` ; Keep xBR; no generative repair of tiny glyphs, spokes, lightning or lattices. |
| X-PARTICLE | xBR4X, blend_colors=false, scale4 | Native alpha nearest4, feather0, erosion0; preserve every particle and centre | `effects/batches/lot50-xbr-small-20261108-v1/production.json` ; If temporal merge/splitting occurs, retain native anchors and use alpha interpolation from the same anchor pair; do not add blur or reshape into discs. |
| X-WATER | xBR2x -> Gaussian sigma0.45 at x2 -> nearest2 to x4 | xBR2x twice; feather0 baseline for droplets; no FOUNT1 feather12/aura5 on thin components by default | `animations/ressources/FOUNT1/runs/fount1-xbr2x-gaussian045-30fps-contour-aura-accepted-20260915/manifest.json` ; xBR4X/no RGB blur if spray vanishes. FOUNT1 aura gain0.9/sigma5, feather12 only as separate broad-mass comparison, not automatic transfer. |
| X-BODY | xBR2x -> nearest2 to x4 | Native alpha retained, no threshold on dark corpse or water | `pipeline/recipes/wtrbody1-xbr-apo8-collapse-20261011-v1/build.py` ; Own WTRBODY2 source and cycles; do not copy WTRBODY1 pixels, duplicate holds or 7.5 FPS input setting. |
| A-BUBBLE | Own BUBLES palette: xBR2 blend -> nearest2 to x4; reuse AMOH7300 method and exact matching source geometry | Reuse matching native masks; xBR alpha as AMOH7300, no feather; premultiply once | `animations/index/qa-decisions/AMOH7300/2026-10-10-accepted-amoh7300-bulles-xbr2blend-apo8-premul-v1.json` ; Do not recolor final green AMOH7300 RGB blindly: source palette contains color collapses; regenerate deterministic RGB from BUBLES palette. No new SeedVR. |
| A-BLOB | Attempt existing accepted TRGOOY spatial anchors; adapt palette/contour/geometry from target source | Target native alpha nearest4; target centres and rectangles; preserve dark outlines | `effects/index/processing.csv` ; Not a proven byte-equivalent reuse. If adaptation changes source drawing/contour, use target xBR4X+Apollo30; no SeedVR by default. Never substitute final retimed TRGOOY pack. |
| N-MASK | No new spatial or AI job; retain native owner mask | Preserve native black RGB and graduated alpha/owner role; no flux conversion, feather or erosion | `projectiles/index/visual-assets.csv` ; If another visible non-mask owner is discovered, qualify that owner separately; this decision is not global acceptance of every BAM use. |

## Affectation exhaustive

| # | Effet | Formule | Noir / particularité | Phases à30 par cycle non vide* |
|---|---|---|---|---|
| 01 | AM3000G | R-SOFT | Alpha natif, matière sombre préservée | 32 |
| 02 | AM6200C | R-COLUMN | Alpha natif, matière sombre préservée | 18 |
| 03 | AM6200D | R-COLUMN | Alpha natif, matière sombre préservée | 18 |
| 04 | AMDEMGT | X-STRUCT | Alpha natif, matière sombre préservée ; SP_DEMGT is a source alias: one spatial production, separate resource binding; no second inference. | 76/8 |
| 05 | HARPDISC | X-STRUCT | Alpha natif, matière sombre préservée | 22 |
| 06 | SPARMOR2 | X-STRUCT | Alpha natif, matière sombre préservée | 80 |
| 07 | SPDIMDR1 | R-PORTAL | Alpha natif, matière sombre préservée | 12 |
| 08 | SPDIMDR2 | R-PORTAL | Alpha natif, matière sombre préservée | 12 |
| 09 | SPMIRROI | X-STRUCT | Alpha natif, matière sombre préservée | 40 |
| 10 | SPRESURI | S-GLOW | Variante alpha de flux + témoin natif | 120 |
| 11 | SPWIRBLA | X-STRUCT | Alpha natif, matière sombre préservée | 92 |
| 12 | WHIRL01 | X-STRUCT | Alpha natif, matière sombre préservée | 24 |
| 13 | WHIRLY | X-STRUCT | Détourage du vert indexé de bord, puis alpha natif | 24 |
| 14 | HIHEDGE | X-STRUCT | Variante alpha de flux + témoin natif | 24 |
| 15 | SHAREAB | N-MASK | Masque noir natif | natif |
| 16 | SPBASEWT | X-STRUCT | Alpha natif, matière sombre préservée | 98 |
| 17 | SPCCOLDE | X-STRUCT | Variante alpha de flux + témoin natif | 32/32/32/32/32 |
| 18 | SPCCWOUI | S-GLOW | Variante alpha de flux + témoin natif | 80/80 |
| 19 | SPCHROMI | X-STRUCT | Variante alpha de flux + témoin natif | 16/16/16/16/16/16/16/16/16 |
| 20 | SPCSPRAI | X-STRUCT | Variante alpha de flux + témoin natif | 48 |
| 21 | SPENTAXI | X-STRUCT | Alpha natif, matière sombre préservée | 46 |
| 22 | SPGENHLB | S-GLOW | Variante alpha de flux + témoin natif | 12/12/18/42 |
| 23 | SPHLYSMT | X-STRUCT | Alpha natif, matière sombre préservée | 30/28/28 |
| 24 | SPHOLMIG | S-GLOW | Variante alpha de flux + témoin natif | 24 |
| 25 | SPHOLYWD | X-STRUCT | Variante alpha de flux + témoin natif | 30/24 |
| 26 | SPRWRA2I | X-STRUCT | Alpha natif, matière sombre préservée | 96 |
| 27 | SPSDIMSP | N-MASK | Masque noir natif | natif |
| 28 | SPSNRAYI | X-STRUCT | Variante alpha de flux + témoin natif | 48 |
| 29 | SPUNHBLT | X-STRUCT | Alpha natif, matière sombre préservée | 30/30/30 |
| 30 | DUST | X-PARTICLE | Alpha natif, matière sombre préservée | 60 |
| 31 | SNOWFAL1 | X-PARTICLE | Alpha natif, matière sombre préservée | 36 |
| 32 | SNOWFAL2 | X-PARTICLE | Alpha natif, matière sombre préservée | 42 |
| 33 | SPSDRABU | N-MASK | Masque noir natif | natif |
| 34 | SPSDRAE2 | N-MASK | Masque noir natif | natif |
| 35 | SPSHADOW | N-MASK | Masque noir natif | natif |
| 36 | TRAVELB | N-MASK | Masque noir natif | natif |
| 37 | BUBBLES1 | X-PARTICLE | Variante alpha de flux + témoin natif | 16 |
| 38 | BUBLES | A-BUBBLE | Alpha natif, matière sombre préservée | 216 |
| 39 | FOUNT2 | X-WATER | Alpha natif, matière sombre préservée | 12 |
| 40 | FOUNTN | X-WATER | Alpha natif, matière sombre préservée | 36 |
| 41 | RIPPLE_1 | X-STRUCT | Variante alpha de flux + témoin natif | 26 |
| 42 | RIPPLE_2 | X-STRUCT | Alpha natif, matière sombre préservée ; Dark source is not evidence of a disposable matte; do not use global flux-alpha conversion. | 60 |
| 43 | RIPPLE_3 | X-STRUCT | Alpha natif, matière sombre préservée ; Dark source is not evidence of a disposable matte; do not use global flux-alpha conversion. | 40 |
| 44 | SPLASH | X-PARTICLE | Alpha natif, matière sombre préservée | 24 |
| 45 | WTRBODY2 | X-BODY | Alpha natif, matière sombre préservée ; Dark source is not evidence of a disposable matte; do not use global flux-alpha conversion. | 20 |
| 46 | WTRDROP1 | X-STRUCT | Alpha natif, matière sombre préservée | 14 |
| 47 | TRBLOBA | A-BLOB | Alpha natif, matière sombre préservée ; Parent spatial TRGOOYAA SeedVR7B x4 accepted; rebuild temporal from target source cycles, never copy parent timing. | 20/124 |
| 48 | TRBLOBB | A-BLOB | Alpha natif, matière sombre préservée ; Parent spatial TRGOOYBB SeedVR7B x4 accepted; rebuild temporal from target source cycles, never copy parent timing. | 20/120 |
| 49 | WEBBOMB | X-STRUCT | Alpha natif, matière sombre préservée | 28 |
| 50 | WEBC | X-STRUCT | Alpha natif, matière sombre préservée | 32/32/12 |

*Prévision au taux source retenu ; cycles constants peuvent réutiliser une seule image. Phases de playback ≠ fichiers distincts.

Les précédents établissent un point de départ. Les paramètres transférés (soft2, feather16, flux-alpha, vert) doivent être jugés sur la nouvelle sortie, sans déduire une acceptation ingame.
