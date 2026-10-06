# Icewind — installation Q3m V7 x2

- Autorisation utilisateur : installation ingame 2026-10-06 ; aucune acceptation QA/release implicite.
- Installation terminée le 2026-10-07 (Europe/Paris), QA ingame en attente ; reçu `ingame-installation/active-test.json`.
- Production immuable : `../q3m-icewind-full-x2-20261006-v1/current-generation.json` ; 36 modèles/40 IDs, 1 115 feuilles/75 176 frames physiques, 1 140 bindings/76 955 occurrences.
- Catalogue combiné : 257 IDs/13 372 feuilles/2 318 470 frames/62 028 routes ; 217 IDs/12 257 feuilles/60 888 routes antérieurs conservés exactement. Monster complet non ajouté.
- Runtime : successeur de la DLL installée MultiNew v2 ; attente des métadonnées +cycles natifs pour owner2/Icewind. INI/Nearest, shaders, exécutable natif et assets acquis conservés.
- Contrôles : `catalog-proof.json`, `verification.json` (décodeur K6×trois formats +playback corps/armes sous le catalogue combiné), `installation-verification.json`, `installed-native-verification.json`.
- État actif : `ingame-installation/active-test.json`. Sauvegarde catalogue/DLL : `work/before/`. Restauration : `restore.ps1`, jeu/InfinityLoader fermés ; ne retirer que les objets/fixtures créés par ce reçu.
- [40 commandes CLUA](CLUA.txt) : `QICE` +ID hexadécimal, ex. `C:CreateCreature("QICEE070")`. CRE neutres issus d'ARNMAN01, sans scripts/effets/items ; les cinq modèles équipables peuvent aussi être testés via les CRE stock pour les armes.
- Préviews : `../q3m-icewind-full-x2-20261006-v1/previews-v2/`. Aucune validation ingame déduite des tests hôte ni de l'installation.
- Commandes : Python `config://chainner_python`, `prepare.py`, `verify.py`, PowerShell `install.ps1 -DryRun`, `install.ps1`, Python `finish.py`. Aucune inférence/aucun encodage recalculé.
- Suite 2026-10-07 : [famille entière validée ingame par l'utilisateur](../q3m-icewind-accepted-x2-20261007-v1/README.md). Les états « en attente » ci-dessus décrivent la remise initiale ; reçu et preuves d'installation immuables.
