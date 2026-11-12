# MANAFORG FullHD30 — 2026-11-12

- Source `video/manaforg/manaforg.wbm`,1280×720/15fps,251images/~16,733s,Vorbis jusqu’à~18,286s ; même chaîne que SARADUSH/FLYTHR01.
- `prepare.py` : SHA inventaire et MD5 YUV420p des251images source→FFV1 vérifiés ;1portion sans raccord ; dernière image tenue jusqu’à la fin du son comme en lecture source.
- ComfyUI localhost8188/RTX5090 ; SeedVR2 3B FP16 LAB1080,seed42,batch33/uniforme/overlap3,bruits0,SDPA,swap32,CPU offload,VAE encode1024/128/decode768/128. Entrée/graphes/jobs/downloads : `video/manaforg/runs/manaforg-seedvr-apollo30-20261112-v1/`.
- `finish.py` : ProRes SeedVR→H264CRF12 ; Apollo8 partagé via endings `interpolate()` : apo-8/30fps/rdt=-0.01/device0/vram0.8/instances0/download0,501images+1tenue=502images ;47images terminales supplémentaires→549images/18,3s couvrant tout le son. RGB→limited bt601 identique aux rendus précédents.
- MP4 H264/AAC192k,masterMKV H264/Vorbis natif,WBM VP8CRF4/30M/qmax12/Vorbis natif. Décodage/comptes/PTS des3formats,audio natif PCM/paquets/PTS MKV/WBM,SSIM runtime échantillonné>0,99 et images intermédiaires Apollo contrôlés avant manifeste final.
- Résultats : `video/final/manaforg-seedvr-apollo30-20261112-v1/MANAFORG/default/` ; manifeste `video/index/manaforg-finals30-20261112-v1.json` et `metadata/manifest.json`.
- QA visuelle acceptée2026-11-12 : `video/index/qa-decisions/MANAFORG/20261112-fullhd30-visual-accepted-v1.json` liée aux SHA finaux. **Vérification ingame en attente**, aucune intégration release.
- `install.py prepare` puis `install.py install` : jeu/InfinityLoader fermés ; original réel sauvegardé ; destinations/SHA contrôlés ; remplacement atomique `config://bg2ee_game_root/movies/manaforg.wbm` +alias neuf `movies/HDMANA.wbm`. Reçu : `video/index/manaforg-ingame-test-20261112-v1.json` ; copie `metadata/installation.json`.
- CLUA Ctrl+Espace en partie : `C:PlayMovie("HDMANA")`.
- Restauration jeu/loader fermés : contrôler SHA actuel=`after_sha256` du reçu ; recopier `video/installations/manaforg-apollo30-20261112-v1/before/movies/manaforg.wbm` vers `config://bg2ee_game_root/movies/manaforg.wbm`, vérifier SHA=`before_sha256` ; retirer uniquement l’alias neuf `movies/HDMANA.wbm` après contrôle de son SHA. Conserver sauvegarde/reçu.
