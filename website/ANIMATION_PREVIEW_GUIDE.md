# Animation comparison — website only

## Scope

- Write only `website/assets/images/` and website HTML when explicitly approved.
- Never change animation runs, BAMs, alphas, packs, manifests, selections, QA, or ingame files.
- A single resource layer is not an ingame-equivalent capture.

## Validated reference

```text
subject: AR0700 / AM0700A
output:  assets/images/gallery-alpha-am0700a-vanilla-x4-spline-fit1-refined.gif
canvas:  1480x740 / background #0D100F / gold divider x=740
fps:     30
frames:  28 / loop
left:    vanilla x1 / nearest-neighbour / native speed
right:   x4 interpolated / Spline Fit 1 alpha / 1px erosion + gblur sigma=1.0
timing:  vanilla loops twice; x4 loops once; intentional desync
```

## Inputs

```text
vanilla: animations/runs/ar0700-fountains-seedvr7b-lab-x4/resources/AM0700A/01_frames_x1/rgba/
x4:      animations/runs/ar0700-fountains-apo8-x4-30fps-v2/work/AM0700A/cycle_000/review_frames/
masks:   <temp>/masks/spline-000.png ... spline-006.png
```

## Phase mapping

```text
for p in 0..27:
  leftPhase   = p % 14
  rightPhase  = floor(p / 2)
  leftNative  = floor(leftPhase / 2)
  rightNative = min(floor(rightPhase / 2), 6)
```

## Compose

```text
left:   vanilla/frame_leftNative -> scale 712x652:neighbor
right:  x4/frame_rightPhase + masks/spline-rightNative
alpha:  spline -> erosion 1px -> gblur sigma=1.0 -> alphamerge(x4 RGB)
layout: left x=16,y=70; right x=752,y=70
```

## Rules

- Use Spline Fit 1 as replacement alpha; do not multiply it with source alpha for the web preview.
- Smooth mask + jagged edge: RGB fringe; keep `erosion + gblur` in website media only.
- Jagged mask: regenerate only a temporary presentation mask.
- Never transfer website erosion, blur, timing, or GIF palette processing to ingame assets.

## Deliver

```text
name:  gallery-alpha-<resref>-vanilla-x4-spline-fit1-refined.gif
encode: PNG sequence / 30 fps / palettegen + paletteuse / loop
check:  first frame / full loop / ffmpeg decode
link:   only after explicit user approval
```
