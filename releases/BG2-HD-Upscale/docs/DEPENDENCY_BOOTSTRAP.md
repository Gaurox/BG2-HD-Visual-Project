# Contrat de dependances et futur bootstrap

Ce document definit le comportement de `Install-BG2HD.exe`. Il est construit
avec chaque archive BG2HD et lance le script controle `bg2hd/tools/Install-BG2HD.ps1`.
Il n'embarque ni EEex ni InfinityLoader.

Pour l'ordre global d'implementation et l'integration de nouveau contenu,
utiliser le [contrat installeur et upscales](INSTALLER_AND_UPSCALE_WORKFLOW.md).

## Perimetre

Le contrat cible BG2EE Steam 2.7.3.0 sous Windows x64. Il ne rend pas Linux,
Proton, Steam Deck, macOS ou une autre boutique supportes. EEex indique que
Proton/Wine peut fonctionner, mais l'integration BG2HD actuelle utilise
PowerShell et les raccourcis COM Windows ; une voie Proton devra etre validee
separement.

La source machine est `manifests/dependency-bootstrap.json`. Les empreintes du
jeu et le contrat de lancement Steam restent dans
`manifests/runtime-compatibility.json`.

## Ordre impose

1. Verifier le jeu cible, le layout d'executables et l'absence de processus
   Baldur/InfinityLoader.
2. Verifier le contrat save-neutral et l'empreinte de `M_IEEE.lua` ; toute
   divergence bloque l'installation avant modification du jeu.
3. Verifier le runtime Microsoft Visual C++ x64 ; s'il manque, afficher le
   lien Microsoft officiel, sans installation automatique.
4. Classer EEex avant de lancer `setup-bg2hd.exe`.
5. Seulement si EEex est absent et que l'utilisateur l'autorise, telecharger
   l'archive officielle figee ou accepter une copie locale de cette archive.
6. Verifier strictement son nom, sa taille et son SHA-256, puis lancer
   l'installeur officiel EEex hors de toute execution WeiDU BG2HD.
7. Revalider EEex, lancer `setup-bg2hd.exe`, puis verifier le shim Steam et le
   garde save-neutral effectivement installes.

Le bootstrap ne doit jamais installer, mettre a jour ou desinstaller EEex de
maniere silencieuse. Il ne doit jamais lancer un second WeiDU pendant que
WeiDU BG2HD est actif.

L'installeur officiel EEex conserve son interface et demande le dossier du jeu.
Apres sa fermeture, BG2HD controle de nouveau l'installation avant d'ouvrir
WeiDU. Une annulation, un code de sortie anormal ou une empreinte de binaire non
conforme arrete le flux sans ecriture BG2HD. `InfinityLoader.db` est un cache de
patterns propre a l'executable detecte ; il est declare mutable et n'est donc pas
compare a une empreinte figee.

## Etats EEex

| Etat | Definition | Action BG2HD |
|---|---|---|
| `absent` | Aucun indice EEex/InfinityLoader | Proposer l'installeur officiel |
| `inactive` | Composants et runtime retires, sources WeiDU officielles encore presentes apres retour vanilla | Proposer l'installeur officiel |
| `compatible` | composants 0/1 dans `WeiDU.log`, chemins requis et toutes les empreintes acceptees | Ne rien modifier et continuer |
| `partial` | Une partie seulement des indices requis est presente | Stopper, demander une reparation EEex |
| `unknown_or_changed` | EEex existe mais est d'une version/empreinte non admise | Stopper sans ecriture |
| `game_process_open` | Baldur ou InfinityLoader est encore ouvert | Stopper sans ecriture |

Une nouvelle version EEex n'est jamais adoptee automatiquement : elle requiert
une nouvelle entree de compatibilite et la matrice de tests BG2HD.

## Propriete et desinstallation

EEex et InfinityLoader restent la propriete de leur installeur officiel. BG2HD
les controle mais ne les copie pas et ne les met pas a jour. Le retrait WeiDU
normal de BG2HD laisse EEex actif et conserve le shim Steam : c'est le choix
sans surprise, y compris quand le bootstrap avait guide son installation.

`Uninstall-BG2HD.exe` fournit en plus un retour **vanilla complet** distinct,
jamais silencieux. Apres retrait du Core et confirmations explicites, il appelle
`setup-EEex.exe` pour retirer les composants 1 puis 0, remet `Baldur.exe`
vanilla et retire le garde EEex. Avant une premiere installation BG2HD, le
bootstrap enregistre si EEex est `bg2hd-bootstrap` ou `pre-existing`; une origine
inconnue (notamment un ancien paquet) est traitee comme potentiellement externe
et affiche le meme avertissement. Pendant cette operation seulement,
`weidu.conf` peut etre bascule temporairement en `en_US` afin de contourner
l'absence de traduction WeiDU EEex francaise, puis il est restaure octet pour
octet. Les sources EEex et `setup-EEex.exe` restent sur disque selon le
comportement WeiDU normal ; aucun fichier inconnu d'un autre mod n'est supprime.
Ce jeu de residus connu est classe `inactive` au prochain lancement de BG2HD :
l'installeur officiel EEex est repropose, sans demander une reparation manuelle.
Toute combinaison contenant encore un composant ou un fichier runtime incomplet
reste classee `partial` et bloquee.

Une reinstallation apres `eeex-retained` ou `vanilla-restored` ouvre une nouvelle
transaction Core. Les journaux renderer peuvent rester comme traces du cycle
precedent, mais `InfinityEngine-Enhancer.ini` et les fichiers runtime sont
toujours revalides sur disque. Un INI supprime par le retour vanilla est recree
depuis le modele manifeste avant l'installation des composants UI. Une
restauration repetee contre un INI deja absent est un no-op sur, afin que WeiDU
ne masque pas l'erreur d'origine pendant un rollback.

Le renderer est a l'inverse une charge BG2HD de l'alpha locale. Chaque fichier
runtime existant est sauvegarde et trace par empreinte avant publication. A la
desinstallation, BG2HD restaure uniquement les fichiers qu'il peut identifier
comme siens. Un fichier modifie apres installation est preserve pour revue
manuelle.

## Securite et distribution

L'archive EEex est telechargee uniquement depuis la release officielle et
verifiee contre l'empreinte figee. Aucun repli vers une version "latest" ou une
archive sans hash ne sera autorise. Le mode hors ligne applique exactement le
meme controle.

EEex/InfinityLoader ne sont pas redistribues dans BG2HD tant qu'une autorisation
explicite de leur auteur n'a pas ete obtenue. La release BG2HD garde donc son
archive independante ; le futur bootstrap aura seulement un flux guide avec
consentement utilisateur.
