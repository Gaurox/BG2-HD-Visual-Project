# Interpolation temporelle d'une animation BAM

Pipeline générique v1 pour une ressource BAM à cycle unique. Les ressources multi-cycles sont
refusées. Pour un pack complet pause-aware, préférer
[`ANIMATION_UPSCALE_30FPS_V2.md`](ANIMATION_UPSCALE_30FPS_V2.md).

## Invariants

- mesurer la cadence des slots BAM ; ne jamais la déduire du nombre de frames ;
- fermer la boucle dernière → première avant interpolation ;
- conserver durée, ordre, centre, crop et alpha source ;
- Topaz produit le mouvement RGB ; l'alpha des phases reste déterministe ;
- toute proposition, entrée, sortie et décision est hashée ;
- le script ne touche jamais au jeu.

## Chaîne

```powershell
python pipeline/scripts/run_animation_interpolation.py plan `
  --resref <RESREF> --frames-manifest <frames.json> `
  --upscale-manifest <upscale.json> --base-pack <pack> --slot-fps <fps>

python pipeline/scripts/run_animation_interpolation.py prepare-video `
  --resref <RESREF> --frames-manifest <frames.json> `
  --upscale-manifest <upscale.json> --base-pack <pack> --slot-fps <fps> `
  --output <work-root>

python pipeline/scripts/run_animation_interpolation.py interpolate `
  --work-root <work-root> --model apo-8

python pipeline/scripts/run_animation_interpolation.py ingest-frames `
  --work-root <work-root> --input-frames <png-dir>

python pipeline/scripts/run_animation_interpolation.py build-patch `
  --work-root <work-root> --output <nouveau-patch>
```

`interpolate` peut être omis si les PNG conformes au contrat de `prepare-video` sont fournis. Les
chemins Topaz sont résolus par la configuration du workspace. `build-patch --resume` revalide une
sortie identique.

## Gates

1. Le plan décrit cadence, durée, phases, base pack et boucle ; obtenir l'accord avant calcul.
2. Le MP4 source contient la frame de fermeture et le contrat de retour.
3. `ingest-frames` vérifie nombre, ordre, dimensions et hashes des PNG.
4. Le patch différentiel contient registre cible, nouvelles phases et hashes de base.
5. L'installation reste une action séparée, jeu fermé :

```powershell
.\pipeline\scripts\Install-AreaAnimation-Interpolation-Patch.ps1 `
  -PatchRoot <nouveau-patch>
.\pipeline\scripts\Restore-AreaAnimation-Interpolation-Patch.ps1 `
  -BackupPath <backup>
```

Après QA utilisateur, synchroniser le registre spatial si nécessaire. Le patch ou sa présence dans
le jeu ne prouve ni l'approbation ni la release.
