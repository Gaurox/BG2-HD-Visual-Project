# Warm-patch targeted Gaussian blur — AM0803B/C/E

Removes SeedVR2 7B "bead / flowing marbles" artifacts on the bright glowing
"coulure" of the Bodhi's Lair blood pools, without touching the dark pool.

- `warmblur_v8.py` — mask + blur. Mask: bright warm seed (V>92, largest connected
  component) → propagate through `Vmax>78 & warm` over the loop → fill + close +
  margin dilation + gaussian feather. Blur = Gaussian on premultiplied RGB inside
  the mask; alpha verbatim.
- `bake_warmblur_final.py` — applies it to the completed spline-fit1-feather4
  30fps v2 packs of AM0803B/C/E, rewrites only the 14 .rgba + the sha256 fields
  in `03_runtime_pack/manifest.json` (registry is structural-only, stays identical).
  Also fix the run's top `manifest.json` `pack_manifest_sha256` afterwards.

Validated in game 2026-09-07 at blur radius r3.5, margin_dil B=3 / C,E=8.
Recipe id: `spline-fit1-multicontour-per-frame-feather4-warmpatchblur-r3p5`.
Not yet a formal pipeline script.
