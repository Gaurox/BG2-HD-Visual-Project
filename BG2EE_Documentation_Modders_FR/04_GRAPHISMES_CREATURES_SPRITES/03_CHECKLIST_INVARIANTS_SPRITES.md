# Checklist des invariants d’un sprite compatible

> **Statut :** Synthèse pratique fondée sur les formats  
> **Dernière vérification :** 2026-08-27

## Structure

- même nombre de cycles, sauf conversion explicitement prévue ;
- même ordre des cycles ;
- même nombre d’indices par cycle ;
- même répétition de frames dans la table de lookup ;
- même correspondance orientation/action ;
- aucune frame orpheline ou index hors limites.

## Géométrie

- largeur et hauteur transformées selon le facteur choisi ;
- centre X et centre Y transformés avec la même convention d’arrondi ;
- origine stable d’une frame à l’autre ;
- absence de saut d’un pixel dû à des arrondis alternés ;
- bounding box et marges transparents cohérents ;
- points de contact visuels stables : pieds, arme, ombre, casque.

## Pixels et transparence

- transparence conservée ;
- aucune frange de couleur autour de la silhouette ;
- palette conservée si la cible exige une palette identique ;
- alpha prémultiplié/non prémultiplié traité de manière constante ;
- absence de pixel opaque dans les marges ;
- compression sans corruption.

## BAM V2 / PVRZ

- pages existantes et correctement nommées ;
- rectangles sources dans les limites ;
- rectangles destinations dans la frame ;
- pas de chevauchement involontaire ;
- pas de trou entre blocs ;
- texture conforme au format attendu ;
- taille et compression acceptées sur la plateforme cible.

## Ressources composées

Pour les sprites avec armures, casques, armes ou plusieurs couches :

- mêmes conventions d’échelle sur toutes les couches ;
- mêmes centres et arrondis ;
- aucune dérive cumulative ;
- ordre de rendu inchangé ;
- test de chaque équipement représentatif ;
- test des orientations diagonales et animations rapides.

## Validation automatique

- comparer manifeste source/cible ;
- vérifier les nombres de cycles et frames ;
- vérifier que `centre_cible = f(centre_source)` selon une règle unique ;
- recomposer les frames et produire des diff visuels ;
- détecter les pixels hors cadre ;
- générer un rapport PASS/FAIL par ressource.

## Sources
- IESDP BAM V1: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v1.htm
- IESDP BAM V2: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v2.htm
