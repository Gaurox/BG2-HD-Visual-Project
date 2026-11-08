# Lot50 — priorité SeedVR — v2, 2026-11-08

Correction explicite utilisateur ; remplace le plan v1. Aucune inférence ou installation lancée.

- **35 SeedVR2 7B INT8/LAB x4** :30 sans flou RGB ajouté,5diffus avec sigma1.2 x4.
- **6 xBR minuscules** : BUBBLES1, SPCSPRAI, DUST, SNOWFAL1, SNOWFAL2, SPLASH.
- **1 adaptation BUBLES** : xBR2blend→nearest2, palette propre, recette AMOH7300.
- **2 réemplois TRBLOBA/BB** : parents TRGOOYAA/BB SeedVR déjà validés ; adaptation spatiale à vérifier, cycles propres. Si impossible : nouveau SeedVR7B/LAB, pas xBR automatique.
- **6 masques natifs** : SHAREAB, SPSDIMSP, SPSDRABU, SPSDRAE2, SPSHADOW, TRAVELB ; aucun job IA.

Contrat : Apollo apo-8→30FPS hors6natifs, durées/pauses/centres/cycles conservés ; 15FPS source par défaut de compatibilité si propriétaire inconnu. Alpha natif nearest4, feather0/érosion0 de départ ; variantes de flux lumineuses avec témoin natif. WHIRLY : vert indexé de bord retiré dans copie de travail avant SeedVR ; pas de vert injecté au modèle. WTRBODY2 : matière sombre conservée. ReboutCX/xBR antérieurement proposés deviennent des replis comparatifs, sans substitution automatique.

| # | Effet | Formule principale | Particularité |
|---|---|---|---|
| 01 | AM3000G | S-SOFT · SeedVR2 7B INT8/LAB x4 |  |
| 02 | AM6200C | S-DETAIL · SeedVR2 7B INT8/LAB x4 | ReboutCX/inner16 precedent AM6200A/B retained as comparison only; main source is SeedVR, feather0 baseline. |
| 03 | AM6200D | S-DETAIL · SeedVR2 7B INT8/LAB x4 | ReboutCX/inner16 precedent AM6200A/B retained as comparison only; main source is SeedVR, feather0 baseline. |
| 04 | AMDEMGT | S-DETAIL · SeedVR2 7B INT8/LAB x4 | SP_DEMGT is a source alias: one spatial production, separate resource binding; no second inference. |
| 05 | HARPDISC | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 06 | SPARMOR2 | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 07 | SPDIMDR1 | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 08 | SPDIMDR2 | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 09 | SPMIRROI | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 10 | SPRESURI | S-SOFT · SeedVR2 7B INT8/LAB x4 |  |
| 11 | SPWIRBLA | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 12 | WHIRL01 | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 13 | WHIRLY | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  ; masque vert indexé dérivé avant SeedVR |
| 14 | HIHEDGE | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 15 | SHAREAB | N-MASK · No new spatial or AI job; retain native owner mask |  |
| 16 | SPBASEWT | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 17 | SPCCOLDE | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 18 | SPCCWOUI | S-SOFT · SeedVR2 7B INT8/LAB x4 |  |
| 19 | SPCHROMI | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 20 | SPCSPRAI | X-TINY · xBR4X, blend_colors=false, scale4 |  |
| 21 | SPENTAXI | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 22 | SPGENHLB | S-SOFT · SeedVR2 7B INT8/LAB x4 |  |
| 23 | SPHLYSMT | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 24 | SPHOLMIG | S-SOFT · SeedVR2 7B INT8/LAB x4 |  |
| 25 | SPHOLYWD | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 26 | SPRWRA2I | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 27 | SPSDIMSP | N-MASK · No new spatial or AI job; retain native owner mask |  |
| 28 | SPSNRAYI | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 29 | SPUNHBLT | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 30 | DUST | X-TINY · xBR4X, blend_colors=false, scale4 |  |
| 31 | SNOWFAL1 | X-TINY · xBR4X, blend_colors=false, scale4 |  |
| 32 | SNOWFAL2 | X-TINY · xBR4X, blend_colors=false, scale4 |  |
| 33 | SPSDRABU | N-MASK · No new spatial or AI job; retain native owner mask |  |
| 34 | SPSDRAE2 | N-MASK · No new spatial or AI job; retain native owner mask |  |
| 35 | SPSHADOW | N-MASK · No new spatial or AI job; retain native owner mask |  |
| 36 | TRAVELB | N-MASK · No new spatial or AI job; retain native owner mask |  |
| 37 | BUBBLES1 | X-TINY · xBR4X, blend_colors=false, scale4 |  |
| 38 | BUBLES | A-BUBBLE · Own BUBLES palette: xBR2 blend -> nearest2 to x4; reuse AMOH7300 method and exact matching source geometry |  |
| 39 | FOUNT2 | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 40 | FOUNTN | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 41 | RIPPLE_1 | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 42 | RIPPLE_2 | S-DETAIL · SeedVR2 7B INT8/LAB x4 | Dark source is not evidence of a disposable matte; do not use global flux-alpha conversion. |
| 43 | RIPPLE_3 | S-DETAIL · SeedVR2 7B INT8/LAB x4 | Dark source is not evidence of a disposable matte; do not use global flux-alpha conversion. |
| 44 | SPLASH | X-TINY · xBR4X, blend_colors=false, scale4 |  |
| 45 | WTRBODY2 | S-DETAIL · SeedVR2 7B INT8/LAB x4 | Dark source is not evidence of a disposable matte; do not use global flux-alpha conversion. ; User priority SeedVR overrides previous xBR recommendation. WTRBODY1 xBR2->nearest2 remains fallback; own dark corpse/water and native10-slot timing preserved. |
| 46 | WTRDROP1 | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 47 | TRBLOBA | A-BLOB · Attempt existing accepted TRGOOY spatial anchors; adapt palette/contour/geometry from target source | Parent spatial TRGOOYAA SeedVR7B x4 accepted; rebuild temporal from target source cycles, never copy parent timing. |
| 48 | TRBLOBB | A-BLOB · Attempt existing accepted TRGOOY spatial anchors; adapt palette/contour/geometry from target source | Parent spatial TRGOOYBB SeedVR7B x4 accepted; rebuild temporal from target source cycles, never copy parent timing. |
| 49 | WEBBOMB | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
| 50 | WEBC | S-DETAIL · SeedVR2 7B INT8/LAB x4 |  |
