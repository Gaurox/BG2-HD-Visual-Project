# Patch 2.7 - conséquences pour le modding

> **Statut :** Annonce officielle Beamdog, juin 2026  
> **Dernière vérification :** 2026-08-27

## Portée générale

Beamdog a publié la mise à jour 2.7 pour BG:EE, BG2:EE et IWD:EE sur PC et mobile. Pour les moddeurs, les éléments les plus importants ne sont pas de nouveaux opcodes, mais les changements de stockage, d’import/export et de compatibilité avec les outils.

## Correction d’indexation BIF

Le patch corrige une erreur « off-by-one » dans les BIF reconstruits, erreur qui affectait certains outils communautaires. Un outil qui dépendait involontairement de l’ancien comportement doit donc être retesté. Pour un pipeline qui reconstruit ou inspecte des archives, il faut prévoir des jeux de test 2.6 et 2.7.

## Modding Android

- les fichiers utilisateur sont exportés vers un emplacement accessible, sous une structure `Documents/<jeu>` ;
- les sauvegardes et personnages peuvent être copiés entre Android et PC ;
- l’import se configure depuis l’interface du jeu ;
- les anciennes installations ayant de mauvaises permissions peuvent exiger une réinstallation, après sauvegarde des données ;
- les gros dossiers `override` bénéficient d’une optimisation visant à réduire les démarrages très longs.

## Modding iOS

Le répertoire `home:/` devient accessible via les outils de fichiers usuels. Les dossiers tels que `save`, `override`, `portraits`, `characters`, `sounds`, `scripts` ou `movies` peuvent être placés dans l’espace du jeu.

Point important : `dialog.tlk` n’est pas lu depuis `home:/override`. Il doit être placé sous `home:/lang/<code_langue>/dialog.tlk`.

## Recommandations de compatibilité

- enregistrer dans le diagnostic du mod la version exacte du jeu ;
- tester toute manipulation de BIF/KEY sur 2.7 ;
- ne pas supposer que les chemins PC, Android et iOS sont identiques ;
- séparer les ressources simples d’override des modifications de `dialog.tlk` ;
- fournir une procédure de sauvegarde avant toute réinstallation mobile.

## Sources
- Annonce officielle 2.7: https://forums.beamdog.com/discussion/90724/2-7-baldurs-gate-icewind-dale-ees-update-new-languages-improved-cloud-support-mobile-modding
- Fichiers officiels 2.7.3: https://files.beamdog.com/
