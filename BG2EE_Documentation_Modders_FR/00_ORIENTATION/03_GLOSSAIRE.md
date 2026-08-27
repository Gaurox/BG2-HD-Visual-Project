# Glossaire technique BG2:EE

> **Statut :** Synthèse technique  
> **Dernière vérification :** 2026-08-27

## Ressources et chargement

**ResRef** — Identifiant court d’une ressource Infinity Engine. Historiquement limité à huit caractères dans de nombreux contextes. Le nom et l’extension désignent une ressource, mais de nombreuses références internes ne stockent que le ResRef.

**override** — Répertoire prioritaire où le moteur cherche des ressources remplaçant celles des archives du jeu. Pratique pour tester, mais dangereux comme stratégie d’installation brute lorsqu’un mod doit cohabiter avec d’autres.

**KEY / BIF** — Couple d’index et d’archives contenant une grande partie des ressources installées. La mise à jour 2.7 a corrigé une erreur d’indexation lors de la reconstruction de BIF, ce qui peut affecter les outils qui supposaient l’ancien comportement.

## Scripts et données

**IDS** — Table d’identifiants numériques vers des noms symboliques. Exemples : `ACTIONS.IDS`, `TRIGGER.IDS`, `CLASSCAT.IDS`.

**2DA** — Table texte bidimensionnelle utilisée pour externaliser des règles, des listes ou des paramètres.

**Opcode** — Effet moteur appliqué par un sort, un objet ou une autre ressource.

**Trigger** — Condition lue par un script. Un trigger ne produit pas l’action lui-même ; il décide si une branche doit s’exécuter.

**Action** — Instruction exécutée par un script.

**SPL / ITM / CRE / ARE** — Respectivement sort, objet, créature et zone.

## Graphismes

**BAM** — Conteneur d’images animées ou organisées en cycles. Utilisé pour les créatures, effets, icônes, boutons et polices.

**Cycle** — Suite logique de références de frames. Plusieurs cycles peuvent partager des frames.

**Centre de frame / offset** — Coordonnées d’ancrage permettant au moteur d’aligner visuellement une frame. Leur conservation est critique lors d’un upscale.

**BAM V1** — Format à palette, avec frames éventuellement compressées en RLE.

**BAM V2** — Format Enhanced Edition dont les blocs de pixels sont stockés dans des pages `PVRZ`.

**PVRZ** — Texture PVR compressée avec zlib, utilisée notamment par BAM V2, MOS V2 et TIS basés sur PVRZ.

**TIS / WED** — Le TIS contient les graphismes en tuiles d’une zone ; le WED décrit leur organisation, les portes, overlays et informations de région visuelle.

## Interface

**UI.menu** — Définition texte de l’interface depuis la branche 2.0.

**BGEE.lua** — Tables et variables Lua utilisées par l’interface et le jeu. Le nom est historique et peut être utilisé par plusieurs Enhanced Editions.

**M_*.lua** — Fichiers Lua additionnels chargés depuis `override` à partir de la version 2.2, conçus pour modifier des tables sans remplacer tout `BGEE.lua`.

## Outils

**Near Infinity** — Explorateur et éditeur Java de ressources Infinity Engine.

**DLTCEP** — Éditeur/validateur de ressources Infinity Engine.

**WeiDU** — Outil de développement, patching, installation et distribution de mods compatibles entre eux.

**IESDP** — Projet communautaire de description des structures et comportements de l’Infinity Engine.

## Sources
- IESDP - notes et formats: https://gibberlings3.github.io/iesdp/file_formats/index.htm
