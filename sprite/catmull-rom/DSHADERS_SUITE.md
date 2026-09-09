# Suite Dshaders complète — contrat de développement D2–D13

Complément obligatoire du [guide principal](README.md). Révision : 2026-09-09.
Autorisation : étendre le plan à toutes les options pour les tester ingame avant choix du patch.
Ce document spécifie le travail restant ; aucune installation ni validation nouvelle n'en découle.

## 1. Livrable et acquis

- Cible : BG2EE Steam 2.7.3.0 Windows x64, OpenGL, InfinityEngine Enhancer.
- Livrable D11 : DLL + INI fusionné + huit shaders intégrés + profils reproductibles + notices.
  Toutes les fonctions ci-dessous doivent être implémentées et disponibles à l'essai, y compris
  celles désactivées dans le futur profil retenu. D12 ajoute le mode optimisé.
- Portées exigées : créatures HD seules ; sprites au sens Dshaders ; ensemble des huit shaders ;
  réglages indépendants par shader. Les presets doivent combiner des portées différentes par effet.
- Socle conservé : D0 `5e68244f447f942396ac189391c5ad7baee386e9`, D1
  `843aa3844dda97d212706b896a100f5ac3ad5a9e`. Aucun nouveau besoin ne rouvre ces lots.
- D1 conserve `CreatureSpriteFilter=Nearest|Linear|CatmullRom`, sa priorité sur la clé legacy,
  `configure_filter_mode`, les poids CPU et `reconstruct_premultiplied`, epsilon `1e-6`.
  Ajouter modules/configuration/tests ; ne pas changer ces sémantiques ni réécrire leurs preuves.
- L'intégration utilise du code source attribué/adapté ; ne pas lancer `setup-drunkshaders.exe`
  sur le jeu du patch. Il remplacerait aussi le `fpSEAM` IEE.
- Garder tous les réglages disponibles après la QA ; sélectionner séparément les valeurs par défaut
  du patch. Une fonction non observée reste `pending-qa`, jamais « sans effet donc validée ».

## 2. Sources vérifiées et écarts à prendre en compte

Révision amont `4722673a8017c56ace4018b3db459392ecbb75a4` = HEAD `main` observé le 2026-09-09,
version 0.3.5. Conserver cet épinglage ; relire les sources avant le lot qui les adapte.

| Référence | Usage |
|---|---|
| [TP2](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/drunkshaders/drunkshaders.tp2) | Composants, presets, valeurs réellement installées et ordre des corrections. |
| [glsl-parts](https://github.com/dtiefling/dshaders/tree/4722673a8017c56ace4018b3db459392ecbb75a4/drunkshaders/glsl-parts) | Trois `header-*.glsl`, huit `flags-*.glsl`, deux fichiers de fonctions. |
| [functions-game.glsl](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/drunkshaders/glsl-parts/functions-game.glsl) | Interpolation, Gaussian, contours, couleurs, heuristiques et sélections. |
| [functions-movies.glsl](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/drunkshaders/glsl-parts/functions-movies.glsl) | Plans YUV, filtrage et colorimétrie vidéo. |
| [README / preview](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/README.md) | Intention visuelle ; ne remplace pas les valeurs du TP2. |
| [Licence Dshaders](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/LICENSE) ; [licence optimizer](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/drunkshaders/tools/glslopt/license.txt) | Notices MIT distinctes ; conserver copyrights et licences si repris/distribués. |

Constats de lecture, pas des défauts ingame affirmés :

| Constat vérifié | Conséquence pour le port |
|---|---|
| TP2 : contour de base `fpSprite=2.0`, `fpSELECT=3.5` ; sélection amincie `2.5`. README : normal `1.5`. | Utiliser `2.0/3.5` pour le preset amont ; `1.5` reste une valeur testable, pas le défaut installé. |
| `functions-game` court-circuite les contours à `<=0.70710678`, contrairement aux seuils décrits dans le README. | Définir absence par `0`, valider les petites tailles depuis l'algorithme ; ne pas convertir les conseils README en bornes de parsing. |
| TP2 : couleurs globales modérées/intenses donnent `uhGamma=1.632` aux deux YUV, `1.02` aux six autres ; correction font ensuite `0.8`. | Profils par shader, ordre explicite ; aucun multiplicateur gamma uniforme « all ». |
| `uhFetchRegion` initialise `idx=0` puis écrit `uhRegion[++idx]` pour `UH_REG_SIZE` entrées. | Corriger l'indexation lors du port : intervalle `0..N-1`, aucune entrée non initialisée. Ne pas copier ce code aveuglément. |
| Un bloc utilise `#if NEEDS_HEURISTIC_BORDER`, alors que les flags définissent `UH_NEEDS_HEURISTIC_BORDER`. | D8 doit spécifier/tester les branches actives et l'effet exact du toggle ; consigner la correction du nom si ce bloc est activé. |
| Couleurs : `pow(color,gamma)` peut recevoir des valeurs négatives après contraste/teinte ; contour : division par alpha combiné. | Borner le domaine avant `pow`, protéger alpha nul ; préserver le contrôle `alpha==0` de D1. |
| Amont emploie `texelFetch`, des tableaux/constructeurs et des offsets `UVTC_SHIFT` propres aux shaders. | Adapter au préambule réellement lié ; D5 garde `floor(q)` et centres physiques D1. Ne pas recopier les offsets sans trace. |
| Conversion linéaire amont utilise des seuils légèrement différents du sRGB usuel. | Documenter la conversion choisie ; équivalence de fonctions/paramètres ne signifie pas identité bit à bit au mod 2.6. |

Sources supplémentaires 2.7.3 lues hors jeu, BIF `data/Shaders.bif`, type `0x0405` :

| Ressource | SHA-256 des octets bruts |
|---|---|
| FPFONT | `06b5bd912d8a3397ca01d6a9eb0f4894706f9b3e94b6f3f3117008bb6a2cefa9` |
| FPTONE | `7477cffe8ad49c4cec44278621064412d314b4648892d04adebb7dbd1aa31fd4` |
| FPSEAM | `fd36694661d419502f445d36ab7aaf5ba286feb029a95d67e6f3f10514141083` |
| FPYUV | `9f6e93abd53a29314416d00cff84bbc0e85b6561eefe53fda0fa8fd36b668dbd` |
| FPYUVGRY | `9aed2cbd57608d95cf033a37beeef580262f2e804e007d3425c4fa03e53bf863` |
| VPYUV | `6b2e8966ee75ae9a14b390cc4a75be766eefc3c51ec479630df2edb4ddaceb5e` |

Extraction D2 : reprendre la commande du guide, remplacer `wanted` par ces ressources et archiver
dans un nouveau run. `D0/evidence.json` et ses six extractions restent inchangés.

## 3. Couverture amont obligatoire

### 3.1 Composants installables

IDs = `DESIGNATED` du TP2, pas des IDs de release BG2HD. Chaque ligne doit avoir son implémentation,
son contrôle de configuration et son essai ingame. Choix exclusifs : tous disponibles, un seul actif.

| IDs amont | Fonction et variantes | Livraison |
|---|---|---|
| 1000 | Base de rendu cohérente, opérations couleur en linéaire, contours réimplémentés, paramètres éditables. | D6–D10 |
| 1105 / 1125 | Catmull–Rom sprites / huit shaders. | D5/D7–D10 |
| 1205 / 1215 / 1225 | Contour normal supprimé ; normal supprimé + sélection `2.5` ; tous contours supprimés. | D6/D7 |
| 1304 / 1314 | Couleurs modérées sprites / huit shaders : gamma `1.02`, contraste `1.1`, bright `0.05` ; YUV gamma `1.632` en global. | D6–D10 |
| 1305 / 1315 | Couleurs intenses sprites / huit shaders : gamma `1.02`, contraste `1.2`, bright `0.1` ; YUV gamma `1.632` en global. | D6–D10 |
| 1405 / 1415 / 1425 / 1435 | Sharpen `+0.25` / `+0.50`, chacun sprites / huit shaders. | D6–D10 |
| 1445 / 1455 / 1465 / 1475 | Blur `-0.25` / `-0.50`, chacun sprites / huit shaders. | D6–D10 |
| 1505 / 1515 | Gamma `fpFONT=0.8` ; même réglage + hack couleur `fpDraw=0.8` pour UI compatibles. | D8 |
| 1605 / 1615 / 1625 / 1635 | Teinte `+3°` / `+5°`, chacun sprites / huit shaders. | D6–D10 |
| 1645 / 1655 / 1665 / 1675 | Teinte `-3°` / `-5°`, chacun sprites / huit shaders. | D6–D10 |
| 1705 | Gamma sélection `2.0` dans `fpDraw` et `fpTone` : cercles et objets surlignés. | D8 |
| 1805 | Désactivation expérimentale de l'anti-glitch dans `fpDraw` et `fpTone`. | D8 |
| 9005 | Optimisation offline des shaders pour les paramètres retenus, désactivable/réversible. | D12 |
| QUICK_MENU | Les dix ensembles de composants de §3.3. | D11 |
| Réglages manuels | Paramètres continus, notamment saturation non proposée comme composant TP2. | D6–D11 |

### 3.2 Paramètres exposés

Noms IEE ci-dessous proposés pour D2 ; figer ensuite dans un schéma unique. Les noms amont sont
des constantes shader : les transformer en paramètres typés, pas en chaînes injectées dans GLSL.
Défaut suite inactive ; les valeurs ci-dessous décrivent une configuration activée neutre/amont.

| Amont → IEE | Défaut / cas de comparaison | Portée et validation |
|---|---|---|
| `uhCatmullRom` → `Filter` | `Native` / `CatmullRom` | Par shader hors HD ; pour HD, utiliser exclusivement `CreatureSpriteFilter` D1. |
| `uhSharpen` → `Sharpen` | `0`, `±0.25`, `±0.50`, `-1` | RGB uniquement ; `-1` remplace RGB par moyenne gaussienne, alpha conservé. |
| `uhGamma` → `Gamma` | `1`, `1.02`, `0.8` font, `1.632` YUV presets | Exposant strictement positif, jamais gamma sur alpha hors effet sélection explicite. |
| `uhContrast` → `Contrast` | `1`, `1.1`, `1.2` | Multiplicateur non négatif. |
| `uhBright` → `Brightness` | `0`, `0.05`, `0.1` | Offset, pas un pourcentage de pixels ; permettre valeurs négatives. |
| `uhSat` → `Saturation` | `1`, `0.8`, `1.2`, `0` diagnostic gris | Multiplicateur non négatif. |
| `uhHueDeg` → `HueDegrees` | `0`, `±3`, `±5` | Rotation YIQ selon matrice amont ; permettre un cycle complet. |
| `uhOutlineSize` → `OutlineSize` | Normal `2`, sélection `3.5`, fin `2.5`, absent `0` | `fpSprite`/`fpSELECT`, réglages distincts ; `OutlineMode=Native|Dshaders`, défaut Native IEE. |
| `uhFontHackGamma` → `FontHackGamma` | `0` off, `0.8` | `fpDraw` et `fpTone` manuellement ; le composant 1515 ne change que `fpDraw`. |
| `uhSelectionGamma` → `SelectionGamma` | `1`, `2` | `fpDraw`/`fpTone`, détection de sélection équivalente à `uhProbableCircle`. |
| `UH_NEEDS_HEURISTIC_BORDER` → `HeuristicBorder` | `true` dans chemin suite Draw/Tone ; toggle `false` | Ne retire ni clamp mémoire ni limites de texture ; ne modifie pas les masques WED. |

Ajouts IEE nécessaires : `Enabled` par profil/shader et `ColorSpace=Stored|SRGBLinear`.
`Stored` maintient le témoin D1 ; les presets Dshaders activent la voie linéaire adaptée.
Un réglage couleur n'active pas automatiquement Catmull–Rom ; sharpen, contours et gamma doivent
aussi fonctionner avec le sampler natif. Toutes valeurs doivent être finies. Définir en D2 les
bornes numériques documentées, couvrant au minimum tous les cas ci-dessus ; valeur invalide
diagnostiquée avec repli neutre, jamais clamp silencieux d'un preset amont valide.
La plage sharpen `0.6..2.4` du README est incompatible avec ses propres exemples : ne pas l'utiliser.

### 3.3 Dix presets à reproduire

| Preset | Composants TP2 dans leur ordre |
|---|---|
| Templates | `1000` |
| BGEE13All | `1000 1125 1225` |
| BGEE13Sprites | `1000 1105 1225` |
| Intense | `1000 1315 1415 1505` |
| IntenseBGEE13 | `1000 1125 1225 1315 1415 1505` |
| Moderate | `1000 1314 1415 1505` |
| ModerateBGEE13 | `1000 1125 1225 1314 1415 1505` |
| AuthorChoice | `1000 1125 1215 1314 1415 1505` |
| AuthorChoiceInfinityUI | `1000 1125 1215 1314 1415 1515` |
| Parys | `1000 1125 1225 1705 1805` |

Résoudre ces composants à partir des valeurs de §3.1, shader par shader. Chaque preset part d'un
état propre `1000`, pas du dernier INI utilisé. Le preset polices appliqué après la couleur remplace
le gamma `fpFONT`, il ne le multiplie pas. `Templates` signifie base Dshaders active, pas rendu natif.
Un composant « sprites only » ne désactive pas le composant de base sur les six autres shaders.
Ajouter séparément les témoins IEE `BaselineNearest`, `BaselineLinear`, `CatmullOnlyHD` et un profil
`Custom`. L'optimizer 9005 reste un choix indépendant de chacun des dix presets.

## 4. Architecture additive

### 4.1 Configuration et priorité

Configuration au démarrage ; changement de profil par candidat INI et redémarrage. Hot-reload non
requis. Toutes les valeurs résolues sont lisibles/exportables pour comparer les captures.

Contrat à figer en D2 :

```ini
[Shaders]
CreatureSpriteFilter = Nearest

[ShaderSuite]
Enabled = false

[ShaderSuite.CreatureHD]
Enabled = false
ColorSpace = Stored
Sharpen = 0
Gamma = 1
Contrast = 1
Brightness = 0
Saturation = 1
HueDegrees = 0
OutlineMode = Native
OutlineSize = 2
SelectedOutlineSize = 3.5

[ShaderSuite.fpSprite]
Enabled = false
Filter = Native
ColorSpace = SRGBLinear
OutlineMode = Dshaders
OutlineSize = 2
```

Créer les blocs homologues pour les sept autres shaders, seulement avec leurs paramètres utiles.
Le générateur de profils matérialise toutes les valeurs ; le runtime n'interprète pas les presets.

Priorité effective, en un seul passage :

1. Suite inactive : conserver le chemin D1/D5 et les modules IEE historiques.
2. Texture propriétaire HD : filtre exclusivement décidé par D1 ; style `CreatureHD` si activé,
   sinon style du shader courant si activé, sinon style natif. Un profil `CreatureHD` actif gagne
   en bloc ; ne pas empiler les corrections globales et HD.
3. Dessin non HD : profil explicite du shader lié ; profil inactif => natif/IEE historique.
4. Programme/contexte non reconnu : aucune activation implicite, diagnostic de capacité.

Les presets « CR all » et « CR sprites » écrivent aussi `CreatureSpriteFilter=CatmullRom` pour
inclure les HD sans changer la priorité D1. Sans CR, matérialiser un choix HD explicite de référence
et le consigner ; le sampler amont non-CR n'est pas assimilable automatiquement à notre NEAREST.
Un master suite désactivé ne désactive pas un CatmullRom D1 explicitement demandé.

La sélection de portée est une expansion en blocs INI, pas un unique scope global bloquant les
combinaisons. `Sprites` = `fpSprite` + `fpSELECT`, donc aussi x1 et objets au sol.
`All` = les huit shaders listés, y compris polices/vidéos. `CreatureHD` seul utilise la provenance.
Une classification par shader ne prétend pas séparer UI/effets partageant `fpDraw`.

### 4.2 Interfaces GPU et neutralité

- Conserver la clé de texture `(contexte, nom GL, génération)` et la frontière draw du guide.
- Métadonnées supplémentaires selon shader : dimensions physiques, rectangle source/atlas,
  échelle logique/physique, disposition YUV et interprétation alpha/couverture.
- Étendre le cache des programmes à une table de capacités : uniforms actifs, types, samplers,
  version de contrat et masque des fonctions. La sonde connaît déjà les slots des huit fragments.
- Séparer uniforms dynamiques du draw et paramètres de profil stables ; aucune dépendance aux
  logs ou à `uIeeEnabled` eau. Les uniforms « active » valent zéro sans initialisation.
- La voie suite inactive doit rendre les octets/opérations du chemin natif ou IEE antérieur,
  même si des presets compilés existent. Paramètres égaux à `1/0` dans une voie linéaire active
  ne suffisent pas à prouver cette neutralité.
- Ne pas changer globalement le sampler des textures moteur partagées. Lectures aux centres et
  bounds prouvés ; `texelFetch` seulement si le préambule le permet, sinon `texture2D` adaptée.
- Ne pas passer toutes les textures dans le reconstructeur RGBA D1 : font = couverture rouge,
  vidéo = plans YUV et parfois alpha séparé, certains effets = blending particulier.
- Pour chaque source non privée, contrôler l'encodage, les bornes et le blend en D2/D8–D10.
  Catmull–Rom n'invente ni voisin hors tuile ni pixels adjacents absents de l'atlas.

### 4.3 Calculs et contours D6

- Réutiliser les poids D1 ; nouvelle référence CPU séparée pour Gaussian, contours et couleurs.
- CR et Gaussian partagent le voisinage 4×4 ; sigma amont `2.5`, poids normalisés selon phase.
  Effet RGB : `(1+s)*C - s*G`, `s=Sharpen`. L'alpha reconstruit reste inchangé par cet effet.
- Pour le HD transparent : `C` issu de D1, `G = somme(gk*ak*ck)/somme(gk*ak)` si dénominateur
  supérieur à epsilon, sinon RGB nul. Neutraliser RGB sous alpha nul ; ne pas accentuer l'alpha
  par la formule RGB. Cette adaptation évite de réintroduire du RGB caché dans D1.
- Pipeline à spécifier/tester : décodage espace couleur → reconstruction → sharpen/heuristiques →
  modulation native/contour → teinte YIQ → saturation → tone natif si présent → contraste/bright →
  gamma RGB → conversion de sortie. Ne pas appliquer deux fois `vColor`, `uColorTone` ou le gamma.
- Pour l'interpolation linéaire, conversion RGB avant prémultiplication ; aucune conversion gamma
  sur alpha. Déclarer domaine intermédiaire et état `FRAMEBUFFER_SRGB`, conversion de sortie unique.
- Reprendre les contours normal noir / sélection `vColor.rgb`, sans changer les couleurs d'équipe.
  Épaisseur en pixels logiques, stable entre x1/x2/x4 ; convertir rayon/support en texels physiques.
  Tester les crops avec la géométrie existante. Le 4×4 CR ne couvre pas à lui seul tout contour.
- Le contour amont utilise un voisinage 6×6 et une estimation de distance ; développer séparément
  du CR 16 lectures. `OutlineMode=Native` préserve les opérations 2.7.3, `Dshaders` active l'alternative.
- Conserver les états flou/invisibilité/sélection observés ; `uSpriteBlurAmount` est déclaré mais
  non utilisé dans les fonctions amont consultées. Ne pas supprimer un comportement moteur prouvé.

### 4.4 Shaders partagés et polices D8

- `fpDraw` : UI, sorts, objets animés et sélections ; `fpTone` : voie avec teinte/pause correspondante.
  Traiter chacun selon son interface 2.7.3, pas selon son nom seulement.
- `fpFONT` natif utilise `texture.r` comme couverture et `vColor` comme couleur/alpha. Filtrer cette
  couverture, vérifier l'effet réel du paramètre gamma sur le texte et le blend final.
- `FontHackGamma` est une heuristique de couleur, pas une identification certaine du texte.
  Conserver l'option et tester chiffres d'inventaire, survol/fade, couleurs ressemblantes non textuelles.
  Ne pas installer une UI tierce pour déclarer un succès ; compatibilité spécifique non observée
  consignée séparément. Les contrôles synthétiques ne valent pas QA de cette UI.
- `SelectionGamma` : identifier la couverture des cercles et surlignages indépendants. Ce réglage
  n'est ni `fpSELECT` ni l'alpha général de tous les sprites. Tester objets non identifiés encore bleus.
- `HeuristicBorder` : exposer on/off et mesurer coutures/faux positifs sur scènes identiques.
  Conserver la voie originale sans heuristique quand suite inactive ; sécuriser les lectures même off.

### 4.5 Fusion `fpSEAM` D9

Source locale : `ENGINE/assets/override/fpSEAM.glsl`, fonctions `seamSample` et `main`.

- Une seule source finale et une seule transaction propriétaire de `override/fpSEAM.glsl`.
- Conserver masque WED, tint auteur, normal/DuDv/foam, modes de liquide, `alphaScale`, F10 et mode
  diagnostic. Les unités eau existantes `2..5` restent réservées ; allouer les autres explicitement.
- Suite off : sortie IEE antérieure. Suite on/eau off : fonctions globales appliquées à la carte.
  Suite on/eau on : reconstruction du matériau + eau existante + colorimétrie finale appliquée une fois.
  Le diagnostic de masque garde ses couleurs de diagnostic sans color grading.
- `seamSample` raisonne en tuiles logiques de 64 px ; Dshaders utilise `vRef` et `tileStart+63`.
  Pour un atlas HD, dériver les bornes physiques et l'échelle depuis le rendu constaté. Ne pas
  recopier `+63` dans une texture x4 ni supposer que `uTcScale` est l'inverse du stockage.
- Protéger alpha de rive et passes WATER_ALPHA ; les effets ne doivent pas filtrer les textures
  techniques de masques/normales comme s'il s'agissait de couleurs affichées.
- Vérifier quatre états suite/eau on/off, terres, raccords, berges, palette jour/nuit et transition
  vers zone sans eau. Une modification du shader partagé exige une QA des cartes, pas seulement sprites.

### 4.6 YUV et YUVGRY D10

- Sources natives relues : `fpYUV` échantillonne Y/U/V dans `uTex` puis module par `vColor` ;
  `vpYUV` construit trois coordonnées, chroma partagé sur la partie basse de la texture.
- `fpYUVGRY` natif a `uTex2` alpha séparé, coordonnée alpha `vTc.y/(2/3)`, wrapping Y et UV distinct
  et `uColorTone`. Préserver ces contrats ; l'amont lit l'alpha différemment.
- Établir les rectangles Y/U/V et phases chroma depuis les dimensions/captures, pas depuis les
  seules dimensions de la fenêtre. Borner chaque plan indépendamment, y compris U contre V.
- Porter CR, sharpen et les cinq réglages couleur sur ces chemins ; garder l'alpha et les états
  gris natifs. Chaque échantillon RGB YUV peut coûter trois lectures ; mesurer le coût réel.
- Les deux gamma vidéo `1.632` des presets sont des valeurs amont à comparer, pas une règle de
  décodage YUV universelle. Documenter conversion et éventuels écarts de rendu avant sélection.
- Prévoir séquence vidéo et élément animé YUV avec alpha/wrapping pour QA ; si aucun cas GRY n'est
  accessible, conserver la ligne non qualifiée et préparer une scène de test ciblée sans changer les
  sauvegardes utilisateur. Une compilation seule ne clôture pas sa validation ingame.

## 5. Installation, profils et optimisation

- Réutiliser les deux transactions décrites dans le guide : renderer DLL/INI et liste shader exacte.
  Installer les huit fragments neutres dès D3 ; enrichir leurs opérations progressivement jusqu’au
  candidat complet D11.
- Chaque profil produit un nouvel INI fusionné, un identifiant et des hashes. Les huit shaders de
  travail restent paramétrables ; une variation numérique ne nécessite pas une recompilation C++.
- Outil de profils plan-only par défaut : liste/diff des valeurs et fichiers avant `--run`.
  Ne pas éditer l'INI live après installation : nouveau candidat/reçu pour chaque A/B, jeu fermé.
  Ne pas empiler indéfiniment les transactions ; restaurer un candidat avant le suivant.
- Vérifier `fpSEAM` live par rapport à une source IEE connue avant fusion. En cas de différence,
  inventorier l'origine ; ne pas restaurer le shader vanilla à la place d'un shader IEE préexistant.
- Baseline catalogue D11 : `CreatureSpriteFilter=Nearest` et suite inactive ; versionner les nouveaux
  reçus/contrats, préserver la lecture des reçus anciens et les travaux D1.
- Candidat final : tous paramètres exposés, même si leur valeur retenue est neutre. Le jeu ne doit
  dépendre ni d'une copie de Dshaders installée ni d'un accès réseau pour rendre les scènes.

Option D12 `9005` :

1. Prévoir un générateur offline reproductible des fragments autonomes, depuis sources révisables
   et profil résolu. Conserver sources non optimisées et profil même après spécialisation.
2. Spécialiser uniquement les constantes de profil, jamais la provenance HD, taille de texture,
   contexte, masque de capacité ou master runtime. Les gates de sécurité restent actives.
3. Épingler source/version ou hash du binaire `glslopt` choisi, licence et arguments. Le TP2 utilise
   `-1 -f` et un préambule temporaire `#version 130` ; vérifier ces conventions avec les dumps 2.7.3.
   Ne jamais ajouter ce préambule au fichier override livré sans justification du contrat moteur.
4. Comparer compilations et sorties GPU avant/après optimisation pour chaque shader/profil testé ;
   tester aussi suite inactive et absence de DLL. Un uniforme éliminé légitimement est décrit par
   le manifeste de capacités, pas interprété comme une corruption générique.
5. Changer un profil spécialisé exige régénération/réoptimisation des shaders et nouveau reçu.
   Présenter ce besoin dans le diff du candidat ; ne jamais prétendre qu'un INI modifié agit sur
   une constante déjà figée. Le profil général non optimisé reste installable.

L'option d'optimisation fait partie du livrable ; son activation release dépend des mesures.
Si l'outil amont ne supporte pas les shaders adaptés, consigner le blocage et développer une voie
équivalente vérifiée ; ne pas omettre silencieusement 9005.

## 6. Fichiers et livrables

Chemins relatifs à `ENGINE`, sauf `FEATURE`. Nouveaux chemins = propositions D2, à créer au lot utile.

| Chemin | Travail |
|---|---|
| `src/iee/core/shader_suite_config.*` | Paramètres typés, défauts, validation et résolution par shader ; branchement additif dans config existante. |
| `src/iee/core/shader_suite_math.*` | Références Gaussian/couleurs/contours/couverture/YUV, séparées des maths D1. |
| `src/iee/shader_suite.*` | Choix de profil au draw, capacités et snapshots ; réutilise la provenance créature D4. |
| `src/iee/shader_probe.*`, `shader_uniform_bridge.*`, `game/opengl_types.*` | Huit programmes, cycle de vie, uniforms stables/dynamiques, samplers multiples. |
| `assets/shader-suite/` | Fragments source communs et templates ; pas de `#include` supposé supporté par le jeu. |
| `assets/override/` | Huit sorties autonomes déterministes ; `fpSEAM` issu de la fusion IEE, conservant sa voie off. |
| `tools/build_shader_suite.py` | Assemblage/validation statique puis spécialisation/optimizer en D12 ; provenance et hashes. |
| `tools/shader_suite_profile.py` | Matérialisation d'un profil dans un candidat, diff et export des valeurs ; aucune édition live implicite. |
| `tools/install_shader_suite_candidate.py` | Transaction introduite D3 ; huit cibles exactes dès D3, collision/rollback/restauration. |
| `tools/InfinityEngine-Enhancer.sample.ini`, `CMakeLists.txt` | Paramètres, assemblage reproductible et notices ; anciens contrats D1 inchangés. |
| `FEATURE/profiles/` | Schéma, paramètres/defaults et dix presets amont + témoins IEE ; suivis Git. |
| `FEATURE/runs/<id>/coverage.json` | Preuve par composant/paramètre/shader/preset ; immuable après scellement, pas une autorité release. |
| `licenses/` | Notices du code et de l'optimizer réellement repris, version/hash d'origine. |
| Tests C++ + `pipeline/tests/` | Maths/configuration, outils/profils/transactions ; associer les fichiers dans `test_changed.py`. |

Choisir en D2 une seule autorité pour valeurs/defaults ; générer/vérifier les autres représentations.
Ne pas dupliquer manuellement les valeurs des presets entre C++, GLSL, JSON et Python.
Les sources natives extraites restent dans les runs ; conserver les sources dérivées nécessaires
au projet avec attribution et provenance comme pour les shaders IEE existants.

## 7. Validation et couverture ingame

### 7.1 Contrôles de développement

- Paramètres : neutres, extrema autorisés, NaN/inf/invalide, round-trip, casse/priorités D1 conservées.
- Gaussian : somme des poids, constantes, symétrie/phase ; sharpen zéro identité, alpha inchangé,
  RGB caché sans influence, `-1` moyenne RGB vérifiée.
- Couleurs : référence numérique d'ordre des opérations, gamma positif, saturation zéro, angle
  zéro/cycle complet, aucun NaN après contraste et teinte ; lumière linéaire sans double conversion.
- Contours : normal/sélection indépendants, taille zéro, alpha nul, épaisseur logique x1/x2/x4,
  transitions, absence de crop sur les tailles promises.
- Routage : HD/x1/sol/UI dans même programme, switch de texture sans `glUseProgram`, occlusion,
  relink/recréation contexte, pas de double effet ; toutes branches off équivalentes à leur référence.
- Formats : rouge font, atlas/tuiles bornés, plans YUV séparés, alpha `uTex2`, wrapping et tone GRY.
- Profils : chaque ID TP2 et paramètre manuel mappé, dix ensembles exacts, différence gamma vidéo,
  correction font après preset global ; chaque valeur exportée correspond au comportement actif.
- Outils : conflits, rollback partiel, restauration de `fpSEAM` IEE exact, anciens reçus compatibles,
  profil spécialisé périmé détecté, toutes notices/fichiers présents dans le candidat.
- Le sélecteur du dépôt prépare les tests du lot ; exécution selon choix utilisateur. Cette révision
  documentaire seule n'appelle aucun test Python, build, packaging ou reconstruction de projection.

### 7.2 Passages ingame

| Jalon | Essai exigé | Portée de la décision |
|---|---|---|
| D2 | Normal/sélection/zoom/options natives ; collecte UI/carte/vidéo et cas restants. | Interfaces et scènes de référence. |
| D3–D4 | Overrides inactifs, ciblage HD et témoins, restauration. | Neutralité et isolation. |
| D5 | Nearest / Linear / CR, alpha/occlusion, fixe + mouvement. | Correction du socle uniquement. |
| D6–D7 | Chaque effet seul, puis combinaisons sur HD, x1, équipement, objets au sol. | Tous réglages sprites opérants. |
| D8 | Texte et chiffres, cercles, portes/conteneurs, objets non identifiés, effets, pause. | Fonctions partagées et faux positifs. |
| D9 | Suite/eau quatre états, raccords x4, berges, jour/nuit, transitions et diagnostic F10. | Intégration carte/eau. |
| D10 | YUV et GRY, détails chroma, bord des plans, transparence/wrapping, pause si applicable. | Voies vidéo actives. |
| D11 | Les dix presets et profil Custom ; profils sprites/global ; effets cumulés en scène représentative. | Candidat complet comparable ; aucun composant manquant. |
| D12 | Profil général/spécialisé, optimizer on/off, scène chargée, texte et vidéo. | Équivalence et coût de chaque option d'optimisation. |
| D13 | Profil retenu exact, séquences et témoins des domaines qu'il touche. | Acceptation utilisateur du rendu pour le patch. |

Tester toutes les fonctions ne nécessite ni tous les sprites du jeu ni toutes les combinaisons
de nombres réels. Couverture minimale : chaque paramètre seul à valeur neutre et valeurs d'essai,
chaque choix discret, chaque shader pertinent, chaque preset et les interactions ci-dessous.

Interactions obligatoires : CR × sharpen ; contour × sélection/alpha/occlusion ; couleur × palette/
tint/pause ; global × profil HD ; anti-glitch × CR/sharpen ; gamma sélection × objets non identifiés ;
eau × profil global ; YUV × gamma/alpha/wrapping ; optimisation × profil/activation.
Captures appariées : même sauvegarde, zoom, résolution, options, position et éclairage, accompagnées
de séquences en mouvement. Le catalogue QA initial reste celui du guide ; élargir les assets
uniquement si un cas manquant l'exige, sans régénérer tout le catalogue.

`coverage.json` doit enregistrer pour chaque cas : identifiant amont/paramètre, shader, profil et
valeurs résolues, hashes DLL/INI/shaders, scène, preuve de draw actif, résultat technique, décision
esthétique utilisateur et capture/log. États distincts : `not-implemented`, `implemented`,
`installed`, `observed`, `pending-qa`, `accepted`, `rejected`, `blocked`.
Une option rejetée est testée et reste disponible ; une option ignorée ou jamais dessinée ne l'est pas.
Les fonctions propres à une UI tierce nécessitent cette UI pour revendiquer sa compatibilité ;
indiquer cette limite sans bloquer la décision d'un profil du patch qui ne l'utilise pas.

### 7.3 Sortie finale

- D11 terminé seulement avec toutes les fonctions installables, les huit shaders et les profils.
- D12 terminé avec optimisation disponible, preuve d'équivalence et mesures CPU/GPU du candidat.
- D13 : choisir le profil, pas seulement le mot `CatmullRom`. Une validation doit porter sur
  l'ensemble effectivement activé ; conserver les essais refusés et les limites explicites.
- Les métadonnées de QA catalogue ne deviennent pas celles du nouveau renderer ; preuve suite
  séparée, liée au catalogue. Aucune conversion implicite d'un baseline historique NEAREST.
- Intégration release distincte : adapter le futur helper renderer, manifests et notices à la liste
  complète après accord dédié ; aucune reconstruction de payload/staging/archive pendant ce plan.
