# Médaillons — périmètre conservé, recette retrouvée

Décision utilisateur 2026-11-10 : conserver les 3 dessins (SoA, ToB, Black Pits II).
« Traite » = conserver dans le périmètre ; réutiliser les exports validés existants.
Ne pas relancer une génération simplement pour appliquer la réduction du périmètre UI.

## Recette validée

- Autorité : `interface/menus-options-bg2ee/docs/MENU_UPSCALE.md`.
- Topaz Gigapixel **8.4.1**, modèle **Recovery v2**, **Detail 50**, **x4**, couleurs préservées.
- PNG RGBA par élément complet (chaque frame BAM / composition MOS), puis recomposition DXT5.
- Géométrie BAM/MOS logique x1 inchangée ; dimensions physiques des pages ×4.
- Commande historique : `-m recovery --mv 2 --detail 50 --scale 4 -f png --cs preserve --pc 4 --suffix '-x4' --se --verbose`.
- Scripts : `.../x4-topaz-recovery-v2-d50/Run-Topaz-RecoveryV2-D50-X4.ps1` et
  `.../selection-des-trois-jeux/Run-Topaz-RecoveryV2-D50-X4.ps1`.
- PNG inspectés : métadonnées `Software=Topaz Gigapixel AI 8.4.1 (Windows)`,
  `topaz:ColorSpace=preserve`, dimensions x4 exactes.
- SeedVR 3B/7B, AdaIN et x2 sous `archive/` = essais antérieurs ; pas la recette de production retenue.

## Deux ressources pour des dessins ressemblants

| Usage | Ressource et dimensions natives | Couverture de production courante |
|---|---|---|
| Sélecteur : SoA | `LOGOSOA`, 207×260, 2 états | 2 PNG Topaz x4 dans la variante parent ; conservés |
| Sélecteur : ToB | `LOGOTOB`, 261×252, 2 états | 2 PNG Topaz x4 dans l'overlay ; conservés |
| Sélecteur : Black Pits II | `LOGOTBP`, 249×229, 2 états | 2 PNG Topaz x4 dans l'overlay ; conservés |
| Grand médaillon menus : SoA | `BIGLOGO`, frame 0, 346×449 | `BIGLOGO-options-frame-0-x4.png`, 1384×1796, existe |
| Grand médaillon menus : ToB | `BIGLOGO`, frame 1, 327×315 | Aucun export individuel trouvé dans la variante courante |
| Grand médaillon menus : Black Pits II | `BIGLOGO`, frame 2, 337×354 | Aucun export individuel trouvé dans la variante courante |

Sélecteur : `EnableSelectorX4=true`, runtime et rendu acceptés le 2026-11-10 ;
`interface/menus-options-bg2ee/integration/selector-startup-20261110-v1/accepted-20261110-v1.json`.
Ces 3 emblèmes sont donc déjà upscalés en jeu. Leurs PNG et atlas sont à réutiliser tels quels.

`BIGLOGO` : builder courant explicitement limité à frame 0 / `MOS0017` ; fond d'atlas
rééchantillonné Lanczos, seule la zone frame 0 reçoit le PNG Topaz. `BIGLOGO` frame 2 utilise
également `MOS0018`, absent du registre de remplacement courant. `EnableBigLogoX4Test=false`
dans l'INI inspecté. Ne pas déduire de l'état du sélecteur que les 3 grandes variantes sont activées.

La réduction du périmètre UI ne modifie aucune de ces installations pendant cette analyse.
