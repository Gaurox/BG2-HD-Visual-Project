# BG2EE — contrôle des 133 ressources UI

1. Démarrer avec `InfinityLoader.exe`, charger une sauvegarde et mettre le jeu en pause.
2. Ouvrir la console avec **Ctrl+Espace**, saisir `BG2UIReview()`, puis **Entrée**. **Fermer** revient à la partie. Les flèches avancent d'une frame et les boutons extérieurs sautent de dix.
3. Vérifier les 153 entrées dans la galerie. Noter le numéro visible et le resref pour chaque défaut. `BG2UIReview(n)` permet de reprendre à un numéro précis.
4. Fermer la galerie et faire les vérifications dans les écrans d'origine ci-dessous. Regarder les raccords, les bords transparents, la géométrie des panneaux et les états de survol.

| Galerie | Entrer | Contenu |
|---|---|---|
| 1–24 | `BG2UIReview(1)` | Chapitres, rêves, départs, retours |
| 25–58 | `BG2UIReview(25)` | HUD, colonnes et cadres |
| 59–87 | `BG2UIReview(59)` | Médaillons, illustrations, chargement, chambres |
| 88–91 | `BG2UIReview(88)` | Carte, cadre et carte des touches |
| 92–153 | `BG2UIReview(92)` | Panneaux de menus, confirmations et variantes |

| Parcours depuis la sauvegarde | Point de contrôle |
|---|---|
| HUD → parler à un PNJ → afficher l'historique | Barre `GUWBTP10` (#54), séparateur `DLGDIVI` (#101) quand les messages sont affichés |
| Carte locale → Carte du monde | `WORLDMAP` (#91) en SoA ou `TOBMAP72` (#90) dans le contexte ToB correspondant |
| Marchand ou aubergiste → services → chambres | Bandeau `GUISTBBB` (#140). Les huit frames `ROOM*` se vérifient en galerie (#80–87) |
| Échap → Options, puis menu de campagne au prochain démarrage | Médaillons `BIGLOGO` (#59–61). Vérifier centrage et survol selon la campagne |
| Multijoueur → écran présentant le niveau de difficulté, si accessible | `GUIDIFF` (#63–69) |

`NPCCHAP` (#147) a une route d'épilogue. L'accès standard à `RECENTEV` (#148) est commenté dans le journal natif. La galerie couvre ces cas, les variantes historiques et les frames non appelées par un cycle de `LOADCNTR`. Une observation en galerie établit le rendu de la ressource, la route native se confirme dans son écran.

Log `InfinityEngine-Enhancer.log` · `Replacing MOS70xx.PVRZ with x4 atlas`. Les correspondances des pages, des resrefs et des numéros de galerie sont dans `pack.json`.
