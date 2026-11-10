# Suivi vidéo — 2026-11-10

- Autorités : sources=`index/resources.csv` ; production/sélections=`index/processing.csv` ; QA=`index/qa-decisions/` ; installation=`installations/*/installation.json` ; release séparée.
- Vue complète50assets : `index/status.csv` ;50sources natives présentes,37cinématiques+13tutoriels.7productions conservées,43assets sans production sélectionnée. Aucun asset vidéo intégré à la release.

| Vidéo | Production conservée | QA | Installation locale |
|---|---|---|---|
| DEATHAND | SeedVR LAB15 → Apollo8 FullHD30, MP4 parent + MOV final | méthode validée2026-08-31 ; livraison/QA asset non définies | non |
| FLYTHR03 | SeedVR LAB15 → Apollo8 FullHD30, MP4 parent + MOV final | méthode validée2026-08-31 ; livraison/QA asset non définies | non |
| RESTDUNG | SeedVR FP16 LAB15 → Apollo8 FullHD30 | comparaison15/30 acceptée | WBM15 ; test ingame en attente |
| RESTINN | SeedVR FP16 LAB15 → Apollo8 FullHD30 | comparaison acceptée | non |
| REST | SeedVR FP16 LAB15 → Apollo8 FullHD30 | comparaison acceptée | non |
| DAYNITE | H3 01604 → fondus10s → nearest FullHD24 → Apollo8 FullHD30 + son natif | sélection pour test local ; post-SeedVR rejeté ; ancienne vidéo signalée ingame | WBM30 présent et SHA conforme ; anomalie ingame non résolue |
| POCKETZZ | `pocketzz/runs/pocketzz-comfyui-experiments-20260814/ComfyUI_00002_.mp4`,SeedVR FP16 LAB FullHD15 | candidat gardé explicitement ; pas de validation | non |

## DAYNITE — chaîne conservée

`daynite.wbm` + SeedVR historique → frames30/114 à2/7,6s → imagesT2 → nuitT2 conservée + jourT4 généré depuis sa géométrie → H3 `MiniMax_H3_01604_-original.mp4` → `rebuild.py`/fondus corrigés → crop6lignes noires haut/bas → nearest1920×1080 → Apollo8/30fps → WBM VP8/Vorbis installé.

- Le graphe embarqué du H3 confirme les deux imagesT4 en entrée ; prompt exact conservé sous `../pipeline/recipes/video-retained-cleanup-20261110-v1/retained-h3-01604-prompt.api.json`.
- Entrées nearest relocalisées dans `daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1/` : MKV crop sans perte + AAC original extrait sans réencodage.
- ImagesT2/T4, sourceH3, montage, inputs nearest, nearest24, final30 et WBM installable conservés ; T1/T3, sens inverse, H3 antérieur et post-upscale SeedVR supprimés.

## Diagnostic ingame DAYNITE

- Retour utilisateur2026-11-10 : ancienne vidéo visible ; QA=`index/qa-decisions/daynite-ingame-old-video-reported-20261110-v1.json`.
- WBM installé conforme au SHA du runtime retenu ; aucun doublon prioritaire trouvé ; logs sans identifiant de film.
- Accès Computer Use/Baldur refusé : reproduction bloquée ; aucun nouveau remplacement spéculatif. Diagnostic/reprise=`../pipeline/recipes/daynite-runtime-diagnosis-20261110-v1/README.md`.

## Nettoyage global

-467fichiers supprimés,4 680 715 222octets ; gain net≈4,27Gio après relocalisation des entrées utiles et archivage des réglages.
- Essais FLYTHR03 nonLAB/Chronos/Aion, branches DAYNITE écartées,270frames et4MP4 POCKETZZ,36conversions WebM historiques et captures temporaires supprimés.
-50sources natives, résultats retenus, parents nécessaires et sauvegardes installées vérifiés par SHA256 ; aucun fichier du jeu ou de release modifié pendant ce nettoyage.
- Mémoire/réglages : `../pipeline/recipes/video-retained-cleanup-20261110-v1/settings-memory/` ; plan/reçu=`plan.json`/`cleanup.json` ; médias conservés et alias de chemins=`index/retained-media-20261110-v1.json`.
- Les run.json historiques archivés gardent leurs chemins et octets originaux ; les chemins retirés ne sont pas des productions manquantes à régénérer.
- Comparateur : `tools/comparator.html` ; uniquement sources, résultats retenus et étapes utiles encore présentes.
