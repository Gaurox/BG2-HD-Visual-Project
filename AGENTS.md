# Reprise agent IA — BG2 Upscale

Point d'entrée opérationnel pour tout agent. Le registre et les index générés décrivent l'état ;
ils ne décident jamais de cet état.

## Lecture minimale

1. Ce fichier, puis [`README.md`](README.md).
2. Un seul README de domaine : `pipeline/`, `animations/`, `sprite/`, `interface/`,
   `engine/InfinityEngine-Enhancer/source-patchee/` ou `releases/BG2-HD-Upscale/`.
3. Avant une nouvelle méthode : [`docs/DECISIONS.md`](docs/DECISIONS.md) et
   [`pipeline/PROBLEMES_A_RESOUDRE.md`](pipeline/PROBLEMES_A_RESOUDRE.md).
4. Pour un format BG2EE : ouvrir l'[`INDEX.md`](BG2EE_Documentation_Modders_FR/INDEX.md), puis
   uniquement la référence nécessaire. Cette base technique ne remplace pas les autorités projet.

## Arborescence utile

| Chemin | Rôle |
|---|---|
| `maps/`, `animations/`, `sprite/`, `interface/`, `portraits*/`, `video/`, `icons/`, `cursors/`, `effects/`, `projectiles/`, `graphics/` | domaines et autorités locales |
| `pipeline/scripts/` | générateurs, audits, pipelines et installateurs ; garder le dossier plat |
| `pipeline/tests/` | tests Python communs |
| `engine/.../source-patchee/` | moteur, manifests de build et tests natifs |
| `releases/BG2-HD-Upscale/` | sélection release et installateur |
| `asset-tracking/` | projections globales générées, jamais autoritatives |
| `config/` | contrat des chemins machine et exceptions historiques bornées |
| `docs/` | contrats transversaux, décisions et preuves synthétiques |
| `runs/`, `proto/`, `archive/`, `backups/`, `temp/`, `override`, captures, packages | données ou historique ; jamais une source d'état par déduction |

## Sources de vérité

| Domaine / décision | Autorité canonique |
|---|---|
| Maps : état, run et build retenus | `areas.csv` |
| Animations : inventaire | `animations/index/` |
| Animations : QA d'un run | `qa-approval.json` immuable du run exact |
| Animations : candidats de zone | `releases/BG2-HD-Upscale/manifests/animation-release-candidates.json` |
| Sprites : inventaire et éligibilité | `sprite/index/` |
| Sprites : génération / installation courantes | `current-generation.json` et `active-test.json` canoniques |
| Vidéos, HUD/UI, polices, icônes, curseurs, effets, projectiles, compléments | index listés dans [`docs/GRAPHICS_INVENTORY.md`](docs/GRAPHICS_INVENTORY.md) |
| Portraits | CSV d'inventaire de chaque sous-domaine |
| Moteur | `src/iee/game/build_manifest.*` et `docs/validation/` du moteur |
| Release | `manifests/release.json`; `manifests/content.json` est généré |

Le contrat transversal est [`docs/ASSET_TRACKING_CONTRACT.md`](docs/ASSET_TRACKING_CONTRACT.md).
Chaque asset sépare cinq axes :

| Axe | Question |
|---|---|
| source | la ressource native est-elle disponible, extraite et vérifiée ? |
| production | un produit technique existe-t-il et a-t-il passé ses contrôles ? |
| QA | le périmètre exact a-t-il reçu une décision qualité explicite ? |
| installation | quel état est vérifié dans le jeu ou le staging ? |
| release | l'asset est-il éligible, approuvé, intégré ou publié ? |

Une production, installation ou capture ne prouve jamais la QA. Une QA ne prouve jamais la
release.

## Projections générées

| Sortie | Usage | Interdiction |
|---|---|---|
| `asset-tracking/registry.json` | vue machine de tous les assets connus et lien vers leur autorité | édition manuelle ou lecture comme autorité métier |
| `asset-tracking/registry.csv` | vue humaine Excel du même registre | correction manuelle durable |
| `coverage.json`, `anomalies.json` | couverture et projections impossibles | promotion automatique d'un état |
| `workspace-integrity.json` | audit disque ↔ autorités ↔ registre ↔ runs | masquer un avertissement par supposition |
| `runs.json`, `runs.csv` | index jetable des runs physiques et de leur rattachement | sélectionner un run depuis cet index |

Toutes ces sorties peuvent être supprimées et régénérées. Les pipelines métier ne doivent pas les
consommer comme sources de vérité.

## Modifier correctement

### Asset ou statut

1. Identifier l'autorité du domaine et la granularité de l'asset.
2. Rechercher références, candidats, jobs, hashes et chaîne de restauration.
3. Modifier uniquement l'autorité ou produire un nouvel artefact autorisé.
4. Régénérer les projections globales ; ne jamais les corriger directement.
5. Exécuter les contrôles du domaine puis les contrôles globaux.

### Nouveau run

- Utiliser le layout natif du domaine ; sinon appliquer
  [`docs/workspace-run.schema.json`](docs/workspace-run.schema.json).
- Conserver `asset_ids`, run id, recette/pipeline, inputs, outputs, provenance et résultat.
- Hasher les preuves utiles et stocker un snapshot immuable de toute recette/job mutable.
- Garder la sélection dans une autorité externe au run.
- Ne jamais réécrire un run, build, approbation ou artefact scellé : créer une nouvelle version.
- Résoudre l'historique avec les migrations/adaptateurs existants, sans réécriture rétroactive.

## Chemins machine

`config/workspace-paths.json` déclare les clés. Utiliser une variable d'environnement ou copier
`config/workspace-paths.example.json` vers le fichier ignoré
`config/workspace-paths.local.json`. Les nouveaux jobs utilisent `config://...`; aucun nouveau
chemin absolu personnel n'est admis. Les exceptions historiques sont bornées dans
`config/historical-absolute-paths.json` et restent inchangées.

## Contrôles

Avant et après une intervention :

```powershell
git status --short
python pipeline/scripts/workspace.py check
```

Régénération déterministe des inventaires graphiques complémentaires et des projections :

```powershell
python pipeline/scripts/workspace.py refresh
```

Tests communs :

```powershell
python -m unittest discover -s pipeline/tests -p "test_*.py"
```

Ajouter les tests du README de domaine. Ne pas lancer SeedVR, Topaz, un build de contenu complet ou
un packaging pour une modification documentaire.

## Règles absolues

- Préserver les modifications utilisateur hors périmètre.
- Jeu et InfinityLoader fermés avant installation/restauration.
- Ne jamais promouvoir QA ou release par déduction ; `pending-qa` n'est pas validé.
- Ne jamais reconstruire payload, staging, `content.json` ou archive sans accord explicite.
- Une mise à jour d'autorité métier et une intégration release sont deux décisions distinctes.
- Après une tâche produisant du `validated-installed`, demander explicitement l'intégration au
  manifeste de release. Sinon préciser qu'aucune intégration n'est nécessaire.
