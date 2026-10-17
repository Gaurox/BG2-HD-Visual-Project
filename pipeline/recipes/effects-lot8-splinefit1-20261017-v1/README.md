# Huit effets — SplineFit1

- `derive.py` : dérivés alpha-only des8 désignés, sources v2 scellées immuables, nouveaux runs/packs. Réutilise `build_per_frame_spline_alpha_30fps_v2.spline_alpha` : fit_error1 x4, sample_spacing1.5, SS4, padding32, threshold0, inner_feather0. RGB droits exacts, RGB prémultipliés rescalés par Anew/Aold.
- `verify.py` : relecture404phases, hashes, RGBdroits exacts, cohérence prémultipliée≤1niveau, trous conservés, Anew≤Aold, géométrie/carrier/timings identiques. Les18autres productions restent v2.
- `review.py` : galerie26, avant/après8 avec mêmes cycles. Productions : `effects/batches/lot26-seedvr7b-apollo30-20261017-v3/`.
- Pas de nouvelle inférence, QA acquise, installation ou release.
