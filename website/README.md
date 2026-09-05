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
- The progress dashboard shows ten visual domains (maps, animations, sprites, effects, UI/HUD,
  videos, icons, portraits, projectiles, cursor set), transcribed by hand from canonical indexes.
  Nothing is fetched automatically. To refresh it, edit both language pages: update each track’s
  raw counts (`--total` / `--produced` / `--qa` / `--release`), visible copy, aria-label, primary
  percentage, snapshot and totals.
- The global progress bar is a workload-weighted measure using retained results (`produced / total`):
  maps 10%, animations 30%, sprites 40%; effects, UI/HUD, videos, icons, portraits, projectiles and
  cursor set share the remaining 20% equally. Zone packs and payload files never enter this ratio.
- Several page images are real project material rather than concept art. Each ships as the WebP
  the pages load; the full-resolution master stays outside the repository, and any heavy source
  that the site had stopped serving has been dropped and is recoverable from Git history.
  - Home hero: AR0700 vanilla-to-x4 render (`assets/images/hero-ar0700-vanilla-x4.webp`).
  - Progress hero: an upscaled in-engine map render (`assets/images/hero-city-rooftops.webp`).
  - Home "Map upscaling" card: AR1600 (Trademeet) at x4
    (`assets/images/hero-ar1600-trademeet.webp`), downscaled from a ~12.7k-wide master.
  - Home "Creature sprite studies" card: a goblin sprite frame through the local scalepix
    x2 upscalers, as a plate (`assets/images/creature-sprite-studies.webp`).
  The featured map comparison uses a matched AR0700 x1/x4 pair. Remaining concept images are
  temporary and can be replaced without changing the layouts.
- Comparison assets follow the convention documented in `assets/comparisons/README.md`.
- Animated vanilla/x4 presentation comparisons follow
  [`ANIMATION_PREVIEW_GUIDE.md`](ANIMATION_PREVIEW_GUIDE.md). This is website-only guidance;
  it does not authorize changes to production animation assets.
- Generated-image briefs are recorded in `ASSET_PROMPTS.md`.

No build step or package installation is required.
