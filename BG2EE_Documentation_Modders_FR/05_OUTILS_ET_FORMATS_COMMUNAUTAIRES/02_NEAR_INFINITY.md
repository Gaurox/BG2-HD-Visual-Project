# Near Infinity - inspection et édition des ressources

> **Statut :** Outil communautaire de référence  
> **Dernière vérification :** 2026-08-27

## Fonction

Near Infinity est un explorateur et éditeur de ressources Infinity Engine écrit en Java. Il permet de parcourir les archives du jeu, d’inspecter les structures et d’exporter ou modifier de nombreux formats.

## Usages recommandés

- confirmer qu’une ressource générée est lisible ;
- inspecter cycles, frames, centres et dimensions d’un BAM ;
- exporter `BGEE.lua` ou d’autres ressources ;
- comparer une ressource originale et une ressource patchée ;
- repérer les références entre objets ;
- vérifier les tables 2DA et fichiers IDS.

## Place dans un pipeline

Near Infinity est un validateur indépendant très utile, mais ne doit pas être l’unique test. Un fichier accepté par l’outil peut encore provoquer un problème d’affichage ou de logique dans le moteur.

## Routine de contrôle d’un BAM

1. Ouvrir l’original et noter version, cycles et frames.
2. Ouvrir la cible et comparer les mêmes compteurs.
3. Vérifier les centres et dimensions.
4. Prévisualiser chaque cycle.
5. Exporter quelques frames pour un diff externe.
6. Vérifier les PVRZ référencés si BAM V2.
7. Lancer le jeu avec un log et un cas de test.

## Automatisation

Pour un grand volume, l’inspection manuelle sert à établir une vérité de référence. Les contrôles répétitifs doivent ensuite être reproduits par script afin d’obtenir un rapport déterministe.

## Sources
- Dépôt Near Infinity: https://github.com/NearInfinityBrowser/NearInfinity
- Release notes Beamdog 2.0 qui recommande Near Infinity: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
