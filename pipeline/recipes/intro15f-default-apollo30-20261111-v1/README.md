# INTRO15F défaut — Apollo8 30fps, 2026-11-11 v1

- Demande : uniquement défaut pour contrôle ; autres langues conditionnées à son acceptation.
- Source assemblée : `video/assembly/intro15f-locales-seedvr-1080-20261111-v1/default/INTRO15F-default-SeedVR2-1080-audio.mp4`,1080p15/2574images ; aucun nouvel upscale.
- Commande : `python -B pipeline/recipes/intro15f-default-apollo30-20261111-v1/produce.py` ; chemins Topaz/modèles via `config://topaz_video_ffmpeg`, `config://topaz_video_models`.
- Apollo8 `apo-8:fps=30:slowmo=1:rdt=-0.01:device=0:vram=0.8:instances=0:download=0` ; RGB24 entrée, GBR16 sortie transmise par pipe à FFmpeg standard ; pas de cache RGB massif.
- Sortie `video/intro15f/runs/intro15f-default-apollo30-20261111-v1/INTRO15F-default-SeedVR2-Apollo8-1080p30-audio.mp4` : H264 CRF14/slow,yuv420p,1080p30,5148images/171.6s vidéo ; origine vidéo native conservée. Dernière image tenue1/30s pour conserver la durée après sortie2N−1 d’Apollo.
- Audio AAC de l’aperçu15fps copié sans réencodage ; hash paquets et PTS vérifiés. Master15fps Vorbis natif inchangé.
- `production.json` local : commandes exactes,SHA/probes,contrôle images intermédiaires40–42s,audio ; `check-*.png` : carton,raccord,plans40/100/160s. Métadonnées finales copiées dans `metadata/`.
- Défaut accepté : `video/index/qa-decisions/INTRO15F/20261111-default-apollo30-accepted-v1.json` ;3autres locales produites ensuite avec `produce.py --locale <de_DE|it_IT|pl_PL>` et regroupées dans `../intro-finals30-20261111-v1/README.md`. Installation séparée : `video/index/intro15f-ingame-test-20261111-v1.json` ; QA ingame en attente, aucune release. Métadonnées originales de l’essai défaut conservées.
