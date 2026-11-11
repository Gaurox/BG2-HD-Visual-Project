# INTRO polonais — réassemblage master30, 2026-11-11 v1

- Demande : reprendre les images disponibles du master commun, conserver l'audio polonais synchronisé, sans interpolation IA.
- Sorties : `video/assembly/intro-polish-master30-20261111-v1/` ; sélection technique/empreintes : `video/index/intro-polish-master30-20261111-v1.json` ; ancien assemblage natif~15fps inchangé.
- Cadence exacte **30000/1001**, identique au master (~30fps nominales) ;1920×1080,3440slots,114.781333s d'image. Audio complet et queue conservés.
- Ouverture PL existante~15fps : maintiens, aucun nouveau dessin ; bascule au master à6.9069s.3137images du master toutes utilisées dans l'ordre, aucune supprimée ;96maintiens supplémentaires de calage dans le corps commun.
- Calage : `INTRO-pl_PL-to-default.csv` natif → chronologie30 → chemin monotone à avances0/1 minimisant l'écart d'appariement. Interpolation d'indices/temps uniquement ; **aucune synthèse ou fusion de pixels**. `frame-map.csv` indique l'image réelle de chaque slot.
- Vérification : tous les indices master0..3136 présents ; comparaison luma native160×90 aux ancrages polonais visibles, erreur médiane1.428/255,max2.363/255. Diagnostic de correspondance visuelle, pas preuve de lip-sync.
- Audio master : Vorbis copié sans coupe/étirement ; PCM et8874PTS de paquets strictement identiques à la source. MP4 navigateur : vidéo copiée, AAC192k. Un seul encodage vidéo H264CRF12/medium.
- `render.py` reproduit vers une destination neuve ; refuse l'écrasement. Aucun SeedVR/Apollo lancé ; aucune modification DE/défaut/INTRO15F, du jeu ou de la release. Comparaison acceptée utilisateur (« ok propre committe ce travail ») ; décision immuable sous `video/index/qa-decisions/INTRO/20261111-polish-shared-master30-accepted-v1.json`.
