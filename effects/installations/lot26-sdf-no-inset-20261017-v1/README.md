# Lot26 installé — SDF sans retrait

- Demande2026-10-17 : annuler le retrait de pixels ; installer les26 pour test. Statut : `installation.json` = `installed-offline-verified`, QA utilisateur en attente ; jeu non lancé par l’agent.
- [26commandes principales](CLUA.md), [60profils par cycle/mode](CLUA-tous-profils.md). Lancer BG2EE HD via InfinityLoader ; une commande à la fois. Contrôleurs isolés, sans mécanique de sort/trajectoire PRO.
- Production : `effects/batches/lot26-sdf-no-inset-20261017-v1/` ; SeedVR7B x4/Apollo30, durée native conservée après retrait des doublons. Huit masques SDF sans érosion : SPHEART/SPHANDAT/SPRAISED/GLPHWRDT/SKLT/SPTRAPBB/TRAPGR/TRSPEART ;18autres v2 inchangés.
- Delta :26productions/27RESREF sources +X26PLAA normal ;253RESREF runtime/32927backings/245productions cumulées.225anciennes ressources/30229backings et anciens enregistrements binaires conservés exactement.
- Alpha normal/lumineux séparé ; SPIPLAAI/SPIPLARI prémultipliés, X26PLAA droit. ICINHIT/ICINTRAV : référence BAM seule adaptée.26VVC principaux +60VVC profils.
- Jeu/InfinityLoader arrêtés avant écriture ; fichiers remplacés sauvegardés sous `before/`, copies atomiques et SHA vérifiés. `transaction.json` détaille2817cibles. `before.json` préserve les empreintes DLL/shaders/personnages/exécutable ; aucune modification de ces fichiers.
- INI seul changement : `EffectMetadataMiB = 16`→`32` ; métadonnées17224952octets. Caches CPU/GPU, filtre NEAREST, profil personnages inchangés.
- `candidate-native-loader.log`, `installed-native-loader.log` : catalogue253ressources prêt,70888contrats natifs/30FPS vérifiés, zéro lecture RGBA par la sonde catalogue. Nouveaux fichiers RGBA vérifiés par hash lors de la préparation/copie.
- Manifest actif SHA256 : `52C359F55AC06916D040E5516BF027BF0E1A4B9521F64173E7698C7156F1C451` ; DLL conservée `FEA4B2B153653461D465B67EB9CC5A762CC97785E511EEBBF5C776348268C246`.
- Recette/restauration ciblée : `pipeline/recipes/effects-lot26-sdf-install-20261017-v1/README.md`. Aucun changement de QA acceptée/release.
