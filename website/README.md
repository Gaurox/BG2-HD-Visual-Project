# BG2 HD Visual Project — website mockup

Static, responsive visual mockup for the project website. It is deliberately independent from
the production pipelines and contains no release manifest or real progress data.

## Pages

- `index.html` — project presentation and visual direction
- `progress.html` — dashboard layout with clearly marked sample values
- `gallery.html` — filterable gallery and interactive comparison layout

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

- All public-facing mockup copy is in English.
- The FR control is reserved but intentionally inactive until approved French copy exists.
- Dashboard values are visual placeholders, not project status.
- The home hero uses a real AR0700 vanilla-to-x4 render (`assets/images/hero-ar0700-vanilla-x4.*`,
  full-resolution PNG kept as source next to a 2560px WebP delivery copy). The featured map
  comparison uses a matched AR0700 x1/x4 pair. Other concept images remain temporary and can be
  replaced without changing the layouts.
- Comparison assets follow the convention documented in `assets/comparisons/README.md`.
- Generated-image briefs are recorded in `ASSET_PROMPTS.md`.

No build step or package installation is required.
