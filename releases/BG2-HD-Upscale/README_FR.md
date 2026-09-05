# BG2 HD Upscale — guide utilisateur

## Statut et prérequis

La version et le statut exacts sont dans [`manifests/release.json`](manifests/release.json). La
version actuelle est une alpha locale non publiable.

- BG2EE Steam 2.7.3.0, Windows x64 ;
- jeu, Steam et InfinityLoader fermés pendant installation/restauration ;
- EEex/InfinityLoader compatibles, installés séparément ou via le bootstrap officiel guidé ;
- espace suffisant pour le payload et les sauvegardes WeiDU.

Linux, Steam Deck, Proton, macOS, les autres boutiques et les builds inconnus ne sont pas pris en
charge. Le paquet ne redistribue ni le jeu, ni EEex, ni InfinityLoader.

## Installer

1. Vérifier le SHA-256 publié de l'archive.
2. Extraire son contenu à la racine contenant `Baldur.exe`, `chitin.key` et `WeiDU.log`, jamais
   dans `override`.
3. Lancer `Install-BG2HD.exe` et suivre le bootstrap EEex si proposé.
4. Dans WeiDU, choisir la langue, le Core obligatoire et les composants voulus.

Le contenu exact vient de `manifests/content.json` et `components.json` : cartes x4 validées,
composants UI approuvés, overlays explicitement sélectionnés et packs animation approuvés. Les
cartes `installed-pending-qa`, builds de développement, backups et captures sont exclus.

Le Core installe le shim vérifié `Baldur.exe → InfinityLoader → BaldurReal.exe`, le renderer et le
garde save-neutral `M_IEEE.lua`. Ce garde empêche les nouvelles chaînes compatibles vanilla de
recevoir les blocs EEex `X-BIV1.0`; il ne répare pas les anciennes sauvegardes qui en contiennent.

## Lancer, mettre à jour, retirer

- Lancer normalement avec le bouton Steam **Jouer** ou le raccourci HD.
- Pour mettre à jour : fermer le jeu, remplacer les fichiers source de l'archive, relancer
  `Install-BG2HD.exe` et laisser WeiDU réinstaller les composants.
- Pour retirer : désinstaller les composants optionnels en ordre inverse, puis le Core via
  `Uninstall-BG2HD.exe`.

Le désinstalleur propose soit de retirer BG2HD en conservant EEex, soit un retour vanilla complet
avec double confirmation. La désinstallation directe du Core via `setup-bg2hd.exe` conserve
toujours EEex. Ne jamais copier ou renommer manuellement les exécutables ; après Steam Verify,
utiliser le flux Repair documenté dans [`docs/STEAM_INTEGRATION.md`](docs/STEAM_INTEGRATION.md).

## Aide

Lire [`docs/RECOVERY.md`](docs/RECOVERY.md) et [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md). Un rapport de
bug contient `WeiDU.log` et les extraits utiles du log renderer, après suppression des chemins et
données personnels. Le protocole de sauvegarde est dans
[`docs/TEST_SAVE_COMPATIBILITY_FR.md`](docs/TEST_SAVE_COMPATIBILITY_FR.md).
