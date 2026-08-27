# Ajout d'un asset vidéo événementiel de zone — procédure LLM

Audience : agent LLM modifiant `G:\AI\BG2_Upscale` et
`engine/InfinityEngine-Enhancer/source-patchee`.

Référence validée : `AR1300` / objet WED `BRIDGE01`, BG2EE `2.7.3.0`, OpenGL,
validation utilisateur du 2026-08-23.

## 0. Routage

Utiliser cette procédure uniquement si le moteur remplace instantanément un décor
conditionnel et qu'aucune animation native exploitable n'existe à cet emplacement.

- Animation de décor BAM existante : utiliser
  `pipeline/ANIMATION_UPSCALE_PIPELINE.md` et
  `animations/UPSCALE_ANIMATIONS_ZONE.md`.
- Vidéo cinématique `.wbm` : utiliser la branche `video/`.
- Transition locale absente du jeu, déclenchée par un état WED/porte/levier : utiliser
  cette procédure.

Le runtime actuel ne lit pas `asset-manifest.json`. Le manifeste est un contrat de
production et de QA. Toute valeur modifiée doit aussi être reportée dans le code C++.

## 1. Contrat de sortie

Créer un dossier de prototype :

```text
proto/<AREA>-<asset>/
├── README.md
├── 01_classic-preview/
│   ├── asset-manifest.json
│   ├── <ASSET>-forward.mp4
│   ├── <ASSET>-reverse.mp4
│   ├── <ASSET>-forward.wav
│   ├── <ASSET>-reverse.wav
│   ├── <ASSET>-closed.bgra
│   └── <ASSET>-open.bgra
└── color-match-inspection/
```

Copier les six fichiers runtime approuvés dans :

```text
engine/InfinityEngine-Enhancer/source-patchee/assets/<asset-directory>/
```

Le manifeste doit au minimum fixer :

- `area_resref` ;
- identifiant de l'objet WED ou signal équivalent ;
- rectangle monde x1 `x`, `y`, `width`, `height` ;
- sens frame 0 et sens dernière frame ;
- cadence rationnelle, nombre de frames et durée `N / fps` ;
- résolution, codec, format pixel et SHA-256 des deux vidéos ;
- format, fréquence, canaux et SHA-256 des deux WAV ;
- résolution, format et SHA-256 des deux endpoints BGRA ;
- méthode de génération (`lanczos`, `seedvr2-7b-x4`, etc.) ;
- statut runtime et QA ;
- validations restantes.

## 2. Préflight moteur et WED

### 2.1 Produire les deux états natifs

Depuis `G:\AI\BG2_Upscale` :

```powershell
python pipeline\scripts\validate_x1_masters.py --area <AREA> --fix
python pipeline\scripts\render_secondary.py <AREA> `
  maps\<AREA>\rendus-x1\tuiles-secondaires\<AREA>-tuiles-secondaires-x1.png
```

Conserver :

```text
maps/<AREA>/rendus-x1/tuiles-principales/<AREA>-tuiles-principales-x1.png
maps/<AREA>/rendus-x1/tuiles-secondaires/<AREA>-tuiles-secondaires-x1.png
```

Ne pas supposer que primaire = fermé. Vérifier visuellement chaque état. Pour
`AR1300`, primaire = pont ouvert et secondaire = pont fermé.

### 2.2 Identifier le signal d'état final

Préférer le signal de rendu final à l'entrée utilisateur :

1. identifier l'objet WED et ses cellules conditionnelles ;
2. relever pour chaque cellule l'index primaire final et l'index secondaire ;
3. observer l'index réellement reçu dans `CVidTile::RenderTexture` après sélection
   du moteur ;
4. classer ces indices en `Open`, `Closed` ou `Unknown` ;
5. ignorer toute cellule identique/persistante dans les deux états ;
6. filtrer par zone active avant de voter un état.

Ne pas accrocher le runtime au clic du levier : scripts, chargement de sauvegarde,
IA et appels `OpenDoor`/`CloseDoor` peuvent changer la porte sans clic. Le signal
correct est l'art primaire/secondaire effectivement rendu.

Référence `AR1300` dans `src/iee/bridge_transition.cpp` :

```text
Open:
2527-2528, 2606-2608, 2685-2689, 2765-2769,
2845-2850, 2925-2931, 3007-3010, 3089

Closed:
4840-4873 sauf 4872

Ignore:
3006 et 4872 ; cellule persistante, secondaire WED = -1/0xFFFF
```

Les 33 cellules utiles déclenchent le même état. Ne pas démarrer plusieurs requêtes
pendant le rendu d'un même objet : ignorer les observations identiques au dernier état.

### 2.3 Déterminer le rectangle monde

Le rectangle doit :

- contenir toute la transition ;
- être identique au pixel près dans les deux états ;
- conserver le même repère haut-gauche que la carte x1 ;
- avoir le même rapport largeur/hauteur que la vidéo ;
- être sauvegardé en PNG sans perte.

Extraction de référence :

```python
from pathlib import Path
from PIL import Image

area = "AR1300"
x, y, w, h = 2848, 1984, 512, 512
root = Path("maps") / area
primary = root / "rendus-x1/tuiles-principales" / f"{area}-tuiles-principales-x1.png"
secondary = root / "rendus-x1/tuiles-secondaires" / f"{area}-tuiles-secondaires-x1.png"
out = root / "cadrages-pont-levis"
out.mkdir(parents=True, exist_ok=True)
Image.open(primary).crop((x, y, x + w, y + h)).save(out / f"{area}-pont-levis-ouvert-x1.png")
Image.open(secondary).crop((x, y, x + w, y + h)).save(out / f"{area}-pont-levis-ferme-x1.png")
```

Référence validée : rectangle monde `(2848, 1984, 512, 512)`.

## 3. Préparation vidéo

### 3.1 Contraintes

- CFR obligatoire ; référence : `24/1`.
- `frame_count` explicite ; référence : `124`.
- durée visuelle : `124 / 24 = 5.166666… s`.
- dimensions paires avec `yuv420p`.
- première frame = état avant transition.
- dernière frame = état après transition.
- aucun mouvement de caméra, zoom, recadrage ou parallaxe.
- géométrie et perspective des endpoints alignées avec les deux crops natifs.
- vidéo compressée, pas de tableau de textures résidentes.

Référence mémoire : `124 × 2048 × 2048 × 4 ≈ 1.94 GiB` si toutes les frames
sont résidentes. Le runtime utilise une file de 8 frames décodées, deux endpoints
BGRA et une texture GL réutilisée.

### 3.2 Version classique de validation

La référence actuelle est un agrandissement Lanczos vers `2048×2048`, pas un
upscale IA. Exemple reproductible :

```powershell
ffmpeg -y -i <source.mp4> -map 0:v:0 `
  -vf "scale=2048:2048:flags=lanczos" -an `
  -c:v libx264 -profile:v high -pix_fmt yuv420p -preset slow -crf 12 `
  -r 24 -fps_mode cfr <ASSET>-forward.mp4
```

Vérifier avant de continuer :

```powershell
ffprobe -v error -select_streams v:0 `
  -show_entries stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,avg_frame_rate,nb_frames `
  -show_entries format=duration,size -of json <ASSET>-forward.mp4
```

### 3.3 Flux inverse seekable

Ne pas simuler la fermeture en décrémentant un décodeur H.264 avant. Produire un
second flux contenant les mêmes images dans l'ordre inverse. L'encoder tout-intra
réduit la latence et rend les seeks de retournement déterministes :

```powershell
ffmpeg -y -i <ASSET>-forward.mp4 -map 0:v:0 -vf reverse -an `
  -c:v libx264 -profile:v high -pix_fmt yuv420p -preset slow -crf 10 `
  -r 24 -fps_mode cfr -g 1 -keyint_min 1 -sc_threshold 0 `
  <ASSET>-reverse.mp4
```

Pour un nouvel asset, encoder aussi le flux avant en tout-intra si la taille disque
est acceptable. La référence AR1300 garde un flux avant inter-frame compact et un
flux inverse tout-intra ; ce montage est validé.

Assertions obligatoires :

```text
forward[n] == reverse[N - 1 - n]
forward.frame_count == reverse.frame_count == N
forward.fps == reverse.fps
forward.duration == reverse.duration == N / fps
```

## 4. Audio et endpoints de masquage

### 4.1 Audio externe

Le runtime Media Foundation ne lit que la piste vidéo. Le son est lu séparément
par MCI `waveaudio`, ce qui permet un seek à la frame courante lors d'une inversion.

```powershell
ffmpeg -y -i <source.mp4> -map 0:a:0 -c:a pcm_s16le -ar 32000 -ac 2 <ASSET>-forward.wav
ffmpeg -y -i <ASSET>-forward.wav -af areverse -c:a pcm_s16le -ar 32000 -ac 2 <ASSET>-reverse.wav
```

Le seek audio est `assetFrame × 1000 / fps` millisecondes. Utiliser un alias MCI
unique par lecture, fermer l'ancien alias avant toute réouverture et arrêter l'audio
quand la vidéo se termine ou change de sens.

### 4.2 Endpoints BGRA

Le moteur change les tuiles WED immédiatement. Afficher l'ancien endpoint dès la
requête masque cette bascule pendant l'amorçage/seek du décodeur.

```powershell
ffmpeg -y -i <ASSET>-forward.mp4 -vf "select=eq(n\,0)" `
  -frames:v 1 -f rawvideo -pix_fmt bgra <ASSET>-closed.bgra
ffmpeg -y -i <ASSET>-forward.mp4 -vf "select=eq(n\,N-1)" `
  -frames:v 1 -f rawvideo -pix_fmt bgra <ASSET>-open.bgra
```

Remplacer `N-1` par l'index numérique réel. Taille obligatoire :

```text
width × height × 4 octets
2048 × 2048 × 4 = 16,777,216 octets pour AR1300
```

Les endpoints restent dans l'espace couleur source. Le shader leur applique la
même correction et le même alpha qu'aux frames vidéo.

## 5. State machine bidirectionnelle

Définir un repère logique indépendant du fichier vidéo :

```text
logical 0       = fermé
logical N - 1   = ouvert
opening asset frame(logical) = logical
closing asset frame(logical) = N - 1 - logical
```

Comportement obligatoire :

1. première observation après chargement : mémoriser l'état, ne rien jouer ;
2. fermé → ouvert au repos : requête `Opening`, logical `0` ;
3. ouvert → fermé au repos : requête `Closing`, logical `N - 1` ;
4. changement d'état pendant lecture : conserver la frame affichée ;
5. annuler le décodage précédent par numéro de série ;
6. seek dans l'autre flux à la frame asset correspondant à la même frame logique ;
7. conserver l'image courante jusqu'à disponibilité de la nouvelle frame ;
8. redémarrer vidéo et audio depuis cette frame ;
9. masquer l'overlay après la dernière frame et laisser visible l'état WED natif.

Ne jamais utiliser directement l'index asset comme position de retournement : il
est inversé dans le flux de fermeture.

Architecture AR1300 :

- décodage Media Foundation sur worker COM `COINIT_MULTITHREADED` ;
- `MF_SOURCE_READER_ENABLE_VIDEO_PROCESSING = TRUE` ;
- sortie demandée `MFVideoFormat_RGB32`, copiée en BGRA8 ;
- file bornée à 8 frames ;
- QPC/frame clock pour la présentation ;
- numéro de série pour invalider requêtes et frames obsolètes ;
- OpenGL uniquement sur le render thread ;
- aucune exception ne doit traverser un detour.

## 6. Placement monde

Publier à chaque frame cohérente :

```text
scrollX, scrollY
viewWorldW, viewWorldH
isTargetArea
```

Pour le viewport GL courant `(vx, vy, vw, vh)` :

```text
screenX = (worldX - scrollX) × vw / viewWorldW
screenY = (worldY - scrollY) × vh / viewWorldH
screenW = worldW × vw / viewWorldW
screenH = worldH × vh / viewWorldH
```

`screenX/screenY` sont locaux au viewport. Ne pas ajouter `vx/vy` dans le shader :
OpenGL applique déjà l'origine du viewport lors de la conversion NDC.

Mapping vertex :

```text
clip.x = pixel.x / vw × 2 - 1
clip.y = 1 - pixel.y / vh × 2
```

Media Foundation fournit la première scanline en haut ; la référence conserve
`vUv = local` sans flip vertical supplémentaire.

## 7. Colorimétrie et alpha

### 7.1 Mesure

Pour chaque nouvel asset :

1. capturer la carte native à état endpoint ;
2. sans déplacer caméra/zoom, capturer l'endpoint vidéo affiché ;
3. aligner les deux captures au pixel près ;
4. exclure pixels mobiles, HUD, bord feather, noirs écrêtés et éléments qui diffèrent
   structurellement ;
5. ajuster une transformation RGB globale sur pixels normalisés ;
6. mesurer le ratio de luminance résiduel par grille spatiale ;
7. interpoler bilinéairement cette grille dans le fragment shader ;
8. revalider plusieurs frames, pas seulement l'endpoint.

Modèle de référence :

```text
p = max(source, 0)^gamma
graded = M × p + b
graded *= bilinear_gain_grid(uv)
output = clamp(graded, 0, 1)
```

Attention : le constructeur GLSL `mat3(a…i)` remplit les colonnes. Copier les
coefficients sans transposition accidentelle.

AR1300 utilise `gamma=1.05`, une matrice `3×3`, un offset RGB et une grille de
gain `8×8` définis dans `bridge_transition.cpp`. Ces coefficients sont spécifiques
à AR1300 ; ne pas les réutiliser sur un autre asset.

### 7.2 Feather

La vidéo H.264 `yuv420p` n'a pas d'alpha. Générer l'alpha dans le shader :

```glsl
vec2 edgePixels = min(uv, vec2(1.0) - uv) * rectSize;
float edgeDistance = min(edgePixels.x, edgePixels.y);
float alpha = smoothstep(0.0, featherPixels, edgeDistance);
```

Référence validée : `featherPixels = 64` pixels écran dans le rectangle rendu.
Mélange : `SRC_ALPHA`, `ONE_MINUS_SRC_ALPHA`.

## 8. Couche de rendu : ordre obligatoire

Ordre BG2EE 2.7.3 :

```text
CGameArea::RenderZoomed
  DrawBeginScaled                 -> configure la cible/échelle carte ; FBO optionnel
  CGameArea::Render               -> met en file le rendu natif
    detour après original
      DrawFlush_GL                -> exécute la file native dans la cible carte courante
      render_world_overlay        -> dessine l'asset dans cette même cible
  DrawEndScaled                   -> finalise/résout carte + asset
CScreenWorld::UpdateLua           -> HUD, dialogues, inventaire, menus
SwapBuffers
```

Règles non négociables :

- ne pas dessiner à `SwapBuffers` : l'asset passerait devant tous les HUD ;
- ne pas dessiner avant `DrawFlush_GL` : la file native recouvrirait ensuite l'asset ;
- ne pas accepter/rejeter la passe d'après la seule valeur de `FRAMEBUFFER_BINDING` :
  la cible carte validée vaut `0`, mais d'autres branches de `DrawBeginScaled` peuvent
  employer un FBO non nul ;
- ne pas masquer le HUD par rectangles/scissor : cela échoue sur menus, résolutions et
  overlays dynamiques ;
- capturer/restaurer programme, texture active/binding, VAO, blend, cull, depth,
  scissor, stencil et framebuffer sRGB ;
- ne pas changer le framebuffer ; dessiner dans celui déjà lié.

Symptôme diagnostique critique : son audible + aucune image + draw GL sans erreur =
dessin recouvert par la file différée ou mauvais framebuffer, pas problème de décodage.

Hooks validés BG2EE `2.7.3.x` :

```text
CGameArea::Render RVA 0x189360, ABI void(void* thisPtr, void* vidMode)
DrawFlush_GL     RVA 0x42B350, ABI void()
```

Ces RVA et signatures vivent dans `src/iee/game/build_manifest.*`. Ne jamais
introduire un RVA build-specific ailleurs. EEex peut déjà avoir détourné le prologue
de `CGameArea::Render` : valider le tail de signature et chaîner via MinHook.

## 9. Fichiers code à modifier

Référence actuelle :

```text
src/iee/bridge_transition.h/.cpp       décodeur, state machine, audio, shader
src/iee/features/tile_render.cpp       observation de la tuile finale
src/iee/hooks.cpp                      couche carte + DrawFlush_GL
src/iee/area_state.cpp                 transform monde
src/iee/game/build_manifest.h/.cpp     hooks/signatures build-specific
src/iee/core/config.h/.cpp             feature flag
src/iee/dll_main.cpp                   prepare/shutdown
src/iee/game/opengl_types.h/.cpp       fonctions/constantes GL requises
CMakeLists.txt                         sources, libs MF/MCI, bundle assets
tests/iee_tests.cpp                    contrats manifest/state mapping
tools/InfinityEngine-Enhancer.sample.ini
```

Le module actuel est mono-asset et ses dimensions, noms, cadence, frame count,
rectangle, indices WED et correction colorimétrique sont codés en dur. Avant un
deuxième asset simultané, extraire un `TransitionSpec` immuable et un état de lecture
par asset. Ne pas dupliquer les globals : deux transitions concurrentes partageraient
sinon serial, décodeur, audio, texture et état de porte.

## 10. Build, bundle et installation

Build Windows utilisé dans ce workspace :

```powershell
cd G:\AI\BG2_Upscale\engine\InfinityEngine-Enhancer\source-patchee
cmake --build build-filter-diagnostic-v142 --config Release `
  --target release_bundle iee_tests -- /m:2
ctest --test-dir build-filter-diagnostic-v142 -C Release --output-on-failure
```

Vérifier dans le bundle :

```text
build-filter-diagnostic-v142/release-bundle/InfinityEngine-Enhancer.dll
build-filter-diagnostic-v142/release-bundle/iee-assets/<asset-directory>/...
```

Installation :

1. vérifier que `Baldur`, `BaldurReal` et `InfinityLoader` sont fermés ;
2. sauvegarder la DLL, l'INI et les assets installés dans un dossier horodaté ;
3. copier le bundle vers la racine du jeu ;
4. activer le flag INI ;
5. lancer uniquement `InfinityLoader.exe` ;
6. comparer SHA-256 source/installé.

Flag historique AR1300 :

```ini
[Shaders]
EnableBridgeTransitionPreview = true
```

Le nom conserve `Preview` pour compatibilité de configuration ; la fonction levier
bidirectionnelle est validée.

## 11. QA obligatoire

### 11.1 Contrats hors jeu

- SHA-256 de tous les assets conforme au manifeste ;
- `ffprobe` : dimensions, fps, frame count, durée, pixel format ;
- paire avant/arrière identique frame par frame après inversion ;
- BGRA exactement `width × height × 4` ;
- première/dernière frame cohérentes avec les crops natifs ;
- build Release réussi ;
- `ctest` à 100 % ;
- signatures/RVA testés dans `iee_tests`.

### 11.2 Matrice en jeu

- chargement sauvegarde porte fermée : aucune animation au chargement ;
- chargement sauvegarde porte ouverte : aucune animation au chargement ;
- fermé → ouvert : forward complet + audio ;
- ouvert → fermé : reverse complet + audio ;
- inversion à ~25 %, ~50 % et ~75 % dans les deux sens ;
- aucun flash de l'état WED opposé au démarrage ou au seek ;
- disparition exacte après la dernière frame ;
- caméra déplacée, zoom min/max, redimensionnement/fenêtré/plein écran ;
- dialogue, icônes de ramassage, HUD normal, inventaire, statistiques, menu Échap,
  quitter le jeu : toujours au-dessus de l'asset ;
- asset toujours au-dessus de la carte ;
- couleur contrôlée en haut-gauche, centre, bas-droit et sur plusieurs frames ;
- feather non visible comme rectangle ;
- aucune pause/hitch anormale ;
- aucune erreur GL, MF ou MCI dans `InfinityEngine-Enhancer.log`.

Ligne de diagnostic attendue pendant lecture :

```text
AR1300 bridge map target: framebuffer=<0-or-nonzero>, viewport=(...), rect=(...),
scroll=(...), world-view=(...)
```

Observation de la session validée : `framebuffer=0`, viewport `2520×1360`. La
preuve de bonne couche est la QA visuelle carte/HUD, pas la valeur numérique du FBO.

### 11.3 Gate d'acceptation

Ne marquer `validated` que si ouverture, fermeture, retournement en cours de lecture,
masquage de la bascule WED et ordre carte/HUD sont tous validés par l'utilisateur.
Conserver séparément le statut de qualité du média (`classic-resize`, `seedvr-x4-pending`,
`seedvr-x4-validated`).

## 12. Diagnostic par symptôme

| Symptôme | Cause prioritaire | Correctif |
|---|---|---|
| Son, aucune image, GL sans erreur | commandes carte différées exécutées après l'overlay | appeler `DrawFlush_GL` avant l'overlay dans le FBO carte |
| Image derrière la carte | mauvais point d'insertion ou file native non vidée | utiliser la fin de `CGameArea::Render` + flush |
| Image devant inventaire/menus | rendu à `SwapBuffers` | déplacer dans le FBO carte |
| Fade visible au contact du HUD | masque/scissor HUD tardif | supprimer le masque ; corriger la couche de rendu |
| Flash porte opposée avant vidéo | absence d'endpoint hold | afficher immédiatement l'ancien endpoint BGRA |
| Fermeture ou inversion incorrecte | confusion frame logique/frame asset | appliquer `closing = N-1-logical` |
| Freeze au retournement | GOP non seekable ou queue obsolète | flux inverse tout-intra + serial d'annulation |
| Vidéo retournée verticalement | double flip MF/OpenGL | conserver une convention top-scanline unique |
| Bon raccord local, mauvais ailleurs | correction RGB globale insuffisante | ajouter une grille de gain spatiale mesurée |
| F9 sans effet | hotkey interrogé hors callback visible/zone filtrée | traiter F9 dans le callback de rendu carte et vérifier la zone |
| Mauvais placement selon viewport | origine viewport ajoutée deux fois | coordonnées locales ; ne pas ajouter `viewport[0:2]` |

## 13. Référence AR1300 et travail restant

```text
Zone                 AR1300
Objet WED            BRIDGE01
Rectangle monde      2848,1984 512×512
Média actuel         2048×2048, 124 frames, 24 fps, 5.166667 s
Génération actuelle  Lanczos classique, sans upscale IA
Déclenchement         indices WED réellement rendus
Ouverture             validée
Fermeture             validée
Inversion live        validée
Masquage bascule WED  validé par endpoints BGRA
Couche map/HUD        validée avec DrawFlush_GL dans le FBO carte
Travail restant       produire et tester la vidéo SeedVR2 7B x4
```

Pour le test SeedVR2 7B x4 : ne modifier ni rectangle, cadence, frame count,
state machine, hooks, ordre de rendu, audio, feather ou convention logique. Remplacer
uniquement les frames/vidéos et régénérer les deux endpoints ; recalibrer la
colorimétrie si les sorties SeedVR changent les distributions RGB. Refaire toute la
matrice QA visuelle avant de remplacer le statut `seedvr-x4-pending`.
