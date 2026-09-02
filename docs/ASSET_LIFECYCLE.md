# Cycle de vie et rangement des assets

Convention progressive pour les nouveaux travaux. Aucun run historique n'est déplacé ni réécrit.
Les autorités métier restent celles d'[`ASSET_TRACKING_CONTRACT.md`](ASSET_TRACKING_CONTRACT.md).

## Invariants

- Créer le run directement dans le layout courant du domaine.
- Ne jamais déplacer, renommer ou modifier un run scellé.
- Une correction produit un nouveau run et référence ses parents ; elle ne remplace pas leurs octets.
- Conserver un essai refusé avec son manifeste et son résultat. Seule une sélection explicite rend un
  run courant.
- Garder la sélection hors du run : `areas.csv`, registre animation, pointeurs sprite ou
  `video/index/processing.csv` selon le domaine.
- QA, installation et release sont trois décisions distinctes.
- Les médias et runs, y compris leurs manifestes internes, sont ignorés par Git. Les catalogues,
  décisions et manifestes d'autorité placés hors des runs constituent le changement committable.

## Checkpoints communs

| Étape | Écriture autoritaire |
|---|---|
| Essai | nouveau run immuable ; aucune promotion |
| Correction | nouveau run avec parents/hashes ; essais précédents conservés |
| Revue technique | preuve interne au run ; QA ingame inchangée |
| Essai jeu | installation/restauration transactionnelle ; QA encore `pending` |
| Décision ingame | preuve immuable + sélection courante + autorité métier, en une transaction |
| Release | accord distinct ; candidat exact + contenu/composants/TP2 ciblés |
| Package | accord distinct ; staging, archive et gates globales |

Après un checkpoint, les tests et les projections restent deux choix indépendants. Un commit porte
les fichiers de contrôle affichés par l'outil ; il ne tente pas d'ajouter les médias ignorés.

Les transactions animation partagent `.tmp/workflow-locks/animation-authority.lock` et journalisent
leurs sauvegardes sous `.tmp/workflow-transactions/`. Une relance `--run` restaure d'abord une
transaction interrompue. Le fichier de verrou persiste normalement ; seul le verrou système détenu
par le processus fait autorité et il est libéré automatiquement si le processus s'arrête.
Les générateurs, validations, staging et builds release tiennent le même verrou jusqu'à leur fin et
refusent tout journal interrompu ; ne jamais supprimer manuellement un journal actif. Une
synchronisation de miroirs interrompue laisse
`releases/BG2-HD-Upscale/bg2hd/manifests/.package-metadata-sync.partial` : relancer uniquement
`Sync-BG2HD-PackageMetadata.ps1`, qui recopie et revalide l'ensemble avant de retirer le marqueur.

## Layouts courants

| Domaine | Sources et runs | Sélection |
|---|---|---|
| Maps | `maps/<AREA>/rendus-x1/`, `maps/<AREA>/runs/<run-id>/` | `areas.csv` |
| Animation mono-resref | `animations/ressources/<RESREF>/`, `animations/ressources/<RESREF>/runs/<run-id>/` | `animations/index/` |
| Animation batch | `animations/batches/<run-id>/` avec cibles explicites dans le manifeste | `animations/index/` |
| Pack animation de zone | `animations/packs-par-zone/<pack-id>/<AREA>/` | manifeste de candidats release |
| Sprite | `sprite/families/.../<asset>/{source,jobs,runs,research}/` | pointeurs du catalogue |
| Vidéo | `video/<asset>/<source>.wbm`, `video/<asset>/runs/<run-id>/` | `video/index/processing.csv` |

Interface, portraits, icônes, effets et projectiles conservent leurs index actuels. Créer un
workspace d'asset seulement au premier traitement ; ne pas dupliquer préventivement les extractions.

`animations/runs/<run-id>/` reste un layout legacy accepté pour la reprise et la lecture. Aucun
nouveau run n'y est créé par défaut.

### Réservation des runs animation

`animation_workflow.py new-run` sans `--run` est strictement en lecture seule. Avec `--run`, il crée
atomiquement `animations/ressources/<RESREF>/.<run-id>.reservation.json` sous le verrou animation.
Le marqueur contient resref, étape, recette, destination et date ; le dossier feuille reste absent.

- Le producteur utilise la destination retournée et ne modifie pas le marqueur.
- Un run ou `.partial` homonyme, y compris legacy, bloque la réservation.
- `finalize --run` valide le run et le marqueur exact, puis consomme le marqueur avant la transaction
  QA ; le run physique protège alors définitivement l'identifiant.
- Une réservation interrompue reste volontairement bloquante. Ne la supprimer qu'après annulation
  explicite et vérification de l'absence du run et de son `.partial`.

## Nouveaux runs animation

Run spatial mono-resref :

```powershell
python pipeline/scripts/run_animation_upscale.py `
  --resref AM0602J --run am0602j-seedvr7b-lab-x4-v1 --scale 4 --plan

python pipeline/scripts/run_animation_upscale.py `
  --resref AM0602J --run am0602j-seedvr7b-lab-x4-v1 --scale 4
```

Le dossier proposé est
`animations/ressources/AM0602J/runs/am0602j-seedvr7b-lab-x4-v1/`.

Run spatial multi-resrefs :

```powershell
python pipeline/scripts/run_animation_upscale.py `
  --area AR0602 --run ar0602-seedvr7b-lab-x4-v1 --scale 4 --plan
```

Le dossier proposé est `animations/batches/ar0602-seedvr7b-lab-x4-v1/`. Le nombre réel de resrefs
résolus décide entre mono-resref et batch.

Run temporel 30 fps :

```powershell
python pipeline/scripts/run_animation_upscale_30fps_v2.py plan `
  --source-run am0602j-seedvr7b-lab-x4-v1 `
  --base-pack <pack-v1> --resref AM0602J `
  --run am0602j-apollo8-30fps-v1

python pipeline/scripts/run_animation_upscale_30fps_v2.py build `
  --source-run am0602j-seedvr7b-lab-x4-v1 `
  --base-pack <pack-v1> --resref AM0602J `
  --run am0602j-apollo8-30fps-v1 `
  --approve-plan-sha256 <sha256>
```

`--source-run` accepte un chemin explicite ou un identifiant recherché dans les layouts courant et
legacy. `build --run` applique le nouveau layout. `build --output <chemin>` conserve le routage
explicite nécessaire aux anciens runs.

Les correcteurs `build_manual_alpha_mask_30fps_v2.py` et
`build_per_frame_spline_alpha_30fps_v2.py` utilisent aussi `--run <run-id>` ;
`build_alpha_feather.py` utilise `--output-run <run-id>` car `--run` désigne encore sa source
legacy. Leurs options `--output` restent réservées aux reprises explicites.

Reprise spatiale legacy explicite :

```powershell
python pipeline/scripts/run_animation_upscale.py `
  --resref <RESREF> --run <run-id> --runs-root animations/runs --resume
```

Sans `--runs-root`, un run existant portant cet identifiant est repris automatiquement s'il existe
à un seul emplacement compatible. Plusieurs emplacements homonymes provoquent un refus.

## Nommage

Utiliser un identifiant simple et stable : `<scope>-<pipeline>-<correctif>-vN`. ASCII, lettres,
chiffres, points, tirets et underscores uniquement. L'identifiant décrit la recette ; la QA et la
release restent dans leurs autorités et ne figurent pas dans le nom.
