# Intros — SeedVR natif, 2026-11-11 v1

- Suivi/empreintes : `video/index/intro-seedvr-20261111-v1.json` ; décision utilisateur : `video/index/qa-decisions/INTRO/20261111-seedvr-native-fps-common-accepted-v1.json`.
- Médias locaux ignorés par Git ; aucune copie binaire dans ce commit. Sources natives et analyse20261110 inchangées. Aucun jeu/staging/release modifié.
- Production : 7 ouvertures, 1 corps commun INTRO, 3 assemblages INTRO avec leurs audios. Corps commun INTRO15F **non commencé** ; ses 4 ouvertures seules sont produites.
- Pas de source FR séparée dans l'installation ; utilisateur a choisi la comparaison du fichier commun original/traité. Aucun doublage/traduction ajouté.

## Réglages et découpe

- SeedVR2 installé2.5.24 : DiT3B FP16, VAE FP16, LAB, seed42, sortie1920×1080, batch33 uniforme, overlap3, prepend0, bruits0, SDPA, swap32, offloadCPU ; VAE encode1024/128, decode768/128.
- **Aucune interpolation**. INTRO défaut/DE ≈29,97fps ; PL ≈15fps avec PTS natifs ; INTRO15F ouvertures ≈15fps. Ne pas confondre le fondu de deux rendus du même instant avec une génération d'images intermédiaires.
- Préparation : `video/preparation/intro-localized-segments-20261111-v1/<film>/<locale>/` ; FFV1 natif, PTS/indices/SHA par image dans `frames.csv` ; INTRO0–8s, INTRO15F0–19s, dont courte queue commune pour raccord.
- Ouvertures : `video/experiments/intro-openings-seedvr3b-1080-20261111-v1/` ; `intro15f-default-seedvr3b-1080-20261111-v1/` ; `intro15f-locales-seedvr3b-1080-20261111-v1/`.

## Corps commun et assemblage

- Corps INTRO : `video/experiments/intro-common-seedvr3b-stream-1080-20261111-v1/` ; source défaut images210..3346, PTS7.019..111.656s ; 3137images,104.671233s. Entrée décodée strictement identique aux SHA natifs.
- CLI streaming330 images/portion,10portions, contexte précédent3 ; cache DiT/VAE actif ; `run.json` = commande effective et tentatives ; `portions/` = sorties intermédiaires.
- Correctifs locaux au processus : disponibilité Flash Attention désactivée pour contourner métadonnées Transformers absentes (backend réel SDPA) ; export RGB→uint8 par groupes8 au lieu d'une copie float32 de330images ; portions finalisées puis concaténées sans réencodage. Installation ComfyUI/dépendances inchangée.
- Assemblages : `video/assembly/intro-locales-seedvr-1080-20261111-v1/<locale>/` ; cartes `INTRO-*-to-default.csv` de l'analyse native ; fondu de deux rendus **alignés sur la même image** dans le chevauchement : défaut210..239, DE208..239, PL105..120.
- Comptes finaux : défaut3347,DE3345,PL1721 ; ordre et PTS natifs conservés (écart master ≤1ms ; PL timestamps exacts). PL utilise un arbre d'expressions PTS équilibré dans `native-pts.filter`, car une cadence moyenne dérive d'environ10ms sur le film complet.
- Master MKV H264CRF12 + Vorbis copié : PCM strictement identique à chaque source ; pas de coupe/étirement des queues audio. MP4 de lecture : vidéo copiée, AAC192k ; aperçu original/traité utilise le même AAC.
- Comparaison retenue : `default/original-vs-seedvr.html`, aperçu source `INTRO-original-720-audio-v2.mp4` (PTS microseconde) et résultat `INTRO-default-SeedVR2-1080-audio.mp4`. Ancien aperçu/tentative PL non sélectionnés.
- QA : comparaison commune acceptée utilisateur (« parfait ! comitte tout ca ») ; pas de QA ingame/release. Ne pas déduire une revue visuelle séparée des autres langues.

## Code et reprise

- Scripts : `pipeline/recipes/video-intro-locales-analysis-20261110-v1/{prepare_segments,finish_seedvr_openings,finish_seedvr_intro15f,run_intro_common_stream,seedvr_cli_bootstrap,intro_stream_progress,finish_intro_common_stream,assemble_intro_locales}.py`.
- Chemins machine du CLI : `config://comfyui_root`, `config://comfyui_python`, `config://seedvr_models` ; valeurs dans override local ignoré ou variables d'environnement déclarées dans `config/workspace-paths.json`.
- Les producteurs figent un identifiant daté et refusent les sorties existantes : choisir une nouvelle version avant relance, ne pas écraser les résultats acceptés. `assemble_intro_locales.py --resume` sert uniquement à reprendre une production incomplète.
- Prochaine production demandée : corps commun INTRO15F, après décision utilisateur. L'interpolation éventuelle doit être une variante séparée, sans remplacer ces références natives.
