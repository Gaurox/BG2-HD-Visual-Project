# Fondation xN — sprites de créature et composites Character

## Statut et périmètre

Cette phase généralise le contrat d'échelle et l'activation runtime. Elle ne valide aucun asset
ingame et ne rend pas encore possible un Character complet en x4 dans un registre monolithique.

Sources de vérité :

- identité et inventaire : `sprite/index/manifest.json` et ses quatre CSV ;
- workflow historique x2 : `sprite/SPRITE_UPSCALE_PIPELINE.md` ;
- job explicite : bloc top-level `upscale` ;
- sortie : `build/build-manifest.json` puis en-tête binaire du registre ;
- compatibilité runtime : `runtime/runtime-manifest.json` ;
- activation : `[Shaders] EnableCreatureSpriteUpscaleTest` dans
  `InfinityEngine-Enhancer.ini`.

Ne pas renommer les schémas de job et de build existants pendant cette fondation. La présence du
bloc `upscale` distingue le chemin xN explicite du chemin V2 historique.

## Contrat d'échelle explicite

Un job individuel ou un set xN doit porter exactement un des blocs suivants :

```json
"upscale": {
  "scale": 2,
  "algorithm": "XBR/xbr2X",
  "passes": 1,
  "antialias": false,
  "xbr_blend": false
}
```

```json
"upscale": {
  "scale": 4,
  "algorithm": "XBR/xbr4X",
  "passes": 1,
  "antialias": false,
  "xbr_blend": false
}
```

Le x4 est un appel direct à `XBR/xbr4X` en une passe. Ne jamais construire le x4 par deux passes
`xbr2X`. Toute autre échelle, combinaison algorithme/échelle, activation de l'anti-alias ou de
`xbr_blend` est bloquante.

Un job sans `upscale` reste un job historique : x2, `XBR/xbr2X`, registre V2
`CreatureSprites-X2.registry`. Ne pas convertir implicitement ses manifestes.

Créer un job explicite sans éditer le JSON à la main en passant une seule fois l'échelle au
runner. Le template fournit l'identité, les chemins, la compatibilité et les outils ; `--scale`
fixe ensemble l'algorithme direct, le suffixe attendu du job et le contrat V3 :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py new-character-job `
  --job sprite/jobs/<job>-xbr4x.json `
  --template-job sprite/jobs/human-female-fighter-chfb1-xbr2x.json `
  --scale 4 `
  --ids-symbol <SYMBOLE_ANIMATE_IDS> `
  --animation-id 0xFFFF `
  --armor-code <1..MAX>
```

La même option s'applique à `new-character-equipment-job`. Sans `--scale`, la commande hérite
strictement du contrat du template afin de préserver les jobs historiques. Pour conserver les PNG
de frames, utiliser `--keep-upscaled-frames`; `--keep-x2-frames` reste un alias de compatibilité.

## Géométrie et composition

Conserver en unités natives x1 pour chaque BAM et chaque frame :

- largeur et hauteur logiques ;
- centres, pivots et offsets ;
- cycles, lookups, cadence, ordre des directions et palette ;
- arguments de dessin et rectangle logique fournis au moteur.

Le backing physique vaut exactement `scale × largeur_x1` par `scale × hauteur_x1`. Utiliser
`NEAREST`, `CLAMP_TO_EDGE`, aucun mipmap et niveau maximal zéro.

Avant toute allocation, le runtime exige une lecture GL valide et strictement positive de
`GL_MAX_TEXTURE_SIZE`, puis vérifie les deux dimensions physiques. Une erreur GL, une capacité nulle
ou un dépassement conserve le rendu natif.

Pour un Character, calculer l'union des calques actifs dans le repère x1 à partir de leurs centres,
puis ajouter la bordure logique native d'un pixel. Multiplier une seule fois le backing final par
l'échelle. Ne jamais multiplier centres, offsets, rectangle de dessin ou bordure avant le calcul de
l'union. Un calque actif absent, une capture palette manquante ou une dimension divergente impose le
fallback natif du personnage entier.

## Registre et manifeste V3

Tout job explicite produit :

```text
registry=iee-assets/creature-sprites/CreatureSprites-XN.registry
registry_magic=IEECSXN
registry_version=3
registry_scale=2|4
```

Le manifeste répète exactement le bloc `upscale` dans `method`. Il expose aussi les compteurs
dynamiques `x{scale}_pixel_count` ou `x{scale}_index_bytes`, le flag
`kept_individual_x{scale}_frames` pour un job individuel et la validation
`dimensions_exact_x{scale}`.

L'en-tête binaire fait 24 octets : magic ASCII nul-terminé sur 8 octets, puis `version`, `scale`,
`resource_count` et `animation_id`, quatre entiers non signés little-endian. L'installateur doit
comparer ces valeurs au job et au manifeste avant copie.

Au runtime, `prepare(directory)` conserve son API. Il cherche d'abord
`CreatureSprites-XN.registry`; si ce fichier est absent, il retombe sur
`CreatureSprites-X2.registry`. Un fichier XN présent mais invalide ne doit jamais être interprété
comme un pack V2.

## Activation et régression x2

La clé primaire est :

```ini
[Shaders]
EnableCreatureSpriteUpscaleTest = true
```

`EnableCreatureSpriteX2Test` reste un alias d'activation pour les installations et tests de
régression existants. Le runtime est actif si l'une des deux clés est vraie. L'installateur xN écrit
la clé primaire à `true` et l'alias à `false` afin de tester explicitement le nouveau chemin ; la
restauration remet l'INI complet sauvegardé.

## Gates avant installation

Exiger toutes les égalités suivantes :

```text
job.upscale == build.method
job.job_id == build.job_id == runtime.job_id
job.animation.id == build.animation_id == registry.animation_id
job.animation.runtime_profile == build.runtime_profile == runtime.runtime_profile
build.registry_magic/version/scale == registry.magic/version/scale
build.registry_bytes/sha256/resource_count == fichier registre
runtime.status=built-tested
runtime.tests_status=passed
runtime.dll_sha256 == fichier DLL
job.compatibility.baldur_real_sha256 == BaldurReal.exe
```

Exiger aussi `dimensions_exact_x{scale}=frame_count` pour un job individuel, zéro collision BAM
hors paperdoll dans `override`, aucun autre test sprite actif et aucun processus `InfinityLoader`,
`Baldur` ou `BaldurReal`.

La validation QA explicite exige dans la même session de log
`source=CreatureSprites-XN.registry`, `scale=x{scale}` et `filter=NEAREST`. Elle recalcule aussi les
hashes de toutes les cibles consignées par l'installation avant d'autoriser
`validated-installed`. Un fallback V2 ou un fichier remplacé après installation invalide la QA.

## Installation et restauration réversibles

Le runner route un job avec `upscale` vers les scripts xN. Les commandes directes de diagnostic
sont :

```powershell
powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Install-CreatureSprite-XN-Test.ps1 `
  -JobFile sprite/jobs/<job>.json

powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-XN-Test.ps1 `
  -JobFile sprite/jobs/<job>.json
```

Ne les exécuter qu'après un `plan` et un `prepare` vérifiés. Aucun de ces scripts ne lance le jeu.
L'installation dérive la source et la cible du registre depuis `build.registry`, vérifie job,
build, runtime, hashes et en-tête, puis sauvegarde DLL, INI, registre XN et éventuel registre X2.
La restauration refuse toute cible modifiée depuis l'installation et restaure exactement présence,
absence et hashes initiaux.

L'installateur publie l'état `installing` avant sa première mutation. Après une interruption du
processus ou de la machine, fermer le jeu, vérifier le job puis utiliser le mode de récupération :

```powershell
powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-XN-Test.ps1 `
  -JobFile sprite/jobs/<job>.json `
  -RecoverInstalling
```

Ce mode vérifie toutes les sauvegardes avant d'écraser les cibles potentiellement partielles. Il
n'est accepté que pour un état actif `installing`.

Pour revenir au code antérieur à la fondation, utiliser la baseline Git `84e17b6` sur la branche de
travail `feature/creature-sprite-xn`, ou la sauvegarde locale documentée dans
`_rollback/creature-sprite-xn-pre-20260825/README.md`. Ne pas écraser les changements sans rapport
présents dans le worktree.

## Limite bloquante avant un Character complet

Le registre V3 de cette phase reste monolithique et conserve les limites runtime de 128 ressources
et 128 Mio. Le coût pixel croît avec le carré de l'échelle ; un bundle Character qui tient en x2
peut donc dépasser la limite en x4 sans ajouter de ressource.

Avant de produire ou installer un Character complet x4, implémenter et valider un registry-set avec
sharding/multi-pack : manifeste de set, partition déterministe, absence de resref dupliqué entre
shards, somme de hashes et compteurs, chargement atomique de tous les shards et fallback natif du
Character entier si un shard manque ou échoue. Tant que ces gates n'existent pas, limiter x4 à des
packs de fondation sous les deux plafonds et ne jamais déclarer le character-set complet.

Cette fondation ne produit aucun élément `validated-installed` et ne modifie pas le manifeste de
release.
