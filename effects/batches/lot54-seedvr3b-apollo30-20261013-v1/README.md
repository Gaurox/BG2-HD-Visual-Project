# Lot54 — 2026-10-13

- Périmètre exact : `batch.json`, 54 nouveaux BAM ; autorisation production + installation utilisateur.
- Recette : SeedVR2 3B INT8 ConvRot/LAB x4, pad x1=32 ; Apollo8 15→30 FPS, one-shot, alpha left ; Gaussian x4=1.2 px, inner feather x4=12 px, RGB prémultiplié.
- Source : 1 595 frames, 1 968 slots natifs ; résultat : 3 936 phases, 3 008 backings uniques.
- Vérifications : `verification.json`, `checks/<BAM>.json` ; 54/54 passent. Hashes, source alpha nearest, géométrie/centres, RGB spatial exact aux phases natives avant traitement, traitement pixel à pixel, durée, répétitions natives, backings/registres.
- Tests : 22 Python ciblés passent ; 3 C++ ciblés passent (`engine-checks.json`).
- Installation : `installation.json` ; 54 nouveaux + 10 précédents préservés, registre v2, 3 447 backings, 1 841 195 968 octets RGBA. INI inchangé ; registre eau compilé identique au build installé antérieur.
- Moteur : `build/iee-effects-lot54-2g-20261013`, limite RGBA 512 Mio→2 Gio ; chargement réel du pack complet par le loader C++ réussi avant installation. Pas de cache à la demande ajouté.
- Reçu/restauration : `effects/installations/lot54-seedvr3b-apollo30-gauss12-feather12-20261013-v1/backups/20261013T190200608823Z-2810cdb0/renderer-install-receipt.json`. Fermer jeu/InfinityLoader avant restauration via `install_renderer_candidate.py restore <reçu>`.
- QA visuelle : **en attente utilisateur ingame**, aucune sélection/acceptation/release déduite. Seules les 54 lignes de production/installation changent.
- Contrôle : `preview/index.html`, planche MP4 30 FPS, GIF d'aperçu 12 FPS, 54 MP4 individuels ; RGB prémultiplié affiché directement sur noir. Comparaisons natives/x4 : `preview/native-x4-review-{1,2,3}.png`. Commandes : `CLUA.md`, `CLUA.lua`, `clua.json` ; contrôleurs VVC réels, une commande à la fois sur Player1.
- Flux RGB après fondu (backings uniques, pas mesure ingame) : `SPSETTIH` −19.73 %, `BDSPCLAR` −14.44 %, `SPBLESHI` −13.25 %, `SHAREAW` −12.09 %, `SPFLSRIN` −10.69 %, `SPSHKIMP` −10.16 %. Paramètres autorisés conservés ; revue visuelle utile.
- Répétitions : poses/pauses et sous-séquences natives exactes permises ; seule une répétition sans même pose ou même transition native/fraction est refusée. `SPSHKIMP` Apollo v1 échoue avec l'ancien contrôle ; v2 produit/scellé, v1 conservé. Nouveau doublon après traitement refusé.
- Générateurs : `pipeline/recipes/effects-lot54-seedvr3b-apollo30-20261013-v1/{produce,verify,preview,review,install}.py`. Runs/packs scellés immuables ; nouvelle version pour remplacer un résultat ou cette planche finale.
- Sauvegarde complète (médias ignorés compris) : `python -B pipeline/scripts/sync_full_project_backup.py` ; vérifier `completed.json` après exécution.
