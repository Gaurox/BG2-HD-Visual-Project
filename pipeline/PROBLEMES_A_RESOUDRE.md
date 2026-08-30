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

## MAP-PERF-001 — gel à la première ouverture de la carte x4

- **Périmètre** : première ouverture/dezoom de la carte ingame sur AR0700N, AR0516, AR0602 et
  AR0900 ; la seconde ouverture déjà chaude n’est pas le défaut principal.
- **Cause mesurée** : 95 à 98 % des frames de pic sont portées par les matérialisations synchrones
  de `CResPVR::Demand`. Les appels GL de création et d’upload restent minoritaires.
- **État** : le mini-lot carte 3 préchauffe progressivement les pages en opt-in. Son candidat ingame
  exact est gelé par le SHA `9FCE57D1…` et se reconstruit avec succès, mais la première session
  n’est pas un A/B contrôlé et AR0900 n’a pas été ouverte après préchauffage.
- **Risques ouverts** : une PVRZ 4096² d’AR0900 peut encore bloquer une frame jusqu’à 43,77 ms ; les
  quatre instantanés intermédiaires sont des sauvegardes brutes sans transaction fail-closed.
- **Gate** : campagne chaude contrebalancée A-B-B-A, processus redémarré entre parcours, même ordre
  de zones, deux ouvertures par zone, AR0900 obligatoire ; comparer pics, matérialisations,
  évictions et coût du préchauffage. Formaliser la restauration avant toute réinstallation.
- **Preuve et protocole** :
  [`../docs/AUDIT_PERFORMANCES_CARTES_X4_SUIVI.md`](../docs/AUDIT_PERFORMANCES_CARTES_X4_SUIVI.md).
- **Règle** : prototype non éligible à la release ; aucune promotion de contenu ou de manifeste
  avant validation ingame concluante et accord explicite.

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
  backing xN, sans règle par map. Le défaut résiduel du `SPHINCT` inférieur d'AR0516 a été prouvé
  indépendant du bridge : géométrie `Cover animations` absente du WED vanilla. Un polygone local
  `0x09` a été validé ingame le 2026-08-27 ; cette exception n'élargit pas le périmètre moteur.
  Installation QA locale seulement ; promotion release interdite.
- **Preuve** :
  `engine/InfinityEngine-Enhancer/source-patchee/docs/validation/native-occlusion-phase1-validation.md`
  et `engine/InfinityEngine-Enhancer/source-patchee/docs/validation/native-occlusion-ar0516-wed-correction.md`.
- **Gate restante** : matrice A/B de
  `engine/InfinityEngine-Enhancer/source-patchee/docs/native-occlusion-phase1.md`, stabilité GL et
  mémoire, Monster/MonsterIcewind, effets/classes non modélisés, transitions et compatibilité packs
  v1/v2/v3 sans modification de leurs hashes.
