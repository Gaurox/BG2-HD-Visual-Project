# LOGO FullHD natif — 2026-11-12

- Source `video/logo/logo.wbm` :1280×720,302images,30000/1001fps (~29,97),PTS3ms→10,046s ;Vorbis natif,durée10,115s.
- Instruction utilisateur : upscale spatial seulement ; aucune interpolation ni passage30fps ; aucun Apollo lancé.
- Préparation/inférence réutilisées du run initial `video/logo/runs/logo-seedvr-apollo30-20261112-v1/` :1portion FFV1/302images,MD5 YUV420p source identiques,index temporaire30 uniquement pour SeedVR. Provenance : `jobs.json`, `production.json`, `native-frame-times.json`, `workflows/part-01.api.json`.
- SeedVR2 3B FP16 LAB1080,seed42,batch33/uniforme/overlap3,bruits0,SDPA,swap32,CPU offload,VAE encode1024/128/decode768/128. ProRes1920×1080/302images.
- `python pipeline/recipes/logo-seedvr-nativefps-20261112-v1/finish.py` :CPU seulement ;302images à30000/1001,base temps1/30000,setpts=N*1001,origine3ms. H264CRF12 ;MKV/Vorbis natif ;MP4/AAC192k ;WBM VP8CRF4/30M/qmax12/Vorbis natif. Audio non étiré.
- Contrôles :302images décodées/format,FPS/dimensions/PTS ≤1,1ms du natif ;audio MKV/WBM PCM/paquets/PTS identiques ;SSIM runtime échantillonné>0,99. Commandes/manifest sous `metadata/`.
- Résultats `video/final/logo-seedvr-nativefps-20261112-v1/LOGO/default/` ;manifeste `video/index/logo-finals-nativefps-20261112-v1.json` ;original de comparaison `video/previews/logo-comparison-20261112-v1/LOGO-original-720p2997.webm`,copie binaire source.
- Source déjà propre ;petites mentions légales :glyphes affinés/reformés par SeedVR,comparaison utilisateur requise. QA visuelle acceptée2026-11-12 ;installation locale effectuée,QA ingame en attente ;aucune intégration release.

- `install.py prepare` puis `install.py install` :jeu/InfinityLoader fermés ;original sauvegardé,remplacement atomique/SHA contrôlés vers `config://bg2ee_game_root/movies/logo.wbm` +alias neuf `movies/HDLOGO.wbm`. Reçu `video/index/logo-ingame-test-20261112-v1.json` ;QA `video/index/qa-decisions/LOGO/20261112-nativefps-visual-accepted-v1.json`.
- CLUA Ctrl+Espace en partie : `C:PlayMovie("HDLOGO")`.
- Restauration jeu/loader fermés :contrôler SHA actuel=`after_sha256` du reçu ;recopier `video/installations/logo-nativefps-20261112-v1/before/movies/logo.wbm` vers `config://bg2ee_game_root/movies/logo.wbm`,vérifier SHA=`before_sha256` ;retirer uniquement alias neuf `movies/HDLOGO.wbm` après contrôle SHA. Conserver sauvegarde/reçu.
