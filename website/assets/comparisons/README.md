# Comparison asset convention

Website comparisons use the following stable layout:

```text
assets/comparisons/<category>/<scope>/<variant>/<comparison-id>/
  comparison.json
  source/
    <scope>-<variant>-<comparison-id>-<mode>.<extension>
  web/
    <scope>-<variant>-<comparison-id>-<mode>.webp
```

Rules:

- Directory and file names are lowercase ASCII; Infinity Engine area identifiers remain visible.
- `scope` is an area resref for map assets (for example `ar0700`) or `bg2ee` for a UI-inclusive
  in-game screenshot.
- `variant` is `day`, `night`, `default`, or another explicit source variant.
- Map comparisons use sequential crop identifiers within the same area and variant: `crop-01`,
  `crop-02`, etc. In-game comparisons use `capture-01`, `capture-02`, etc.
- Map pairs use modes `x1` and `x4`, must show the exact same framing, and the x4 source must have
  exactly four times the x1 width and height.
- In-game pairs use modes `vanilla` and `x4` and must share the same capture viewport dimensions.
- PNG files are preserved as source evidence. WebP files are delivery derivatives and may be
  regenerated from those sources. Original JPEG screenshots are likewise preserved as source
  evidence.
- `comparison.json` records dimensions, capture or crop metadata, hashes and relative asset paths.

The website normally loads files from `web/`. A fidelity-critical comparison may reference the
PNG files from `source/` directly when the exact original pixels must be preserved; neither form
is treated as a project production source.
