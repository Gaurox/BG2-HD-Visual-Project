# Sélection des tests

## Consentement obligatoire

Après toute tâche locale, demander explicitement à l'utilisateur de choisir une option :

1. tests ciblés pour la tâche réalisée ;
2. tous les tests ;
3. aucun test.

Aucun test, build de test, CTest ou gate release ne démarre avant la réponse. Cette règle s'applique
à tous les domaines et remplace toute formulation historique de test « obligatoire » pour le travail
local. Une gate peut rester nécessaire pour déclarer un package/release validé ; si l'utilisateur la
refuse, ne pas revendiquer cette validation.

La CI, les runs planifiés et les commandes explicitement demandées par l'utilisateur ne nécessitent
pas une seconde confirmation interactive.

## Préparer le choix ciblé

```powershell
python pipeline/scripts/test_changed.py --targeted
```

La planification seule est le défaut : aucune commande de test n'est exécutée sans `--run`.
`--targeted` classe les fichiers modifiés, y compris les deux côtés d'un rename, et ne devient
jamais `full`. Un fichier de test modifié cible son propre module. Un chemin sans mapping produit
un plan vide au lieu d'une suite globale. `--json` fournit le plan structuré ; `--list` reste un
alias de compatibilité.

`--changed` conserve un plan prudent pour la CI : il peut recommander `full`, mais même
`--changed --run` refuse alors l'exécution. Seul `--full --run` peut démarrer la suite globale.

## Exécution après choix

```powershell
# Ciblés
python pipeline/scripts/test_changed.py --targeted --run

# Tous, seulement après choix explicite
python pipeline/scripts/test_changed.py --full --run

# Continuer les étapes indépendantes, puis retourner un échec agrégé
python pipeline/scripts/test_changed.py --targeted --run --keep-going
```

« Aucun test » signifie : ne lancer aucune des deux commandes et l'indiquer dans le compte rendu.
`git status`, `git diff`, `git diff --check`, la lecture des fichiers et les commandes sans `--run`
ne sont pas des tests. Les reconstructions suivent un choix séparé dans
[`WORKSPACE_INTEGRITY.md`](WORKSPACE_INTEGRITY.md).

## Groupes ciblables

| Groupe | Déclencheurs principaux |
|---|---|
| `smoke` | commande workspace et résolution des chemins |
| `documentation` | Markdown et points d'entrée agent |
| `workspace-command`, `workspace-paths`, `test-selection` | orchestration, chemins et sélecteur |
| `maps`, `map-diagnostics` | cartes, WED, injection, PVRZ diagnostique |
| `animations` | inventaire, upscale, timeline, packs et transactions animation |
| `animation-release` | gate temporaire du seul candidat animation de zone modifié |
| `sprite-inventory` | index et générateurs de jobs/familles |
| `sprite-formats` | runner, registres et catalogues |
| `sprite-installation` | installateur/restaurateur du catalogue cumulatif |
| `graphics-inventory` | UI, portraits, vidéos, icônes, curseurs, effets, projectiles |
| `video-upscale`, `video-interpolation` | recettes et runners vidéo |
| `registry`, `integrity` | contrat global, projections, runs, hashes, migrations |
| `renderer-transaction` | candidat renderer transactionnel |
| `release`, `engine` | Phase 2 release et CTest moteur |

Le sélecteur travaille au niveau module. La suite complète ajoute tous les tests Python,
`workspace.py check --after-full-tests`, la gate release Phase 2, puis configuration/build/CTest
moteur. Elle reste utile avant intégration sensible ou sur demande, pas comme contrôle local par
défaut.

`--keep-going` ne transforme jamais un échec en succès : toutes les étapes indépendantes restantes
sont exécutées, les erreurs sont récapitulées et le code final reste non nul.
