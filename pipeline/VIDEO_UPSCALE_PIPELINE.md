# Upscale spatial des vidéos

## Contrat LAB v2

| Champ | Valeur |
|---|---|
| Entrée | `video/index/resources.csv`, `role=cinematic`, 1280×720 |
| Sortie | 1920×1080, cadence et images conservées, progressif |
| Modèle | `seedvr2_3b_int8_convrot.safetensors` |
| VAE | `seedvr2_ema_vae_fp16.safetensors` |
| VAE spatial | tuile 512, recouvrement 128 |
| VAE temporel | taille 64, recouvrement 8 |
| Sampler | seed `959948902156062`, Euler, 1 pas, CFG 1, simple, denoise 1 |
| Pré-redimensionnement | Lanczos, 1920×1080, crop centré |
| Couleur | `lab` |
| Latent temporel | découpage `auto`, recouvrement 0, fusion activée |
| Workflow | `comfyui/workflows/SeedVR-Video-BG2-3B-INT8-1080p-LAB-v2.api.json` |
| SHA-256 workflow | `B379615AFD78660DCE7C9283DAAFB0B91E40ACF4832E9CFD88D2E58A0A296F4A` |

Le runner refuse toute dérive du workflow, source absente, hash d'inventaire différent, file
ComfyUI non vide ou tutoriel 384×480.

## Exécution

```powershell
python pipeline/scripts/run_video_upscale.py `
  --asset-key movie:default:<RESREF> --run <run-id> --plan

python pipeline/scripts/run_video_upscale.py `
  --asset-key movie:default:<RESREF> --run <run-id>
```

ComfyUI vient de `config://comfyui_url`. Le workflow est modifié uniquement en mémoire pour le nom
d'entrée et le préfixe de sortie.

## Run immuable

```text
video/<asset>/runs/<run-id>/
  request.json
  run.json
  upscale-report.json
  02_upscale/<RESREF>-1080p-seedvr2-3b-int8.<ext>
```

`run.json` suit `docs/workspace-run.schema.json`. Un run existant est refusé. Un échec est scellé ;
rejouer avec un nouvel identifiant.

## Gates techniques

1. asset présent dans l'inventaire canonique et hash source exact ;
2. workflow hashé et paramètres v1 exacts ;
3. nœuds ComfyUI disponibles, file vide ;
4. sortie 1920×1080 progressive ;
5. cadence et nombre d'images identiques à la source.

## Hors périmètre

- interpolation ;
- audio autoritaire ;
- encodage de livraison ;
- QA visuelle ;
- intégration jeu ;
- sélection release.

Ces étapes ne doivent ni modifier ni promouvoir le run d'upscale scellé.
