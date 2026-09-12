# Audit de performance du workflow — mise à jour 2026-09-06

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
| Tests Python | 390 méthodes dans 40 fichiers, hors sous-tests |
| Gates release | 12 scripts `Test-*.ps1` |
| Code pipeline Python/PowerShell | ~40 700 lignes dans 88 fichiers |
| Plus grands monolithes | `run_creature_sprite_x2.py` 8 214 lignes ; `audit_workspace_integrity.py` 3 018 ; `build_global_asset_registry.py` 2 237 |
| Documentation suivie | 158 fichiers Markdown |

Mesures obtenues par inventaires lecture seule ; aucun test ni projection n'a été exécuté.

## Ancienne chaîne de coût supprimée

Exemple historique : une ligne d'`areas.csv` changeait.

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
| P0 | Tests automatiques après chaque tâche | ancien `AGENTS.md` imposait `--changed` ; fallback `full` très large | tests uniquement s'ils apportent une information utile |
| P0 | Régénération globale systématique | `workspace.py` lance trois générateurs, chacun deux fois | génération en lot ou seulement comme livrable/gate |
| P0 | Plan de données dans le worktree | ~466 k fichiers, ~192 Gio pour 801 fichiers suivis | sortir runs/sources/builds du worktree via `config://...` |
| P1 | Tests dits unitaires sur l'état réel | registry, graphics et integrity lisent `ROOT` et rebâtissent les sorties | fixtures petites pour unitaires ; tests workspace séparés |
| P1 | Sélecteur tout-ou-rien | tout rename/delete et toute release/runtime deviennent `full` | ciblage strict par domaine ; full uniquement explicite |
| P1 | Déterminisme répété localement | générateurs et tests rebâtissent chacun deux fois | mono-passe local ; double passe en CI planifiée |
| P1 | Couplage de domaines | une autorité map déclenche registre de 15 k assets et audit de 562 runs | graphe de dépendances et refresh `--scope`/incrémental |
| P2 | Scripts monolithiques | 8,2 k lignes pour le runner sprite ; tests associés 2,7 k | extraire bibliothèques par format/étape et tester par module |
| P2 | Assertions sur snapshot global | tests d'intégrité figent compteurs, octets et présence physique | invariants sur fixtures ; snapshot réel dans une gate dédiée |
| P2 | Documentation distribuée | commandes/tests répétés dans plusieurs guides | politique canonique unique et liens courts |

## Plan de réduction

### Phase 0 — appliquée dans la documentation

- Aucun test automatique ni question rituelle ; lancer seulement le contrôle utile au cas courant.
- `--list` autorisé pour estimer le plan sans exécution.
- Un choix ciblé ne peut pas devenir `full` implicitement.
- `workspace.py refresh/check` n'est plus un rituel de fin de tâche ; regrouper les mises à jour.

Gain attendu sur les petites tâches : suppression de la quasi-totalité du temps de validation
quand l'utilisateur choisit aucun test, et forte réduction quand il choisit ciblés.

### Phase 1 — appliquée et simplifiée

- `test_changed.py` plan-only par défaut ; toute exécution exige `--run`.
- `--targeted --path ...` isole le lot des autres changements Git et ne devient jamais `full` ;
  `--changed --run` refuse une recommandation globale implicite.
- Un changement de code cible uniquement son module de test direct. Autorités, assets, projections
  et documentation ne sélectionnent aucun test Python.
- Les groupes Python par domaine sont supprimés ; les seules gates spéciales restent release et
  moteur.
- `workspace.py` plan-only, mono-passe et sans test documentaire embarqué.
- Reconstructions ciblables par `--scope graphics|registry|integrity`; `--changed` propose les scopes.
- `--verify-determinism` est explicite ; la CI ajoute elle-même `--run`.
- L'audit d'intégrité lit et valide la projection du registre au lieu de la reconstruire.
- Les doubles générations dans les tests registre, graphisme et intégrité sont retirées ; le contrôle
  de déterminisme reste disponible explicitement par CLI.

Critère : une modification Markdown n'exécute rien ; une modification d'un script map ne charge ni
sprites, ni inventaire graphique, ni release, ni moteur.

Le gain visé est supérieur à 80 % pour les lots d'assets et les changements de code localisés. La
suite release reste exhaustive ; son temps n'est pas soumis à cet objectif.

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
- Garder dans `AGENTS.md` le principe documentaire facultatif ; les autres fichiers servent
  d'index de solutions et de commandes.

## Ordre recommandé

1. Sélecteur plan-only, chemins explicites et ciblage direct — fait.
2. Mono-passe local et scopes de projection — fait.
3. Mesurer plusieurs lots réels sans modifier le workflow.
4. N'ajouter cache ou scopes incrémentaux que si la cible de 80 % n'est pas atteinte.
5. Garder le déplacement du data-root et le découpage des monolithes comme projets séparés.

Cette phase ne modifie aucun format métier, manifeste, artefact scellé ou projection existante.
