# Pipeline de rendu BG2EE — état de connaissance

Statut : référence vivante du chantier graphique. Dernière vérification : 2026-09-09 (D3 terminée ;
huit overrides linkés, A/B neutre vérifié, transactions restaurées).

## Règle de maintenance

- Mettre à jour ce document seulement lorsqu'une décision finale réutilisable du chantier
  Catmull-Rom / suite shaders doit être conservée.
- Ne documenter comme **confirmé** qu’un comportement lisible dans le code, un shader archivé ou une preuve de test identifiée.
- Marquer **hypothèse** lorsqu’une interprétation reste plausible mais non prouvée ; marquer **à vérifier** lorsqu’aucune preuve ne permet encore de conclure.
- Les runs et leurs `evidence.json` restent les preuves immuables ; ce document les indexe, sans les remplacer.

## Périmètre et niveaux de preuve

| Marque | Sens |
|---|---|
| Confirmé | Code courant, source shader archivée ou test/run référencé. |
| Observé | Trace d’un test précis ; ne généralise pas aux scènes non testées. |
| Prévu | Contrat ou plan accepté, pas encore implémenté. |
| À vérifier | Information manquante ou résultat non attesté. |

Périmètre actuellement prouvé : BG2EE 2.7.3.0 Windows x64, `BaldurReal.exe` SHA-256 `B51093…4D57`, backend OpenGL (renderer alternatif désactivé lors du run D2). Les adresses et capacités effectives restent sous `engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/build_manifest.*`; une identité d’exécutable inconnue échoue fermée.

## Architecture concernée

### Vue d’ensemble

**Confirmé — pipeline sprite xN IEE actuel**

```text
BAM/cycle/frame résolu par le moteur
  -> scope propriétaire IEE (Character / Monster / MonsterIcewind)
  -> snapshot de palette CVidPalette::Realize + frame correspondante du registre xN
  -> texture RGBA privée IEE x2/x4, géométrie logique x1 conservée
  -> CVidCell::RenderTexture détourné ; texture de remplacement liée
  -> commandes Draw* moteur différées
  -> DrawFlush_GL / glDrawArrays ; programme GL lié par BG2EE
  -> blending framebuffer / affichage
```

- `hooks.cpp` intercepte `CVidCell::RenderTexture` dans une scope créature ; il lie une frame Monster/MonsterIcewind ou compose les couches Character, puis appelle l’original exactement une fois.
- Le moteur conserve les coordonnées et dimensions logiques x1. La texture backing IEE est x2 ou x4 ; cette dissociation est la base du rendu HD actuel.
- La sélection d’une frame dépend du resref, cycle et frame effectivement lus sur le `CVidCell`, puis du registre catalogue xN. Toute divergence de propriétaire, ressource, palette, dimensions, contexte ou API provoque un fallback natif.
- Les commandes `Draw*` sont différées : entourer l’appel C++ à `RenderTexture` d’un changement d’uniforme ne couvre pas le draw GL réel. Cette approche a été abandonnée.
- **Observé D2 :** le draw d’une texture composite créature x2 (`logical 52x49`, `physical 104x98`) est passé par `fpDraw`, avec sampler `nearest`.

**À vérifier — pipeline générique du jeu.** Le graphe ci-dessus ne démontre pas que toutes les créatures vanilla, objets au sol, UI, effets et décors suivent la même classe, le même programme ou le même ordre de passes. Les classes hors scopes IEE restent hors de la preuve Catmull-Rom.

### Threads, durée de vie et frontière GPU

**Confirmé :** OpenGL ne peut être touché que sur le thread qui possède le contexte WGL. Chargement de zone, worker éventuel et rendu GL sont séparés. Un changement de contexte invalide noms de textures IEE, classification de programmes et locations d’uniformes.

**Observé D2 :** une table GL globale utilisée entre contextes a causé un crash (`RIP 0`) ; une sonde trop large a rendu le jeu inutilisable. La version D2 retenue borne la sonde au contexte primaire et déduplique les requêtes. Les essais 3 sont fluides avec « Nearest Neighbour Scaling » activé et désactivé.

Conséquence : un futur filtre ne doit pas faire d’I/O, prendre le mutex du catalogue, allouer librement, ni effectuer une introspection GL non bornée dans le hook de draw.

## Ressources BAM et textures sprites

### Chaîne BAM → texture IEE

| Étape | État confirmé |
|---|---|
| Identification | Le hook lit resref, cycle et frame actuels du `CVidCell`. |
| Couleur | `CVidPalette::Realize` fournit un snapshot de 256 couleurs dans l’encodage natif RGBA/BGRA supporté. |
| Source HD | Le registre xN fournit indices et métadonnées de frame ; il n’est pas une lecture directe du BAM original au draw. |
| Frame seule | Les indices xN sont convertis en RGBA physique dans une texture privée IEE. |
| Character | Les couches (jusqu’à 8) sont composées CPU avec les centres BAM ; tout pixel source non transparent écrase la couche précédente, puis une texture transitoire unique est dessinée. |
| Fallback | Échec de validation, dimensions, contexte, rendu non-OpenGL ou texture : dessin BAM natif conservé. |

### Taille, UV et bordures

- **Confirmé :** `CVidCell` réserve un bord transparent logique de 1 pixel autour de la frame BAM. La texture xN garde ce bord : `(largeur_frame + 2) × scale`, idem hauteur.
- **Confirmé :** le contenu est déposé après un décalage physique de `scale` pixels ; la zone initialisée à zéro conserve le bord transparent. Ceci évite de transformer une frame visible seule en bord de texture.
- **Confirmé :** les textures xN créatures sont `GL_CLAMP_TO_EDGE` en S/T, sans mipmaps (`GL_TEXTURE_MAX_LEVEL = 0`).
- **Confirmé :** `vpDraw` calcule `vTc = aTc * uTcScale` et `vRef = aRef * uTcScale`. `uTcScale` appartient au contrat du jeu ; il ne doit pas être réécrit pour adapter le backing xN.
- **À vérifier :** orientation effective des UV, interpolations de sommets et transformations écran/zoom pour chaque chemin de dessin. Seul le code de `vpDraw` est archivé, pas la totalité des appels de géométrie BG2EE.

### Alpha, transparence et risques de bord

- **Confirmé :** la palette/frame xN conserve alpha ; l’entrée transparente est forcée transparente lors de la construction de texture. Les shaders natifs `fpSprite`, `fpSELECT`, `fpDraw`, `fpTone` échantillonnent du RGBA droit (« straight ») puis utilisent l’alpha dans leurs opérations finales.
- **Confirmé :** le Catmull-Rom natif `fpCatRom` ne filtre que RGB et force `gl_FragColor.a = 1.0`; il ne convient donc pas tel quel à un sprite transparent.
- **Confirmé :** le bridge d’occlusion applique un transfert de visibilité pré/post clipping WED sur une texture xN temporaire. Il traite explicitement clear total, alpha réduit et dither noir ; l’extension xN efface aussi le support voisin transparent si un clear complet l’exige.
- **À vérifier :** le mode exact de blend GL pour chaque shader/objet. D2 le trace par draw, mais aucun tableau exhaustif par famille n’est établi.

Risques connus, non encore attribués à Catmull-Rom : halo sombre/coloré (RGB caché sous alpha nul, interpolation droite), bleeding à une bordure, lignes de raccord, contour qui dépasse l’occlusion, scintillement au mouvement/zoom. Aucun de ces défauts ne doit être déclaré « corrigé » par le chantier D0–D2 : aucun shader Catmull-Rom de sprite n’a été exécuté.

## Shaders BG2EE identifiés

Sources natives archivées : `sprite/catmull-rom/runs/d0-20260909-native-shaders/native-shaders/` et `sprite/catmull-rom/runs/d2-20260909-shader-suite-capture/native-shaders/`. Les sources liées (préambule moteur inclus) sont archivées sous `linked-shaders/` du run D2.

| Fragment / vertex | Rôle lu dans le code shader | Textures / données natives | Couverture D2 |
|---|---|---|---|
| `fpSprite` + `vpDraw` | Blur/contour de sprite : noyau gaussien 5×5, puis `mix(blur, texel, alpha)`. | `uTex` RGBA, `uSpriteBlurAmount`, `vTc`, `vColor`. Offsets fixes UV `0.0005`. | Linké ; aucun draw observé. |
| `fpSELECT` + `vpDraw` | Sprite sélectionné/survolé : texel central si alpha > 0,1 ; sinon voisinage 7×7 pour surlignage. | `uTex` RGBA, `uSpriteBlurAmount`, `uTcScale`, `vTc`, `vColor`. | Linké ; aucun draw observé. |
| `fpDraw` + `vpDraw` | Échantillonnage RGBA central, modulation `vColor`, teinte luminance `uColorTone`. | `uTex`, `uColorTone`, `vTc`, `vColor`. | Linké et draws observés, dont une composite créature. |
| `fpTone` + `vpDraw` | Même combinaison teinte/couleur que `fpDraw`. | `uTex`, `uColorTone`, `vTc`, `vColor`. | Linké et draws observés. |
| `fpFONT` + `vpDraw` | Glyphe : canal rouge = couverture alpha, couleur blanche modulée. | `uTex` couverture rouge, `vTc`, `vColor`, `depth`. | Linké et draw observé. |
| `fpSEAM` + `vpDraw` | Atlas de tuiles : interpolation avec garde aux bords noirs des tuiles 64×64, puis teinte. | `uTex` RGBA atlas, `uTcScale`, `uColorTone`, `vTc`, `vRef`, `vColor`. | Linké et draws observés ; override eau IEE actif. |
| `fpYUV` + `vpYUV` | Vidéo opaque : lit Y/U/V dans régions rouge d’une texture packée, convertit YUV→RGB. | `uTex`, `vTc`, `vTcU`, `vTcV`, `vColor`. | Linké et draw observé seulement lors de l’essai D2 en échec. |
| `fpYUVGRY` + `vpYUV` | Vidéo/effet YUV avec alpha séparé, protège les jonctions par epsilon. | `uTex` YUV, `uTex2` alpha rouge, `uColorTone`, varyings YUV. | Linké ; aucun draw observé. |
| `fpCatRom` + `vpBlit` | Filtre de blit Catmull-Rom natif : chemin rapide 9 taps RGB ; référence 16 taps désactivée par `#if 0`; alpha forcé opaque. | `uTex`, `uTcScale`, `uTcClamp`, `uZoomStrength`, `vTc`. | Non linké/non observé dans D2. |

Portées « créatures, objets, UI, décors » : la table donne le rôle déduit du shader et le contrat D2, pas une attribution exhaustive de toutes les instances du jeu. En particulier, `fpDraw` est déjà observé pour une créature composite, mais son usage exact pour objets au sol, cercles de sélection, UI et effets reste à cartographier par scènes ciblées.

## Remplacement et instrumentation des shaders

### Mécanisme actuellement utilisé

- **Confirmé :** BG2EE peut charger un fragment par son nom depuis le répertoire jeu `override/`.
  Les huit fragments D3 ont été installés, linkés puis restaurés par transaction locale.
- **Confirmé :** le bundle CMake copie `assets/override/` dans son répertoire `override`. `shader_probe.cpp` observe `glShaderSource`, compile, link, `glUseProgram`, suppression et — en mode diagnostic D2 — `glDrawArrays`.
- **Confirmé :** les programmes sont nommés depuis le commentaire `// fp…glsl` / `// vp…glsl` de leur source, puis classés après chaque link. Les programmes contenant des uniforms `uIee*` reçoivent les uniforms IEE.
- **Confirmé :** `game/shader_override.cpp` peut vérifier qu’un remplacement conserve les identifiants `uniform`/`varying` déclarés dans la source native. Ce contrôle est structurel : il ne prouve ni compilation pilote ni équivalence visuelle.
- **Validé D3 :** transaction distincte pour les huit fragments de la suite, liste explicite sans
  glob de `override/`, préflight, installation, vérification et restauration autonome exécutés.

### Uniforms IEE actifs aujourd’hui

Le pont `shader_uniform_bridge.*` alimente uniquement les uniforms que le programme lié expose :
`uIeeShaderSuiteEnabled` (D3, défaut 0), `uIeeTime`, `uIeeEnabled`, `uIeeScroll`, `uIeeZoom`,
`uIeeViewport`, `uIeeWorldSizeInv`, `uIeeWaterTint`, `uIeeAreaMask`, `uIeeNormalMap`,
`uIeeDudvMap`, `uIeeFoamMap`. Tous sauf le master D3 servent au shader eau `fpSEAM` actuel ;
ils ne constituent pas le futur contrat dynamique Catmull-Rom.
Le master suit le contrat INI D2 : `[ShaderSuite] Enabled = false` par défaut.

**Prévu, non implémenté :** `uIeeCreatureFilterMode` et `uIeeCreatureTexelSize` pour le chemin Catmull-Rom créature. La taille doit être `1 / (largeur_physique, hauteur_physique)`, pas une taille logique ou une déduction depuis `uTcScale`.

## Sampling et options graphiques

### Textures créatures xN

| `CreatureSpriteFilter` | Sampler backing xN actuel | Shader Catmull-Rom de sprite |
|---|---|---|
| `Nearest` (défaut/QA) | `GL_NEAREST` min/mag | Absent ; chemin natif. |
| `Linear` | `GL_LINEAR` min/mag | Absent ; A/B historique. |
| `CatmullRom` | `GL_NEAREST` min/mag | Absent ; prévu pour une reconstruction explicite 16 lectures. |

- Parsing insensible à la casse ; une valeur invalide revient à `Nearest`. La nouvelle clé prime sur l’ancien booléen `EnableCreatureSpriteLinearFiltering`.
- La valeur `CatmullRom` n’active aujourd’hui aucune reconstruction : elle n’est qu’un mode de configuration/sampler prêt pour D3–D5.
- Le moteur possède aussi une configuration linéaire/mipmap/anisotrope pour les tuiles ; elle ne décrit pas le sampler des textures créatures xN.

### Nearest Neighbor Scaling BG2EE

**Observé D2 :** essais fluides avec l’option activée et désactivée ; les snapshots Lua et logs sont conservés dans le run D2.

**À vérifier :** son point précis dans la chaîne de rendu, son interaction visuelle avec les textures xN et Catmull-Rom, et son effet sur chaque shader. D2 ne valide ni l’absence de différence visuelle ni une méthode de sampling universelle du jeu.

## État Catmull-Rom

### Implémenté

- Configuration `CreatureSpriteFilter = Nearest|Linear|CatmullRom` et tests hôte D1 associés dans le code moteur.
- Textures créatures xN bornées, bordées et étiquetées par trace D2 ; preuve nécessaire pour cibler une texture au draw réel.
- Cartographie des huit interfaces de la suite dans `sprite/catmull-rom/profiles/shader-suite-contract-v1.json`.
- Capture des sources BIF, des sources réellement liées, des programmes et de quelques draws D2.
- D3 source : huit overrides neutres exposent `uIeeShaderSuiteEnabled`; le master INI est désactivé
  par défaut et alimenté par le pont d’uniformes. Les sept nouveaux fragments conservent les
  opérations natives ; `fpSEAM` conserve l’eau IEE et sa voie off antérieure.
- D3 source : transaction shader séparée avec manifeste, hashes, collision insensible à la casse,
  `--verify-only`, rollback et restauration autonome.
- D3 ingame : les huit fragments ont été introspectés dans huit programmes ; aucun échec shader
  observé. La zone statique A/B off/on est identique à 99,9985 % des canaux après capture JPEG
  (écart moyen 0,000028 ; maximum 4). Renderer puis shaders ont été restaurés.

### Non implémenté

- Aucun registre de provenance de production au hook `glDrawArrays` ; `record_creature_texture_trace` D2 est un diagnostic, explicitement pas le registre D4.
- Aucun envoi dynamique de `uIeeCreatureFilterMode` / `uIeeCreatureTexelSize`.
- Aucun Catmull-Rom 16 taps prémultiplié dans un shader de sprite, aucune sélection de draw par provenance, aucune comparaison QA Catmull-Rom.

### Algorithme prévu, non validé ingame

Le contrat D1/D2 prévoit une reconstruction 4×4 (16 lectures) à partir de `vTc`, texel centers et dimensions **physiques**, avec interpolation de RGBA prémultiplié puis retour à alpha droit si nécessaire. Il doit conserver les voisins, seuils et étapes finales natives de `fpSprite`/`fpSELECT` tant qu’une QA ne justifie pas leur modification.

Motifs : le 9-taps natif exploite l’interpolation matérielle et ne correspond pas automatiquement à 16 lectures prémultipliées ; `fpCatRom` force alpha à 1. Les bords doivent utiliser le clamp de la texture complète, sans `fract` ni troncature à la place de `floor`.

## Artefacts, causes et décisions

| Sujet | Fait établi | Décision / état |
|---|---|---|
| Crash D2 essai 1 | Dispatch GL global écrasé par un autre contexte/thread. | Corrigé dans l’essai 3 par bornage au contexte primaire ; ne pas réintroduire d’état GL global. |
| Ralentissement D2 essai 2 | Réinstallations et inférences de slots très nombreuses ; sondes avant déduplication. | Corrigé dans l’essai 3 ; rester borné et mesurer avant d’élargir. |
| Alpha sprite | `fpCatRom` est opaque ; sprites et sélection utilisent alpha. | Rejeter son emploi direct pour sprites transparents. |
| Halo/bleeding potentiel | RGB caché, interpolation RGBA droite et soutien de bord peuvent contaminer une reconstruction. | Prévu : prémultiplier pour les 16 lectures ; à vérifier par A/B, pas encore retenu visuellement. |
| Bord/Crop | Le bord transparent CVidCell est réel et xN doit le conserver. | Retenu dans l’uploader xN actuel ; aucune réduction de bord. |
| Occlusion | Une texture xN masquée peut avoir un sampler `GL_LINEAR` historique. | Prévu Catmull : backing `GL_NEAREST` pour la référence 16 taps, sans changer les autres objets ; à implémenter. |
| Lignes YUV | `fpYUVGRY` limite les coordonnées avec epsilon explicitement pour éviter des lignes de wrap. | Fait shader natif ; toute réécriture doit le préserver. |
| Seam tuiles | `fpSEAM` évite la fuite aux bords noir/64×64 de l’atlas. | Override eau IEE actuel à préserver ; ne pas le confondre avec un shader sprite. |
| Scintillement/mouvement/zoom | Aucun résultat Catmull-Rom. | À mesurer en séquences, jamais par capture fixe seule. |

## Contraintes de performance et moteur

- Le draw natif doit être appelé exactement une fois ; aucune exception ne traverse une frontière hook/ABI.
- Toute entrée inconnue (texture, programme, contexte, ownership, dimensions, capacité) doit désactiver le filtre pour ce draw, sans modifier le fallback natif.
- Pas d’I/O, consultation de catalogue ou mutex créature dans le hook GL final.
- Le coût théorique du socle 16 taps est 16 lectures centrales au lieu d’une ; `fpSprite` garderait en plus son voisinage natif. Le budget suggéré par le plan est médiane ≤ 5 % et pas de dégradation p95 répétée, à fixer sur la machine de référence.
- La provenance doit vivre par `(génération WGL, nom GL)` et survivre jusqu’à la suppression GL réelle ; un nom peut être réutilisé. Ce registre est **prévu**, non livré.
- La texture d’occlusion transitoire et le bridge ont leurs propres contraintes de dimensions/mémoire ; le bridge reste opt-in et hors validation release générale.

## Lessons learned for custom shaders

- Cibler un draw prouvé par programme + sampler + texture propriétaire ; ne jamais classifier un sprite par son ratio x2/x4 seul.
- Séparer la taille logique moteur de la taille physique GL. Calculer les pas de filtre à partir du backing réellement attaché.
- Préserver toutes les interfaces natives (`uniform`, `varying`, coordonnées, seuils et opérations finales) avant toute amélioration esthétique.
- Pour une ressource transparente, filtrer en prémultiplié et restaurer l’alpha de manière définie ; un filtre RGB opaque existant n’est pas réutilisable tel quel.
- Conserver le bord transparent logique et utiliser `CLAMP_TO_EDGE`; les erreurs de bord sont souvent des erreurs de support, pas seulement de formule de filtre.
- Les appels `RenderTexture` ne sont pas la frontière de draw. Les paramètres dynamiques doivent être appliqués autour du `glDrawArrays` effectif, puis remis au chemin neutre.
- Gérer explicitement WGL : contexte recréé = classifications, locations et provenance invalides.
- Les sondes GL doivent être ciblées, dédupliquées et sans verrou partagé autour de GL. D2 a démontré qu’une sonde correcte fonctionnellement peut être instable ou inutilisable.
- Évaluer le résultat après blending, sélection, occlusion, zoom et mouvement. Un screenshot fixe ne valide ni l’alpha ni la stabilité temporelle.
- Garder `Nearest` disponible comme témoin neutre et ne pas promouvoir un shader/asset à partir d’une installation d’essai restaurée.

## Known unknowns

- Quel programme BG2EE dessine chaque famille : créatures vanilla, Character multicouche, Monster, objets au sol, cercles de sélection, UI, portraits, effets, décors et overlays ?
- Dans quelles scènes `fpSprite`, `fpSELECT` et `fpYUVGRY` produisent-ils réellement un draw en 2.7.3 ?
- Quel est le mode de blend, framebuffer et espace couleur effectif pour chaque famille de draw ?
- Quelle est l’influence exacte de « Nearest Neighbour Scaling » sur le pipeline, les UV, le zoom et les samplers ?
- `uTcScale` représente-t-il exactement `1 / dimensions_logiques` pour tous les programmes/draws observés ? Le rapport prévu `texelSize = uTcScale / scale` reste à confirmer.
- Comment le jeu choisit-il tous ses shaders et quelles variantes ne sont pas présentes dans les huit cibles D2 ?
- Les textures de créatures passent-elles systématiquement par `fpDraw` dans les scènes réelles, ou le passage observé D2 est-il une variante limitée ?
- Quel comportement final de l’alpha Catmull-Rom et quel seuil/contour sont acceptables sur sprites, sélection et occlusion ?
- Quelles optimisations (9 taps, taps groupés, espace couleur) sont équivalentes au 16 taps prémultiplié requis ? Aucune ne doit être supposée équivalente.
- Quel budget GPU/CPU mesuré est acceptable sur la machine de référence et en scène de combat ?

## Fichiers de reprise

| Chemin | Rôle |
|---|---|
| `sprite/catmull-rom/README.md` | Plan D0–D13, décisions et protocole Catmull-Rom. |
| `sprite/catmull-rom/DSHADERS_SUITE.md` | Contrat détaillé de la suite D2–D13 et matrice QA prévue. |
| `sprite/catmull-rom/profiles/shader-suite-contract-v1.json` | Autorité des huit interfaces, paramètres, presets et profils. |
| `sprite/catmull-rom/runs/d0-20260909-native-shaders/evidence.json` | Provenance/hashes des six sources natives initiales. |
| `sprite/catmull-rom/runs/d2-20260909-shader-suite-capture/evidence.json` | Programme/draw coverage, essais D2, hashes et restauration. |
| `sprite/catmull-rom/runs/d3-20260909-neutral-shader-suite/evidence.json` | Candidat D3, tests, link des huit programmes, A/B neutre et restaurations. |
| `engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp` | Scopes propriétaires et détournement `CVidCell::RenderTexture`. |
| `engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.*` | Registre xN, palette, composition, upload, bord et sampler créature. |
| `engine/InfinityEngine-Enhancer/source-patchee/src/iee/shader_probe.cpp` | Hooks GL, classification/link, diagnostic de draws et contexte. |
| `engine/InfinityEngine-Enhancer/source-patchee/src/iee/shader_uniform_bridge.*` | Uniforms eau et master neutre D3. |
| `engine/InfinityEngine-Enhancer/source-patchee/tools/install_shader_suite_candidate.py` | Préparation et transaction des huit shaders D3. |
| `engine/InfinityEngine-Enhancer/source-patchee/docs/shader-suite-candidate-transaction.md` | Commandes, frontières et ordre de restauration D3. |
| `engine/InfinityEngine-Enhancer/source-patchee/assets/override/` | Huit overrides D3 ; `fpSEAM` conserve l’eau IEE. |
| `engine/InfinityEngine-Enhancer/source-patchee/docs/threading-model.md` | Contraintes WGL, threads, hooks et shutdown. |
| `engine/InfinityEngine-Enhancer/source-patchee/docs/native-occlusion-phase1.md` | Bridge WED pré/post clipping et alpha xN. |

## Development history

| Phase | Résultat conservé |
|---|---|
| Avant D0 | Pipeline sprite xN IEE : remplacement de backing, géométrie x1 et fallback strict ; bridge d’occlusion séparé. |
| D0 — 2026-09-09 | Extraction/hash des shaders BIF de référence et snapshot de l’état local ; aucune installation. |
| D1 | Ajout du mode `CreatureSpriteFilter`, protections `Nearest`, contrat dimensions/bord/sampler. Le résultat d’exécution des tests D1 n’est pas attesté dans les preuves consultées. |
| D2 — 2026-09-09 | Capture des huit interfaces cibles, sources liées et draws ; correction du problème inter-contextes/sondes ; essais fluides nearest on/off. Aucun override de suite ni Catmull-Rom sprite. |
| D3 — 2026-09-09 | Huit overrides neutres et master off/on testés ingame ; huit programmes linkés, A/B neutre et transactions restaurées. Gates D3/release/engine vertes ; suite Python globale rouge sur dix contrôles hors D3 consignés dans le run. |
| Prochaine phase | D4 uniquement : registre propriétaire, hook draw effectif, uniforms dynamiques, nettoyage et fallback. D5+ ne sont pas commencées. |

## Mise à jour suivante

Ajouter à la fin de la prochaine phase : commit et run, hashes des fragments modifiés, interface réellement linkée, programmes/draws attestés, textures/samplers/UV observés, conditions de test, artefacts vus ou absents, mesures de performance, restauration effectuée et décision QA explicite. Ne jamais remplacer les entrées D0/D2 scellées.
