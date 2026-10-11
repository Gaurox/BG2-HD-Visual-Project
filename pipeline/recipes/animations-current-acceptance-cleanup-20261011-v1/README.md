# QA actuelle et purge — 2026-10-11

- Demande : acceptation ingame explicite des cinq assets visités ; conserver les versions ; supprimer les runs inutilisés ; actualiser le suivi.
- AR0205 `AM0205A/B/C/D` : 54 phases, 30 FPS. AR0604 `AM0604A` : 14 phases, 30 FPS, masque spline-fit2 alpha.
- `acceptance.json` : cinq décisions immuables, SHA des anciennes QA, payloads exacts installés et snapshots complets. Aucun fichier jeu remplacé.
- `purge-plan.json` : 959 racines examinées ; 737 protégées ; 222 candidates sans dépendance retenue. Fermeture transitive depuis QA/sélections/registre/verrou/release ; protection BAM natifs, réservations, approbations techniques et reparse points.
- `delete-verified.json` : empreintes avant suppression, archives et SHA des recettes/conclusions de diagnostic. `discarded-run-records/` : copies originales des métadonnées racines ; historique de chemins conservé.
- `delete_unused_runs.ps1` : vérification absolue des racines puis suppression native PowerShell. `deletion-progress.json` : journal. `purge-receipt.json` : suppression effective, 27 860 fichiers / 14 557 029 249 octets.
- `artifact-metadata-verification.json` : 1 265 manifests QA/sélection existants et hashés après purge, aucune erreur. Les anciens chemins de provenance déjà absents avant purge restent listés dans `purge-plan.json`.
- `verification.json` : cinq contrôles workflow, jeu = snapshots, anciennes QA intactes, 234 zones cohérentes.
- Suivi courant : `docs/validation/animations-cleanup-status-20261011-v3.json`. Aucune mutation release/payload/staging/TP2.
- Exécution effectuée : `accept_current.py` → `purge_unused_runs.py plan` → `verify-delete` → `delete_unused_runs.ps1` → `after-delete` → `finish_tracking.py`. Ne pas rejouer : preuves finales immuables, écritures exclusives.
