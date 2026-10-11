# AM0510A — SeedVR accepté, lot4 terminé, 2026-10-11

- Demande : nouvelle version SeedVR de l'arche/portail du lot4. La version en jeu était déjà SeedVR2 7B INT8/LAB x4 (2026-09-19, seed959948902156062), Apollo8, masque arche/halo appliqué le 2026-10-11.
- Nouvelle inférence depuis les9frames BAM natives : `am0510a-seedvr7b-lab-x4-retest-20261011-v1`, workflow `pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json`, modèle `seedvr2_7b_int8_convrot.safetensors`, LAB, x4/pad32, **seed20261011**.
- Temporal : Apollo8 15→30FPS, RGB caché nearest-opaque-dilate ; 9poses distinctes →18phases distinctes, boucle0,6s ; centres/dimensions/cycles inchangés.
- Masque conservé : `animations/ressources/AM0510A/runs/am0510a-seedvr7b-retest-accepted-20261011-v1/mask.png` ; SHA256 `39564e36dacc98902cfce1c2e5866bfb50d022f049b77a21ec5e663670ca1105`. Identique au masque installé, appliqué après interpolation ; halo/aperture/alpha final inchangés.
- Sortie actuelle : `animations/batches/am0510a-seedvr7b-retest-20261011-v1/{final-assets,temporal,manifest.json,installation.json}`. Comparatifs contenant l'ancienne version retirés à la demande utilisateur.
- État courant : **installé et accepté ingame sur AR0510**, lot4 terminé ; lot5 en attente, release non sélectionnée. Manifeste du trial initial immuable : son état décrit sa date de production ; QA finale ci-dessous.

```powershell
python pipeline/scripts/run_animation_upscale.py --resref AM0510A --run am0510a-seedvr7b-lab-x4-retest-20261011-v1 --scale 4 --pad 32 --seed 20261011
python pipeline/recipes/am0510a-seedvr7b-retest-20261011-v1/build.py
```

AR0510 : script BCS désactive l'animation malgré le flag ARE natif actif. Pour QA une fois la carte chargée : `C:Eval('AmbientActivate("AM0510A",1)')`, puis fermer la console/reprendre le jeu. Aucune variable de quête modifiée.

## Installation, 2026-10-11

- Producteur : `python pipeline/recipes/am0510a-seedvr7b-retest-20261011-v1/install.py` ; jeu/InfinityLoader arrêtés.
- Pack actif : `animations/packs-par-zone/am0510a-seedvr7b-retest-30fps-mask-20261011-v1/AR0510` ; wrapper `animations/ressources/AM0510A/runs/am0510a-seedvr7b-retest-30fps-mask-20261011-v1`.
- Reçu : `animations/batches/am0510a-seedvr7b-retest-20261011-v1/installation.json`. Après acceptation, les18frames du portail écarté dans la sauvegarde `previous/` sont supprimées ; reçu historique et frères conservés. Cette sauvegarde ne permet plus de restaurer l'ancien portail.
- 18frames AM0510A remplacées ; registre byte-identique ; FLAME2M/FLAME2S/FLMS byte-identiques ; DLL/INI/ARE inchangés. CSV `validé-x4`, sélection acceptée, verrou AR0510 lié directement au pack actif.
- Commandes complètes : batch `CLUA.md`, inclut `AmbientActivate("AM0510A",1)` après initialisation du script de zone.

## Acceptation / retrait / lot5

- Décision explicite : « ok je valide ta derniere version. supprime toutes traces de l'ancienne version ».
- Producteur : `finalize.py` ; reçu documentaire `acceptance.json` : chemins/fichiers/octets du retrait, conservation exacte des20cartes du lot5, absence d'écriture du jeu/release.
- QA immuable : `animations/index/qa-decisions/AM0510A/2026-10-11-accepted-am0510a-lot4-final-v1.json` ; sélection `animations/index/selections/AM0510A.json` ; run final `am0510a-seedvr7b-retest-accepted-20261011-v1` (parents = nouvelle inférence + nouveau temporal uniquement).
- Retrait effectué : inférence/timing de septembre, ancien wrapper/final/masque (masque courant copié avant retrait), ancien merged-AR0510, anciens aperçus/comparatifs,18frames de sauvegarde. Sources BAM natives/références de carte et métadonnées historiques conservées.
- **Retrait restant soumis à confirmation** : `animations/packs-par-zone/lot45-final-20261011-v1-complete` (1,25Go), qui contient la dernière copie de l'ancien portail et20cartes du lot5. Le contrôle automatique a refusé sa suppression car ce dossier partagé dépasse AM0510A. Aucun contournement : dossier conservé.
- Avant ce retrait proposé : lot5 copié depuis ses20feuilles merged vers `animations/packs-par-zone/lot5-current-20261011-v1`, hashes installés inchangés ; nouveaux wrappers `*-lot5-current-20261011-v1`, CSV toujours `à-valider`, verrou relocalisé. Les wrappers lot45 historiques sont archivés ; l'index partagé n'est plus une dépendance des sélections/verrous courants.
- Lot5 : `animations/batches/lot5-current-20261011-v1/{preview-lot5.png,CLUA.md,manifest.json}` ;3assets/4variantes/20cartes/68occurrences ; AM3000E aperçu sur cycle1 effectivement utilisé ; FLM2PUR embarqué et PLT_PURP séparés ; AMWRPGT1 source acceptée inchangée.
- Les producteurs `build.py`/`install.py` sont historiques : leurs chemins de comparaison/prédécesseur ont été supprimés après validation ; ne pas les relancer sur les mêmes IDs.
