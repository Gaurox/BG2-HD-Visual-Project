# Sélection des tests

## Politique

| Changement | Contrôle local | Contrôle différé |
|---|---|---|
| Autorité métier, asset, projection ou documentation | aucun test Python | projections au jalon ; suite complète avant release |
| Code Python/PowerShell | test du module directement associé | suite complète avant release |
| Manifeste candidat animation | gate de la zone concernée | gate Phase 2 avant release |
| Moteur | build et CTest moteur | suite complète avant release |

Les contrôles globaux restent dans la suite complète. Ils ne sont pas une conséquence automatique
d'une modification de données. Aucun test, build, CTest ou gate ne démarre sans `--run` et sans
choix explicite de l'utilisateur.

## Plan isolé recommandé

Déclarer uniquement les fichiers du lot courant. `--path` est répétable et ignore les autres
modifications du worktree :

```powershell
python pipeline/scripts/test_changed.py --targeted `
  --path pipeline/scripts/build_alpha_feather.py `
  --path pipeline/tests/test_build_alpha_feather.py
```

Règles de sélection :

- un `pipeline/tests/test_*.py` sélectionne uniquement son module ;
- un script sélectionne `test_<nom_du_script>.py` s'il existe ;
- les rares noms non symétriques utilisent un alias explicite dans `test_changed.py` ;
- autorités, assets, projections et documentation ne sélectionnent aucun test Python ;
- un chemin de code inconnu produit un avertissement et un plan vide en mode `--targeted` ;
- rename et suppression examinent les deux chemins sans escalade globale en mode `--targeted`.

Les chemins doivent être relatifs au dépôt. `--path` est incompatible avec `--base` et exige
`--targeted`.

## Modes Git et CI

```powershell
# Plan strict sur tout le worktree ; utile seulement si son contenu correspond à une tâche
python pipeline/scripts/test_changed.py --targeted

# Plan prudent pour la CI ; un chemin inconnu peut recommander la suite complète
python pipeline/scripts/test_changed.py --changed --base origin/main

# Plan exhaustif explicite
python pipeline/scripts/test_changed.py --full
```

Même si `--changed` recommande `full`, `--changed --run` refuse l'escalade. Seul
`--full --run` démarre la suite globale. `--json` fournit le plan structuré et `--list` reste un
alias de compatibilité.

## Exécution après choix

```powershell
# Reprendre les mêmes --path que dans le plan validé
python pipeline/scripts/test_changed.py --targeted --path CHEMIN --run

# Suite complète : Python (dont fraîcheur des projections), Phase 2, moteur
python pipeline/scripts/test_changed.py --full --run

# Poursuivre les étapes indépendantes et conserver un code final non nul en cas d'échec
python pipeline/scripts/test_changed.py --full --run --keep-going
```

Avant release, la suite complète reste obligatoire pour revendiquer une validation finale. Les
reconstructions sont indépendantes et décrites dans
[`WORKSPACE_INTEGRITY.md`](WORKSPACE_INTEGRITY.md).
