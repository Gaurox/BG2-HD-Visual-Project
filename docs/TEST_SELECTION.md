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

Sans `--run`, la commande affiche seulement un plan. `--targeted --path` isole le fichier indiqué
des autres changements du worktree. Le sélecteur connaît une seule convention :
`pipeline/scripts/x.py` → `pipeline/tests/test_x.py`. Il n'existe plus de fallback global.

## Repères de coût

- Documentation, autorités, assets et projections n'ont généralement aucun test Python utile.
- L'ajout d'un candidat accepté ou d'une projection release ne sélectionne automatiquement aucun
  test global.
- Un script peut sélectionner son `pipeline/tests/test_<script>.py` associé.
- Les contrôles globaux parcourent un workspace volumineux ; les réserver à une finalisation ou à
  un diagnostic transversal explicitement demandé. La CI ordinaire reste ciblée par impact.
- Build, CTest moteur, projections et QA ingame sont indépendants des tests Python.

Ces repères sont des options, pas un workflow de clôture.
