# Release animations — 2026-10-11 v1

- Autorisation : étape 4 release ; aucune publication publique ni modification du jeu.
- Production figée : `animations/packs-par-zone/animations-release-20261011-v1/<AREA>` ; 234 compositions complètes, registres et payloads identiques aux zones installées.
- Promotion : `promotion-plan-v3.json` → `promotion-receipt.json` ; transactions officielles `animation_release.apply_acceptance`, QA antérieures conservées.
- QA : 246 BAM acceptés ; 489 packs QA vérifiés (`qa-pack-compatibility.json`). Dates acquises inchangées.
- Rattachements courants : AM0309A occurrence 945,763 (QA 2026-09-21) ; OHHPORT run canonique (QA 2026-10-10). Anciens manifests/décisions immuables ; reçus `ar0309-occurrence-binding.json`, `ohhport-canonical-binding.json`.
- FIRE_4 : six zones gardent leur version installée approuvée via continuité byte-identique, indépendamment de la sélection globale.
- AR0516 WED : géométrie/octet inchangés, preuve acquise liée au registre complet actuel ; `ar0516-wed-acquired-qa-binding.json`.
- Renderer alpha.9 : DLL acceptée arbres/nuit SHA `5D4EE06D84E0D6C6F6FB81797EAB0E9756B3ECE335EBF537E57C5597E0B40BCF` ; source conservée + `renderer-source-inventory.json`. Aucun nouveau build source revendiqué.
- Installation : `owned_ini_keys.core-steam.Shaders.EnableAreaAnimationX4=true`, section réellement lue par le moteur.
- INI : détection BOM corrigée (comparaisons octet par octet) ; `Test-BG2HD-ConfigEncoding.ps1` vérifie activation/restauration UTF-8, UTF-8 BOM, UTF-16 LE/BE et préservation des clés étrangères modifiées. Essai compressé `build-a.json` antérieur à cette correction, supplanté.
- Ancien staging/renderer conservés hors `bg2hd` : `previous-staging-moves.json`, `renderer-bundle-before.json`, `runtime-compatibility-before.json`.
- WTLAKE : deux fichiers manquants réhydratés depuis staging conservé ; SHA approuvés inchangés (`restored-release-inputs.json`).
- Scripts `prepare.py`/`bind_*.py`/`freeze_runtime_and_wed.py` écrivent des versions immuables : ne pas rejouer sur les sorties existantes. `replan.py`/`repair_plan.py` consignent les réparations de références.
- Vérifications et paquet final : `docs/validation/animations-release-status-20261012-v1.json`.
- Publication bloquée : installation jeu propre, lancement Steam, sauvegardes vanilla futures, restauration complète/désinstallation, prérequis EEex absent, cycle renderer combiné, contact/provenance publics.

- Vérificateur par lot : `verify_animation_release_candidate.py --all` ou `--area ARxxxx --area ARyyyy` ; même validation complète, cache borné au verrou, rejet du lot au premier échec.
- Paquet : `build_and_validate.ps1` ; construction finale sans compression (ZIP_STORED), tests archive/installation, ZIP final retenu et scratch propre supprimé. Essai compressé antérieur supplanté après correction UTF-16 ; pas de comparaison de deux constructions finales. Aucun ancien paquet supprimé.
