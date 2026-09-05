# Masques alpha par spline

La spline périodique lisse la trajectoire d'une silhouette lorsque le nettoyage gaussien reste trop
fidèle aux marches. Elle est manuelle, produit une nouvelle sortie et exige une QA par cible.

| Cible | Script | Sortie |
|---|---|---|
| Asset ou animation | `build_spline_alpha_mask.py` | nouveau PNG alpha |
| Carte PVRZ | `build_spline_map_alpha.py` | nouveau build TIS/PVRZ |

## Réglages de départ

| Paramètre | Asset | Carte | Rôle |
|---|---:|---:|---|
| `--fit-error` | `1.0` | `1.0` | fidélité du contour |
| `--sample-spacing` | `1.5` | `1.5` | échantillonnage en pixels source |
| `--supersample` | `4` | `2` | rasterisation avant réduction |
| seuil | `127` | interne | frontière initiale |

Ces valeurs proviennent d'AR0604/AM0604A ; elles ne valent pas approbation globale. Réduire
`fit-error` conserve plus de détails, l'augmenter arrondit et peut déplacer les pointes.

## Asset ou animation

```powershell
python pipeline/scripts/build_spline_alpha_mask.py `
  <alpha-source.png> <nouveau-masque.png> `
  --fit-error 1.0 --sample-spacing 1.5 --threshold 127 --supersample 4

python pipeline/scripts/build_manual_alpha_mask_30fps_v2.py `
  --temporal-run <run-30fps-source> --resref <RESREF> `
  --mask <nouveau-masque.png> --run <nouveau-run>
```

Le premier script ajuste la plus grande silhouette fermée. Le second conserve RGB et timeline et
applique le masque dans un nouveau run ; il n'installe rien.

## Carte

```powershell
python pipeline/scripts/build_spline_map_alpha.py `
  --area ARxxxx <build-reference> <nouveau-build> `
  --fit-error 1.0 --sample-spacing 1.5 --supersample 2

python pipeline/scripts/verify_upscaled.py `
  ARxxxx <nouveau-build> <rendu-primaire-x4.png>
python pipeline/scripts/inject_build.py install ARxxxx <nouveau-build> --verify-only
```

Le builder travaille sur le canvas WED complet, traite primaire et secondaire séparément, conserve
trous et îlots, et refuse une réutilisation de tuile ambiguë. Exiger le rapport
`spline-alpha-report.json`, `0 OOB`, DXT5 et un RGB inchangé.

Installer ensuite avec `inject_build.py install`, conserver son reçu et faire la QA en jeu. Une
variante nuit reste un build et une QA indépendants.
