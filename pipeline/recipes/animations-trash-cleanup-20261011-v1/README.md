# Suppression et corbeille — 2026-10-11

- Autorisation utilisateur : supprimer les 43 candidats de l'audit ; déplacer les cas incertains en corbeille racine.
- Audit source : `../animations-remaining-runs-audit-20261011-v1/reviewed-audit.json`.
- `operation-plan.json` : empreintes recontrôlées, 43 suppressions, 29 déplacements, 22 réservations associées ; SHA complets des fichiers mis en corbeille, sources BAM canoniques vérifiées.
- `discarded-run-records/` : copies exactes des diagnostics/scripts/manifests des 43 runs supprimés, sous namespace hashé ; binaires générés supprimés.
- Exécution effectuée : `prepare.py` → `apply.ps1` → `verify_and_record.py`. Plans/reçus finaux immuables ; ne pas rejouer au même chemin.
- PowerShell natif, `LiteralPath`, chemins absolus vérifiés dans le dépôt ; aucune destination existante remplacée. Journal `operation-progress.json`.
- `receipt.json` : 43 supprimés (~0,98 Gio net) ; 29 déplacés + 22 réservations, mêmes SHA ; 665 conservés ; 1 265 manifests QA/sélection intacts ; 234 zones cohérentes.
- Corbeille : `corbeille/animations-20261011-v1/manifest.json` ; payloads locaux ignorés par Git. `animations/index/run-quarantine-20261011-v1.json` mappe les anciens chemins vers la corbeille ; aucune implication QA/install/release.
- Suivi courant : `docs/validation/animations-cleanup-status-20261011-v4.json`. Aucun fichier jeu/release/payload/staging/TP2 modifié.
