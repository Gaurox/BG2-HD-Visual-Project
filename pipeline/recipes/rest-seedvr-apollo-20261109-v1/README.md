# REST — SeedVR FP16 LAB + Apollo30, comparaison seule

- Suite demandée après acceptation RESTINN ; aucune installation en jeu. REST complète la série de repos RESTDUNG/RESTINN/REST.
- Source : `video/rest/rest.wbm`,1280×720/15fps/180frames,12s. Remux WebM uploadé vérifié identique au flux natif (`source-check.json`).
- ComfyUI MCP : prompt `9885b349-7e77-4658-9f75-5fdd82ae2b06`. Workflow exact : `seedvr-workflow.api.json` ; profil identique RESTINN validé : SeedVR2 3B FP16,VAEFP16,LAB,seed42,1080,batch33uniforme,overlap3,bruits0,swap32,SDPA,offloadCPU ; VAE encode1024/128,decode768/128.
- Run : `video/rest/runs/rest-seedvr-apollo-20261109-v1/` ; `production.json` = commandes, hashes, contrôles.
- SeedVR15 : `REST-SeedVR2-3B-FP16-LAB-1080p15.mp4`,1920×1080/15fps/180frames ; audio source complet AAC192k.
- Apollo30 : `REST-SeedVR2-3B-FP16-LAB-Apollo8-1080p30.mp4`,1920×1080/30fps/359frames ; `apo-8`,slowmo1,rdt−0,01, pas de grain ni correction spatiale supplémentaire ; flux AAC copié depuis15 ; x264CRF16/slow.
- `finish.py` finalise les deux previews et vérifie cadence/nombre d'images/intermédiaires/audio ; `add_comparator.py` ajoute source/15/30 aux deux menus et ouvre REST par défaut, précédentes vidéos conservées.
- Master FFV1 temporaire supprimé après contrôles. QA utilisateur en attente ; aucun fichier jeu/installation/staging/release touché.
