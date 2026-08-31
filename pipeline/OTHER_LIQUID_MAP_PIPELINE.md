# Liquides et overlays non standards

Le préflight route ici les overlays `WT*`/`YS*` qui ne suivent pas automatiquement la recette eau.
Leur couleur, alpha, animation et profil optique doivent être établis par famille.

## Autorités

- Politique des overlays livrés :
  `releases/BG2-HD-Upscale/manifests/overlay-sources.json`.
- État et QA des zones : `areas.csv`.
- Routage technique : `audit_area_preflight.py`, `audit_water_area.py` et
  `build_upscaled_area.py`.
- Problème ouvert WTLAVA-D : [`PROBLEMES_A_RESOUDRE.md`](PROBLEMES_A_RESOUDRE.md).

Ne pas déduire la politique depuis l'`override`, un ancien backup ou une zone témoin.

## Familles connues

| Famille | Overlay release | Traitement de zone |
|---|---|---|
| `WTSWAM`, `WTSEW`, `WTOIL` | stock | restauration/lissage alpha selon audit |
| `WTLAKE`, `WTPOOL`, `WTLAKA-D` | package x2/x4 selon `overlay-sources.json` | branche eau/alpha selon audit |
| autre liquide | aucune recette implicite | préflight bloquant jusqu'à décision |

La classification de `WTLAVA-D` dans les scripts de préflight contredit actuellement le manifeste
release. Ne pas masquer cette divergence.

## Règles de build

- Restaurer l'alpha des variantes principale et secondaire depuis les données natives.
- Employer `--transparent-full-water-base` uniquement si l'audit identifie les bases opaques sans
  secondaire sous le liquide.
- Garder les tuiles à secondaire et leurs masques inverses.
- Ne jamais installer un overlay déclaré `stock` ni reconstruire un atlas pour corriger une
  sentinelle locale.
- Toute nouvelle famille exige une zone témoin, une comparaison vanilla/patch et une QA de
  non-régression avant généralisation.

Les paramètres historiques et verdicts par zone restent dans les runs, `areas.csv`, les preuves
moteur et [`../docs/DECISIONS.md`](../docs/DECISIONS.md), pas dans ce guide.
