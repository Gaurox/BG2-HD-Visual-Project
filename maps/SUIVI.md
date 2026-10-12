# Maps — état courant et réserves

Mise au propre du suivi/nettoyage clôturée : 2026-10-12. Finalisation release locale maps terminée
le même jour ; sources validées et fichiers du jeu conservés.

## Release / installeur locaux — terminés le 2026-10-12

- Alpha locale `0.1.0-alpha.6` : 399 variantes (OH6460 via OH8100), 8 566 fichiers maps.
- 64 assemblages actualisés : 63 WED liquides avec décor/contours/TIS/WED et 188 identités
  overlay jour/pluie, plus AR3003. Sources finales copiées à octets constants, 144 preuves QA
  acquises reliées ; aucune nouvelle validation ingame.
- AR3003 : quatre pages du patch réellement installé le 2026-09-06 retrouvées dans `output/` ;
  reçu historique exact, rendu accepté le 2026-10-11. AR0413 : pile finale du 2026-09-28,
  22 fichiers ; AR0516 : contrat WED animation conservé exact.
- Animations/sprites/effets/overlays partagés/renderer conservés. Core possède maintenant
  `[Shaders].EnableWaterOverlayRoute2=true`, `WaterOverlayStrength=1.00`, valeurs du rendu validé.
- Compilation, staging, formats, ZIP, installation/mise à jour/retrait/restauration sur fixtures
  passés ; 33 tests unitaires. ZIP **sans compression** (29 141 entrées ZIP_STORED).
- Rapport : [`../docs/validation/maps-release-status-20261012-v1.json`](../docs/validation/maps-release-status-20261012-v1.json).
  Recette : `../pipeline/recipes/maps-release-finalization-20261012-v1/README.md`.
- Jeu installé inchangé. Publication toujours `blocked` : qualifications réelles Steam/EEex,
  renderer combiné, sauvegardes HD→vanilla, retrait complet et provenance/contact publics.

## Statut : production, QA visuelle, suivi et nettoyage terminés

- Décors : 400 variantes `validated-installed` ; liquides : 63 WED actives acceptées.
- Réserves visuelles AR3003/AR5200/AR2101/AR0604 levées ; dernière passe représentative
  AR0900/AR1000/AR0500, jour/nuit, sec/pause/pluie/cycle jour→nuit→jour validée le 12 octobre.
- Nettoyage des 29 dossiers exécuté ; preuves conservées. **19 dossiers ambigus conservés
  sur décision utilisateur du 2026-10-12**, total mesuré 252 341 371 octets = 252,34 Mo.
  Leur conservation ne leur attribue pas de validation ni de sélection production.
- Aucun travail ingame supplémentaire demandé pour cette clôture. Les conditions non
  observées sur d'autres maps restent explicitement non attestées et facultatives ; classification
  technique/préflight et qualification générale du renderer restent des sujets distincts.
- Cette clôture ne modifie ni les états d'installation ni les états d'intégration release.

## Autorités et portée

| État | Autorité | État enregistré |
|---|---|---|
| Décor x4 | [`../areas.csv`](../areas.csv) | 369 zones + 31 nuits = 400 variantes `validated-installed` ; runs/builds renseignés |
| Traitement liquide | [`../pipeline/water/ingame-map-tracking-v1.json`](../pipeline/water/ingame-map-tracking-v1.json) | 63 WED actifs acceptés ; 4 sans cellule liquide active ; références QA reliées aux 63 WED |
| QA exacte | `../pipeline/water/manifests/*user-qa*.json`, `*validated*.json` | décisions immuables ; réserve acceptée ≠ travail bloqué ; portée météo/variante explicite |
| Registre runtime courant déclaré | `../pipeline/water/route2-registry-current.json` | pointeur distinct de la QA et des états historiques intégrés aux registres d'inférence |
| Anciennes sélections eau | `../pipeline/water/release-tracking-v1.json` | QA du traitement actualisée ; overlay/q/artifacts/runtime = photographie legacy du 2026-09-12, pas preuve des octets actuellement installés |
| Sélection / assemblages release locale | `../releases/BG2-HD-Upscale/manifests/map-release-candidates.csv`, `map-release-assemblies.json` | 399 variantes explicites, inventaires/hashes/sources/QA acquises ; assemblages finaux distincts des sélections legacy |
| Animations / release | `../animations/index/`, `../releases/BG2-HD-Upscale/manifests/` | domaines indépendants ; aucune validation ni intégration déduite du statut décor |

## Réserves visuelles clôturées le 2026-10-11

| Zone | Point conservé | Preuve / limite |
|---|---|---|
| AR3003 | Ancien liseré cyan du raster BC1/PVRZ | Rendu actuel vérifié et accepté par l'utilisateur ; aucune nouvelle correction d'asset déduite |
| AR5200 | Ancienne réserve sur une portion eau hors lave | Map vérifiée, tout est OK selon l'utilisateur ; identification/traitement supplémentaire non demandé |
| AR2101 | Ancienne retouche Photoshop des contours | Rendu actuel vérifié et accepté ; réserve levée |
| AR0604 | Ancien signalement contours du décor | Rendu actuel vérifié et accepté ; réserve levée, AM0604A indépendant |

Preuve : [`qa-retour-ingame-20261011-v1.json`](qa-retour-ingame-20261011-v1.json).

## Observations complémentaires non attestées

| Zones | Point | Portée |
|---|---|---|
| AR0046, AR0204, AR0300, AR1100, AR1200, AR1201, AR1403, AR1607, AR1700, AR1800, AR1901, AR2700 | Anciens signalements de tuiles visibles dans l'eau en pause | Traitements eau ultérieurs acceptés ; observation pause distincte non attestée dans les décisions retenues. Incertitude de clôture, pas diagnostic d'un défaut présent |

## Réserves esthétiques acceptées

| Zones | Réserve retenue | Décision |
|---|---|---|
| AR1604 | Panneaux/décor améliorés mais imparfaits | `../pipeline/water/manifests/wtlake-family-user-qa-20260926-v1.json`, exception AR1604 : « c'est pas parfait mais c'est mieux. on valide. » |
| AR0506, AR1003, AR1004 | Arrondis gaussiens/BC3 résiduels, `spline_fit=0` | manifestes contour `*-contour-user-qa-20260926-v1.json` ; aucune passe plus dure demandée |
| AR1000, AR2000 | Anneaux de pluie WTPOOLR très discrets | manifestes temporels `*-temporal-30fps-user-qa-20260926-v1.json` ; pluie observée, conservée en l'état |
| AR1600 | Liseré cyan-vert résiduel sur échelle/cordages | `../pipeline/water/manifests/ar1600-contour-matte-map-user-qa-20260923-v1.json` ; correction couleur testée et refusée |
| AR2100 | Matte courant conservé | `../pipeline/water/manifests/ar2100-contour-user-qa-20260923-v3.json` ; adaptation CONTOUR-NET abandonnée |
| Contours eau fins | Fin liseré jaune-clair/cyan-vert possible | `../pipeline/water/CONTOUR_MATTE_PIPELINE.md` ; spline fit1 accepté comme C par défaut le 2026-09-25, pas de réserve bloquante universelle |

## Incertitudes documentaires et contrôles distincts

- Décor Watcher's Keep : **26 maps AR3001, AR3003–AR3027 validées explicitement le 2026-09-05**.
  Trace utilisateur retrouvée dans le chat `01a072bf-d5ce-7413-b81c-4600c25678f7` à 21:18:48Z ;
  commit `dae1d9bc`. Les 24 notes sans provenance sont maintenant reliées à
  [`qa-documentaire-20261011-v1.json`](qa-documentaire-20261011-v1.json). Pas de nouvelle QA
  décor nécessaire pour ce lot ; réserve ultérieure AR3003 levée le 2026-10-11. Passes eau AR3024/AR3025
  acceptées ultérieurement (2026-09-28 / 2026-09-25).
- Revue eau : **q 46 validés / 17 pending** ; **pluie 7 validés / 17 pending** ; **nuit 3 validés / 3 pending**.
  `pending` signifie contrôle distinct non attesté ; il n'annule pas les 63 acceptations de traitement.
  q : décisions explicites 2026-09-29 concordantes avec le registre, plus AR3000/AR5203/AR6300 q0,40.
  Pluie : AR1000/AR2000 q0 observés. Nuits : ni météo séparée ni cycle jour→nuit→jour déduits d'une QA générique.
- Retour 2026-10-11 : AR0011, AR0046, AR0046N, AR0204, AR0300 (5 premières lignes eau)
  vérifiées et acceptées au q courant. Pluie, pause et cycle jour→nuit→jour non précisés ;
  leurs états distincts conservés. La revue exhaustive reste facultative, sans blocage de la
  mise au propre ; aucune nouvelle tournée complète demandée.
- Passe finale 2026-10-12 : AR0900/AR0900N, AR1000/AR1000N, AR0500/AR0500N
  acceptées en sec, pause/reprise, pluie/retour au sec et cycle jour→nuit→jour. Ancien symptôme
  pause AR0900 clos ; pluie nocturne AR1000N attestée. Preuve :
  [`../pipeline/water/manifests/water-final-pass-user-qa-20261012-v1.json`](../pipeline/water/manifests/water-final-pass-user-qa-20261012-v1.json).
  Dernière passe demandée terminée ; aucune nouvelle tournée requise pour mettre le suivi au propre.
  Cycles non attestés ailleurs : AR0046N, AR0300N, AR2000N (complément facultatif).
- Sélections eau legacy : **30 preuves + 9 racines payload dans 8 anciens runs WTLAKE** supprimés
  lors du ménage autorisé du 2026-09-26. Cause retrouvée :
  [`qa-documentaire-20261011-v1.json`](qa-documentaire-20261011-v1.json), commande historique et
  résultat `REMOVED_TARGETS=36; ALL_GONE=True`. Chemins/hashes historiques conservés dans
  `release-tracking-v1.json` ; fichiers toujours absents, octets legacy non certifiables.
  Aucune vérification ingame nécessaire pour ces chemins ; QA WTLAKE du 26 septembre disponible.
- Liste précise des contrôles et commandes : [`VERIFICATIONS_INGAME.md`](VERIFICATIONS_INGAME.md).
  Les 4 réserves visuelles nommées sont levées ; la table reste un inventaire de contrôles
  facultatifs q/pluie/nuit/pause, avec variantes et recoupements. Pluie AR1100/AR2500/AR2600/AR2700 :
  déclaration de contrôle au niveau du lot swamp retrouvée ; confirmation nominative possible
  avant de demander une nouvelle visite.
- OH6460 : rendu x4 accepté via le tileset OH8100 installé. Son propre build n'est pas installé,
  car il écraserait OH8100 ; ce n'est pas une QA manquante.
- Préflight décor : classification WT5000A-D AR5000/AR5203 et politique WTLAVA-D à réconcilier avec
  les sélections ; traitements visuels acceptés. Détails : `../pipeline/PROBLEMES_A_RESOUDRE.md`.
- Performance/transition renderer : qualification générale distincte des acceptations visuelles ;
  aucune performance finale ni compatibilité release déduite ici.
- Nettoyage exécuté 2026-10-12 : [`NETTOYAGE_RUNS_20261012.md`](NETTOYAGE_RUNS_20261012.md),
  reçu `cleanup-executed-20261012-v1.json`. 14 217 médias/binaires retirés des 29 dossiers
  autorisés, aucun échec ; 4,454 Go logiques, 3,396 Go d’allocation associée après liens physiques.
  **Espace libre sur G : +2,980 Go pendant l’opération** (delta incluant l’activité du volume).
  822 fichiers conservés vérifiés par SHA256 ; 19 cas ambigus et 650 dossiers sélectionnés/acceptés
  ou dépendances conservés. Décisions QA et travail validé inchangés ; release non modifiée par
  ce nettoyage. Manifestes des essais retirés conservés, sans prétendre que leurs binaires existent.
  Décision finale utilisateur : garder les 19 cas ambigus (252,34 Mo) ; aucune suppression
  supplémentaire à planifier pour ces dossiers.

## Mentions dépassées remplacées

- « NON injecté », « QA à faire », « en attente » supprimés lorsqu'une installation/acceptation
  ultérieure est déjà consignée ; paramètres et références techniques utiles conservés.
- WTLAKE AR0046, AR0300, AR0900, AR0512, AR1604, AR2300 : anciens états ambigus/bloqués remplacés
  par le verdict du lot 2026-09-26 ; autres WED du lot reliés à la même preuve.
- AR2300 : repagination stable validée 2026-09-05, correction locale validée 2026-09-06 ; le crash
  historique n'est plus présenté comme un défaut courant.
- AR3000 : runtime + raccords RGB validés 2026-10-11,
  `../pipeline/water/manifests/ar3000-runtime-and-all-rgb-edges-user-qa-20261011-v1.json` ; météo non spécifiée.
- AR1000N : débordement de noms PVRZ corrigé/revalidé 2026-08-18 ; ancien risque latent clos.
- AR0601 / AM0602J : ancienne réserve de boucle levée, QA 2026-09-02 ;
  `../animations/index/qa-decisions/AM0602J/2026-10-11-preserved-historical-am0602j-v1.json`.
