# Pipeline V2 x4 + 30 fps — runbook agent

## Routage

Utiliser ce document pour transformer des animations de zone BAM déjà upscalées x4 et lues à
15 fps en ressources `TimedTimeline` à 30 fps, sans accélérer leur cycle.

Ne pas utiliser cette voie :

- pour produire le x4 spatial initial : suivre
  [`ANIMATION_UPSCALE_PIPELINE.md`](ANIMATION_UPSCALE_PIPELINE.md) ;
- pour remplacer uniquement les répétitions d'un cycle sans modifier l'horloge : suivre
  [`ANIMATION_INTERPOLATION_PIPELINE.md`](ANIMATION_INTERPOLATION_PIPELINE.md) ;
- pour 20 ou 25 fps : le runtime les représente, mais ce pipeline est verrouillé sur 15 -> 30 et
  aucun contrat de génération 20/25 n'est validé.

Script principal : `pipeline/scripts/run_animation_upscale_30fps_v2.py`.

## Contrat fixe

- Entrée, choisir exactement une voie :
  - `--source-run` : run V1 x4, schéma `bg2-upscale-area-animation-run-v1`, statut `completed` ;
  - `--base-runtime-only` : ancres 15 fps du pack de base, uniquement si la ressource est
    complète, `Native` et de géométrie uniforme.
- Base runtime : pack complet V1 ou V2 correspondant à l'état qui sera actif à l'installation.
- Une cible doit être en mode `Native` dans le pack de base.
- Cadences : native `15/1`, cible `30/1`.
- Modèle : Topaz `apo-8`, filtre `tvai_fi`, `fps=30`, `rdt=-0.01`, device par défaut `-2`.
- Cycle de `N` positions : `N` ancres + `N` intermédiaires, `2*N` phases, durée `N/15` inchangée.
- Exception explicite `--collapse-uniform-duplicate-holds` : un cycle composé de maintiens
  consécutifs identiques et tous de longueur `H >= 2` devient une suite de poses uniques ; chaque
  transition reçoit `2*H-1` intermédiaires, soit `2*H` phases à 30 fps. Durée inchangée. Refuser
  une répétition non uniforme, une pose réutilisée dans plusieurs maintiens ou un maintien à la
  couture cyclique. Ne jamais activer cette exception par défaut.
- Entrée Topaz : cycle sur canvas x4 aligné + première position ajoutée une fois.
- Sortie Topaz admise : exactement `2*N+1` ou `2*N` PNG.
- Phase paire : asset natif byte-identique ; ne jamais prendre l'ancre recalculée par Topaz.
- Phase impaire : RGB Topaz, crop de la frame native gauche, alpha runtime exact de cette frame.
- Stratégie cyclique multi-contexte interdite : essai refusé en QA.
- Les ressources non ciblées restent `Native`, assets et cycles inchangés.
- Le run V1, le pack de base, le jeu, la DLL, l'INI et les catalogues ne sont jamais modifiés par
  le script Python.

Plafonds identiques au parseur runtime : 512 ressources, 4 096 frames par resref, 256 cycles par
resref, 65 536 positions par cycle/timeline, dimension logique maximale 8 192 et 512 MiB RGBA par
pack. Ne pas augmenter ces limites localement.

**Le plafond de 512 MiB est cumulatif sur tout le jeu, pas par zone**, tant qu'un seul registre
global est installé. L'inventaire complet pèse ~2,7 GiB en x4 natif et ~8 GiB une fois interpolé :
un pack global ne peut donc pas couvrir le jeu. La sortie de ce pipeline est désormais un **pack
d'auteur** à découper par zone avant installation — voir
[`ANIMATION_PACKS_PAR_ZONE.md`](ANIMATION_PACKS_PAR_ZONE.md). Ajouter
`--authoring-pack-for-area-split` au `plan` **et** au `build` pour un lot qui dépasserait 512 MiB
en cumul ; le pack produit porte alors `runtime_budget_enforced: false` et l'installateur refuse
de le poser tel quel.

### Cadence cible : pourquoi 30 et pas 20 ou 25

Le runtime représente n'importe quelle cadence rationnelle, mais **descendre sous 30 fps ne
réduit pas la mémoire** — c'est l'inverse de l'intuition. 30 est un multiple de 15, donc une phase
sur deux réutilise une frame native déjà stockée. Aux autres cadences les phases ne retombent plus
sur les natives :

| Cible | Frames nouvelles | Coût mémoire | Fluidité |
|---|---|---|---|
| 20 fps | `N` | 1,00× | 1,33× |
| 25 fps | `4N/3` | 1,33× | 1,67× |
| **30 fps** | `N` | **1,00×** | **2,00×** |

20 fps coûte autant que 30 pour une animation moins fluide ; 25 fps est pire sur les deux tableaux.
Le pipeline reste donc verrouillé sur 15 → 30, et la voie mémoire est le découpage par zone, pas la
baisse de cadence.

Référence validée : `PORTL1A`, cycle natif `[0..5]`, timeline
`[0,6,1,7,2,8,3,9,4,10,5,11]`, 0,4 s. Petite irrégularité de couture acceptée. Ne pas appliquer
cette tolérance automatiquement à une autre ressource.

## Variables de travail

Définir une fois :

```powershell
$SourceRun = 'animations/runs/<run-spatial-v1>' # voie source-run seulement
$BasePack = '<pack-runtime-complet-actif-avant-v2>'
$Resrefs = @('<RESREF1>', '<RESREF2>')
$Run = 'animations/runs/<nouveau-run>-apo8-x4-30fps-v2'
$PlanFile = 'temp/<nouveau-run>-30fps-v2-plan.json'
$resrefArgs = foreach ($resref in $Resrefs) { '--resref'; $resref }
$collapseArgs = @('--collapse-uniform-duplicate-holds') # seulement après diagnostic des maintiens
```

Règles :

- normaliser les resrefs en majuscules, 1 à 8 caractères ASCII alphanumériques ;
- exiger un nouveau `$Run` ; ne jamais viser un run V1 ou un résultat V2 différent ;
- avec `--source-run`, tous les resrefs du build doivent exister dans le même `$SourceRun` ;
- avec `--base-runtime-only`, ne fournir aucun `$SourceRun` : refuser une cible incomplète,
  déjà `TimedTimeline`, ou dont les ancres ne partagent pas largeur, hauteur et offsets ;
- ne pas choisir un pack partiel. En cas de doute, comparer son `registry_sha256` au registre actif
  et laisser le préflight d'installation vérifier tous les assets de base ; ne jamais forcer une
  divergence.

## Gate 0 — plan en lecture seule

```powershell
python pipeline/scripts/run_animation_upscale_30fps_v2.py plan `
  --source-run $SourceRun `
  --base-pack $BasePack `
  @resrefArgs `
  > $PlanFile

# Variante : asset déjà traité x4/15 fps, ancres homogènes dans $BasePack
python pipeline/scripts/run_animation_upscale_30fps_v2.py plan `
  --base-runtime-only `
  --base-pack $BasePack `
  @resrefArgs `
  > $PlanFile

$Plan = Get-Content -Raw $PlanFile | ConvertFrom-Json
$Plan.plan_sha256
```

Contrôler pour chaque cible/cycle :

```text
output_frame_count = base_frame_count + somme(native_slots)
timeline_phases    = 2 * native_slots
duration_seconds   = native_slots / 15
added_raw_bytes    = somme(width_x4 * height_x4 * 4 des phases impaires)
```

Le plan doit référencer le `$SourceRun`, le `$BasePack`, les resrefs et `apo-8` attendus. Si la
demande courante autorise déjà explicitement le build, utiliser son hash sans demander une seconde
confirmation. Sinon présenter le résumé exact et attendre le GO. Ne jamais inventer le hash.

Si le preview V2 standard conserve des maintiens doubles au lieu de produire un mouvement visible,
replanifier avec `$collapseArgs`. Exiger dans chaque cycle :

```text
timing_strategy = collapse-uniform-duplicate-holds
interpolation_input_frame_indices = poses uniques
hold_slots = H
phases_per_transition = 2*H
timeline_phases = native_slots*2
duration_seconds = native_slots/15
```

Le filtre Topaz reçoit les poses uniques à `15/H` fps et sort à 30 fps. Chaque phase intermédiaire
garde crop et alpha exacts de sa pose gauche. Ce mode ne corrige pas un défaut visuel de l'asset.

## Gate 1 — build immuable

```powershell
python pipeline/scripts/run_animation_upscale_30fps_v2.py build `
  --source-run $SourceRun `
  --base-pack $BasePack `
  @resrefArgs `
  --output $Run `
  --approve-plan-sha256 $Plan.plan_sha256

# Variante runtime-only : remplacer --source-run $SourceRun par --base-runtime-only.
# Variante maintiens uniformes : ajouter $collapseArgs au plan et au build, sans changer le reste.
```

Reprise après interruption : relancer la commande strictement identique avec `--resume`.

- `<Run>.partial` présent : seuls les cycles terminés et hash-validés sont réutilisés.
- `$Run` final présent : `--resume` revalide sans relancer Topaz.
- Plan ou paramètres différents : créer un nouveau run ; ne pas nettoyer ou réutiliser l'ancien.
- Ne jamais modifier manuellement `request.json`, `cycle.json`, `manifest.json`, le registre ou un
  asset pour franchir une validation.

Si un patch historique mono-ressource `TimedTimeline` est déjà actif, le promouvoir d'abord en pack
V2 complet, puis employer ce nouveau pack comme `$BasePack` :

```powershell
python pipeline/scripts/run_animation_upscale_30fps_v2.py adopt-clock-patch `
  --base-pack <pack-v1-compatible> `
  --clock-patch <patch-runtime-historique> `
  --output <pack-v2-complet>
```

Cette commande est hors jeu, ne produit aucun asset interpolé et exige la compatibilité exacte du
patch avec le pack V1. Ne pas l'utiliser pour remplacer, réparer ou modifier un patch accepté.

Sorties à conserver :

```text
$Run/manifest.json
$Run/work/<RESREF>/cycle_NNN/cycle.json
$Run/work/<RESREF>/cycle_NNN/review-30fps-exact.mp4
$Run/work/<RESREF>/cycle_NNN/review-30fps-loop-4s.mp4
$Run/03_runtime_pack/manifest.json
$Run/03_runtime_pack/AreaAnimations-X4.registry
$Run/03_runtime_pack/AAX4-*.rgba
```

## Gate 2 — QA vidéo utilisateur

Afficher `review-30fps-loop-4s.mp4` pour chaque resref et chaque cycle. Utiliser la review exacte
pour diagnostiquer la couture.

Demander une décision explicite sur : forme, crop, alpha, placement, vitesse, dernière -> première
phase, flash/halo/déformation/saut. L'agent ne peut pas auto-approuver.

Si refus :

- ne pas exécuter `approve` ;
- ne pas installer ;
- conserver le run refusé ;
- créer un autre run à partir d'un nouveau plan si un nouvel essai est demandé.

Après validation explicite de toutes les reviews :

```powershell
$RunHash = (Get-FileHash -Algorithm SHA256 "$Run/manifest.json").Hash.ToLowerInvariant()
python pipeline/scripts/run_animation_upscale_30fps_v2.py approve `
  --output $Run `
  --approve-run-manifest-sha256 $RunHash `
  @resrefArgs
```

Résultat requis : `$Run/qa-approval.json`, schéma
`bg2-upscale-area-animation-30fps-approval-v2`, couvrant exactement `$Resrefs`. La commande ne
modifie pas le run ni le pack approuvés.

## Gate 3 — validation et préflight sans écriture

```powershell
python pipeline/scripts/run_animation_upscale_30fps_v2.py validate --output $Run

.\pipeline\scripts\Install-AreaAnimations-30fps-V2.ps1 `
  -RunRoot $Run `
  -VerifyOnly
```

Le préflight doit réussir avant toute installation. Il contrôle :

- processus BG2EE/InfinityLoader absents ;
- run, pack et approbation cohérents par SHA-256 ;
- DLL v2 présente ;
- registre actif identique au registre du pack de base ;
- chaque asset de base actif identique au manifeste ;
- chaque nouvelle phase source valide et absente du jeu.

En cas d'échec, arrêter. Ne pas copier à la main, supprimer une phase, remplacer le registre ou
contourner le contrôle.

## Gate 4 — installation

Ne franchir ce gate que si la demande utilisateur autorise l'installation. Jeu et
`InfinityLoader` fermés :

```powershell
.\pipeline\scripts\Install-AreaAnimations-30fps-V2.ps1 -RunRoot $Run
```

Conserver le chemin `30fps-v2-backup-*` affiché. L'installateur sauvegarde DLL, INI et registre,
installe la DLL/registre v2 et uniquement `new_assets`, force une clé unique
`EnableAreaAnimationX4=true` sous `[Shaders]`, puis contrôle les hashes. Il ne lance pas le jeu.

## Gate 5 — QA ingame utilisateur

L'agent ne lance pas le jeu. Demander à l'utilisateur de vérifier :

1. vitesse et boucle pendant plusieurs cycles ;
2. pause puis reprise sans saut/retour ;
3. sortie puis retour dans le champ ;
4. changement de zone puis retour ;
5. crop, taille, ancrage, alpha, teinte et occlusion.

Attendre la fermeture du jeu avant toute modification.

Si la QA est refusée, restaurer uniquement après autorisation :

```powershell
.\pipeline\scripts\Restore-AreaAnimations-30fps-V2.ps1 `
  -BackupPath <30fps-v2-backup> `
  -VerifyOnly

.\pipeline\scripts\Restore-AreaAnimations-30fps-V2.ps1 `
  -BackupPath <30fps-v2-backup>
```

La restauration refuse un état installé modifié. Ne pas forcer : signaler les hashes divergents.

## Conditions de fin

Hors ligne terminé uniquement si :

- `build` et `validate` réussissent ;
- toutes les reviews sont explicitement acceptées ;
- `qa-approval.json` correspond aux hashes actuels ;
- l'installation `-VerifyOnly` réussit.

Ingame terminé uniquement si :

- installation réversible réussie ;
- chemin de backup consigné ;
- QA ingame explicitement acceptée.

Ne pas mettre à jour le statut humain du CSV avant la QA ingame. Ne jamais supprimer le run V1, le
pack de base, un run V2 refusé ou un backup.
