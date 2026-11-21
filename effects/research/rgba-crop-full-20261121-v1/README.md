# Rognage RGBA intégral

`IEECROP2` stocke les rectangles utiles en RGBA brut, liés par SHA-256 au registre et à l’index de partage éventuel. Le lecteur restitue le canevas x4 d’origine. Un pixel hors rectangle vaut `00 00 00 00`. Les couleurs sous alpha nul, les dimensions, le placement, les cycles et les alias sont conservés.

| Source | Ressources | Frames physiques / logiques | Gain net, index inclus |
|---|---:|---:|---:|
| Jeu local | 743 | 72 563 / 72 563 | 8 882 369 504 octets (23,61 %) |
| Alpha.10 | 733 | 65 849 / 71 971 | 8 337 298 300 octets (23,98 %) |

`results-*.json` contient les empreintes des fichiers. `build.py build live|release` produit les packs locaux ignorés par Git et vérifie chaque frame physique après relecture du blob. `build.py verify live --live-directory <pack-RGBA-original>` peut reprendre cette vérification après installation. Le lecteur de test charge les deux packs avec `--metadata-mib 32 --streaming` et contrôle 2 304 contrats de phase avec le TSV du lot COW sur le jeu local.

## Parcours en jeu

1. Relancer via `InfinityLoader.exe`. Dans `InfinityEngine-Enhancer.log`, chercher `Effect crop storage: physicalFrames=72563`, puis `Prepared effect animation x4 runtime pack: resources=743`. Après le test, contrôler les lignes `Effect streaming CPU` et `failures=0` si les statistiques périodiques sont activées.
2. Ouvrir une sauvegarde de test dans une zone dégagée avec deux personnages espacés. Ouvrir la console avec Ctrl+Espace et jouer les commandes une par une.

   ```lua
   C:Eval('CreateVisualEffectObject("ZCOWV",Player1)',0)
   C:Eval('CreateVisualEffectObject("Z31T12",Player1)',0)
   C:Eval('CreateVisualEffectObject("ZR1810",Player1)',0)
   C:Eval('ForceSpellRES("SPWI304",Player2)',0)
   C:Eval('ForceSpellRES("SPWI502",Player2)',0)
   C:Eval('ForceSpellRES("SPWI299",Player2)',0)
   ```

3. Observer le sprite COW fixe, le souffle `SPRDRABU` et `BDFORCEW` sur le personnage, puis l’impact de Boule de feu, la persistance du Nuage mortel et le trajet du projectile COW. Vérifier l’ancrage, les contours, les masques devant un décor et l’absence de frame qui saute. Rejouer après pause/reprise et changement de zone. Quitter sans sauvegarder les déclenchements offensifs.
4. Ouvrir le journal et l’inventaire depuis le HUD, puis lancer un dialogue et sélectionner une réponse pour contrôler le HUD avec le nouveau lecteur.

## Retour au pack précédent

Fermer BG2EE et InfinityLoader. Exécuter `Install-CroppedEffects.ps1 -Action Restore` sous PowerShell 7. Le pack original et le DLL précédent sont conservés dans le dossier du jeu. Le reçu d’installation local est `packs/installed.json`.
