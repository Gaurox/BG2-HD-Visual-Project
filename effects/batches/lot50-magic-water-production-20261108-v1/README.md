# Magie/eau — pack traité, 2026-11-08

**Comparaisons3 demandées — 2026-11-08** : [planche50](http://127.0.0.1:8799/), menus de versions sur SPBASEWT/SPENTAXI/SPCSPRAI. Deux variantes alpha-flux (288phases, P conservé, reconstruction≤1), sans clé noire : sources0pixel noir pur couvert,38043/5324pixels quasi-noirs respectivement ; propriétaires/blend non identifiés dans les index, recommandation visuelle et non preuve de blend natif. SPCSPRAI : nouveau test SeedVR7B INT8/LAB x4/Apollo30,96phases/2profils/192contrats passants, xBR conservé ; aucun suivi actif changé. Exception GPU limitée à cet asset à la demande utilisateur, puis modèles déchargés et pause globale conservée,30.04/31.82Gio libres. `three-tests-review.json`, `alternatives/black-alpha-check-20261108-v1/`, `alternatives/spcsprai-seedvr7b-test-20261108-v1/result.json`. QA et installation inchangées.

**Sélection courante v2 / pause GPU utilisateur** : `current-production.json` → `production-current-v2.json`.36SeedVR7B,6xBR4X,1BUBLES xBR2blend,1WTRBODY2 xBR2/nearest2,6masques natifs ;44productions Apollo30/50cartes. WTRBODY2 SeedVR surinterprète le corps/reflets32px : repli fidèle affiché, variante SeedVR/production.json baseline conservées. GPU déchargé,30.04/31.82Gio libres constatés ; aucun nouveau GPU avant signal explicite. Dernières opérations planche/classement = CPU seulement.

- [Planche50 natif/traité](http://127.0.0.1:8799/) : pause/phase/vitesse/cycles/fonds ; halos alpha lumineux sélectionnés par défaut, témoin alpha natif accessible.
- **37 SeedVR7B INT8/LAB x4 +6 xBR4X +BUBLES xBR2blend/nearest2 palette propre ;6 masques natifs conservés**. TRBLOBA/BB : réemploi direct non équivalent, repli SeedVR autorisé exécuté ; parents acceptés inchangés.
- Apollo apo-8 vers30FPS sur44productions, cycles once/loop et poses tenues conservés ; cadence source15FPS = compatibilité si propriétaire inconnu, pas mesure ingame.6masques natifs non nouvellement interpolés.
- 5460phases /140profils /2573backings ; 10920contrats natifs passants. Source/carrier : pixels, palettes, centres et cycles natifs conservés ; WHIRLY dérivation du vert indexé178 de bord dans copie de travail.
- Packs courants exclusivement dans `production.json`, registrev3 ; `*-initial-*` sont intermédiaires. Alias SP_DEMGT documenté mais aucune nouvelle liaison ingame installée.
- QA visuelle utilisateur en attente ; aucune installation/release. Planche peut afficher des compagnons de flux sans changer les octets du pack alpha natif ; routage propriétaire à choisir lors de l’intégration.
- `verification/*.json` : géométrie/timing/alpha/pixels ; `runtime-verification/*.json` : lecteur natif. Recette : `pipeline/recipes/effects-magic-water-production-20261108-v1/`.

| # | Source | Production | Pack |
|---|---|---|---|
| 01 | AM3000G | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/AM3000G/packs/am3000g-magic-x4-apollo30-profiles-20261108-v1` |
| 02 | AM6200C | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/AM6200C/packs/am6200c-magic-x4-apollo30-profiles-20261108-v1` |
| 03 | AM6200D | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/AM6200D/packs/am6200d-magic-x4-apollo30-profiles-20261108-v1` |
| 04 | AMDEMGT | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/AMDEMGT/packs/amdemgt-magic-x4-apollo30-profiles-20261108-v1` |
| 05 | HARPDISC | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/HARPDISC/packs/harpdisc-magic-x4-apollo30-profiles-20261108-v1` |
| 06 | SPARMOR2 | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPARMOR2/packs/sparmor2-magic-x4-apollo30-profiles-20261108-v1` |
| 07 | SPDIMDR1 | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPDIMDR1/packs/spdimdr1-magic-x4-apollo30-profiles-20261108-v1` |
| 08 | SPDIMDR2 | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPDIMDR2/packs/spdimdr2-magic-x4-apollo30-profiles-20261108-v1` |
| 09 | SPMIRROI | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPMIRROI/packs/spmirroi-magic-x4-apollo30-profiles-20261108-v1` |
| 10 | SPRESURI | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPRESURI/packs/spresuri-magic-x4-apollo30-profiles-20261108-v1` |
| 11 | SPWIRBLA | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPWIRBLA/packs/spwirbla-magic-x4-apollo30-profiles-20261108-v1` |
| 12 | WHIRL01 | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/WHIRL01/packs/whirl01-magic-x4-apollo30-profiles-20261108-v1` |
| 13 | WHIRLY | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/WHIRLY/packs/whirly-magic-x4-apollo30-profiles-20261108-v1` |
| 14 | HIHEDGE | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/HIHEDGE/packs/hihedge-magic-x4-apollo30-profiles-20261108-v1` |
| 16 | SPBASEWT | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPBASEWT/packs/spbasewt-magic-x4-apollo30-profiles-20261108-v1` |
| 17 | SPCCOLDE | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPCCOLDE/packs/spccolde-magic-x4-apollo30-profiles-20261108-v1` |
| 18 | SPCCWOUI | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPCCWOUI/packs/spccwoui-magic-x4-apollo30-profiles-20261108-v1` |
| 19 | SPCHROMI | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPCHROMI/packs/spchromi-magic-x4-apollo30-profiles-20261108-v1` |
| 20 | SPCSPRAI | XBR/xbr4X | `effects/ressources/SPCSPRAI/packs/spcsprai-magic-x4-apollo30-profiles-20261108-v1` |
| 21 | SPENTAXI | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPENTAXI/packs/spentaxi-magic-x4-apollo30-profiles-20261108-v1` |
| 22 | SPGENHLB | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPGENHLB/packs/spgenhlb-magic-x4-apollo30-profiles-20261108-v1` |
| 23 | SPHLYSMT | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPHLYSMT/packs/sphlysmt-magic-x4-apollo30-profiles-20261108-v1` |
| 24 | SPHOLMIG | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPHOLMIG/packs/spholmig-magic-x4-apollo30-profiles-20261108-v1` |
| 25 | SPHOLYWD | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPHOLYWD/packs/spholywd-magic-x4-apollo30-profiles-20261108-v1` |
| 26 | SPRWRA2I | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPRWRA2I/packs/sprwra2i-magic-x4-apollo30-profiles-20261108-v1` |
| 28 | SPSNRAYI | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPSNRAYI/packs/spsnrayi-magic-x4-apollo30-profiles-20261108-v1` |
| 29 | SPUNHBLT | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/SPUNHBLT/packs/spunhblt-magic-x4-apollo30-profiles-20261108-v1` |
| 30 | DUST | XBR/xbr4X | `effects/ressources/DUST/packs/dust-magic-x4-apollo30-profiles-20261108-v1` |
| 31 | SNOWFAL1 | XBR/xbr4X | `effects/ressources/SNOWFAL1/packs/snowfal1-magic-x4-apollo30-profiles-20261108-v1` |
| 32 | SNOWFAL2 | XBR/xbr4X | `effects/ressources/SNOWFAL2/packs/snowfal2-magic-x4-apollo30-profiles-20261108-v1` |
| 37 | BUBBLES1 | XBR/xbr4X | `effects/ressources/BUBBLES1/packs/bubbles1-magic-x4-apollo30-profiles-20261108-v1` |
| 38 | BUBLES | XBR/xbr2blend-nearest2 | `effects/ressources/BUBLES/packs/bubles-magic-x4-apollo30-profiles-20261108-v1` |
| 39 | FOUNT2 | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/FOUNT2/packs/fount2-magic-x4-apollo30-profiles-20261108-v1` |
| 40 | FOUNTN | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/FOUNTN/packs/fountn-magic-x4-apollo30-profiles-20261108-v1` |
| 41 | RIPPLE_1 | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/RIPPLE_1/packs/ripple_1-magic-x4-apollo30-profiles-20261108-v1` |
| 42 | RIPPLE_2 | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/RIPPLE_2/packs/ripple_2-magic-x4-apollo30-profiles-20261108-v1` |
| 43 | RIPPLE_3 | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/RIPPLE_3/packs/ripple_3-magic-x4-apollo30-profiles-20261108-v1` |
| 44 | SPLASH | XBR/xbr4X | `effects/ressources/SPLASH/packs/splash-magic-x4-apollo30-profiles-20261108-v1` |
| 45 | WTRBODY2 | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/WTRBODY2/packs/wtrbody2-magic-x4-apollo30-profiles-20261108-v1` |
| 46 | WTRDROP1 | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/WTRDROP1/packs/wtrdrop1-magic-x4-apollo30-profiles-20261108-v1` |
| 47 | TRBLOBA | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/TRBLOBA/packs/trbloba-magic-x4-apollo30-profiles-20261108-v1` |
| 48 | TRBLOBB | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/TRBLOBB/packs/trblobb-magic-x4-apollo30-profiles-20261108-v1` |
| 49 | WEBBOMB | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/WEBBOMB/packs/webbomb-magic-x4-apollo30-profiles-20261108-v1` |
| 50 | WEBC | seedvr2_7b_int8_convrot.safetensors | `effects/ressources/WEBC/packs/webc-magic-x4-apollo30-profiles-20261108-v1` |
| 15 | SHAREAB | natif conservé | pas de nouveau pack |
| 27 | SPSDIMSP | natif conservé | pas de nouveau pack |
| 33 | SPSDRABU | natif conservé | pas de nouveau pack |
| 34 | SPSDRAE2 | natif conservé | pas de nouveau pack |
| 35 | SPSHADOW | natif conservé | pas de nouveau pack |
| 36 | TRAVELB | natif conservé | pas de nouveau pack |
