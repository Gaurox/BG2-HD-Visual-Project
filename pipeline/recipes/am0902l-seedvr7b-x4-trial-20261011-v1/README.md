# AM0902L — essai SeedVR 7B x4, 2026-10-11

- Demande : comparer SeedVR 7B x4 à ReboutCX actuellement installé ; aucun remplacement ingame demandé.
- Sorties : `animations/batches/am0902l-seedvr7b-x4-trial-20261011-v1/` ; `comparison.png`, `comparison-three-poses.png`, `comparison.gif`, `final-assets/`.
- Base indépendante : `animations/ressources/AM0902L/runs/am0902l-seedvr7b-lab-x4-trial-20261011-v1/` (32 dessins natifs).
- SeedVR2 `seedvr2_7b_int8_convrot.safetensors`, LAB, seed20261011, x4, pad32 ; workflow `pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json`, SHA256 `30dec619a4c1a3ecde076c0926a5ed8ee29d5f2ca8b4eb89a75d3b5f7811b61e`.
- 4 tuiles ×8 poses synchronisées ; union x1 puis remplissage RGB nearest opaque ; 8 inférences complètes supplémentaires ; seuls les RGB des bandes partagées remplacés dans les bases indépendantes, poids `clip((4-distance)/3,0,1)`, limité au segment réel, centres x4 ; alpha natif nearest x4.
- Aucun doublon dans les8 montages natifs ; Apollo8 sur montage complet à15→30FPS ; inner2 sur silhouette extérieure puis redécoupe native ; 4cycles ×16phases, 64frames ; boucle `8/15 = 16/30 = 0,533333s` ; dimensions/centres/lookup natifs conservés.
- Référence comparée : `animations/batches/lot3-decor-x4-20261011-v1/final-assets/`, AM0902L ReboutCX contextuel/Apollo8/inner2 installé AR0902 ; comparaison phases0/6/12 et boucle complète.
- GIF : cadence quantifiée en centisecondes (~0,53s) ; registre et séquence PNG30FPS conservent la durée exacte.
- État essai initial : produit pour comparaison ; son manifeste historique reste immuable. Installation ultérieure demandée et réalisée, voir ci-dessous ; QA ingame en attente.

Commandes productrices, dans l'ordre (sorties neuves ; ne pas réécrire l'essai terminé) :

```powershell
python pipeline/scripts/run_animation_upscale.py --resref AM0902L --run am0902l-seedvr7b-lab-x4-trial-20261011-v1 --scale 4 --pad 32 --seed 20261011
python pipeline/recipes/am0902l-seedvr7b-x4-trial-20261011-v1/build.py prepare
python pipeline/scripts/upscale_animation_frames.py animations/batches/am0902l-seedvr7b-x4-trial-20261011-v1/assembled-native/rgb animations/batches/am0902l-seedvr7b-x4-trial-20261011-v1/assembled-native/alpha animations/batches/am0902l-seedvr7b-x4-trial-20261011-v1/assembled-seedvr-x4 --frame-manifest animations/batches/am0902l-seedvr7b-x4-trial-20261011-v1/assembled-native/manifest.json --scale 4 --pad 32 --seed 20261011 --upload-folder BG2_Upscale/animation-runs/am0902l-seedvr7b-x4-trial-20261011-v1/context
python pipeline/recipes/am0902l-seedvr7b-x4-trial-20261011-v1/build.py context
python pipeline/recipes/am0902l-seedvr7b-x4-trial-20261011-v1/build.py finish
```

Le premier lancement a échoué avant inférence (ComfyUI arrêté) ; reprise identique `--resume` après démarrage ComfyUI par l'utilisateur. Les manifestes producteur authentifient les sorties et leurs paramètres.

## Installation demandée, 2026-10-11

- Actif : AM0902L SeedVR sur AR0902, remplace ReboutCX ; 65fichiers/75 461 612octets authentifiés ; registre runtime byte-identique (contrat géométrie/cycles/FPS inchangé), 64payloads RGB remplacés.
- Feuille : `animations/packs-par-zone/am0902l-seedvr7b-x4-30fps-context-20261011-v1/AR0902/` ; wrapper canonique `animations/ressources/AM0902L/runs/am0902l-seedvr7b-x4-30fps-context-20261011-v1/manifest.json`.
- Reçu actif : batch `installation.json` ; sauvegarde transactionnelle `backups/animations/area-tests/AR0902-20261011T133438963101Z-2067dc2c/install-backup.json` ; précédent `lot3-decor-x4-20261011-v1-complete/AR0902` conservé.
- Producteur installation : `python pipeline/recipes/am0902l-seedvr7b-x4-trial-20261011-v1/install.py` ; jeu/InfinityLoader absents ; DLL/INI/ARE inchangés ; sélection AM0902L et verrou AR0902 mis à jour ; QA `à-valider`, release non sélectionnée.
- Après bascule réussie, le verrou a normalisé la recette en `merged_from` plutôt que `leaf` ; contrôle adapté aux signatures de recette, suivi finalisé depuis le reçu sans réinstaller.
- Test : `C:MoveToArea("AR0902")`, puis `C:Eval('JumpToPoint([1171.811])',0)` ; coordonnées logiques x1.

## QA finale, 2026-10-11

- Utilisateur : « on valide SeedVR. tu peux valider tout le lot 3 » ; SeedVR accepté sur AR0902, tous les4assets du lot3 validés.
- Décision : `animations/index/qa-decisions/AM0902L/2026-10-11-accepted-am0902l-lot3-final-v1.json` ; sélection `animations/index/selections/AM0902L.json` ; wrapper `animations/ressources/AM0902L/runs/am0902l-lot3-four-decors-accepted-20261011-v1/`.
- Production initiale/comparatif/installation restent immuables ; QA ne se déduit pas de leurs anciens champs `pending`/`not-installed`.
