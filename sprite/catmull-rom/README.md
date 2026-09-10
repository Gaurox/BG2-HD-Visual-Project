# Catmull–Rom et suite graphique Dshaders — guide de développement

Statut : **D0–D6 terminés ; D7 partiel : x2 validé, x1 non routé ; tests non exécutés**. Vérification : 2026-09-10.
Public : agent IA reprenant le développement sans historique de conversation.

## 1. Mission et reprise

Intégrer nativement à InfinityEngine Enhancer toutes les fonctions configurables de Dshaders
0.3.5 sur BG2EE Steam 2.7.3.0 Windows x64, avec Catmull–Rom adapté aux créatures HD x2/x4.
Livrer un candidat complet permettant les comparaisons ingame avant de choisir le rendu du patch.
Conserver géométrie x1, ressources/palettes, équipement, cadence et sauvegardes ; les corrections
de couleur agissent uniquement au rendu.

- Socle D2–D5 : reconstruction 4×4 / 16 lectures, alpha prémultiplié, activation opt-in.
- Entrées : catalogue de sprites existant ; aucune nouvelle génération xBR requise.
- Socle créatures : `fpSprite`, `fpSELECT`, autres programmes seulement si tracés ; activation
  par provenance de texture au **dessin OpenGL effectif**.
- Suite D6–D11 obligatoire : contours, sharpen/flou, gamma/contraste/luminosité/saturation/teinte,
  polices, sélections, anti-glitch, portées sprites/tous les shaders, paramètres manuels et presets.
- Huit fragments cibles : `fpSprite`, `fpSELECT`, `fpDraw`, `fpTone`, `fpFONT`, `fpSEAM`,
  `fpYUV`, `fpYUVGRY`. `fpSEAM` doit intégrer la suite et conserver l'eau IEE existante.
- D12 : option d'optimisation disponible et comparée. D13 : sélection du rendu après QA complète.
- Installer toutes les capacités ne signifie pas activer simultanément des options exclusives.
  Le profil de référence reste disponible ; aucune fonction ne peut être reportée implicitement.
- Exclusions maintenues : remplacement brut par l'installeur Dshaders, nouveaux assets d'upscale,
  modification des sauvegardes, promotion release automatique. Le périmètre graphique global
  précédemment exclu est désormais inclus, via des profils explicitement activés.
- `Nearest` reste le défaut et la référence QA. Aucun rendu Catmull–Rom n'est encore approuvé.

Lecture de reprise : [AGENTS](../../AGENTS.md), [README projet](../../README.md),
[README sprites](../README.md), [décisions](../../docs/DECISIONS.md),
[blocages](../../pipeline/PROBLEMES_A_RESOUDRE.md), puis ce guide et
[DSHADERS_SUITE.md](DSHADERS_SUITE.md), contrat exhaustif de l'extension D2–D13.
Avant le code moteur : [AGENTS moteur](../../engine/InfinityEngine-Enhancer/source-patchee/AGENTS.md),
[README moteur](../../engine/InfinityEngine-Enhancer/source-patchee/README.md),
[threads/GL](../../engine/InfinityEngine-Enhancer/source-patchee/docs/threading-model.md).

Conventions utilisées ci-dessous, chemins relatifs à la racine du dépôt :

```text
FEATURE = sprite/catmull-rom
ENGINE  = engine/InfinityEngine-Enhancer/source-patchee
CATALOG = sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/runs/catalog-xbr2x-x2
GAME    = config://bg2ee_game_root
```

`FEATURE` reste le point d'entrée historique et conserve D0/D1 ; l'extension couvre aussi les
autres domaines graphiques. Ne pas déplacer les runs ou dupliquer un second plan à la racine.
Le code exécutable reste sous `ENGINE` ; aucune copie moteur sous `sprite/`.
Arborescence prévue, créer les sous-dossiers seulement au besoin :

```text
sprite/catmull-rom/
  README.md                         # parcours, socle et phases
  DSHADERS_SUITE.md                  # couverture complète, paramètres et contrats D2+
  runs/<run-id>/                    # captures/preuves/candidats immuables, déjà ignorés par Git
    native-shaders/                 # octets extraits des BIF, non redistribués comme sources projet
    linked-shaders/                 # sources réellement soumises au pilote
    candidate/                     # DLL/INI et payload shader séparés selon les transactions
    captures/
    evidence.json                  # provenance, capacités, paramètres, mesures, reçus
```

## 2. Résultat de la dernière vérification

Révision du plan : HEAD `843aa3844dda97d212706b896a100f5ac3ad5a9e`, worktree propre avant édition.
D0 : commit `5e68244f447f942396ac189391c5ad7baee386e9` ; six shaders et snapshot INI du run
revérifiés par SHA-256. D1 : commit `843aa38` ; maths/configuration, samplers, tests et protection
NEAREST des installateurs présents. Leur code et les preuves D0 restent inchangés.
L'utilisateur confirme le développement D0/D1 terminé ; le dépôt consulté ne consigne pas de
résultat d'exécution des tests D1. Ne pas inventer un succès ni recommencer D1 pour étendre la suite.

Le tableau suivant décrit le **socle créatures** ; la couverture élargie se lit dans le complément.

| Point | État établi et conséquence |
|---|---|
| Accès aux shaders 2.7.3 | Sources lues hors jeu dans `data/Shaders.bif`, type ressource `0x0405`. La capture ingame n'est **pas** un préalable à l'analyse ni au squelette. |
| Catmull–Rom natif | `fpCatRom` existe déjà : chemin actif 9 lectures RGB, alpha forcé à 1 ; référence 16 lectures sous `#if 0`. Associé à `vpBlit` dans la sonde. Ne pas l'employer tel quel pour des sprites transparents. |
| Compatibilité 2.7.3 | Le problème est l'intégration ciblée aux sprites HD et à leur alpha, pas la disponibilité de l'algorithme dans cette version. |
| Dessin différé | `RenderTexture` peut seulement enregistrer des commandes. Une portée uniforme C++ autour de son `original(...)` ne couvre pas leur exécution ultérieure. **Cette proposition initiale est abandonnée.** |
| Frontière GPU | Désassemblage local : `DrawFlush_GL` appelle `glDrawArrays` via un thunk d'import. Utiliser un hook GL avant cet appel, sans forcer un flush par créature. |
| Taille de texture | Descripteur moteur x1 ; stockage GL x2/x4. Le pas de lecture doit provenir de la taille physique, bord transparent inclus. |
| Occlusion | `native_occlusion_bridge` crée une nouvelle texture de sortie, actuellement en `GL_LINEAR`. Transmettre son identité/provenance au filtre ; ne pas supposer qu'elle conserve le sampler de l'entrée. |
| Capture | Une scène normale, une créature sélectionnée/survolée, puis comparaison des réglages de zoom suffisent pour découvrir les programmes. Aucun défilement exhaustif des sprites. |
| Compatibilité graphique restante | Préambule GLSL, programmes réellement utilisés par état et effet du réglage « Nearest Neighbor Scaling » à confirmer ingame. Aucun défaut visuel n'est affirmé sans essai. |

Preuves locales de référence : commit `de4bbd4ac2d9a5d7b7a21265e68cd8589349d395`.
Ces hashes identifient le snapshot inspecté ; les manifests/captures du nouveau run feront autorité.

| Entrée | SHA-256 |
|---|---|
| `GAME/BaldurReal.exe` | `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57` |
| `GAME/data/Shaders.bif` | `A93A717FDB677C711F5BFBCD131BC42E17A34FE5725552218964049E906FD1C6` |
| `GAME/chitin.key` | `1818FFEBB2424992FB39FB13509E7F629AC819B08A553C2DD4AC25F2E40A979F` |
| `FPSPRITE` brut BIF | `5af0681b758b70583eca4adb5fbeffd120f03bfdd2719272628b3956378039f8` |
| `FPSELECT` brut BIF | `a94dae1b816454db48e85ccf884e4f4d59ebce9c97fc6bcfd2cf58dd45c1b1c6` |
| `vpDraw` brut BIF | `9a309182765e8a7bd06c71a8676cc897e2f980013d93167391ce19d564363a38` |
| `fpDraw` brut BIF | `c54e9f42127097a516f438a9dbe0be586b81c68a38fdc3693bb4a9b62fbc12cb` |
| `fpCatRom` brut BIF | `bff864f08f69da2e72531076f9a64b10abca2b306d60a991893c124039935ace` |
| `vpBlit` brut BIF | `21d575a5e502de4fb2337d3b67b3b6136014126a59996a7982d0323068dca6cc` |

Sur cet exécutable : `DrawFlush_GL` commence au RVA `0x42B350` ; appel au RVA `0x42BAE5`
vers le thunk `0x531344`, résolu en import `glDrawArrays`. Preuve de routage uniquement :
ne pas coder ces offsets dans un nouveau hook. Employer l'API GL résolue ; toute nouvelle adresse
moteur doit passer par `src/iee/game/build_manifest.*` et sa validation.

État local observé en D0 : seul `override/fpSEAM.glsl` présent ; aucun `iee-shader-dumps/`.
Catalogue actif : `CATALOG/current-generation.json` et `CATALOG/ingame-installation/active-test.json`.
Génération observée `D55EFD6D1B342B1240AC2BBD222BC088B38F86D4503E6F46B03CB447A704B8F2` ;
xBR2x, x2, `antialias=false`, `xbr_blend=false`, `sampling=NEAREST` ;
animations `0x6102`, `0x6110`, `0xE400` ; `installed-pending-qa`. Relire les autorités à la reprise.

### D0 — référence locale 2026-09-09

| Résultat | Preuve |
|---|---|
| Six sources BIF `0x0405` extraites, octets bruts et hashes conformes au tableau ci-dessus | `runs/d0-20260909-native-shaders/native-shaders/` ; `runs/d0-20260909-native-shaders/evidence.json` |
| Snapshot INI brut, aucune installation ni modification de jeu | `runs/d0-20260909-native-shaders/candidate/InfinityEngine-Enhancer.ini` ; `runs/d0-20260909-native-shaders/evidence.json` |
| Aucune collision avec les six shaders cibles ; seul `override/fpSEAM.glsl` est présent | `runs/d0-20260909-native-shaders/evidence.json` |
| Autorités catalogue relues : génération `D55E…B8F2`, test `installed-pending-qa`, `NEAREST`, `0x6102/0x6110/0xE400` | `runs/d0-20260909-native-shaders/evidence.json` |

Écart consigné, non corrigé : hash de l'INI live `4F9A…FA9EA` différent de
`active-test.json` (`installed_ini_sha256=4E09…8A17`). Cet état n'est ni une installation D0 ni
une QA ; toute opération D2+ devra partir de ce snapshot et utiliser sa transaction dédiée.

## 3. Sources natives et externes

### 3.1 Extraction locale sans installation

Réutiliser `pipeline/scripts/bg2lib.py` : `load_key()`, `resolve_resource()`.
`workspace_paths.get_path('bg2ee_game_root')` résout la configuration machine ; ne pas ajouter de
chemin personnel. Exemple vérifié, lecture seule depuis la racine du dépôt :

```powershell
python -B -c "import sys,hashlib; sys.path.insert(0,'pipeline/scripts'); import bg2lib; b,r=bg2lib.load_key(); wanted={'FPSPRITE','FPSELECT','VPDRAW','FPDRAW','FPCATROM','VPBLIT'}; [(print(n,hex(t),origin,hashlib.sha256(data).hexdigest()),print(data.decode('utf-8'))) for n,t,loc in r if n.upper() in wanted and t==0x405 for data,origin in [bg2lib.resolve_resource(b,loc)]]"
```

Pour l'archivage futur : conserver les **octets bruts** avant normalisation des fins de ligne.
Les shaders BIF ne comprennent pas le préambule ajouté par le moteur. Ne pas transformer un dump
complet en override en dupliquant `#version`, macros de précision ou en-tête moteur.

### 3.2 Comportement à préserver

| Source | Comportement lu |
|---|---|
| `vpDraw` | Transforme les coordonnées texels logiques : `vTc = aTc * uTcScale`. |
| `FPSPRITE` | Flou/contour : 25 lectures à offsets UV fixes de `0.0005`, puis lecture centrale et `mix(blur_colour, tex_color, tex_color.a)`. `uTcScale` n'est pas déclaré dans ce fragment. |
| `FPSELECT` | Lecture centrale ; seuil alpha `0.1` ; `mix(vColor, texColor, texColor.a)` si solide ; sinon voisinage 7×7 basé sur `uTcScale` pour le surlignage. |
| `fpDraw` | Lecture centrale, modulation `vColor`, teinte `uColorTone`. Candidat au socle HD si tracé ; obligatoire en D8 pour la suite. |
| `fpCatRom` | Filtre de blit opaque ; ne reconstruit pas un alpha de sprite. Conserver son chemin natif. |

Première variante GPU : remplacer uniquement la lecture centrale dans les deux shaders cibles.
Conserver voisins, seuils et opérations finales natifs. La reconstruction prémultipliée en amont
ne prouve pas à elle seule la qualité de l'alpha final : les deux shaders mélangent à nouveau
avec cet alpha. Tester le résultat après blending avant de modifier ces opérations.

### 3.3 Dshaders : source de la suite complète

Révision épinglée : `4722673a8017c56ace4018b3db459392ecbb75a4` ; version annoncée 0.3.5.

- [README / prérequis 2.6](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/drunkshaders/readme.txt).
- [Fonctions GLSL / `uhFetchCatmullRom`](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/drunkshaders/glsl-parts/functions-game.glsl).
- [Licence MIT](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/LICENSE).

Reprendre les fonctionnalités et paramètres, en adaptant les interfaces natives 2.7.3 et les
textures HD. Le TP2 et les sources GLSL font foi pour les valeurs et portées réellement installées ;
les écarts README/code vérifiés sont consignés dans [le complément](DSHADERS_SUITE.md).
Le quadrillage `1/uTcScale` amont ne connaît pas notre backing HD. Les exigences du mod sur
Nearest ne constituent pas un contrat pour notre implémentation. Conserver attribution et licence
du code repris ; aucune dépendance runtime à WeiDU/Dshaders n'est nécessaire.

## 4. Architecture de référence

Sections 4.1–4.4 : contrat du socle créatures D2–D5. L'extension ajoute le routage par shader,
les profils et les effets selon [DSHADERS_SUITE.md](DSHADERS_SUITE.md), sans changer la sémantique D1.

### 4.1 Texture et provenance

Flux prévu :

```text
palette + frame/couches HD
  -> texture GL privée, backing physique xN
  -> éventuelle texture privée masquée par le bridge d'occlusion
  -> commandes moteur différées référant cette texture
  -> DrawFlush_GL : programme + texture réellement liés
  -> hook glDrawArrays : identifier la texture, alimenter les uniformes
  -> dessin natif exactement une fois
```

Créer un petit registre RAM borné, possédé par le thread de rendu, indépendant du mutex du
catalogue. Clé : `(génération de contexte WGL, nom GL)` ; valeur minimale : provenance créature,
largeur/hauteur physiques, échelle 2/4, génération de contenu, sampler attendu, variante masquée.

Règles :

1. Enregistrer uniquement une texture privée après upload validé ; jamais par simple ratio x2/x4.
2. Enregistrer frames mises en cache et composites Character transitoires.
3. Lors d'une occlusion, transférer la provenance à la sortie **seulement** si l'entrée est une
   texture créature enregistrée. Les sorties d'animations de zone/effets restent exclues.
4. Le moteur marque certains descripteurs `delete-pending` avant le flush. Ne pas retirer
   l'identité au retour de `RenderTexture` ni au seul `DrawDeleteTexture` logique.
5. Retirer/renouveler l'identité à la suppression GL réelle, à la redéfinition du stockage ou à
   la réutilisation de son nom. Intégrer les hooks d'upload/suppression existants ; tenir compte
   des chemins compressés susceptibles de réutiliser un nom GL. Publier après réussite d'upload.
6. Un `TexImage` moteur peut déclencher des travaux différés avant la redéfinition physique :
   ne pas invalider prématurément la preuve des dessins déjà en attente.
7. Changement de contexte : invalider registre, programmes et locations ; réinscrire les nouvelles
   textures. Capacité dépassée/état inconnu : filtrage désactivé pour les dessins non prouvés.
8. Aucun accès catalogue/disque ni prise de `g_mutex` créatures depuis le hook GL. Le moteur peut
   flusher pendant une création de texture déjà exécutée sous ce mutex.

### 4.2 Activation au dessin effectif

Le hook `glDrawArrays` doit être installé dès l'activation du mode expérimental, indépendamment
de `VerboseLogs`, `PerformanceLogs`, du module eau et des prototypes UI.

- Avant chaque dessin : programme reconnu comme shader sprite modifié + sampler `uTex` réellement
  utilisé + texture enregistrée + contexte/capacités valides => filtre actif.
- Sinon, pour tout programme sprite modifié, alimenter explicitement le chemin neutre.
- Lire l'unité effective de `uTex` ; ne pas confondre unité GL active et unité du sampler.
- MVP : requêtes GL ciblées pour établir cet état. Optimiser le cache des bindings seulement après
  mesure ; `glUseProgram` seul ne couvre pas les changements de texture avec programme inchangé.
- Uniformes dynamiques hors du court-circuit `lastAppliedRevision` du bridge statique.
- MVP : remettre l'uniforme dynamique à zéro après le `glDrawArrays` natif via une garde de portée.
  Sur erreur avant le dessin, sélectionner le chemin neutre si le contexte et les locations sont
  valides. Cette portée entoure l'appel GL réel, et non la mise en file par `RenderTexture`.
- Ne pas forcer un `DrawFlush_GL` par créature ; conserver les lots du moteur.
- Les appels `glDrawArrays` du FBO d'occlusion sont exclus par leur programme.
- Original appelé exactement une fois, y compris en cas d'erreur ; aucune exception C++ ne traverse
  la frontière ABI. Aucun appel GL sous `g_probeMutex`.
- Une trace bornée doit vérifier qu'aucun autre type de draw GL ne porte les sprites ciblés.
  N'ajouter un hook supplémentaire que si cette trace l'exige.

### 4.3 Contrat INI D1 conservé et GLSL du socle

Clé sous `[Shaders]` :

```ini
CreatureSpriteFilter = Nearest
```

| Valeur | Enum D1 | Texture créature | Filtre shader |
|---|---:|---|---|
| `Nearest` | 0 | `GL_NEAREST` | chemin natif |
| `Linear` | 1 | `GL_LINEAR` | chemin natif, A/B historique |
| `CatmullRom` | 2 | `GL_NEAREST` pour la référence 16 lectures | actif uniquement sur texture propriétaire |

Parsing insensible à la casse ; défaut `Nearest`. La nouvelle clé présente prime sur
`EnableCreatureSpriteLinearFiltering`, quel que soit l'ordre des lignes. Si elle est absente,
ancien booléen vrai => `Linear`, sinon `Nearest`. Valeur invalide => avertissement et `Nearest`.
Conserver explicitement la présence de la clé pendant le parsing ; ne pas utiliser la seule valeur
par défaut pour résoudre la priorité. MVP : configuration au démarrage, sans hot-reload des samplers.

Uniformes proposés, distincts de l'eau :

```glsl
uniform float uIeeCreatureFilterMode;  // 0/1/2, ou 0 si fonctionnalité indisponible
uniform vec2 uIeeCreatureTexelSize;    // 1/Wphys, 1/Hphys ; (0,0) pour un dessin non propriétaire
```

Activer le calcul seulement pour mode 2 et taille de texel strictement positive/valide.
L'échelle x2/x4 est validée en C++ et conservée en diagnostic. Transmettre directement l'inverse
des dimensions physiques évite de dépendre d'un uniforme absent de `FPSPRITE`.
Relation de contrôle, après confirmation de `uTcScale` : `texelSize = uTcScale / scale`.
Ne jamais modifier `uTcScale` natif : `vpDraw` et les voisins de `FPSELECT` en dépendent.

Les textures masquées ont actuellement `GL_LINEAR` même sous baseline créatures NEAREST :
conserver le comportement historique en modes 0/1 ; garantir `GL_NEAREST` sur leur backing en
mode 2. Ne pas changer le sampler du bridge pour les animations de zone/effets.
Aux centres exacts, une lecture `texture2D` LINEAR peut aussi retourner un texel exact, mais la
référence NEAREST supprime cette dépendance à la précision des coordonnées.

Uniformes à zéro sans DLL => branche native **si le shader compile et linke**. Cette propriété
ne protège pas d'une erreur GLSL ; validation pilote et restauration restent nécessaires.
Avec filtre demandé mais programme non disponible : repli sans filtrage cubique + diagnostic,
pas de promesse de reconstitution x1 ni de modification silencieuse du catalogue.

### 4.4 Reconstruction 16 lectures

Coordonnées à utiliser à partir du `vTc` normalisé réel :

```text
q = vTc / texelSize - 0.5
i = floor(q)
f = q - i
voisins : i + (dx,dy), dx/dy dans {-1,0,1,2}
UV de lecture : (voisin + 0.5) * texelSize
poids 2D : wx[dx+1] * wy[dy+1]
```

Poids Catmull–Rom pour `t` dans `[0,1]` :

```text
w0 = -0.5*t^3 +     t^2 - 0.5*t
w1 =  1.5*t^3 - 2.5*t^2         + 1
w2 = -1.5*t^3 +   2*t^2 + 0.5*t
w3 =  0.5*t^3 - 0.5*t^2
```

- Déplier les 16 lectures, factoriser les poids X/Y ; pas de tableau de voisinage global 6×6.
- Respecter `CLAMP_TO_EDGE` sur la texture complète. Les voisins peuvent sortir du domaine avant
  clamp ; ne pas appliquer `fract(vTc)` ni tronquer vers zéro à la place de `floor`.
- Backing : `(Wframe+2)*scale` pour une frame ; `(Wunion+2)*scale` pour un composite. Même formule
  sur H. Le bord transparent correspond à un pixel logique de chaque côté.
- Ce bord fournit le support de la reconstruction ; il ne prouve pas que la géométrie rasterisée
  couvre tout le contour natif. Vérifier les crops, sans agrandir automatiquement la géométrie.
- Choisir la syntaxe à partir du préambule 2.7.3. `texture2D` suffit ; ne pas imposer arbitrairement
  `#version 110`, ni exiger `textureSize`/`texelFetch` dans le MVP.

Traitement RGBA, avant les opérations natives de contour/surlignage :

```text
pour chaque texel k :
  ak = clamp(alpha_k, 0, 1)
  ck = RGB dans l'espace de travail ; neutralisé si ak == 0
  pk = ck * ak
Araw = somme(poids_k * ak)
Praw = somme(poids_k * pk)
A = clamp(Araw, 0, 1)
P = clamp(Praw, vec3(0), vec3(A))
si A <= epsilon : RGBA = 0
sinon : RGBA = (conversion_sortie(P/A), A)
```

`epsilon` fixé par D1 : `1e-6`. Ne pas borner séparément les sommes intermédiaires
horizontales ; borner après accumulation complète. Les poids négatifs sont normaux : les clamps
bornent les valeurs, sans garantir l'absence de ringing perceptible.

Variante initiale : espace des valeurs stockées (`GL_RGBA8`), coût réduit et comparaison native
directe. Variante expérimentale secondaire : conversion sRGB exacte vers lumière linéaire avant
prémultiplication, inverse après division. Ne pas gamma-corriger l'alpha ; vérifier l'état
`FRAMEBUFFER_SRGB`/format de destination avant de revendiquer une chaîne linéaire correcte.
Ces variantes restent comparables ; D6 ajoute les paramètres colorimétriques de la suite sans
modifier la référence CPU D1. Leur contrat et l'ordre des opérations sont dans le complément.

Un Catmull–Rom local n'est pas un filtre de réduction d'échelle complet. Au zoom arrière,
tester scintillement et moiré ; ne pas ajouter de mipmaps ni de filtre plein écran au socle.
Le sharpening est développé séparément en D6 puis disponible dans le candidat complet.

## 5. Carte du code à modifier

Tous les chemins suivants sont relatifs à `ENGINE`, sauf indication contraire.

| Fichier/module | Intervention prévue |
|---|---|
| `src/iee/core/config.h/.cpp` | Contrat D1 acquis ; ajouts de configuration suite sans changer enum/priorité legacy. |
| `src/iee/core/creature_sprite_filter_math.h/.cpp` | Référence CPU pure 4×4, poids et RGBA prémultiplié ; présente depuis D1. |
| `src/iee/dll_main.cpp` | Initialisation `configure_filter_mode` acquise ; ajouter celle de la suite. |
| `src/iee/creature_sprite_x2.h/.cpp` | Samplers, publication d'identité après `upload_frame_locked`/`upload_composite_texture_locked`, renouvellement du cache. |
| `src/iee/hooks.cpp` | `detour_vid_cell_render_texture` : corréler propriété et éventuelle sortie d'occlusion ; pas de portée shader limitée à cet appel. |
| `src/iee/native_occlusion_bridge.h/.cpp` | Propager les métadonnées de l'entrée créature vers la sortie ; sampler de sortie adapté au mode 2 seulement. |
| Nouveau `src/iee/creature_sprite_filter.h/.cpp` | Registre de textures, état effectif du draw et contrôle de capacité. Séparer les fonctions pures testables si nécessaire. |
| `src/iee/shader_probe.cpp` | Hook `glDrawArrays`, cycle de vie upload/delete, classification, preuves compile/link, invalidation de contexte/programme. |
| `src/iee/shader_uniform_bridge.h/.cpp` | Locations des uniformes, alimentation statique et dynamique séparées ; aucune réutilisation de `uIeeEnabled`. |
| `src/iee/game/opengl_types.h/.cpp` | Déjà `glDrawArrays` ; compléter seulement les requêtes GL nécessaires au contrat effectif. |
| `src/iee/game/shader_override.*` | Renforcer si besoin le contrôle de déclarations : l'actuel vérifie essentiellement la présence de noms, pas toute l'interface typée. |
| `assets/override/fpDraw.glsl`, `fpSprite.glsl`, `fpSELECT.glsl` | Sources natives adaptées, entrée cubic unique, branche désactivée identique ; `fpDraw` couvre le chemin créature HD réellement tracé. |
| `tools/InfinityEngine-Enhancer.sample.ini` | Nouvelle clé et portée documentées. |
| `tests/iee_tests.cpp` et tests dédiés éventuels | Configuration, maths, contrats, cycle de vie du filtrage. |
| `CMakeLists.txt` | Ajouter sources/tests. La copie du dossier `assets/override` existe déjà ; cela ne met pas à jour les manifests de release. |
| `tools/install_shader_suite_candidate.py` | Transaction à liste exacte : huit shaders dès D3 selon la notice courante. Manifeste, collision/rollback/restauration ; remplace le nom projeté `install_sprite_shader_candidate.py`. |
| `pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1` | D1 force déjà `CreatureSpriteFilter=Nearest`. Ajouter en D11 le contrôle suite désactivée pour ce baseline. |
| `pipeline/tests/` et `pipeline/scripts/test_changed.py` | Tests de transaction, migration INI et routage ciblé du nouveau script. |

Modules supplémentaires, génération des shaders et profils : [carte de l'extension](DSHADERS_SUITE.md#6-fichiers-et-livrables).

Dans `shader_probe.cpp`, `read_shader_source_prefix` lit actuellement 4096 octets pour détecter
`uIee`. Déclarer les uniformes près du début, puis vérifier leurs **locations actives** et la version
du contrat sur chaque programme lié. Une simple occurrence de `uIee` dans un commentaire ne suffit
pas à déclarer le filtre disponible. Invalider aussi après relink/deletion du programme.

`submit_shader_source` journalise et transmet actuellement les sources sans les remplacer.
Les overrides sont chargés par le jeu ; les programmes déjà liés sont retrouvés par introspection.
Ne pas fonder le MVP sur un remplacement à chaud des sources ou des programmes moteur.

## 6. Étapes de développement et critères de sortie

| Lot | Travail | Critère de sortie |
|---|---|---|
| D0 — Référence | Relire état Git/autorités ; extraire les six ressources ; créer un run d'étude avec hashes et snapshot INI. | Sources 2.7.3 disponibles, aucune collision shader non résolue. |
| D1 — Maths/config | Référence CPU, poids, alpha, enum et priorité INI ; tests unitaires préparés. | Reconstruction exacte au centre, invariants mathématiques et configuration spécifiés/testés selon choix utilisateur. |
| D2 — Capture et contrat suite | Relever les huit fragments, leurs programmes et textures ; figer profils/paramètres et interfaces HD/globales. | Capture créatures exploitable ; inventaire des huit interfaces, shaders restants à observer identifiés et planifiés. |
| D3 — Overrides neutres/transaction | Sources dérivées 2.7.3 pour les sprites ; interfaces de la suite et transaction extensible. | Compile/link ingame, A/B neutre, installation/restauration vérifiées dès le premier override. |
| D4 — Routage texture | Registre propriétaire, hook draw effectif, uniformes dynamiques, sortie d'occlusion, nettoyage et fallback. | Créature HD détectée même après retour de RenderTexture ; témoins hors périmètre jamais marqués. |
| D5 — Filtre GPU de référence | 16 lectures, coordonnées physiques, alpha ; remplacement central seulement. | Référence CPU/GPU cohérente ; contrôle ingame du socle, sans sélection esthétique finale. |
| D6 — Suite esthétique créatures HD | Contours normal/sélection, sharpen/flou, espace linéaire et cinq réglages de couleur ; paramètres indépendants. | Chaque réglage est effectif ingame, neutre désactivé, transparent sans frange ; D1 reste une référence inchangée. |
| D7 — Tous les sprites | Ajouter la portée `fpSprite`/`fpSELECT` incluant x1 et objets au sol, sans dépendre du catalogue HD. | Profils HD seul / sprites amont comparés ; pas de double filtrage des HD. |
| D8 — Draw/Tone/Font | Effets partagés, gamma polices/hack UI, gamma sélection, anti-glitch commutable. | UI/effets/objets/sélections et pause testés ; chaque option supportée est observable. |
| D9 — Cartes/SEAM | Fusion source de la suite avec l'eau IEE, bornes de tuiles HD et espaces couleur. | A/B eau on/off, cartes x4, raccords, transitions et diagnostics existants préservés. |
| D10 — YUV/YUVGRY | Filtrage/netteté/couleurs des vidéos et éléments YUV, plans/chroma/alpha natifs adaptés. | Les deux chemins compilent ; coordonnées, alpha, wrapping et préréglages vidéo vérifiés ingame. |
| D11 — Candidat complet/QA | Installer les huit shaders, tous les paramètres et dix presets amont ; outil de profils ; couverture exhaustive des options. | Chaque option est livrée/testable ; matrice individuelle et presets combinés exécutée, reçus et restauration vérifiés. |
| D12 — Optimisation/performance | Option GLSL optimizer et profils spécialisés ; comparer aux sources non optimisées, mesurer scènes complètes. | Optimisation reproductible/désactivable, équivalence dans tolérance, coût CPU/GPU documenté. |
| D13 — Choix du patch/promotion | QA finale du profil exact retenu, décision utilisateur, documentation puis demande release distincte. | Aucune option manquante masquée par D5 ; profil validé et hashes scellés ; release seulement sur accord spécifique. |

D0–D3 sont conservés ; la reprise est D4. Les anciens D6–D8 sont remplacés par D6–D13 ci-dessus.
Les fonctions de D6–D12 sont obligatoires à livrer, leur activation reste optionnelle.
Employer la transaction renderer dès le premier candidat D2 et la transaction shader dès D3.
Chaque nouveau shader D7–D10 passe d'abord un A/B neutre. Les essais intermédiaires valident
l'intégration ; le choix esthétique final attend le candidat complet D11 et ses mesures D12.

### D2 : protocole de capture

1. Fermer jeu et InfinityLoader avant changement de fichiers. Conserver l'INI exact et les hashes
   des éventuels overrides ; `fpSEAM` reste installé.
2. Préparer un candidat INI fusionné avec `[Shaders] DumpEngineShaders=true` et
   `[Core] VerboseLogs=true`. Ne pas remplacer l'INI partagé par le sample.
3. Pour la capture native des sprites, aucun override sprite. `fpSEAM` IEE reste installé et son
   dump est identifié comme IEE, pas natif. Extraire son original du BIF séparément. Archiver un
   dump préexistant avant relance : `dump_shader_source` ouvre les fichiers en mode troncature.
4. Charger une sauvegarde avec groupe visible ; créature normale, sélection/survol, déplacement ;
   invisibilité/flou si disponible. Relever programmes et textures, pas seulement les sources.
5. Capturer séparément « Nearest Neighbor Scaling » activé/désactivé, zooms identiques ; redémarrer
   si nécessaire. `Alternate Renderer` désactivé pour la cible OpenGL.
6. Vérifier dans `GAME/iee-shader-dumps/` au minimum `fpSprite`, `fpSELECT`, `vpDraw` ; conserver
   les huit fragments de la suite, `vpYUV`, `fpCatRom`, `vpBlit` s'ils sont dumpés. Compléter les
   cinq nouveaux fragments BIF dans un **nouveau run D2**, jamais dans D0. La sonde balaie aussi
   les programmes préexistants ; leur présence ne prouve pas un dessin effectivement observé.
7. Archiver sources linkées et logs ; vérifier les hashes et la présence du préambule. Le dump
   contient les sources attachées actuelles, y compris un override éventuel : son nom ne prouve
   pas son origine native. Restaurer les options de diagnostic après collecte.

Trace GPU minimale bornée : contexte/programme/type de shader, texture et unité `uTex`, dimensions
logiques/physiques, provenance, min/mag filter, viewport/FBO, paramètres de blending, options/zoom.
Si un programme cible manque, vérifier le traçage et le log ; ne pas essayer tous les sprites.
Pour la suite : ouvrir inventaire/texte, observer un objet au sol, les sélections porte/conteneur,
une animation/sort, la pause/teinte et une séquence vidéo disponible. Identifier les scènes utiles
à D8–D10 si tout n'est pas activable au premier passage ; aucun défilement exhaustif des sprites.
Relever aussi alpha source/couverture, sous-rectangles d'atlas et textures YUV multiples.
`fpDraw` est obligatoire pour la suite, même s'il ne porte aucun sprite HD. Dans le socle D5,
un chemin HD par `fpDraw` reste conditionné par le même contrôle propriétaire.

## 7. Validation

### 7.1 Tests automatisés à prévoir

| Domaine | Cas utiles |
|---|---|
| Maths | Poids somme 1, symétrie, texel au centre, couleur constante, damier/impulsion, positions négatives avant clamp. |
| Alpha | RGB caché sous alpha nul sans influence, alpha partiel, petites valeurs, aucun NaN, résultat borné, traits d'un texel. |
| Géométrie | x2/x4, bord transparent, composite non carré, toutes phases sous-pixel, centres et dimensions physiques. |
| GPU synthétique | CPU vs shader sur petite texture connue ; comparaison avec tolérance déclarée de quantification RGBA8. Test séparé de la sortie finale avec blend natif. |
| Configuration | Défaut, trois modes, casse, valeur invalide, clé legacy, ordre des clés, round-trip. |
| Dessin différé | Enregistrer créature, sortir de RenderTexture, exécuter le draw plus tard : filtre encore actif. |
| Isolation | Même programme : HD → x1 → effet → HD ; changement de texture sans `glUseProgram` ; mode off ; bridge eau off. |
| Lifetime | Delete-pending avant flush, suppression GL, redéfinition/recyclage du nom, changement de contexte, relink programme, capacité saturée. |
| Occlusion | Texture enfant créature reconnue ; enfant effet/zone exclu ; état GL et sampler restaurés. |
| Distribution | Shaders et notices présents dans bundle candidat ; transactions exactes et restaurables. |

Cette matrice couvre le socle. La [matrice suite](DSHADERS_SUITE.md#7-validation-et-couverture-ingame)
ajoute paramètres, scopes, presets, shaders partagés, eau, YUV et optimisation ; elle est obligatoire.

Tests des maths et du registre sans contexte GL dans une cible isolée si possible. Les tests de
présence de chaînes ne remplacent ni un test de comportement ni la compilation réelle du pilote.
Pour un shader manquant, tester le repli ; pour une erreur de compilation, tester la récupération
par restauration sans prétendre que l'uniforme zéro peut réparer un programme non lié.

### 7.2 QA visuelle

Variantes D5 : baseline `Nearest`, témoin `Linear`, Catmull–Rom espace stocké ; lumière linéaire
seulement après fonctionnement de la première. Pas de régénération x4 pour la seule comparaison.
Le support mathématique x4 peut être testé sur texture synthétique ; une qualification ingame x4
exige ensuite un catalogue x4 déjà disponible ou une génération autorisée.

| Axe | Couverture minimale |
|---|---|
| Créatures | `0x6102`, `0x6110`, `0xE400` ; personnage composé et monstre. |
| Animation | Attente, marche 8 directions, attaque, sort, impact, mort ; changements de frame en mouvement. |
| Équipement | Armure, casque, arme fine, bouclier/offhand ; palettes contrastées. |
| États | Normal, sélection/survol, invisibilité/semi-transparence, flou/images miroir si applicables. |
| Occlusion | Murs ; bridge actif/inactif en comparaison contrôlée ; contours d'intersection à fort contraste. |
| Zoom | Minimum, usuel, maximum, niveaux intermédiaires ; sol clair/sombre ; mouvement de caméra. |
| Témoins | Créature x1 non cataloguée, animation de zone, effet, objet au sol, texte/UI, eau `fpSEAM`. |

Critères : détail conservé, lissage accepté, pas de frange sombre/colorée ni de scintillement
supplémentaire marqué ; ancrage/crop stables ; surlignage lisible ; aucun témoin hors périmètre
modifié dans le profil HD seul. Pour les scopes élargis, la matrice précise les cibles autorisées
et les témoins. Captures fixes appariées et séquences temporelles : une image ne valide pas la marche.

L'alpha de la texture masquée est lui aussi interpolé ; cela ne garantit pas une découpe WED
strictement identique aux pixels masqués. Si un débordement visible est constaté, mesurer puis
tester un repli Nearest pour ces seuls dessins. Une éventuelle réapplication séparée du masque
après reconstruction constitue un lot suivant, avec durée de vie de masque prouvée ; ne pas
réutiliser aveuglément le masque temporaire partagé ni corriger les WED pour cacher le défaut.

### 7.3 Performance et optimisations

- Scène de combat fixe, cache chaud, beaucoup de créatures, selected/unselected, zooms usuels.
- Mesurer frame time médian/p95 et temps CPU du hook ; temps GPU si l'outillage le permet.
  Un FPS plafonné identique à 30 ne prouve pas l'absence de coût GPU.
- Désactiver les logs verbeux pendant les mesures ; conserver les mêmes options de rendu/FPS.
- Budget initial proposé, à fixer sur la machine de référence : surcoût total médian ≤ 5 % et
  p95 sans dégradation répétée notable. Ajouter un budget GPU de 1 ms si une mesure GPU fiable existe.
- Coût théorique du socle D5 seulement : 16 lectures centrales au lieu de 1 ; voisins natifs inchangés.
  `FPSPRITE` passe ainsi de 26 à 41 lectures source dans sa forme non optimisée, pas à 26×16.
- Priorité : pas d'I/O/allocation/catalogue dans le hook ; locations et classification mises en
  cache ; écritures d'uniformes évitées si la valeur du **draw** est inchangée ; ensuite code GLSL.
- Préférer le shader 16 lectures tant que le budget est tenu. Le 9 lectures natif regroupe des
  voisins via interpolation matérielle LINEAR. Appliqué à RGBA droit, puis prémultiplié après
  lecture, il n'est pas équivalent au filtre 16 lectures prémultipliées. Même contrainte pour
  une conversion sRGB après interpolation. Une optimisation 9 lectures exige un stockage/sampler
  adapté et une preuve d'équivalence ; elle n'est pas un remplacement direct.
- D12 mesure aussi les scopes globaux, profils combinés, contours et YUV. Le 4×4 CR/sharpen doit
  partager ses lectures ; les contours peuvent exiger un support supérieur. Ne pas annoncer
  « 16 lectures pour toute la suite ». Contrat optimizer dans le complément.

## 8. Installation, suivi et release

### 8.1 Candidat de développement

Référence obligatoire : [transaction renderer](../../engine/InfinityEngine-Enhancer/source-patchee/docs/renderer-candidate-transaction.md).
Elle possède exactement DLL + INI ; conserver ce contrat. La transaction shader séparée doit avoir :

- liste exacte par candidat, initialement `override/fpSprite.glsl` et `override/fpSELECT.glsl`,
  puis les huit fragments à D11 ; aucun glob sur `override/` ;
- `--verify-only`, reçu unique, copies avant/après hashées, refus de liens et chemins hors périmètre ;
- détection de collision insensible à la casse ; shader tiers inconnu => refus, aucune fusion automatique ;
- publication fichier par fichier atomique et rollback compensatoire du lot en cas d'échec ;
  ne pas qualifier deux remplacements disque indépendants de transaction atomique globale ;
- vérification et restauration idempotentes ; fichier changé par un tiers laissé intact avec erreur ;
- retrait d'un fichier initialement absent uniquement s'il correspond encore au hash du candidat ;
- reçu conservé même si le dossier de build disparaît ; liaison des deux reçus dans `evidence.json`.

Installation jeu/InfinityLoader fermés : préflight des deux transactions, shaders puis DLL/INI,
vérification des deux reçus avant lancement. Si la seconde transaction échoue, restaurer la première.
Restauration : DLL/INI puis shaders, avant tout redémarrage ; vérifier les hashes initiaux.

D1 a déjà ajouté `CreatureSpriteFilter=Nearest` aux installateurs et au contrat du catalogue.
D11 doit aussi protéger ce baseline contre une suite esthétique active : contrôle explicite du
nouveau master et preuve du profil neutre. Conserver la lecture des anciens reçus sans réécriture.
Ne pas relancer un install/restore du catalogue ou du renderer release pendant une transaction
suite active. Pour `fpSEAM`, sauvegarder/restaurer les octets IEE réellement installés, pas le BIF
ni un bundle historique. Restaurer les expérimentations dans l'ordre inverse.

### 8.2 Preuve et promotion

Chaque `evidence.json` doit identifier : schema/version, run, commit+diff source, cible EXE,
hashes BIF/bruts/linkés, DLL/INI/shaders, génération catalogue, GPU/pilote/GL/GLSL,
options natives, mode demandé/effectif, variantes/captures, tests exécutés ou non, mesures,
reçus install/restore et décision QA utilisateur. Pas de hash/succès fictif.
Ajouter pour la suite : profils résolus et hashes, huit états de capacité/dessin, couverture de
chaque paramètre/preset, espaces couleur, écarts amont assumés et identité de l'optimiseur.

Le run de filtrage référence la génération de sprites existante ; il ne la réécrit pas.
Ne pas falsifier `sampling=NEAREST` de l'ancien `active-test.json` pour décrire un nouvel essai.
Conserver la preuve du candidat séparément tant que le contrat courant ne permet pas de sélectionner
ce tuple renderer+shaders. Versionner ce contrat si une sélection courante doit être ajoutée.

Après acceptation ingame seulement : enregistrer le résultat avec ses hashes et préparer la décision
d'intégration release distincte. Consulter [README release](../../releases/BG2-HD-Upscale/README.md).
La liste figée de fichiers du helper renderer et `manifests/renderer-bundle.json` doivent être
adaptés/testés pour les nouveaux shaders ; la copie CMake seule ne suffit pas.
Ne pas modifier un bundle scellé, `content.json`, payload, staging ou archive sans accord dédié.

## 9. Commandes et règles de contrôle

Préflight de chaque lot : `git status --short`. Préserver les changements hors périmètre.
Après édition de code, préparer seulement le plan des fichiers réellement modifiés, par exemple :

```powershell
python pipeline/scripts/test_changed.py --targeted `
  --path engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_filter.cpp `
  --path engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/config.cpp
```

Demander le choix **tests ciblés / tous les tests / aucun test** avant exécution.
Après choix ciblé, reprendre exactement les mêmes `--path` avec `--run`.
Lire [TEST_SELECTION](../../docs/TEST_SELECTION.md) ; ne pas élargir un lot ciblé au worktree entier.
Le nouveau script de transaction doit avoir son test directement associé dans ce routage.

Build Windows de développement après choix autorisant les builds/tests, depuis `ENGINE` :

```powershell
cmake -S . -B cmake-build-catmull-rom -G "Visual Studio 17 2022" -A x64 `
  -DIEE_BUILD_WINDOWS_DLL=ON -DBUILD_TESTING=ON
cmake --build cmake-build-catmull-rom --config Release --target InfinityEngine-Enhancer iee_tests
ctest --test-dir cmake-build-catmull-rom -C Release -R '^iee_tests$' --output-on-failure
```

Cet exemple construit et teste `iee_tests` seulement ; si le plan moteur contient d'autres
exécutables de tests, employer les commandes exactes générées par le sélecteur. CMake ≥ 3.28 requis
pour la DLL ; C++20. `release_bundle` assemble un bundle et n'est pas requis pour chaque itération.

Documentation seule : aucun test Python ciblé applicable. Aucune projection à reconstruire pour ce
guide ni pour un essai d'affichage indépendant. Installation et QA ne valent pas intégration release.

## 10. État de reprise à maintenir

- [x] Sources moteur/installation et shaders BIF inspectés en lecture seule.
- [x] Frontière différée corrigée ; appel final `glDrawArrays` identifié hors jeu.
- [x] Guide et chemins de développement définis.
- [x] D0 : autorités relues ; run `d0-20260909-native-shaders`, six shaders bruts, hashes et snapshot INI créés.
- [x] D1 : développement committé `843aa38`, confirmé terminé par l'utilisateur ; résultat d'exécution des tests non attesté dans la notice consultée.
- [x] D2 : contrat suite figé ; huit fragments linkés, draws observés pour `fpDraw`, `fpTone`, `fpFONT`, `fpSEAM`, `fpYUV` ; `fpSprite`, `fpSELECT`, `fpYUVGRY` restent linkés sans draw attesté et sont planifiés D6–D10.
- [x] D3 : huit shaders neutres et master off/on testés ; huit programmes linkés sans erreur,
  A/B ingame neutre et transactions renderer/shaders restaurées.
- [x] D4 : registre/routage/uniformes dynamiques et propagation d'occlusion validés. Le chemin réel
  `fpDraw` route une sortie d'occlusion créature x2 en mode 2 avec texels physiques ; 28 témoins
  `fpDraw` restent neutres, sans fuite ni erreur shader. Tests non exécutés par choix utilisateur.
- [x] D5 : filtre GPU 16 lectures implémenté sur `fpDraw`, `fpSprite` et `fpSELECT` ; DLL Release
  construite, candidat installé et activation `fpDraw` attestée ingame. Aucun bug/crash ; différence
  visuelle non évidente, sans sélection esthétique requise. Tests non exécutés par choix utilisateur.
- [x] D6 : profil `CreatureHD`, Gaussian/sharpen, colorimétrie et contours implémentés ; profil retenu
  Catmull–Rom + `Sharpen=-0.35`, couleurs neutres, contour natif. Tests non exécutés par choix utilisateur.
- [ ] D7 : candidat installé ; x2 `CreatureHD` validé, mais aucun draw `fpSprite`/`fpSELECT` observé.
- [ ] D8–D10 : toutes les fonctions/paramètres amont restants portés et vérifiés par domaine.
- [ ] D11 : candidat complet installé ; couverture des options et dix presets consignée.
- [ ] D12 : optimisation disponible et coût mesuré ; A/B équivalent.
- [ ] D13 : profil final validé ingame et éventuelle intégration release décidés.

Résultat D2 : run [`d2-20260909-shader-suite-capture`](runs/d2-20260909-shader-suite-capture/),
preuve [`evidence.json`](runs/d2-20260909-shader-suite-capture/evidence.json). Six sources BIF
supplémentaires et sources linkées hashées ; préambule confirmé. Les essais 1/2 ont isolé puis corrigé
un dispatch GL inter-contextes et une sonde non bornée. L'essai 3 est fluide/stable avec « Nearest
Neighbour Scaling » activé puis désactivé, selon confirmation utilisateur. Aucun test exécuté par
choix utilisateur ; cible DLL Release compilée. Les trois transactions sont restaurées ; DLL/INI et
options natives initiales vérifiées. D0/D1 inchangés ; aucune projection ni intégration release.

Résultat D3 : run [`d3-20260909-neutral-shader-suite`](runs/d3-20260909-neutral-shader-suite/),
preuve [`evidence.json`](runs/d3-20260909-neutral-shader-suite/evidence.json). Les huit programmes
fragment sont linkés sans erreur ; l'A/B statique off/on est identique à 99,9985 % après capture
JPEG. Les tests D3, release et moteur Debug/Release passent. La suite Python globale conserve dix
échecs hors D3 consignés dans la preuve. Renderer puis shaders ont été restaurés ; aucune projection
ni intégration release.

Résultat D4 : run `d4-20260910-fpdraw-routing`, preuve locale `evidence.json`. DLL Release du commit
`74cb5e5` compilée et candidat installé. QA visuelle utilisateur réussie ; anomalie d'aggro fermée
comme effet d'un objet d'invisibilité. Trace : créature masquée `43x47`/`86x94`, échelle x2,
`mode=2`, texels `1/86 x 1/94` ; 28 témoins `fpDraw` en mode 0 ; aucune fuite de routage.

Résultat D5 : run `d5-20260910-catrom-reference`, preuve locale `evidence.json`. DLL Release et huit
shaders installés ; `fpDraw`, `fpSprite` et `fpSELECT` sont linkés avec le contrat D5. La trace réelle
`fpDraw` active `mode=2` sur une créature xBR x2 (`23x70` logique, `46x140` physique, texels physiques
`1/46 x 1/140`) ; 42 témoins `fpDraw` restent en mode 0, sans erreur shader/OpenGL. L'utilisateur
confirme l'absence de bug/crash ; la différence visuelle n'est pas évidente, ce qui ne constitue pas
une sélection esthétique D5. Tests non exécutés par choix utilisateur ; candidat restauré avant D6.

Implémentation D6 : configuration typée `[ShaderSuite.CreatureHD]`, références CPU séparées,
profil au draw conditionné par provenance x2/x4, onze uniforms, Gaussian 4×4 partagé avec D5,
contour logique issu d'un voisinage 6×6, pipeline couleur et générateur déterministe des trois
shaders créature. Source Dshaders 0.3.5 épinglée et licence MIT conservée. D7 non commencé.

Installation D6 : tests non exécutés par choix utilisateur ; validation hors ligne BG2EE 2.7.3 et
build Release réussis. Profil de diagnostic combiné : sRGB linéaire, sharpen `+0.50`, gamma `1.02`,
contraste `1.10`, luminosité `+0.05`, saturation `1.20`, teinte `+5°`, contours Dshaders `2/3.5`.
Les huit shaders et le renderer sont installés et revérifiés ; reçus copiés dans
`runs/d6-20260910-creature-hd-style/{shader,renderer}-transaction/`. Session AR0602 : trois témoins
`fpDraw` HD x2 actifs, 31 témoins neutres, aucune erreur shader/OpenGL et aucun crash. Les captures
montrent un rendu trop dur/sombre avec contours noirs ; le profil combiné doit être ajusté avant
acceptation. Aucune intégration release engagée.

Profil D6 doux : run `d6-20260910-creature-hd-soft`. Le candidat combiné précédent a été restauré
et vérifié avant installation. DLL et shaders inchangés ; INI réglé sur espace stocké, Gaussian léger
`Sharpen=-0.25`, couleurs neutres et `OutlineMode=Native`. Nouveau candidat installé et revérifié ;
deux témoins `fpDraw` HD x2 actifs, 22 témoins neutres et aucune erreur shader/OpenGL. L'utilisateur
juge le rendu « vraiment propre » et valide le profil. D6 terminé ; D7 non commencé, aucune intégration
release engagée.

Affinage post-validation : `Sharpen=-0.50` rejeté au profit de `-0.25`, puis compromis `-0.35`
retenu par l'utilisateur. Run courant `d6-20260910-creature-hd-soft035`, candidat installé et reçu
vérifié. La session charge le profil exact, atteste 24 remplacements `0xE400` et aucune erreur ; la
fenêtre de trace ne contient aucun draw style actif après 14 témoins neutres. Cette limite est
consignée sans réinterprétation ; la preuve technique D6 reste la session `-0.25`.

Implémentation D7 : profils typés `[ShaderSuite.fpSprite]` et `[ShaderSuite.fpSELECT]`, portée x1
conditionnée par le programme fragment et `IEE_SPRITE_SCOPE_CONTRACT_V1`, paramètres `Filter`,
Gaussian/couleurs/contours indépendants et texels issus du stockage GL lié. Une texture catalogue
connue conserve exclusivement le mode D1 ; `CreatureHD` gagne en bloc, puis le profil du shader ne
fournit que le style si `CreatureHD` est désactivé. Capacité de registre dépassée, stockage incohérent
ou Catmull–Rom x1 sans sampler NEAREST : repli neutre. `fpDraw` reste limité au chemin créature HD
réel. D6 `soft035` a été restauré et vérifié avant l'installation transactionnelle du candidat
`d7-20260910-sprite-scope-upstream`. Build Release et validation offline 2.7.3 réussis ; tests non
exécutés par choix utilisateur. Reçus D7 installés vérifiés. Session `19:25:28–19:27:34` : 93 draws
tracés, dont trois `fpDraw/CreatureHD` x2 actifs et 90 neutres ; zéro bind/draw `fpSprite` ou
`fpSELECT`, aucune erreur shader/OpenGL. L'utilisateur valide le rendu x2 mais ne voit aucun effet
sur x1. Les deux programmes sont linkés avec le contrat D7 mais non utilisés dans la scène ; D7
reste incomplet et son extension x1 ne doit pas être déclarée opérante. D8 et release non commencés.
