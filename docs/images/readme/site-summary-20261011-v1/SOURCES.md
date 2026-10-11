# README visual sources — 2026-10-11 v1

Source: `https://bg2hd.gaurox.dev/`; canonical checkout `config://website_checkout`.
Paths below are relative to that checkout. Game media remain excluded from root MIT.
Only layout, crops and display resizing changed; no AI-generated replacement pixels.

| Output | Source | Adaptation |
|---|---|---|
| `map-ar0700.webp` | `assets/comparisons/maps/ar0700/day/crop-02/web/ar0700-day-crop-02-{x1,x4}.webp` | Complete matched crops; 900 px per panel; x1 nearest, x4 Lanczos; English labels. |
| `animation-ar0700-fountain.gif` | `assets/images/gallery-alpha-am0700a-vanilla-x4-spline-fit1-refined.webp` | 14 frames, 1000 × 500; GIF timing 930 ms vs source 933 ms; original labels retained. Isolated web study. |
| `effects-horror.webp` | `assets/comparisons/ingame/effects/horror/web/effects-horror-capture-01-{vanilla,x4}.webp` | Identical crop `(700,220,1580,780)`; 880 px per panel, no resize; English labels. Different animation phases; x4 side also treats maps/animations; sprites native. |
| `sprites-vanilla-nearest-vs-reboutcx-ingame.webp` | `assets/comparisons/ingame/bg2ee/party-sprites/capture-01/web/bg2ee-party-sprites-capture-01-{nearest,reboutcx}.webp` | Identical crop `(850,510,1660,1300)`; no resize; English labels; 1644 × 848. Same party, slightly different animation poses. |

Sprite provenance: adjacent `comparison.json`; captures dated 2026-09-21. Vanilla ×1 nearest / installed ReboutCX ×2. Right background ×4, left vanilla. Site alignment already resamples ReboutCX with cubic spline, scale 1.01099; montage preserves supplied web pixels.

Content snapshot: `/progress` and `/news`, published figures dated 2026-10-07.
The September ReboutCX capture is not relabelled as October Q3M production.
