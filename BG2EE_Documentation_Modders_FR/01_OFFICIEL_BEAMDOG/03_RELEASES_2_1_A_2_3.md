# Versions 2.1 à 2.3 - compléments utiles aux moddeurs

> **Statut :** Officiel Beamdog - synthèse  
> **Dernière vérification :** 2026-08-27

## Version 2.1

La documentation 2.1 ne contient pas un nouveau chapitre d’API comparable à celui de 2.0. Elle signale toutefois une correction importante : les mods qui ajoutent des kits ne doivent plus casser à cause de `25STWEAP.2da`. Ce point est surtout une information de compatibilité et non une méthode d’installation.

## Version 2.2

La principale fonction de modding documentée est le chargement des fichiers `M_*.lua` placés dans `override`. Ce mécanisme permet d’ajouter ou de redéfinir des tables et variables Lua sans remplacer l’intégralité de `BGEE.lua`.

Exemple d’usage typique : ajouter des portraits à la table existante ou changer une seule entrée de couleur. Le bénéfice principal est la résistance aux mises à jour du jeu : le mod conserve seulement son delta au lieu de distribuer une copie complète d’un fichier système.

Limite explicitement signalée par Beamdog : ce mécanisme ne permet pas de patcher `UI.menu` de façon incrémentale. `UI.menu` reste traité comme un fichier global.

## Version 2.3

Le document consolidé 2.0-2.3 sert surtout à regrouper les notes précédentes et les correctifs. Il ne remplace pas la lecture du chapitre technique 2.0 et de la fiche `M_*.lua` pour comprendre le modding.

## Conséquence pour un projet moderne

- Ne distribuer un `BGEE.lua` complet que lorsqu’il n’existe vraiment aucune autre solution.
- Préférer `M_<nom_du_mod>.lua` pour des ajouts ciblés.
- Considérer `UI.menu` comme une ressource à fort risque de conflit.
- Utiliser WeiDU ou un patcher explicite pour détecter la version et éviter les écrasements silencieux.

## Sources
- Release notes 2.1: https://items.gog.com/releasenotes_2_1.pdf
- Release notes 2.2: https://items.gog.com/releasenotes_2_2.pdf
- Guide officiel M_*.lua: https://forums.beamdog.com/discussion/57210/m-lua-files-and-bgee-lua
- Document consolidé 2.0-2.3: https://files.beamdog.com/files/BG-2.0-2.3-ReleaseNotes.pdf
