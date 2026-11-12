# ENDCRDIT — T1 Proteus neutre + Apollo30,2026-11-12

- Choix utilisateur :« on garde T1. fais le traitement complet T1 + interpolation 30 fps ». T1 accepté sur0–5s ;compléments/7B non sélectionnés. Film complet et interpolation restent soumis à revue finale.
- Source `video/endcrdit/endcrdit.wbm`,1280×720/15fps,2001images,durée133,451s. Source/SHA inventaire vérifiés ;méthode T1 exacte :conversion bt601 limited→RGB16 full,Proteus `prob-4` neutre x2/2560×1440,puis Lanczos1920×1080 ;grain0,estimate0,GPU0/vram0.8/instances0/download0.
- `spatial.py` :décodage standard →Topaz →H264CRF12 medium en pipes RGB16 sans stockage intermédiaire massif ;source0–fin,aucune passe SeedVR. Export spatialFullHD15 bt709 limited ;journaux/commandes/probe/SHA sous run.
- `finish.py` :Apollo8 `apo-8`,30fps/slowmo1/rdt=-0.01,GPU0,vram0.8 ;4001images générées+1tenue ;2tenues supplémentaires pour couvrir audio natif complet →4004images/133,4667s. Matrice couleur bt709 conservée ;origine PTS native restaurée au muxage.
- Livrables MP4 H264/AAC192k,MKV H264/Vorbis natif,WBM VP8CRF4/30M/qmax12/Vorbis natif ;aucun étirement/troncature audio. Vérifications :décodage3formats,comptes/FPS/dimensions/PTS,audio PCM+paquets+PTS identiques MKV/WBM,SSIM runtime échantillonné>0,99,images interpolées non dupliquées.
- Run `video/endcrdit/runs/endcrdit-proteus-T1-apollo30-20261112-v1/` ;finaux `video/final/endcrdit-proteus-T1-apollo30-20261112-v1/ENDCRDIT/default/` ;index `video/index/endcrdit-proteus-T1-finals30-20261112-v1.json` créé après vérifications seulement.
- Ancien préfixe SeedVR rejeté/checkpoint de pause conservés comme historique,non utilisés. Aucune installation/release ;QA visuelle film complet30fps en attente.

- Résultat :4004images/30fps ;2000images intermédiaires testées non dupliquées ;audio PCM/flux/PTS natif identique MKV/WBM ;SSIM WBM échantillonné0.990746 ;écart maximal PTS vidéo<1.1ms. Préfixe spatial4s vsT1 accepté :SSIM0.998797. `record.py` publie production/suivi après manifeste,QA complète reste en attente.

## Installation/validation2026-11-12

- Film complet validé utilisateur ;QA visuelle `video/index/qa-decisions/ENDCRDIT/20261112-fullhd30-visual-accepted-v1.json`. QA ingame considérée acceptée sur instruction explicite (aucun test de jeu observé par agent) : `20261112-fullhd30-ingame-accepted-v1.json` dans le même dossier. Ces décisions succèdent aux états pending des preuves de production immuables ci-dessus.
- `install.py prepare` puis `install.py install` :jeu/InfinityLoader fermés,original sauvegardé,SHA vérifiés,remplacement atomique `config://bg2ee_game_root/movies/endcrdit.wbm` +alias neuf `movies/HDENDCRD.wbm`. Reçu : `video/index/endcrdit-ingame-test-20261112-v1.json`,copie `metadata/installation.json`. Aucune intégration release.
- CLUA Ctrl+Espace en partie : `C:PlayMovie("HDENDCRD")`.
- Restauration jeu/loader fermés :SHA installé=`after_sha256` ;recopier `video/installations/endcrdit-proteus-T1-apollo30-20261112-v1/before/movies/endcrdit.wbm` vers `config://bg2ee_game_root/movies/endcrdit.wbm`,vérifier SHA=`before_sha256` ;retirer uniquement alias neuf `movies/HDENDCRD.wbm` après contrôle SHA. Conserver sauvegarde/reçu.
