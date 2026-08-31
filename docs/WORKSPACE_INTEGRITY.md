# Intégrité du workspace

## Commandes

```powershell
python pipeline/scripts/workspace.py check
python pipeline/scripts/workspace.py refresh
python pipeline/scripts/test_changed.py --changed
python pipeline/scripts/test_changed.py --full
```

`check` est sans écriture. `refresh` régénère les inventaires complémentaires, le registre global,
la couverture, les anomalies, l'index des runs et le rapport d'intégrité.
Le sélecteur exécute `workspace.py check --after-full-tests` en mono-passe après la suite Python
complète, car les tests ont déjà prouvé le déterminisme des trois générateurs.

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

Ces manifestes sont des preuves de migration. Ils ne deviennent pas des autorités métier.
