# Audit de performance du workflow — 2026-08-31

## Conclusion

La lenteur ne vient pas principalement du nombre brut de tests. Le multiplicateur dominant est
l'enchaînement automatique de contrôles globaux sur un workspace de données massif : une petite
modification peut reconstruire plusieurs fois les mêmes projections, parcourir des centaines de
milliers de fichiers, puis être reclassée en suite Python + release + moteur.

Objectif : tâche documentaire/métadonnée < 30 s hors travail utile ; test ciblé unitaire < 60 s ;
contrôle de domaine < 2 min ; suite globale uniquement sur choix explicite ou CI. Mesurer les temps
avant/après chaque phase.

## Mesures

| Indicateur | Valeur observée |
|---|---:|
| Fichiers suivis Git | 801 |
| Fichiers physiques hors `.git` | ~466 000 |
| Volume physique hors `.git` | ~192 Gio |
| Données principales | maps 133,6 Gio ; animations 36,1 Gio ; sprites 11,9 Gio |
| Runs indexés | 562 |
| Assets du registre global | 15 137 |
| Sorties `asset-tracking/` | 18,2 Mio, dont `registry.json` 13,2 Mio |
| Tests Python | 285 méthodes dans 33 fichiers, hors sous-tests |
| Gates release | 12 scripts `Test-*.ps1` |
| Code pipeline Python/PowerShell | ~40 700 lignes dans 88 fichiers |
| Plus grands monolithes | `run_creature_sprite_x2.py` 8 214 lignes ; `audit_workspace_integrity.py` 3 018 ; `build_global_asset_registry.py` 2 237 |
| Documentation suivie | 158 fichiers Markdown |

Mesures obtenues par inventaires lecture seule ; aucun test ni projection n'a été exécuté.

## Chaîne de coût actuelle

Exemple : une ligne d'`areas.csv` change.

```text
workspace.py refresh
  → inventaire graphique ×2
  → registre global ×2
  → intégrité physique/runs ×2
  → test documentation

test_changed.py --changed
  → smoke + maps + registry + integrity
  → registre reconstruit ×2 dans ses tests
  → intégrité reconstruite ×2 dans ses tests
```

Le suffixe `×2` vient de la preuve de déterminisme. Les audits lisent le workspace réel :
`rglob`, hashes SHA-256, inspection des 562 runs, sources, migrations et archives. Pour un
rename/delete, chemin inconnu, configuration, test/CI, release ou moteur, le sélecteur passe en
`full` et ajoute tous les tests Python, `workspace.py check`, la gate release Phase 2, CMake, build
et CTest moteur.

## Causes classées

| Priorité | Cause | Preuve | Correction |
|---|---|---|---|
| P0 | Tests automatiques après chaque tâche | `AGENTS.md` imposait `--changed` ; fallback `full` très large | choix utilisateur ciblés/tous/aucun ; aucune escalade implicite |
| P0 | Régénération globale systématique | `workspace.py` lance trois générateurs, chacun deux fois | génération en lot ou seulement comme livrable/gate |
| P0 | Plan de données dans le worktree | ~466 k fichiers, ~192 Gio pour 801 fichiers suivis | sortir runs/sources/builds du worktree via `config://...` |
| P1 | Tests dits unitaires sur l'état réel | registry, graphics et integrity lisent `ROOT` et rebâtissent les sorties | fixtures petites pour unitaires ; tests workspace séparés |
| P1 | Sélecteur tout-ou-rien | tout rename/delete et toute release/runtime deviennent `full` | ciblage strict par domaine ; full uniquement explicite |
| P1 | Déterminisme répété localement | générateurs et tests rebâtissent chacun deux fois | mono-passe local ; double passe en CI planifiée |
| P1 | Couplage de domaines | une autorité map déclenche registre de 15 k assets et audit de 562 runs | graphe de dépendances et refresh `--scope`/incrémental |
| P2 | Scripts monolithiques | 8,2 k lignes pour le runner sprite ; tests associés 2,7 k | extraire bibliothèques par format/étape et tester par module |
| P2 | Assertions sur snapshot global | tests d'intégrité figent compteurs, octets et présence physique | invariants sur fixtures ; snapshot réel dans une gate dédiée |
| P2 | Documentation distribuée | commandes/tests répétés dans plusieurs guides | politique canonique unique et liens courts |

## Plan pour atteindre ×10

### Phase 0 — appliquée dans la documentation

- Aucun test automatique ; question obligatoire : ciblés, tous ou aucun.
- `--list` autorisé pour estimer le plan sans exécution.
- Un choix ciblé ne peut pas devenir `full` implicitement.
- `workspace.py refresh/check` n'est plus un rituel de fin de tâche ; regrouper les mises à jour.

Gain attendu sur les petites tâches : suppression de la quasi-totalité du temps de validation
quand l'utilisateur choisit aucun test, et forte réduction quand il choisit ciblés.

### Phase 1 — appliquée

- `test_changed.py` plan-only par défaut ; toute exécution exige `--run`.
- `--targeted` classe strictement les fichiers et ne devient jamais `full` ; `--changed --run`
  refuse une recommandation globale implicite.
- Tests séparés par modules/groupes et scopes Python/release/engine.
- `workspace.py` plan-only, mono-passe et sans test documentaire embarqué.
- Reconstructions ciblables par `--scope graphics|registry|integrity`; `--changed` propose les scopes.
- `--verify-determinism` est explicite ; la CI ajoute elle-même `--run`.

Critère : une modification Markdown n'exécute rien ; une modification d'un script map ne charge ni
sprites, ni inventaire graphique, ni release, ni moteur.

Restent à implémenter : cache par hash d'inputs, scopes métier plus fins et télémétrie durée/fichiers/
octets par stage.

### Phase 2 — découplage du plan de données

1. Déplacer progressivement `maps/*/runs`, `animations/runs`, `animations/packs-par-zone`,
   `sprite/**/runs` et sources extraites vers un data-root externe.
2. Garder dans Git uniquement autorités, manifests, jobs, recettes, hashes et pointeurs
   `config://...`.
3. Remplacer les scans globaux par la lecture des manifests ; vérifier les octets physiques
   seulement dans une gate d'intégrité explicitement choisie.
4. Mémoriser les hashes par `(chemin, taille, mtime)` pour le contrôle local ; recalcul complet en
   CI/release.

Critère : les commandes de routine ne parcourent jamais les ~192 Gio.

### Phase 3 — maintenabilité

- Découper les trois plus grands scripts sans changer leur CLI.
- Transformer les tests sur workspace réel en fixtures synthétiques et petites.
- Conserver une seule gate de snapshot réel par domaine.
- Centraliser les politiques transversales dans `AGENTS.md`, `DECISIONS.md` et
  `TEST_SELECTION.md` ; les README de domaine ne gardent qu'un lien.

## Ordre recommandé

1. Instrumentation des durées.
2. Sélecteur plan-only + ciblage strict — fait.
3. Mono-passe local et scopes de projection — fait.
4. Séparation unitaires/intégration.
5. Cache et scopes métier incrémentaux.
6. Data-root externe.
7. Découpage des monolithes.

Les étapes 2 à 5 devraient fournir l'essentiel du gain ×10 sans modifier les formats métier ni les
artefacts scellés. Le déplacement du data-plane apporte ensuite un gain durable sur les scans,
recherches et audits Windows.
