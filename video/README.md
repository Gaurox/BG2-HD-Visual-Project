# Vidéos BG2EE

`index/manifest.json` et `index/resources.csv` constituent l'inventaire canonique des
cinématiques WBM libres et des tutoriels WBM du KEY/BIF. Les WBM utilisés comme animations de
zone restent sous l'autorité de `animations/index/occurrences.csv` et sont exclus ici.

`index/processing.csv` sélectionne les runs validés par étape et le run utilisé par le patch.
`patch_run` vide signifie qu'aucun artefact vidéo n'est intégré au patch.

END15FPS/MELISSAN finales2026-11-11 : **7versions FullHD30 validées ingame le2026-11-11**,2masters SeedVR FP16 LAB/Apollo8 partagés, audios natifs et timings PL adaptés ; décision : `index/qa-decisions/endings-ingame-accepted-20261111-v1.json`. Production : `index/endings-finals30-20261111-v1.json` ; installation : `index/endings-ingame-test-20261111-v1.json` ; [console et restauration](../pipeline/recipes/endings-shared-30fps-20261111-v1/README.md). Aucune intégration release.

Intros finales2026-11-11 : **7ensembles FullHD prêts techniquement pour installation future** :
`index/intro-finals30-20261111-v1.json` ; chemins lecture/jeu : `index/intro-review-files-20261111-v1.json`.
Local : `video/final/intro-30fps-20261111-v1/{INTRO,INTRO15F}/<locale>/` ; MP4 AAC de contrôle,
MKV H264/Vorbis natif, WBM VP8/Vorbis natif destiné au jeu. Native PCM/PTS audio vérifiés,
décodage complet/PTS vidéo/nombres d’images contrôlés ; SSIM échantillonné runtime >0.99.
INTRO défaut/DE/PL :30000/1001 (~29.97fps), fichiers acceptés existants réutilisés ; PL = master30,
carton natif tenu, aucune interpolation IA. INTRO15F défaut/DE/IT/PL :30/1 après Apollo8 ; défaut
et3autres variantes acceptés en revue visuelle ; décision groupée `index/qa-decisions/INTRO15F/20261111-four-apollo30-assemblies-accepted-v1.json`. Master partagé INTRO15F accepté ; les PTS
polonais irréguliers sont restaurés avant grille30fps, audio non étiré. Recettes :
[`intros finales30`](../pipeline/recipes/intro-finals30-20261111-v1/README.md),
[`assemblage INTRO15F`](../pipeline/recipes/intro15f-locales-assembly-20261111-v1/README.md).
Test local des3INTRO déjà installé : `index/intro-ingame-test-20261111-v1.json` ; sauvegardes
`installations/intro-locales-seedvr-20261111-v1/before/` ; alias `HDINEN`/`HDINDE`/`HDINPL`.
4INTRO15F installées pour test local : `index/intro15f-ingame-test-20261111-v1.json` ; sauvegardes
`installations/intro15f-apollo30-20261111-v1/before/` ; alias `HD15EN`/`HD15DE`/`HD15IT`/`HD15PL`.
[Console/restauration](../pipeline/recipes/intro15f-ingame-test-20261111-v1/README.md). QA ingame reste en attente ; aucune intégration release.
Sources/runs précédents conservés ; médias locaux ignorés par Git.

Périmètre production :37cinématiques ;13tutoriels exclus sur demande utilisateur2026-11-11,
`index/production-scope.json`. Ne pas réintroduire les tutoriels dans le suivi ou une file de traitement.
Inventaire source50assets et fichiers tutoriels conservés.
Suivi courant : [`SUIVI.md`](SUIVI.md) ; vue37cinématiques : `index/status.csv` ; médias réellement
conservés et alias des entrées déplacées : `index/retained-media-20261110-v1.json`.

RESTDUNG : SeedVR2 3B FP16 LAB Full HD15 retenu le 2026-11-09 ; installé localement en WBM
VP8/Vorbis, QA ingame en attente. Sélection : `index/qa-decisions/RESTDUNG/` ; reçu :
`installations/restdung-seedvr-20261109-v1/installation.json`. Réglages des essais supprimés et
restauration : [`mémoire RESTDUNG`](../pipeline/recipes/restdung-seedvr-selected-20261109-v1/README.md).

RESTDUNG30 et RESTINN SeedVR15/Apollo30 acceptés en comparaison ; décisions immuables sous
`index/qa-decisions/`. RESTINN n'est pas installé. Recette :
[`RESTINN SeedVR + Apollo`](../pipeline/recipes/restinn-seedvr-apollo-20261109-v1/README.md).

REST SeedVR15/Apollo30 accepté en comparaison ; décision sous `index/qa-decisions/REST/` ;
aucune installation. Recette : `../pipeline/recipes/rest-seedvr-apollo-20261109-v1/`.

DAYNITE : H3 01604 remonte10s/fondus corrigés → nearest1920×1080 → Apollo8/30fps, son natif.
Sélection pour test local2026-11-10 : `index/qa-decisions/DAYNITE/` ; installé uniquement dans
`movies/daynite.wbm`, QA ingame en attente. Reçu/sauvegarde :
`installations/daynite-h3-nearest-20261110-v1/installation.json` ; recette/restauration :
`../pipeline/recipes/daynite-h3-nearest-ingame-20261110-v1/`. Aucune intégration release.
La chaîne DAYNITE conserve imagesT2/T4, sourceH3, montage, inputs crop/audio, nearest24/30 et WBM.
Le post-upscale SeedVR sur H3 a été jugé dégradant par l'utilisateur ; ses médias, les essais
direct/inverse et T1/T3 ont été supprimés. Réglages/logs historiques :
`../pipeline/recipes/video-retained-cleanup-20261110-v1/settings-memory/`.

Nettoyage2026-11-10 :467fichiers supprimés (gain net≈4,27Gio),50sources et sauvegardes conservées.
POCKETZZ : seul candidat SeedVR FullHD15 gardé explicitement, aucune validation déduite.
Comparateur `tools/comparator.html` : uniquement sources/résultats retenus/étapes encore utiles.

## Organisation

```text
video/<asset>/
├── <source>.wbm
└── runs/<run-id>/
```

Interdit : nouveau run sous `video/runs/`. Un déplacement historique ne modifie pas le
`run.json` scellé ; les outils résolvent son ancien préfixe vers le dossier asset.

Les sous-dossiers contenant les WBM extraits sont des copies locales ignorées par Git. Régénérer
et contrôler l'inventaire avec les commandes décrites dans
[`../docs/GRAPHICS_INVENTORY.md`](../docs/GRAPHICS_INVENTORY.md).

## Upscale spatial LAB v2

| Élément | Autorité |
|---|---|
| Recette | `../pipeline/comfyui/workflows/SeedVR-Video-BG2-3B-INT8-1080p-LAB-v2.api.json` |
| Runner | `../pipeline/scripts/run_video_upscale.py` |
| Procédure | [`../pipeline/VIDEO_UPSCALE_PIPELINE.md`](../pipeline/VIDEO_UPSCALE_PIPELINE.md) |
| Run | `<asset>/runs/<run-id>/run.json` conforme à `../docs/workspace-run.schema.json` |

La recette LAB v2 couvre uniquement les cinématiques 1280×720 vers 1920×1080. Elle conserve
cadence et nombre d'images. Les tutoriels 384×480 sont refusés.

```powershell
python pipeline/scripts/run_video_upscale.py `
  --asset-key movie:default:FLYTHR03 --run <nouveau-run> --plan

python pipeline/scripts/run_video_upscale.py `
  --asset-key movie:default:FLYTHR03 --run <nouveau-run>
```

Un run terminé prouve uniquement l'upscale technique. Il ne prouve ni QA, interpolation, encodage
de livraison, intégration jeu ou release.

## Interpolation 30 fps v1

| Élément | Autorité |
|---|---|
| Recette | `../pipeline/topaz/recipes/Video-Interpolation-Apollo8-30fps-v1.json` |
| Runner | `../pipeline/scripts/run_video_interpolation.py` |
| Procédure | [`../pipeline/VIDEO_INTERPOLATION_PIPELINE.md`](../pipeline/VIDEO_INTERPOLATION_PIPELINE.md) |

```powershell
python pipeline/scripts/run_video_interpolation.py `
  --upscale-run <run-upscale-scellé> --run <nouveau-run>
```

Apollo 8 produit 30 fps en `2N−1`. `rdt=-0.01` désactive les quasi-doublons ; un post-traitement
hashé retire seulement les frames adjacentes identiques. La sortie ProRes est technique, sans audio.
