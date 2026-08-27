# Localisation WeiDU

Le patch propose neuf choix d'installation, alignes sur les neuf langues actuellement indiquees pour BG2EE Steam : anglais, francais, allemand, espagnol (Espagne), italien, polonais, russe, coreen et chinois simplifie.

Lorsqu'un composant est ajoute, suivre d'abord le [contrat installeur et
integration des upscales](INSTALLER_AND_UPSCALE_WORKFLOW.md), puis appliquer
ici sa partie TRA.

Chaque dossier `bg2hd/tra/<langue>/setup.tra` contient les memes identifiants `@1` a `@15`. Le TP2 charge toujours `english/setup.tra` en premier, puis le TRA choisi : une cle manquante dans une traduction retombe donc sur l'anglais plutot que de faire echouer l'installation. Les fichiers sont en UTF-8 sans BOM. Comme le premier paquet ne vise que BG2EE, `HANDLE_CHARSETS` n'est pas employe : cette fonction sert principalement a convertir les TRA pour les anciennes editions avec leurs encodages historiques.

Les traductions francaise et anglaise sont la base de travail. Les sept autres sont des traductions initiales et portent le statut `needs-native-review` dans `manifests/languages.json`. Elles doivent etre relues par une personne maitrisant la langue avant toute release publique. Toute nouvelle chaine doit etre ajoutee avec le meme numero dans les neuf fichiers lors de la meme modification.

Le choix de la langue du mod est independant de la langue deja selectionnee dans Steam : WeiDU affiche son propre choix avant l'installation. Il ne faut donc jamais supposer un dossier de langue a partir des reglages locaux du jeu.

References : la syntaxe `LANGUAGE` et le mecanisme de TRA de repli sont documentes par [WeiDU](https://weidu.org/~thebigg/README-WeiDU.html) et le cours communautaire [A Course in WeiDU](https://gibberlings3.github.io/Documentation/readmes/weiducourse/weiducourse_1.html). Les langues Steam sont verifiees sur [la fiche officielle BG2EE](https://store.steampowered.com/app/257350/Baldurs_Gate_II_Enhanced_Edition/).
