# Lot64 — installation locale

- Autorisation : installer64 effets SeedVR7B x4/NEAREST/30FPS, taille native ; personnages avec AA actuel ; lancement et contrôle du jeu exclusivement utilisateur.
- `installation.json` : reçu final après validation transactionnelle et chargeur natif sur fichiers installés.161 ressources cumulées ;97 anciennes ressources RGBA/cycles identiques ;97carriers BAM ; cartes/VVC/shaders personnages non modifiés.
- `before.json`, `backups/*/renderer-install-receipt.json` : état antérieur et restauration transactionnelle ; aucune validation ingame déduite.
- `ctest.log` :7/7 tests ciblés réussis ;19 tests Python installer/compositeur réussis. `native-profile-offsets.json` : vérification des offsets owner dans l'exécutable exact.
- `runtime-contracts.tsv`, `candidate-native-loader.log`, `installed-native-loader.log` :33548 contrats (20028 nouveaux64), tous slots/phases/cycles/profils/casse/dimensions/backings ; filtre NEAREST et cacheGPU64.
- [CLUA](CLUA.md) :64 commandes principales et tous contrôleurs natifs alternatifs ; `clua.json` relie chaque BAM au VVC réel.
- Recette : `pipeline/recipes/effects-lot64-install-20261015-v1/README.md`. QA64 et cadence réellement présentée à confirmer par l'utilisateur ; release non modifiée.

- Acceptation utilisateur2026-10-15 :64/64 validés, `effects/batches/lot64-accepted-20261015-v1/acceptance.json` ; reçus antérieurs conservés immuables, mesure instrumentée de cadence distincte.
