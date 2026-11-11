# INTRO15F — corps commun SeedVR, 2026-11-11 v1

- Demande : traiter tout le corps commun ; montrer la première portion puis continuer ; première portion acceptée (« validé. continue jusqu'aubout »).
- Suivi : `video/index/intro15f-common-seedvr-20261111-v1.json` ; QA limitée aux22premières secondes : `video/index/qa-decisions/INTRO15F/20261111-shared-body-first-portion-accepted-v1.json`.
- Source `video/intro15f/intro15f.wbm`, images270..2573, PTS18.012..171.545s ;2304images,153.6s à15fps. Entrée FFV1 vérifiée contre les SHA YUV natifs. Ouvertures localisées jusque19s déjà disponibles.
- Profil identique au premier film : SeedVR2 3B FP16/VAE FP16,LAB,1080,seed42,batch33 uniforme,overlap3,bruits0,SDPA,swap32,offloadCPU ; VAE encode1024/128 et decode768/128.
-7portions330images maximum, cache modèles actif ; exports par groupes8 et portions finalisées individuellement, puis concaténation sans réencodage. Aucune interpolation, aucune reconstruction audio dans le master commun.
- Run local : `video/experiments/intro15f-common-seedvr3b-stream-1080-20261111-v1/` ; `run.json`, `frames.csv`, `seedvr-stream.log`, `portions/INTRO15F-common-part-*.mp4`.
- Commandes : `python -B pipeline/recipes/video-intro-locales-analysis-20261110-v1/run_intro_common_stream.py --film INTRO15F` ; progression : `intro_stream_progress.py --film INTRO15F` ; finition : `finish_intro_common_stream.py --film INTRO15F`. Les producteurs refusent une destination existante : utiliser une nouvelle version pour relancer.
- Assemblages linguistiques INTRO15F non commencés ; cadrage final PL toujours à décider. Aucun fichier INTRO15F du jeu ni manifeste release modifié. Installation des3INTRO menée séparément sous `intro-ingame-test-20261111-v1`.
