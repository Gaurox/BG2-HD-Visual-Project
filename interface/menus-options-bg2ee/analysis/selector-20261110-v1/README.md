# Sélecteur BG2EE — diagnostic 2026-11-10

Demande : retrouver les assets de la capture utilisateur et expliquer la disparition du x4.
Écran = `UI.menu`, menu `START` ; ne pas confondre `START_MAIN` ni le HUD monde.
Audit du jeu courant **en lecture seule**. Aucun changement INI/DLL/asset installé/release ; aucune nouvelle QA ingame.

## Conclusions

| Constat | Niveau de preuve |
|---|---|
| `EnableMainMenuX4Test` absent de l'INI courant → défaut `false` ; `EnableBigLogoX4Test=false` ; `EnableMenuX2Test` absent → `false` | Fichier installé + `core/config.h:170–176` ; suffit à désactiver tout ce sélecteur |
| 7/7 atlas de l'overlay installés, tailles correctes, SHA256 identiques à la production | `evidence/audit.json`, `pages.csv` |
| 5 empreintes moteur erronées : hash PVRZ au lieu du contenu DXT5 présenté à OpenGL | Recalcul exact ; constantes erronées également présentes dans la DLL installée, constantes DXT5 correctes absentes |
| Les 3 boutons inférieurs ne sont pas couverts par ce pack x4 | UI native → `GUIOSTUL/UM/UR` → `MOS0152/0153` ; pages absentes du registre et du pack courant |
| Ancienne intermittence compatible avec un hook GL installé après le premier upload ; attribution historique non démontrée | Analyse code/ordre de démarrage ; aucune trace ancienne positive/négative permettant de conclure |

Les sources décodées des 7 pages de l'overlay sont identiques pixel par pixel aux PNG historiques.
Une évolution des images natives n'explique donc pas les 5 empreintes erronées.
L'ancienne mention « validé » décrit une QA historique ; elle ne démontre ni l'exhaustivité de cette
QA ni l'activation actuelle. Aucun artefact historique n'a été réécrit.

## Cartographie des pixels de la capture

Toutes les ressources BAM/MOS suivantes proviennent de `data/bgee.bif` ; pas d'override concurrent
pour ces compositions ou leurs pages dans l'installation inspectée.

| Pixels / contrôles | Ressource | Dimensions natives / états | Pages | Production retrouvée |
|---|---|---|---|---|
| Cadre intégral, fond, couvertures/charnières/gemmes, titre BG2 + Enhanced Edition, titres des 3 campagnes, logo rouge D&D | `START3EE.MOS` | 1024×768, 8 blocs | 258, 259 | `selection-des-trois-jeux/upscale-topaz-recovery-v2-d50/START3EE-background-x4.png`, 4096×3072 |
| Emblème personnage SoA | `LOGOSOA.BAM` | 207×260, 2 frames, 1 cycle | 181 | Exports x4 dans le dossier parent de la variante, `LOGOSOA-frame-00/01-x4.png` |
| Emblème crâne ToB | `LOGOTOB.BAM` | 261×252, 2 frames, 1 cycle | 182, 183 | Overlay, `LOGOTOB-frame-00/01-x4.png` |
| Emblème armes Black Pits II | `LOGOTBP.BAM` | 249×229, 2 frames, 1 cycle | 181, 182 | Overlay, `LOGOTBP-frame-00/01-x4.png` |
| Habillage bouton Crédits | `GUIOSTUL.BAM` | 232–233×44, 4 frames | 152 | Aucun remplacement dans ce pack |
| Habillage bouton Quitter | `GUIOSTUM.BAM` | 201×42 ou 203×44, 4 frames | 152 | Aucun remplacement dans ce pack |
| Habillage bouton Options | `GUIOSTUR.BAM` | 232–234×44, 4 frames | 153 | Aucun remplacement dans ce pack |
| CRÉDITS / QUITTER LA PARTIE / OPTIONS | `L_fr_FR.lua`, style `button` de `BGEE.lua` | `STONESML`, 10 pt, texte dynamique | Polices | Hors atlas x4 ; `STONESML.ttf` + `.fnt` sous `interface/fonts/source/` ; BAM historique dans `data/GUIFont.bif` |
| v2.7.3.0 | `versionString` moteur, style `label`, override `text point 10` | `STONESML`, 10 pt | Polices | Hors atlas x4 |

`UI.menu` courant : `data/Patch2.bif`, type 1032 ; `START` lignes 7146–7306.
`BGEE.lua` : `data/Patch2.bif`, type 1033 ; styles button/label lignes 2884/2895.
`L_fr_FR.lua` : clés lignes 204/565/591 ; encodage CP1252.
`STONESML.ttf` : `data/Patch2.bif` ; `.fnt` : `data/fonts.bif`. Aucun override de ces fichiers.
Menu d'arrière-plan `BACKGROUND` : référence `GUIBG` absente du KEY et de l'override inspectés ;
pas de pixels attribuables à cette référence derrière le fond plein `START3EE` de la capture.

## Production retrouvée

Racine : `interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50/`.
Overlay : `selection-des-trois-jeux/`, 17 exports Topaz Recovery v2 Detail 50 x4 conservés.
7 atlas DXT5 dans `assets/` : `MAINMENU-MOS0181/0258-x4.dxt5`,
`SELECTOR-MOS0182/0183/0184/0185/0259-x4.dxt5`.
Les deux atlas MAINMENU sont les **versions fusionnées de l'overlay**, pas les versions parent seules ;
les versions installées correspondent bien aux versions fusionnées.

Sur les 17 nouveaux exports : 1 fond + 4 frames ToB/TBP + 12 frames `MAINEEAN`.
`MAINEEAN` n'est pas référencé dans `UI.menu` courant : ces libellés anglais historiques
Play/Tutorial/Black Pits ne sont pas les textes français des boutons visibles.
`MOS0184/0185` ne sont donc pas nécessaires aux pixels de cet écran courant.
`STARTMBT.BAM` appartient à `START_MAIN` et d'autres menus : ce n'est pas le trio de boutons de `START`.

## Erreur exacte de registre

`src/iee/biglogo_ui_upscale.cpp:40–57` ; `try_replacement()` lignes 151–168.
Le hook `shader_probe.cpp:2246–2268` transmet `data,imageSize` de `glCompressedTexImage2D` :
contenu DXT5 sans en-tête PVR ni compression zlib, pas le fichier PVRZ.

| Page | Constante actuelle = FNV64(PVRZ) | FNV64(DXT5) attendu |
|---|---|---|
| MOS0182 | `4A6C0F19556FF84A` | `BC13C466CDC91E6C` |
| MOS0183 | `3FEAAA2B11115E8C` | `4917CA8A551C8566` |
| MOS0184 | `AFFAC5742D9338B4` | `F28D45053A121C32` |
| MOS0185 | `5D8AB0391325C7C2` | `69EC1ACC79F26FA6` |
| MOS0259 | `CADBE0DA29AC3001` | `B3CABD9947A268DE` |

`MOS0181` et `MOS0258` ont les bonnes empreintes DXT5. Avec la seule option réactivée,
ces deux pages seraient éligibles, les cinq autres resteraient refusées : fond potentiellement
partiel, SoA couvert, ToB refusé, Black Pits partiel. La présence des 7 fichiers ne suffit pas.

## Ancienne intermittence : hypothèse distincte

- `InitBindings` historique (`98b405477`, 2026-08-27) lançait `InitThread` sans attendre sa fin.
- Remplacement uniquement lors de l'upload GL ; aucun rattrapage des textures déjà chargées.
- Hooks GL installés paresseusement depuis le thread de rendu (`hooks.cpp:2496`,
  `frame_hook.cpp:77`) ; première tentative à la présentation d'une frame ou d'un draw couvert.
  Des pages de menu chargées avant cette tentative restent natives dans le cache.
- Barrière de démarrage ajoutée dans `2e7c84e12` (2026-10-15), présente dans la source actuelle ;
  elle attend les assets CPU/hooks généraux, sans garantir un hook GL avant chaque premier upload UI.
- Session observée du 2026-11-10 : DLL chargée 22:04:23.047 ; barrière libérée 22:04:33.624 ;
  `Installed GL shader probes` 22:04:35.352. Fuseau du log non qualifié ; heures reproduites telles quelles.
- Pas de trace des uploads `START3EE` dans cette session : **ne pas conclure que la course a été observée**.

Chronologie de configuration vérifiable, `config://bg2ee_game_root` :
`InfinityEngine-Enhancer.backup-20260823-before-animation-clock-probe.ini` → x4 menu actif ;
`.ini.bak-avant-sonde-20260903-220136` et `.ini.bak-20260904-probe-off` → menu x4 explicitement désactivé ;
INI courant → clé absente (défaut désactivé). Auteur/motif exact de la désactivation non établis.
Les 4 journaux rotatifs encore présents ne contiennent pas de ligne `Prepared reversible MOS` / `Replacing MOS`.

## Suite technique déduite, non exécutée

1. Corriger les cinq constantes contre les octets DXT5 ; préserver le filtrage strict format/taille/hash.
2. Réactiver seulement `EnableMainMenuX4Test=true` dans l'INI courant, `EnableMenuX2Test=false` ;
   ne pas recopier l'ancien INI complet ni installer l'ancienne DLL des scripts historiques.
3. Qualifier l'ordre premier upload UI / installation du hook GL ; rendre cet ordre déterministe si nécessaire.
4. Traiter séparément les 12 frames `GUIOSTUL/UM/UR` pour compléter les 3 boutons ; polices = voie distincte.
5. QA locale répétée démarrage/retour aux menus, états normal/survol ; aucun statut QA/release anticipé.

## Fichiers de résultat

- `evidence/audit.json` : SHA256 locaux INI/DLL/7 atlas, empreintes sources et constantes binaires.
- `evidence/resources.csv`, `pages.csv` : inventaires techniques.
- `evidence/UI-START.txt` : déclaration native du menu avec numéros de ligne.
- `evidence/assets-overview.png` : compositions natives remontées des BIF, vue inspectée.
- Reproduction vers un **nouveau** dossier :
  `python -B interface/menus-options-bg2ee/analysis/selector-20261110-v1/analyze.py --output <nouveau-dossier>`.
