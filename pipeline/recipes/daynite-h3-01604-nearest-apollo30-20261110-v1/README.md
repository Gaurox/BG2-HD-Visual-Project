# DAYNITE H3 01604 — nearest FullHD, son original, Apollo30

- Demande2026-11-10 : utilisateur juge le post-traitement SeedVR dégradant ; refaire l'upscale nearest en1920×1080 avec son original. Cadence30 conservée ; témoin nearest24 ajouté pour isoler l'interpolation.
- Entrée : `video/daynite/runs/daynite-h3-01604-seedvr-apollo30-20261110-v1/DAYNITE-H3-01604-corrected-16x9-input-v1.mkv` = uniquement le crop sans perte du H3 aux fondus corrigés, AVANT SeedVR.1344×756/24fps/240frames ; aucun rendu post-SeedVR réutilisé.
- Run : `video/daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1/` ; `produce.py`, `verify.py`, `add_comparator.py`.
- Upscale : FFmpeg `scale=1920:1080:flags=neighbor,format=yuv420p` ; H264CRF14/slow,bt709 limité,trcIEC61966-2-1 ; aucun modèle de restauration ni netteté ajouté.
-24 : `DAYNITE-H3-01604-NEAREST-1080p24-son-original-v1.mp4`,240frames/10s.30 : `DAYNITE-H3-01604-NEAREST-Apollo8-1080p30-son-original-v1.mp4`,300frames/10s.
- Interpolation seule : Topaz `apo-8`,fps30,slowmo1,rdt−0,01,device0,vram0,8 ;299images +1noire finale ; master FFV1RGB16 temporaire supprimé après encodage/contrôles.
- Son du jeu `video/daynite/daynite.wbm` : paquets AAC copiés depuis le témoin16:9 déjà vérifié ; hashes identiques témoin/nearest24/nearest30. Aucune coupe ni modification tempo ; fin audio complète≈10,292s après noir vidéo10s.
- Contrôles :1920×1080,240/300frames ; premiers/derniers pixels noirs exacts ;87/87intermédiaires testés distincts des voisins24 ; luminance24/30 corrélation0,999985 ; aucune remontée lumineuse centrale. Rapports `production.json`, `verification.json`, aperçu `final30-timeline.jpg`.
- Comparateur : nearest30 par défaut à droite, nearest24 aussi disponible des deux côtés ; versions SeedVR conservées pour comparaison. QA finale en attente utilisateur ; aucun fichier ingame/release modifié.
- Suite2026-11-10 : nearest30 sélectionné pour test local et installé via `../daynite-h3-nearest-ingame-20261110-v1/` ; reçu `video/installations/daynite-h3-nearest-20261110-v1/installation.json`. QA ingame en attente, aucune intégration release.
