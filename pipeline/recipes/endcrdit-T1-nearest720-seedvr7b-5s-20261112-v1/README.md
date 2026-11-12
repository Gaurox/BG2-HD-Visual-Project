# ENDCRDIT — T1 nearest720 puis SeedVR7B,2026-11-12

- Demande explicite utilisateur :T1 accepté →1280×720 nearest →SeedVR7B ;extrait0–5s seulement.
- `prepare.py` :T1 MP4 accepté/SHA vérifié →FFV1 YUV420p nearest1280×720 ;MD5 de chaque image redimensionnée identique au FFV1.75images/15fps conservées ;aucune interpolation.
- ComfyUI local8188/RTX5090 :SeedVR2 **7B FP16**,VAE FP16 ;FullHD1080,seed42,LAB,batch17 uniforme,overlap3,bruits0,SDPA,swap36/CPU,VAE encode1024/128 decode768/128,cachefalse. Modèles installés réutilisés ;aucun téléchargement/mise à jour.
- Workflow `workflow.api.json` ;préparation/job sous `metadata/` ;médias `video/endcrdit/runs/endcrdit-T1-nearest720-seedvr7b-5s-20261112-v1/`.
- Sortie Comfy MOV/ProRes →MP4 H264CRF12 avec audio AAC T1 copié ;75images1920×1080/15fps à vérifier. Comparaison avec T1 exact ;QA du nouveau candidat en attente.
- Source T1/première passe validée et historique SeedVR rejeté inchangés ;aucune reprise intégrale/installation/release.

- Décision finale utilisateur2026-11-12 :T1 seul retenu pour production complète +Apollo30 ;secondes passes/SeedVR7B non sélectionnés. [Production/install/QA courantes](../endcrdit-proteus-T1-apollo30-20261112-v1/README.md). Les états pending des rapports expérimentaux restent des instantanés historiques.
