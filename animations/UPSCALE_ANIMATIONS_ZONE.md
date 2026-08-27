# Upscale des animations de zone BAM — procédure LLM

## Statut et périmètre

- Preuve initiale validée : `AM0205E`, dans `AR0205`, position monde `(1661, 1387)`.
- Référence générique validée en jeu le 2026-08-20 : les 13 BAM / 219 frames de `AR0602` via un
  registre unique, dont `AM0602AA/AB/AC`, `BUBBLES2` et `FLAME2S` à géométrie variable.
- Build validé : BG2EE `2.7.3.x`, rendu OpenGL.
- Résultat validé : pixels physiques x4, taille écran x1, ancrage et cadence inchangés.
- Interpolation temporelle validée le 2026-08-21 : `AM0205E` étendu à 27 frames runtime sur les
  27 positions de son cycle natif. Procédure :
  [`../pipeline/ANIMATION_INTERPOLATION_PIPELINE.md`](../pipeline/ANIMATION_INTERPOLATION_PIPELINE.md).
- Timeline runtime validée le 2026-08-23 : `PORTL1A` conserve son cycle natif de 6 positions à
  15 fps et affiche 12 phases à 30 fps. Procédure V2 séparée :
  [`../pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](../pipeline/ANIMATION_UPSCALE_30FPS_V2.md).
- Implémentation de production :
  `engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_animation_x4_registry.*`, hooks dans
  `src/iee/hooks.cpp`, adresses dans `src/iee/game/build_manifest.*`.
- L'ancien hook ciblé du prototype `AM0205E` reste une preuve historique, pas le chemin à dupliquer.
- Cette procédure vise les animations de décor déclarées dans une ressource `ARE` et rendues par
  `CGameStatic::RenderBam`. Elle ne couvre pas automatiquement les créatures, les effets, l'UI ou
  les overlays liquides.

## Invariants obligatoires

1. Ne jamais remplacer le BAM x1 par un BAM dont les dimensions de frames sont multipliées : le
   moteur agrandirait l'objet à l'écran.
2. Conserver séparément RGB et alpha. SeedVR ne traite que le RGB.
3. Agrandir l'alpha source avec `nearest-neighbour`; ne jamais générer l'alpha avec le modèle.
4. Pour chaque frame, conserver les dimensions logiques, le centre BAM, le cycle et le timing x1.
5. Déclarer la texture au moteur avec les dimensions logiques x1, puis réallouer uniquement son
   stockage OpenGL avec les dimensions physiques xN.
6. Créer et modifier les ressources GL uniquement sur le thread possédant le contexte courant.
7. Restaurer l'identifiant de texture moteur précédent immédiatement après le dessin remplacé.
8. Verrouiller tous les RVA et offsets par identité de build, signatures machine et manifeste.
9. Toute installation en jeu doit être réversible, avec sauvegarde et SHA-256.
10. `EnableAreaAnimationX4=true` doit se trouver sous `[Shaders]`. Une clé avant la première
    section est ignorée par le parseur même si son texte paraît correct.
11. Ne jamais lancer le jeu à la place de l'utilisateur. Lui fournir le test, puis lire les logs et
    captures après fermeture du jeu.

## Pourquoi les essais bas niveau ont échoué

Le moteur ne téléverse pas nécessairement une frame d'animation de zone comme une texture GL
autonome. Pour `AM0205E`, le chemin constaté est :

```text
CGameStatic::RenderBam
  -> CInfinity::FXPrep / FXLock / FXRender
  -> CVidCell::FXRender3d / Blt8To32
  -> composition CPU dans une grande surface dynamique partagée
  -> CInfinity::FXUnlock
  -> CInfinity::FXBltFrom
  -> CVidMode::FXBltToBack
  -> CVidCell::RenderTexture final
```

Conséquences :

- un hook cherchant un `glTexImage2D(W, H)` égal à la frame ne voit rien ;
- un hook `glTexSubImage2D` cherchant la frame dans un atlas BAM peut ne rien voir ;
- promouvoir un atlas supposé ne modifie pas la composition CPU réelle ;
- l'outline visible peut appartenir à la map x4 tandis que le centre animé reste le BAM x1.

Pour ce chemin, intercepter l'identité de l'objet au début de `RenderBam`, puis remplacer la texture
au dernier `RenderTexture` appelé pendant ce même rendu.

## Procédure complète

Pour un nouveau traitement, employer le pipeline automatisé décrit dans
`pipeline/ANIMATION_UPSCALE_PIPELINE.md`. Les étapes 1 à 5 et la construction de
`03_runtime_pack` sont automatisées. Les étapes 6 à 13 spécifient le runtime, la compilation,
l'installation réversible et la validation en jeu.

Pour conserver ce x4 et ajouter une lecture visuelle 15 -> 30 fps, ne pas modifier le run spatial :
enchaîner avec
[`../pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](../pipeline/ANIMATION_UPSCALE_30FPS_V2.md).

Après une QA x4 techniquement saine, un liseré d'objet ou la délimitation visible du canvas se
traite dans un prototype alpha séparé, jamais dans le pack canonique. Procédure et registre :
[`../pipeline/ANIMATION_ALPHA_CORRECTIONS.md`](../pipeline/ANIMATION_ALPHA_CORRECTIONS.md).

### 1. Identifier la ressource et son occurrence

Lister les animations de la zone :

```powershell
python pipeline/scripts/list_animations.py ARxxxx
```

Relever au minimum :

- resref et type de ressource ARE (`BAM`, `WBM` ou `PVRZ`) ;
- mode de palette et resref de palette externe, le cas échéant ;
- position monde ;
- séquence et frame initiale ;
- dimensions maximales ;
- nombre de frames et cycles ;
- zones et occurrences réutilisant le même BAM.

Sources canoniques :

- `animations/index/occurrences.csv` pour les occurrences ;
- `animations/index/ressources.csv` pour les ressources ;
- `animations/ressources/<RESREF>/source.bam` pour le BAM extrait.

Pour régénérer seulement l'inventaire canonique sans réécrire les médias extraits :

```powershell
python pipeline/scripts/extract_area_animations.py --index-only --keep-going
```

Omettre `--index-only` seulement lorsqu'une nouvelle extraction des sources et aperçus BAM est
réellement nécessaire.

Avant tout traitement, fournir un aperçu et faire confirmer l'objet par l'utilisateur.

### 2. Créer le prototype isolé

Chemin de production automatisé : `animations/runs/<run>/resources/<RESREF>/`. Le dossier
`proto/` est réservé aux recherches ponctuelles et aux preuves historiques.

Pour un run x4 terminé, la sortie de production contient aussi :

```text
animations/runs/<run>/03_runtime_pack/
  manifest.json
  AreaAnimations-X4.registry
  AAX4-<RESREF>-frameXXX.rgba
```

Arborescence attendue :

```text
proto/<RESREF>-<description>/
  01_source/
    <RESREF>.bam
    aperçu.gif ou planche.png
  02_frames_x1/
    rgb/frame_XXX.png
    alpha/frame_XXX.png
    rgba/frame_XXX.png
    manifest.json
  x4/
    00_padded_x1/
    01_comfy_padded_x4/
    rgb/
    alpha/
    rgba/
    raw_rgba/
    preview/
    manifest.json
  ingame-x4-test/
    assets bruts renommés
    scripts Install / Restore / Set-State
    README.md
```

Ne jamais écraser un prototype existant. Employer un nouveau dossier ou arrêter.

### 3. Extraire les frames x1

```powershell
python pipeline/scripts/export_bam_frames.py `
  proto/<RESREF>-<description>/01_source/<RESREF>.bam `
  proto/<RESREF>-<description>/02_frames_x1
```

Le manifeste doit conserver :

- `source_size` de chaque frame ;
- `centre` de chaque frame ;
- `canvas_offset` ;
- `aligned_canvas_size` ;
- `cycles[].frame_indices`.

Contrôles bloquants :

- nombre de PNG RGB = alpha = RGBA = nombre de frames BAM ;
- chaque alpha a les mêmes dimensions que son RGB ;
- les centres et tables de cycles sont lisibles dans le manifeste ;
- aucune frame n'est extraite depuis une planche concaténée.

### 4. Vérifier la géométrie avant l'upscale

Cas A — toutes les frames ont les mêmes dimensions et le même centre : utiliser directement le
canvas aligné. C'est le cas validé de `AM0205E` : neuf frames `165x130`, centre `(83,130)`.

Cas B — dimensions ou centres variables : le registre générique validé avec `AR0602` crée le
stockage de remplacement par frame avec :

- taille logique = `source_size` de cette frame ;
- taille physique = `source_size * scale` ;
- placement conservé par le centre BAM original.

Le pipeline recadre le canvas aligné avec `canvas_offset * scale` et `source_size * scale`, puis
inscrit chaque `logical_size_x1` dans `AreaAnimations-X4.registry`. Ne jamais alimenter le runtime
avec les dimensions du canvas commun.

### 5. Upscaler chaque frame

Le serveur ComfyUI/SeedVR doit déjà être lancé. Le dossier de sortie doit être vide.

```powershell
python pipeline/scripts/upscale_animation_frames.py `
  proto/<RESREF>-<description>/02_frames_x1/rgb `
  proto/<RESREF>-<description>/02_frames_x1/alpha `
  proto/<RESREF>-<description>/x4 `
  --frame-manifest proto/<RESREF>-<description>/02_frames_x1/manifest.json `
  --scale 4
```

Réglages validés :

- SeedVR2 7B ;
- échelle x4 ;
- `euler`, `simple`, 1 étape, CFG `1`, denoise `1` ;
- correction colorimétrique `lab` ;
- padding x1 `32` autour de chaque entrée ;
- alpha source agrandi en nearest-neighbour.

Sortie runtime requise : RGBA non compressé, ordre de lignes natif du PNG, exactement
`physical_width * physical_height * 4` octets.

Contrôles bloquants :

- manifeste `status: completed` ;
- dimensions x4 exactes ;
- taille exacte de chaque `.rgba` ;
- SHA-256 enregistré pour chaque source et sortie ;
- planche de contact inspectée ;
- absence de halo, canal inversé, frame retournée ou alpha opaque.

### 6. Résoudre le chemin moteur

Pour les animations de décor `ARE` rendues par `CGameStatic`, utiliser directement le chemin de
composition final validé. Ne refaire un diagnostic d'upload bas niveau que pour une autre famille
(créature, effet, UI, overlay liquide) ou un autre build.

Pour une animation de zone `CGameStatic` :

1. Hooker `CGameStatic::RenderBam`.
2. Lire le resref dans le `CVidCell` embarqué.
3. Lire séquence et position de frame courantes.
4. Résoudre l'index BAM absolu avec `cycles[sequence].frame_indices[currentFrame]`.
5. Poser un marqueur `thread_local` uniquement autour de l'appel original.
6. Hooker le wrapper final `CVidCell::RenderTexture` utilisé par `CVidMode::FXBltToBack`.
7. Sous le marqueur uniquement, lier la texture xN de la frame résolue.
8. Appeler le wrapper original sans modifier ses arguments.
9. Restaurer la texture moteur précédente.

Ne jamais utiliser `currentFrame / répétitions` comme règle générale. `AM0205E` accepte
`currentFrame / 3` uniquement parce que son cycle 0 vaut
`[0,0,0,1,1,1,...,8,8,8]`.

### 7. Créer une texture x1 logique / xN physique

Pour chaque frame, sur le thread GL :

```cpp
oldId = (engineGlTextureState >> 21) & 0x1FF;

id = DrawGenTexture(GL_LINEAR, 0, 0, 0);  // fiche moteur RGBA + filtre linéaire
DrawBindTexture(id);
TexImage(logicalWidth, logicalHeight, nullptr, 0);  // métadonnées x1

glTexImage2D(
    GL_TEXTURE_2D,
    0,
    GL_RGBA8,
    logicalWidth * scale,
    logicalHeight * scale,
    0,
    GL_RGBA,
    GL_UNSIGNED_BYTE,
    rgbaXn);

glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0);

DrawBindTexture(oldId);
```

Pourquoi cela fonctionne :

- `DrawTexCoord` conserve les coordonnées entières x1 du BAM ;
- `DrawEnd_GL` normalise ces coordonnées avec la largeur/hauteur enregistrée dans la fiche moteur ;
- la fiche moteur reste en x1, donc les UV couvrent toujours `[0,1]` ;
- le sampler GL lit réellement la surface xN ;
- le wrapper original conserve position, taille écran, alpha, teinte, clipping rectangulaire,
  ordre de rendu et cadence.

Ne pas appeler `DrawGenTexture(GL_NEAREST, ...)` : un échantillonnage nearest lors du retour à la
taille écran peut annuler l'essentiel du gain xN.

Sauvegarder/restaurer `GL_UNPACK_ALIGNMENT`, `GL_UNPACK_ROW_LENGTH`, `GL_UNPACK_SKIP_ROWS` et
`GL_UNPACK_SKIP_PIXELS`. Refuser la création si un pixel-unpack buffer est lié sans chemin sûr pour
le neutraliser.

Après chaque création, vérifier avec `glGetTexLevelParameteriv` que les dimensions physiques sont
exactes. En cas d'échec, supprimer les identifiants créés, restaurer `oldId` et rendre le BAM x1.

### 8. Gérer le contexte et les erreurs

- Associer les identifiants de textures au `HGLRC` courant.
- Sur changement de contexte, oublier les anciens identifiants et recréer paresseusement les
  textures lors du prochain dessin cible.
- Ne jamais supprimer des textures GL depuis le thread de shutdown sans contexte courant.
- Toute exception du prototype doit déléguer au rendu original.
- Le marqueur de rendu doit être `thread_local` et supporter l'imbrication.
- Les hooks ne doivent modifier aucun autre resref.

Limitation connue : les polygones d'occlusion appliqués pendant la composition de la surface FX ne
sont pas présents dans la texture de remplacement autonome. Le wrapper final conserve le clipping
rectangulaire, mais pas forcément les masques polygonaux déjà rasterisés. Tester explicitement les
animations passant derrière murs, arches ou avant-plans. Ne pas généraliser sans ce test.

### 9. Verrouiller le build

Faits de référence BG2EE `2.7.3.x`, à ne pas recopier comme support générique :

| Élément | RVA / offset validé |
|---|---:|
| `CGameStatic::RenderBam` | `0x1F2B50` |
| wrapper final `CVidCell::RenderTexture` | `0x425790` |
| `DrawDeleteTexture` | `0x413270` |
| `DrawGenTexture` | `0x413350` |
| `DrawGetRenderer` | `0x413390` |
| `TexImage` | `0x4135E0` |
| état texture GL | `0x2F73F6C` |
| resref dans `CGameStatic` | `+0x1C0` |
| frame courante dans `CGameStatic` | `+0x1C8` |
| séquence courante dans `CGameStatic` | `+0x1CA` |

Pour un ajout durable :

- déplacer les RVA/offsets requis dans `game/build_manifest.*` ;
- ajouter patterns ou signatures et preuves de validation ;
- vérifier version à quatre composants + identité produit ;
- échouer fermé si une signature diffère ;
- ne jamais annoncer de support pour un build non testé.

Les RVA, offsets et signatures du runtime générique sont dans `game/build_manifest.*`. Les anciens
fichiers de prototype peuvent encore contenir de la logique ciblée ; ne pas les étendre pour une
nouvelle ressource.

### 10. Organiser plusieurs remplacements

Le chemin spatial V1 emploie un registre binaire généré par
`pipeline/scripts/build_animation_runtime_pack.py` :

```text
RegistryHeader
  magic = IEEAAX4\0
  version
  scale = 4
  resourceCount
Resource[]
  resref[8]
  frameCount / cycleCount
  frames[]: logicalWidth / logicalHeight
  cycles[]: absoluteFrameIndices[]
```

La version 2, générée par `pipeline/scripts/run_animation_upscale_30fps_v2.py`, ajoute après les
deux compteurs de ressource :

```text
ResourceV2
  resref[8]
  frameCount / cycleCount
  playbackMode                 # 0 Native, 1 TimedTimeline
  nativeFpsNumerator / nativeFpsDenominator
  targetFpsNumerator / targetFpsDenominator
  frames[]: logicalWidth / logicalHeight
  cycles[]:
    nativeFrameIndices[]
    timelineFrameIndices[]     # vide en mode Native
```

La version 3 conserve tous ces champs et insère, avant `frames[]` :

```text
ResourceV3
  … en-tête et cadences v2 …
  positionMode                 # 0 = variante libre, 1 = occurrence exacte
  worldX / worldY              # int32, coordonnées brutes de l'entrée ARE
  variantIndex                 # uint32, stable dans ce resref
  … frames[] et cycles[] v2 …
```

La variante 0 utilise `AAX4-RESREF-frameNNN.rgba`; les suivantes utilisent
`AAX4-RESREF-vN-frameNNN.rgba`. Une position est une clé exacte, sans tolérance. La résolution
cherche d'abord la variante liée à `(worldX, worldY)`, puis une variante libre. Deux variantes du
même resref à la même position, deux variantes libres ou deux `variantIndex` identiques font
échouer le pack fermé. Voir
[`../pipeline/ANIMATION_PER_OCCURRENCE_OCCLUSION.md`](../pipeline/ANIMATION_PER_OCCURRENCE_OCCLUSION.md).

Une ressource `TimedTimeline` doit conserver exactement la durée de son cycle :
`timelineCount / targetFps == nativeCount / nativeFps`. Les cadences sont rationnelles. Une
ressource `Native` porte quatre champs de cadence à zéro et une timeline vide. Le parseur de
production accepte les registres v1, v2 et v3 ; toute valeur, durée ou index invalide fait échouer le
chargement fermé.

Un seul hook `RenderBam`, un seul hook de composition finale et un cache LRU borné de textures par
contexte servent tout le pack. `resolve_frame` compare le resref, vérifie la séquence, puis applique
la table de cycle. Le flag unique est `EnableAreaAnimationX4`.

Le runtime charge et valide le registre et tous les buffers avant d'installer les hooks. Une erreur
de schéma, taille, index ou asset fait échouer le pack fermé et conserve les BAM x1.

Un seul fichier `AreaAnimations-X4.registry` est actif à la fois. Un pack doit donc contenir
l'union de toutes les ressources désirées ; ne jamais superposer partiellement deux packs. Un
resref partagé présent dans le registre est remplacé sur toutes ses maps, pas seulement sur la zone
ayant servi de sélecteur.

Pour le registre v2, la sélection d'une phase temporelle n'est autorisée que si la frontière de
présentation, QPC, le signal de pause `CTimerWorld::m_active` et la timeline sont tous valides. Le
cycle BAM natif reste l'autorité et sert de fallback. Le scheduler est possédé par le thread de
rendu, se recale à chaque transition native, gèle pendant la pause et oublie ses pointeurs lors
d'un changement de zone.

### 11. Construire et tester la DLL

Windows :

```powershell
cmake --build engine/InfinityEngine-Enhancer/source-patchee/build-filter-diagnostic-v142 `
  --config Release --target InfinityEngine-Enhancer --parallel

ctest --test-dir engine/InfinityEngine-Enhancer/source-patchee/build-filter-diagnostic-v142 `
  -C Release --output-on-failure
```

Exiger : build réussi, tests `100% passed`, hash SHA-256 calculé.

### 12. Installer de façon réversible

Le pack V1 spatial emploie les scripts génériques décrits ci-dessous. Un run 30 fps V2 doit
obligatoirement employer `Install-AreaAnimations-30fps-V2.ps1` et
`Restore-AreaAnimations-30fps-V2.ps1`, après `qa-approval.json`, suivant
[`../pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](../pipeline/ANIMATION_UPSCALE_30FPS_V2.md). Ne pas
installer un registre v2 avec l'installateur V1.

Jeu et `InfinityLoader` fermés :

1. Refuser l'installation si un processus du jeu existe.
2. Résoudre les chemins absolus.
3. Vérifier DLL, INI, `03_runtime_pack/manifest.json`, registre et tous les assets source.
4. Protéger un asset cible non identique : arrêter au lieu d'écraser.
5. Créer `xN-animation-backup-YYYYMMDD-HHMMSS/`.
6. Sauvegarder DLL, INI et assets déjà présents.
7. Écrire `install-backup.json` avec présence initiale, SHA-256 originaux et installés.
8. Copier la DLL et les assets.
9. Supprimer toute occurrence existante des clés modifiées, puis insérer sous la première section
   `[Shaders]` : `EnableAreaAnimationX4=true`. Désactiver les anciens prototypes concurrents.
10. Vérifier que le hash de la DLL installée égale celui du build.
11. Relire l'INI avec suivi de section et prouver que la clé générique apparaît exactement une fois
    sous `[Shaders]`. Une simple recherche textuelle n'est pas un contrôle suffisant.
12. Vérifier après copie les SHA-256 du registre et de chaque `.rgba` installé.

Fournir trois scripts :

- `Install-...ps1` : sauvegarde + installation ;
- `Set-...-State.ps1 -Mode x1|xN` : bascule INI, jeu fermé ;
- `Restore-...ps1 -BackupPath ...` : restauration exacte, y compris suppression des assets qui
  n'existaient pas avant le test.

### 13. Validation en jeu

Demander à l'utilisateur :

1. lancer lui-même BG2EE ;
2. ouvrir la map connue et rejoindre la position connue ;
3. observer au moins un cycle complet ;
4. vérifier centre animé, contour, alpha, teinte, taille, ancrage, cadence et occlusion ;
5. prendre une capture ;
6. fermer le jeu avant toute modification suivante.

Logs attendus pour le runtime générique :

```text
Prepared area-animation x4 runtime pack: <BAM> BAM, <frames> frames, <MiB> MiB raw
Area-animation x4 registry high-level composition hooks installed
Area animation x4 texture <id>: <RESREF> frame <NNN>, logical <W>x<H>, physical <4W>x<4H>
Composing area animation <RESREF> frame <NNN>: logical <W>x<H>, physical <4W>x<4H>
...
```

Pour la référence AR0602, les deux premiers compteurs valent `13 BAM` et `219 frames`. Leur absence
au démarrage signifie que le pack n'est pas actif ; ne pas juger l'upscale visuellement avant de
corriger ce gate.

Validation A/B : même sauvegarde, caméra, zoom, résolution et map ; capture x1 puis xN ; assembler
les deux images dans un PNG sans perte. Ne pas conclure à partir d'un JPEG redimensionné.

La map xN n'est pas une condition technique pour lier la texture xN. Elle rend toutefois le gain
plus lisible et évite de comparer une animation détaillée à un fond volontairement x1.

## Diagnostic rapide

| Symptôme | Cause probable | Action |
|---|---|---|
| Aucun log `Prepared area-animation` | Flag ignoré ou pack non chargé | Vérifier clé unique sous `[Shaders]`, registre et assets |
| Aucun log de frame dans les hooks GL | Frame composée en CPU | Utiliser le hook de composition final |
| Contour net, centre pixelisé | Contour dans la map xN, BAM encore x1 | Vérifier marqueur resref/frame et hook final |
| Objet quatre fois plus grand | Dimensions logiques passées en x4 | Revenir aux dimensions x1 dans `TexImage` |
| Texture x4 mais gain faible | Filtre nearest ou fiche moteur x4 | Enregistrer `GL_LINEAR` et dimensions logiques x1 |
| Mauvaise frame | Mapping de cycle supposé | Lire `cycles[sequence].frame_indices[currentFrame]` |
| Décalage / tremblement | Centre ou canvas mal traité | Utiliser dimensions natives et centre BAM par frame |
| Rectangle opaque | Alpha perdu ou format incorrect | Vérifier RGBA, alpha nearest et taille brute |
| Couleurs inversées | RGBA/BGRA confondu | Vérifier l'ordre des canaux du buffer et de l'upload |
| Texture retournée | Convention de lignes incohérente | Comparer une mire asymétrique et corriger une seule fois |
| Passe devant un mur | Masque polygonal FX contourné | Bloquer la généralisation ou réimplémenter l'occlusion |
| Crash au démarrage | ABI, RVA ou signature incorrects | Restaurer le backup, comparer le build, échouer fermé |
| Fonctionne puis disparaît | Contexte GL recréé | Invalider les IDs sur changement de `HGLRC` |

## Critères de fin

- Objet confirmé par l'utilisateur avant extraction.
- Frames x1 séparées, alpha séparé, manifeste complet.
- Upscale frame par frame ; aucun upscale de planche concaténée.
- `03_runtime_pack` terminé, registre reproductible, cycles et 100 % des assets vérifiés par hash.
- Dimensions logiques x1 et physiques xN prouvées dans le log.
- Cycle complet observé ; toutes les frames loguées.
- Taille, ancrage, cadence, alpha, teinte et occlusion validés.
- DLL compilée, tests passés, hash installé vérifié.
- Backup et restauration testables.
- Support limité explicitement aux builds réellement validés.

## Références

- Preuve historique : `proto/AM0205E-orifice/`.
- Runtime générique validé :
  `engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_animation_x4_registry.cpp`.
- Hooks : `engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp`.
- Extraction frame par frame : `pipeline/scripts/export_bam_frames.py`.
- Pipeline automatisé : `pipeline/scripts/run_animation_upscale.py` et
  `pipeline/ANIMATION_UPSCALE_PIPELINE.md`.
- Construction/validation du registre : `pipeline/scripts/build_animation_runtime_pack.py`.
- Pack de référence validé :
  `animations/runs/ar0602-all-bam-seedvr7b-lab-x4/03_runtime_pack/`.
- Upscale générique x2/x4 + alpha + buffers bruts :
  `pipeline/scripts/upscale_animation_frames.py`.
- Inventaire des animations : `pipeline/scripts/extract_area_animations.py`.
- Règles de hooking : `engine/InfinityEngine-Enhancer/source-patchee/AGENTS.md`.
- Threading et contexte GL : `engine/InfinityEngine-Enhancer/source-patchee/docs/threading-model.md`.
