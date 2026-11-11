# Quatre menus SeedVR2 7B x4 — test installé

- Choix hors jeu : `../../experiments/menus-seedvr-x4-7b-3b-20261110-v1/selection-20261111.json`.
- Menus : inventaire `INVENTOR`, journal `QUESTBAK`, personnage `GUIREC2`, options `STONEOPT`.
- État : installé, QA ingame utilisateur en attente. Aucun changement release.
- Reçu : `installed-20261111-v1.json` ; sauvegarde exacte : `backups/20261110T231055Z/receipt.json`.
- DLL compilée MSVC v142 Release x64 : `build/iee-four-menus-seedvr7b-20261111-v1/Release/InfinityEngine-Enhancer.dll`.

## Périmètre technique

- `[Shaders] EnableGameplayMenusX4=true`, flag dédié ; sélecteur et autres flags préservés.
- 8 pages : `MOS0155/0156/0180/0181/0253/0254/0263/0264`.
- Page181 : atlas installé du sélecteur utilisé comme base ; seuls les rectangles `INVENTOR` changent.
- Autres pages : DXT5 natif agrandi sans perte (endpoints/indices conservés), puis remplacement des blocs des quatre fonds seulement.
- Aucun BAM/MOS/PVRZ natif remplacé ; géométrie x1 et boutons/contrôles superposés préservés.
- Pixels x4 7B exacts recadrés par blocs MOS, pas de nouvelle inférence ni d’upscale d’atlas.
- `assets.json` : empreintes FNV1a des payloads natifs, SHA256 des atlas, rectangles, contrôle blocs non sélectionnés.
- Chargement : interception compressée armée avant PVR Demand, également pour le nouveau flag.

## Vérifications effectuées

- 8 pages : blocs hors rectangles byte-identiques à la base ; fallbacks natifs décodés identiques au nearest x4.
- `iee_menu_upscale_tests` : 8 pages menus / 7 sélecteur, isolation des flags, hash/format/dimensions invalides refusés, défaut désactivé.
- `iee_tests` via CTest : réussi.
- Jeu/InfinityLoader fermés ; DLL, INI et 8 atlas installés avec sauvegarde/rollback.
- 10 fichiers installés vérifiés par octets. Pas de validation ingame déduite.

## Test utilisateur

Lancer par le raccourci InfinityLoader habituel, charger une partie puis ouvrir inventaire,
journal, fiche personnage et options. Vérifier netteté, contours transparents, cases/boutons,
retours successifs aux menus et sélecteur. Aucun lancement automatique demandé.

## Retour exact — jeu et InfinityLoader fermés

Depuis la racine du projet :

```powershell
python -B interface/integration/four-menus-seedvr7b-20261111-v1/install.py --restore interface/integration/four-menus-seedvr7b-20261111-v1/backups/20261110T231055Z/receipt.json
```

Refus si DLL/INI/atlas ont changé depuis le reçu. Restaure les fichiers antérieurs et retire
uniquement les nouveaux atlas absents avant installation.

`build_assets.py` reconstruit à partir des PNG 7B retenus ; ne pas le relancer contre la page181
déjà modifiée sans restaurer d’abord la base : utiliser les assets SHA256 du manifeste existant.
