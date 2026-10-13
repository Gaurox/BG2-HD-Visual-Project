# Lot54 — acceptation 3B et nettoyage, 2026-10-13

- Décision explicite : « je valide le parck des 54 effets en 3b. ils sont ok. supprime les test non utilisés et committe » ; réponse complémentaire : « Oui, garder le lot entièrement en 3B ».
- `acceptance.json` : 54 décisions QA immuables `effects/index/qa-decisions/<BAM>/`, 54 sélections exactes ; référence au lot initial et aux vérifications 54/54. Recette : SeedVR2 3B/LAB x4 → Apollo8 15→30, native-left → Gaussian1.2/feather12, RGB prémultiplié ; effects NEAREST.
- Production courante = spatial 3B et traitement sélectionné ; QA=passed. Installation et release restent des états séparés ; aucune mutation release.
- Installation finale : `effects/installations/lot54-accepted-3b-nearest-20261013-v1/result.json` ; 545 backings 7B remplacés par les 3B retenus, 10 anciens effets hors lot préservés. DLL nearest, INI et shaders/catalogue personnages SHA identiques ; sprites NearestRGB-SilhouetteAlphaAA conservés.
- Nettoyage : `purge-plan.json` + `purge-receipt.json` ; 51 racines (11 essais ratés + 30 runs 7B non retenus + 10 packs 7B), 7850 fichiers, 1936533533 octets logiques retirés. Gain d'espace libre non mesuré ; liens physiques possibles.
- `discarded-trial-metadata/` : recettes/descripteurs/manifests/conclusions exacts avant suppression. Productions 3B retenues, parents, BAM sources, sauvegardes/candidats d'installation, comparatifs finaux 3B/7B conservés. Pas de purge d'une autre famille, d'une carte ou de preuves finales.
- `verification-after-cleanup.json` : 54 contrôles workflow passés après suppression ; dépendances retenues présentes, QA/sélections exactes, autres lignes et champs release inchangés, installation finale conforme.
- Réserve technique distincte : FDAWNX a un fallback de géométrie connu31x32/31x76 ; la décision visuelle ne répare pas ce chemin runtime. Voir `docs/measurements/effects-character-native-fallback-20261013-212235-v1/`.
- Scripts dans `pipeline/recipes/effects-lot54-accept-cleanup-20261013-v1/` : acceptation → réinstallation3B → plan de purge → vérification SHA et suppression PowerShell → contrôle final. Résultats immuables ; ne pas rejouer dans ces dossiers.
