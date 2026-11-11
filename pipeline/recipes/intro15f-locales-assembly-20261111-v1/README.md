# INTRO15F — assemblages localisés 2026-11-11 v1

- Commande : `python -B pipeline/recipes/video-intro-locales-analysis-20261110-v1/assemble_intro15f_locales.py` ; destination `video/assembly/intro15f-locales-seedvr-1080-20261111-v1/{default,de_DE,it_IT,pl_PL}/`.
- Entrées : ouvertures SeedVR1080 existantes (~19s) + master commun1080/15fps accepté (`video/index/qa-decisions/INTRO15F/20261111-shared-body-full-accepted-v1.json`). Aucun nouveau passage IA ni interpolation.
- Chronologie : PTS natifs explicites par image ; appariements CSV analyse20261110, variante `-fitted` PL ; fondu linéaire entre mêmes instants alignés du chevauchement ~18–19s. CSV de montage conservé dans chaque dossier local.
- Cadrage natif conservé : défaut/DE/IT image4:3 avec bandes latérales ; PL crop1440×1080 centré dans le master1920×1080 → Lanczos1920×1440 → crop1920×1080 centré. Même zoom4/3 que la source polonaise ; aucune nouvelle QA déduite de cette transformation.
- Masters `INTRO15F-<locale>-SeedVR2-1080-native-audio.mkv` : H264 CRF12/medium + Vorbis source copié, audio complet sans étirement/coupe. Vérifications : SHA PCM exact, nombre/PTS paquets audio, nombre/dimensions/PTS de toutes les images.
- Lecture `INTRO15F-<locale>-SeedVR2-1080-audio.mp4` : vidéo copiée du MKV, AAC192k, faststart. `check-*.png` : raccord17.9/18.5/19.2s et plan65s. Aucun comparateur demandé.
- Résultats : `video/index/intro15f-locales-assembly-20261111-v1.json` ; métadonnées de montage copiées sous `metadata/`. QA des quatre assemblages en attente du contrôle utilisateur ; aucune installation INTRO15F ni intégration release.
- Les trois INTRO existants ne sont pas réencodés : défaut/DE assemblage `intro-locales-seedvr-1080-20261111-v1` ; PL variante acceptée `intro-polish-master30-20261111-v1`. Les sept chemins de lecture sont regroupés dans `video/index/intro-review-files-20261111-v1.json`.
