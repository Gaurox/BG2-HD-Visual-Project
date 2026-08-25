# BG2 Upscale

Point d'entrée pour un LLM ou agent de code travaillant sur l'upscale des cartes, animations,
sprites, interfaces, portraits et vidéos de Baldur's Gate II: Enhanced Edition. Router chaque tâche
vers son contrat spécialisé avant toute lecture ou écriture de production.

## Par où commencer

Ce fichier **route** ; il ne documente pas. Chaque domaine a son document d'entrée : y aller
directement plutôt que de chercher dans l'arborescence.

| Tâche | Document d'entrée |
|---|---|
| **Traiter une zone de jeu** (décors, TIS/PVRZ) | [`pipeline/README.md`](pipeline/README.md) — séquence, branches, critères de passage |
| **Qualifier une zone avant son upscale** | [`pipeline/AREA_PREFLIGHT.md`](pipeline/AREA_PREFLIGHT.md) — détecte eau, alpha, secondaires et paire jour/nuit, puis route vers les procédures requises |
| **Méthode détaillée d'upscale des cartes** | [`pipeline/UPSCALE_MAP_PIPELINE.md`](pipeline/UPSCALE_MAP_PIPELINE.md) — résolution, découpe et correction colorimétrique |
| **Choisir le découpage SeedVR d'une carte** | Colonne `split_seedvr` d'`areas.csv` ; règle et seuils : [`pipeline/MAP_SPLITTING_POLICY.md`](pipeline/MAP_SPLITTING_POLICY.md) |
| **Connaître l'état, la géométrie ou la campagne d'une zone** | `areas.csv` — schéma et pièges : section « Catalogue des zones » ci-dessous |
| **Correction locale Topaz sur une carte** | [`pipeline/TOPAZ_GIGAPIXEL_CLI_REFERENCE.md`](pipeline/TOPAZ_GIGAPIXEL_CLI_REFERENCE.md) — CGI neutre sous masque uniquement |
| Zone **contenant de l'eau** | [`pipeline/WATER_MAP_PIPELINE.md`](pipeline/WATER_MAP_PIPELINE.md) — obligatoire, appelé par la séquence ci-dessus |
| Zone avec **masque alpha**, **secondaires** ou **jour/nuit** | [`pipeline/AREA_PREFLIGHT.md`](pipeline/AREA_PREFLIGHT.md) — routeur ; ne pas choisir une procédure à l'intuition |
| Contour de masque encore en escalier après build | [`pipeline/GEOMETRIC_ALPHA_MASK_CLEANUP.md`](pipeline/GEOMETRIC_ALPHA_MASK_CLEANUP.md) — correction post-build, réglages et QA réversible |
| Contour nécessitant une trajectoire plus lisse (asset ou map) | [`pipeline/SPLINE_ALPHA_MASK_PIPELINE.md`](pipeline/SPLINE_ALPHA_MASK_PIPELINE.md) — spline `fit 1.0` manuelle, génération sans installation |
| **Menus, écrans-titre ou HUD** | [`interface/README.md`](interface/README.md) — mécanisme, séquence, état des deux branches |
| **Procédure d'upscale des menus** | [`interface/menus-options-bg2ee/docs/MENU_UPSCALE.md`](interface/menus-options-bg2ee/docs/MENU_UPSCALE.md) |
| **Plan d'intégration du HUD** | [`interface/gameplay-hud-bg2ee/analysis/HUD_RESOURCE_INVENTORY.md`](interface/gameplay-hud-bg2ee/analysis/HUD_RESOURCE_INVENTORY.md) |
| **Portraits** | [`portraits/README.md`](portraits/README.md) ; mod publié : [`portraits/mod-PPE/LISEZ-MOI.md`](portraits/mod-PPE/LISEZ-MOI.md) |
| **Identifier, auditer ou upscaler un sprite de créature / Character** | [`sprite/README.md`](sprite/README.md) — point d'entrée agent et index normalisé ; procédure : [`sprite/SPRITE_UPSCALE_PIPELINE.md`](sprite/SPRITE_UPSCALE_PIPELINE.md) |
| **Animations de décor (BAM)** | [`pipeline/ANIMATION_UPSCALE_PIPELINE.md`](pipeline/ANIMATION_UPSCALE_PIPELINE.md) — x4 spatial V1 ; [`pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](pipeline/ANIMATION_UPSCALE_30FPS_V2.md) — x4 + 30 fps ; [`animations/UPSCALE_ANIMATIONS_ZONE.md`](animations/UPSCALE_ANIMATIONS_ZONE.md) — runtime |
| **Découper et installer les animations par zone** (obligatoire dès qu'un pack global dépasserait 512 MiB) | [`pipeline/ANIMATION_PACKS_PAR_ZONE.md`](pipeline/ANIMATION_PACKS_PAR_ZONE.md) — découpage, préflight, installation réversible et QA |
| **Ajouter une animation vidéo événementielle locale** (porte, pont, mécanisme sans animation native) | [`engine/InfinityEngine-Enhancer/source-patchee/docs/event-video-overlay-assets.md`](engine/InfinityEngine-Enhancer/source-patchee/docs/event-video-overlay-assets.md) — procédure LLM complète, de l'analyse WED à la QA carte/HUD |
| **Moteur et DLL** | [`engine/InfinityEngine-Enhancer/source-patchee/README.md`](engine/InfinityEngine-Enhancer/source-patchee/README.md) ; preuves BG2EE : [`bg2ee-2.7.3-evidence.md`](engine/InfinityEngine-Enhancer/bg2ee-2.7.3-evidence.md) |
| **Publier un paquet** | [`releases/PUBLISHING_STRATEGY.md`](releases/PUBLISHING_STRATEGY.md) |
| Problèmes techniques différés | [`pipeline/PROBLEMES_A_RESOUDRE.md`](pipeline/PROBLEMES_A_RESOUDRE.md) — symptômes constatés et essais négatifs, pas une procédure de production |
| Environnement, formats, pièges | [`HANDOVER.md`](HANDOVER.md) — **référence technique**, à consulter, pas une procédure à suivre |
| Travaux en cours et pistes non tranchées | [`CHANTIERS_OUVERTS.md`](CHANTIERS_OUVERTS.md) — état volatil, à ne pas confondre avec une procédure |

Sans document d'entrée à ce jour : `video/` et `release-staging/` (voir les sections de ce
fichier), `incoming/` (non classé par définition).

### Règle de classement des documents

Deux natures, deux règles — ne pas les confondre lors d'un rangement :

- Une **note de provenance** vit avec ses fichiers. Elle dit ce qui a produit le contenu d'un
  dossier et avec quels réglages. Elle ne se centralise jamais : sa valeur vient de son adjacence.
- Un **document de procédure** doit être atteignable depuis ce fichier **en un saut**. S'il ne
  l'est pas, il est invisible en pratique, même s'il est complet.

## Organisation

- `maps/<AREA>/` : une zone du jeu (extérieur majeur, intérieur, mini-zone ou sous-zone).
- `rendus-x1/tuiles-principales/` : rendu x1 avec les tuiles primaires du WED.
- `rendus-x1/tuiles-secondaires/` : rendu x1 avec les tuiles secondaires du WED substituées.
- `rendus-x1/tuiles-principales-nuit/`, `rendus-x1/tuiles-secondaires-nuit/` : mêmes rendus pour
  le WED nuit `ARxxxxN`, uniquement pour les zones qui en ont un (colonne `has_night_variant` de
  `areas.csv`). Fichiers nommés `<AREA>N-tuiles-*-x1.png`. Extraction : `batch_extract.py` /
  `batch_extract_secondary.py --night` ; contrôle : `validate_x1_masters.py --night`. Voir
  [`pipeline/DAY_NIGHT_MAP_PIPELINE.md`](pipeline/DAY_NIGHT_MAP_PIPELINE.md) — **méthode validée**
  sur AR0700/AR0700N : jour et nuit upscalés comme deux jeux indépendants avec `--tile-kind
  tuiles-*-nuit`.
- `maps/<AREA>/runs/<RUN>/tuiles-principales/01_brut/` : sorties xN issues du rendu de tuiles principales.
- `maps/<AREA>/runs/<RUN>/tuiles-secondaires/01_brut/` : sorties xN issues du rendu de tuiles secondaires.
- `tuiles-*/02_decoupe/` : morceaux x1 et leurs sorties xN, seulement pour les formats qui l'exigent.
- `tuiles-*/03_assemble/` : image xN reassemblee.
- `tuiles-*/04_corrige/` : image recalee colorimetriquement et LUT associee.
- `05_build/` : fichiers TIS/PVRZ/BAM et verification du build.
- `06_qa/` : captures, comparaisons et controles visuels.
- `pipeline/` : documents de procédure des zones + `pipeline/scripts/` (scripts Python).
- `animations/` : bibliothèque centrale des animations de décor (BAM), commune à toutes les zones.
- `interface/menus-options-bg2ee/` : menus, écrans-titre et sélecteurs.
- `interface/gameplay-hud-bg2ee/` : HUD de jeu.
- `portraits/` : portraits de personnages et mod PPE.
- `portraits-recrutables/` : un dossier par personnage recrutable (31 à ce jour).
- `sprite/` : index normalisé des animations/familles/BAM/ITM, jobs x2 et essais historiques.
- `engine/InfinityEngine-Enhancer/` : DLL, sources, patch et preuves BG2EE.
- `video/<VIDEO>/<VIDEO>.wbm` : fichier vidéo original extrait du jeu, conservé intact.
- `video/<VIDEO>/<VIDEO>.webm` : remux WebM sans réencodage de l'original.
- `releases/` : futurs paquets regroupant plusieurs cartes.
- `release-staging/` : paquets en préparation avant publication.
- `incoming/` : fichiers entrants qui ne sont pas encore classes.
- `archive/` : essais abandonnes ou fichiers historiques conserves.
- `backups/` : états réversibles horodatés, écrits par le pipeline avant chaque intégration.
  `backups/maps/<AREA>-<horodatage>/` (assets de zone remplacés), `backups/override/` (override
  complet), `backups/engine/` (DLL et shaders), `backups/masters-corrompus/` (rendus x1 mis en
  quarantaine par `validate_x1_masters.py`). Ne rien y supprimer sans vérifier qu'aucun document
  de run ne le référence comme point de retour.

Chaque `runs/<RUN>` couvre les deux variantes techniques de la meme zone : elles ne sont
pas separees dans deux runs. Les sous-dossiers numerotes ne sont crees que lorsqu'ils
contiennent des fichiers ; en particulier, `02_decoupe` ne doit pas etre cree avant
d'avoir identifie un format qui en a besoin.

Les rendus secondaires ne doivent pas etre injectes tels quels lorsqu'ils proviennent
d'un upscale IA distinct : l'IA modifie aussi le decor immobile. En l'absence d'une méthode
validée pour ces variantes, omettre le rendu secondaire xN lors du build et conserver les
tuiles secondaires originales rééchantillonnées.
Chaque fichier image conserve le code de sa carte dans son nom.

Une zone sans tuile secondaire conserve malgré tout son rendu secondaire x1 : il est alors
identique au rendu principal, sauf exceptions de décodage à diagnostiquer séparément.

Les termes `tuiles-principales` et `tuiles-secondaires` décrivent les deux rendus techniques
d'une même zone (tuiles primaires du WED / tuiles secondaires substituées) : ne pas les confondre
avec autre chose.

## Catalogue des sprites — `sprite/index/`

Utiliser [`sprite/README.md`](sprite/README.md) comme routeur du domaine. Les quatre CSV normalisent
les relations `ANIMATE.IDS`/INI/BAM/ITM : animations, familles et variantes, ressources décodées,
objets et équipements. `sprite/index/manifest.json` porte les hashes de l'installation analysée,
les limites et les totaux ; ne recopier ces valeurs dans aucun autre document.

Une ligne `pipeline_ready=yes` signifie que les prérequis automatisables connus sont satisfaits.
Elle ne vaut ni build, ni installation, ni validation ingame. Une tâche de production suit ensuite
[`sprite/SPRITE_UPSCALE_PIPELINE.md`](sprite/SPRITE_UPSCALE_PIPELINE.md). Une tâche d'évolution du
pipeline sélectionne une famille bloquée, traite chaque code `blocker`, régénère l'index et exécute
les tests avant tout job QA.

## Catalogue des zones — `areas.csv`

Registre des **369 zones injectables**, régénéré par `pipeline/scripts/refresh_area_catalog.py` —
qui préserve les colonnes manuelles.

**Seule source d'avancement du projet.** Ne recopier aucun état ni pourcentage dans la
documentation : y renvoyer. À la fin de chaque tâche de production ou de validation, l'agent doit
demander séparément l'accord pour mettre à jour le catalogue et pour intégrer les éléments
éligibles au manifeste de release; sans accord explicite, il n'écrit pas le manifeste — voir
[`pipeline/README.md`](pipeline/README.md) étape 8.

Colonnes dans l'ordre du fichier :

| Colonne | Contenu | Origine |
|---|---|---|
| `area_id` | Code de zone `ARxxxx` / `OHxxxx` | `chitin.key` |
| `campaign` | `SoA`, `ToB` ou `BlackPits` | Déduit, voir ci-dessous |
| `name_fr`, `name_en` | Nom bilingue de la zone | `dialog.tlk` ou identification externe |
| `name_source` | `WORLDMAP`, `WORLDM25` ou `area-list` | — |
| `name_strref` | strref du nom, ou l'`area_id` si aucun | — |
| `name_confidence` | `official` ou `confirmed` | — |
| `location_group` | Lieu unique découpé en plusieurs cartes | Régions de voyage |
| `accessible_from` | Zones d'où l'on entre (`;` si plusieurs) | Régions de voyage |
| `resolution_x1` | `LxH tuiles (largeur px x hauteur px)` | Overlay du `.WED` |
| `resolution_x1_mpx` | Surface x1 en mégapixels | Calculé |
| `split_seedvr` | Découpage SeedVR prescrit | Calculé, voir ci-dessous |
| `map_variants_count` | Nombre de rendus à produire (1, 2 ou 4) | `.WED` + `has_night_variant` |
| `workload_mpx` | Charge totale de la ligne, toutes variantes | Calculé |
| `workload_done_mpx` | Part de cette charge déjà traitée | Dérivé de `status` / `status_nuit` par `refresh_area_catalog.py` ; ne pas modifier à la main |
| `x1_tuiles_principales`, `x1_tuiles_secondaires` | Rendus x1 jour extraits | État réel des dossiers |
| `runs`, `build`, `status` | Suivi de production jour | **Manuel** |
| `has_night_variant`, `x1_tuiles_*_nuit` | Variante nuit `ARxxxxN` et ses rendus x1 | `chitin.key` + dossiers |
| `runs_nuit`, `build_nuit`, `status_nuit` | Suivi de production nuit | **Manuel** |
| `spline_fit_1_0` | Filtre alpha spline `fit 1.0` appliqué à la zone (`yes` si oui) | **Manuel** |
| `notes` | Contexte libre par zone | **Manuel** |

### Règles de remplissage

- **Noms** : `official` = issu de `WORLDMAP`/`WORLDM25`. `area-list` + `confirmed` = identifié
  hors carte du monde (textes de régions d'info et acteurs de la zone, recoupés avec une source
  externe) ; `name_strref` reprend alors l'`area_id`. Vide = non vérifié, ne pas nommer à
  l'intuition.
- **`BGEE.LUA-cheatAreas`** = libellé anglais de la table `cheatAreas` de `BGEE.LUA`
  (`data/Patch2.bif`), celle qu'affiche le menu de téléportation de debug. **Livrée avec le jeu,
  mais non localisée et non canonique** : ce sont des étiquettes de développement, pas des noms de
  carte du monde. Elles ne remplissent donc que `name_en` — `name_fr` reste vide — et
  `name_strref` reprend l'`area_id`. `confirmed` quand le libellé identifie la zone sans
  ambiguïté ; **`name_confidence` vide** quand il est partagé par plusieurs zones (`Crypt` pour
  AR0805 et AR0806) ou marqué incertain par les développeurs (`Ancient Spirits?`), la raison étant
  alors écrite en `notes`. Import du 2026-08-18 : 228 zones renseignées (206 `confirmed`,
  22 sans confiance), 65 restent sans nom. **Ne jamais écraser un nom existant avec cette
  source** : elle est moins fiable qu'une identification recoupée.
- **Topologie** : `location_group` et `accessible_from` viennent des régions de voyage
  (`Region type=2`) des `.ARE`, jamais des noms de dossier. `accessible_from` vaut `worldmap`
  pour une entrée depuis la carte du monde.
- **`campaign`** : 266 zones par propagation depuis les seeds `WORLDMAP` (SoA) / `WORLDM25`
  (ToB) sur le graphe de régions ; les 103 restantes recoupées avec la référence IESDP
  (`appendices/area_lists/bg2aref.htm`, Gibberlings3/iesdp). `SoA`/`ToB` incluent les zones EE
  des compagnons exclusifs (Dorn, Neera, Hexxat), rattachées à leur période. `BlackPits` =
  mode arène, hors trame principale.
- **Géométrie** : `resolution_x1` est lue dans l'overlay primaire du `.WED`.
  `split_seedvr` applique [`MAP_SPLITTING_POLICY.md`](pipeline/MAP_SPLITTING_POLICY.md)
  (~1,80 Mpx x1 par morceau) et en reprend les libellés ; répartition 189/43/66/27/14/30,
  conforme à l'inventaire de ce document.
- **`map_variants_count`** = `(2 si secondaires distinctes, sinon 1) × (2 si nuit, sinon 1)`.
  186 zones ont une secondaire distincte, 31 une variante nuit → 169 lignes à 1, 183 à 2, 17 à 4.
- **`workload_done_mpx`** : une variante compte comme traitée si son `status` (ou `status_nuit`)
  vaut `installed-pending-qa` ou `validated-installed` ; `source-only`/`source-pending` = 0.
  Il est recalculé par `refresh_area_catalog.py` après toute modification de statut.

### Pièges

- **Ne pas déduire la campagne d'une plage de numéros** : les préfixes `OHxxxx` mélangent SoA et
  ToB. Ne pas se fier non plus à une recherche web non filtrée par jeu : BG1 et BG2 ont chacun
  leur table de zones, qui se recoupent numériquement sans rapport de contenu (`AR1008` désigne
  deux lieux différents selon le jeu).
- **`accessible_from` vide (65 zones) ne veut pas dire « inaccessible »** : certaines transitions
  passent par un script (`EscapeArea`) et non par une région, d'autres liaisons sont à sens unique.
- **`map_variants_count` ne se déduit pas de `x1_tuiles_secondaires`**, qui vaut `yes` même quand
  le rendu secondaire duplique le primaire. Lire le `.WED` (cellule `secondary != 0xFFFF`).
- **Seuil de découpe** : s'il est réévalué, mettre à jour `MAP_SPLITTING_POLICY.md` **et** le
  script qui régénère `split_seedvr` ensemble.

### Tableau de bord

`BG2_Areas.xlsx` (bureau) charge `areas.csv` par Power Query et calcule l'avancement en Mpx par
campagne et global ; il est en lecture seule vers le CSV, qui reste la source de vérité. À la
recréation : forcer délimiteur `,` + encodage UTF-8 dans la requête, et convertir les colonnes
numériques en culture `en-US` — sinon la locale FR lit mal le point décimal et vide les colonnes.

## Animations de décor — inventaire et prototype runtime validé

Les animations attachées aux cartes (lampes, flammes, fumée, eau, etc.) sont des ressources
`BAM`, placées une ou plusieurs fois dans une zone. Une même ressource peut être réutilisée
par plusieurs zones : elle ne doit donc jamais être dupliquée dans chaque dossier de carte.

La bibliothèque canonique est `animations/` :

- `animations/ressources/<BAM>/source.bam` : source extraite ;
- `animations/ressources/<BAM>/<BAM>_sheet.png` : planche RGB PNG sans perte ;
- `animations/ressources/<BAM>/<BAM>_alpha.png` : masque de transparence correspondant ;
- `animations/ressources/<BAM>/<BAM>.gif` : aperçu animé ;
- `animations/index/ressources.csv` : une ligne par BAM (frames, nombre d'occurrences,
  zones utilisatrices) ;
- `animations/index/occurrences.csv` : une ligne par pose dans une zone (zone, position,
  ressource, cycle et frame initiale) ;
- `animations/index/zones.csv` : synthèse inverse, par zone ;
- `animations/index/erreurs.csv` : références déclarées par une zone mais absentes de
  l'installation examinée.

L'inventaire actuel couvre 423 zones : 3 442 occurrences référencent 266 BAM
distincts, dont 246 ont été extraits. Les 20 références sans ressource disponible restent
dans les index afin de ne pas être perdues.

L'extracteur reproductible est `pipeline/scripts/extract_area_animations.py` :

```powershell
python pipeline/scripts/extract_area_animations.py --keep-going
```

Le runtime générique x4 est validé sur plusieurs ressources et conserve les dimensions logiques x1
dans le moteur tout en utilisant une texture OpenGL physique x4. Le mode registre v2
`TimedTimeline` ajoute une timeline visuelle pause-aware ; son proof 15 -> 30 fps `PORTL1A` a été
accepté, avec une petite irrégularité de couture connue. Les procédures complètes sont dans
[`animations/UPSCALE_ANIMATIONS_ZONE.md`](animations/UPSCALE_ANIMATIONS_ZONE.md).

Ne pas upscaler les planches PNG concaténées : traiter chaque frame séparément avec son alpha,
ses dimensions, son point d'ancrage et son cycle. Le runtime reste verrouillé au build BG2EE
`2.7.3.x`. Le pipeline spatial V1 est
[`pipeline/ANIMATION_UPSCALE_PIPELINE.md`](pipeline/ANIMATION_UPSCALE_PIPELINE.md) ; le pipeline
temporel séparé est
[`pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](pipeline/ANIMATION_UPSCALE_30FPS_V2.md).

**Budget mémoire — contrainte structurante.** Le moteur ne charge qu'un seul registre, dont la
charge RGBA est plafonnée à 512 MiB, **cumulativement sur toutes les zones converties**. Or
l'inventaire complet pèse ~2,7 GiB en x4 natif et ~8 GiB interpolé : un pack global ne peut pas
couvrir le jeu. La sortie du 30 fps est donc un pack d'auteur à **découper par zone** avant
installation — [`pipeline/ANIMATION_PACKS_PAR_ZONE.md`](pipeline/ANIMATION_PACKS_PAR_ZONE.md). Le
plafond devient alors une limite par zone, que 234 des 236 zones porteuses d'animations respectent
seules. Baisser la cadence à 20 ou 25 fps **n'économise rien** : voir le tableau de
[`ANIMATION_UPSCALE_30FPS_V2.md`](pipeline/ANIMATION_UPSCALE_30FPS_V2.md).

## Transitions vidéo événementielles

Le runtime vidéo local `AR1300/BRIDGE01` est validé en jeu : ouverture, fermeture,
inversion depuis la frame courante, masquage de la bascule instantanée WED et rendu
strictement au-dessus de la carte mais sous tous les HUD et menus. La version média
actuelle est un agrandissement Lanczos 2048² ; le runtime est validé, mais la vidéo
SeedVR2 7B x4 reste à produire et à tester. Procédure reproductible :
[`event-video-overlay-assets.md`](engine/InfinityEngine-Enhancer/source-patchee/docs/event-video-overlay-assets.md).

## Vidéos

- Un dossier par vidéo, directement sous `video/`; aucun sous-dossier supplémentaire.
- Les vidéos originales sont en `.wbm`, déjà des conteneurs WebM (VP8, 1280×720 ; audio Vorbis sauf `outro`).
- Le `.webm` associé est créé avec `ffmpeg -map 0 -c copy` : les flux sont copiés, sans perte ni réencodage.
- Les doublons localisés sont préfixés par leur langue (`de_DE_`, `it_IT_`, `pl_PL_`) afin d'éviter tout écrasement.
- Ne jamais remplacer ou supprimer le `.wbm` source. Toute future conversion destinée à l'upscale doit être produite à côté de lui.

## Méthode validée

- La résolution SeedVR2 7B/LAB par défaut est **x4** pour toute zone. Le nombre de morceaux et
  la grille sont définis par [`pipeline/MAP_SPLITTING_POLICY.md`](pipeline/MAP_SPLITTING_POLICY.md) :
  les plus grandes maps passent en 2×5, soit dix morceaux à recouvrement. L'utilisateur peut
  demander explicitement un x2 lorsqu'il privilégie le poids ou la rapidité.
- Les builds x4 entièrement opaques utilisent DXT1 par défaut. La présence d'alpha, d'eau ou de
  liquide impose DXT5 afin de préserver les transparences.
- **Pagination PVRZ : 2 048 px par défaut**, passage à 4 096 **uniquement** si 2 048 dépasse la
  limite de nommage, et **échec explicite du build** si 4 096 ne suffit pas — aucune escalade
  au-delà. Ne jamais forcer 4 096 sur une carte qui tient en 2 048, et ne pas rebuilder une carte
  2 048 déjà valide au seul motif de cette règle. Raison : un resref tient sur 8 caractères, or le
  préfixe d'une variante **nuit** (`A0900N`) en consomme 6 : elle plafonne à **100 pages**, contre
  1 000 pour le jour. En x4 une page de 2 048 px ne porte que 49 tuiles, si bien qu'une grande zone
  nuit dépasse ce plafond dès ~4 900 tuiles — au-delà, le nom devient inexprimable et **le jeu
  plante** (`0xC0000005`). Règle détaillée et exception `AR0900` jour :
  [`pipeline/README.md`](pipeline/README.md) étape 4 et
  [`pipeline/PROBLEMES_A_RESOUDRE.md`](pipeline/PROBLEMES_A_RESOUDRE.md).
- Tout masque alpha non opaque est restauré depuis le x1 puis lissé bilinéairement à la mise à
  l'échelle. Cette règle s'applique à toutes les zones et à toutes les variantes, pas seulement à
  l'eau ; le flou gaussien demeure un réglage de finition réservé aux rives liquides.
- Topaz CGI neutre est autorisé seulement comme correction locale sous un masque dessiné par
  l'utilisateur ; il ne remplace pas une carte complète.
- Une zone à variante nuit (`ARxxxxN`) est traitée comme **deux jeux indépendants**, jour et nuit,
  chacun avec sa propre correction colorimétrique LAB — jamais de référence croisée entre les
  deux. Voir [`pipeline/DAY_NIGHT_MAP_PIPELINE.md`](pipeline/DAY_NIGHT_MAP_PIPELINE.md), validé
  sur AR0700/AR0700N.
- Un masque blanc sélectionne CGI et le noir conserve SeedVR. Le bord est fondu avant la
  composition ; le masque doit correspondre exactement à la variante xN ciblée.
- La référence finale AR0602 est le run SeedVR2 7B/LAB x4 sans CGI ni masque,
  `seedvr2-7b-int8-lab-grid-2x5-x4-png-review` ; les rendus primaire et secondaire y sont
  inférés séparément.
- Les prototypes et les réglages rejetés sont archivés, sans être des candidats de production.
