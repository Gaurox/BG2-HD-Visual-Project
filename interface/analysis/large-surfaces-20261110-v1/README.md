# Interface — périmètre réduit, 2026-11-10

**Lots 01–23 résolus ; aucun choix visuel en attente.**
Catalogue avant vérification : 196 ressources logiques ; états détaillés dans `inventory.json`/`resources.csv`.
Série directe `UI.menu` complétée par des fonds/variantes natifs et des illustrations indirectes.
La présence d'une variante dans les BIF ne prouve pas son usage courant : routage runtime à qualifier.
`GUIBG`/`GUINOTE` restent non résolus. Pas de revendication d'exhaustivité des graphismes du jeu.
Petits champs/contrôles/icônes hors périmètre ; miniatures de maps dans leur domaine.
Décision finale : tous les refus explicites révoqués ; lots 07 et 17 intégralement conservés.
Lot 21 : `GUIWLS20`/`GUIWRS20`, deux colonnes conservées (« oui »).
Historique complet, y compris révisions : `decisions.json`.
Il s'agit du choix des sources à traiter, pas d'une QA d'upscale.

Demande : annuler la production des boutons/petites icônes UI, conserver les grandes surfaces.
Analyse et choix visuels uniquement : aucune génération, suppression d'asset, modification du jeu
ou de la release. « Traite » = retenu dans le périmètre ; pas une nouvelle QA de production.

## Décisions utilisateur

| Élément | Décision | Ressources |
|---|---|---|
| Fonds/grands panneaux inventaire, personnage, options et autres menus | Conserver, revue visuelle effectuée | Inventaire `resources.csv`, décisions individuelles/lots |
| Grands titres graphiques | Conserver | `TITLE`, toutes variantes ; titres peints dans les fonds |
| 3 grands médaillons | Conserver | `BIGLOGO` frames 0/1/2 |
| 3 emblèmes du sélecteur déjà en x4 | Réutiliser tels quels | `LOGOSOA`, `LOGOTOB`, `LOGOTBP`, états existants |
| Illustration de don au temple | Conserver, contour en fondu impératif | `DONATE`, 2 frames ; alpha natif inspecté : 14 niveaux, 1 973 pixels intermédiaires sur le modèle montré |
| Chambres d'auberge | Conserver | `INNROOMS`, 4 catégories × 2 états |
| Feuille de papier du journal | Conserver | `QUESTBG`, variantes natives |
| Colonnes décoratives gauche/droite | Conserver | `GUIWLSP`, `GUIWRSP` ; variantes HUD déjà repérées `GUIWLS20`, `GUIWRS20` |
| Cadre conteneur / barre d'actions, planche A/B | Finalement conserver les deux (révision utilisateur) | `GMPWMSG0`, `GUWBTP10` |
| Bandeau boutique / sélection de groupe, planche C/D | Finalement conserver les deux (révision utilisateur) | `GUISTBBB`, `GUWPKPC0` |
| Boutons, petites icônes, contrôles, texte de police | Hors nouvelle production UI | Dont `STARTMBT`, `GUILS10/20`, `GUIBTACT`, contrôles GUIOST*, sliders, cases/coches, scrollbars |

Les grandes illustrations cliquables explicitement retenues ne sont pas assimilées aux petits boutons.
Les décisions ne révoquent ni ne suppriment les preuves/QA historiques d'autres domaines.

## Ce qui resterait

Inventaire natif statique `UI.menu` (quoted et bare resrefs, noms de menus séparés des noms de contrôles) :

- **55 compositions MOS** retenues : les 51 fonds/panneaux/colonnes initiaux
  et les 4 cadres finalement réintégrés. Revue de cette série terminée.
- **8 familles BAM** de grandes illustrations retenues : `BIGLOGO`, `TITLE`, `LOGOSOA`, `LOGOTOB`,
  `LOGOTBP`, `DONATE`, `INNROOMS`, `QUESTBG`. Plusieurs états/variantes par famille.
- 6 références MOS laissées hors série par le filtre initial :
  `DLGDIVI`, `PAPERSEP`, `PCHAPTER`, `GUWBTP20` (petites décorations/barre console),
  `GUISLDR` (contrôle), `GUWBTP30` (interface de debug).
  `DLGDIVI`, `PAPERSEP`, `PCHAPTER` présentés puis exclus au lot 17, finalement réintégrés par la dernière décision utilisateur.
- 2 références non résolues : `GUIBG`, `GUINOTE` ; ni KEY ni override dans l'installation inspectée.

Ces quantités comptent des **ressources logiques repérées**, pas des écrans, des travaux restant à
produire ou un inventaire global des graphiques du jeu. Des ressources servent à plusieurs menus.

| Famille d'écran | Principaux fonds/panneaux retenus |
|---|---|
| Inventaire / statistiques / détails d'objet | `INVENTOR`, `INVSTATS`, `GUIINVHI`, `GUIMGX` |
| Personnage / personnalisation / export | `GUIREC2`, `GUICUSTB`, `GUICHISD`, `GUIMPB`, `GUIHSB` |
| Options générales / gameplay / audio / graphismes / raccourcis | `STONEOPT`, `GUITUTB`, `GUICHISD` |
| Création de personnage | `GUICGB`, `GUIAPB`, `GUIGDB`, `GUIDCX`, `GUIHSBS`, `GUILUPB`, `GUISMDA`, `GUISMDB`, `GUISMF`, `GUISMS`, `GU3MPB` |
| Livres de sorts | `GUIMGB`, `GUIPRB`, `GUIMGCP` |
| Boutiques / temple / auberge | `GUISTBSC`, `GUISTDOB`, `GUISTIDB`, `GUISTROB` + illustrations retenues |
| Journal | `QUESTBAK`, `RECENTEV`, papier `QUESTBG` |
| Sauvegarde / chargement / import de groupe | `GUILOAD`, `GUICREDT`, `GUISAVEB`, `GUISRRQB`, `GMPCARBD` |
| Menus principaux / campagnes | `START`, `START3EE` + grands titres/médaillons ; pack existant `START2EE` à rapprocher de la route effective |
| Crédits / cinématiques / connexion / grands popups | `GUISMBM`, `GUIMOVB`, `GUICONNB`, `GUICONN1`, `GUIINVHB`, `GUIERR/6/7`, `GUIDLC` |
| Habillage carte du monde / épilogue | `GUIMAPWB`, `NPCCHAP` ; pas une autorisation de modifier cartes ou images dynamiques |
| HUD | Colonnes décoratives et cadres horizontaux réintégrés ; boutons/icônes exclus |

Exhaustif pour les références statiques recensées : `inventory.json` et `resources.csv`.
Images de chapitres choisies en Lua/moteur, cartes du monde, portraits et paperdolls = routes/domaines
distincts ; aucune annulation ni nouvelle production déduite de cette analyse.
Des slots/contours sont peints dans certains fonds : le statut candidat ne vaut pas autorisation
de retraiter les contrôles superposés ni d'inférer un modèle dédié par petite case.

## Existant : réutilisation et séparation

- Recette validée retrouvée : **Topaz Gigapixel 8.4.1 Recovery v2 / Detail 50 / x4 / couleurs préservées**.
  Élément complet traité séparément, puis atlas DXT5 ; géométrie logique native conservée.
  Référence : `../../menus-options-bg2ee/docs/MENU_UPSCALE.md` ; détails : `MEDALLIONS.md`.
- Sélecteur : 3 emblèmes déjà en x4 et runtime accepté le 2026-11-10. Ne pas les régénérer.
- `BIGLOGO` : grand SoA déjà produit en x4 ; aucune sortie individuelle ToB/Black Pits II trouvée
  dans la variante actuelle ; leur maintien dans le périmètre ne signifie pas que ce travail est fini.
- Menu principal : 26 états `STARTMBT` → pages `MOS0261/0262`, à retirer du futur pack réduit.
  `TITLE` → `MOS0265/0266`, à conserver ; `LOGOSOA` → `MOS0181`, à conserver.
- Sélecteur : les 12 libellés `MAINEEAN` anciens sont hors nouvelle production ; `MOS0184/0185`
  ne servent qu'à eux dans ce lot. `MOS0183` est partagé avec le survol ToB : conserver ce dernier.
- `GUILS10`/toolbar gauche x4 historique → hors nouveau périmètre, sans suppression de ses fichiers.
- Page mixte : recomposer une **nouvelle variante** avec seulement les éléments retenus en HD ;
  garder le contenu natif des éléments exclus. Ne pas écraser les atlas/QA déjà acceptés.
- Pour `DONATE`, porter l'alpha natif progressif séparément de l'inférence RGB et vérifier
  prémultiplication, matting et contours dans le jeu ; ne pas inventer une découpe opaque.

## Artefacts de l'analyse

- `decisions.json` : réponses utilisateur, contraintes, recette et portée.
- `inventory.json`, `resources.csv` : resrefs, dimensions, menus, lignes UI, dépendances PVRZ, statut.
- `surfaces-overview.png`, `previews/`, `choices-*.png` : vues natives locales, régénérables, sans QA de production.
- `analyze.py` : relire le KEY/BIF/override et appliquer les décisions existantes ; écrit seulement ici.
  Commande depuis la racine : `python -B interface/analysis/large-surfaces-20261110-v1/analyze.py`.
- Autorités source inchangées : `interface/index/`, `interface/gameplay-hud-bg2ee/index/`.

## Passe complémentaire — catalogue natif

- `verify_catalogue.py` → `verification-pass.json` ; lecture seulement.
- 617 MOS du KEY inspectés, y compris hors index interface ; BAM de l’index interface inspectés à partir de 10 000 px/frame.
- Oubli confirmé : `GKEYMAP`, `GOPGAMB`, `GOPSNDSB` (864×710), proposés au lot 22.
- Lot 22 : + `LOADCNTR`, `ROOMDELU/MERC/NOBE/PEAS`, `COADCNTR` ; variantes/illustrations à choisir, usage courant non déduit.
- Ambigus présentés puis conservés au lot 23 : `GUIRSP20` (panneau), `GUIDIFF` (livre), `BAR-FINL/STEP` (grand décor de progression).
- `GUINOTE` : fond du texte d’aide options graphiques, UI.menu:2759 ; absent KEY/override.
- `GUIBG` : menu `BACKGROUND`, UI.menu:16777 ; absent KEY/override. Ne pas fabriquer de remplacement.
- Limites : noms calculés Lua et chemins moteur ne sont pas une preuve d’usage runtime ; BAM hors index non audités globalement (sprites/autres domaines).

### Résultat consolidé

- 209 ressources logiques cataloguées ; 204 retenues, 3 hors périmètre, 2 références non résolues.
- Lots 22 et 23 conservés intégralement ; aucune génération/installation/release modifiée.
- Couverture statique vérifiée : 617 MOS KEY, BAM de l’index interface (seuil 10 000 px/frame), ajouts UI override.
- Override supplémentaire : barres B3T (2–10 px de large), contrôles X-* 64×64 ; hors grandes surfaces.
- Cette passe ne prouve pas toutes les routes calculées Lua/moteur ni l’usage actuel des variantes historiques.

### Révision finale des refus

- Demande : « finalement accepte meme ceux qu’on a refusé ».
- Réintégrés : `GUIW12_1..8`, `GUIVERB`, `DLGDIVI`, `PAPERSEP`, `PCHAPTER` (12 ressources).
- Historique des réponses conservé ; la dernière décision prévaut.
- 204 retenues / 209 cataloguées ; `GUISLDR` contrôle, `GUWBTP20` petite décoration non présentée et `GUWBTP30` debug restent hors périmètre ; 2 références introuvables.
- Sélection de production uniquement, aucune QA d’upscale ni modification du jeu déduite.
