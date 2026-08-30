# Comparison asset convention

Website comparisons use the following stable layout:

```text
assets/comparisons/<category>/<area>/<variant>/<crop-id>/
  comparison.json
  source/
    <area>-<variant>-<crop-id>-x1.png
    <area>-<variant>-<crop-id>-x4.png
  web/
    <area>-<variant>-<crop-id>-x1.webp
    <area>-<variant>-<crop-id>-x4.webp
```

Rules:

- Directory and file names are lowercase ASCII; Infinity Engine area identifiers remain visible.
- `variant` is `day`, `night`, or another explicit source variant.
- Crop identifiers are sequential within the same area and variant: `crop-01`, `crop-02`, etc.
- The x1 and x4 files must show the exact same framing.
- An x4 source must have exactly four times the x1 width and height.
- PNG files are preserved as source evidence. WebP files are delivery derivatives and may be
  regenerated from those sources.
- `comparison.json` records dimensions, crop coordinates, hashes and relative asset paths.

The website normally loads files from `web/`. A fidelity-critical comparison may reference the
PNG files from `source/` directly when the exact original pixels must be preserved; neither form
is treated as a project production source.
