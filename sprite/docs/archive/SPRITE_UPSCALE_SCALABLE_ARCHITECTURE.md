# Architecture scalable — catalogue cumulatif de sprites de créature xN

## Objet et statut

Appliquer cette architecture pour faire croître une installation ingame unique sans charger tous
les sprites au démarrage, sans remplacer un contenu déjà validé et sans multiplier physiquement les
shards identiques entre générations du dépôt.

Contrat de production principal :

```text
échelle                 x2
algorithme              XBR/xbr2X, une passe
stockage                catalogue V2 + shards XN V5
échantillonnage QA      NEAREST
installation            cumulative, transactionnelle, LIFO
fallback                BAM natif
```

Le même format accepte x4 `NEAREST` avec `XBR/xbr4X` direct. Ne jamais mélanger x2 et x4 dans un
catalogue. Le registre AA V4 reste expérimental, limité à son prototype `CDMB1`, et hors de cette
architecture. Ne jamais convertir ou importer implicitement un overlay AA/x4 imbriqué.

Aucun script, runner ou installateur ne lance le jeu automatiquement. Appliquer la politique de QA
ingame de [`sprite/README.md`](../../README.md#politique-de-qa-ingame-pilotée). Cette architecture ne modifie
jamais `$mapSpecs`, `content.json`, le staging, l'archive ou le manifeste de release.

## Sources de vérité

Lire avant toute production :

1. [`sprite/README.md`](../../README.md) et les index sous [`sprite/index/`](../../index/) pour l'identité et l'éligibilité ;
2. [`SPRITE_UPSCALE_XN_FOUNDATION.md`](SPRITE_UPSCALE_XN_FOUNDATION.md) pour la géométrie xN ;
3. [`SPRITE_UPSCALE_PIPELINE.md`](SPRITE_UPSCALE_PIPELINE.md) pour les invariants BAM, palette et
   runtime ;
4. [`CHARACTER_COMPLETE_X2_RUNBOOK.md`](CHARACTER_COMPLETE_X2_RUNBOOK.md) pour produire un
   Character complet ;
5. [`SPRITE_UPSCALE_CATALOG_RUNBOOK.md`](SPRITE_UPSCALE_CATALOG_RUNBOOK.md) pour la transaction
   cumulative ;
6. [`SPRITE_UPSCALE_VARIANT_TEST_RUNBOOK.md`](SPRITE_UPSCALE_VARIANT_TEST_RUNBOOK.md) pour isoler
   x2, x4, LINEAR et les prototypes.

État canonique par étape :

| Question | Source de vérité |
|---|---|
| Animation, famille, resref, collisions et usage par les CRE stock | `sprite/index/manifest.json` et les quatre CSV |
| Entrées d'une génération | job catalogue, jobs feuilles et leurs manifestes scellés |
| Génération courante du dépôt | `<run>/current-generation.json` |
| Contenu produit | `<generation>/build/build-manifest.json` |
| DLL et contrat runtime | `<generation>/runtime/runtime-manifest.json` |
| État ingame courant | `<run>/ingame-installation/active-test.json` |
| Propriétaire live | `<GameRoot>/iee-assets/creature-sprites/CreatureSprites-XN.catalog-owner.json` |
| Restauration | `<backup_root>/install-state.json` et les artefacts scellés référencés |

Ne jamais prendre un fichier d'`override`, une capture, une sauvegarde de jeu, un répertoire
temporaire ou un ancien rapport comme source de contenu.

## Flux de données

```text
jobs/builds feuilles V2 ou V3 validés
                  |
                  v
records logiques triés + digest indépendant du stockage
                  |
                  v
shards XN V5 (XPRESS_HUFF ou brut, décision par frame)
                  |
        +---------+----------+
        |                    |
        v                    v
CAS immutable du dépôt   catalogue V2 + route directory
        |                    |
        +---- hardlinks -----+----> génération scellée
                                      |
                                      | copies indépendantes
                                      v
                                  installation jeu
                                      |
                  route O(log N) -> worker asynchrone -> caches bornés
                                      |
                              rendu xN ou fallback natif
```

Le catalogue réutilise les composants logiques communs à plusieurs animation IDs. Un resref partagé
entre deux IDs reste résolu dans la portée de son couple `(animation_id, resref)` ; il n'est jamais
résolu globalement par son seul nom.

## Catalogue V2 : index de routage borné

Le fichier prioritaire est
`iee-assets/creature-sprites/CreatureSprites-XN.catalog`, magic `IEECSNC\0`, version `2`. Le header
V2 mesure 104 octets : le préfixe V1 de 64 octets, puis `directory_count u32`,
`directory_entry_bytes=24 u32` et le SHA-256 brut de la directory.

Les tables restent dans cet ordre : animations, memberships, composants, shards, puis directory.
Une entrée de directory est :

```text
animation_id u32
resref[8]
component_index u32
shard_index u32
resource_ordinal u32
```

Exiger :

- clés `(animation_id,resref)` uniques et strictement triées par octets ;
- composant membre de l'animation ;
- shard compris dans l'intervalle du composant ;
- ordinal compris dans le shard ;
- couverture exacte de toutes les ressources de chaque animation ;
- au plus 1 048 576 entrées ;
- digest exact
  `SHA256("IEECSNC-DIRECTORY-V2\0" || LE_u32(scale) || directory_brute)`.

Le runtime effectue une recherche binaire dans cette table : le routage est `O(log N)` et un resref
absent en V2 n'est ni mis en queue ni mémorisé dans un cache négatif croissant.

Le catalogue V1 reste lisible uniquement pour compatibilité, restauration et migration. Il ne
dispose pas de directory et doit sonder ses shards V3 en arrière-plan. Ne jamais produire un
nouveau V1.

Limites du catalogue :

| Élément | Maximum |
|---|---:|
| animations | 512 |
| composants | 16 384 |
| memberships | 262 144 |
| shards | 16 384 |
| ressources physiques | 32 768 |
| frames | 4 194 304 |
| entrées de directory | 1 048 576 |
| octets de registres | 128 Gio |
| ressources par shard | 128 |
| frames par resref | 4 096 |
| payload logique d'une frame | 128 Mio |
| shard x2 | 128 Mio |
| shard x4 | 512 Mio |

Ces limites sont des arrêts fail-closed, pas des objectifs de dimensionnement. Un parse complet de
shard est transitoirement borné par la limite du shard ; maintenir les shards nettement sous leur
plafond réduit le pic de première matérialisation, surtout en x4.

## Shard XN V5 : compression indépendante par frame

V5 conserve le magic `IEECSXN\0`, l'en-tête de 24 octets, l'échelle x2 ou x4 et la sentinelle
catalogue `animation_id=0xFFFF`. V5 n'est valide que comme shard d'un catalogue V2. Il n'est jamais
chargé comme monolithe ou registry-set autonome.

L'en-tête de ressource et les cycles restent identiques au record V3. L'en-tête de frame reste long
de 528 octets :

| Offset | Champ |
|---:|---|
| 0 | largeur logique `u16` |
| 2 | hauteur logique `u16` |
| 4 | centre X `i16` |
| 6 | centre Y `i16` |
| 8 | indice transparent `u8` |
| 9 | codec `u8` |
| 10 | deux octets réservés, zéro |
| 12 | longueur physique stockée `u32` |
| 16 | 256 représentants de palette `u16` |

La longueur logique vaut `largeur * hauteur * scale * scale`. Le writer utilise l'API de
compression Windows `cabinet` :

```text
codec=0  brut          stored_bytes == logical_bytes
codec=1  XPRESS_HUFF   0 < stored_bytes < logical_bytes
```

Compresser chaque frame séparément conserve l'accès aléatoire. Si XPRESS_HUFF n'est pas strictement
plus petit, écrire la frame brute ; le codec ne doit jamais augmenter la taille du payload. Refuser
codec inconnu, octet réservé non nul, longueur incohérente, sortie décompressée partielle ou
supérieure à 128 Mio.

V5 est sans perte : il ne change ni géométrie, ni cycles, ni centres, ni représentants, ni indices
de palette, ni provenance des indices dupliqués. Il reproduit le record logique V3 après
décompression. La légère perte de qualité autorisée par l'utilisateur n'est donc pas consommée par
ce correctif.

Chaque shard conserve SHA-256 et CRC32 du fichier complet. Chaque frame lazy conserve aussi le
SHA-256 de son bloc physique stocké. Le runtime vérifie la taille de sortie exacte, puis que chaque
indice décompressé possède un représentant valide avant de le rendre disponible.

Dans les manifestes V5 :

```text
totals.total_index_bytes         taille logique décompressée des indices
storage.stored_index_bytes       taille physique des seuls blocs d'indices
totals.total_registry_bytes      taille physique complète des shards
storage.compressed_frame_count   frames XPRESS_HUFF
storage.raw_frame_count          fallbacks bruts
```

Ne jamais comparer `total_index_bytes` à l'espace disque V5 : le premier est volontairement
logique.

## Identité logique V3/V5

Le digest physique `component.digest` dépend des entrées de shards, donc de leur version, de leur
taille et de leurs hashes. Il change normalement lors d'un repack V3 vers V5.

La preuve de contenu utilise une deuxième identité :

1. normaliser chaque frame V5 en en-tête V3 brut (`codec=0`, longueur logique) et décompresser son
   payload ;
2. hasher les records logiques triés par resref sous le domaine
   `IEECSNC-SOURCE-COMPONENT-V1\0` ;
3. hasher l'échelle, les digests logiques de composants, les animation IDs, les propriétaires et
   leurs indices de composants sous le domaine `IEECSNC-LOGICAL-CONTENT-V1\0`.

Exiger dans un `storage-repack` :

```text
ancien.logical_component_digests == nouveau.logical_component_digests
ancien.logical_content_sha256    == nouveau.logical_content_sha256
animation IDs, propriétaires et mappings logiques inchangés
source_members et provenance scellée inchangés
total_resources, total_frames et total_index_bytes inchangés
```

Les hashes physiques, `total_registry_bytes` et les digests physiques peuvent changer. Cette
distinction autorise une migration de stockage sans prétendre qu'un fichier compressé est identique
octet pour octet à son prédécesseur.

## Runtime : chargement progressif et budgets bornés

### Activation

En présence d'un catalogue V2, `prepare()` lit, borne et authentifie uniquement le petit index du
catalogue. Il n'ouvre et ne hashe aucun shard au démarrage. Le fichier catalogue reste ouvert sous
un lease Windows ; le chemin chaud d'une frame résidente n'effectue pas de `stat`, d'ouverture ou
de lecture disque.

Ordre de priorité inchangé : catalogue, registry-set V1, monolithe XN, registre X2 historique. Un
fichier prioritaire présent mais invalide interdit le fallback vers un layout inférieur ; le rendu
BAM natif du jeu reste disponible.

### Première rencontre d'une ressource

1. Rechercher `(animation_id,resref)` par dichotomie dans la directory.
2. Si le shard n'est pas résident, dédupliquer la clé `(animation_id,resref)` et la placer dans
   l'unique queue FIFO, bornée à 256. La déduplication ne porte pas sur le shard : plusieurs resrefs
   du même shard peuvent occuper plusieurs entrées. Une demande refusée est retentée à un dessin
   ultérieur.
3. Rendre immédiatement le BAM natif pendant le chargement des métadonnées du shard.
4. Sur le worker, ouvrir un seul shard, vérifier identité, SHA-256, CRC32, en-tête, sentinelle,
   totaux, ordinals et resrefs, puis capturer le SHA-256 de chaque bloc depuis ce shard authentifié.
5. Publier atomiquement ses métadonnées si la génération du catalogue n'a pas changé.
6. À la première utilisation de la frame, le thread de rendu lit le bloc, vérifie son SHA-256,
   décompresse XPRESS_HUFF, valide les représentants et publie les indices dans le cache lazy sous
   le mutex global. Cette étape est synchrone et peut produire un hitch ponctuel.
7. Rendre cette frame en xN tant que ses métadonnées et indices restent résidents. La première
   utilisation d'une autre frame, ou sa réutilisation après éviction, répète l'étape synchrone 6.

Le worker n'exécute aucune opération OpenGL. Un handle de frame transporte l'index du shard et sa
génération ; une éviction ou réutilisation entre résolution et dessin rend le handle obsolète et
impose le fallback natif.

### Budgets résidents

| Cache ou file | Borne |
|---|---:|
| queue de chargement | 256 clés `(animation_id,resref)` dédupliquées |
| métadonnées de shards | LRU, 128 Mio |
| indices décompressés | LRU, 128 Mio |
| textures de frames | 128 entrées et 128 Mio |
| composites CPU Character | 32 entrées et 4 Mio |

L'éviction de métadonnées invalide uniquement les indices, composites et générations du shard
victime. Elle ne vide pas les caches des composants sans rapport. Les IDs de texture moteur
devenus anciens ne peuvent plus être des cache hits et sont placés en tête de réutilisation sans
détruire arbitrairement les textures encore vivantes.

Ces nombres bornent les caches résidents ; leur somme n'est pas la mémoire totale du processus. Ils
excluent les tables persistantes et leur overhead, le parse transitoire d'un shard complet, ainsi que
la coexistence possible du bloc compressé et de sa sortie logique. Les limites x2/x4 bornent le
shard transitoire ; le payload logique d'une frame reste limité à 128 Mio.

### Limites runtime avant bestiaire complet

L'architecture est fail-closed et utilisable pour des ajouts progressifs. Ne pas la déclarer robuste
pour le bestiaire complet tant que les gates suivants ne passent pas :

1. remplacer la recherche/éviction linéaire du `std::vector` d'indices lazy (`find_if`,
   `min_element`) par un index hashé et un LRU à coût borné ;
2. coalescer la queue par shard ou prouver par stress que la déduplication `(animation_id,resref)`
   ne sature pas l'unique worker FIFO ;
3. journaliser au minimum : queue refusée/saturée, chargements et rechargements de shards, accès
   disque, hits/misses et évictions des caches métadonnées/indices ;
4. tester un parcours froid puis chaud sur plus de 50 shards uniques, avec pression d'éviction,
   sauvegarde/chargement, changement de zone et arrêt du jeu ;
5. mesurer le coût du premier payload synchrone et déplacer lecture/hash/décompression hors du
   thread de rendu si le budget de frame est dépassé.

Le compteur `RenderTexture ... evictions=` ne mesure pas les caches catalogue. En l'absence de la
télémétrie ci-dessus, ne pas conclure « aucun rechargement disque » à partir du log courant.

### Arrêt des workers

`ShutdownBindings` doit s'exécuter avant `FreeLibrary`, hors du loader lock. Il arrête d'abord les
callbacks moteur, demande l'arrêt du worker catalogue, le notifie et le joint avant de libérer les
caches de sprites.

Le worker de décodage bridge, distinct du catalogue mais présent dans la même DLL, utilise un owner
`ProcessLifetimeWorker` à destructeur trivial, `_beginthreadex` et une auto-référence du module. Un
arrêt normal joint le thread puis libère cette référence. Un self-join ou un échec de wait conserve
fail-closed le handle et la référence jusqu'à la fin du processus au lieu de décharger du code
encore exécuté. Ne jamais déplacer cette synchronisation dans `DllMain`.

## Portée des pannes et collisions

| Défaut | Réaction attendue |
|---|---|
| catalogue/directory invalide ou remplacé | désactiver le catalogue entier, rendu natif |
| shard, bloc ou décompression invalide | mettre en quarantaine son composant, autres composants disponibles |
| route V2 absente | ne rien charger, rendu natif, aucune croissance de cache négatif |
| cache métadonnées plein | évincer le shard LRU et invalider seulement ses dépendances |
| cache indices/textures/composites plein | évincer l'entrée LRU propre à ce cache |
| payload lazy >128 Mio ou structure invalide | mettre le composant en quarantaine |
| dimension/texture GL impossible au dessin | rendu natif de la frame/du Character |
| calque Character actif absent, palette manquante, union divergente | rendu natif du Character entier |
| collision BAM exacte dans `override` | bloquer plan/build/install |
| resref dupliqué dans une même animation | bloquer le catalogue |
| même resref dans deux animations | autorisé uniquement avec deux routes exactes par animation ID |
| objet CAS existant avec hash divergent | bloquer sans remplacer l'objet |
| état ingame inconnu ou test concurrent non importé exactement | bloquer l'installation |

La quarantaine locale protège la stabilité du jeu, mais toute ligne de quarantaine fait échouer la
QA technique. Ne jamais assimiler un fallback stable à un résultat visuel validé.

## Générations immuables, reprise et CAS

Le `generation_id` est le SHA-256 canonique du verrou d'entrée : job catalogue, jobs feuilles,
manifestes et payloads membres, hash du jeu, builder et contrat source moteur. Les sorties sont
uniquement sous :

```text
<run>/generations/<generation_id>/build
<run>/generations/<generation_id>/runtime
```

Règles :

- utiliser `--resume` pour une génération exacte déjà vérifiée ;
- refuser une génération existante invalide ;
- ne jamais utiliser `--force` sur un catalogue ;
- ne jamais réparer, renommer ou supprimer une génération en place ;
- créer un fichier de job versionné pour un append, avec le même `job_id` et le même `run_dir` ;
- conserver le job historique indiqué par chaque état installé.

Le store partagé est :

```text
<run>/object-store/creature-sprites-xn-v5/
```

Un objet est nommé par son SHA-256 et publié une seule fois. Une génération crée un hardlink vers
l'objet ; l'opération exige le même volume et échoue si les hardlinks ne sont pas disponibles. Le
workflow ne remplace et ne garbage-collecte jamais un objet.

Cette CAS empêche la croissance quadratique de l'espace physique des futures générations. Le
builder peut néanmoins recompresser et revérifier les entrées pour sceller une nouvelle génération ;
ne pas confondre réutilisation physique et absence de travail CPU.

L'installateur copie les shards depuis la génération vers le jeu. Il ne crée jamais de hardlink
entre le jeu et le dépôt : une restauration ou une altération du jeu ne peut donc pas muter la CAS.

Les anciens builds V3, générations, états et backups restent volontairement présents. Les mesures
de réduction V5 concernent le contenu actif et la croissance future ; elles ne signifient jamais
que l'historique préexistant a été supprimé.

## Installation cumulative transactionnelle

Le catalogue accepte quatre transitions explicites :

| Mode | Condition |
|---|---|
| `initial`/`migration` | aucun catalogue propriétaire, ou état parent importé exactement |
| `append` | strict superset, même version, échelle et stockage |
| `runtime-refresh` | contenu et shards physiques identiques, nouvelle DLL testée |
| `storage-repack` | exactement V1/V3 vers V2/V5, identité logique inchangée |

Un append doit conserver tous les animation IDs, propriétaires, composants, shards et mappings
actifs et ajouter au moins un mapping. Il ne peut ni retirer, ni réattribuer, ni remplacer un
contenu. Effectuer le `storage-repack` séparément avant le premier append V5 ; ne jamais combiner
migration de stockage et ajout de créature dans la même transaction.

Avant mutation, l'installateur :

1. prend le mutex global dérivé du `GameRoot` ;
2. refuse `InfinityLoader`, `Baldur` ou `BaldurReal` ouvert ;
3. revalide job, génération, manifests, DLL, `BaldurReal.exe`, catalogue, directory et tous les
   shards ;
4. recalcule l'identité logique V3/V5 ;
5. vérifie les collisions exactes dans `override` ;
6. sauvegarde DLL, INI, owner, catalogue, état précédent et chaque cible mutable ;
7. publie atomiquement un état `installing` avant la première mutation.

Il copie ensuite la DLL, impose les trois clés INI `true/false/false`, publie les nouveaux shards,
retire seulement les anciens shards V3 rendus non référencés par un `storage-repack`, écrit l'owner,
puis publie le catalogue en dernier. Chaque retrait V3 possède un `restore_source_path` vers le
shard exact de la génération V1 scellée. Une erreur après mutation déclenche la restauration depuis
l'état publié.

Les layouts standard set/monolithe masqués ne sont pas supprimés arbitrairement. Les shards déjà
présents avec le hash attendu sont des no-ops immuables ; un même nom avec un contenu divergent est
bloquant.

Succès attendu :

```text
status=installed-pending-qa
installed_files_match=true
active_identity_matches_job=true
installation_mode=<mode préflight>
```

## Restauration LIFO jusqu'au jeu original

Une restauration ne signifie pas nécessairement « sans upscale ». Elle retire exactement un niveau
de transaction et republie l'état précédent. Toujours lire `job_file`, `schema`,
`previous_active_state` et `imported_active_state` dans l'état actif ; ne jamais deviner le parent.

Procédure par niveau :

1. fermer les trois processus ;
2. exécuter le `-VerifyOnly` du restaurateur correspondant au schéma ;
3. exiger hashes live, backups, artefacts scellés et chemins sous le même `GameRoot` ;
4. restaurer un seul niveau ;
5. relire l'état redevenu actif et recommencer avec son job/restaurateur exact.

Le restaurateur catalogue remet catalogue, owner, DLL, INI, pointeur de génération, shards ajoutés
ou shards V3 retirés. Il ne supprime jamais jobs, builds, générations, CAS ou backups.

Instantané historique non canonique de la chaîne observée le 26 août 2026 :

```text
catalogue V2/V5 corrigé
  -> catalogue V1/V3 antérieur
  -> overlay x4 CDMB1 importé
  -> parent nain x2
  -> jeu original sans upscale de sprites
```

Ne jamais sauter un niveau, supprimer un fichier live à la main ou utiliser le restaurateur d'un
autre schéma. Pour un état `installing` ou `restoring` interrompu, utiliser
`-RecoverInterrupted` seulement après validation de toutes les sources de restauration.

## Dimensionnement et seuils

### Mesure du catalogue actif de référence

Mesure réelle de la conversion des deux Characters actifs, sur les mêmes records logiques :

| Stockage des shards | `total_registry_bytes` physique |
|---|---:|
| V3 brut | 2 021 980 972 octets, soit 1,883 Gio |
| V5 XPRESS_HUFF/brut | 379 146 243 octets, soit 361,58 Mio |

Réduction physique : 81,25 %. Les indices logiques mesurés représentent 1 830 529 268 octets ; V5
en stocke 187 694 539, avec 88 790 fallbacks bruts sur 356 717 frames. Les headers de frames,
représentants et cycles expliquent l'écart entre les seuls indices stockés et la taille complète.
`total_registry_bytes` additionne uniquement les shards de la génération active ; il exclut le
catalogue, le CAS, les générations antérieures, jobs, backups et autres historiques.

### Inventaire global et couverture des CRE stock

Pour toute décision courante, lire `sprite/index/manifest.json.stock_cre_usage`. Le scanner mesure
les ressources CRE `0x03F1` du KEY/BIF stock et l'ID `u16-le` à l'offset `0x28` ; il ne déduit pas
l'usage depuis les noms de fichiers.

```powershell
$manifest = Get-Content sprite/index/manifest.json -Raw | ConvertFrom-Json
$manifest.stock_cre_usage | Select-Object cre_resource_count, animation_id_count, `
  nonzero_animation_id_count, with_bam_animation_id_count, without_bam_animation_id_count, `
  without_bam_nonzero_animation_id_count, fully_pipeline_ready_animation_id_count, `
  fully_pipeline_ready_cre_resource_count, fully_pipeline_ready_cre_coverage_percent, `
  runtime_supported_without_bam_animation_id_count, runtime_supported_blocked_animation_id_count, `
  runtime_unsupported_animation_id_count, runtime_unsupported_nonzero_animation_id_count
```

Instantané non canonique du 26 août 2026 :

| Périmètre | IDs | CRE/BAM/frames | Statut |
|---|---:|---:|---|
| index défini | 504 | — | inventaire |
| index `runtime_supported` | 209 | — | profil runtime présent |
| index avec au moins une famille éligible | 122 | 5 683 BAM, 1 681 786 frames | capacité catalogue projetable |
| CRE stock | 279 valeurs, dont `0x0000` | 4 735 CRE ; 278 IDs non nuls | usage réel du jeu stock |
| CRE stock avec BAM | 273 | 8 503 BAM uniques, 2 260 139 frames | corpus physique maximal actuel |
| CRE stock sans BAM | 6, dont `0x0000` | 5 IDs non nuls | aucune production possible sans assets |
| CRE stock entièrement prêts | 101 | 2 400 CRE, soit 50,686 % | candidats immédiats |
| CRE stock runtime sans BAM | 1 (`0xE520`) | — | bloqué `no-bam-resources` |
| CRE stock hors profils runtime avec BAM | 172 | — | profil moteur à implémenter |
| CRE stock hors profils runtime sans BAM | 5, dont `0x0000` | 4 IDs non nuls | profil et/ou assets absents |

Les 101 IDs stock prêts sont un sous-ensemble des 122 IDs éligibles de l'index. Le catalogue actif
en contient 2 (`0x6102`, `0x6110`) ; 99 restent donc des candidats stock immédiats. Les 172 IDs avec
BAM mais hors profils runtime exigent un profil moteur prouvé. Les cinq IDs non nuls sans BAM ne sont
pas productibles depuis cette installation. Exclure `0x0000` de toute production.

Dimensionnement non canonique, à recalculer après toute régénération :

| Corpus | V3 logique/layout | Projection V5 physique |
|---|---:|---:|
| 101 IDs stock prêts, par-ID sans déduplication | 62,27 Gio | ne pas produire ainsi |
| 101 IDs stock prêts, composants uniques | 7,147 Gio | non mesurée |
| 122 IDs éligibles de l'index | 382 composants, 389 shards | environ 1,37 Gio |
| 273 IDs utilisés avec BAM, si tous les profils existent | 10,84 Gio x2 ; 39,96 Gio x4 | environ 2,03 Gio x2 ; 7,49 Gio x4 |

Les projections V5 appliquent le ratio physique observé sur les deux Characters actifs ; le corpus
complet, surtout x4, n'est pas mesuré. Traiter les fourchettes de planification `2–2,5 Gio` en x2 et
`7,5–9 Gio` en x4 comme scénarios, jamais comme gates. Le corpus des 273 IDs avec BAM tient dans les
limites de format (8 503 BAM uniques, 2 260 139 frames), mais 172 profils runtime manquent encore.
Les six valeurs sans BAM ne font pas partie de cette projection.

Le CAS déduplique les shards V5 entre générations. Il ne supprime ni les anciens builds V3, ni les
jobs, états ou backups. Ne jamais sommer `FileInfo.Length` entre le CAS et ses générations hardlinkées
pour estimer l'espace réellement alloué ; mesurer les identités de fichiers ou l'allocation disque.

Recalcul minimal de l'éligibilité de l'index et des composants dédupliqués :

```powershell
$families = Import-Csv sprite/index/sprite_families.csv
$eligible = @($families | Where-Object {
    $_.runtime_supported -eq 'yes' -and
    $_.pipeline_ready -eq 'yes' -and
    [string]::IsNullOrEmpty($_.blocker) -and
    [string]::IsNullOrEmpty($_.override_collision)
})
$components = @($eligible | Group-Object bam_prefix | ForEach-Object { $_.Group[0] })
[pscustomobject]@{
    animation_ids = @($eligible.animation_id | Sort-Object -Unique).Count
    memberships = $eligible.Count
    unique_components = $components.Count
    projected_shards_x2 = ($components | Measure-Object shard_count_x2 -Sum).Sum
    physical_resources = ($components | Measure-Object resource_count -Sum).Sum
    physical_frames = ($components | Measure-Object frame_count -Sum).Sum
}
```

### Gates de taille

Appliquer avant chaque append. Le seuil de 900 Mio est un gate opérateur du runbook ; le runner ne
l'impose pas encore automatiquement :

```text
format/capacité             tous les maxima catalogue, shard et frame passent
taille marginale            < 900 Mio de shards physiques pour l'animation ajoutée
stockage                    total_registry_bytes et stored_index_bytes viennent du build vérifié
mémoire                     aucun budget runtime n'est augmenté pour faire passer le contenu
historique                  aucune suppression de job/build/état/backup/CAS
projection globale          déclarée comme projection, jamais comme mesure
```

Pour rendre le seuil marginal non ambigu, ajouter une animation ID par job d'append. Après la
migration V5, comparer le manifeste proposé à l'état actif :

```powershell
$catalogJob = 'sprite/catalogs/creature-x2-nearest/jobs/creature-sprites-progressive-xn-xbr2x.json'
$run = 'sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/runs/catalog-xbr2x-x2'
$state = Get-Content -LiteralPath "$run/ingame-installation/active-test.json" -Raw |
    ConvertFrom-Json
$pointer = Get-Content -LiteralPath "$run/current-generation.json" -Raw |
    ConvertFrom-Json
$build = Get-Content -LiteralPath (
    Join-Path (Resolve-Path $pointer.generation_dir) $pointer.build_manifest
) -Raw | ConvertFrom-Json
if ($state.catalog_version -ne 2 -or $state.shard_registry_version -ne 5) {
    throw 'Mesure marginale réservée à un append V2/V5'
}
$addedIds = @($build.animation_ids | Where-Object { $_ -notin @($state.animation_ids) })
$delta = [int64]$build.totals.total_registry_bytes - [int64]$state.total_registry_bytes
if ($addedIds.Count -ne 1) { throw 'Mesurer un append d’une seule animation ID' }
if ($delta -lt 0) { throw 'Delta physique négatif incohérent' }
if ($delta -ge 900MB) { throw "Animation trop volumineuse : $delta octets" }
```

Ce gate mesure les nouveaux shards uniques après déduplication ; il n'attribue pas plusieurs fois
un composant partagé.

## Procédure reproductible

Toutes les commandes partent de `G:\AI\BG2_Upscale`. Elles inspectent, construisent ou installent ;
aucune ne lance le jeu.

### 1. Vérifier les processus et le job

```powershell
Set-Location 'G:\AI\BG2_Upscale'
$catalogJob = 'sprite/catalogs/creature-x2-nearest/jobs/creature-sprites-progressive-xn-xbr2x.json'
$catalog = Get-Content -LiteralPath $catalogJob -Raw | ConvertFrom-Json
$run = [string]$catalog.paths.run_dir
$running = @(Get-Process InfinityLoader,Baldur,BaldurReal -ErrorAction SilentlyContinue)
if ($running.Count -ne 0) { throw 'Fermer InfinityLoader, Baldur et BaldurReal' }

python pipeline/scripts/run_creature_sprite_x2.py plan --job $catalogJob
if ($LASTEXITCODE -ne 0) { throw 'Plan catalogue refusé' }
```

Exiger au minimum :

```text
baldur_real_compatible=true
registry_layout_policy=content-addressed-multi-animation-catalog
generation_shards_are_hardlinks=true
game_install_shards_are_independent_copies=true
game_launch_is_never_automatic=true
release_manifest_is_out_of_scope=true
```

### 2. Préparer et vérifier la génération

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare --job $catalogJob --resume
if ($LASTEXITCODE -ne 0) { throw 'Préparation catalogue refusée' }

python pipeline/scripts/run_creature_sprite_x2.py verify --job $catalogJob
if ($LASTEXITCODE -ne 0) { throw 'Vérification catalogue refusée' }
```

Exiger :

```text
status=prepared-verified
registry_layout=catalog
catalog version=2
shard registry version=5
frame_storage=XPRESS_HUFF-or-raw-per-frame-v1
build.validation.records_copied_without_xbr=true
build.validation.logical_records_preserved_after_lossless_storage_repack=true
build.validation.palette_frames_exactly_remapped=build.totals.total_frames
build.validation.partial_alpha_pixels=0
build.validation.new_colors=0
build.validation.override_collisions=0
runtime.status=built-tested
runtime.tests_status=passed
runtime.bridge_worker_tests_status=passed
```

Ne pas installer si un test Python ou C++ du runtime a échoué. Suite de régression locale :

```powershell
python -m unittest `
  pipeline.tests.test_creature_sprite_xn_catalog `
  pipeline.tests.test_creature_sprite_xn_catalog_install `
  pipeline.tests.test_creature_sprite_x2_pipeline
if ($LASTEXITCODE -ne 0) { throw 'Régression sprites refusée' }
```

### 3. Préflight et installation

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile $catalogJob `
  -VerifyOnly
if ($LASTEXITCODE -ne 0) { throw 'Préflight installation refusé' }

python pipeline/scripts/run_creature_sprite_x2.py install --job $catalogJob
if ($LASTEXITCODE -ne 0) { throw 'Installation catalogue refusée' }

python pipeline/scripts/run_creature_sprite_x2.py status --job $catalogJob
if ($LASTEXITCODE -ne 0) { throw 'Statut catalogue illisible' }
```

Pour la migration courante V1/V3 vers V2/V5, exiger `Mode=storage-repack`. Pour une future
créature, exiger `Mode=append`. Ne jamais poursuivre si le mode diffère de l'intention.

### 4. Analyse de log après une session ingame

Appliquer la politique de [`sprite/README.md`](../../README.md#politique-de-qa-ingame-pilotée). Après fermeture
du jeu, que la session ait été contrôlée par l'utilisateur ou par l'agent explicitement autorisé :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py qa-log `
  --job $catalogJob `
  --write-report
if ($LASTEXITCODE -ne 0) { throw 'Analyse de log refusée' }
```

### 5. Préflight et restauration d'un niveau

Utiliser le job exact de l'état actif :

```powershell
$statePath = "$run/ingame-installation/active-test.json"
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$activeJob = [string]$state.job_file

powershell -NoProfile -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile $activeJob `
  -VerifyOnly
if ($LASTEXITCODE -ne 0) { throw 'Préflight restauration refusé' }

python pipeline/scripts/run_creature_sprite_x2.py restore --job $activeJob
if ($LASTEXITCODE -ne 0) { throw 'Restauration catalogue refusée' }
```

Si le niveau restauré n'est plus un catalogue, sélectionner son restaurateur depuis son schéma :
overlay x4 dédié, xN standard ou x2 historique. Ne pas réutiliser la commande catalogue par défaut.

## Gates de QA et de performances

Le log d'une session V2 saine doit contenir :

```text
Creature sprite xBR catalog ready: ... catalog-version=V2 ...
... source=CreatureSprites-XN.catalog; filter=NEAREST ...
Creature sprite catalog shard <N> ready on demand for animation 0xNNNN, resref <RESREF>: ...
Creature sprite animation 0xNNNN reached <owner>::Render
Composing creature sprite <PREFIXE> ... animation=0xNNNN ... NEAREST ...
```

Le parser accepte encore l'ancien marqueur `catalog animation ... materialized` pour une génération
historique. Pour V2, le marqueur `ready on demand` prouve le chargement progressif.

Exiger :

- source catalogue et DLL conformes à l'état installé ;
- au moins un marqueur `ready on demand` dans la session pour prouver le chemin lazy ; un shard
  partagé déjà résident peut ne pas produire un nouveau marqueur pour chaque animation ;
- animation atteinte et composition scoped pour chaque animation exercée ;
- composition `NEAREST` pour chaque couple `(animation_id,préfixe)` requis ;
- zéro `Creature sprite catalog component ... quarantined:` ;
- zéro échec lazy, reset de pool, texture non liée, rejet de backing ou upload in-place ;
- directions, actions, palettes, pivots, équipements et changements de zone corrects ;
- sauvegarde/chargement et sortie du jeu sans crash ;
- après ajout de la télémétrie catalogue exigée plus haut, zéro rechargement disque répété sur un
  cache hit ;
- temps de chargement comparé sur la même sauvegarde avant/après, en distinguant première rencontre
  asynchrone et parcours chaud.

La première frame d'un shard peut rester native pendant le chargement asynchrone. Le premier payload
xN peut ensuite produire un hitch synchrone de lecture/hash/décompression. Un fallback transitoire
est prévu ; une boucle de chargement, une quarantaine ou l'absence persistante de remplacement ne
l'est pas.

Le parser actuel n'agrège pas les preuves entre sessions : `technical_pass=true` exige toutes les
animations et tous les préfixes du catalogue dans une même session post-installation. Tester
seulement l'ID ajouté constitue un smoke incrémental, pas une validation globale. Conserver
`installed-pending-qa` et ne pas exécuter `record-qa --result pass` tant que la couverture globale
n'est pas complète et explicitement acceptée par l'utilisateur.

### Smoke V2/V5 observé le 26 août 2026 — non canonique

La source live reste `active-test.json`, le log du jeu et la sortie courante de `qa-log`. L'instantané
ci-dessous documente la session analysée ; il ne remplace aucun gate :

```text
initialisation DLL -> catalogue prêt   346 ms (V1 précédent : 15,869 s)
premier fallback -> shard CDMB1 prêt   66 ms
shard prêt -> premier composite        11 ms
cadence chaude                         ~164–165 fps, dropped=0
quarantaine/échec lazy/reset           0 observé
fallback natif pré-ready               1 warning attendu
couverture                             0x6102/CDMB1 seulement
0x6110                                 non atteint
technical_pass                         false
état                                   installed-pending-qa
log SHA-256                            0012155606B89D4092484C06B30A0F351447068E6A0A088E2AD4AE471F9C501B
```

La première demande de shard est postérieure au chargement de la sauvegarde dans cette session ;
elle n'explique donc pas la lenteur perçue de ce chargement. La sortie V2 n'a produit aucun événement
WER 1000/1001, sans prouver la stabilité du bestiaire complet. Une mesure exploratoire après cette
charge a observé environ 571 Mio de working set et 903 Mio de mémoire privée ; ne pas utiliser ces
valeurs comme cible ou gate.

## Recherche future de taille : V6, non implémenté et non mesuré

Aucun script, rapport ni artefact reproductible du dépôt ne mesure actuellement un format V6.
Ne citer aucune taille V6 et ne pas annoncer une cible globale `<1 Gio` avant un benchmark scellé du
corpus explicite.

V6 n'est pas implémenté : aucun writer, parser runtime, inspecteur, installateur, restaurateur,
test de corruption ou format binaire V6 ne fait partie du contrat actuel. Ne jamais étiqueter un
artefact V5 comme V6 et ne rien installer sans format implémenté et benchmark scellé.

Gates avant toute implémentation V6 :

1. spécifier un format random-access borné et versionné ;
2. conserver une identité logique égale à la baseline V5 si la méthode reste sans perte ;
3. prouver la provenance exacte de chaque indice de palette, y compris les RGBA dupliqués ;
4. mesurer le corpus complet et démontrer `<1 Gio`, pas seulement extrapoler deux Characters ;
5. conserver les budgets de 128/128/128/4 Mio et le fallback natif ;
6. tester corruption, bombes de décompression, éviction, hot path sans E/S et arrêt des workers ;
7. ajouter une migration et une restauration LIFO vers V5/V3 sans supprimer l'historique ;
8. refaire la QA ingame Character et MonsterIcewind.

Autres pistes à étudier seulement dans des prototypes séparés : déduplication de frames/blocs entre
shards, deltas temporels bornés et upscale à la volée depuis les BAM natifs. Elles ajoutent des
indirections, du CPU ou un risque d'écart xBR et ne remplacent pas V5 sans mesures. Une méthode
avec perte peut être envisagée puisque la contrainte l'autorise, mais elle doit rester hors du
catalogue validé tant qu'elle ne démontre pas palettes dynamiques, tints, alpha et stabilité
temporelle. Ne jamais fusionner arbitrairement deux indices qui partagent le même RGBA.

## Arrêts obligatoires

Arrêter sans contournement sur : identité d'animation incohérente, famille non prête, collision
`override`, méthode/échelle mixte, AA V4, limite dépassée, shard ou directory divergent, digest
logique différent, génération non scellée, CAS non hardlinkée, DLL non testée, processus du jeu
ouvert, état concurrent inconnu, append non strict, backup/source de restauration absent ou QA
technique incomplète.

Ce document ne rend aucun pack x2 éligible au manifeste de release.
