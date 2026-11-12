# FLYTHR01 FullHD30 — 2026-11-12

- Plus longue nouvelle vidéo restante après SARADUSH : FLYTHR01/22,332s ; ENDCRDIT en pause exclu. Source `video/flythr01/flythr01.wbm`,1280×720/15fps,301images/~20,067s,Vorbis jusqu’à~22,332s.
- `prepare.py` : SHA inventaire et MD5 YUV420p des301images source→FFV1 vérifiés ;1portion sans raccord. Dernière image native noire,maintenue jusqu’à la fin du son comme en lecture source.
- ComfyUI localhost8188/RTX5090 ; SeedVR2 3B FP16 LAB1080,seed42,batch33/uniforme/overlap3,bruits0,SDPA,swap32,CPU offload,VAE encode1024/128/decode768/128. Entrée/graphes/jobs/downloads : `video/flythr01/runs/flythr01-seedvr-apollo30-20261112-v1/`.
- `finish.py` : ProRes SeedVR→H264CRF12 ; Apollo8 partagé via endings `interpolate()` : apo-8/30fps/rdt=-0.01/device0/vram0.8/instances0/download0,601images+1tenue=602images ;68images noires terminales supplémentaires→670images/22,333s couvrant tout le son. RGB→limited bt601 identique aux rendus précédents.
- MP4 H264/AAC192k,masterMKV H264/Vorbis natif,WBM VP8CRF4/30M/qmax12/Vorbis natif. Décodage/comptes/PTS des3formats,audio natif PCM/paquets/PTS MKV/WBM,SSIM runtime échantillonné>0,99 et images intermédiaires Apollo contrôlés avant manifeste final.
- Résultats : `video/final/flythr01-seedvr-apollo30-20261112-v1/FLYTHR01/default/` ; manifeste `video/index/flythr01-finals30-20261112-v1.json` et `metadata/manifest.json`.
- QA visuelle acceptée2026-11-12 : `video/index/qa-decisions/FLYTHR01/20261112-fullhd30-visual-accepted-v1.json` liée aux SHA finaux. **Vérification ingame en attente**, aucune intégration release.
- `install.py prepare` puis `install.py install` : jeu/InfinityLoader fermés ; original réel sauvegardé ; destinations/SHA contrôlés ; remplacement atomique `config://bg2ee_game_root/movies/flythr01.wbm` +alias neuf `movies/HDFLY01.wbm`. Reçu : `video/index/flythr01-ingame-test-20261112-v1.json` ; copie `metadata/installation.json`.
- CLUA Ctrl+Espace en partie : `C:PlayMovie("HDFLY01")`.
- Restauration jeu/loader fermés : contrôler SHA actuel=`after_sha256` du reçu ; recopier `video/installations/flythr01-apollo30-20261112-v1/before/movies/flythr01.wbm` vers `config://bg2ee_game_root/movies/flythr01.wbm`, vérifier SHA=`before_sha256` ; retirer uniquement l’alias neuf `movies/HDFLY01.wbm` après contrôle de son SHA. Conserver sauvegarde/reçu.
