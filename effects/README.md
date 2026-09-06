# Effets BG2EE

## Portée et autorités

Un asset de production est un BAM visuel : `effects:bam:<RESREF>`. Les VVC/VEF restent des contrôleurs et consommateurs ; un BAM partagé n'est traité qu'une fois.

| Fichier | Rôle | Édition |
|---|---|---|
| `index/manifest.json`, `resources.csv`, `dependencies.csv` | inventaire VVC/VEF et graphe de dépendances | généré |
| `index/bam-assets.csv` | inventaire unifié des BAM d'effet, provenance, consommateurs et source | généré |
| `index/processing.csv` | états spatiaux/temporels, sélection, QA, installation, release | autorité métier |

`bam-assets.csv` inclut les BAM directement référencés par VVC/VEF et les BAM des BIF dédiées effets. Les BAM partagés avec les projectiles restent des assets `effects`; leurs consommateurs PRO sont listés, sans duplication sous `projectiles/`.

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
