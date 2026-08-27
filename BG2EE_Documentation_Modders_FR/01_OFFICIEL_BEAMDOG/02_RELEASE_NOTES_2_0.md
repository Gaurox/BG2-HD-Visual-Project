# Release notes 2.0 - carte de la documentation de modding

> **Statut :** Officiel Beamdog - synthèse des pages 23 à 31 du document  
> **Dernière vérification :** 2026-08-27

## Pourquoi ce document est central

Beamdog consacre une section explicite aux fonctions utilisables dans des créations de mods. Le document indique que Near Infinity ou DLTCEP sont nécessaires pour exploiter certains ajouts.

## Contenu technique

### Nouveaux opcodes

- `346` — modification des jets de sauvegarde selon une école de magie ;
- `365` — rendre une créature non sélectionnable ;
- `344` — modifier le niveau d’enchantement des attaques selon une cible IDS.

### Nouveaux triggers

Le document décrit notamment la détection d’un état modal, d’un niveau de catégorie de classe, d’un sort connu, d’une rencontre aléatoire forcée, de la classe inactive d’un personnage biclassé, d’une porte secrète détectée, d’une immunité à un niveau de sort et de l’activation du mode Histoire.

### Nouvelles actions

Les ajouts couvrent les minuteries aléatoires, la restauration de l’IA du groupe, un déplacement avec offset, le verrouillage du zoom, deux variantes de marche aléatoire et deux formes d’affichage de texte.

### Externalisations

Des comportements auparavant codés dans le moteur deviennent modifiables par ressources :

- réactions au pickpocket dans `PPBEHAVE.2da` ;
- chant de barde par défaut dans `BARDSONG.spl` ;
- icônes d’état via `STATDESC.2da` ;
- noms et rotation des sauvegardes via `SAVENAME.2da` ;
- échec d’incantation via `CONCENTR.2da`.

### Nouveau système d’interface

Le document fournit un mini-manuel pour :

- activer le mode d’édition ;
- déplacer et redimensionner les éléments ;
- recharger l’interface ;
- retrouver la ligne correspondante dans `UI.menu` ;
- changer les polices et styles ;
- comprendre un bloc `UI.menu` ;
- appeler ou afficher des valeurs Lua.

## Précautions

La documentation date de 2016. Elle décrit l’intention et la syntaxe de l’époque, pas toutes les contraintes actuelles. Toute fonction doit être testée sur une copie propre de la version cible, particulièrement depuis les évolutions 2.6 et 2.7.

## Sources
- PDF officiel 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
- Guide UI officiel: https://forums.beamdog.com/discussion/48994/the-new-ui-system-how-to-use-it
