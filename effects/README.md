# Effets BG2EE

## Portée et autorités

Un asset de production est un BAM visuel : `effects:bam:<RESREF>`. Les VVC/VEF restent des contrôleurs et consommateurs ; un BAM partagé n'est traité qu'une fois.

| Fichier | Rôle | Édition |
|---|---|---|
| `index/manifest.json`, `resources.csv`, `dependencies.csv` | inventaire VVC/VEF et graphe de dépendances | généré |
| `index/bam-assets.csv` | inventaire unifié des BAM d'effet, provenance, consommateurs et source | généré |
| `index/processing.csv` | états spatiaux/temporels, sélection, QA, installation, release | autorité métier |

`bam-assets.csv` inclut les BAM directement référencés par VVC/VEF, les BAM référencés directement par un PRO et les BAM des BIF dédiées effets. Les BAM partagés avec les projectiles restent des assets `effects`; leurs consommateurs PRO sont listés, sans duplication sous `projectiles/`. `origin=projectile-member` désigne un BAM connu uniquement par un PRO.

## Layout

```text
effects/
  source/{vvc,vef}/                 # contrôleurs stock extraits
  ressources/<RESREF>/
    source.bam                       # BAM stock unique, ignoré Git
    runs/<run-id>/
      run.json                       # docs/workspace-run.schema.json
      00-frames-x1/                  # optionnel
      01-spatial-x4/                 # run spatial
      02-interpolation/              # seulement dans un run dérivé
```

Créer un run directement sous le BAM concerné. Aucun nouveau run sous `effects/runs/`. Un run d'interpolation est distinct, scellé et porte son run spatial parent dans `provenance.parents`. Ne pas créer de répertoires permanents `x4/` ou `interpolation/` hors d'un run. Ne jamais modifier un run scellé.

## Workflow de production

`pipeline/scripts/effect_workflow.py` ne génère pas d'image. Il contrôle l'autorité et les descripteurs scellés ; le producteur écrit les fichiers du run avant son enregistrement.

| Étape | `pipeline.id` imposé | Entrée et lineage requis | Écriture autorité |
|---|---|---|---|
| spatial | `effects.spatial-x4.v1` | une preuve `source-bam` vers `source.bam`, hashée comme `bam-assets.csv` | `spatial_run`, `spatial_state=produced` |
| interpolation | `effects.interpolation-30fps.v1` | parent unique = `spatial_run`; preuve `parent-spatial-output` égale à une sortie parent | `interpolation_run`, `interpolation_state=produced` |

```powershell
# Prépare seulement l'identifiant, sans écrire.
python pipeline/scripts/effect_workflow.py new-run --resref <RESREF> --stage spatial --recipe <recipe>

# Réserve explicitement l'identifiant ; le producteur crée ensuite runs/<run-id>/run.json.
python pipeline/scripts/effect_workflow.py new-run --resref <RESREF> --stage spatial --recipe <recipe> --run

# Vérifie hash, tailles, source et lineage. Sans --run, aucune autorité n'est modifiée.
python pipeline/scripts/effect_workflow.py register-run --resref <RESREF> --stage spatial --run-id <run-id>
python pipeline/scripts/effect_workflow.py register-run --resref <RESREF> --stage spatial --run-id <run-id> --run
python pipeline/scripts/effect_workflow.py check --resref <RESREF>
```

Le workflow ne sélectionne aucun run, ne déclare aucune QA, n'installe rien et ne touche pas à la release. Ces axes seront ajoutés après validation du pack/runtime.

## Producteur spatial

`run_effect_spatial.py` crée uniquement un run spatial mono-BAM ; il ne choisit aucun asset par défaut. Le workflow SeedVR doit être un fichier du workspace et reste hashé dans `recipe.json`.

```powershell
# Plan sans écriture ni appel ComfyUI.
python pipeline/scripts/run_effect_spatial.py --resref <RESREF> --workflow <workflow.json> --recipe-id <recipe>

# Production explicite, puis enregistrement distinct après revue du run.
python pipeline/scripts/run_effect_spatial.py --resref <RESREF> --workflow <workflow.json> --recipe-id <recipe> --run
python pipeline/scripts/effect_workflow.py register-run --resref <RESREF> --stage spatial --run-id <run-id>
```

Le producteur écrit `00-frames-x1/`, `01-spatial-x4/`, `recipe.json` et `run.json` sous le run réservé. Il préserve le BAM source, conserve l'alpha source, refuse un run scellé et laisse `processing.csv` inchangé.

## Initialisation / extraction

```powershell
python pipeline/scripts/workspace.py refresh --scope graphics --run
python pipeline/scripts/build_graphics_inventory.py --extract-effects --run
python pipeline/scripts/sync_effect_processing.py
python pipeline/scripts/sync_effect_processing.py --run
```

La première commande régénère l'inventaire. La seconde extrait seulement les contrôleurs et BAM d'effets. La dernière initialise ou complète `processing.csv` sans réécrire une ligne existante.

Deux BAM stock absents restent `blocked`; ne pas créer de `source.bam` fictif.

## Suivi

`processing.csv` contient une ligne par `asset_key` de `bam-assets.csv` :

```text
asset_key,asset_directory,spatial_run,spatial_state,interpolation_run,
interpolation_state,selected_run,qa_state,qa_evidence,installation_state,
installation_receipt,release_state,release_candidate,notes
```

États de production : valeurs du contrat commun (`not-started`, `in-progress`, `produced`, `verified`, `rejected`, `blocked`, `not-applicable`). `qa=passed` exige un `selected_run` et une preuve. Installation et release restent des décisions séparées.

## Gate runtime

Il n'existe pas encore de chemin VVC/VEF/PRO xN dans le moteur. Avant tout run x4, démontrer sur un effet représentatif : ancrage logique, cycle/timing, alpha, palette, partage multi-contrôleur, consommateur projectile et fallback natif. L'interpolation reste hors périmètre tant que ce gate spatial n'est pas validé.
