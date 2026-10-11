# Nettoyage animations — points 1 à 3, 2026-10-11

| Action | Preuve / état |
|---|---|
| AR3021 : restauration AM3021D/E/F acceptés | `repair-installation.json`, sauvegardes transactionnelles |
| AR5000 : ajout FISH1L/FISH2L/FISH2S/FISH3S acceptés | Idem ; chaque fichier voisin conservé à l'identique |
| AR0307/AR0411/AR6001/AR6005 : verrou/recette | `repair-baseline.json` ; snapshot complet = installé, aucun fichier jeu remplacé |
| 43 QA historiques | `historical-registry-rows.json`, `historical-evidence/`, `historical-qa-migration.json` |
| Contrôles finaux | `verification.json` ; `../../../docs/validation/animations-cleanup-status-20261011-v2.json` |

Commandes exécutées, **ne pas rejouer les écritures** :

```powershell
python pipeline/recipes/animations-cleanup-points1-3-20261011-v1/prepare_repairs.py
python pipeline/recipes/animations-cleanup-points1-3-20261011-v1/install_repairs.py --verify-only
python pipeline/recipes/animations-cleanup-points1-3-20261011-v1/install_repairs.py
python pipeline/recipes/animations-cleanup-points1-3-20261011-v1/formalize_legacy.py
python pipeline/recipes/animations-cleanup-points1-3-20261011-v1/verify_and_report.py
```

Snapshot QA mono-asset : `animations/packs-par-zone/<resref>-historical-qa-bound-20261011-v1` ; **ne jamais installer sa feuille seule**. Le pack complet des six réparations est `animations/packs-par-zone/animations-cleanup-points1-3-20261011-v1`.

Écarts d'installation ouverts : `AM0205A/B/C/D` (accepté 27 phases Native/15 FPS, installé 54 phases/30 FPS) ; `AM0604A` (accepté Apollo14 sans alpha corrigé, installé spline alpha non approuvée). Sélections = versions historiques acceptées, jamais approbation implicite des versions installées. Les cinq installations restent inchangées ; décision/restauration ou QA ciblée requise.

AM0602F : 9 phases Native actuellement installées = QA AR0602 du 2026-09-05 ; la note plus ancienne 18 phases/30 FPS ne décrit pas cette version.

Pas de génération, modification de QA existante, ni intégration release. Les trois images utilisateur non suivies restent hors commit.

Cause des recettes cassées corrigée dans `pipeline/scripts/area_pack_state.py` : les objets de provenance multi-zone sous `merged_from` ne deviennent plus des chemins Python sérialisés. Régression couverte dans `pipeline/tests/test_area_pack_state.py` ; cinq tests passent.
