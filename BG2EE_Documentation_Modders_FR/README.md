# Documentation BG2:EE pour développeurs et moddeurs - synthèse française

> **Statut :** Index de l’archive ; contenu original de synthèse  
> **Dernière vérification :** 2026-08-27

Cette archive transforme la documentation technique disponible autour de **Baldur’s Gate II: Enhanced Edition** en une base Markdown structurée et exploitable par un humain, un LLM ou un agent de développement.

## Ce que contient l’archive

- la documentation officiellement publiée par Beamdog sur les fonctions de modding ajoutées en 2.0 ;
- les guides officiels de l’interface `UI.menu`, de Lua et des fichiers `M_*.lua` ;
- les informations officielles récentes de la branche 2.7 utiles aux moddeurs ;
- un inventaire du paquet officiel **Beamdog Creature Process** et des fichiers de debug mis à disposition ;
- des annexes communautaires clairement séparées : IESDP, Near Infinity, DLTCEP et WeiDU ;
- des procédures de travail, de test et de migration adaptées à un projet technique moderne ;
- un chapitre spécifique aux sprites et à un pipeline d’upscale x2/x4.

## Nature du contenu

Les textes de Beamdog ne sont **pas reproduits intégralement**. Ils sont paraphrasés, restructurés et condensés en français. Les identifiants d’API, noms de fichiers, signatures de fonctions et petits exemples techniques sont conservés lorsqu’ils sont nécessaires à la compréhension.

Chaque fichier précise son statut :

- **Officiel Beamdog** : page, PDF ou annonce publiée par Beamdog ;
- **Officiel - forum Beamdog** : guide ou précision publiée par un membre identifié de l’équipe ;
- **Communautaire de référence** : source reconnue mais non officielle ;
- **Synthèse pratique** : recommandations déduites des sources, explicitement signalées comme telles.

## Commencer

1. Ouvrir [`INDEX.md`](INDEX.md).
2. Choisir un parcours dans [`00_ORIENTATION/02_PARCOURS_PAR_PROFIL.md`](00_ORIENTATION/02_PARCOURS_PAR_PROFIL.md).
3. Pour un travail sur les sprites, commencer par [`04_GRAPHISMES_CREATURES_SPRITES/README.md`](04_GRAPHISMES_CREATURES_SPRITES/README.md).
4. Pour modifier l’interface, commencer par [`03_INTERFACE_UI_LUA/01_ARCHITECTURE_UI.md`](03_INTERFACE_UI_LUA/01_ARCHITECTURE_UI.md).
5. Pour développer ou empaqueter un mod, lire aussi la section `05_OUTILS_ET_FORMATS_COMMUNAUTAIRES`.

## Limite importante

Beamdog n’a pas publié un SDK exhaustif décrivant tous les formats internes de BG2:EE. Les formats détaillés (`BAM`, `TIS`, `WED`, `ARE`, `CRE`, `ITM`, etc.) restent principalement documentés par l’IESDP et implémentés dans des outils communautaires. L’archive maintient cette séparation afin de ne pas présenter une information communautaire comme officielle.

## Sources
- Portail officiel Beamdog Files: https://files.beamdog.com/
- Release notes officielles 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
