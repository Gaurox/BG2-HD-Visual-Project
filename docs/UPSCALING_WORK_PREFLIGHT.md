# Préflight obligatoire — upscaling

À lire avant tout travail de carte, animation ou effet.

## Avant production

1. Exécuter `git status --short`; préserver tout changement hors périmètre.
2. Lire `README.md`, le README du domaine, `docs/DECISIONS.md` et
   `pipeline/PROBLEMES_A_RESOUDRE.md`.
3. Identifier l'asset, son autorité et son état séparé : production, QA, installation, release.
4. Créer une nouvelle sortie immuable. Ne jamais réécrire un run, build, pack ou reçu existant.

## Animations — contrôles bloquants

| Objet créé ou modifié | Exigence dans la même tâche |
|---|---|
| Run mono-resref | `animations/ressources/<RESREF>/runs/<run-id>/`; manifeste avec `asset_ids`, recette, parents, entrées, sorties et hashes |
| Run multi-resrefs | `animations/batches/<run-id>/`; `asset_ids` explicites |
| Run sous `animations/runs/` | Interdit pour un nouveau run. Pour un legacy sans propriétaire : entrée `synthetic_run_bindings` dans `animations/index/path-migrations.json` |
| Racine sous `animations/packs-par-zone/` | Pack terminé uniquement. Ajouter immédiatement son nom, hash du `manifest.json`, date, classification et raison dans `animations/index/post-p3-pack-retention-20260902.json` |
| Intermédiaire jetable | Garder sous `.tmp/` ou dans le run ; ne pas laisser une racine non inventoriée dans `packs-par-zone/` |
| Nouveau schéma ou statut QA | Adapter tous les consommateurs : workflow/release, registre global, intégrité et tests |
| QA ingame validée | Utiliser `animation_workflow.py finalize`; ne pas éditer séparément CSV, sélection ou décision |
| Intégration release | Accord distinct et `animation_release.py`; aucune promotion déduite de la QA |

Ne jamais figer dans un test un total dérivé (`nombre de runs`, `packs`, `assets`). Calculer le total
depuis l'autorité concernée.

## Ordre de clôture

1. Mettre à jour les autorités et adaptateurs ; ne jamais modifier une projection générée à la main.
2. Vérifier que chaque nouveau run a des `asset_ids` et chaque pack physique une entrée de rétention.
3. Si du code a changé, préparer sans exécuter les tests de ses seuls fichiers :

   ```powershell
   python pipeline/scripts/test_changed.py --targeted --path <chemin-modifié>
   ```

4. Pour un lot limité aux autorités/assets, ne lancer aucun test Python ; conserver la validation
   transactionnelle et ingame du domaine.
5. À un jalon, pour un livrable de projection ou avant release/CI, préparer
   `workspace.py refresh --changed`, puis demander reconstructions ciblées/toutes/aucune.
6. Demander le choix ciblés/tous/aucun avant toute exécution de tests.
7. Si une reconstruction ou un test échoue, corriger l'autorité ou son consommateur. Ne pas masquer
   l'erreur, modifier la projection, supprimer un artefact par supposition ou élargir les tests.

## Échecs typiques à prévenir

| Signal | Cause à rechercher |
|---|---|
| `animation-pack-p3-drift` | Racine `packs-par-zone` absente du manifeste de rétention |
| Run sans asset | Layout legacy sans manifeste exploitable ni `synthetic_run_bindings` |
| QA devenue `not-assessed` | Nouveau contrat QA non pris en charge par le registre global |
| Test de total en échec après ajout légitime | Valeur agrégée codée en dur au lieu d'être dérivée |
