# Publication, installation et compatibilité

> **Statut :** Synthèse pratique  
> **Dernière vérification :** 2026-08-27

## Contenu d’une version publiable

- archive propre sans caches ;
- README d’installation ;
- versions de jeu prises en charge ;
- avertissements de compatibilité ;
- changelog ;
- licence de chaque composant ;
- hashes ;
- procédure de désinstallation ;
- journal de tests ;
- source ou scripts de génération lorsque distribuables.

## Installation

Privilégier WeiDU pour les changements structurés et l’ordre de mods. Pour les ressources volumineuses, l’installateur peut vérifier et copier des fichiers, mais doit garder un manifeste et éviter les écrasements non signalés.

## Mise à jour

Une mise à jour du mod doit :

- détecter l’ancienne version ;
- migrer ou remplacer proprement ses propres fichiers ;
- ne pas supprimer les fichiers d’un autre mod ;
- conserver une sauvegarde des ressources globales modifiées ;
- invalider les caches si nécessaire ;
- relancer les validations essentielles.

## Compatibilité déclarée

Distinguer :

- **testé** ;
- **probablement compatible** ;
- **non testé** ;
- **incompatible connu**.

Ne pas annoncer une compatibilité uniquement parce que l’installation se termine sans erreur.

## Distribution des sources Beamdog

Cette archive renvoie vers les téléchargements officiels. Ne pas réinclure les PDF, symboles ou archives Beamdog dans une distribution sans vérifier les droits de redistribution applicables.

## Sources
- WeiDU: https://weidu.org/WeiDU/README-WeiDU.html
- Beamdog Files: https://files.beamdog.com/
