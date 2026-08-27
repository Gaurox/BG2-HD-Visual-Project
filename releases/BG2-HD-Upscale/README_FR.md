# Baldur's Gate II: Enhanced Edition HD Upscale — guide utilisateur

## Statut

`0.1.0-alpha.2` est une alpha Windows testee localement, pas encore une
publication publique. Ne partagez pas l'archive tant que la gate de licences
et de provenance n'est pas levee.

## Prerequis

- BG2EE obtenu sur Steam, version 2.7.3.0, Windows 64 bits ;
- EEex/InfinityLoader deja compatibles, ou une connexion Internet / l'archive
  officielle EEex 1.2.0 pour le flux guide ;
- jeu et launcher fermes pendant l'installation ;
- espace libre pour environ 1,1 Go de payload et les sauvegardes WeiDU.

Linux, Steam Deck, Proton, macOS, les autres boutiques et une version Steam
inconnue ne sont pas pris en charge. Le paquet ne redistribue ni le jeu, ni
EEex, ni InfinityLoader. Le renderer BG2HD est inclus dans cette alpha locale,
mais son test de cycle complet sur installation propre reste requis avant toute
diffusion publique.

La politique retenue pour une future alpha publique est gratuite et non
commerciale : elle exige une copie legitime du jeu, l'archive intacte avec ses
credits et exclut les executables du jeu, EEex et InfinityLoader. Les details
sont dans [Politique de diffusion](docs/DISTRIBUTION_POLICY.md).

## Installer l'archive

1. Verifier le SHA-256 annonce avec `Get-FileHash <archive> -Algorithm SHA256`.
2. Extraire **le contenu** de l'archive a la racine du jeu, la ou se trouvent
   `Baldur.exe`, `chitin.key` et `WeiDU.log`. Ne pas extraire dans `override`.
3. Fermer Steam et le jeu, puis lancer `Install-BG2HD.exe` depuis ce dossier.
4. S'il manque, autoriser le telechargement de l'archive EEex officielle ou
   fournir son chemin local. L'installeur EEex s'ouvre alors : indiquez la
   racine du jeu et installez ses deux composants requis.
5. Apres reverification, BG2HD ouvre automatiquement WeiDU : choisir la langue,
   puis le Core et les composants souhaites.

Le Core est obligatoire. Le paquet inclut le menu x4, le selecteur de jeu et
**toutes les cartes marquees `validated-installed` dans `areas.csv`** : 143
variantes (135 composants de cartes, les couples jour/nuit restant atomiques).
Chaque carte est proposee comme composant WeiDU distinct ; les cartes en
attente, les builds x2 et les sources de developpement restent exclus.
L'installation du menu x4 active automatiquement le renderer pour le menu et
le selecteur ; le selecteur x4 ajoute ensuite ses atlas specifiques.

WeiDU sauvegarde les fichiers qu'il remplace. Le Core sauvegarde l'etat du
lanceur et du renderer, fusionne seulement ses propres reglages et cree un raccourci
`Baldur's Gate II Enhanced Edition - HD` sur le bureau.

### Compatibilite des futures sauvegardes

Le Core installe un `M_IEEE.lua` verifie qui active
`EEex_Debug_DisableExtraCreatureMarshalling = true` avant l'initialisation du
renderer. EEex n'ajoute donc pas les enregistrements prives `X-BIV1.0` que le
moteur vanilla 2.7.3.0 ne sait pas relire. Le paquet bloque l'installation si
ce garde-fou est absent ou modifie.

Cette garantie vise les nouvelles chaines de sauvegarde commencees depuis un
etat compatible vanilla apres installation de ce correctif. Elle ne repare pas
les anciennes sauvegardes qui contiennent deja `X-BIV1.0`.

## Lancer, mettre a jour et retirer

Apres installation, le bouton **Jouer** de Steam reste le chemin normal :
Steam lance `Baldur.exe`, qui est le shim vers InfinityLoader, puis vers
`BaldurReal.exe`, l'executable Steam original preserve. Le raccourci HD lance
le meme chemin.

Pour une mise a jour, fermez le jeu, extrayez la nouvelle archive a la racine
du jeu et relancez `Install-BG2HD.exe`. WeiDU reconnait les composants et propose
leur reinstallation/mise a jour.

Pour retirer le patch, desinstallez d'abord les composants optionnels dans
l'ordre inverse, puis lancez `Uninstall-BG2HD.exe` et terminez par le Core. Le
programme propose deux choix explicites :

- **Retirer BG2HD et conserver EEex** (choix normal) : les fichiers BG2HD, le
  renderer et le raccourci HD sont retires. `Baldur.exe` reste le shim EEex et
  Steam continue donc de lancer le jeu correctement ;
- **Retour vanilla complet** : apres deux confirmations, retire aussi les deux
  composants EEex par leur installeur officiel puis remet l'executable Steam
  original en place. Si EEex etait deja present, ou si son origine est inconnue,
  le programme l'indique avant la confirmation car d'autres mods peuvent en
  dependre.

`setup-bg2hd.exe` conserve toujours EEex lorsqu'il retire le Core directement.
Le retour vanilla complet est volontairement reserve a `Uninstall-BG2HD.exe`.
L'outil EEex laisse ses sources et son installeur dans le dossier du jeu, comme
un desinstalleur WeiDU classique, mais ses composants actifs et son garde de
lancement sont retires. Au prochain lancement, BG2HD reconnait cet etat comme
EEex desinstalle et repropose automatiquement son installeur officiel. Vos
sauvegardes ne sont pas touchees. Chaque reinstallation ouvre une nouvelle
transaction BG2HD et recree la configuration du renderer si le retour vanilla
l'avait supprimee ; les anciens journaux ne sont jamais pris pour des fichiers
encore actifs.

Ne copiez jamais manuellement un `Baldur.exe`. Si Steam Verify restaure le
fichier vanilla, utilisez `Repair` via l'installeur WeiDU (voir
[Integration Steam](docs/STEAM_INTEGRATION.md)).

## Obtenir de l'aide

Consultez d'abord [Recuperation](docs/RECOVERY.md) et
[Problemes connus](KNOWN_ISSUES.md). Pour un rapport de bug, joindre `WeiDU.log`
et les extraits pertinents de `InfinityEngine-Enhancer.log`, apres avoir retire
nom Windows, nom de compte, chemins personnels et toute sauvegarde.

Le protocole de validation HD -> vanilla est decrit dans
[Test des futures sauvegardes](docs/TEST_SAVE_COMPATIBILITY_FR.md).
