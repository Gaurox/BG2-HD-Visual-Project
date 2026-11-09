# RESTDUNG — SeedVR sélectionné, essais supprimés, installation locale

- Décision utilisateur2026-11-09 : SeedVR gagne ; conserver SeedVR, supprimer essais, installer ingame.
- Sélection : `video/restdung/runs/restdung-seedvr-reference-20261109-v1/SeedVR2-RESTDUNG-3B-FP16-LAB-1080p15.mp4` ; image copiée sans réencodage du run ComfyUI20260814 ; audio source complet.
- Source immuable : `video/restdung/restdung.wbm` ; aperçu source séparé `video/restdung/source-preview-720p15.mp4`.
- QA : `video/index/qa-decisions/RESTDUNG/20261109-seedvr-fullhd-selected-v1.json` ; comparaison acceptée, validation ingame encore inconnue.
- Runtime : `video/restdung/runs/restdung-seedvr-ingame-20261109-v1/restdung.wbm`, VP8 1920×1080 /15fps /91frames, Vorbis source copié ; CRF4,20M,qmax12,cpu-used0. SSIM≈0,9945 face au MP4 SeedVR ; PCM audio SHA256 identique au natif.
- Installation : `config://bg2ee_game_root/movies/restdung.wbm` ; reçu `video/installations/restdung-seedvr-20261109-v1/installation.json`, original précédent sous `before/restdung.wbm` ; remplacement atomique, jeu/InfinityLoader absents avant écriture.
- Release/patch/package : aucune modification. `patch_run` reste vide.

## Réglages retenus

- Modèle : `seedvr2_ema_3b_fp16.safetensors`, VAE `ema_vae_fp16.safetensors`, correction LAB.
- Seed42 ; résolution1080 ; batch33 uniforme ; overlap temporel3 ; prepend0 ; bruits input/latent0.
- VAE encode tiled1024/overlap128, decode tiled768/overlap128 ; CUDA0 ; offloadCPU.
- DiT blocks_to_swap32 ; swap_io_components=false ; attentionSDPA ; pas de cache modèle.
- Workflows complets : `seedvr-original-prompt.json`, `seedvr-original-workflow.json`. Cette recette FP16 historique est distincte de LAB-v2 INT8 ConvRot canonique ; sélection limitée à RESTDUNG.

## Mémoire de tous les essais

- `settings-memory/runs/` : copies exactes des scripts, JSON, recettes effectives, logs et contrôles A/B/N1/N2/T1–T6.
- `settings-memory/analysis/` : mesures par région, timestamps source et script d'analyse.
- Six chaînes et interprétation : `../restdung-topaz-six-proposals-20261109-v1/README.md` ; codes de production gardés comme mémoire historique, pas comme commande de reprise des médias supprimés.
- MCP : analyse faux positifs visages ; première estimation105frames incorrecte, comptage réel91. Aucun Iris produit.
- A=Proteus doux direct ; B=Gaia CG direct ; N1=nettoyageProteus720 puisA ; N2=Nyx3 doux720 puisA.
- T1=Proteus→Proteus→Apollo ; T2=Proteus→Gaia→Apollo ; T3=Proteus doux→Gaia→Apollo ; T4=Proteus→Lanczos→Apollo ; T5=Proteus→Apollo720→Gaia ; T6=Proteus→Gaia→Aion. Six sorties1080p30,181frames ; intermédiaires réels contrôlés. Résultats non retenus.
- Conclusion : N1 augmente netteté et dureté/aplats ; Nyx apporte moins ; SeedVR préféré nettement pour le détail apparent. Aucune recette Topaz n'est promue en production.
- `cleanup.json` : cibles et octets supprimés ; aucun asset autre que RESTDUNG supprimé.

## Restauration locale

Fermer jeu/InfinityLoader ; restaurer `video/installations/restdung-seedvr-20261109-v1/before/restdung.wbm` vers la cible exacte du reçu ; vérifier `before_sha256`. Ne pas utiliser le natif du workspace à la place : la sauvegarde représente le fichier réellement remplacé.

## Comparaison SeedVR15 / Apollo30

- Demande suivante2026-11-09 : interpoler le SeedVR retenu, comparer15/30fps. Producteur : `interpolate30.py`.
- Sortie : `video/restdung/runs/restdung-seedvr-apollo30-20261109-v1/SeedVR2-RESTDUNG-3B-FP16-LAB-Apollo8-1080p30.mp4` ; `run.json` = paramètres/commandes/parentSHA ; `verification.json` = contrôles.
- Apollo8 (`apo-8`),30fps,slowmo1,rdt−0,01 ;91→181frames, durée de mouvement conservée ; audio AAC du MP415 copié à l'identique. MP4 x264CRF16/slow ; source non étiquetée conservée dans la même interprétation YUV (pas de correction d'exposition ajoutée).
- Sur30intermédiaires centraux :30 distincts des deux voisins ; écart moyen des ancres décodées≈1,05/255, luma≈−1,02/255 (traitement/encodage, pas identité pixel à pixel). Source15SHA inchangé.
- Master de travail FFV1≈0,96Gio supprimé après vérification ; seul le MP4 de comparaison et les petits reçus/logs sont conservés.
- Deux menus du comparateur : SeedVR15 et SeedVR+Apollo30. Choix30 accepté en comparaison par l’utilisateur lors du passage à RESTINN ; installation du jeu toujours SeedVR15, aucune promotion QA/release.
