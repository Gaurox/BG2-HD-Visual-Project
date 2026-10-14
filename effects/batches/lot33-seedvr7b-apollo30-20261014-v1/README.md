# Lot33 — SeedVR2 7B x4, 2026-10-14

- Autorisation utilisateur : « traite le lot complet avec la recette habituelle et seedVR 7b x4 » ; instance ComfyUI fournie.
- `batch.json` : 33 BAM ; 1054 frames sources, 1101 slots natifs ; projection2202phases30FPS. Proposition native conservée séparément.
- Spatial : workflow approuvé7B, `seedvr2_7b_int8_convrot.safetensors`, x4 explicite, LAB, pad32 ; seed959948902156062, steps1/cfg1, euler/simple, VAE512/overlap128.
- Temporel : Apollo8 15→30, one-shot, alpha native-left, déduplication physique ; répétitions/pauses natives conservées.
- Traitement habituel : GaussianRGB sigma1.2 px x4, fondu intérieur12 px x4, RGB prémultiplié une fois ; alpha <= source.
- Producteurs : `pipeline/recipes/effects-lot33-seedvr7b-apollo30-20261014-v1/{run_all,produce,verify,preview,status}.py` ; `spatial-progress.json`, `temporal-progress.json`, `checks/`, `verification.json`.
- Résultats par asset : `effects/ressources/<BAM>/runs/` et `packs/` ; productions enregistrées, sélection/QA/installation/release indépendantes.
- Revue : `preview/index.html`, vidéos individuelles et planche30FPS ; thumbnails nearest, vues1:1, RGB déjà prémultiplié affiché directement sur noir. GIF d'aperçu12FPS distinct des vidéos30FPS.
- `CLUA.md` : contrôleurs VVC natifs pour un test ultérieur après installation. Cette demande ne modifie pas le jeu ni les sélections acceptées.

- Résultat final : `production-result.json` ; 33/33 contrôles passés, 1054 frames sources, 2202 phases30FPS, 1586817728 octets dans les33packs autonomes.
- Galerie vérifiée : `review-browser.json`, 34 vidéos chargées et lues sans erreur, pause/replay communs, vue1:1 contrôlée ; URL `http://127.0.0.1:8768/preview/index.html`.
- Atténuation RGB intégrée (mesure fichiers, pas qualité ingame) : SPATTCK2−35.61 %, OHDSTREE−27.19 % ; paramètres habituels12px conservés à la demande. Comparatifs natif/final : `preview/native-x4-review-{1,2}.png`.

- Installation ultérieure explicitement demandée : `installation.json` ; 33x7B ajoutés aux64 précédents, x4/nearest/30FPS, personnages conservés. Reçu et CLUA actuels : `effects/installations/lot33-seedvr7b-apollo30-nearest-20261014-v1/`. `production-result.json` reste le constat immuable de fin de production avant cette installation ; QA visuelle ingame en attente.
