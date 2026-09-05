# Intégrité du workspace

## Choix obligatoire

```powershell
python pipeline/scripts/workspace.py refresh --changed
```

La commande affiche seulement les scopes affectés par les changements Git. Après la tâche, demander
séparément :

1. reconstructions ciblées proposées ;
2. toutes les projections ;
3. aucune reconstruction.

Sans `--run`, `refresh` et `check` ne font qu'afficher le plan. Exécutions possibles après choix :

```powershell
# Exemple ciblé ; reprendre exactement les scopes proposés
python pipeline/scripts/workspace.py refresh --scope registry --scope integrity --run

# Toutes les projections
python pipeline/scripts/workspace.py refresh --scope all --run

# Continuer les scopes indépendants et récapituler les échecs
python pipeline/scripts/workspace.py refresh --scope all --run --keep-going
```

| Scope | Sorties |
|---|---|
| `graphics` | inventaires graphiques complémentaires |
| `registry` | registre, CSV, couverture et anomalies |
| `integrity` | index des runs et rapport d'intégrité physique |

`refresh` écrit les projections ; `check` les compare sans écriture. Les stages sont mono-passe par
défaut. `--verify-determinism` les exécute deux fois et exige un accord explicite ou une gate CI.
Ne pas reconstruire après chaque tâche : regrouper les autorités ou attendre le livrable/gate.
`--keep-going` poursuit les scopes indépendants, mais retourne toujours un code non nul si l'un
d'eux échoue.

Les tests suivent le choix indépendant décrit dans [`TEST_SELECTION.md`](TEST_SELECTION.md). La
suite complète appelle tous les scopes en `check` mono-passe après ses tests.

## Sorties générées

| Fichier | Contenu |
|---|---|
| `asset-tracking/registry.json`, `.csv` | assets connus et autorité associée |
| `asset-tracking/coverage.json` | couverture par domaine et état |
| `asset-tracking/anomalies.json` | états impossibles ou incomplets |
| `asset-tracking/runs.json`, `.csv` | runs physiques et rattachement connu |
| `asset-tracking/workspace-integrity.json` | erreurs, avertissements et informations de contrôle |

Toutes ces sorties sont jetables. Les pipelines métier lisent les autorités listées dans
[`ASSET_TRACKING_CONTRACT.md`](ASSET_TRACKING_CONTRACT.md), jamais ces projections.

## Nouveau run

Utiliser le layout natif du domaine. À défaut, suivre
[`workspace-run.schema.json`](workspace-run.schema.json) :

- identifiant stable et `asset_ids` explicites ;
- recette/pipeline et snapshot immuable de tout job mutable ;
- entrées, sorties et preuves hashées utiles ;
- résultat technique séparé de la QA, de l'installation et de la release ;
- sélection courante conservée dans une autorité externe au run.

Un run existant n'est jamais réécrit pour adopter le schéma courant.

## Portabilité et legacy

Les chemins machine passent par [`config/workspace-paths.json`](../config/workspace-paths.json), une
variable d'environnement, ou le fichier local ignoré `workspace-paths.local.json`. Les exceptions
historiques sont bornées par `config/historical-absolute-paths.json`.

Les compatibilités et déplacements historiques sont déclarés, non devinés :

| Sujet | Registre |
|---|---|
| Runs et preuves d'animation déplacés | `animations/index/path-migrations.json`, `qa-evidence-migrations.json` |
| Runs sprite déplacés | `sprite/index/path-migrations.json` |
| Nettoyages et archives physiques | `docs/workspace-cleanup-manifest*.json` et `docs/workspace-archive-manifest*.json` |
| Retours post-nettoyage depuis une archive | `docs/workspace-restoration-manifest.json`, avec manifeste cible et hash exact |

Ces manifestes sont des preuves de migration. Ils ne deviennent pas des autorités métier.
