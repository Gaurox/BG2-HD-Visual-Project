# Surfaces liquides des maps — base de conception et de validation des pipelines

Date de l'analyse : **2026-09-23**. Statut : **stratégie proposée ; aucun pipeline universel validé**.

Ce document reprend la notice d'analyse vanilla/HD remise dans la conversation. Il sert de base
à la création des pipelines et aux décisions jusqu'à leur validation définitive. Les rubriques
sont des repères de conception, pas un ordre de travail imposé ni une obligation de préflight.

Évolution du 2026-09-23 : rendu spatial du lot témoin accepté globalement par l'utilisateur
(`manifests/liquid-families-spatial-user-qa-20260923-v1.json`). Cible temporelle demandée :
**30 FPS pour toutes les composantes animées de l'eau**, sans accélérer les cycles.
Premier essai [AR1600 v1](AR1600_WATER_30FPS_20260923.md) (36 phases + demi-fondus) remplacé.
**v2 validée ingame le même jour** : 72 phases réelles, interpolation périodique à bande limitée +
SeedVR vidéo — [AR1600 v2](AR1600_WATER_30FPS_V2_20260923.md). Procédé commun des familles :
[TEMPORAL_30FPS_PIPELINE.md](TEMPORAL_30FPS_PIPELINE.md). Apollo/flux rejetés pour les overlays liquides.
Les constats de l'analyse initiale ci-dessous restent historiques ; cette cible ne signifie pas
que toutes les maps ont déjà reçu une interpolation.

Étude complémentaire après capture du bateau :
[lissage généralisable des contours devant l'eau](LISSAGE_CONTOURS_EAU_STRATEGIE_20260923.md).
Constat AR1600 : alpha déjà bilinéaire, mais silhouette x1 et RGB noir partiellement révélés ;
stratégie proposée = géométrie + RGB de bord + composition des passes.
Masque témoin accepté visuellement ; [correctif couleur/BC3 installé sur le bateau AR1600](AR1600_CONTOURS_ESSAI_20260923.md),
validation ingame en attente. Aucune généralisation à la map entière ou à une autre variante.

## 1. Mandat, périmètre et statut des preuves

- Objectif : un traitement commun ; sinon, quelques recettes déterminées par la structure réelle.
- Surfaces concernées : mer, océan, rivière, bassin, flaque, marais, égout, huile, lave,
  acide/saumure ou similaire **participant à la composition des maps**.
- Inclure les occurrences ARE/BAM uniquement lorsqu'elles constituent directement la surface
  ou son raccord : cascade, bassin, prolongement animé. Exclure les animations indépendantes.
- Analyse initiale : lecture seule des KEY/BIF/WED/ARE/TIS/PVRZ, fichiers HD installés,
  sources moteur, images existantes et décisions documentées. Aucun test, aucune nouvelle
  validation en jeu, aucune modification d'asset/script/configuration.
- Présent Markdown : création documentaire explicitement demandée après remise du rapport.
  Elle n'autorise ni implémentation, ni essai, ni installation, ni modification release.
- Les constats sur l'installation sont une photographie du 2026-09-23 ; ne pas les transformer
  en garanties sur une installation ultérieure.

| Désignation | Résolution / autorité |
|---|---|
| `VANILLA` | Entrée explicite de l'analyse : `G:/AI/BG2_Vanilla_23534562/` ; Steam BuildID 23534562, voir `VANILLA_BUILD.txt` |
| `HD` | `config://bg2ee_game_root` ; résolution lors de l'analyse : `G:/SteamLibrary/steamapps/common/Baldur's Gate II Enhanced Edition/` |
| Chemins de code/artefacts non préfixés dans le texte | Relatifs à la racine du dépôt BG2_Upscale |
| Maps et QA de décor | [`areas.csv`](../../areas.csv) |
| File eau par WED | [`ingame-map-tracking-v1.json`](ingame-map-tracking-v1.json) |
| Sélections eau | [`release-tracking-v1.json`](release-tracking-v1.json) et décisions immuables qu'il référence |
| Politique overlays release | [`overlay-sources.json`](../../releases/BG2-HD-Upscale/manifests/overlay-sources.json) |
| Surfaces ARE/BAM | [`animation_upscale_registry.csv`](../../animations/index/animation_upscale_registry.csv), sélections et QA immuables correspondantes |

**États séparés : source / production / QA / installation / release.** Décor accepté ≠ eau
acceptée ; fichier installé ≠ validé ; recette historiquement validée ≠ QA de nouveaux octets.
Un reçu d'installation « pending » antérieur ne remplace pas une QA immuable postérieure.
Ce guide ne remplace aucune de ces autorités.

## 2. Conclusion de conception

**Un pipeline commun est possible ; une recette unique imposant même alpha, même upscale,
même animation et même shader est contredite par les cas étudiés.**

Architecture recommandée : traitement commun de la composition + quelques branches de
topologie + profils de matériau et exceptions déclaratives. Les huit groupes de ressources
recensés ne justifient pas huit scripts de production par map.

Priorité : préserver le contrat natif et les contributions du décor ; améliorer séparément
RGB, contours, animation et matériau. La route2 actuelle est un module utile, pas encore
une représentation universelle de toutes les surfaces.

## 3. Inventaire vanilla vérifié

Lecture en mémoire de `VANILLA/chitin.key` et des ressources des archives BIF :

- **400 WED** parcourus.
- **67 WED déclarent** un overlay liquide : **98 slots déclarés**.
- **63 WED l'utilisent effectivement** : **94 slots actifs**.
- Critère actif : au moins une cellule principale sélectionne le slot par ses bits d'overlay.
- Déclarations inactives : `AR0700`, `AR0700N`, `AR2804`, `AR2805` ; leurs cellules ne
  sélectionnent jamais l'overlay déclaré. AR2804/5 possèdent néanmoins des surfaces ARE/BAM.
- **17 noms de TIS actifs**, regroupés en huit familles de ressources.
- Le compte historique 67/98 de la matrice n'est pas faux : il décrit les déclarations,
  pas seulement les cellules actives.
- Ce recensement n'identifie pas automatiquement toutes les flaques peintes dans le décor
  ni toutes les surfaces portées par des occurrences ARE/BAM.

| Groupe vanilla | WED actifs¹ | Images disponibles par TIS | Exemples |
|---|---:|---:|---|
| `WTLAKE` | 14 | 6 | AR0900, AR0204, AR1600, AR2300 |
| `WTPOOL` | 13 | 6 | AR1000, AR0408, AR2000 |
| `WTSWAM` | 19 | 6 | AR1607, AR1800, AR1000N |
| `WTSEW` | 2 | 6 | AR0404, AR2100 |
| `WTOIL` | 6 | 6 | AR0413, AR0603, AR2102 |
| `WTLAKA–D` | 2 | 8 | AR3000, AR6300 |
| `WTLAVA–D` | 6 | 12 | AR0011, AR1401, AR5200 |
| `WT5000A–D` | 2 | 8 | AR5000, AR5203 |

¹ Les comptes de WED se chevauchent : AR1100 emploie WTPOOL et WTSWAM.

### 3.1 Noms de lieux et nature du liquide

- Littoral de Brynnlaw `AR1600` : `WTLAKE` ; une mer n'implique pas `WTWAVE`.
- Bassins `AR1000` : `WTPOOL` le jour, `WTSWAM` dans `AR1000N`.
- `WTWAVE`, `WTRIV`, `WTGOO` existent dans les archives, mais aucun overlay WED actif
  recensé ne les référence. Leur présence n'établit pas de nouvelles familles utilisées.
- Aucun overlay actif ne démontre une famille spécifique « acide ». Ne pas déduire
  la nature chimique des bassins d'une couleur ; leur structure technique reste classifiable.

### 3.2 Ressources physiques vérifiables

Les noms ARE/WED/TIS suivants désignent des ressources internes aux archives, pas nécessairement
des fichiers autonomes. Les correspondances exactes passent par `chitin.key` ; les pages PVRZ
des exemples examinés peuvent être résolues dans `data/Patch24.bif`.

| Ressources | Archive relative à `VANILLA/` |
|---|---|
| WTLAKE, WTPOOL, WTSWAM, WTSEW, WTOIL, WTLAVA–D et variantes météo | `data/ARMisc.bif` |
| WTLAKA–D, WT5000A–D et variantes météo | `data/25ArMisc.bif` |
| AR0900.WED/TIS | `data/AREA0900.bif` |
| AR1000.WED/TIS et AR1000N.WED/TIS | `data/AREA1000.bif` |
| AR1607.WED/TIS | `data/AREA160B.bif` |
| AR1800.WED/TIS | `data/AREA1800.bif` |
| AR0404.WED/TIS | `data/AREA040A.bif` |
| AR2100.WED/TIS | `data/AREA2100.bif` |
| AR0413.WED/TIS | `data/AREA040B.bif` |
| AR3000.WED/TIS ; AR6300.WED/TIS | `data/AREA3000.bif` ; `data/AREA6300.bif` |
| AR0011.WED/TIS ; AR5200.WED/TIS | `data/AREA000A.bif` ; `data/AREA5200.bif` |
| AR5000.WED/TIS ; AR5203.WED/TIS | `data/AREA5000.bif` ; `data/AREA520B.bif` |
| AR2300.WED/TIS | `data/AREA2300.bif` |
| ARE des exemples SoA | `data/Areas.bif` |
| ARE des exemples ToB, dont AR3021 | `data/25Areas.bif` |

## 4. Contrat de composition vanilla

### 4.1 Structure

- ARE `+0x08` : WED associé.
- WED : grille de cellules logiques **64 × 64** ; overlay 0 = décor principal.
- En-tête de couche : dimensions, resref TIS, pointeurs tilemap/lookup, paramètres de couche.
- Cellule : début/nombre d'indices principaux, tuile secondaire éventuelle, bits d'overlay,
  vitesse et flags d'état. `0xFFFF` : pas de secondaire.
- Les bits sélectionnent les overlays ; une déclaration dans un en-tête ne prouve pas leur usage.
- TIS : pixels palettisés ou références page/X/Y dans des PVRZ.
- Les TIS liquides vanilla examinés sont palettisés : **5120 octets par tuile 64 × 64**.
- Les TIS de base représentatifs ont des entrées PVRZ **12 octets** ; les pages examinées
  sont en DXT1. Le moteur compose donc des couches de formats différents.
- Primaire/secondaire sert également aux portes et états alternatifs : ce couple seul
  ne permet pas d'identifier l'eau.

Références : [WED IESDP](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/wed_v1.3.htm),
[TIS IESDP](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/tis_v1.htm),
[PVRZ IESDP](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/pvrz.htm),
[`file_formats.h`](../../engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/file_formats.h).

### 4.2 Contributions à préserver

| Contribution | Contenu / rôle |
|---|---|
| Art local | Fond, coloration, ombres, reflets, rive et objets appartenant au décor |
| Sous-couche animée | Motif liquide partagé entre cellules |
| Masques et passes primaire/secondaire | Zones visibles et opacité des contributions |
| Paramètres moteur | Opacité de zone, teinte, météo, cadence, ressources effectivement sélectionnées |
| Surface locale ARE/BAM éventuelle | Cascade/bassin/prolongement et ses raccords avec le décor |

Modèle simplifié du mélange non émissif, hors teinte/éclairage :

```text
C = a × A + (1 − a) × U
A : art local ; U : liquide animé ; a : opacité effective de l'art

Extension route2 : U2 = mix(U, matériau_procédural, q)
                  C  = a × A + (1 − a) × U2
```

L'opacité effective ne se réduit pas à l'alpha d'un PNG : elle dépend aussi du format et
de la passe de dessin. **128 n'est pas universel.**

| ARE vanilla | Champ à `0x52` | Opacité native correspondante |
|---|---:|---:|
| AR0900, AR1800 | 0 | Défaut moteur 128 |
| AR1607 | 100 | 100 |
| AR6300 | 160 | 160 |

Le passage DXT1 → DXT5 doit préserver le résultat de composition. Alpha255 partout peut cacher
l'animation ; alpha0 partout peut supprimer les ombres/reflets. Les populations avec secondaire
et sans secondaire n'expriment pas leur art de la même manière.

Preuve moteur du défaut 0→128 :
[`WTSWAM_AR1607_AR1800_PILOT_20260912.md`](WTSWAM_AR1607_AR1800_PILOT_20260912.md),
rubrique diagnostic révisé. BG2 classique et EE n'utilisent pas des masques interchangeables :
[tis2ovl](https://github.com/InfinityTools/tis2ovl). Ne pas transposer sans distinction une
reconstruction GemRB/NI à tous les chemins du moteur Beamdog.

### 4.3 Temporalité et variantes

- Un cycle = **lookup WED réellement sélectionnée + vitesse**, pas toutes les images du TIS.
- AR0512 : WTLAKE limité à **une image** en vanilla.
- AR5200/5201/5204 : lave à **11 indices `[0…9,11]`**, malgré 12 images dans chaque TIS.
- Jour/nuit peut changer art, WED et famille ; AR1000/N en est la preuve.
- La pluie peut sélectionner un autre TIS possédé par le moteur ; traiter seulement le nom sec
  écrit dans le WED est insuffisant.
- Les slots d'un même pavage peuvent avoir des valeurs de vitesse différentes ; préserver
  l'organisation native avant de proposer une nouvelle animation.

## 5. Classification : quatre classes de composition, profils de matériau séparés

| Classe | Fonctionnement | Recette standard proposée |
|---|---|---|
| Surface peinte dans le décor | Pixels du TIS principal, sans animation liquide distincte sur la portion concernée | Traiter avec le décor continu ; conserver reliefs/reflets/raccords ; ne pas créer artificiellement un overlay |
| Motif animé unique répété | Overlay généralement 1 × 1 réutilisé dans les cellules sélectionnées | Traitement spatial périodique ; séquence temporelle conservée ; composition primaire/secondaire restaurée |
| Pavage animé à plusieurs motifs | WTLAKA–D, WTLAVA–D, WT5000A–D distribués spatialement | Traiter les relations entre motifs et séquences ensemble ; reconstruire les raccords selon le pavage réel |
| Surface locale ARE/BAM composée | Bassin, cascade ou prolongement animé placé dans le décor | Traiter silhouette, positions, occlusion et raccords avec la map et entre occurrences |

La classe « décor peint » relève du pipeline map ordinaire ; les trois autres demandent des
opérateurs spécifiques dans la même infrastructure. Matériaux proposés : eau claire,
eau trouble/égout, liquide visqueux, lave émissive ; les huit groupes vanilla servent de
références de qualification, sans imposer huit programmes séparés.

### 5.1 Pavages : ne pas confondre distribution et superposition

- **Aucune cellule des 400 WED examinés ne sélectionne plusieurs overlays liquides simultanément.**
- A/B/C/D sont distribués entre cellules ; ce ne sont pas quatre nappes complètes superposées.
- AR3000 et AR5203 : répartition régulière **2 × 2**, A/B au-dessus de C/D selon parité X/Y.
- AR6300, AR5000 et les maps de lave : ne pas appliquer automatiquement cette même parité globale.
- Rendre chaque motif périodique isolément ne garantit pas les raccords A↔B ou A↔C.
- Paramètre nécessaire : voisinages réellement présents dans les WED consommateurs ; traiter
  un supermotif seulement lorsque cette topologie est établie.

### 5.2 Exemples quantifiés

| WED | Cellules liquides actives | Avec secondaire | Conséquence |
|---|---:|---:|---|
| AR0900 | 1635 | 860 | Coexistence des deux populations |
| AR1000 / AR1000N | 37 / 37 | 37 / 37 | Aucune correction centrale sans secondaire à appliquer |
| AR1607 | 874 | 349 | 525 centrales ; opacité native 100 |
| AR1800 | 101 | 94 | 7 centrales ; opacité native 128 |
| AR0404 | 140 | 138 | 2 cellules sans secondaire |
| AR2100 | 208 | 169 | Contrat distinct du témoin AR0404 |
| AR0413 | 576 | 227 | Eau/huile + sentinelles à examiner par usage |
| AR2300 | 1111 | 1111 | Surface WED entièrement à secondaire + cascades ARE/BAM |
| AR3000 / AR6300 | 322 / 36 | 138 / 36 | Même groupe A–D, populations différentes |
| AR5000 / AR5203 | 723 / 634 | 402 / 268 | Même groupe WT5000, distribution différente |

### 5.3 Surfaces locales directement constitutives

| Map | Ressources ARE/BAM vanilla vérifiées | Composition / état HD documenté |
|---|---|---|
| AR2300 | FALL1A/B, FALL2/3/4, FALL5A/B/C, FALL6, FALLA1/A2 ; AM2300A ×3 | Cascade/prolongements en complément de WTLAKE ; raccord FALL6/statue corrigé dans le décor |
| AR2804 | AM2805A/B/C ; deuxième B désactivé | B/C fusionnés en HD via porteur AM28ADD ; QA acquise avec réserve mineure sur jointure horizontale |
| AR2805 | AM2805A | Variante de composition locale ; WTPOOL déclaré mais inactif |
| AR2801 / AR2802 | AM2801A / AM2802A | Bassins ovales ; map HD porte déjà l'eau, pas de couverture de trou noir nécessaire |
| AR3021 | AM3021D/E/F | Bassins illithids ; recette locale validée ; ne pas affirmer « acide » d'après couleur |

Références : [`ANIMATION_RECIPE_CATALOG.md`](../../animations/ANIMATION_RECIPE_CATALOG.md)
(LIQUIDE-SEEDVR-SPLINE4, BASSIN-SUR-TROU-DE-CARTE),
[`animation_upscale_registry.csv`](../../animations/index/animation_upscale_registry.csv)
(AM2801A/AM2802A/AM2805A–C/AM3021D–F/FALL6).

Les flags ARE natifs et les changements de blend HD doivent rester distincts. Le support
« eau déjà peinte » versus « trou à couvrir » justifie une différence de composition,
indépendamment de l'étiquette générique « bassin ».

## 6. Traitements HD existants et acquis

### 6.1 Recettes documentées

| Cas | Traitement et portée de l'acquis |
|---|---|
| WTLAKE — AR0204 / AR1600 | Composition native conservée ; alpha effectif restauré ; raccords RGB réparés ; overlay x4 périodique ; animation enrichie ; validation documentée |
| WTPOOL — AR1000 jour | SeedVR amplifiait la trame diagonale en quadrillage ; bilinéaire x4 périodique 3 × 3 retenu ; version q0 jugée figée ; alias WTPOOL2, 36 phases et route2 q0.70 validés |
| WTSWAM — AR1607 / AR1800 | Opacités 100/128 ; raccords réparés ; alias WSWPIL/WSWPILR sec/pluie compatibles 36 phases ; validation documentée |
| WTSWAM — AR1000N | Variante sèche nocturne validée ; pluie installée mais non observée séparément |
| WTSEW — AR0404 | Overlay x4, 36 phases et matériau dédié q0.70 validés |
| WTSEW — AR2100 | État de repli installé accepté : WED stock + overlay partagé ; ne valide ni équivalence vanilla ni future entrée route2 |
| WTOIL — AR0413 | Ancien remplacement procédural, primaires libérées à alpha0, contours et sentinelles visibles corrigés ; historiquement validé |
| AR0300N v10 | Choix artistique validé : opacité primaire/secondaire appariée 160, RGB nocturnes conservés, dépendance au runtime correspondant |

Sources principales :

- [`VALIDATED_WATER_RECIPES.md`](VALIDATED_WATER_RECIPES.md).
- [`AR0204_AR1600_REPAIR_20260912.md`](AR0204_AR1600_REPAIR_20260912.md).
- [`README.md`](README.md) : WTPOOL / AR1000N.
- [`WTSWAM_RAIN_RESOURCE_REPAIR_20260912.md`](WTSWAM_RAIN_RESOURCE_REPAIR_20260912.md).
- [`WTSEW_AR0404_PILOT_20260912.md`](WTSEW_AR0404_PILOT_20260912.md).
- [`AR0413_WTOIL_CASE.md`](../../docs/archive/map-cases/AR0413_WTOIL_CASE.md).
- [`QA AR0300N v10`](manifests/ar0300n-reflections-alpha160-validated-20260912-v10.json).

Depuis le 2026-09-23, les témoins AR1600, AR1000 jour, AR1607, AR0404 et AR0413 sont installés
avec les alias du lot spatial (AR1600 : 30 FPS v2) ; les états route2 36 phases/q0.70 ci-dessus
restent des acquis historiques, non actifs sur ces WED.

### 6.2 Paramètres utiles à conserver sans les universaliser

- WTLAKE : référence x4 historique avec contexte périodique 3 × 3/crop central ; wavelet
  conservé sur cette référence. Le simple changement LAB→wavelet ne rend pas un motif périodique.
- Nouveaux traitements du lot eau : correction couleur `none` ; les références LAB/wavelet
  acquises ne deviennent pas incorrectes par cette nouvelle préférence.
- WTPOOL : bilinéaire périodique + interpolation cyclique linéaire 6→36 ; preuve que
  le génératif n'est pas toujours préférable.
- Raccords AR0204/1600 : donneur = maître secondaire x4 de la **même variante** ; bande 8 px x4,
  garde de vraie rive 1 px x1, poids `[1,1,1,1,.75,.5,.25,0]`, marges adaptées. Certains
  changements visuels viennent des RGB, pas d'une modification d'alpha décodé.
- Contours : traitement sur canvas WED complet ; conserver îlots/trous, rôles primaire/secondaire
  et usages partagés. Réglage par tuile indépendante insuffisant.
- AR0413 : alpha0 appartient au contrat procédural historique. Ce n'est pas une recette
  de préservation native ; une migration constituerait un changement visuel à valider.
- AR0300N : v8 alpha208 rejetée ; v9 retour natif ; v10 alpha160 apparié validé par QA
  postérieure au reçu d'installation. q0 seul ne restaure pas v9 : assets et runtime sont liés.
- Surfaces ARE/BAM : SeedVR + timeline + spline/feather disposent de témoins validés ; un
  bassin sur trou et un bassin sur eau peinte n'exigent pas le même raccord de couverture.

### 6.3 Photographie de l'installation HD lue le 2026-09-23

Chemins sous `HD/override/`, sauf retour aux ressources du KEY lorsqu'aucun override n'existe.
Les dimensions indiquées sont celles des tuiles de texture, pas celles de la grille logique.

| Ressource | TIS lu | Sélection WED / particularité |
|---|---|---|
| WTLAKE | 36 phases, 256 px, PVRZ DXT5 | AR0900/N, AR0300N et autres WED adaptés à 36 |
| WTPOOL | 6 phases, 128 px, PVRZ DXT5 | Ressource partagée x2 |
| WTPOOL2 | 36 phases, 256 px, PVRZ DXT5 | Alias AR1000 jour ; `WPOOL200.PVRZ` |
| WTSWAM | 36 phases, 256 px, PVRZ DXT5 | Partagé ; 16 WED actifs gardent leur lookup stock 0–5 |
| WSWPIL / WSWPILR | 36 phases chacun, 256 px, PVRZ DXT5 | AR1607, AR1800, AR1000N ; `WWPIL00.PVRZ` / `WWPILR00.PVRZ` |
| WTSEW | 36 phases, 256 px, PVRZ DXT5 | AR0404.WED : 36 ; AR2100.WED stock : 6 |
| WTOIL | Stock palettisé, 6 images | Pas d'override TIS lu |
| WTLAKA | 8 images, 128 px, PVRZ DXT5 | Exemple lu du groupe turquoise x2 |
| WTLAVA | 12 images, 256 px, PVRZ DXT5 | Exemple lu du groupe lave x4 ; lookup11 conservée sur certains WED |
| WT5000A | Stock palettisé, 8 images | Exemple lu du groupe WT5000 conservé stock |

Les variantes `WTLAKER`, `WTSWAMR`, `WTSEWR`, `WTLAVAR`, `WTLAKAR` n'avaient pas d'override TIS
lors de la lecture. `WSWPILR` était présent. Une alternative absente ne prouve pas à elle seule
un défaut : il faut savoir si le moteur la sélectionne dans le contexte concerné.

## 7. Anomalies : distinguer cause, preuve et correction

| Symptôme | Cause établie/documentée | Réponse appropriée |
|---|---|---|
| Carrés de luminosité différente | Opacité effective différente entre populations primaire/secondaire | Réparer le contrat commun de composition |
| Ombres/reflets disparus ou eau opaque | Art supprimé ou animation masquée par l'alpha | Restaurer les contributions natives |
| Traits noirs/bleus aux interfaces | RGB contaminé, pixels transparents noirs, marges d'atlas | Corriger RGB/padding ; l'alpha seul peut être sans effet |
| Quadrillage répété | Inférence non périodique ou amplification d'un motif source | Corriger le motif et son contexte avant le shader |
| Rives crénelées | Silhouette x1 ou liseré RGB élargi | Contour continu avec îlots/trous préservés ; distinguer géométrie et RGB |
| Mosaïque sous pluie | Alternative météo omise ou incompatible avec la timeline | Ressources sec/pluie et routage cohérents |
| Mouvement ralenti/incomplet | Nombre, ordre et vitesse des phases désaccordés | Préserver durée et séquence effective |
| Crash après timeline | Insertion sans relocation complète des pointeurs WED | Préserver tables et polygones des portes |
| Teinte intermittente erronée | Mauvaise identification texture côté moteur | Corriger le routage, pas les pixels de la map |

Exemples documentés :

- AR0204/1600 : RGB de maître secondaire donneur ; certaines normalisations alpha n'ont changé
  aucun alpha décodé. Ne pas attribuer la réparation visuelle à l'alpha seul.
- AR1607/1800 sous pluie : WED demandait 36 phases, WTSWAMR stock n'en fournissait que 6 ;
  le hook et l'identification ne couvraient pas correctement la ressource alternative.
- AR0046N : slot de texture interne pris pour nom OpenGL ; problème runtime de teinte.
- AR0900N : changement WED jour/nuit sans renouvellement du CGameArea, cache d'identité périmé.
- Relocation WED : ajout de 60 octets de timeline sans déplacer certains pointeurs de portes.
  AR0204 BRIDGE01 avait zéro polygone : incohérence réelle, pas preuve de crash associé.
- AR0413 : seules les sentinelles noires effectivement visibles devaient être corrigées,
  pas toutes les entrées `page=FFFFFFFF` de la zone.

Sources : [`WATER_REPAIR_RUNBOOK.md`](../WATER_REPAIR_RUNBOOK.md),
[`AR0900_NIGHT_REPAIR_20260912.md`](AR0900_NIGHT_REPAIR_20260912.md),
[`WTSWAM_RAIN_RESOURCE_REPAIR_20260912.md`](WTSWAM_RAIN_RESOURCE_REPAIR_20260912.md),
[`water-tint-engine-slot-resolution`](../../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/water-tint-engine-slot-resolution-20260912.md).

### 7.1 Déduction nouvelle : TIS partagé36 / WED stock6

**Constat des fichiers, sans observation nouvelle en jeu :** WTSEW contient 36 phases,
AR0404 sélectionne 0–35, AR2100 sélectionne encore 0–5. Les ancres d'origine du producteur
WTSEW sont rangées en **0,6,12,18,24,30** ; les indices intermédiaires sont des interpolations.

Conséquence déduite pour AR2100 avec la vitesse stock :

- Seule l'ancre0 puis cinq intermédiaires vers l'ancre1 sont parcourus.
- Le retour 5→0 omet le reste du cycle ; il ne rejoue pas les six poses natives.
- La boucle de lecture conserve sa durée nominale de 2,4 s, mais n'affiche qu'environ le
  premier sixième du contenu prévu ; le mouvement local est ralenti par la tenue des phases.
- La QA historique AR2100 valide cet état observé ; cette analyse ne la révoque pas et
  n'affirme pas une nouvelle panne visuelle.

Même incompatibilité de contrat pour WTSWAM partagé36 avec les WED stock6 suivants :
`AR0310`, `AR0500`, `AR0500N`, `AR1106`, `AR1201`, `AR1100`, `AR1403`, `AR1500`, `AR2500`,
`AR2210`, `AR2600`, `AR2602`, `AR2700`, `AR0604`, `AR3025`, `AR6008`.

**q0 ne restaure pas le vanilla : il utilise la ressource actuellement installée.** L'INI lue
activait effet eau et route2, dosage global0.70 ; une identité non reconnue reste q0 et sa
timeline route2 est désactivée. Ce repli ne corrige pas le couple WED6/TIS36.

Implication de conception : toute modification du nombre/ordre des phases d'un TIS partagé
doit adapter les consommateurs concernés ou utiliser un alias isolé et ses alternatives météo.
Un registre shader par identité ne contient pas les effets d'une modification globale de TIS.

Preuves : `HD/override/WTSEW.TIS`, `HD/override/WTSWAM.TIS`, WED résolus depuis le KEY HD,
[`build_wtsew_route2_pilot.py`](../scripts/build_wtsew_route2_pilot.py) (ancres autour de ligne303),
[`QA WTSEW`](manifests/wtsew-ar0404-ar2100-validated-20260912-v1.json),
[`shader_probe.cpp`](../../engine/InfinityEngine-Enhancer/source-patchee/src/iee/shader_probe.cpp)
(activation temporelle autour de ligne1798).

## 8. Exceptions et qualification restant ouvertes

| Cas | Limite à conserver |
|---|---|
| AR0512 | WTLAKE natif1 image ; WED installé36 ; animation ajoutée, pas simple upscale équivalent |
| AR0512 / AR1604 | Profil intérieur route2 non qualifié ; ne pas extrapoler depuis mer/lac extérieur |
| AR5200/5201/5204 | Lookup lave11 `[0…9,11]` à préserver ; 12 images disponibles ne définissent pas le cycle |
| AR1000/N | Changement de famille entre variantes ; nuit sèche validée, pluie non observée séparément |
| AR0300N | Exception artistique160 appariée assets/runtime ; pas une nouvelle valeur native universelle |
| WTOIL | Acquis du remplacement procédural historique ; migration vers composition native à valider |
| AR2102 / AR3024 | Aliasing eau encore signalé / revue eau-huile différée dans le suivi |
| WT5000A–D | Décors AR5000/5203 x4 acceptés ; overlays stock, eau explicitement hors de cette validation |
| AR6008 | Cellule centrale WTSWAM non réparée ; acceptation décor ne prouve pas traitement eau |
| AR5200 | Réserve sur une portion eau distincte des overlays lave ; resref/cellule à identifier |
| Acide/saumure | Pas de famille chimique démontrée par les noms actifs ; qualifier structure puis matériau |
| Surfaces locales | Trous de décor, eau déjà peinte, occlusion et jointures entre occurrences à distinguer |

Référence des réserves : [`PROBLEMES_A_RESOUDRE.md`](../PROBLEMES_A_RESOUDRE.md) et
[`areas.csv`](../../areas.csv). Aucune de ces entrées n'a été corrigée ou clôturée par l'analyse.

### 8.1 États et politiques contradictoires

- Lave : `overlay-sources.json` sélectionne le package x4, mais les classificateurs historiques
  la considèrent encore parfois stock. La qualification route2/périodicité reste distincte.
- WTSWAM / WTSEW : politique release stock ; installation inspectée avec TIS partagés x4/36.
  Ne pas confondre contenu du disque, politique de livraison et recette validée.
- AR0900 jour : recette historique acquise ; sélection courante du suivi encore pending après
  relocation WED. Une correction du contrat runtime peut nécessiter une nouvelle QA de portée.
- AR2300 : décor/performance et raccord FALL6 ont été acceptés ; cela ne ferme pas automatiquement
  la QA d'une sélection eau/WED ultérieure. Ne pas annoncer un crash actuel depuis un ancien run.
- Les audits/builders legacy conservent des recommandations alpha0, des listes stock codées
  en dur et une classification incomplète WT5000 ; leur généralisation automatique est incorrecte.

Sources : [`family-policy-v1.json`](family-policy-v1.json),
[`release-tracking-v1.json`](release-tracking-v1.json),
[`overlay-sources.json`](../../releases/BG2-HD-Upscale/manifests/overlay-sources.json),
[`audit_water_area.py`](../scripts/audit_water_area.py),
[`build_upscaled_area.py`](../scripts/build_upscaled_area.py).

### 8.2 Limites du moteur HD actuel

- Deux contrats différents : ancien shader remplissant les trous alpha/supprimant une
  contribution secondaire, versus route2 enrichissant la sous-couche native identifiée.
  « Voie1 » désigne aussi des réparations d'assets dans certains documents : préciser le sens.
- Route2 couvre eau/égout/marais ; pas une recette généralisée lave/goo/huile.
- Timeline actuelle : atlas uniforme, une page, ensemble de phases d'un cycle ; elle ne
  représente pas toutes les séquences/spatialités WED. Ne pas y projeter directement tous les A–D.
- Fluidification couplée à q>0 ; à séparer du dosage procédural dans une architecture modulaire.
- Horloge réelle globale ; pause du jeu et phases natives à qualifier avant généralisation.
- Teinte moyenne par zone et représentation de matériau par cellule : limites pour des
  matériaux distincts dans une même zone comme AR1100. Aucune superposition multibit liquide
  n'a cependant été observée dans les cellules vanilla parcourues.
- Registre source, registre compilé et DLL installée sont des états différents.

Sources : [`fpSEAM.glsl`](../../engine/InfinityEngine-Enhancer/source-patchee/assets/override/fpSEAM.glsl),
[`generate_water_route2_registry.py`](../../engine/InfinityEngine-Enhancer/source-patchee/tools/generate_water_route2_registry.py),
[`area_state.cpp`](../../engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_state.cpp),
[`frame_hook.cpp`](../../engine/InfinityEngine-Enhancer/source-patchee/src/iee/frame_hook.cpp).

## 9. Architecture recommandée — proposition, non implémentée

Les opérations suivantes sont des modules de conception, pas des étapes imposées à toute tâche.

### 9.1 Graphe des dépendances et classification structurelle

```text
ARE → variante WED → cellules/rôles → séquences TIS → pages
                        ↘ ressources météo réellement utilisées
ARE → occurrences constitutives → BAM/cycles/positions/flags → raccords avec la map
```

- Distinguer déclaration et usage ; identifier les consommateurs d'une ressource partagée.
- Déduire la topologie avant le matériau ; ne pas router seulement par préfixe WT*/YS*.
- Conserver une identité par variante, slot et ressource effectivement utilisée.

### 9.2 Contrat de composition explicite

- Données : art local, masques, opacité effective, ordre des contributions, format source,
  secondaires, sentinelles et réemplois de tuiles.
- Référence commune : résultat natif ; aucun alpha0/128/255 imposé globalement.
- Garder l'ancien remplacement procédural comme contrat distinct lorsqu'il est déjà acquis.
- Préserver les références RGB nocturnes et les décisions artistiques limitées à une identité.

### 9.3 RGB et contours en continuité spatiale

- Reconstituer les couches avec leurs voisins corrects ; traiter RGB et masques séparément.
- Recouper en tuiles après traitement ; marges et RGB transparents doivent correspondre au filtrage.
- Réutiliser les donneurs compatibles, notamment secondaire de même variante.
- Travailler la géométrie sur canvas complet ; conserver îlots/trous ; refuser ou dédoubler
  explicitement un usage partagé lorsqu'un même index exigerait deux résultats différents.

Contours d'objets devant l'eau : procédé validé [CONTOUR_MATTE_PIPELINE.md](CONTOUR_MATTE_PIPELINE.md)
(silhouette RGB x4, pas de vectorisation du masque x1 pour les éléments fins).

Chaîne standard implémentée (plans + orchestration, producteurs inchangés) : [SPATIAL_X4_PIPELINE.md](SPATIAL_X4_PIPELINE.md).

### 9.4 Traitement périodique adapté à la topologie

- Motif unique : contexte 3 × 3/crop central comme opérateur déjà éprouvé.
- Groupe A–D : contraintes entre motifs tirées des voisinages WED ; supermotif seulement
  lorsque la disposition est établie ; mêmes relations temporelles aux raccords.
- Deux modes disponibles : non génératif et génératif ; choix selon la texture et les résultats,
  pas une obligation d'IA ni un choix fondé uniquement sur lac/piscine.

### 9.5 Temporalité indépendante

Recette validée (AR1600) et application par famille : [TEMPORAL_30FPS_PIPELINE.md](TEMPORAL_30FPS_PIPELINE.md).
Les points ci-dessous restent les contraintes de conception.


- Préserver ordre exact, durée, maintiens, phase et fermeture de boucle.
- Distinguer interpolation temporelle, amélioration spatiale et matériau procédural.
- Ne pas imposer 6→36 aux ressources de 1, 8, 11 ou 12 images.
- Couvrir les alternatives météo réellement utilisées.
- ~~Privilégier une interpolation runtime conservant le contrat WED~~ : tranché par AR1600 v2 —
  phases réelles stockées (WED réécrit, durée conservée), demi-fondu shader rejeté (flou/pulsation).
- Si modification WED nécessaire : préserver géométrie/portes/pointeurs, pas seulement la lookup.

### 9.6 Isolation des changements partagés

- Changement nombre/ordre des phases : adapter tous les consommateurs concernés ou utiliser
  un alias isolé avec ses variantes nécessaires.
- Garder une référence native exploitable ; q0 ne suffit pas à la restaurer si les fichiers
  partagés ont changé.
- Les alias ne sont pas des recettes différentes par map : ils bornent la portée d'un contrat.

### 9.7 Matériaux et exceptions déclaratifs

- Infrastructure commune ; paramètres par profil : couleur, réflexion, opacité, mouvement,
  émission et environnement.
- Eau claire / eau trouble-égout / liquide visqueux / lave émissive : base de profils à qualifier.
- Ne pas propager un matériau eau ou son mélange alpha aux liquides émissifs.
- Exceptions admises lorsqu'établies : opacité artistique, raccord de cascade, sentinelle visible,
  réemploi ambigu, séquence atypique, comportement de variante.
- Préférer des paramètres et une portée explicite aux branches codées par numéro de map.

## 10. Base de travail jusqu'à validation définitive

**État initial de cette phase : conception uniquement ; aucun témoin sélectionné définitivement,
aucun nouvel essai exécuté.** L'utilisateur prévoit de sélectionner ensuite quelques maps.

### 10.1 Témoins proposés, à sélectionner

| Groupe / risque | Maps proposées | Décision que les futurs essais pourront éclairer |
|---|---|---|
| Motif unique, grandes étendues, art local | AR0900 ou AR1600 | Préservation native, raccords, répétition et animation |
| Bassins jour/nuit | AR1000 / AR1000N | Non génératif vs génératif ; changement de famille ; secondaires |
| Marais et météo | AR1607 / AR1800 | Opacité100/128 ; sous-couches sèches/pluie ; mêmes raccords |
| Ressource partagée, contrats temporels différents | AR0404 / AR2100 | Isolation ou adaptation des consommateurs WTSEW |
| Pavage turquoise | AR3000 / AR6300 | Assemblage A–D, opacité et dispositions différentes |
| Rivière brune | AR5000 / AR5203 | Classification, périodicité entre motifs, courant et composition HD |
| Lave | AR0011 / AR5200 | Matériau émissif ; lookup12 vs11 ; ne pas confondre réserve eau AR5200 |
| Liquide visqueux, acquis ancien | AR0413 | Préserver le résultat acquis ou qualifier une migration de contrat |
| Surface locale composée | AR2804 ou AR3021 | Jointures entre occurrences et décor ; occlusion/alpha |

### 10.2 Questions de validation, selon le risque du témoin

- La contribution du décor est-elle conservée : ombres/reflets/rives et opacité effective ?
- Raccords internes, vrai contour et marges d'atlas sont-ils cohérents au grossissement utile ?
- Motifs et transitions A–D restent-ils continus spatialement et temporellement ?
- Cycle complet, durée, maintiens, fermeture, pause/reprise correspondent-ils au contrat retenu ?
- Variantes concernées (jour/nuit/pluie) utilisent-elles les ressources prévues ?
- Les autres consommateurs partagés conservent-ils leur contrat ?
- La solution réemploie-t-elle les mêmes opérateurs, ou révèle-t-elle une exception technique réelle ?

Ce sont des critères de décision pour les futurs essais, **pas une batterie exécutée ni une
checklist obligatoire pour chaque asset**. Choisir les observations nécessaires au problème réel.

### 10.3 Enregistrement des résultats futurs

- Conserver les preuves historiques/QA immuables ; créer une nouvelle décision lorsqu'un nouveau
  résultat change les octets ou le contrat runtime concerné.
- Documenter seulement les choix utiles : identité et version, recette/paramètres, résultat,
  limites, décision, éventuelle exception, autorité de QA correspondante.
- Mettre à jour les index de domaine concernés lorsqu'une décision finale le nécessite ;
  ce guide reste une synthèse de conception, pas un registre global réconciliant les états.
- Une recette de famille devient définitive pour un **contrat et une portée qualifiés**,
  pas pour toutes les maps ayant une couleur ou un nom similaire.
- L'intégration release reste une action distincte, explicitement demandée ; validation du
  pipeline n'autorise pas implicitement payload, staging, content.json, TP2 ou archive.
- Jusqu'à la prochaine sélection utilisateur : aucune implémentation, aucun test, aucune installation.

## 11. Références de reprise ciblée

| Besoin | Source |
|---|---|
| Doctrine du dépôt | [`PRODUCTION_RAPIDE.md`](../../docs/PRODUCTION_RAPIDE.md) |
| Recettes acquises | [`VALIDATED_WATER_RECIPES.md`](VALIDATED_WATER_RECIPES.md) |
| Composition et réparations TIS/PVRZ/WED | [`WATER_REPAIR_RUNBOOK.md`](../WATER_REPAIR_RUNBOOK.md) |
| Mouvement/runtime | [`WATER_ROUTE2_EXPERIMENT_RUNBOOK.md`](../WATER_ROUTE2_EXPERIMENT_RUNBOOK.md) |
| Liquides non standards | [`OTHER_LIQUID_MAP_PIPELINE.md`](../OTHER_LIQUID_MAP_PIPELINE.md) |
| Contours continus | [`SPLINE_ALPHA_MASK_PIPELINE.md`](../SPLINE_ALPHA_MASK_PIPELINE.md) |
| Masques et géométrie | [`GEOMETRIC_ALPHA_MASK_CLEANUP.md`](../GEOMETRIC_ALPHA_MASK_CLEANUP.md) |
| Réserves ouvertes | [`PROBLEMES_A_RESOUDRE.md`](../PROBLEMES_A_RESOUDRE.md) |
| Matrice historique déclarative67/98 | [`liquid-target-matrix-v1.json`](manifests/liquid-target-matrix-v1.json) |
| QA / sélections eau | [`WATER_RELEASE_TRACKING.md`](WATER_RELEASE_TRACKING.md) |

Lire uniquement les sections liées au symptôme ou à la décision en cours. Les recettes,
manifestes et sources ci-dessus sont des aides ; leurs divergences documentées restent à
résoudre dans la portée d'une tâche autorisée, pas par une migration implicite.
