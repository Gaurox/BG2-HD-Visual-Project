# RESTINN — SeedVR FP16 LAB + Apollo30, comparaison seule

- Demande2026-11-09 : appliquer SeedVR+interpolation après validation RESTDUNG30 ; aucune installation en jeu.
- Source : `video/restinn/restinn.wbm`, 1280×720/15fps/90frames ; WebM historique uploadé vérifié identique au flux vidéo natif (`source-upload-check.json`).
- ComfyUI MCP : prompt `11649285-9251-4cef-ad69-168920135b1e` ; SeedVR2 node2.5.24, mêmes réglages que RESTDUNG retenu :3B FP16, VAEFP16, seed42, LAB,1080,batch33uniforme,overlap3,bruits0,swap32,SDPA,offloadCPU ; VAE encode1024/128,decode768/128.
- Workflow exact conservé ici et dans le run : `seedvr-workflow.api.json`. Adaptation SaveVideo au schéma dynamique actuel (`format.codec=h264`, CRF16) ; pas de modification des réglages d'inférence.
- Run : `video/restinn/runs/restinn-seedvr-apollo-20261109-v1/` ; rapport `production.json` avec commandes, paramètres, hashes et contrôles.
- SeedVR15 : `RESTINN-SeedVR2-3B-FP16-LAB-1080p15.mp4`,1920×1080/15fps/90frames ; image copiée du rendu ComfyUI, audio source complet remuxé en AAC192k.
- Final30 : `RESTINN-SeedVR2-3B-FP16-LAB-Apollo8-1080p30.mp4`,1920×1080/30fps/179frames ; Topaz `apo-8`,slowmo1,rdt−0,01. Même chaîne que RESTDUNG30 validé ; flux AAC copié à l'identique entre15/30.
- Contrôle :30/30 intermédiaires centraux distincts des deux voisins ; écart moyen ancres décodées≈0,884/255 ; aucune validation visuelle utilisateur déduite. Master FFV1 temporaire supprimé après contrôles pour limiter la place.
- Aperçu source : `video/restinn/source-preview-720p15.mp4`. Comparateur `video/tools/comparator.html` : RESTINN source à gauche par défaut, SeedVR+Apollo30 à droite ;15/30 disponibles des deux côtés ; RESTDUNG reste disponible.
- QA RESTINN en attente utilisateur. Aucun fichier de jeu, installation, staging ou release modifié. RESTDUNG30 accepté séparément sous `video/index/qa-decisions/RESTDUNG/20261109-seedvr-apollo30-accepted-v1.json` ; installation RESTDUNG15 inchangée.
