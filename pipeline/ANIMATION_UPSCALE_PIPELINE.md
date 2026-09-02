# Upscale spatial des animations BAM

## Sélection et run

```powershell
python pipeline/scripts/run_animation_upscale.py `
  --resref AMxxxx --scale 4 --plan

python pipeline/scripts/run_animation_upscale.py `
  --area ARxxxx --scale 4 --plan

python pipeline/scripts/run_animation_upscale.py `
  --area ARxxxx --run <nouveau-run> --scale 4
```

`--resref` et `--area` sont répétables. `--prepare-only` arrête avant ComfyUI ; `--resume`
revalide et reprend strictement le même run. Le script ne modifie ni jeu, DLL, INI, override ni
catalogue.

## Contrat du run

- sources BAM copiées et hashées avant traitement ;
- cycles, frames, centres et dimensions conservés ;
- frames exportées séparément, jamais en planche ;
- RGB upscalé frame par frame, alpha reconstruit séparément ;
- dimensions et manifests vérifiés avant le pack runtime ;
- sortie existante incompatible refusée, jamais réécrite.

Les géométries différentes entre frames sont normales : l'alignement vient du centre BAM, pas d'un
canvas forcé commun.

## Pack runtime

```powershell
python pipeline/scripts/build_animation_runtime_pack.py `
  animations/ressources/<RESREF>/runs/<run-id> [<nouveau-pack>]
```

Pour un lot, utiliser `animations/batches/<run-id>`. Un chemin sous `animations/runs/` n'est fourni
que pour reprendre explicitement un run legacy existant.

`--include-pack` compose des packs v1 terminés ; `--alpha-override-manifest` conserve un correctif
alpha approuvé ; `--resume` revalide sans écrire. Un pack au-delà de 512 Mio doit être produit en
mode auteur lorsqu'il y a lieu, puis découpé selon
[`ANIMATION_PACKS_PAR_ZONE.md`](ANIMATION_PACKS_PAR_ZONE.md).

## Gates

1. sélection = BAM typé et source disponible ;
2. export = inventaire complet, hashes et géométrie cohérents ;
3. upscale = dimensions ×4 exactes et alpha valide ;
4. pack = registre relu, assets présents et budget respecté ;
5. QA = décision utilisateur, puis mise à jour du registre canonique ;
6. release = décision séparée dans `animation-release-candidates.json`.

Pour une timeline 30 fps, partir du pack spatial achevé et suivre
[`ANIMATION_UPSCALE_30FPS_V2.md`](ANIMATION_UPSCALE_30FPS_V2.md).
