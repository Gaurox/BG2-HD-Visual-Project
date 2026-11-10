# DAYNITE — nearest + Apollo30 installé pour test local

- Demande2026-11-10 : « integre la ingame pour test et committe ». Choix : H3 01604/fondus corrigés/nearest1920×1080/Apollo8/30fps/300frames ; pas le rendu SeedVR.
- Preview : `video/daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1/DAYNITE-H3-01604-NEAREST-Apollo8-1080p30-son-original-v1.mp4`.
- `python -B pipeline/recipes/daynite-h3-nearest-ingame-20261110-v1/runtime.py prepare` : VP8 libvpx,CRF4,30M,qmin0,qmax12,cpu-used0,good,yuv420p ; image10s, son Vorbis natif copié depuis `video/daynite/daynite.wbm` ; durée conteneur≈10,292s.
- Runtime : `video/daynite/runs/daynite-h3-nearest-ingame-20261110-v1/daynite.wbm` ; `encoding.json`, `quality-check.json`.1920×1080/30fps/300frames ; SSIM0,990231 face au MP4 ; PCM Vorbis SHA256 identique au natif.
- `runtime.py install` : seulement `config://bg2ee_game_root/movies/daynite.wbm` ; jeu/InfinityLoader absents avant sauvegarde et remplacement atomique ; copie installée hash-identique au runtime.
- Reçu : `video/installations/daynite-h3-nearest-20261110-v1/installation.json` ; original remplacé sous `before/daynite.wbm` (SHA256687b2e7e72d995238f4f0963e6cc45d3baba66b0388a88d0fa2344877e62f208).
- Sélection utilisateur : `video/index/qa-decisions/DAYNITE/20261110-h3-nearest-apollo30-selected-for-local-test-v1.json`. QA ingame EN ATTENTE ; aucune validation ingame/release déduite.
- Restaurer : fermer jeu/InfinityLoader ; recopier le `before/daynite.wbm` du reçu vers sa cible exacte ; contrôler `before_sha256`. Garder le reçu de test historique ; créer un nouveau reçu si restauration.
