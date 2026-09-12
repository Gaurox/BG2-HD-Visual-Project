# Tests — index de commandes

Ce document aide à choisir une commande lorsqu'un test apporte une information utile. Il n'impose
aucun test, aucune question préalable et aucune suite complète. La demande utilisateur et le risque
réel de la modification déterminent seuls si un contrôle est pertinent.

## Commandes disponibles

| Besoin | Commande |
|---|---|
| Voir le test associé à un fichier | `python pipeline/scripts/test_changed.py --targeted --path <chemin>` |
| Exécuter ce test | même commande avec `--run` |
| Voir un plan depuis Git | `python pipeline/scripts/test_changed.py --changed --base origin/main` |
| Voir la suite globale | `python pipeline/scripts/test_changed.py --full` |
| Exécuter la suite globale | `python pipeline/scripts/test_changed.py --full --run` |
| Continuer après erreurs indépendantes | ajouter `--keep-going` |

Sans `--run`, la commande affiche seulement un plan. `--targeted --path` isole le fichier indiqué
des autres changements du worktree et ne s'élargit pas automatiquement à la suite complète.

## Repères de coût

- Documentation, autorités, assets et projections n'ont généralement aucun test Python utile.
- Un script peut sélectionner son `pipeline/tests/test_<script>.py` associé.
- Les contrôles globaux parcourent un workspace volumineux ; les réserver aux cas où leur couverture
  apporte réellement quelque chose, par exemple CI ou préparation explicite d'une release.
- Build, CTest moteur, projections et QA ingame sont indépendants des tests Python.

Ces repères sont des options, pas un workflow de clôture.
