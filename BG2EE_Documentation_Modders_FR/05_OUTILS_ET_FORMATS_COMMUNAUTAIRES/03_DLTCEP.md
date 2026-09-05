# DLTCEP - éditeur et validateur Infinity Engine

> **Statut :** Outil communautaire, non officiel Beamdog  
> **Dernière vérification :** 2026-08-27

## Fonction

DLTCEP est un éditeur, vérificateur et explorateur de fichiers pour les jeux Infinity Engine. Beamdog le cite avec Near Infinity comme outil permettant d’utiliser les fonctions de modding 2.0.

## Intérêt

- édition structurée de ressources ;
- vérification de champs et références ;
- deuxième lecture indépendante d’un fichier ;
- comparaison de comportement avec Near Infinity.

## Usage prudent

- travailler sur une copie ;
- vérifier que la version de DLTCEP et ses données prennent en charge la branche EE ciblée ;
- ne pas enregistrer un lot complet sans diff ;
- conserver les fichiers originaux et les logs ;
- valider ensuite dans le moteur.

## Near Infinity ou DLTCEP ?

Le meilleur choix n’est pas exclusif. Near Infinity est souvent pratique pour la navigation et la prévisualisation ; DLTCEP peut servir de second validateur ou d’éditeur spécialisé. Pour un pipeline automatisé, les deux restent des contrôles externes, pas la source de vérité de production.

## Sources
- Page DLTCEP: https://www.gibberlings3.net/mods/tools/dltcep/
- Release notes Beamdog 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
