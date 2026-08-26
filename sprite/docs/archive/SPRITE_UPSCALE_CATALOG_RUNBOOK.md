# Runbook agent — catalogue cumulatif de créatures xN

## Objet

Utiliser ce runbook pour ajouter progressivement des animations compatibles dans une installation
ingame unique. Le catalogue standardise x2 `NEAREST` et accepte un catalogue x4 `NEAREST`
séparé. Il ne mélange jamais les échelles et n'accepte pas le registre AA V4 expérimental.

Job de référence initial :
`sprite/catalogs/creature-x2-nearest/jobs/creature-sprites-progressive-xn-xbr2x.json`. Il contient les Characters complets
`0x6102` et `0x6110`. Le runner ne recalcule pas xBR : il vérifie les builds membres puis copie
leurs records logiques validés dans des shards XN V5 sans perte, compressés frame par frame avec
XPRESS_HUFF ou conservés bruts lorsque la compression n'est pas strictement plus petite.

Pour le dimensionnement global, le chargement lazy, les budgets mémoire et le store content-addressé,
appliquer aussi [`SPRITE_UPSCALE_SCALABLE_ARCHITECTURE.md`](SPRITE_UPSCALE_SCALABLE_ARCHITECTURE.md).

## Sources de vérité

```text
sélection des familles          sprite/index/manifest.json et les quatre CSV
jobs et builds membres          sprite/index/sprite-layout.json et <run>/build/build-manifest.json
job cumulatif                   schema bg2-upscale-creature-sprite-xn-catalog-job-v1
génération active du projet     <run>/current-generation.json
build cumulatif                 <generation>/build/build-manifest.json
runtime cumulatif               <generation>/runtime/runtime-manifest.json
état ingame canonique           <run>/ingame-installation/active-test.json
propriétaire ingame             iee-assets/creature-sprites/CreatureSprites-XN.catalog-owner.json
historique restaurable          <backup_root>/install-state.json
```

Ne pas prendre un registre présent dans `override`, une sauvegarde, une capture, un dossier
temporaire ou un ancien état comme source d'un membre.

## Contrat du job

Le job porte :

```json
{
  "schema": "bg2-upscale-creature-sprite-xn-catalog-job-v1",
  "job_id": "<id stable>",
  "members": [
    "sprite/families/playable-characters/<animation-id>-<character-type>/family-runs/<aggregate>/jobs/<animation-complete-xn>.json"
  ],
  "paths": {
    "game_root": "<BG2EE>",
    "run_dir": "<run catalogue dédié>",
    "engine_source": "engine/InfinityEngine-Enhancer/source-patchee",
    "engine_build": "<build moteur catalogue dédié>"
  },
  "compatibility": {
    "baldur_real_sha256": "<64 hex>"
  },
  "upscale": {
    "algorithm": "XBR/xbr2X",
    "scale": 2,
    "passes": 1,
    "antialias": false,
    "xbr_blend": false
  }
}
```

Pour x4, remplacer ensemble `algorithm` par `XBR/xbr4X` et `scale` par `4`. Tous les membres et
leurs feuilles doivent avoir la même méthode et la même échelle. En x2 seulement, les records V2
ou V3 audités peuvent être normalisés puis empaquetés en shards V5 sans recalcul xBR. Une animation
ID ne peut apparaître que dans un membre top-level.

`installation.import_active_state` est réservé à la migration initiale d'un état existant connu.
Il contient exactement `state_path` et `job_id`. L'installateur exige l'état, les cibles et leurs
hashes exacts ; ce champ n'est pas un contournement générique d'un test concurrent. Le job de
référence a importé l'overlay x4 `CDMB1`, parent historique de la première génération catalogue,
afin que sa restauration reste possible. Ne jamais en déduire l'état live : lire
`<run>/ingame-installation/active-test.json`.
Retirer ce champ dans les nouveaux déploiements qui partent sans état sprite actif.

## Catalogue V2, shards V5 et compatibilité V1/V3

Le fichier prioritaire
`iee-assets/creature-sprites/CreatureSprites-XN.catalog` conserve le magic `IEECSNC\0`. La version
courante est `2`. Le runtime et le restaurateur acceptent encore la version `1` uniquement pour
charger ou restaurer une génération historique, pour un `runtime-refresh` V1 vers V2 à shards
physiquement identiques, ou pour un `storage-repack` V1/V3 vers V2/V5 à contenu logiquement
identique. Ne jamais produire un nouveau catalogue V1 ni rétrograder V2 vers V1 hors restauration
LIFO.

Le préfixe little-endian commun de 64 octets contient :

```text
8s magic
u32 version, scale, animation_count, component_count, membership_count, shard_count
u64 total_resources, total_frames, total_index_bytes, total_registry_bytes
```

Il est suivi, dans cet ordre, de :

- `animation_count` entrées de 16 octets : `animation_id`, propriétaire, début et nombre de
  memberships en `u32` ; propriétaire `1=Character`, `2=MonsterIcewind` ;
- `membership_count` indices de composant en `u32` ;
- `component_count` entrées de 72 octets : digest SHA-256 binaire, début et nombre de shards,
  ressources, réservé zéro en `u32`, puis frames, octets indexés et octets registre en `u64` ;
- `shard_count` entrées de 64 octets : SHA-256 binaire, CRC32 et ressources en `u32`, puis frames,
  octets indexés et octets registre en `u64`.

En V2, le header mesure 104 octets. Les 40 octets ajoutés après le préfixe commun contiennent
`directory_count` en `u32`, `directory_entry_bytes=24` en `u32`, puis le SHA-256 brut de la
directory. Les quatre tables historiques commencent à l'offset 104. La directory suit la table des
shards. Chaque entrée contient `animation_id u32`, `resref[8]`, `component_index u32`,
`shard_index u32`, `resource_ordinal u32`. Les couples `(animation_id,resref)` sont uniques et triés
strictement par octets. Chaque route doit désigner un composant membre de l'animation, un shard de
ce composant et le resref exact à l'ordinal déclaré. Son digest vaut :

```text
SHA256("IEECSNC-DIRECTORY-V2\0" || LE_u32(scale) || toutes_les_entrées_brutes)
```

Limiter la directory à 1 048 576 entrées de 24 octets. Une divergence de digest, de couverture, de
tri, de route ou de resref invalide le catalogue entier et conserve le rendu natif.

Chaque shard est nommé
`CreatureSprites-XN-<SHA256 MAJUSCULE>.registry`. Le format de production est un registre
`IEECSXN\0` V5 de même échelle, avec `animation_id=0xFFFF`. La sentinelle interdit son utilisation
autonome et V5 n'est valide que sous un catalogue V2. L'en-tête de ressource et les cycles restent
identiques à V3. L'en-tête de frame de 528 octets porte : géométrie et transparence aux offsets
`0..8`, `codec u8` à l'offset 9, deux octets réservés zéro, `stored_bytes u32` à l'offset 12, puis
les 256 représentants `u16`. Exiger :

```text
codec=0 RAW           stored_bytes == width * height * scale * scale
codec=1 XPRESS_HUFF   0 < stored_bytes < width * height * scale * scale
```

Refuser tout codec inconnu, octet réservé non nul, taille incohérente, sortie de décompression
incomplète ou dépassement de limite. Le digest physique du composant vaut :

```text
SHA256("IEECSNC-COMPONENT-V1\0" || LE_u32(scale) || entrées_shards_binaires)
```

Ce digest change lors d'un repack V3 vers V5. La preuve de contenu est indépendante du stockage :
pour chaque composant, décompresser V5, normaliser chaque frame en record V3 brut exact, trier les
records par resref et calculer :

```text
SHA256("IEECSNC-SOURCE-COMPONENT-V1\0" || LE_u32(scale) || LE_u32(record_count)
       || pour chaque record : ASCII(resref) || NUL || LE_u64(record_bytes) || record_logique)
```

Le digest logique global couvre ensuite l'échelle, les compteurs, les digests logiques des
composants en ordre, puis chaque animation, propriétaire et membership sous le domaine
`IEECSNC-LOGICAL-CONTENT-V1\0`. Le builder, l'installateur et le restaurateur doivent recalculer ces
preuves depuis les payloads ; ne jamais faire confiance à un champ de manifeste non corroboré.

Dans les manifests V5, `total_index_bytes` est la somme logique des indices décompressés,
`storage.stored_index_bytes` leur taille physique, et `total_registry_bytes` la taille physique
complète des shards. `total_index_bytes > total_registry_bytes` est autorisé uniquement pour V5.
Exiger `registry_catalog_shard_version=5`,
`registry_catalog_frame_storage=XPRESS_HUFF-or-raw-per-frame-v1`, les compteurs RAW/XPRESS et les
digests logiques exacts. Un mélange V3/V5 est interdit.

Les catalogues V1 et shards V3 restent acceptés uniquement pour lire, vérifier ou restaurer un état
historique et pour la migration transactionnelle décrite ci-dessous. Ne jamais produire un nouveau
catalogue V1 ni un nouveau shard catalogue V3.

Ordre de priorité runtime : catalogue, set V1, monolithe XN V3, registre X2 historique. L'absence
autorise le niveau suivant. La présence d'un catalogue invalide, incomplet ou modifié échoue fermée
et conserve le rendu natif ; elle n'autorise jamais le fallback vers le set ou monolithe masqué.
Le préflight recalcule SHA-256 et CRC32 de chaque shard. La lecture lazy conserve en plus un SHA-256
par bloc physique de frame, décompresse vers la taille logique exacte et vérifie les représentants :
une substitution ultérieure est refusée même si taille et date du fichier ont été conservées.

Une erreur du fichier catalogue, de sa directory ou de ses digests pendant `prepare()` désactive le
catalogue entier. Une divergence physique découverte seulement lors de l'ouverture lazy d'un shard
met en quarantaine le composant concerné ; les autres composants restent disponibles. Toute
quarantaine échoue la QA technique.

Limites du catalogue : 512 animations, 16 384 composants, 262 144 memberships, 16 384 shards,
32 768 ressources physiques, 4 194 304 frames et 128 Gio de registres. Les limites de chaque shard
restent 128 ressources, 4 096 frames par resref, 128 Mio en x2 ou 512 Mio en x4. Une frame lazy
reste limitée à 128 Mio.

## Génération immuable et reprise

Le verrou d'entrée couvre le job cumulatif, les jobs et manifestes source/build de chaque feuille,
les fichiers payload physiques de chaque build feuille avec leur SHA-256, CRC32 et taille, les
manifestes des membres, `BaldurReal.exe` et le contrat source moteur. Son SHA-256 est le
`generation_id`. Chaque payload est hashé en une passe avec identité et métadonnées stables ; tout
ReparsePoint est refusé. Le builder reprend le snapshot avant publication et recalcule sur les
shards produits le digest exact des records copiés par composant. Les sorties sont exclusivement
sous :

```text
<run>/generations/<generation_id>/build
<run>/generations/<generation_id>/runtime
```

Une génération existante valide est réutilisée avec `--resume`. Une génération existante invalide
est bloquante. Ne jamais utiliser `--force`, supprimer une génération, modifier un shard ou réparer
un manifeste en place. Toute modification d'entrée doit produire un autre `generation_id`.

Le pointeur `current-generation.json` est publié seulement lorsque build et runtime testés existent.
Il verrouille les hashes des deux manifestes. Les jobs, builds, sources, états et sauvegardes des
générations antérieures restent intacts.

Sous Visual Studio 2019, garder `paths.engine_build/<generation_id>` à 120 caractères absolus ou
moins. Le FileTracker ajoute des chemins `TryCompile/*.tlog` non compatibles avec une racine plus
longue ; le runner refuse cette configuration avant CMake. Utiliser une racine courte dédiée telle
que `sprite/.work/cmake/catalog` et ne jamais réutiliser le build d'une autre génération. Les
générateurs d'append et de refresh QA imposent cette racine aux nouveaux jobs ;
`sprite/.cmake-catalog` reste uniquement une référence historique résolue par l'index de migration.

Un job catalogue est lui aussi immuable. Pour un append, créer un nouveau fichier de job versionné,
conserver le même `job_id` et le même `run_dir`, puis ajouter les membres dans ce nouveau fichier.
Ne jamais éditer le job d'une génération déjà installée : sa restauration et son QA exigent le
`job_file` et le `job_sha256` consignés dans son état. Après une restauration LIFO vers une ancienne
génération, reprendre le `job_file` indiqué par l'état redevenu actif pour restaurer le niveau
suivant.

## Préparer et vérifier

Fermer `InfinityLoader`, `Baldur` et `BaldurReal`, puis exécuter :

```powershell
$catalogJob = 'sprite/catalogs/creature-x2-nearest/jobs/creature-sprites-progressive-xn-xbr2x.json'

python pipeline/scripts/run_creature_sprite_x2.py plan --job $catalogJob
if ($LASTEXITCODE -ne 0) { throw 'Plan catalogue refusé' }

python pipeline/scripts/run_creature_sprite_x2.py prepare --job $catalogJob --resume
if ($LASTEXITCODE -ne 0) { throw 'Préparation catalogue refusée' }

python pipeline/scripts/run_creature_sprite_x2.py verify --job $catalogJob
if ($LASTEXITCODE -ne 0) { throw 'Vérification catalogue refusée' }
```

Exiger :

```text
status=prepared-verified
registry_layout=catalog
runtime.status=built-tested
runtime.tests_status=passed
runtime.bridge_worker_tests_status=passed
job_sha256 et generation_id exacts dans build, runtime et pointeur
build.validation.records_copied_without_xbr=true
build.validation.logical_records_preserved_after_lossless_storage_repack=true
registry_catalog_version=2
registry_catalog_shard_version=5
registry_catalog_frame_storage=XPRESS_HUFF-or-raw-per-frame-v1
registry_catalog_logical_content_sha256 == runtime.catalog_logical_content_sha256
build.validation.palette_frames_exactly_remapped == somme des frames membres
build.validation.partial_alpha_pixels=0
build.validation.new_colors=0
build.validation.override_collisions=0
animations, memberships, composants, shards et totaux identiques au binaire
SHA256, CRC32, en-tête V5, codecs, tailles stockées et sentinelle exacts pour chaque shard
digests logiques de composants recalculés depuis les frames décompressées
aucun resref dupliqué dans la portée d'une animation ID
```

## Installation initiale et append strict

L'installation utilise un mutex global dérivé du `GameRoot`, publie `installing` avant la première
mutation, sauvegarde chaque cible, écrit les shards immuables, le propriétaire, puis le catalogue en
dernier. L'INI final doit contenir une occurrence unique de chaque clé :

```ini
[Shaders]
EnableCreatureSpriteUpscaleTest = true
EnableCreatureSpriteX2Test = false
EnableCreatureSpriteLinearFiltering = false
```

`InfinityEngine-Enhancer.ini` est un fichier partagé avec les autres pipelines ingame. Son ordre et
ses clés non propriétaires peuvent évoluer sans invalider le catalogue ; l'intégrité sprite exige
en revanche exactement une occurrence de chacune des trois clés ci-dessus avec ces valeurs. Tous
les autres fichiers installés restent soumis à leur SHA-256 binaire exact.

Préflight direct sans mutation :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile $catalogJob `
  -VerifyOnly
if ($LASTEXITCODE -ne 0) { throw 'Préflight installation refusé' }
```

Installation :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py install --job $catalogJob
if ($LASTEXITCODE -ne 0) { throw 'Installation catalogue refusée' }

python pipeline/scripts/run_creature_sprite_x2.py status --job $catalogJob
if ($LASTEXITCODE -ne 0) { throw 'Statut catalogue illisible' }
```

Exiger `installed-pending-qa`, `active_identity_matches_job=true` et
`installed_files_match=true`. L'installateur ne supprime ni set, ni monolithe, ni shard numéroté
préexistant : le catalogue prioritaire les masque et la restauration retrouve leur état exact. La
seule exception est le retrait transactionnel de shards V3 content-addressés devenus non référencés
pendant un `storage-repack`; chacun conserve une source de restauration scellée et vérifiée.

Si un catalogue est déjà actif, la nouvelle génération doit être un append strict :

1. conserver chaque animation ID existante et son propriétaire ;
2. conserver tous les composants, digests et shards déjà référencés ;
3. autoriser seulement l'ajout de composants à une animation existante ou de nouvelles animations ;
4. ajouter au moins un mapping ;
5. refuser retrait, remplacement, changement d'échelle, changement de méthode ou réattribution d'un
   composant ;
6. réutiliser sans copie tout shard content-addressé déjà présent avec le hash exact ;
7. chaîner `previous_active_state` et ne jamais écraser son backup.

Un append V5 doit rester V5 et conserver le même contrat de stockage. Ne jamais combiner un append
de créature avec une migration de format.

Le job d'append peut avoir un autre chemin que le job précédent, mais il doit conserver le même
`job_id` et le même `run_dir`. Les deux fichiers restent présents. Cette règle rend chaque niveau de
la pile de restauration vérifiable sans réécrire un job historique.

Ne jamais copier manuellement un shard dans le jeu et ne jamais éditer le propriétaire pour faire
accepter un append.

### Repack de stockage V1/V3 vers V2/V5

Effectuer `storage-repack` une seule fois, séparément de tout append, pour migrer le catalogue actif
V1 et ses shards V3 bruts vers le catalogue V2 et ses shards V5 lossless. Le préflight doit annoncer
exactement `Mode=storage-repack`. Toute autre paire de versions, tout mélange V3/V5 ou tout ajout ou
retrait de contenu est bloquant.

Le mode est accepté seulement si l'installateur :

1. parse et recalcule depuis les payloads live V3 l'identité logique de l'ancien état, même si cet
   état historique ne persiste aucun digest logique ;
2. décompresse et recalcule depuis les shards V5 l'identité logique candidate ;
3. obtient les mêmes resrefs, SHA source, frames, cycles, géométries, centres, transparences,
   représentants, indices et compteurs logiques pour chaque composant ;
4. conserve exactement animation IDs, propriétaires, memberships, méthode, échelle et
   `source_members` scellés ;
5. vérifie la directory V2 complète, les manifests build/runtime, la nouvelle génération, la DLL
   différente et `bridge_worker_tests_status=passed` ;
6. autorise uniquement les différences physiques attendues : hashes/digests de shards,
   `stored_index_bytes` et `total_registry_bytes` ;
7. chaîne `previous_active_state` et intègre à la transaction chaque cible créée, remplacée ou
   retirée.

Les shards V3 content-addressés que V5 ne référence plus reçoivent le rôle
`retired-content-addressed-shard`. Ils sont retirés du jeu seulement après publication de l'état
`installing`; `restore_source_path` désigne leur copie exacte dans la génération V1/V3 immuable et
son SHA-256 est vérifié avant mutation. Une interruption ou une restauration LIFO recopie exactement
ces V3. Ne jamais supprimer leur génération, leur job, leur état, leur source de restauration ou
leur backup.

Les nouvelles générations V5 réutilisent le store immuable
`<run>/object-store/creature-sprites-xn-v5/` par hardlinks vers des objets nommés par SHA-256. Le jeu
reçoit toujours des copies indépendantes. Ne jamais remplacer ni garbage-collecter un objet CAS, et
ne jamais copier manuellement un shard pour contourner le builder ou l'installateur. Voir
[`SPRITE_UPSCALE_SCALABLE_ARCHITECTURE.md`](SPRITE_UPSCALE_SCALABLE_ARCHITECTURE.md) pour les gates
CAS, les budgets lazy et la reprise.

### Rafraîchir uniquement le runtime

Utiliser `runtime-refresh` lorsqu'une correction DLL doit être déployée sans ajouter, retirer ni
remplacer de contenu validé. Préparer normalement une nouvelle génération scellée, puis exécuter le
préflight standard. Exiger `Mode=runtime-refresh`.

Ce mode reste physiquement exact et n'est pas un repack. Il est accepté seulement si :

1. méthode, échelle, animations, propriétaires, memberships et digests de composants sont
   strictement identiques ;
2. chaque shard conserve exactement SHA-256, CRC32, ressources, frames et tailles ;
3. une même version conserve le catalogue octet pour octet et ne republie pas son fichier live ;
4. la seule transition de catalogue admise est V1 vers V2 avec les mêmes shards physiques, avec la
   directory V2 entièrement vérifiée contre les resrefs physiques ; la transition de shards V3 vers
   V5 relève exclusivement de `storage-repack` ;
5. `generation_id` et hash de DLL diffèrent de l'état actif, et le runtime porte
   `status=built-tested` et `tests_status=passed` ;
6. `previous_active_state` est sauvegardé avant mutation et toutes les cibles mutables sont intégrées
   à la transaction.

Un catalogue de même taille dont un mapping ou shard diffère n'est jamais interprété comme un
refresh. Une tentative de réinstallation de la même DLL, une rétrogradation V2 vers V1 ou une
génération identique échoue fermée. Après installation, exiger `installation_mode=runtime-refresh`,
`installed_files_match=true` et conserver la QA `installed-pending-qa` jusqu'au nouveau test ingame.

## QA multi-animation

Aucun runner ou installateur ne lance automatiquement le jeu. Appliquer la politique de
[`sprite/README.md`](../../README.md#politique-de-qa-ingame-pilotée). Pour chaque entrée de `qa.animations`, tester
le personnage ou la créature prévu, puis toutes les armures et familles d'équipement couvertes.
Vérifier directions, actions, pivots, taille, palettes, changement d'équipement,
sauvegarde/chargement, changement de zone, stabilité et performances.

Après fermeture du jeu :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py qa-log --job $catalogJob --write-report
if ($LASTEXITCODE -ne 0) { throw 'Analyse de log refusée' }
```

Exiger dans une même session post-installation :

```text
Creature sprite xBR catalog ready ... source=CreatureSprites-XN.catalog; filter=NEAREST
owner scope installé pour chaque propriétaire déclaré
au moins un `Creature sprite catalog shard <N> ready on demand ...` dans la session
animation 0xNNNN reached ...::Render pour chaque animation
composition NEAREST et remplacement transient pour chaque préfixe requis par le contrat QA scellé
zéro reset du pool, warning texture, rejet backing, échec lazy ou upload in-place
installed_files_match=true
technical_pass=true
```

Les preuves de composition sont indexées par couple `(animation_id, préfixe)`. Une ligne produite
pour une autre animation qui partage le même préfixe ne satisfait jamais le gate.
Pour Character, `required_bam_prefixes` contient tous les corps et un représentant de chaque type
d'équipement ; les contrôles de build restent exhaustifs sur tous les autres préfixes.
Le parser accepte encore `catalog animation ... materialized` pour un catalogue V1 historique ;
pour V2, exiger le marqueur `ready on demand` et zéro quarantaine de composant. Un shard partagé
déjà résident peut ne pas produire un nouveau marqueur pour chaque animation ; les lignes
`animation reached` et de composition scoped restent obligatoires par animation.

Le parser ne cumule pas les preuves entre sessions. Après un append, une session limitée au nouvel
ID est un smoke incrémental utile, mais elle ne peut pas produire `technical_pass=true`. La validation
globale exige toutes les animations et tous les préfixes dans une même session post-installation.
Conserver `installed-pending-qa` si cette couverture manque. Enregistrer un succès seulement après
validation utilisateur explicite :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py record-qa `
  --job $catalogJob `
  --result pass `
  --note '<validation utilisateur exacte>'
if ($LASTEXITCODE -ne 0) { throw 'Décision QA refusée' }
```

## Restauration et interruption

Fermer les trois processus. Préflight :

```powershell
$catalog = Get-Content -LiteralPath $catalogJob -Raw | ConvertFrom-Json
$activeStatePath = Join-Path $catalog.paths.run_dir 'ingame-installation/active-test.json'
$activeState = Get-Content -LiteralPath $activeStatePath -Raw | ConvertFrom-Json
$activeJob = [string]$activeState.job_file

powershell -NoProfile -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile $activeJob `
  -VerifyOnly
if ($LASTEXITCODE -ne 0) { throw 'Préflight restauration refusé' }
```

Restaurer un niveau LIFO :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py restore --job $activeJob
if ($LASTEXITCODE -ne 0) { throw 'Restauration catalogue refusée' }
```

Une restauration d'append republie exactement le catalogue, propriétaire, DLL, INI et état
précédents. Une restauration de la génération initiale remet exactement le test importé ou la
baseline. Une restauration de `storage-repack` retire les shards V5 ajoutés et recopie chaque shard
V3 retiré depuis son `restore_source_path` scellé, puis republie catalogue V1, propriétaire, DLL,
INI, pointeur et état précédents. Elle ne supprime jamais les générations, builds, jobs, CAS ni
backups.

Instantané historique non canonique observé le 26 août 2026 : la pile comporte quatre niveaux à
retirer avant le jeu original : catalogue V2/V5, catalogue V1/V3, overlay x4 `CDMB1`, puis parent
nain x2. Revalider chaque parent depuis l'état redevenu actif et exécuter le `VerifyOnly` du
restaurateur correspondant avant chaque restauration. Ne jamais coder cette chaîne en dur, sauter
un niveau ou supprimer manuellement un état, une sauvegarde ou un fichier live.

Lors d'un retour vers une génération catalogue précédente, le restaurateur republie aussi son
`current-generation.json` à partir des deux manifests immuables déjà vérifiés. La génération
restaurée ne dépend pas de l'état actuel du builder, du source moteur ou des builds feuilles : ces
entrées live sont exigées lors de l'installation, tandis que la restauration s'appuie sur le job
historique exact, l'état, les manifests et payloads scellés de la génération, puis les backups.

Avant chaque niveau LIFO, lire `job_file` dans
`<run>/ingame-installation/active-test.json` et passer ce fichier exact à `--job`. Un job plus récent
est volontairement refusé si son SHA-256 ne correspond pas à l'état actif.

Pour un état `installing` ou `restoring` interrompu, exécuter le restaurateur avec
`-RecoverInterrupted` après validation de tous les backups ; `-RecoverInstalling` reste un alias.
Ne pas utiliser la récupération sur un état sain.

```powershell
$catalog = Get-Content -LiteralPath $catalogJob -Raw | ConvertFrom-Json
$activeStatePath = Join-Path $catalog.paths.run_dir 'ingame-installation/active-test.json'
$activeState = Get-Content -LiteralPath $activeStatePath -Raw | ConvertFrom-Json
$activeJob = [string]$activeState.job_file

powershell -NoProfile -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile $activeJob -RecoverInterrupted -VerifyOnly
if ($LASTEXITCODE -ne 0) { throw 'Récupération interrompue non vérifiable' }

powershell -NoProfile -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile $activeJob -RecoverInterrupted
if ($LASTEXITCODE -ne 0) { throw 'Récupération interrompue refusée' }
```

## Arrêts obligatoires

Bloquer la préparation ou l'installation sur processus ouvert, hash du jeu ou du moteur divergent,
pointeur obsolète, membre non vérifié, gate palette incomplet, collision `override`,
échelle/méthode mixte, AA V4, limite dépassée, resref dupliqué dans une animation,
catalogue/shard/propriétaire altéré, codec ou taille V5 invalide, digest logique divergent, mélange
V3/V5, append non strict, état concurrent non importé exactement, objet CAS divergent, source de
shard retiré ou backup absent, reprise ambiguë. En restauration, exiger le job historique, les
artefacts scellés et les backups exacts sans imposer que les sources centrales soient restées à leur
ancienne version.

Ce workflow ne modifie jamais `$mapSpecs`, `content.json`, le staging ou l'archive. Il ne lance pas le
jeu automatiquement. Un catalogue x2 ou `installed-pending-qa` n'est pas éligible au manifeste de
release. Appliquer la décision de fin de tâche imposée par `AGENTS.md` seulement aux éléments
`validated-installed` ; ne rien intégrer sans accord affirmatif explicite.
