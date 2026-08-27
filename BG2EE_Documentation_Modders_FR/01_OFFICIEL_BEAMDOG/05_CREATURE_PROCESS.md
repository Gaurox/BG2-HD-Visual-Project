# Beamdog Creature Process - ce qui est officiellement établi

> **Statut :** Officiel Beamdog, portée limitée par les métadonnées publiées  
> **Dernière vérification :** 2026-08-27

## Description officielle vérifiée

Beamdog présente **Beamdog Creature Process** comme un exemple montrant comment une nouvelle créature a été ajoutée aux jeux Enhanced Edition de l’Infinity Engine. BG2:EE est explicitement inclus dans la liste des jeux concernés. L’archive officielle est distribuée au format ZIP.

## Ce que cette publication permet raisonnablement d’attendre

Le paquet est pertinent pour comprendre un pipeline de création et d’intégration d’animation de créature, donc potentiellement :

- la préparation des rendus ;
- l’organisation des animations ;
- la conversion vers des ressources compatibles avec le moteur ;
- la liaison entre ressources graphiques et définition de créature/animation.

Ces points sont une **interprétation de la finalité du paquet**, pas un inventaire garanti de son contenu. Le portail ne publie pas, dans sa description, une liste détaillée des fichiers internes.

## Limite de cette retranscription

L’archive binaire officielle n’est pas recopiée dans le présent ZIP. Cette documentation fournit le lien, la portée vérifiée et une méthode d’analyse, mais ne prétend pas décrire des fichiers internes qui n’ont pas été inspectés.

## Procédure d’analyse recommandée après téléchargement

1. Extraire l’archive dans un dossier isolé.
2. Générer un inventaire récursif : chemins, tailles, extensions et hash SHA-256.
3. Identifier les scripts, projets 3D, images sources, fichiers BAM/PVRZ et documents.
4. Repérer les conventions de nommage des orientations et séquences.
5. Relever les dimensions, centres et offsets des frames finales.
6. Comparer les ressources finales à leur source de rendu.
7. Documenter les outils requis et leur version.
8. Ne réutiliser que les concepts et scripts dont la licence ou l’autorisation est claire.

## Utilité pour un pipeline d’upscale

Le paquet doit être étudié surtout pour ses **invariants d’intégration** : nombre de cycles, ordre des frames, ancrages, nommage, découpe et dépendances. L’upscale lui-même peut être externe ; la compatibilité moteur dépend davantage de la reconstruction fidèle de ces invariants.

## Sources
- Page officielle Beamdog Files: https://files.beamdog.com/
- Archive officielle: https://files.beamdog.com/files/BeamdogCreatureProcess.zip
