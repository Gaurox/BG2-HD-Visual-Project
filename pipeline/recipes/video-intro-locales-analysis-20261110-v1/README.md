# Intros multilingues — analyse native

- Bilan conservé : `docs/validation/video-intro-locales-analysis-20261110-v1.json`.
- Données/preuves locales : `video/research/intro-locales-analysis-20261110-v1/` ; README détaillé, SHA par image YUV, SHA paquets VP8, audio, PTS natifs, cartes d'appariement CSV et comparatifs JPEG. Caches miniatures `*.gray` ignorés ; sources natives inchangées.
-7fichiers présents : INTRO défaut/DE/PL ; INTRO15F défaut/DE/IT/PL. Pas de fichier français séparé dans cette installation. INTRO et INTRO15F sont2films distincts, pas2cadences du même film.
- Cartons d'Alaundo traduits : INTRO~0–7s, INTRO15F~0–18s, fenêtres conservatrices avec fondus. Bornes de montage à fixer exactement avant production.
- INTRO DE :3167/3345images natives retrouvées exactement ; après7s,3135/3135 alignées identiques. PL~15fps au lieu de~30, film réencodé, mêmes scènes ; erreur luma160×90 après recalage, médiane1,42/255 et max3,09 hors carton.
- INTRO15F DE/IT :2103/2574 et2111/2574images natives retrouvées ; après32,736s, images strictement identiques. Film avant cette borne légèrement différent par encodage (hors carton, erreur luma max1,64).
- INTRO15F PL : scènes communes, mais image4:3 centrale960×720 agrandie~4/3 vers1280×960 puis recadrée verticalement en1280×720. Revue RGB des6zones de plus gros résidu ; comparaison miniature sur tout le film. Pas d'identité de pixels certifiée ; pas d'autre carton traduit identifié après l'ouverture.
-7audios PCM distincts ; Vorbis stéréo, défaut22050Hz, locales44100Hz. Garder pistes/PTS/queues propres aux langues ; durées conteneur différentes ne signifient pas un changement de montage. Paquets VP8 invisibles ≠ images affichées.
- Proposition :2masters partagés, cartons traités séparément, variantes cadrage/PTS et audio natif. Décider si PL conserve son zoom ou adopte le4:3 complet. Contextes temporels/recouvrements pour SeedVR et interpolation, jointures contrôlées ; aucun nouveau rendu lancé.
- Estimation images IA :18707→7046 avec cartons supplémentaires, soit~62,3% en moins ; jusqu'à~68,3% si cartons recréés sans inférence. Pas un benchmark GPU ni une réduction garantie de taille livrée.
- Reproduction : `extract.py` (sortie neuve), `compare.py`, `inspect_frames.py`, `spatial.py`, `spatial_stretch.py`, `fit_geometry.py`, `review_polish.py`, `finalize.py`. `native_times.py` = complément ponctuel de la première extraction ; les nouvelles extractions incluent ces PTS.
- États production/QA/installation/release conservés ; analyse seule.
