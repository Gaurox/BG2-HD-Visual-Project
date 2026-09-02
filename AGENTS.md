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
| Animations : inventaire et QA ingame | [`animations/index/`](animations/index/), `qa-decisions/` immuable et `selections/` courant |
| Animations : sélection release | [`animation-release-candidates.json`](releases/BG2-HD-Upscale/manifests/animation-release-candidates.json) |
| Sprites : inventaire et éligibilité | [`sprite/index/`](sprite/index/) |
| Sprites : génération et test actifs | `current-generation.json` et `active-test.json` canoniques |
| UI, vidéos et autres graphismes | index listés dans [`docs/GRAPHICS_INVENTORY.md`](docs/GRAPHICS_INVENTORY.md) |
| Portraits | `portraits/inventaire_portraits.csv` ; vues d'usage recrutables/rencontres séparées |
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

Ces fichiers peuvent être supprimés et régénérés, après choix explicite, avec
`workspace.py refresh --scope all --run`.

## Modifier correctement

- Modifier l'autorité du domaine, jamais sa projection.
- Conserver asset ids, recette, entrées, sorties, provenance, résultat et hashes utiles.
- Ne jamais réécrire un run, build, approbation ou artefact scellé : créer une version.
- Garder toute sélection courante hors du run ; adapter le legacy sans le réécrire.
- Après « validé ingame », utiliser `animation_workflow.py finalize`; ne pas éditer séparément le CSV,
  la sélection et la preuve. Un `qa-approval.json` dans un run reste une revue technique, pas la
  décision ingame courante.
- Utiliser les clés `config://...` de [`config/workspace-paths.json`](config/workspace-paths.json),
  jamais un nouveau chemin absolu personnel.
- Préserver les changements utilisateur hors périmètre.

## Contrôles

Avant une intervention, contrôler seulement l'état Git :

```powershell
git status --short
```

Après l'intervention, ne lancer aucun test automatiquement. Demander explicitement à l'utilisateur
de choisir une seule option :

- tests ciblés pour la tâche réalisée ;
- tous les tests ;
- aucun test.

Préparer la proposition sans exécution :

```powershell
python pipeline/scripts/test_changed.py --targeted
python pipeline/scripts/workspace.py refresh --changed
```

Demander séparément le choix de reconstruction :

- reconstructions ciblées proposées par le plan ;
- toutes les projections ;
- aucune reconstruction.

Les deux commandes sont plan-only par défaut. Toute exécution exige `--run`. Un choix ciblé utilise
`test_changed.py --targeted --run` et les `workspace.py --scope ... --run` exacts ; il ne peut jamais
devenir complet. `--verify-determinism` double les reconstructions et exige un accord explicite.
Quand l'utilisateur demande d'aller au bout malgré les erreurs, ajouter `--keep-going`; le code final
reste non nul et toutes les erreurs sont récapitulées.
Voir [`docs/TEST_SELECTION.md`](docs/TEST_SELECTION.md) et
[`docs/WORKSPACE_INTEGRITY.md`](docs/WORKSPACE_INTEGRITY.md).

Ne pas exécuter de `workspace.py ... --run` comme contrôle routinier. Régénérer
les projections seulement si la tâche les livre, si un consommateur en a besoin, avant une gate
release/CI, ou sur demande explicite. Les mises à jour peuvent être regroupées ; les autorités
métier restent valides entre-temps.

Ajouter les tests indiqués par le README du domaine dans [`pipeline/tests/`](pipeline/tests/).
Pour une modification documentaire, ne pas lancer SeedVR, Topaz, un build de contenu ou un
packaging.

Audit et plan de réduction des délais :
[`docs/WORKFLOW_PERFORMANCE_AUDIT.md`](docs/WORKFLOW_PERFORMANCE_AUDIT.md).

## Règles critiques

- Fermer le jeu et InfinityLoader avant installation ou restauration.
- Ne jamais déduire une QA ou une release ; `pending-qa` n'est pas validé.
- Ne pas reconstruire payload, staging, `content.json` ou archive sans accord explicite.
- Une mise à jour métier et une intégration release sont deux décisions distinctes.
- Après une tâche produisant du `validated-installed`, demander explicitement l'intégration au
  manifeste de release ; sinon indiquer qu'elle n'est pas nécessaire.
