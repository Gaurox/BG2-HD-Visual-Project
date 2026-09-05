# Architecture du système UI depuis la version 2.0

> **Statut :** Officiel Beamdog - synthèse  
> **Dernière vérification :** 2026-08-27

## Éléments principaux

### `UI.menu`

Fichier texte définissant les menus et contrôles. Il décrit les blocs, positions, dimensions, ressources graphiques, textes, styles et actions.

### `BGEE.lua`

Fichier Lua contenant des tables, couleurs, styles et données utilisées par l’interface. Le guide 2.0 propose de l’exporter avec Near Infinity pour l’étudier ou le modifier.

### `M_*.lua`

Depuis 2.2, fichiers Lua supplémentaires chargés depuis `override`. Ils permettent d’appliquer des modifications ciblées à `BGEE.lua` sans distribuer une copie complète.

### Ressources associées

- BAM et PNG pour les graphismes ;
- TTF pour les polices ;
- chaînes de traduction ou StrRef ;
- fonctions Lua exposées par le moteur.

## Flux de développement conseillé

1. Activer le mode d’édition dans `baldur.lua`.
2. Exporter une copie de travail de `UI.menu` et, si nécessaire, `BGEE.lua`.
3. Localiser un contrôle avec F11 puis Tab.
4. Modifier une petite section.
5. Recharger avec F5.
6. Fermer le jeu avant toute suppression ou restauration du fichier.
7. Reporter la modification dans une installation reproductible.

## Séparation des responsabilités

- **géométrie et déclaration de contrôle** : `UI.menu` ;
- **tables et styles globaux** : `BGEE.lua` ou `M_*.lua` ;
- **images et polices** : ressources séparées dans `override` ou installées par WeiDU ;
- **installation et conflits** : gérés par le mod, idéalement avec détection et sauvegarde.

## Limite structurelle

Beamdog a explicitement précisé que `M_*.lua` ne permet pas de patcher `UI.menu` par fragments. Toute distribution d’un `UI.menu` complet ou tout patch textuel sur ce fichier doit donc être considéré comme sensible aux conflits.

## Sources
- Guide UI officiel: https://forums.beamdog.com/discussion/48994/the-new-ui-system-how-to-use-it
- Guide M_*.lua: https://forums.beamdog.com/discussion/57210/m-lua-files-and-bgee-lua
- Release notes 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
