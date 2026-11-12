# FLYTHR04 FullHD30 — 2026-11-12

- Source `video/flythr04/flythr04.wbm`,1280×720/15fps,245images/~16,333s,Vorbis/conteneur16,329s. Même profil SeedVR/Apollo que films précédents ; aucune extension terminale supplémentaire nécessaire.
- `prepare.py` : SHA inventaire et MD5 YUV420p des245images source→FFV1 vérifiés ;1portion sans raccord,horloge15fps conservée.
- ComfyUI localhost8188/RTX5090 ; SeedVR2 3B FP16 LAB1080,seed42,batch33/uniforme/overlap3,bruits0,SDPA,swap32,CPU offload,VAE encode1024/128/decode768/128. Entrée/graphes/jobs/downloads : `video/flythr04/runs/flythr04-seedvr-apollo30-20261112-v1/`.
- `finish.py` : ProRes SeedVR→H264CRF12 ; Apollo8 partagé via endings `interpolate()` : apo-8/30fps/rdt=-0.01/device0/vram0.8/instances0/download0,489images+1tenue=490images/16,333s ; réutilisation directe de la vidéo Apollo,sans réencodage de prolongation. RGB→limited bt601 identique aux rendus précédents.
- MP4 H264/AAC192k,masterMKV H264/Vorbis natif,WBM VP8CRF4/30M/qmax12/Vorbis natif. Décodage/comptes/PTS des3formats,audio natif PCM/paquets/PTS MKV/WBM,SSIM runtime échantillonné>0,99 et images intermédiaires Apollo contrôlés avant manifeste final.
- Résultats : `video/final/flythr04-seedvr-apollo30-20261112-v1/FLYTHR04/default/` ; manifeste `video/index/flythr04-finals30-20261112-v1.json` et `metadata/manifest.json`.
- QA visuelle acceptée2026-11-12 : `video/index/qa-decisions/FLYTHR04/20261112-fullhd30-visual-accepted-v1.json` liée aux SHA finaux. **Vérification ingame en attente**, aucune intégration release.
- `install.py prepare` puis `install.py install` : jeu/InfinityLoader fermés ; original réel sauvegardé ; destinations/SHA contrôlés ; remplacement atomique `config://bg2ee_game_root/movies/flythr04.wbm` +alias neuf `movies/HDFLY04.wbm`. Reçu : `video/index/flythr04-ingame-test-20261112-v1.json` ; copie `metadata/installation.json`.
- CLUA Ctrl+Espace en partie : `C:PlayMovie("HDFLY04")`.
- Restauration jeu/loader fermés : contrôler SHA actuel=`after_sha256` du reçu ; recopier `video/installations/flythr04-apollo30-20261112-v1/before/movies/flythr04.wbm` vers `config://bg2ee_game_root/movies/flythr04.wbm`, vérifier SHA=`before_sha256` ; retirer uniquement l’alias neuf `movies/HDFLY04.wbm` après contrôle de son SHA. Conserver sauvegarde/reçu.
