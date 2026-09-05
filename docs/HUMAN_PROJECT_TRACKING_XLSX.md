# Suivi humain global XLSX

Projection jetable du registre global. Le classeur et ses métriques ne sont pas des autorités
métier et ne reçoivent aucune saisie manuelle.

## Entrées

| Entrée | Usage |
|---|---|
| `asset-tracking/registry.json` | lignes par asset, états, provenance, sélections, sources |
| `asset-tracking/coverage.json` | cardinalités, périmètres non inventoriés, contrôle des agrégats |
| `asset-tracking/anomalies.json` | synthèse des lacunes et incohérences |
| `docs/asset-tracking-record.schema.json` | domaines et états autorisés |

Pour les vidéos, le registre adapte `video/index/processing.csv` avant génération du classeur.

Les sources canoniques exactes restent celles listées dans `registry.json.inputs` et dans
`canonical_source` de chaque asset.

## Sorties

| Sortie | Rôle |
|---|---|
| `outputs/bg2ee-hd-human-tracking/BG2EE-HD-suivi-global.xlsx` | vue humaine reconstruisible |
| `asset-tracking/dashboard-metrics.json` | métriques structurées réutilisables ultérieurement par le site |

## Indicateurs

| Indicateur | Numérateur | Dénominateur |
|---|---|---|
| Produits | `production ∈ {produced, verified}` | `production != not-applicable` |
| QA validés | `qa = passed` | `qa != not-applicable` |
| Release éligible+ | `release ∈ {eligible, approved, integrated, published}` | `release != not-applicable` |

Un dénominateur nul produit `N/A`. Les états `ready`, `in-progress`, `pending`, `failed`, `blocked`,
`ineligible`, `unknown`, `not-assessed` et `not-evaluated` restent distincts et ne sont pas promus.
Pour les portraits, les axes hors source restent `N/A` tant qu'aucune autorité de production, QA,
installation ou release n'existe.

## Génération et contrôle

Fermer le classeur dans Excel puis double-cliquer sur :

```text
outputs/bg2ee-hd-human-tracking/Mettre-a-jour-suivi.cmd
```

Le lanceur reconstruit d'abord `asset-tracking/registry.*`, `coverage.json` et `anomalies.json`
depuis les autorités du workspace, puis régénère et contrôle le XLSX et
`asset-tracking/dashboard-metrics.json`. Il ne reconstruit aucun asset graphique, pack ou archive.

Équivalent en ligne de commande :

Exécuter avec le runtime Node fourni par le workspace et ses modules `@oai/artifact-tool` et
`jszip` disponibles :

```powershell
node pipeline/scripts/generate_human_tracking_xlsx.mjs --verify-determinism
node pipeline/scripts/generate_human_tracking_xlsx.mjs --check
```

Le générateur refuse les empreintes divergentes entre registre, couverture et anomalies, les ids
dupliqués, les domaines/états hors contrat et les écarts de cardinalité. `--check` compare chaque
liste d'ids du XLSX au registre courant et contrôle les métriques structurées.
