# Avancement des validations projectiles —2026-11-10

- Projection chiffrée : `index/validation-progress-current.json` ;autorité QA/installation : `index/work-tracking.json` ;analyse source : `analysis/20261109-bilan-validations-v13/`.
- Les3couleurs sont **acceptées** :HLYMITE rouge194,SHAIR4/130,SHEARTH6/137. Confirmation utilisateur conservée dans le bilanJSON ;preuve initiale immuable [acceptance.json](analysis/final-four-colours-accepted-20261109-v1/acceptance.json). Aucun nouvel essai demandé.

| Domaine | Acquis | Limite |
|---|---|---|
| Inventaire |243PRO stock,107BAM,175contextes image/palette ;77IDs moteur sansPRO suivis,33référencés | Un ID/PRO partagé n'est pas une nouvelle image. |
| Images connues |167contextes avec sortie réutilisable(86acceptés+81packs palette vérifiés),8masques natifs ;0sortie manquante identifiée |175/175contextes couverts côté production/disposition ;pas une QA de tous consommateurs. |
|10omissions de scope natif |10raccordées/installées | Les6premières routes+3couleurs ont des drawsHD observés ;SPSCORIC qualifié statiquement9cycles,QA visuelle antérieure conservée sans nouveau tir. |
| QA visuelle par propriétaire |39PRO et10IDs moteur avec acceptation des composants observés | Portées précises,preuves mutualisables àcontrat compatible ;pas39chaînes intégrales ni204essais à imposer. |
| Lots récents |Tous les exemples CLUA acceptés,puis6nouveaux raccordsHD acceptés,puis3couleurs acceptées |0essai manuel préparé restant ;aucun retest de composant acquis inchangé. |
| Installation |DLL `5A1559B5…3106612B`,catalogue743ressources/72563backings ;trace désactivée |743noms de catalogue≠743projectiles ;images/PRO/registre etautres réglages conservés. |
| Release | Inchangée | Aucune intégration release déduite de la QA ou de l'installation. |

## Travail restant utile

1. **Réconciliation technique automatisée des propriétaires** avec les preuves communes :pack exact,palette/blend,géométrie,cycles/timing etchemin de rendu. Les classifications conservatrices du générateur ne constituent pas une liste d'essais manuels.
2. Traiter uniquement les exceptions réellement découvertes. `LIGHTSTO` référence toujours `MAGMIS` absent ;aucun pilote normal SPL/ITM/PRO trouvé. Préserver natif,sans inventer une substitution ou une production.
3. QA manuelle uniquement pour une nouvelle variante visuelle ou une anomalie reproductible. Déplacement interpolé `PROJ-MOTION-001` toujours reporté ;release séparée.

## Lecture des anciens compteurs

- Projection dominante actuelle :161réemplois/contrats,54routes moteur,27natifs,1dépendance absente.99PRO portent encore `integration=verified-static` ;d'autres composants ont leur preuve installée/observée distincte. Ces groupes ne sont ni des liens déclarés cassés ni un nombre de validations visuelles à refaire.
- Les anciens «100complets/124partiels/4imagesmanquantes» etlibellés d'enfants sont historiques. La correction des index0x214/0x21a a corrigé150arêtes/111PRO ;les preuves natives récentes ne sont pas toutes projetées dans la vieille classification.
- Aucun pourcentage fiable de **chaînes entièrement validées** n'est calculé à partir des seuls175contextes ou39accordsPRO. La suite consiste à fermer les contrats par familles etréemploi de preuves.

## Vérifications retenues pour le commit

-8tests du suivi passants ;5suites CPU/GPU du moteur passantes sur la DLL installée.
-1624contrats natifs pourles6premiers raccords ;1776pourles4derniers,avant+aprèsinstallation.
-528+830backings existants vérifiés SHA ;3transferts de palette vérifiés sur765nœudsRGB,identité neutre,cacheGPU etretour aux couleurs d'origine ;anciennes palettesSHAREA conservées.
- Traces :HD/masques/phasesimpaires surles6premières ressources ;HD+palettes réalisées liées surles3couleurs. MasqueSHEARTH non observé,drawliveSPSCORIC non revendiqué. Les données manquantes ne deviennent pas automatiquement des demandes de retest.
