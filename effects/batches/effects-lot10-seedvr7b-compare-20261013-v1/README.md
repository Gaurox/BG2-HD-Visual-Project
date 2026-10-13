# Comparatif effects 3B/7B — 2026-10-13

- Demande : utilisateur juge tous les effets 3B encore pixelisés ; essai10effects SeedVR2 7B x4 après contrôle du runtime.
- Runtime observé : [`session21:45`](../../../docs/measurements/effects-character-stable-session-20261013-214500-v1/README.md), CharactersHDx2 sans fallback signalé,6effects x4 confirmés,1800x4Bound/0fallback ;48autres assets non observés dans cette session.
- Sélection : BDETHER, BDSPCLAR, EXALTAH, GLDUSTH, SPNWCHRM, SPPLANAR, ABJURH, SPGFLSH1, COLDH, SPCCMDSI ;290frames sources/364slots natifs/728phases30FPS.
- Différence unique : `seedvr2_3b_int8_convrot.safetensors` -> `seedvr2_7b_int8_convrot.safetensors` ; workflow7B canonique `pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json`, multiplicateur runtime4 ; mêmes seed959948902156062/euler/1step/cfg1/denoise1/LAB/VAE/tiling/pad32.
- Temporal : Apollo8,15->30FPS,one-shot,native-left-alpha,dedup ; GaussianRGBσ1.2x4/featherintérieur12x4/premul. Centres/canvas/cycles/alpha identiques à3B ; comparaison pixel exacte pour chaque phase.
- Autorité : `batch.json` (runs/parents3B/packs), `verification.json`, `checks/<RESREF>.json`, `review-artifacts.json`.10/10checks passés ;366430208octets de packs7B ; essais non enregistrés dans `processing.csv`, aucune installation7B, QA visuelle en attente.
- Scripts : `pipeline/recipes/effects-lot10-seedvr7b-compare-20261013-v1/{produce,verify,compare,run_all}.py` ; relance `python -B pipeline/recipes/effects-lot10-seedvr7b-compare-20261013-v1/run_all.py`. Runs scellés réutilisés, jamais écrasés ; spatialv2 emploie le workflow7B supporté par le producteur.
- Contrôle : `preview/index.html`, `preview/comparison-animated-30fps.mp4`, `preview/videos/<RESREF>-3B-7B.mp4` ;3B gauche/7B droite, mêmes phases/ancrages,RGBpremul affiché sur noir sans seconde multiplication alpha. Pause/Rejouer/agrandissement/taille réelle ;11vidéos chargées,0erreur média.
- URL locale : `http://127.0.0.1:8767/preview/index.html` ; serveur127.0.0.1,pid29812. GIF12FPS seulement aperçu ; juger les clips30FPS/pleine résolution.
- Différences RGB dans `preview/comparison.json` : mesure d'écart, pas score de qualité. Observation locale BDETHER : bandes/escaliers plus lisses en7B ; gain global/animation à juger par l'utilisateur.
- Limite : modèle7B ne change pas l'alpha natif agrandi ni la découpeWED. Aucun verdict automatique « pixelisation résolue » ; aucun changement du candidat sprites `NearestRGB-SilhouetteAlphaAA`.
- Installation préservée par SHA : DLLcache64,INI,fpDraw/fpSprite/fpSELECT,cataloguecreatures,registre64effects3B ; suivi courant également inchangé.
