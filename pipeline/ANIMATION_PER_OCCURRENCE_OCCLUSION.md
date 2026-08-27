# Masques d'occlusion par occurrence — implémentation et gates QA

**Statut au 2026-08-27 : runtime et chaîne de production v3 implémentés. Gates automatisés
franchis : `iee_tests` + `iee_bridge_worker_tests` (2/2), tests Python animation (26/26), dont
les variantes par position. Le lot `combined-20260827-ar0900-two-manual-masks-v3` est installé
avec AR0900 en registre v3, deux variantes AM0900DM et la DLL qui normalise
`ARE.y = drawingY - height` ; les anciens overrides `AR0900.ARE` et `AM0900DN.BAM` sont absents.
La QA en jeu des deux occurrences et de leurs masques est validée par l'utilisateur sur sauvegarde
ancienne et nouvelle : AM0900DM est `validated-installed`. La DLL installée contient en plus le
garde-fou de teinte liquide décrit dans `WATER_MAP_PIPELINE.md`, encore `pending-qa`. Aucun manifeste
de release ni catalogue n'a été modifié.**

Sauvegarde de restauration de l'installation courante :
`animations/packs-par-zone/combined-20260827-ar0900-two-manual-masks-v3/install-backups/per-area-backup-20260827-031740`.

## Problème

Une animation de décor qui passe derrière un élément du décor doit être occultée. Le runtime x4
contourne l'occlusion native du moteur (limitation connue, voir
[`../animations/UPSCALE_ANIMATIONS_ZONE.md`](../animations/UPSCALE_ANIMATIONS_ZONE.md) § 8), et la
parade retenue est de **cuire l'occulteur dans l'alpha** à partir d'un masque peint à la main.

Cette parade se heurte à une limite d'architecture : le runtime indexe une texture de remplacement
sur le **seul resref BAM**. Deux occurrences du même resref dans une zone partagent donc la même
texture et ne peuvent pas recevoir deux masques différents. Or leur décor diffère : sur `AR0900`
les deux sphères sont en miroir.

Le contournement actuel (repointer une occurrence sur un resref dupliqué via un override `.ARE`,
voir `Install-AreaOverrideAssets.ps1`) fonctionne sur une partie neuve, mais il est
**inutilisable dans un paquet distribué**.

### Pourquoi l'override `.ARE` ne peut pas être livré

Une sauvegarde Infinity Engine **embarque sa propre copie du `.ARE`** de chaque zone déjà visitée,
et cette copie prime sur `override/`. Vérifié le 2026-08-27 sur les sauvegardes du projet : 5 des
28 parties contiennent un `AR0900.are` de 104 à 114 Ko, table d'animations intacte, occurrence sud
pointant toujours sur `AM0900DM`.

Conséquence pour un joueur qui installerait le patch :

- partie neuve, ou zone jamais visitée → le repointage s'applique, rendu correct ;
- **partie existante ayant déjà visité la zone → le repointage est ignoré**, l'occurrence reçoit le
  masque de l'autre occurrence, et le rendu est faux.

Patcher les sauvegardes de l'utilisateur final n'est pas une option. **Le correctif décrit ici
n'est donc pas un confort : c'est le prérequis à toute distribution d'un masque par occurrence.**
Il est immunisé par construction, parce que la position lue dans `CGameStatic` provient de l'`ARE`
réellement chargé — sauvegardé ou non, elle est identique — et parce qu'il ne modifie aucun fichier
de jeu.

Le coût annexe reste par ailleurs : un `.ARE` en override est un point de conflit avec tout autre
mod touchant la zone, et la duplication de BAM double la charge mémoire de la ressource.

### Ampleur mesurée

Sur `animations/index/occurrences.csv` et `ressources.csv` :

| Population | Nombre |
|---|---:|
| Paires (zone, resref) | 633 |
| dont plusieurs occurrences dans la même zone | 322 |
| dont ressource *blended* | 251 |
| **dont occultable et sprite ≥ 50×50 px x1** | **53** |

Les 251 tombent à 53 parce que la majorité sont `FIRE_4` et `FLAME2S`, des flammèches minuscules
presque toujours marquées « jamais occultée » (bit 6 des flags ARE).

Ces 53 cas couvrent 24 ressources et 31 zones. Le plus lourd est `AR0414` avec `DSTDVL1A` posée
11 fois. Sans ce correctif, ce sont 53 overrides `.ARE` et 53 BAM dupliqués à livrer.

## Contrat moteur implémenté

| Élément | Emplacement | Constat |
|---|---|---|
| Lecture de l'objet | [`hooks.cpp`](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp) `read_area_animation_frame` | Lit resref, frame, séquence, X, Y de dessin et hauteur depuis `CGameStatic` ; normalise `ARE.y = drawingY - height` ; utilise `kAnyWorldPosition` si les offsets sont absents |
| Résolution | [`area_animation_x4_registry.h`](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_animation_x4_registry.h) | `resolve_frame(resref, worldX, worldY, sequence, currentFrame, …)` |
| Appariement | [`area_animation_x4_registry.cpp`](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_animation_x4_registry.cpp) | Deux passes : position exacte liée, puis variante libre |
| Offsets BG2EE 2.7.3 | [`build_manifest.h`](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/build_manifest.h) / [`.cpp`](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/build_manifest.cpp) | `gameStaticPositionX = 0x0C`, `gameStaticPositionY = 0x10`, `gameStaticHeight = 0x14`, optionnels et ajoutés en fin d'initialiseur |
| Cache texture | [`area_animation_x4_registry.cpp`](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_animation_x4_registry.cpp) | Clé inchangée : `FrameHandle {resourceIndex, frameIndex}` |

**Conséquence de conception heureuse** : le cache est indexé par `resourceIndex`, pas par resref.
Si deux ressources distinctes partagent un resref et se distinguent par leur position, le cache et
`bind_frame_texture` **n'ont pas à changer**. C'est ce qui rend ce correctif petit.

## Conception retenue

Autoriser plusieurs `Resource` portant le même resref, départagées par une position monde
optionnelle. Une ressource sans position reste le comportement actuel, ce qui garde les 25 packs
de zone déjà installés valides tant qu'ils ne sont pas régénérés.

### 1. Offsets de position — RÉSOLUS le 2026-08-27 par analyse statique et observation runtime

Le désassemblage de `CGameStatic::RenderBam` (RVA `0x1F2B50`, BG2EE 2.7.3 x86-64,
`ImageBase 0x140000000`) identifie les trois champs et leur relation. L'observation runtime
d'AR0900 établit lequel est le Y de dessin et confirme la formule de normalisation.

| Offset | Taille | Rôle |
|---|---|---|
| **`+0x0C`** | int32 | **position monde X de l'ARE, en pixels** |
| **`+0x10`** | int32 | **Y de dessin, égal à `ARE.y + height`** |
| **`+0x14`** | int32 | **hauteur (`height` de l'entrée ARE)** |
| `+0x94` | int32 | flags de l'animation (le `test …, 0x1000` du prologue) |

Preuve, dans le prologue de `RenderBam` :

```asm
mov   rbx, rcx                 ; rbx = this (CGameStatic)
mov   eax, [rcx+0x10]          ; Y
sub   eax, [rcx+0x14]          ; moins height
idiv  <cst 64>                 ; -> ligne de tuile
movsx ecx, word [r9+0xbbc]     ; largeur de la zone, en tuiles
mov   eax, [rbx+0x0c]          ; X
imul  r8d, ecx                 ; ligne * largeur
idiv  <cst 64>                 ; -> colonne de tuile
add   ax, r8w                  ; index = ligne*largeur + colonne
cmp   eax, [r9+0xbb8]          ; borné par le nombre de cellules
```

C'est le test de brouillard de guerre par cellule. Il établit que `+0x0C` est le X monde et que
`+0x10 - +0x14` est le Y brut de l'ARE : divisés par 64 ils donnent la tuile, et l'index composé
est borné par le nombre de cellules de la zone.

Corroboration indépendante : `+0x94` est testé contre `0x1000`, or le bit 12 est positionné sur
les six entrées d'animation d'`AR0900` — c'est bien le champ `flags` de l'`ARE`. Et le champ
`height` de l'`ARE` (offset `+0x38` de l'entrée) vaut `-7` et `-13` pour les deux sphères
d'`AR0900`, `30` et `42` pour les `FLAME2M` : non nul, ce qui explique la soustraction.

**Confirmation runtime du 2026-08-27** : les lectures dans AR0900 ont donné `(2246,2174)` pour
l'occurrence nord et `(1689,2655)` pour l'occurrence sud. Les hauteurs ARE correspondantes sont
`-13` et `-7`, donc `2174 - (-13) = 2187` et `2655 - (-7) = 2662`. Cela invalide l'hypothèse que
`+0x10` reproduit directement `ARE.y` et confirme `drawingY = ARE.y + height`.

**Appariement** : utiliser `+0x0C` pour X et `+0x10 - +0x14` pour Y. Sur `AR0900`, on retrouve
exactement les positions déclarées `(1689,2662)` et `(2246,2187)`.

**Journalisation runtime** : le registre conserve un échantillon borné des positions sans
correspondance. Une position absente échoue fermée et laisse le moteur dessiner son BAM natif.

### 2. Registre v3

Le format v2 est documenté dans
[`../animations/UPSCALE_ANIMATIONS_ZONE.md`](../animations/UPSCALE_ANIMATIONS_ZONE.md) § 10.
L'en-tête (`magic[8]`, `version`, `scale`, `resourceCount`, `reserved`) ne change pas ; seul
`version` passe à 3. Après les quatre champs de cadence, ajouter :

```text
ResourceV3
  … champs v2 inchangés …
  positionMode                 # 0 = toute occurrence, 1 = liée à une position
  worldX / worldY              # int32, ignorés si positionMode == 0
  variantIndex                 # uint32 ; 0 garde le nom historique des assets
  … frames[] et cycles[] inchangés …
```

Les assets de la variante 0 gardent `AAX4-RESREF-frameNNN.rgba`. Les variantes suivantes sont
nommées `AAX4-RESREF-vN-frameNNN.rgba`. Le suffixe est déclaré par `variantIndex`, jamais déduit de
l'ordre de chargement.

Le parseur doit accepter v1, v2 **et** v3 — les packs déjà installés ne doivent pas cesser de
fonctionner. Toute valeur hors domaine fait échouer le pack fermé, comme aujourd'hui.

### 3. Appariement

```text
resolve_frame(resref, worldX, worldY, sequence, currentFrame, out)
```

Règle, dans cet ordre :

1. une ressource `positionMode == 1` dont la position correspond **exactement** ;
2. sinon une ressource `positionMode == 0` portant ce resref ;
3. sinon échec — le moteur rend son BAM d'origine.

L'ordre compte : la variante liée prime, la variante libre sert de défaut. Deux ressources liées à
la même position et au même resref doivent être **refusées au chargement**, pas départagées à
l'exécution.

Ne jamais apparier sur une distance ou une tolérance. Une position est une clé, pas une mesure.

### 4. Fichiers moteur touchés

| Fichier | Nature |
|---|---|
| `game/build_manifest.h` / `.cpp` | Deux champs d'offset + validation + signature |
| `area_animation_x4_registry.h` | Signature de `resolve_frame` |
| `area_animation_x4_registry.cpp` | Parsing v3, champs de `Resource`, appariement |
| `hooks.cpp` | Lire la position dans `read_area_animation_frame`, la transmettre |

`bind_frame_texture`, le cache LRU, `prepare_for_area`, `flush_retired_textures` et le
scheduler `TimedTimeline` **ne changent pas**.

### 5. Chaîne de production

| Script | Évolution |
|---|---|
| `run_animation_upscale_30fps_v2.py` | `registry_v2_from_resources` → écrire v3 ; `validate_v2_pack` accepte `position` |
| `split_animation_pack_by_area.py` | Propager la position lors du découpage |
| `build_blended_rgb_neutral_pack.py` | `--mask-anchor-x1` devient aussi la **position déclarée** de la variante produite |
| `merge_area_pack_resources.py` | Fusionner des variantes de même resref via `CHEMIN::X,Y`, attribuer les index et renommer les assets ; aucun nouveau resref BAM |
| `combine_area_pack_splits.py` | Inchangé |

Le flux utilisateur cible, par occurrence à traiter :

1. générer l'assemblage carte + animation au format de l'union des phases ;
2. peindre le masque (blanc conserve, noir retire, aplati) ;
3. `build_blended_rgb_neutral_pack.py --mask-png … --mask-anchor-x1 X Y` ;
4. `merge_area_pack_resources.py --pack <nord>::2246,2187 --pack <sud>::1689,2662 …` pour réunir les variantes de la zone ;
5. `combine_area_pack_splits.py` puis `Install-AreaAnimations-PerArea.ps1`.

Plus aucun override `.ARE`, plus aucun BAM dupliqué.

### 6. Tests exigés avant toute QA en jeu

Côté moteur (`tests/iee_tests.cpp`) :

- registre v1, v2 et v3 chargés côte à côte ;
- deux variantes même resref / positions distinctes → chacune résout sa propre `resourceIndex` ;
- variante liée + variante libre → la liée prime ;
- deux variantes même resref **même** position → chargement refusé ;
- `positionMode` ou dimensions hors domaine → pack refusé fermé ;
- manifeste sans offset de position → le mode par position se désactive proprement, les packs v1/v2
  continuent de fonctionner.

Côté Python (`pipeline/tests/`) :

- écriture et relecture du registre v3, y compris l'aller-retour de la position ;
- découpage par zone préservant les variantes ;
- fusion refusant deux variantes de même position ;
- immutabilité et `--resume` inchangés.

## Gates et repli

1. **Gate offset** : franchi pour BG2EE 2.7.3 par le calcul de brouillard dans `RenderBam` et les
   valeurs runtime d'AR0900 : nord `(2246,2174,-13)` → `(2246,2187)`, sud
   `(1689,2655,-7)` → `(1689,2662)`.
2. **Gate compatibilité** : les 25 packs de zone installés doivent charger sans régénération.
3. **Gate mémoire** : une variante par occurrence multiplie la charge d'une ressource par son
   nombre d'occurrences. `AR0414` avec 11 occurrences de `DSTDVL1A` est le pire cas du projet et
   doit être chiffré **avant** de coder — s'il dépasse 512 MiB, il faudra n'attacher un masque
   qu'aux occurrences qui en ont visiblement besoin et laisser les autres sur la variante libre.
4. **Repli** : le mode par position se désactive si le manifeste n'a pas l'offset ; le runtime
   retombe alors exactement sur le comportement actuel.
5. Ne jamais supprimer les packs, prototypes ou sauvegardes existants.

## Ce que ce correctif ne résout pas

- Il **ne supprime pas** le masque peint à la main. Il supprime seulement l'override `.ARE` et la
  duplication de BAM.
- Il ne restaure pas l'occlusion native du moteur. Faire respecter les polygones `cover animations`
  du WED reste une autre voie, non chiffrée : les 76 polygones d'`AR0900` ne couvrent que ~5 % du
  cadre du sprite, ce qui **ne correspond pas** à l'occultation observée en vanilla. Le mécanisme
  réel n'est pas identifié ; ne pas partir sur cette voie sans l'avoir établi.

## Mesure du 2026-08-27 — le moteur n'occulte pas

Test conduit sur `AR0900` : sphère nord inchangée (témoin, byte-identique), sphère sud servie par
`AM0900DN` avec fondu et prémultiplication mais **sans masque**. Une seule variable modifiée.

**Résultat validé par l'utilisateur : l'anneau sud est entier et flotte par-dessus tout le décor.**

Conséquences :

1. Le contournement de l'occlusion par le runtime est **total**, pas partiel. Aucune occultation
   résiduelle n'est appliquée par le moteur sur les animations remplacées.
2. Le masque peint à la main reste **indispensable** pour chaque occurrence occultable.
3. Les « encoches rectangulaires » soupçonnées auparavant sur la sphère sud n'ont pas été
   reproduites : absentes des frames source (ancres et phases interpolées équivalentes), absentes
   des masques (une seule composante connexe, aucun blob parasite), et la grille 8 px du screenshot
   JPEG présente un blocking de ×1,11. **Attribuées à la compression du screenshot** ; ce n'était
   pas un défaut de la chaîne. Le gate qui conditionnait ce correctif à leur élucidation est levé.

Le correctif décrit ici garde donc tout son intérêt, et son périmètre est confirmé : supprimer la
tuyauterie (override `.ARE`, duplication de BAM), jamais l'étape de peinture.

## Références

- Runtime : `engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_animation_x4_registry.*`
- Hooks : `engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp`
- Règles de hooking : `engine/InfinityEngine-Enhancer/source-patchee/AGENTS.md`
- Format de registre : [`../animations/UPSCALE_ANIMATIONS_ZONE.md`](../animations/UPSCALE_ANIMATIONS_ZONE.md) § 10
- Packs par zone : [`ANIMATION_PACKS_PAR_ZONE.md`](ANIMATION_PACKS_PAR_ZONE.md)
- Corrections alpha : [`ANIMATION_ALPHA_CORRECTIONS.md`](ANIMATION_ALPHA_CORRECTIONS.md)
