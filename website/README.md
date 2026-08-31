# BG2 HD Visual Project — website mockup

Static, responsive visual mockup for the project website. It is deliberately independent from
the production pipelines and contains no release manifest or real progress data.

## Pages

- `index.html` — project presentation and visual direction
- `progress.html` — progress dashboard, seven asset domains, figures kept by hand
- `gallery.html` — filterable gallery and interactive comparison layout

Each page has a French counterpart under `fr/` with identical layout. The two
language sets share `assets/`; the header `EN / FR` control links each page to
its other-language pair. See `locales/README.md`.

## Local preview

From the repository root:

```powershell
python -m http.server 4173 --directory website
```

Then open `http://127.0.0.1:4173/`.

## GitHub Pages

The repository workflow `.github/workflows/website-pages.yml` uploads this directory as a static
GitHub Pages artifact. After the repository is connected to GitHub, choose **GitHub Actions** as
the Pages source in the repository settings. The workflow runs on changes to `website/` on `main`
and can also be started manually.

## Content status

- Public-facing copy exists in English (root) and French (`fr/`); the `EN / FR` control switches
  between the two mirrored page sets.
- The progress dashboard shows real figures for seven asset domains (maps, animations, sprites,
  effects, UI/HUD, videos, icons), transcribed by hand from the tracking workbook. Nothing is
  fetched automatically. To refresh it, edit both language pages: for each domain update the raw
  counts in the `style` attribute (`--total` / `--produced` / `--qa` / `--release`), the numbers in
  the visible text and the headline percentage, then the snapshot date and the four totals. The
  bars derive their widths from the raw counts, so they stay in sync on their own.
- Several page images are real project material rather than concept art. Most keep a
  full-resolution source next to a lighter WebP delivery copy the pages load; the largest
  source stays outside the repo and only the WebP ships.
  - Home hero: AR0700 vanilla-to-x4 render (`assets/images/hero-ar0700-vanilla-x4.*`).
  - Progress hero: an upscaled in-engine map render (`assets/images/hero-city-rooftops.*`).
  - Home "Map upscaling" card: AR1600 (Trademeet) at x4, WebP only
    (`assets/images/hero-ar1600-trademeet.webp`), downscaled from a ~12.7k-wide master.
  - Home "Creature sprite studies" card: a goblin sprite frame through the local scalepix
    x2 upscalers, as a plate (`assets/images/creature-sprite-studies.*`).
  The featured map comparison uses a matched AR0700 x1/x4 pair. Remaining concept images are
  temporary and can be replaced without changing the layouts.
- Comparison assets follow the convention documented in `assets/comparisons/README.md`.
- Generated-image briefs are recorded in `ASSET_PROMPTS.md`.

No build step or package installation is required.
