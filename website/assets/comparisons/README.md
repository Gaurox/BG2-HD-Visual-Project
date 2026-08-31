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
- WebP files are delivery derivatives. The PNG or JPEG they were generated from is source
  evidence and is kept next to them only while it is worth its weight: once the WebP is the file
  the pages load, the heavy original may be dropped from the repository. It then stays recoverable
  from Git history, and `comparison.json` records `sourceRetained: false` while keeping
  `sourceSha256`, so the original a WebP derives from remains identifiable.
- `comparison.json` records dimensions, capture or crop metadata, hashes and relative asset paths.
  An asset entry omits its `source` path when the original is no longer retained.

Page layout: a comparison frame steps outside the reading column and is sized by
`max(--shell, min(--shell-wide, --compare-max-height * --compare-aspect))`, so it widens on a
large screen but never gets taller than the viewport. Each `.compare-frame` declares
`--compare-aspect` inline. When frames sit inside a wrapper that carries the width — the gallery
feature block, the in-game grid — that wrapper declares the same `--compare-aspect`, which means
frames grouped under one wrapper must share an aspect ratio.

The website normally loads files from `web/`. A fidelity-critical comparison may reference the
PNG files from `source/` directly when the exact original pixels must be preserved; neither form
is treated as a project production source.
