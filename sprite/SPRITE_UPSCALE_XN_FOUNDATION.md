# Fondation xN — sprites de créature et composites Character

## Statut et périmètre

Cette phase généralise le contrat d'échelle, ajoute le registry-set shardé et conserve les chemins
monolithiques historiques. Elle ne valide encore aucun asset ingame. Le registry-set lève le
plafond monolithique pour un Character complet sans charger tous ses payloads en mémoire.

Sources de vérité :

- identité et inventaire : `sprite/index/manifest.json` et ses quatre CSV ;
- workflow historique x2 : `sprite/SPRITE_UPSCALE_PIPELINE.md` ;
- job explicite : bloc top-level `upscale` ;
- sortie : `build/build-manifest.json`, puis index de set ou en-tête binaire du registre ;
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

## Registres V3 et registry-set

Le manifeste répète exactement le bloc `upscale` dans `method`. Un bundle explicite fixe
`registry_layout` à `monolith` ou `set` et conserve `registry_magic=IEECSXN`,
`registry_version=3` et `registry_scale=2|4` pour les registres de données. Un build individuel ou
monolithique antérieur peut omettre `registry_layout` ; il reste interprété strictement comme
monolithe, jamais comme set. Le manifeste expose aussi les compteurs dynamiques
`x{scale}_pixel_count` ou `x{scale}_index_bytes`, le flag
`kept_individual_x{scale}_frames` pour un job individuel et la validation
`dimensions_exact_x{scale}`.

Un monolithe utilise les champs historiques :

```text
registry_layout=monolith
registry=iee-assets/creature-sprites/CreatureSprites-XN.registry
registry_set=null
shards=[]
```

Son en-tête V3 fait 24 octets : magic `IEECSXN\0` sur 8 octets, puis `version=3`, `scale`,
`resource_count` et `animation_id`, quatre entiers non signés little-endian. Il reste borné à
128 ressources. Son plafond physique dépend de l'échelle : 128 Mio en x2, 512 Mio en x4.

Un set utilise :

```text
registry_layout=set
registry=null
registry_set=iee-assets/creature-sprites/CreatureSprites-XN.set
shards[0].registry=iee-assets/creature-sprites/CreatureSprites-XN-0000.registry
```

Les noms de shards sont contigus à partir de `0000`. Chaque entrée de `shards` répète `index`,
`registry`, `sha256`, `crc32`, `resource_count`, `frame_count`, `index_bytes` et
`registry_bytes`. Les champs top-level `total_resources`, `total_frames`, `total_index_bytes` et
`total_registry_bytes` doivent être égaux à la somme des entrées ; `registry_set_bytes` est la
taille propre de l'index. Chaque shard est un registre XN
V3 autonome, limité à 128 ressources et à 128 Mio en x2 ou 512 Mio en x4. Les 512 Mio x4 sont la
capacité physique équivalente au budget logique x2 de 128 Mio : le nombre d'indices croît avec le
carré de l'échelle. Un set accepte au plus 64 shards,
8192 ressources, 1 048 576 frames et 8 Gio de registres cumulés.

Le payload indexé d'une frame individuelle reste limité à 128 Mio, quelle que soit l'échelle : le
cache lazy doit pouvoir matérialiser au moins une frame entière. Cette borne par frame est distincte
du total d'un shard x4 à 512 Mio et doit être vérifiée par le preflight, l'inspecteur Python,
l'installateur et le runtime.

Le build xBR traite l'ordre canonique des frames en lots dont la sortie projetée vise au plus
64 Mio. Il écrit les records et payloads du registre directement dans le flux de sortie et ne
conserve que cinq PNG d'échantillon par ressource. Une frame individuelle dépassant le budget de
lot forme un lot singleton, mais reste refusée si elle dépasse la limite lazy de 128 Mio. Le bloc
`xbr_batching` du manifeste de build consigne le budget, le nombre de lots et leur maximum réel.

`CreatureSprites-XN.set` commence par un en-tête little-endian de 56 octets :

| Offset | Type | Valeur |
|---:|---|---|
| 0 | 8 octets | magic `IEECSNS\0` |
| 8 | `u32` | version `1` |
| 12 | `u32` | échelle `2|4` |
| 16 | `u32` | nombre de shards |
| 20 | `u32` | total de ressources |
| 24 | `u32` | animation ID |
| 28 | `u32` | réservé, zéro |
| 32 | `u64` | total de frames |
| 40 | `u64` | total d'octets indexés |
| 48 | `u64` | total d'octets des registres |

Il est suivi d'une entrée de 64 octets par shard : SHA-256 binaire sur 32 octets, CRC32 IEEE du
fichier complet en `u32`, `resource_count` en `u32`, puis `frame_count`, `index_bytes` et
`registry_bytes` en `u64`. L'index ne contient pas de chemin arbitraire : le rang de l'entrée
dérive le nom canonique du shard.

Au runtime, `prepare(directory)` conserve son API et applique cet ordre : set, monolithe XN, puis
registre X2 historique. L'absence autorise le niveau suivant ; la présence d'un set ou monolithe
invalide échoue fermée et n'autorise aucun fallback vers un format de priorité inférieure. Le rendu
natif reste disponible.

La publication du set est atomique au niveau de l'index et des métadonnées : le runtime valide
séquentiellement l'index, les SHA/CRC, les structures, les totaux et l'unicité des resrefs avant de
rendre le set visible. Il ne conserve pas tous les payloads en RAM. Les indices de frames sont lus
à la demande dans un cache LRU borné à 128 Mio. Une erreur de lecture ou de validation lazy
désactive le set et impose le fallback natif du Character entier.

Tout monolithe XN V3, x2 comme x4, utilise le même chargement lazy et le même cache de 128 Mio :
`prepare` valide sa structure complète et conserve métadonnées et offsets, puis le runtime revalide
taille et date du fichier avant chaque résolution de frame, ainsi qu'avant et après chaque lecture.
Une disparition, modification ou lecture partielle désactive le chemin XN et impose le rendu natif,
y compris si indices ou textures avaient déjà été mis en cache. Seul le registre historique X2
V1/V2 reste entièrement résident ; il ne reçoit aucune nouvelle sémantique.

### Reprise x2 sans recalcul xBR

Un set explicite x2 peut reprendre des registres membres V2 x2 déjà construits. Le pipeline
réécrit seulement leur en-tête en V3, conserve à l'identique les records et payloads, puis repasse
les contrôles de structure, géométrie, compteurs et hashes avant le sharding. Il ne relance pas
Scalepix. Utiliser ce chemin pour valoriser les assets x2 vérifiés existants et éviter de dépenser
des crédits ou du temps de calcul sans changement pixel.

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
runtime.status=built-tested
runtime.tests_status=passed
runtime.dll_sha256 == fichier DLL
job.compatibility.baldur_real_sha256 == BaldurReal.exe
```

Pour `registry_layout=monolith`, exiger en plus :

```text
build.registry_bytes/registry_sha256/resource_count/frame_count == fichier registre
build.registry_set == null
build.shards == []
```

Pour `registry_layout=set`, exiger avant toute copie :

```text
build.registry == null
build.registry_set_sha256 == SHA256(CreatureSprites-XN.set)
build.registry_set_bytes == taille(CreatureSprites-XN.set)
index.magic/version/scale/animation_id == IEECSNS/1/job.scale/job.animation.id
index.shard_count == longueur(build.shards)
index.entries[*] == build.shards[*] == en-têtes et fichiers shards
SHA256 et CRC32 de chaque shard == index et build.shards
totaux index == totaux manifeste == sommes des shards
aucun resref dupliqué entre shards
```

Exiger aussi `dimensions_exact_x{scale}=frame_count` pour un job individuel, zéro collision BAM
hors paperdoll dans `override`, aucun autre test sprite actif et aucun processus `InfinityLoader`,
`Baldur` ou `BaldurReal`.

La validation QA explicite exige dans la même session de log la source exacte
`CreatureSprites-XN.set` ou `CreatureSprites-XN.registry`, `scale=x{scale}` et
`filter=NEAREST`. Elle recalcule aussi présence et hashes de toutes les cibles consignées par
l'installation avant d'autoriser `validated-installed`. Un fallback de priorité inférieure, un
shard absent ou un fichier remplacé après installation invalide la QA.

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
L'installation sélectionne le layout uniquement depuis `build.registry_layout`. L'absence de ce
champ n'est acceptée que comme monolithe historique ; elle n'est jamais interprétée comme un set.
Elle revalide job, build, runtime et tous les fichiers binaires avant de créer sa sauvegarde. Même
appelé directement, le script recalcule le hash du contrat source moteur consigné par le manifeste
runtime et refuse une DLL/manifeste construite depuis une autre révision. Pour un job individuel,
il relie aussi le build au manifeste source courant, à Scalepix et à l'adaptateur xBR ; pour un set,
il revalide les hashes des manifestes source/build de chaque membre et leurs contrats d'outil.

L'état récupérable v2 sauvegarde dynamiquement : DLL, INI, monolithe XN, index de set, registre X2,
tous les shards cibles et tous les shards canoniques préexistants, y compris ceux qui deviendront
obsolètes. Il est publié avant la première mutation du jeu. Pour un set, l'installateur retire les
layouts XN actifs, copie et revalide les shards, puis publie l'index en dernier. Pour un monolithe,
il retire tout index et shard qui masquerait ou contaminerait le test. Le registre X2 est sauvegardé
mais reste intact comme fallback de compatibilité.

La restauration traite seulement les chemins dynamiques consignés sous le `game_root` exact. Elle
refuse doublon, chemin absolu, évasion de racine, cible modifiée, backup déplacé ou altéré et shard
apparu hors état. Après ce préflight complet, elle restaure exactement présence, absence et hashes
initiaux. L'ancien état xN v1 monolithique reste restaurable.

L'installateur publie l'état `installing` avant sa première mutation et le restaurateur publie
`restoring` avant la sienne. Après une interruption du processus ou de la machine, fermer le jeu,
vérifier le job puis utiliser le mode de récupération :

```powershell
powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-XN-Test.ps1 `
  -JobFile sprite/jobs/<job>.json `
  -RecoverInstalling
```

Ce mode vérifie toutes les sauvegardes avant d'écraser les cibles potentiellement partielles. Il
n'est accepté que pour un état actif `installing` ou `restoring` ;
`-RecoverInterrupted` est un alias plus générique du même switch.

Toutes les écritures d'état xN utilisent un fichier temporaire adjacent puis un remplacement
atomique. Installateurs legacy et xN ainsi que leurs restaurateurs prennent le même mutex Windows
global dérivé du `GameRoot` pendant tout leur chemin critique ; une deuxième mutation concurrente,
y compris depuis une autre session Windows, échoue avant la lecture de l'état actif. Les dossiers
de sauvegarde portent timestamp fractionnaire, PID et UUID afin de ne jamais partager une cible
entre deux exécutions.

Pour revenir au code antérieur à la fondation, utiliser la baseline Git `84e17b6` sur la branche de
travail `feature/creature-sprite-xn`, ou la sauvegarde locale documentée dans
`_rollback/creature-sprite-xn-pre-20260825/README.md`. Ne pas écraser les changements sans rapport
présents dans le worktree.

Le registry-set est développé sur `feature/creature-sprite-registry-set`. Son point de retour
pré-sharding est le commit xN validé `0075587`.

La branche Git focalisée ne suit pas les sorties générées de `sprite/index/`. Après un retour à
`0075587`, régénérer impérativement les quatre CSV et `manifest.json` avec la version restaurée de
`build_sprite_inventory.py` ; `git restore` seul ne remet pas ces fichiers non suivis en cohérence.

## Dimensionnement du Character complet

Ne recopier aucun total d'inventaire dans ce document. La source canonique est
`sprite/index/manifest.json`, sous
`registry_set_projections.animations["0x6110"]` : `resource_count`, `frame_count`, puis pour x2 et
x4 `shard_byte_limit`, `maximum_resource_resref`, `maximum_resource_bytes`,
`maximum_frame_resref`, `maximum_frame_index_bytes`, `shard_count`, `total_registry_bytes`,
`fits_set` et `blocker`.

Cette projection prouve qu'un monolithe ne convient pas au Character complet et que le
registry-set tient sous la limite cumulée de 8 Gio sans augmenter le cache RAM de 128 Mio. La
projection x4 du cas réel signalé par `maximum_resource_resref=WQNFSG1` dépasse 128 Mio : le
plafond de 512 Mio par shard x4 est nécessaire, tandis que le plafond de
128 Mio reste inchangé en x2. Toujours relire les octets projetés dans le manifeste régénéré.

Ce dimensionnement valide la capacité du format et du runtime, pas les sprites. Avant production
complète, exiger un build déterministe du set, les tests de corruption/absence/doublon, la preuve du
chargement lazy borné, puis une QA ingame x2 sur le Character et tous ses calques. Le x4 reste une
production et une QA séparées.

Cette fondation ne produit aucun élément `validated-installed` et ne modifie pas le manifeste de
release.
