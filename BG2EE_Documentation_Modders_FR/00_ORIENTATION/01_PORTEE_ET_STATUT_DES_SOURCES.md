# Portée, autorité et limites des sources

> **Statut :** Méthodologie de l’archive  
> **Dernière vérification :** 2026-08-27

## Niveaux d’autorité

### 1. Publication officielle Beamdog

Ce niveau regroupe le portail `files.beamdog.com`, les PDF de release notes et les annonces de mise à jour publiées par Beamdog. C’est la base la plus solide pour savoir qu’une fonction existe et pour comprendre son intention initiale.

### 2. Guide publié sur le forum officiel par un membre de l’équipe

Les guides sur `UI.menu` et `M_*.lua` ont été publiés sur le forum Beamdog par Dee, alors membre de l’équipe. Ils sont traités ici comme documentation officielle complémentaire. Ils restent toutefois attachés à leur époque et ne constituent pas un contrat d’API versionné.

### 3. Documentation communautaire de référence

L’IESDP, Near Infinity, DLTCEP et WeiDU ne sont pas des produits Beamdog. Ils fournissent néanmoins la plus grande partie des spécifications réellement utilisables pour créer des outils ou des mods complexes.

### 4. Synthèses et recommandations de cette archive

Les checklists, propositions d’arborescence, procédures de test et conseils pour l’upscale sont des déductions pratiques. Elles sont conçues pour réduire les risques, mais elles ne remplacent pas un test dans le moteur.

## Versions concernées

La documentation de modding la plus détaillée a été publiée pour la branche **2.0**, complétée en **2.2** par `M_*.lua`. La branche **2.7**, publiée en juin 2026, ajoute surtout des changements de compatibilité, de stockage et de modding mobile. La présence de fichiers de debug officiels pour **2.7.3.0** confirme que cette branche est aujourd’hui une cible technique importante.

## Règle de lecture

- Une fonction documentée en 2.0 doit être testée sur la version cible actuelle.
- Une absence dans la documentation Beamdog ne signifie pas forcément que le moteur ne sait pas faire quelque chose.
- Une information IESDP doit être confrontée à un fichier réel et, si possible, à l’implémentation de Near Infinity.
- Une hypothèse sur les sprites doit être validée par comparaison des cycles, frames, centres et ressources dépendantes avant/après transformation.

## Ce qui n’est pas fourni officiellement

Il n’existe pas, dans les sources recensées, de manuel Beamdog unique et exhaustif couvrant tous les formats binaires, toutes les limites du moteur, le chargement exact des ressources, les priorités d’override et les invariants de chaque animation. C’est précisément le rôle des annexes communautaires de cette archive.

## Sources
- Beamdog Files: https://files.beamdog.com/
- Annonce officielle 2.7: https://forums.beamdog.com/discussion/90724/2-7-baldurs-gate-icewind-dale-ees-update-new-languages-improved-cloud-support-mobile-modding
- IESDP: https://gibberlings3.github.io/iesdp/site_info/iesdpfaq.htm
