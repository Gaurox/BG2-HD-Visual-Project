# DAYNITE — H3 01604 fondus corrigés → SeedVR1080 → Apollo30

- Demande2026-11-10 : FullHD1920×1080 + interpolation30fps + comparateur + son du DAYNITE original du jeu. Aucune installation ingame/release demandée.
- Entrée acceptée : `video/daynite/runs/daynite-minimax-h3-01604-fades-20261110-v1/DAYNITE-H3-01604-fondus-corriges-24fps-10s-v1.mp4`,1344×768/24fps/240frames. Source conservée.
- Ratio : `crop=1344:756:0:6` ;6lignes noires haut/bas retirées, aucun décor recadré ni déformé. MKV FFV1 sans perte ;240hashes de frames identiques après crop (`input-check.json`).
- Run : `video/daynite/runs/daynite-h3-01604-seedvr-apollo30-20261110-v1/` ; workflow exact ici et dans le run. ComfyUI MCP prompt `5d010aa8-6275-4a9d-aa3e-ecaec3ec50ef`, terminé ; MOV ProRes1920×1080/24fps/240frames.
- SeedVR2 node2.5.24 :3B FP16,VAE FP16,seed42,resolution1080,batch33uniforme,overlap3,prepend0,bruits0,LAB,swap32,SDPA,offloadCPU ; VAE encode1024/128,decode768/128,cachefalse. Identique aux essais retenus précédents.
- `finish.py` : conserve central SeedVR frames72..167 ; jour figé sur frame72,nuit sur168 ; fondus noirs reconstruits0..1/9..10s. Phases0–1 noir→jour,1–3jour,3–7jour→nuit,7–9nuit,9–10nuit→noir. Garantit noirs et plateaux après IA.
- Apollo Topaz `apo-8`,fps30,slowmo1,rdt−0,01,device0,vram0,8,download0 ;299images interpolées, puis1image finale noire pour300images/10s. Master FFV1 RGB16 temporaire supprimé après encodage/contrôles.
- Exports H264CRF16/slow,yuv420p,bt709 limité,trcIEC61966-2-1. Seed24=`DAYNITE-H3-01604-SeedVR2-1080p24-son-original-v1.mp4` ; final30=`DAYNITE-H3-01604-SeedVR2-Apollo8-1080p30-son-original-v1.mp4`.
- Son : `video/daynite/daynite.wbm` → AAC192k/22050Hz une seule fois dans le témoin16:9 ; copie des paquets identique versSeed24/final30. Aucune modification tempo ni coupe ; durée audio10,292s, vidéo10s puis noir tenu par le lecteur. Corrélation PCM alignée0,999848 ; décalage17ms correspondant au timestamp initial Vorbis, SNR35,06dB (`native-audio-check.json`).
- `verify.py` :1920×1080/240frames24 et300frames30 ; premiers/derniers pixels noirs exacts ;87/87intermédiaires testés distincts des voisins24 ; corrélation luminance24/30=0,999985 ; pas de remontée lumineuse centrale. Aperçu `final30-timeline.jpg`.
- `add_comparator.py` : trois choix des deux côtés (témoin16:9,Seed24,Seed+Apollo30), son original sur les trois ; final30 par défaut à droite, source du jeu à gauche. Anciennes versions conservées.
- État : comparaison prête, validation utilisateur finale en attente ; aucun fichier du jeu, staging ou release modifié. Rapports `production.json`, `verification.json`, `input-check.json`, `native-audio-check.json`.
