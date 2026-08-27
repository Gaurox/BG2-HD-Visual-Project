# Problèmes ouverts

Source unique des blocages non résolus. Un problème résolu est retiré de ce fichier et sa décision
durable est ajoutée à [`../docs/DECISIONS.md`](../docs/DECISIONS.md). Les statuts de zones restent
dans `areas.csv`.

## MAP-WATER-001 — rendu de liquide incorrect selon l'état du jeu

- **Périmètre** : eau marron sur AR0900 après nouvelle partie/transition et sur AR1607/AR1800 avec
  WTSWAM ; overlays visibles pendant la pause.
- **Preuves** : statuts et notes des zones dans `areas.csv`, captures/backups locaux.
- **Gate** : reproduction contrôlée nouvelle partie, transition, pause et rechargement ; identifier
  séparément couleur, animation de cycle et couche de composition.

## MAP-WTPOOL-001 — cycle WTPOOL figé

- **Périmètre confirmé** : AR0408 et AR0703.
- **Gate** : vérifier l'index de cycle et les sentinelles avec stock, x2 et x4, sans modifier la map
  dans le même essai.

## MAP-ALPHA-001 — contours de liquide en marches

- **Périmètre** : AR0604/AR0413 et défauts légers signalés sur plusieurs secondaires/eaux.
- **État** : spline périodique `fit 1.0` validée sur AR0413, mais pas solution globale.
- **Gate** : fixture alpha contenant lignes droites, courbes, coins et secondaire ; comparaison
  avant/après sans changement RGB.

## MAP-QA-001 — zones installées non validées

- **Périmètre actuel** : lire `areas.csv`; au moment de l'assainissement, AR1607 et AR1800 étaient
  `installed-pending-qa` après refus sur l'eau.
- **Gate** : correction, vérification SHA de l'installation puis nouvelle QA utilisateur.
- **Règle** : ne jamais transformer ce statut en `validated-installed` depuis un log de batch.

## ENGINE-OCCLUSION-001 — validation ingame du bridge structurel xN

- **Périmètre** : animations de zone v1/v2/v3 non masquées, Monster, MonsterIcewind et Character
  remplacés ; premier plan WED, dither partiel, flag ARE `No Wall`, transitions et resize.
- **État** : jalon Phase 1 validé ingame sur AR0516 pour une animation de zone `CGameStatic` x4
  et une créature `Character` xN. Le bridge générique réapplique correctement l'occlusion WED au
  backing xN, sans règle par map. Installation QA locale seulement ; promotion release interdite.
- **Preuve** :
  `engine/InfinityEngine-Enhancer/source-patchee/docs/validation/native-occlusion-phase1-validation.md`.
- **Gate restante** : matrice A/B de
  `engine/InfinityEngine-Enhancer/source-patchee/docs/native-occlusion-phase1.md`, stabilité GL et
  mémoire, Monster/MonsterIcewind, effets/classes non modélisés, transitions et compatibilité packs
  v1/v2/v3 sans modification de leurs hashes.
