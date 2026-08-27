# Opcodes ajoutés et documentés en version 2.0

> **Statut :** Officiel Beamdog - paraphrase technique  
> **Dernière vérification :** 2026-08-27

## Opcode 346 - Saving Throw vs. School

But : appliquer un modificateur de jet de sauvegarde limité à une école de magie.

Paramètres documentés :

- **Paramètre 1** : valeur du modificateur ;
- **Paramètre 2** : `0` pour un modificateur cumulatif, `1` pour une valeur fixe ;
- **MSpecial** : école ciblée.

Valeurs d’école : `0` aucune, `1` abjuration, `2` conjuration, `3` divination, `4` enchantement, `5` illusion, `6` invocation, `7` nécromancie, `8` transmutation, `9` généraliste, `10` magie sauvage.

Précaution Beamdog : l’effet reste attaché à la cible jusqu’à suppression et ne possède pas le mode permanent irréversible habituel. Éviter d’empiler inutilement de nombreuses instances.

## Opcode 365 - Make Unselectable

But : empêcher le joueur de sélectionner une créature et de lui donner des ordres.

- **Paramètre 1 - Disable Conversation** : `0` désactive l’option de dialogue ; `1` ne la désactive pas.
- **Paramètre 2 - Disable AI** : `0` désactive l’IA normale ; `1` la laisse active.
- **MSpecial** : `0` cercle violet ; `1` cercle vert.

Les intitulés sont contre-intuitifs : dans le document, `0` active bien la désactivation. Un test fonctionnel doit couvrir sélection, dialogue, scripts automatiques et restauration de l’état.

## Opcode 344 - Enchantment Bonus

But : changer le niveau d’enchantement effectif des attaques de la cible, avec filtrage IDS.

- **Paramètre 1** : entrée IDS ;
- **Paramètre 2** : fichier IDS ;
- **Paramètre 3** : main ciblée (`0` arme courante, `1` main principale, `2` main secondaire, `3` les deux) ;
- **Paramètre 4** : `0` toutes les armes, `1` type d’objet spécifique ;
- **MSpecial** : nouveau niveau d’enchantement.

Le PDF affiche plusieurs valeurs `0` successives pour les fichiers IDS, ce qui ressemble à une erreur de mise en page ou de numérotation. Ne pas recopier cette table telle quelle dans du code : vérifier la table effective dans Near Infinity/IESDP et tester les cas EA, GENERAL, RACE, CLASS, SPECIFIC, GENDER et ALIGNMENT.

## Stratégie de test minimale

- créer une ressource de test isolée par opcode ;
- tester application, retrait, sauvegarde/rechargement et changement de zone ;
- vérifier le cumul et la priorité avec un autre effet du même type ;
- inspecter la ressource finale dans Near Infinity ;
- consigner la version exacte de BG2:EE.

## Sources
- Release notes officielles 2.0, section Modding Features: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
