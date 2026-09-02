# Animations x4 à 30 fps — TimedTimeline v2

TimedTimeline double les positions temporelles sans accélérer le cycle et conserve la pause/reprise.
La QA vidéo et la QA ingame sont obligatoires.

## Plan

```powershell
python pipeline/scripts/run_animation_upscale_30fps_v2.py plan `
  --source-run <id-ou-chemin-run-spatial> `
  --base-pack <pack-complet> --resref <RESREF> --run <nouveau-run> > <plan.json>
```

Pour un asset x4/15 fps déjà présent avec ancres homogènes, remplacer `--source-run` par
`--base-runtime-only`. Répéter `--resref` si nécessaire. N'utiliser
`--collapse-uniform-duplicate-holds` qu'après constat de maintiens uniformes ; le plan et le build
doivent porter exactement la même option.

Vérifier resrefs, cycles, nombre de phases, durée, bytes ajoutés, base pack et `plan_sha256`. Un
pack partiel ou une cible déjà TimedTimeline est bloquant.

## Build immuable

```powershell
$plan = Get-Content <plan.json> -Raw | ConvertFrom-Json
python pipeline/scripts/run_animation_upscale_30fps_v2.py build `
  --source-run <id-ou-chemin-run-spatial> `
  --base-pack <pack-complet> --resref <RESREF> `
  --run <nouveau-run> `
  --approve-plan-sha256 $plan.plan_sha256
```

Les chemins Topaz viennent de `config://topaz_video_ffmpeg` et
`config://topaz_video_models`; les options CLI ne servent qu'à une surcharge explicite. Après
interruption, relancer la même commande avec `--resume`. Toute autre recette reçoit un nouveau run.

Pour un pack d'auteur destiné au split par zone, ajouter `--authoring-pack-for-area-split` au plan
et au build. Il reste non installable avant découpage.

## RGB transparent pour Topaz

Si le RGB sous `alpha=0` est un chroma key et contamine les phases intermédiaires, ajouter aux deux
commandes :

```powershell
--transparent-rgb-mode nearest-opaque-dilate
```

Le mode propage la couleur opaque la plus proche seulement dans les images RGB livrées à Topaz ;
les ancres x4, alpha, géométrie et pack source restent inchangés. Le mode est hashé dans le plan et
enregistré dans le run. QA visuelle obligatoire ; ne pas l'utiliser sans contamination constatée.

## QA et approbation

Afficher chaque `review-30fps-loop-4s.mp4`, puis contrôler la review exacte pour la couture. Après
acceptation explicite de tous les cycles :

```powershell
$run = 'animations/ressources/<RESREF>/runs/<nouveau-run>'
$hash = (Get-FileHash -Algorithm SHA256 "$run/manifest.json").Hash.ToLowerInvariant()
python pipeline/scripts/run_animation_upscale_30fps_v2.py approve `
  --output $run --approve-run-manifest-sha256 $hash --resref <RESREF>
python pipeline/scripts/run_animation_upscale_30fps_v2.py validate --output $run
```

Pour un build multi-resrefs, utiliser à la place `animations/batches/<nouveau-run>`.

`qa-approval.json` doit couvrir exactement les resrefs approuvés. Il scelle la revue technique et
vidéo du run ; il ne vaut pas décision QA ingame. Un refus conserve le run, sans approbation ni
installation.

## Installation réversible

Jeu et InfinityLoader fermés, et seulement si l'installation est autorisée :

```powershell
.\pipeline\scripts\Install-AreaAnimations-30fps-V2.ps1 -RunRoot $run -VerifyOnly
.\pipeline\scripts\Install-AreaAnimations-30fps-V2.ps1 -RunRoot $run

.\pipeline\scripts\Restore-AreaAnimations-30fps-V2.ps1 `
  -BackupPath <backup> -VerifyOnly
.\pipeline\scripts\Restore-AreaAnimations-30fps-V2.ps1 `
  -BackupPath <backup>
```

La QA ingame couvre vitesse, couture, pause/reprise, entrée/sortie du champ, changement de zone,
géométrie, alpha et occlusion. Après décision explicite, utiliser `animation_workflow.py finalize`
pour mettre à jour atomiquement la preuve ingame, la sélection et le registre. La release reste une
décision séparée.
