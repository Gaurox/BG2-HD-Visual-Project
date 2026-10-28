# V11 — traînées LIGHTCHA

- Source : `src/iee/core/effect_secondary_scope.h` + test `effect_surface_owner_tests.cpp` ; ajout scopeSPCHLGT1/3, aucun algorithme/cycle natif modifié. [Préparation/contrats](../../../../projectiles/analysis/eclairs-v11-preparation-20261028-v1/README.md).
- [Reçu actif](installation.json), [état précédent](before.json), [tests](tests.log), transaction/rollback sous `backups/`. Jeu/loader arrêtés avant installation.
- Deux fichiers remplacés : DLL et INI (seule clé `EnableEffectStreamingTrace=true`). Ancienne DLL V10 sauvegardée ; ressources538/62500backings, metadata, images, PRO inchangés,0inférence/0release.
- Trois suites passantes +824contrats/27cycles ; QAingame V11 attendue. Après capture, désactiver seulement la trace avec jeu/loader arrêtés ; garder V11.
