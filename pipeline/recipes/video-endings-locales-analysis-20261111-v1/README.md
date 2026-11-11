# END15FPS / MELISSAN — analyse multilingue, 2026-11-11 v1

- Bilan versionné : `docs/validation/video-endings-locales-analysis-20261111-v1.json` ; preuves locales : `video/research/endings-locales-analysis-20261111-v1/` (ignorées Git).
- 7 sources SHA256 conformes à `video/index/resources.csv`. END15FPS : défaut/DE/IT/PL ; MELISSAN : défaut/DE/PL. Aucun WBM français séparé dans l’installation inventoriée.
- END15FPS défaut/DE/IT : **1829/1829 images YUV420p et séquence complète de paquets VP8 strictement identiques**. MELISSAN défaut/DE : **525/525 images et séquence VP8 identiques**. Horodatages de départ légèrement différents ; fichiers complets différents.
- 7 pistes PCM distinctes ; Vorbis stéréo, défaut22050Hz, locales44100Hz. Aucun traitement audio requis, copie native possible.
- PL : END15FPS1827images, MELISSAN556images ; réencodage, mêmes scènes/cadrage observés, pas d’identité des pixels. END15FPS erreur luma160×90 après appariement : médiane1,24/255, max3,60. MELISSAN : différences de niveaux clairs, notamment pendant les flashes/fondu final ; ne pas assimiler à un plan traduit.
- Aucun texte/carton traduit repéré : appariement luma sur toutes les images, planches PL chaque seconde, revue RGB du pire résidu de8fenêtres temporelles par film. Revue visuelle échantillonnée, pas certification OCR exhaustive.
- MELISSAN PL : premières525images correspondant au contenu défaut, puis31images quasi fixes sur la fin blanche (~2,07s). Le DTW devient ambigu dans le fondu blanc ; ses répétitions finales ne représentent pas un changement de montage. Utiliser les indices du contenu puis un maintien final, à contrôler lors du montage.
- PTS0 dupliqué sur les2premières images des2PL. Ne pas convertir automatiquement les sources PL en CFR avant d’avoir enregistré les correspondances natives.

## Traitement minimal proposé

1. Masters muets défaut : END15FPS1829images (~121,93s), MELISSAN525images (35s). Une passe SeedVR + une passe Apollo30 par film ; aucune découpe linguistique ni ouverture séparée nécessaire.
2. Défaut/DE/IT compatibles : réutiliser le même master traité ; tenir compte du départ vidéo natif (END défaut12ms, DE/IT3ms ; MEL défaut0ms, DE3ms) et remuxer chaque piste native.
3. PL : même master, recalage temporel monotone par scènes/PTS natifs. Carte `*-to-default.csv` = diagnostic, pas montage approuvé ; contrôler les coupes, ne pas réutiliser aveuglément le DTW sur les fondus ou plans fixes. Rééchantillonner le master30 selon ce recalage, sans nouvelle interpolation IA. MELISSAN : prolonger l’image finale jusqu’à la fin vidéo native PL (~37,03s).
4. Le master partagé adopte l’apparence défaut ; si les niveaux de blanc propres au PL doivent être conservés, étalonnage déterministe après traitement. Aucun recadrage spécifique repéré.
5. Conserver Vorbis natif/PTS/queues audio ; MKV technique et WBM jeu, AAC seulement pour aperçu MP4. Ne pas employer `-shortest`, ne pas étirer l’audio ni prendre la durée conteneur comme durée visuelle.
6. Durées utiles : MEL dernière image défaut34,933s/DE34,936s, audio jusqu’à~37,11/37,24s ; PL dernière image36,967s, audio~37,10s. END PL durée conteneur122,901s mais dernière image121,779s et dernier paquet audio121,900s (~121,923s avec durée paquet) : tag conteneur insuffisant pour le montage.
7. À la production : contrôler coupes/recalage PL/fondu final, PCM et PTS audio identiques aux sources, nombres d’images/PTS/décodage des sorties. Aucune validation visuelle finale ou ingame déduite de cette analyse.

- Inférence spatiale :8920images pour7traitements séparés →2354images pour2masters, **−73,61%** (6566images évitées). Estimation d’entrées IA, pas benchmark GPU ; encodages/assemblages par langue restent nécessaires.
- Reproduction (nouvelle destination pour `extract.py`) : `extract.py`, `compare.py`, `review_alignment.py`, `analyze_tails.py`, `contact_sheets.py`. Exécuter avec `python -B pipeline/recipes/video-endings-locales-analysis-20261111-v1/<script>.py`.
- `extract.py`/`compare.py` adaptés de la recette intros20261110 ; `sources.json`, SHA image/paquet, probes, PTS, cartes CSV et planches conservés localement. Aucun rendu IA, installation ou release effectué ; suivi de production inchangé.
