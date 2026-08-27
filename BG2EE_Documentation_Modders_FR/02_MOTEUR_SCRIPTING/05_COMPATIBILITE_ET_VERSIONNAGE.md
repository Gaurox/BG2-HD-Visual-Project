# Compatibilité moteur et versionnage

> **Statut :** Synthèse pratique fondée sur les sources officielles  
> **Dernière vérification :** 2026-08-27

## Pourquoi versionner explicitement

Les fonctions de modding ont été introduites progressivement. Un mod qui fonctionne sur 2.0 peut rencontrer une différence de chargement, de stockage ou d’outil sur 2.7. La version doit être une donnée de diagnostic, pas une information implicite.

## Matrice minimale

| Axe | Cas à couvrir |
|---|---|
| Version moteur | au moins la version officiellement ciblée ; si nécessaire 2.6.6 et 2.7.3 |
| Plateforme | Windows ; Linux si supporté ; mobile seulement si annoncé |
| Installation | propre ; avec le mod ; avec un mod concurrent représentatif |
| Sauvegarde | nouvelle partie ; sauvegarde existante ; changement de zone |
| Langue | langue principale ; une langue avec `dialog.tlk` distinct si le mod écrit du texte |
| Ressources | override direct ; ressources patchées ; archives reconstruites si applicable |

## Détection et journalisation

Le diagnostic du mod devrait consigner :

- version du jeu ;
- plateforme et architecture ;
- langue ;
- ordre d’installation WeiDU ;
- hash des ressources critiques générées ;
- présence de fichiers UI globaux ;
- présence d’une extension native ou d’InfinityLoader.

## Compatibilité 2.7

La correction BIF de 2.7 justifie un test spécifique pour tout outil qui reconstruit, indexe ou lit des archives. Les changements de dossiers mobiles exigent de distinguer `install:/` et `home:/`. Les fichiers `dialog.tlk` suivent un chemin particulier et ne doivent pas être traités comme une simple ressource d’override.

## Règle de décision

Un comportement non documenté mais stable dans un test ne doit pas être présenté comme garanti. Le documenter comme « observé sur version X », avec un test reproductible, facilite la maintenance future.

## Sources
- Release notes 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
- Annonce 2.7: https://forums.beamdog.com/discussion/90724/2-7-baldurs-gate-icewind-dale-ees-update-new-languages-improved-cloud-support-mobile-modding
