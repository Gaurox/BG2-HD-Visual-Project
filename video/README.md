# Vidéos BG2EE

`index/manifest.json` et `index/resources.csv` constituent l'inventaire canonique des
cinématiques WBM libres et des tutoriels WBM du KEY/BIF. Les WBM utilisés comme animations de
zone restent sous l'autorité de `animations/index/occurrences.csv` et sont exclus ici.

`index/processing.csv` sélectionne les runs validés par étape et le run utilisé par le patch.
`patch_run` vide signifie qu'aucun artefact vidéo n'est intégré au patch.

## Organisation

```text
video/<asset>/
├── <source>.wbm
└── runs/<run-id>/
```

Interdit : nouveau run sous `video/runs/`. Un déplacement historique ne modifie pas le
`run.json` scellé ; les outils résolvent son ancien préfixe vers le dossier asset.

Les sous-dossiers contenant les WBM extraits sont des copies locales ignorées par Git. Régénérer
et contrôler l'inventaire avec les commandes décrites dans
[`../docs/GRAPHICS_INVENTORY.md`](../docs/GRAPHICS_INVENTORY.md).

## Upscale spatial LAB v2

| Élément | Autorité |
|---|---|
| Recette | `../pipeline/comfyui/workflows/SeedVR-Video-BG2-3B-INT8-1080p-LAB-v2.api.json` |
| Runner | `../pipeline/scripts/run_video_upscale.py` |
| Procédure | [`../pipeline/VIDEO_UPSCALE_PIPELINE.md`](../pipeline/VIDEO_UPSCALE_PIPELINE.md) |
| Run | `<asset>/runs/<run-id>/run.json` conforme à `../docs/workspace-run.schema.json` |

La recette LAB v2 couvre uniquement les cinématiques 1280×720 vers 1920×1080. Elle conserve
cadence et nombre d'images. Les tutoriels 384×480 sont refusés.

```powershell
python pipeline/scripts/run_video_upscale.py `
  --asset-key movie:default:FLYTHR03 --run <nouveau-run> --plan

python pipeline/scripts/run_video_upscale.py `
  --asset-key movie:default:FLYTHR03 --run <nouveau-run>
```

Un run terminé prouve uniquement l'upscale technique. Il ne prouve ni QA, interpolation, encodage
de livraison, intégration jeu ou release.

## Interpolation 30 fps v1

| Élément | Autorité |
|---|---|
| Recette | `../pipeline/topaz/recipes/Video-Interpolation-Apollo8-30fps-v1.json` |
| Runner | `../pipeline/scripts/run_video_interpolation.py` |
| Procédure | [`../pipeline/VIDEO_INTERPOLATION_PIPELINE.md`](../pipeline/VIDEO_INTERPOLATION_PIPELINE.md) |

```powershell
python pipeline/scripts/run_video_interpolation.py `
  --upscale-run <run-upscale-scellé> --run <nouveau-run>
```

Apollo 8 produit 30 fps en `2N−1`. `rdt=-0.01` désactive les quasi-doublons ; un post-traitement
hashé retire seulement les frames adjacentes identiques. La sortie ProRes est technique, sans audio.
