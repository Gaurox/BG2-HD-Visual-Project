# BG2 HD Visual Project — website mockup

Static, responsive visual mockup for the project website. It is deliberately independent from
the production pipelines and contains no release manifest or real progress data.

## Pages

- `index.html` — project presentation and visual direction
- `progress.html` — dashboard, ten visual domains, figures kept by hand
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

## Mise à jour Progress — protocole LLM

Périmètre : `website/` uniquement. Ne jamais modifier les autorités métier, les runs, les
projections `asset-tracking/` ou les manifests release pour cette tâche.

1. Lire `areas.csv`, les index indiqués ci-dessous et les deux pages `progress.html`.
2. Mettre à jour EN et FR à l’identique : compteurs CSS, texte, `aria-label`, pourcentage,
   relevé, totaux, deux barres globales.
3. `release` est un axe distinct. Ne jamais le déduire de `produced`, QA ou installation.
4. Ne pas lancer `workspace.py ... --run`, build, packaging ni tests sans choix explicite.

| Piste | Total canonique | `produced` | QA | `release` / note |
|---|---|---|---|---|
| Maps | `areas.csv` : 1 variante jour par ligne + 1 nuit si `has_night_variant=yes` | `status`/`status_nuit` ∈ `validated-installed`, `installed-pending-qa` | `validated-installed` | `content.json` : `kind=map`, `area` distinct |
| Animations | `animations/index/animation_upscale_registry.csv` : lignes BAM | `status` ∈ `validé-x4`, `validé-natif` | fichiers courants `animations/index/selections/*.json` | barre : `0`; note séparée = candidats `approval_status=approved-for-release` dans `animation-release-candidates.json` |
| Sprites | `sprite/index/sprite_families.csv` + `graphics/index/supplemental-assets.csv` (`domain=sprites`) | `active-test.json` du catalogue : `component_count` | `0` tant que le statut actif est `installed-pending-qa` | `0` |
| Effects | `effects/index/resources.csv` + compléments `domain=effects` | `0` sauf autorité dédiée future | `0` | `0` |
| UI & HUD | 33 extraction UI non-PVRZ/non-HUD + `interface/index/resources.csv` + HUD + fonts + compléments `domain=ui` + 2 composants de menus | composants `ui-mainmenu-x4`, `ui-selector-x4` validés dans `content.json` | mêmes composants validés | mêmes composants dans `content.json` |
| Videos | `video/index/resources.csv` | lignes `processing.csv` où `upscale_state=validated` et `interpolation_state=validated` | `0` : validation de méthode ≠ QA ingame | `0` tant que `patch_state=not-integrated` |
| Icons | `icons/index/resources.csv` | `0` sans autorité de production | `0` | `0` |
| Portraits | lignes `portraits/inventaire_portraits.csv` | `0` sans autorité de production | `0` | `0` |
| Projectiles | `projectiles/index/resources.csv` | `0` sans autorité de production | `0` | `0` |
| Cursor set | `cursors/index/resources.csv` | `0` sans autorité de production | `0` | `0` |

Chemins sprites actifs :

```text
sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/runs/catalog-xbr2x-x2/current-generation.json
sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/runs/catalog-xbr2x-x2/ingame-installation/active-test.json
```

Formules d’agrégat :

```text
results = Σ produced
p(domain) = produced(domain) / total(domain)
work_progress = 0.10*p(maps) + 0.30*p(animations) + 0.40*p(sprites)
              + (0.20/7)*Σ p(effects, ui, videos, icons, portraits, projectiles, cursor)

visible(maps) = qa(maps) / total(maps)
visible(animations) = produced(animations) / total(animations)
visible(sprites) = produced(sprites) / total(sprites)
visible(ui) = qa(ui) / total(ui)
visible(videos, effects, icons, portraits, projectiles, cursor) = 0 until in-game integration
ingame_progress = 0.50*visible(maps) + 0.30*visible(animations) + 0.10*visible(sprites)
                + (0.10/7)*Σ visible(effects, ui, videos, icons, portraits, projectiles, cursor)
```

- Arrondir chaque barre globale à une décimale ; mettre à jour son `--overall-progress`, texte et `aria-label`.
- Les packs de zone, fichiers payload et occurrences ne participent jamais à `global_progress`.
- Vérifier `git diff --check` seulement ; proposer ensuite « tests ciblés / tous / aucun » sans lancer de test.
