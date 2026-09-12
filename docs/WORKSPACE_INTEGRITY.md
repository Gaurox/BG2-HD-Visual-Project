# Intégrité du workspace — index de commandes

Les projections d'intégrité sont facultatives et régénérables. Elles ne sont pas nécessaires après
une correction locale et leur fraîcheur ne conditionne pas les autorités métier.

## Commandes disponibles

Afficher un plan sans écrire :

```powershell
python pipeline/scripts/workspace.py refresh --changed
```

Produire une projection lorsqu'un consommateur la demande :

```powershell
python pipeline/scripts/workspace.py refresh --scope graphics --run
python pipeline/scripts/workspace.py refresh --scope registry --run
python pipeline/scripts/workspace.py refresh --scope integrity --run
python pipeline/scripts/workspace.py refresh --scope all --run
```

`--keep-going` poursuit les scopes indépendants. `--verify-determinism` effectue une seconde passe et
coûte environ deux fois plus cher ; il n'a d'intérêt que pour un contrôle explicite de déterminisme.

## Sorties

| Scope | Sorties principales |
|---|---|
| `graphics` | inventaires graphiques complémentaires |
| `registry` | `registry.json/.csv`, couverture et anomalies |
| `integrity` | index des runs et rapport d'intégrité physique |

Ces sorties sont jetables. Les pipelines métier lisent leurs autorités, pas ces projections.

## Repères facultatifs pour un nouveau run

- identité et assets concernés ;
- recette et entrées utiles ;
- sorties et hashes nécessaires à la reproductibilité ;
- résultat technique séparé d'une éventuelle QA, installation ou release.

Un format détaillé est disponible dans `workspace-run.schema.json` lorsqu'un consommateur l'exige.
Les chemins machine peuvent utiliser `config/workspace-paths.json`.
