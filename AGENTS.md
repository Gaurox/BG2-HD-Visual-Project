# Reprise agent IA — BG2 Upscale

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

Point d'entrée opérationnel. Les fichiers générés décrivent l'état ; ils ne le décident pas.

## Lecture minimale

1. Lire ce fichier puis [`README.md`](README.md).
2. Lire seulement le README du domaine concerné.
3. Avant toute nouvelle méthode, consulter [`docs/DECISIONS.md`](docs/DECISIONS.md) et
   [`pipeline/PROBLEMES_A_RESOUDRE.md`](pipeline/PROBLEMES_A_RESOUDRE.md).
4. Pour un format BG2EE, partir de
   [`BG2EE_Documentation_Modders_FR/INDEX.md`](BG2EE_Documentation_Modders_FR/INDEX.md), puis ouvrir
   uniquement la référence nécessaire.

## Sources de vérité

| Périmètre | Autorité canonique |
|---|---|
| Cartes : état, run et build retenus | [`areas.csv`](areas.csv) |
| Animations : inventaire et QA | [`animations/index/`](animations/index/) et `qa-approval.json` immuable du run exact |
| Animations : sélection release | [`animation-release-candidates.json`](releases/BG2-HD-Upscale/manifests/animation-release-candidates.json) |
| Sprites : inventaire et éligibilité | [`sprite/index/`](sprite/index/) |
| Sprites : génération et test actifs | `current-generation.json` et `active-test.json` canoniques |
| UI, vidéos et autres graphismes | index listés dans [`docs/GRAPHICS_INVENTORY.md`](docs/GRAPHICS_INVENTORY.md) |
| Portraits | CSV d'inventaire de chaque sous-domaine |
| Moteur | `src/iee/game/build_manifest.*` et `docs/validation/` sous [`engine/`](engine/InfinityEngine-Enhancer/source-patchee/) |
| Release | [`release.json`](releases/BG2-HD-Upscale/manifests/release.json) ; `content.json` est généré |

Le contrat transversal est [`docs/ASSET_TRACKING_CONTRACT.md`](docs/ASSET_TRACKING_CONTRACT.md).
Il sépare toujours cinq axes : source, production, QA, installation et release. Aucun axe ne prouve
automatiquement le suivant.

## Projections générées

| Sortie | Usage | Interdiction |
|---|---|---|
| `asset-tracking/registry.json` et `.csv` | vue globale des assets et lien vers leur autorité | édition manuelle ou usage comme autorité métier |
| `coverage.json`, `anomalies.json` | couverture et incohérences | promotion automatique d'un état |
| `workspace-integrity.json` | audit disque ↔ autorités ↔ registre ↔ runs | masquer un avertissement par supposition |
| `runs.json`, `runs.csv` | index jetable des runs physiques | sélectionner un run depuis cet index |

Ces fichiers peuvent être supprimés et régénérés avec `workspace.py refresh`.

## Modifier correctement

- Modifier l'autorité du domaine, jamais sa projection.
- Conserver asset ids, recette, entrées, sorties, provenance, résultat et hashes utiles.
- Ne jamais réécrire un run, build, approbation ou artefact scellé : créer une version.
- Garder toute sélection courante hors du run ; adapter le legacy sans le réécrire.
- Utiliser les clés `config://...` de [`config/workspace-paths.json`](config/workspace-paths.json),
  jamais un nouveau chemin absolu personnel.
- Préserver les changements utilisateur hors périmètre.

## Contrôles

Avant et après une intervention :

```powershell
git status --short
python pipeline/scripts/workspace.py check
```

Après une modification d'autorité ou d'inventaire :

```powershell
python pipeline/scripts/workspace.py refresh
python -m unittest discover -s pipeline/tests -p "test_*.py"
```

Ajouter les tests indiqués par le README du domaine. Pour une modification documentaire, ne pas
lancer SeedVR, Topaz, un build de contenu ou un packaging.

## Règles critiques

- Fermer le jeu et InfinityLoader avant installation ou restauration.
- Ne jamais déduire une QA ou une release ; `pending-qa` n'est pas validé.
- Ne pas reconstruire payload, staging, `content.json` ou archive sans accord explicite.
- Une mise à jour métier et une intégration release sont deux décisions distinctes.
- Après une tâche produisant du `validated-installed`, demander explicitement l'intégration au
  manifeste de release ; sinon indiquer qu'elle n'est pas nécessaire.
