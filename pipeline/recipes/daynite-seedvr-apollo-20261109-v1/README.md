# DAYNITE — SeedVR FP16 LAB + Apollo30, comparaison seule

- Courte suivante après validation REST :≈10,3s. Aucune installation en jeu.
- Source : `video/daynite/daynite.wbm`,1280×720/15fps/150frames. Rendu SeedVR existant : `video/daynite/runs/daynite-comfyui-experiment-20260814/ComfyUI_00003_.mp4`,1920×1080/15fps/150frames ; réutilisé sans réencoder son image.
- Recette exacte extraite des métadonnées : `seedvr-original-prompt.json`, `seedvr-original-workflow.json` ; SeedVR2node2.5.22,3B FP16,VAEFP16,LAB,seed42,1080,batch33uniforme,overlap3,bruits0,swap32,SDPA,offloadCPU ; VAE encode1024/128,decode768/128. Même profil historique que RESTDUNG retenu.
- Run : `video/daynite/runs/daynite-seedvr-apollo-20261109-v1/` ; `production.json` = commandes, hashes, contrôles et provenance du rendu existant.
- SeedVR15 : `DAYNITE-SeedVR2-3B-FP16-LAB-1080p15.mp4` ; audio source complet AAC192k remis sur l'image existante.
- Apollo30 : `DAYNITE-SeedVR2-3B-FP16-LAB-Apollo8-1080p30.mp4`,1920×1080/30fps/299frames ; `apo-8`,slowmo1,rdt−0,01 ; x264CRF16/slow ; flux AAC copié à l'identique depuis15.
- Contrôle :30/30 intermédiaires centraux différents des deux voisins ; ancres décodées écart moyen≈1,50/255 ; dimensions/cadence/comptage conformes. Master FFV1 temporaire supprimé après vérification.
- Comparateur : DAYNITE source à gauche et30fps à droite par défaut ;15/30 disponibles des deux côtés ; précédents films conservés.
- QA DAYNITE en attente utilisateur. Aucun fichier jeu/installation/staging/release modifié. Acceptation REST enregistrée sous `video/index/qa-decisions/REST/20261109-seedvr-apollo30-accepted-v1.json`.
