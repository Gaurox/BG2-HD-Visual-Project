# Catmull–Rom pour sprites HD — guide de développement

Statut : **plan vérifié, implémentation non commencée**. Dernière vérification : 2026-09-09.
Public : agent IA reprenant le développement sans historique de conversation.

## 1. Mission et reprise

Intégrer à InfinityEngine Enhancer un filtrage Catmull–Rom des textures de créatures HD x2/x4,
sur BG2EE Steam 2.7.3.0 Windows x64. Réduire les marches de pixels au zoom sans le flou excessif
du réglage graphique global. Conserver géométrie x1, palettes, équipement, cadence et sauvegardes.

- MVP : reconstruction 4×4 / 16 lectures, alpha traité en prémultiplié, activation opt-in.
- Entrées : catalogue de sprites existant ; aucune nouvelle génération xBR requise.
- Cibles primaires : `fpSprite` et `fpSELECT`. Vérifier leur couverture réelle avant de figer
  la liste des shaders installés ; certains états peuvent employer `fpDraw`.
- Activation : texture appartenant explicitement au module créatures, au **dessin OpenGL effectif**.
- Exclusions : cartes, animations de zone, sorts, UI, cercles de sélection indépendants,
  post-traitement global, modification de `fpSEAM`, remplacement global par Dshaders.
- `Nearest` reste le défaut et la référence QA. Aucun rendu Catmull–Rom n'est encore approuvé.

Lecture de reprise : [AGENTS](../../AGENTS.md), [README projet](../../README.md),
[README sprites](../README.md), [décisions](../../docs/DECISIONS.md),
[blocages](../../pipeline/PROBLEMES_A_RESOUDRE.md), puis ce guide.
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

`FEATURE` porte le guide et les futurs essais de cette fonction transversale aux familles.
Le code exécutable reste sous `ENGINE` ; aucune copie moteur sous `sprite/`.
Arborescence prévue, créer les sous-dossiers seulement au besoin :

```text
sprite/catmull-rom/
  README.md                         # présent guide, suivi Git
  runs/<run-id>/                    # captures/preuves/candidats immuables, déjà ignorés par Git
    native-shaders/                 # octets extraits des BIF, non redistribués comme sources projet
    linked-shaders/                 # sources réellement soumises au pilote
    candidate/                     # DLL/INI et payload shader séparés selon les transactions
    captures/
    evidence.json                  # provenance, capacités, paramètres, mesures, reçus
```

## 2. Résultat de la dernière vérification

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

État local observé : seul `override/fpSEAM.glsl` présent ; aucun `iee-shader-dumps/`.
Catalogue actif : `CATALOG/current-generation.json` et `CATALOG/ingame-installation/active-test.json`.
Génération observée `D55EFD6D1B342B1240AC2BBD222BC088B38F86D4503E6F46B03CB447A704B8F2` ;
xBR2x, x2, `antialias=false`, `xbr_blend=false`, `sampling=NEAREST` ;
animations `0x6102`, `0x6110`, `0xE400` ; `installed-pending-qa`. Relire les autorités à la reprise.

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
| `fpDraw` | Lecture centrale, modulation `vColor`, teinte `uColorTone`. Candidat seulement si le traçage prouve qu'il dessine des créatures cibles. |
| `fpCatRom` | Filtre de blit opaque ; ne reconstruit pas un alpha de sprite. Conserver son chemin natif. |

Première variante GPU : remplacer uniquement la lecture centrale dans les deux shaders cibles.
Conserver voisins, seuils et opérations finales natifs. La reconstruction prémultipliée en amont
ne prouve pas à elle seule la qualité de l'alpha final : les deux shaders mélangent à nouveau
avec cet alpha. Tester le résultat après blending avant de modifier ces opérations.

### 3.3 Dshaders : référence limitée

Révision épinglée : `4722673a8017c56ace4018b3db459392ecbb75a4` ; version annoncée 0.3.5.

- [README / prérequis 2.6](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/drunkshaders/readme.txt).
- [Fonctions GLSL / `uhFetchCatmullRom`](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/drunkshaders/glsl-parts/functions-game.glsl).
- [Licence MIT](https://github.com/dtiefling/dshaders/blob/4722673a8017c56ace4018b3db459392ecbb75a4/LICENSE).

Retenir les mathématiques 4×4, pas le remplacement global : Dshaders modifie aussi les contours,
la colorimétrie et les shaders de cartes. Son quadrillage tiré de `1/uTcScale` correspond aux
dimensions logiques ; il ne connaît pas notre backing HD. Ses exigences sur le réglage natif
Nearest ne constituent pas un contrat pour cette nouvelle implémentation. Si du code est repris,
conserver attribution et licence ; aucune dépendance runtime au mod n'est nécessaire.

## 4. Architecture de référence

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

### 4.3 Contrat INI et GLSL proposé

Clé sous `[Shaders]` :

```ini
CreatureSpriteFilter = Nearest
```

| Valeur | Enum proposé | Texture créature | Filtre shader |
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

`epsilon` proposé : `1e-6`, à fixer et tester. Ne pas borner séparément les sommes intermédiaires
horizontales ; borner après accumulation complète. Les poids négatifs sont normaux : les clamps
bornent les valeurs, sans garantir l'absence de ringing perceptible.

Variante initiale : espace des valeurs stockées (`GL_RGBA8`), coût réduit et comparaison native
directe. Variante expérimentale secondaire : conversion sRGB exacte vers lumière linéaire avant
prémultiplication, inverse après division. Ne pas gamma-corriger l'alpha ; vérifier l'état
`FRAMEBUFFER_SRGB`/format de destination avant de revendiquer une chaîne linéaire correcte.
Choisir une variante après QA ; aucune option colorimétrique publique supplémentaire dans le MVP.

Un Catmull–Rom local n'est pas un filtre de réduction d'échelle complet. Au zoom arrière,
tester scintillement et moiré ; ne pas ajouter d'emblée mipmaps, sharpening ou filtre plein écran.

## 5. Carte du code à modifier

Tous les chemins suivants sont relatifs à `ENGINE`, sauf indication contraire.

| Fichier/module | Intervention prévue |
|---|---|
| `src/iee/core/config.h/.cpp` | Enum, nouvelle clé, priorité legacy, sérialisation. |
| `src/iee/dll_main.cpp` | Initialiser le mode ; appel actuel à `configure_linear_filtering`. |
| `src/iee/creature_sprite_x2.h/.cpp` | Samplers, publication d'identité après `upload_frame_locked`/`upload_composite_texture_locked`, renouvellement du cache. |
| `src/iee/hooks.cpp` | `detour_vid_cell_render_texture` : corréler propriété et éventuelle sortie d'occlusion ; pas de portée shader limitée à cet appel. |
| `src/iee/native_occlusion_bridge.h/.cpp` | Propager les métadonnées de l'entrée créature vers la sortie ; sampler de sortie adapté au mode 2 seulement. |
| Nouveau `src/iee/creature_sprite_filter.h/.cpp` | Registre de textures, état effectif du draw et contrôle de capacité. Séparer les fonctions pures testables si nécessaire. |
| `src/iee/shader_probe.cpp` | Hook `glDrawArrays`, cycle de vie upload/delete, classification, preuves compile/link, invalidation de contexte/programme. |
| `src/iee/shader_uniform_bridge.h/.cpp` | Locations des uniformes, alimentation statique et dynamique séparées ; aucune réutilisation de `uIeeEnabled`. |
| `src/iee/game/opengl_types.h/.cpp` | Déjà `glDrawArrays` ; compléter seulement les requêtes GL nécessaires au contrat effectif. |
| `src/iee/game/shader_override.*` | Renforcer si besoin le contrôle de déclarations : l'actuel vérifie essentiellement la présence de noms, pas toute l'interface typée. |
| Nouveaux `assets/override/fpSprite.glsl`, `fpSELECT.glsl` | Sources natives adaptées, entrée cubic unique, branche désactivée identique. |
| `tools/InfinityEngine-Enhancer.sample.ini` | Nouvelle clé et portée documentées. |
| `tests/iee_tests.cpp` et tests dédiés éventuels | Configuration, maths, contrats, cycle de vie du filtrage. |
| `CMakeLists.txt` | Ajouter sources/tests. La copie du dossier `assets/override` existe déjà ; cela ne met pas à jour les manifests de release. |
| Nouveau `tools/install_sprite_shader_candidate.py` | Transaction des seuls shaders retenus après traçage ; contrat ci-dessous. |
| `pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1` | Éviter qu'une nouvelle clé Catmull persistante contourne l'assertion historique du baseline NEAREST. |
| `pipeline/tests/` et `pipeline/scripts/test_changed.py` | Tests de transaction, migration INI et routage ciblé du nouveau script. |

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
| D2 — Capture et traçage | Dump pilote et trace bornée `glDrawArrays` pour les sprites cibles, sélection, zoom et options natives. | Préambule, unité `uTex`, dimensions, blend, type de draw et liste des shaders à couvrir connus. |
| D3 — Overrides neutres | Sources dérivées 2.7.3, contrôles d'interface et nouveaux uniformes ; mode désactivé. | Compile/link ingame réussi ; A/B neutre sur scène identique. |
| D4 — Routage texture | Registre propriétaire, hook draw effectif, uniformes dynamiques, sortie d'occlusion, nettoyage et fallback. | Créature HD détectée même après retour de RenderTexture ; témoins hors périmètre jamais marqués. |
| D5 — Filtre GPU | 16 lectures, coordonnées physiques, alpha ; remplacement central seulement. | Référence CPU/GPU cohérente ; pas de décalage ; résultat ingame exploitable. |
| D6 — Transactions/QA | Installer/restaurer candidat avec reçus ; exécuter la matrice visuelle et les tests choisis. | Résultats et défauts attribuables à un tuple DLL/INI/shaders/catalogue précis ; restauration vérifiée. |
| D7 — Performance | Mesures CPU/GPU en scène chargée ; optimisation uniquement si utile. | Coût documenté, aucune perte de filtrage en texture/cache/context switches. |
| D8 — Validation/promotion | Décision ingame explicite ; documentation finale ; demande d'intégration release distincte. | Preuve `validated-installed` seulement si acceptée ; sélection release seulement après accord spécifique. |

D1 peut avancer avant le passage ingame D2. Pour les essais D2–D5 nécessitant une DLL installée,
employer dès le premier candidat la transaction renderer existante. Dès D3, les nouveaux overrides
exigent aussi la transaction shader ; ne pas attendre D6 pour sécuriser leur installation.

### D2 : protocole minimal de capture

1. Fermer jeu et InfinityLoader avant changement de fichiers. Conserver l'INI exact et les hashes
   des éventuels overrides ; `fpSEAM` reste installé.
2. Préparer un candidat INI fusionné avec `[Shaders] DumpEngineShaders=true` et
   `[Core] VerboseLogs=true`. Ne pas remplacer l'INI partagé par le sample.
3. Pour la capture native, aucun override des shaders cibles. Archiver un dump préexistant avant
   relance : `dump_shader_source` ouvre les fichiers en mode troncature.
4. Charger une sauvegarde avec groupe visible ; créature normale, sélection/survol, déplacement ;
   invisibilité/flou si disponible. Relever programmes et textures, pas seulement les sources.
5. Capturer séparément « Nearest Neighbor Scaling » activé/désactivé, zooms identiques ; redémarrer
   si nécessaire. `Alternate Renderer` désactivé pour la cible OpenGL.
6. Vérifier dans `GAME/iee-shader-dumps/` au minimum `fpSprite`, `fpSELECT`, `vpDraw` ; conserver
   aussi `fpDraw`, `fpCatRom`, `vpBlit` s'ils sont dumpés. La sonde balaie les programmes préexistants
   à la frontière de frame et introspecte ceux utilisés plus tard.
7. Archiver sources linkées et logs ; vérifier les hashes et la présence du préambule. Le dump
   contient les sources attachées actuelles, y compris un override éventuel : son nom ne prouve
   pas son origine native. Restaurer les options de diagnostic après collecte.

Trace GPU minimale bornée : contexte/programme/type de shader, texture et unité `uTex`, dimensions
logiques/physiques, provenance, min/mag filter, viewport/FBO, paramètres de blending, options/zoom.
Si un programme cible manque, vérifier le traçage et le log ; ne pas essayer tous les sprites.
Si `fpDraw` est nécessaire pour une situation contractuelle, ajouter un override avec le même
contrôle propriétaire, puis élargir explicitement la liste exacte de la transaction et ses tests.

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

Tests des maths et du registre sans contexte GL dans une cible isolée si possible. Les tests de
présence de chaînes ne remplacent ni un test de comportement ni la compilation réelle du pilote.
Pour un shader manquant, tester le repli ; pour une erreur de compilation, tester la récupération
par restauration sans prétendre que l'uniforme zéro peut réparer un programme non lié.

### 7.2 QA visuelle

Variantes : baseline `Nearest`, témoin `Linear`, Catmull–Rom espace stocké ; lumière linéaire
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
modifié. Captures fixes appariées et séquences temporelles : une seule image ne valide pas la marche.

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
- Coût théorique : 16 lectures centrales au lieu de 1 ; les voisins natifs restent inchangés.
  `FPSPRITE` passe ainsi de 26 à 41 lectures source dans sa forme non optimisée, pas à 26×16.
- Priorité : pas d'I/O/allocation/catalogue dans le hook ; locations et classification mises en
  cache ; écritures d'uniformes évitées si la valeur du **draw** est inchangée ; ensuite code GLSL.
- Préférer le shader 16 lectures tant que le budget est tenu. Le 9 lectures natif regroupe des
  voisins via interpolation matérielle LINEAR. Appliqué à RGBA droit, puis prémultiplié après
  lecture, il n'est pas équivalent au filtre 16 lectures prémultipliées. Même contrainte pour
  une conversion sRGB après interpolation. Une optimisation 9 lectures exige un stockage/sampler
  adapté et une preuve d'équivalence ; elle n'est pas un remplacement direct.

## 8. Installation, suivi et release

### 8.1 Candidat de développement

Référence obligatoire : [transaction renderer](../../engine/InfinityEngine-Enhancer/source-patchee/docs/renderer-candidate-transaction.md).
Elle possède exactement DLL + INI ; conserver ce contrat. La transaction shader séparée doit avoir :

- liste exacte des fichiers retenus en D2, initialement `override/fpSprite.glsl` et `override/fpSELECT.glsl` ;
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

Attention au catalogue : son installateur force seulement l'ancienne clé LINEAR à faux aujourd'hui.
Une nouvelle clé prioritaire laissée à `CatmullRom` invaliderait la promesse NEAREST du test.
Adapter sa gestion des clés/reçus lors du développement ; ne pas relancer un install/restore du
catalogue pendant une transaction Catmull active. Restaurer les expérimentations dans l'ordre inverse.

### 8.2 Preuve et promotion

Chaque `evidence.json` doit identifier : schema/version, run, commit+diff source, cible EXE,
hashes BIF/bruts/linkés, DLL/INI/shaders, génération catalogue, GPU/pilote/GL/GLSL,
options natives, mode demandé/effectif, variantes/captures, tests exécutés ou non, mesures,
reçus install/restore et décision QA utilisateur. Pas de hash/succès fictif.

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
- [ ] D0 : run de développement et snapshots créés.
- [ ] D1 : référence CPU/configuration implémentées.
- [ ] D2 : préambule et dispatch GPU observés en jeu.
- [ ] D3–D5 : shaders neutres, routage et filtre implémentés.
- [ ] D6–D7 : transactions, tests choisis, QA et coût mesurés.
- [ ] D8 : validation ingame et éventuelle intégration release décidées.

Prochaine action d'un agent chargé d'implémenter : relire Git/autorités, créer le run D0, extraire
les sources BIF et commencer D1. Préparer ensuite le candidat diagnostic D2 pour une courte session
ingame. Ne pas reprendre l'ancienne idée de portée shader autour du seul `RenderTexture`.
