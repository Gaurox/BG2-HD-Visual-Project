# Vidéos BG2EE

**37/37 variantes acceptées en jeu** après confirmation utilisateur pour `DEATHAND`, `FLYTHR03`, `REST`, `RESTINN` le 2026-11-22. [Suivi](SUIVI.md) · [Décision](index/qa-decisions/remaining-four-ingame-accepted-20261122-v1.json).

`index/manifest.json` et `index/resources.csv` constituent l'inventaire canonique des
cinématiques WBM libres et des tutoriels WBM du KEY/BIF. Les WBM utilisés comme animations de
zone restent sous l'autorité de `animations/index/occurrences.csv` et sont exclus ici.

`index/processing.csv` sélectionne les runs validés par étape et le run utilisé par le patch.
`patch_run` vide signifie qu'aucun artefact vidéo n'est intégré au patch.

ENDCRDIT produit2026-11-12 :**T1 Proteus neutre seul +Apollo8 FullHD30**,4004images/~133,47s,audio natif complet. **Film complet accepté2026-11-12**,WBM +alias `HDENDCRD` installés ;**QA ingame acceptée sur instruction explicite utilisateur**. Reçu : `index/endcrdit-ingame-test-20261112-v1.json` ;QA visuelle/ingame sous `index/qa-decisions/ENDCRDIT/`. [Recette](../pipeline/recipes/endcrdit-proteus-T1-apollo30-20261112-v1/README.md),manifeste `index/endcrdit-proteus-T1-finals30-20261112-v1.json`.37cinématiques désormais produites ;anciens essais/pauses conservés comme historique.

QA ingame2026-11-12 :24versions supplémentaires acceptées,DAYNITE inclus explicitement ;33versions installées désormais acceptées (ENDCRDIT ajouté sur instruction utilisateur). Décision/SHA : `index/qa-decisions/installed-batch-ingame-accepted-20261112-v1.json`. RESTDUNG :validation du WBM15 installé ;LOGO :29,97fps natifs,sans interpolation. Reçus/QA historiques inchangés ;aucune intégration release.

LOGO produit2026-11-12 : SeedVR FullHD seul,302images à30000/1001fps (~29,97),sans interpolation/Apollo sur instruction utilisateur. Original1280×720 déjà propre ;rendu accepté2026-11-12,WBM +alias `HDLOGO` installés ;**QA ingame acceptée2026-11-12**. Reçu : `index/logo-ingame-test-20261112-v1.json` ;QA : `index/qa-decisions/LOGO/20261112-nativefps-visual-accepted-v1.json`. Manifeste : `index/logo-finals-nativefps-20261112-v1.json` ;[recette](../pipeline/recipes/logo-seedvr-nativefps-20261112-v1/README.md).

NITEDAY sélection2026-11-12 : **H3 DAYNITE01604 inversé/recalé**,300images/FullHD30/10s vidéo,durée déclarée totale native10,942s,audio NITEDAY Vorbis inchangé. H3 inversé validé visuellement et installé avec alias `HDNTDAY` ; **QA ingame acceptée2026-11-12**. Production : `index/niteday-h3-reverse-finals30-20261112-v1.json` ; reçu : `index/niteday-h3-reverse-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/NITEDAY/20261112-h3-reverse-visual-accepted-v1.json` ; [recette/console/restauration](../pipeline/recipes/niteday-h3-reverse-20261112-v1/README.md). Candidat SeedVR antérieur conservé non sélectionné ; aucune intégration release.

FLYTHR02 produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,404images/FullHD30/~13,47s ;187images natives conservées,maintien terminal pour la queue audio complète. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDFLY02`, **QA ingame acceptée2026-11-12**. Reçu : `index/flythr02-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/FLYTHR02/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/flythr02-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/flythr02-seedvr-apollo30-20261112-v1/README.md).

DORNGORG produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,386images natives à PTS irréguliers reconstruites en464images/FullHD30/~15,47s ; audio natif conservé en MKV/WBM. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDDGORG`, **QA ingame acceptée2026-11-12**. Reçu : `index/dorngorg-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/DORNGORG/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/dorngorg-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/dorngorg-seedvr-apollo30-20261112-v1/README.md).

RASAADMI produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,403images natives à PTS irréguliers reconstruites en484images/FullHD30/~16,13s ; audio natif conservé en MKV/WBM. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDRASAMI`, **QA ingame acceptée2026-11-12**. Reçu : `index/rasaadmi-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/RASAADMI/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/rasaadmi-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/rasaadmi-seedvr-apollo30-20261112-v1/README.md).

FLYTHR04 produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,245images15fps vers490images/FullHD30/~16,33s ; audio natif conservé en MKV/WBM. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDFLY04`, **QA ingame acceptée2026-11-12**. Reçu : `index/flythr04-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/FLYTHR04/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/flythr04-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/flythr04-seedvr-apollo30-20261112-v1/README.md).

NEERAES produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,422images natives à PTS irréguliers reconstruites en507images/FullHD30/16,9s ; audio natif conservé en MKV/WBM. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDNEERA`, **QA ingame acceptée2026-11-12**. Reçu : `index/neeraes-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/NEERAES/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/neeraes-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/neeraes-seedvr-apollo30-20261112-v1/README.md).

HEXXATDR produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,442images natives à PTS irréguliers reconstruites en531images/FullHD30/17,7s ; audio natif conservé en MKV/WBM. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDHEXX`, **QA ingame acceptée2026-11-12**. Reçu : `index/hexxatdr-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/HEXXATDR/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/hexxatdr-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/hexxatdr-seedvr-apollo30-20261112-v1/README.md).

MANAFORG produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,549images/FullHD30/18,3s ;251images natives conservées,maintien terminal pour la queue audio complète. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDMANA`, **QA ingame acceptée2026-11-12**. Reçu : `index/manaforg-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/MANAFORG/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/manaforg-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/manaforg-seedvr-apollo30-20261112-v1/README.md).

DORNTREE produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,461images natives à PTS irréguliers reconstruites en553images/FullHD30/~18,43s ; audio natif conservé en MKV/WBM. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDDTREE`, **QA ingame acceptée2026-11-12**. Reçu : `index/dorntree-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/DORNTREE/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/dorntree-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/dorntree-seedvr-apollo30-20261112-v1/README.md).

RASAADTE produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,499images natives à PTS irréguliers reconstruites en599images/FullHD30/~19,97s ; audio natif conservé en MKV/WBM. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDRASATE`, **QA ingame acceptée2026-11-12**. Reçu : `index/rasaadte-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/RASAADTE/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/rasaadte-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/rasaadte-seedvr-apollo30-20261112-v1/README.md).

FLYTHR01 produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,670images/FullHD30/22,333s ;301images natives conservées,maintien noir terminal pour la queue audio complète. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDFLY01`, **QA ingame acceptée2026-11-12**. Reçu : `index/flythr01-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/FLYTHR01/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/flythr01-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/flythr01-seedvr-apollo30-20261112-v1/README.md).

SARADUSH produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,694images/FullHD30/23,133s ;315images natives conservées,maintien terminal pour la queue audio complète. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDSARAD`, **QA ingame acceptée2026-11-12**. Reçu : `index/saradush-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/SARADUSH/20261112-fullhd30-visual-accepted-v1.json`. Résultats : `index/saradush-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/saradush-seedvr-apollo30-20261112-v1/README.md).

BLACKPIT produit2026-11-12 : SeedVR FP16 LAB1080 →Apollo8,611images natives à PTS irréguliers reconstruits en733images/FullHD30/~24,44s ; audio natif conservé dans MKV/WBM. Rendu validé visuellement2026-11-12 ; WBM installé avec alias `HDBLKPIT`, **QA ingame acceptée2026-11-12**. Reçu : `index/blackpit-ingame-test-20261112-v1.json` ; QA : `index/qa-decisions/BLACKPIT/20261112-fullhd30-visual-accepted-v1.json`. Manifeste : `index/blackpit-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/blackpit-seedvr-apollo30-20261112-v1/README.md).

POCKETZZ finale2026-11-12 : SeedVR FullHD15 →Apollo8 FullHD30,180images/6s, rendu validé visuellement. WBM installé avec alias `HDPCKZZ` ; **QA ingame acceptée2026-11-12**. Production : `index/pocketzz-finals30-20261112-v1.json` ; installation : `index/pocketzz-ingame-test-20261112-v1.json` ; [recette/console/restauration](../pipeline/recipes/pocketzz-apollo30-20261112-v1/README.md). Aucune intégration release.

OUTRO finale2026-11-12 : SeedVR FP16 LAB →Apollo8 FullHD30,2450images/~81,667s,sans audio comme la source ; MP4/MKV/WBM validés visuellement, WBM installé avec alias `HDOUTRO` et validé ingame le2026-11-12. Résultats : `index/outro-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/outro-seedvr-apollo30-20261112-v1/README.md). Installation : `index/outro-ingame-test-20261112-v1.json` ; décisions QA : `index/qa-decisions/OUTRO/20261112-fullhd30-visual-accepted-v1.json` et `index/qa-decisions/OUTRO/20261112-fullhd30-ingame-accepted-v1.json`. Aucune intégration release.

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
[Console/restauration](../pipeline/recipes/intro15f-ingame-test-20261111-v1/README.md). QA ingame acceptée2026-11-12 ; aucune intégration release.
Sources/fichiers finaux/preuves QA conservés ; intermédiaires inutiles retirés2026-11-11 selon `index/cleanup-20261111-v1.json`. Médias locaux ignorés par Git.

Périmètre production :37cinématiques ;13tutoriels exclus sur demande utilisateur2026-11-11,
`index/production-scope.json`. Ne pas réintroduire les tutoriels dans le suivi ou une file de traitement.
Inventaire source50assets et fichiers tutoriels conservés.
Suivi courant : [`SUIVI.md`](SUIVI.md) ; vue37cinématiques : `index/status.csv` ; médias réellement
conservés et alias des anciennes copies : `index/retained-media-20261111-v1.json` (inventaire20261110 historique conservé).

RESTDUNG : SeedVR2 3B FP16 LAB Full HD15 retenu le 2026-11-09 ; installé localement en WBM
VP8/Vorbis, QA ingame acceptée2026-11-12 (version15fps installée). Sélection : `index/qa-decisions/RESTDUNG/` ; reçu :
`installations/restdung-seedvr-20261109-v1/installation.json`. Réglages des essais supprimés et
restauration : [`mémoire RESTDUNG`](../pipeline/recipes/restdung-seedvr-selected-20261109-v1/README.md).

RESTDUNG30 et RESTINN SeedVR15/Apollo30 acceptés en comparaison ; décisions immuables sous
`index/qa-decisions/`. RESTINN n'est pas installé. Recette :
[`RESTINN SeedVR + Apollo`](../pipeline/recipes/restinn-seedvr-apollo-20261109-v1/README.md).

REST SeedVR15/Apollo30 accepté en comparaison ; décision sous `index/qa-decisions/REST/` ;
aucune installation. Recette : `../pipeline/recipes/rest-seedvr-apollo-20261109-v1/`.

DAYNITE : H3 01604 remonte10s/fondus corrigés → nearest1920×1080 → Apollo8/30fps, son natif.
Sélection pour test local2026-11-10 : `index/qa-decisions/DAYNITE/` ; installé uniquement dans
`movies/daynite.wbm`, QA ingame acceptée2026-11-12 après test explicite ;ancien signalement clos. Reçu/sauvegarde :
`installations/daynite-h3-nearest-20261110-v1/installation.json` ; recette/restauration :
`../pipeline/recipes/daynite-h3-nearest-ingame-20261110-v1/`. Aucune intégration release.
La chaîne DAYNITE conserve imagesT2/T4, sourceH3, montage, inputs crop/audio, nearest24/30 et WBM.
Le post-upscale SeedVR sur H3 a été jugé dégradant par l'utilisateur ; ses médias, les essais
direct/inverse et T1/T3 ont été supprimés. Réglages/logs historiques :
`../pipeline/recipes/video-retained-cleanup-20261110-v1/settings-memory/`.

Nettoyage2026-11-11 :141fichiers de travail supprimés,14 631 402 684octets (~13,63Gio),dont109dans le projet et32caches vidéo BG2 ComfyUI.34contrôles de doublons ;748fichiers protégés inchangés.50sources,42fichiers finaux,preuves QA,sauvegardes et pause ENDCRDIT conservés ; aucune tâche GPU/décodage. Reçu : `index/cleanup-20261111-v1.json` ; recette : `../pipeline/recipes/video-cleanup-20261111-v1/README.md`.

Nettoyage2026-11-10 :467fichiers supprimés (gain net≈4,27Gio),50sources et sauvegardes conservées.
POCKETZZ : candidat SeedVR FullHD15 conservé lors de ce nettoyage ; statut courant ci-dessus.
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
