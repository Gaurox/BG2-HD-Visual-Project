# Interpolation vidéo 30 fps

## Contrat v1

| Champ | Valeur |
|---|---|
| Entrée | sortie `upscale-technical-video` d'un run vidéo `completed`, `sealed=true` |
| Source | 1920×1080, 15 fps, progressive |
| Modèle | Topaz Apollo 8 (`apo-8`) |
| Sortie | 1920×1080, 30 fps CFR, progressive, sans audio |
| Temporalité | `2N−1` avant suppression exacte ; aucun doublon terminal ajouté |
| Doublons Topaz | `rdt=-0.01` ; détection approximative désactivée |
| Doublons exacts | MD5 des frames décodées ; répétitions adjacentes supprimées |
| Intermédiaire | MOV ProRes 422 HQ, `yuv422p10le`, non final |
| Recette | `topaz/recipes/Video-Interpolation-Apollo8-30fps-v1.json` |
| SHA-256 | `E707DD23CB5FE789B2D0AE14DE53392AB107C51B54A986771015E106ABB47D5E` |

## Exécution

```powershell
python pipeline/scripts/run_video_interpolation.py `
  --upscale-run <run-upscale-scellé> --run <nouveau-run> --plan

python pipeline/scripts/run_video_interpolation.py `
  --upscale-run <run-upscale-scellé> --run <nouveau-run>
```

Chemins Topaz : `config://topaz_video_ffmpeg`, `config://topaz_video_models`.

## Run immuable

```text
video/<asset>/runs/<run-id>/
  request.json
  run.json
  interpolation-report.json
  topaz.log
  exact-duplicate-filter.txt          # seulement si doublons trouvés
  03_interpolation/video-1080p-30fps-apollo8.mov
```

Le run enfant conserve `videos:<run-upscale>` dans `provenance.parents`. Un run existant est refusé.

## Gates

1. parent vidéo terminé, scellé, preuve `upscale-technical-video` exacte ;
2. recette hashée, Apollo 8 installé ;
3. entrée 1920×1080 progressive à 15 fps ;
4. sortie Topaz 30 fps avec `2N−1` frames ;
5. sortie finale progressive, ProRes, sans audio, zéro doublon exact adjacent.

## Hors périmètre

- encodage de livraison ;
- audio et synchronisation finale ;
- intégration jeu ;
- QA visuelle d'asset ;
- sélection release.
