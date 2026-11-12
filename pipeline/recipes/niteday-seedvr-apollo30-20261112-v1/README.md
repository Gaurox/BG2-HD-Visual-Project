# NITEDAY FullHD30 — 2026-11-12

- Source `video/niteday/niteday.wbm`,1280×720/15fps,150images/10s,Vorbis jusqu’à~10,942s. Asset NITEDAY autonome ; chaîne DAYNITE historique inchangée.
- `prepare.py` : SHA inventaire et MD5 YUV420p des150images source→FFV1 vérifiés ;1portion sans raccord ; dernière image tenue jusqu’à la fin du son comme en lecture source.
- ComfyUI localhost8188/RTX5090 ; SeedVR2 3B FP16 LAB1080,seed42,batch33/uniforme/overlap3,bruits0,SDPA,swap32,CPU offload,VAE encode1024/128/decode768/128. Entrée/graphes/jobs/downloads : `video/niteday/runs/niteday-seedvr-apollo30-20261112-v1/`.
- `finish.py` : ProRes SeedVR→H264CRF12 ; Apollo8 partagé via endings `interpolate()` : apo-8/30fps/rdt=-0.01/device0/vram0.8/instances0/download0,299images+1tenue=300images ;29images terminales supplémentaires→329images/10,967s couvrant tout le son. RGB→limited bt601 identique aux rendus précédents.
- MP4 H264/AAC192k,masterMKV H264/Vorbis natif,WBM VP8CRF4/30M/qmax12/Vorbis natif. Décodage/comptes/PTS des3formats,audio natif PCM/paquets/PTS MKV/WBM,SSIM runtime échantillonné>0,99 et images intermédiaires Apollo contrôlés avant manifeste final.
- Résultats : `video/final/niteday-seedvr-apollo30-20261112-v1/NITEDAY/default/` ; manifeste `video/index/niteday-finals30-20261112-v1.json` et `metadata/manifest.json`.
- Candidat SeedVR non sélectionné : utilisateur2026-11-12 retient la version H3 inversée ; voir `../niteday-h3-reverse-20261112-v1/README.md`. Résultats/métadonnées SeedVR conservés historiquement ; aucune validation ni installation de ce candidat déduite.
