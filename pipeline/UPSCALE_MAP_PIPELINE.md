# Upscale des cartes — paramètres retenus

La séquence, les commandes et les gates sont dans [`README.md`](README.md). Cette page fixe
seulement la recette d'inférence.

## Recette par défaut

- SeedVR2 7B INT8, x4, correction colorimétrique LAB ;
- sampler `euler`, scheduler `simple`, une étape, CFG `1`, denoise `1`, VAE FP16 ;
- découpage déterminé par `areas.csv` et
  [`MAP_SPLITTING_POLICY.md`](MAP_SPLITTING_POLICY.md) ;
- variantes principale et secondaire inférées séparément, avec la même échelle et la même grille ;
- x2 seulement sur demande explicite.

Exemple :

```powershell
python pipeline/scripts/run_seedvr_comfyui.py `
  --area ARxxxx --run <run> --preflight <preflight.json> `
  --tile-kind tuiles-principales --split-grid 2 5 `
  --scale 4 --expected-scale 4

python pipeline/scripts/run_seedvr_comfyui.py `
  --area ARxxxx --run <run> --preflight <preflight.json> `
  --tile-kind tuiles-secondaires --split-grid 2 5 `
  --scale 4 --expected-scale 4 --append
```

Adapter ou omettre `--split-grid` selon `split_seedvr`; ne jamais reprendre l'exemple comme valeur
universelle. `--allow-blocked-test` autorise seulement une expérience tracée et ne valide rien.

## Reconstruction

```powershell
python pipeline/scripts/build_upscaled_area.py `
  ARxxxx <principale-x4.png> <build-dir> [secondaire-x4.png]

python pipeline/scripts/verify_upscaled.py `
  ARxxxx <build-dir> <principale-x4.png>
```

- DXT1 si tout est opaque, DXT5 dès qu'un alpha est requis.
- `0 resampled` et `0 OOB` sont obligatoires.
- La pagination 2048/4096 est choisie par le builder selon la capacité du resref.
- Les options eau, alpha, nuit et secondaire viennent du préflight et de leurs guides spécialisés.

Les anciens comparatifs de modèles sont archivés ; les décisions réutilisables restent dans
[`../docs/DECISIONS.md`](../docs/DECISIONS.md).
