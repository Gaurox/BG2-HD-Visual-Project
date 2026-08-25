# Pipeline LLM — sprite de créature ou calque Character xBR2x x2

Ce document est le contrat historique x2 pour les jobs sans bloc `upscale`. Les règles d'identité,
d'inventaire et de QA restent applicables aux jobs explicites. Pour un bloc `upscale`, une cible x4,
un registre `CreatureSprites-XN.registry` ou le flag `EnableCreatureSpriteUpscaleTest`, appliquer en
plus [`SPRITE_UPSCALE_XN_FOUNDATION.md`](SPRITE_UPSCALE_XN_FOUNDATION.md), qui prévaut sur les
constantes x2 de ce document.

Pour produire toutes les variantes et tous les équipements d'un animation ID Character, appliquer
directement [`CHARACTER_COMPLETE_X2_RUNBOOK.md`](CHARACTER_COMPLETE_X2_RUNBOOK.md). Ce runbook porte
la validation opérationnelle de référence et la séquence sans décision manuelle.

## Contrat

- Traiter une famille BAM V1 BG2EE.
- Produire un registre externe V2 ; ne jamais installer de BAM x2 dans `override`.
- Utiliser `XBR/xbr2X`, x2, une passe, `xbr_blend=false`, anti-alias désactivé.
- Conserver géométrie, centres, cycles, cadence et palette en x1.
- Afficher le backing x2 avec `NEAREST`, sans mipmaps.
- Ne jamais lancer le jeu. Demander à l’utilisateur d’utiliser `InfinityLoader.exe`.
- Ne jamais modifier le manifeste de release sans accord affirmatif explicite.
- Un job cible un seul animation ID et un seul calque : corps avec un code d’armure, ou famille
  d’équipement résolue depuis un ITM stock. Un bundle Character agrège des jobs du même ID dans
  un registre unique pour couvrir les changements d’équipement ingame.

## Échantillonnage d'affichage : NEAREST / LINEAR

Portée : runtime de sprites xN uniquement. Le réglage modifie le filtre OpenGL du backing déjà
construit. Il ne modifie ni PNG, ni BAM, ni registre, ni palette, ni géométrie, ni manifeste.
Pour intégrer ce filtre dans un essai comparatif réversible avec d'autres variantes, appliquer
[`SPRITE_UPSCALE_VARIANT_TEST_RUNBOOK.md`](SPRITE_UPSCALE_VARIANT_TEST_RUNBOOK.md).

Préconditions :

```text
- InfinityLoader, Baldur et BaldurReal fermés.
- InfinityEngine-Enhancer.dll compilée depuis une révision qui contient
  EnableCreatureSpriteLinearFiltering.
- Un seul test sprite xN actif.
```

Dans `<GameRoot>\InfinityEngine-Enhancer.ini`, sous `[Shaders]`, conserver une seule occurrence de
la clé :

```ini
; Baseline et seule configuration éligible à la QA formelle.
EnableCreatureSpriteLinearFiltering = false

; Comparaison visuelle locale uniquement.
; EnableCreatureSpriteLinearFiltering = true
```

| Valeur | Filtre | Usage | Éligible à `record-qa --result pass` |
|---|---|---|---|
| `false` | `NEAREST` | baseline, QA et release | oui |
| `true` | `LINEAR` | comparaison visuelle locale | non |

Après chaque changement, relancer le jeu via `<GameRoot>\InfinityLoader.exe`. Ne pas reconstruire
les assets ni réinstaller le registre. Après une session, lire les dernières lignes de
`<GameRoot>\InfinityEngine-Enhancer.log` et exiger :

```text
filter=NEAREST  # baseline / QA
filter=LINEAR   # comparaison locale
```

Avant `qa-log` ou `record-qa`, remettre la valeur à `false`, relancer le jeu, couvrir tous les
préfixes requis et obtenir les compositions `NEAREST` exigées par le job. Une session `LINEAR`, ou
une DLL de comparaison non attendue par l'état d'installation, ne produit jamais
`validated-installed`.

CLI : `pipeline/scripts/run_creature_sprite_x2.py`  
Jobs de référence : `sprite/jobs/goblin-mgo1-xbr2x.json`,
`sprite/jobs/human-female-fighter-chfb1-xbr2x.json` et
`sprite/jobs/human-female-fighter-complete-xn-xbr2x.json`
Point d'entrée agent : [`README.md`](README.md)  
Contrat xBR : [`UPSCALE_XBR2X.md`](UPSCALE_XBR2X.md)  
Inventaire global : [`index/README.md`](index/README.md)

## Gate I0 — résoudre la famille dans l'inventaire

Avant de créer ou copier un job :

1. lire la ligne de l'ID dans `index/sprite_animations.csv` ;
2. sélectionner exactement une ligne de `index/sprite_families.csv` par `animation_id`,
   `layer_kind`, `variant_kind`, `variant_value` et `bam_prefix` ;
3. pour un équipement, confirmer `item_resref`, `item_type_symbol`, `animation_code` et les
   préfixes résolus dans `index/sprite_items.csv` ;
4. lire toutes les lignes `sprite_resources.csv` dont `family_ids` contient le `family_id` ;
5. conserver `family_id` et les diagnostics de la ligne dans le compte rendu du job.

Un job de production exige :

```text
runtime_supported=yes
pipeline_ready=yes
blocker=<vide>
override_collision=<vide>
```

Une tâche d'évolution du pipeline peut cibler `pipeline_ready=no`. Dans ce cas, prendre les
valeurs de `blocker` comme critères d'acceptation, ne pas contourner le scanner, modifier ses règles
si le contrat du pipeline évolue, régénérer les quatre CSV et exécuter les tests d'index. Arrêter
avant création ou installation d'un job si un bloqueur non ciblé subsiste.

Ne jamais résoudre une famille depuis un ancien manifeste d'extraction. Exemple de régression :
`0x6100 FIGHTER_MALE_HUMAN` utilise `CHMB*`; `CHMM1` appartient à
`0x6500 MONK_MALE_HUMAN`.

## Créer un job de personnage

Lire l’animation ID exacte dans le CRE ou la sauvegarde, puis résoudre son symbole dans
`ANIMATE.IDS`. Si seul le symbole est fourni, le lire directement dans `ANIMATE.IDS`. Ne pas
déduire l’animation depuis le nom, le portrait ou l’apparence.

```powershell
python pipeline/scripts/run_creature_sprite_x2.py new-character-job `
  --job sprite/jobs/<job>-xbr2x.json `
  --template-job sprite/jobs/human-female-fighter-chfb1-xbr2x.json `
  --ids-symbol <SYMBOLE_ANIMATE_IDS> `
  --animation-id 0xFFFF `
  --armor-code <1..MAX> `
  --name "<nom QA>" `
  --qa-area <ARxxxx> `
  --qa-creature <CRE>
```

`--animation-id` est optionnel. Le fournir si l’ID a été lu dans la sauvegarde : le générateur
doit alors confirmer l’égalité symbole/ID.

Utiliser `--armor-code 1` pour le corps sans armure stock. Ne jamais former le préfixe depuis
`resref_paperdoll` ni depuis un BAM `*INV`.

Le générateur doit :

1. résoudre le symbole dans `ANIMATE.IDS` ;
2. lire `<ID>.INI` de type 2050 depuis le KEY/BIF installé ;
3. exiger `animation_type=5000|6000`, section `[character]` et `split_bams=1` ;
4. lire `resref`, `armor_max_code`, `resref_armor_base` et
   `resref_armor_specific` ;
5. refuser un code hors `1..armor_max_code` ;
6. dériver le préfixe :
   - code inférieur au maximum : `<resref><code>` ;
   - code maximal avec resref spécifique : remplacer le suffixe
     `resref_armor_base` par `resref_armor_specific`, puis ajouter le code ;
7. exiger les 23 BAM corporels exacts : `A1..A9`, `CA`, `G1`, `G11..G19`, `SA`,
   `SS`, `SX` ;
8. exclure les paperdolls `*INV` ;
9. refuser `override/<ID>.INI` et `override/ANIMATE.IDS` ;
10. écrire `ids_symbol`, `armor_code`, le préfixe et le profil
    `character-bg2ee-2.7.3.0` dans le job.

Exiger `status=character-job-created`, `resource_count=23` et les valeurs attendues de
`animation_id`, `ids_symbol`, `bam_prefix`, `body_resref` et `armor_code`.

Régressions de référence :

- `FIGHTER_FEMALE_HUMAN`, `0x6110`, armure 1 → `CHFB1` ;
- `FIGHTER_FEMALE_HUMAN`, `0x6110`, armure 4 → `CHFF4` ;
- `THIEF_FEMALE_HUMAN`, `0x6310`, armure 1 → `CHFT1` ;
- `0x6310 + CHFB1` → refuser.

## Créer un job d’équipement Character

Ne pas deviner un préfixe d’équipement depuis son apparence. Partir d’un ITM stock et laisser le
pipeline croiser son code d’animation avec les codes de hauteur de `<ID>.INI` :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py new-character-equipment-job `
  --job sprite/jobs/<job>-xbr2x.json `
  --template-job sprite/jobs/human-female-fighter-chfb1-xbr2x.json `
  --ids-symbol <SYMBOLE_ANIMATE_IDS> `
  --animation-id 0xFFFF `
  --layer-kind <helmet|shield|weapon> `
  --item-resref <ITEM> `
  --name "<nom QA>" `
  --qa-area <ARxxxx> `
  --qa-creature <CRE>
```

Le générateur doit lire le type et le code d’animation à deux caractères dans `<ITEM>.ITM`, puis
former le préfixe avec `height_code_helmet`, `height_code_shield` ou `height_code`. Un code de
hauteur spécialisé vide retombe sur `height_code`. Il inventorie uniquement les suffixes
Character stock présents, exclut explicitement le paperdoll `<prefix>INV`, exige au moins un BAM
et refuse tout autre suffixe inconnu. Les anciens jobs
sans `animation.layer` restent des jobs corporels ; un job d’équipement écrit explicitement :

```json
"layer": { "kind": "helmet", "item_resref": "HELM01" }
```

Régressions BG2EE 2.7.3 pour `FIGHTER_FEMALE_HUMAN` (`height_code=WQN`) :

- `HELM01`, type casque, code `J6` → `WQNJ6`, 14 ressources ;
- `SHLD01`, type bouclier, code `C0` → `WQNC0`, 5 ressources ;
- `SHLD08`, type bouclier, code `C4` → `WQNC4`, 5 ressources.

Refuser `override/<ITEM>.ITM`, un type casque/bouclier incohérent ou un préfixe déclaré différent
de celui dérivé du couple INI/ITM.

## Générer un Character complet

Pour couvrir toutes les familles visuelles d'un même ID Character, générer les jobs depuis
`index/sprite_families.csv` plutôt que d'énumérer manuellement les ITM :

```powershell
python pipeline/scripts/generate_character_complete_x2_jobs.py `
  --animation-id 0xFFFF `
  --template-job sprite/jobs/<membre-existant>-xbr2x.json `
  --job-stem <character> `
  --aggregate-job sprite/jobs/<character>-complete-xbr2x.json
```

Le générateur réutilise un job x2 compatible par `bam_prefix`, crée un membre explicite x2 pour
chaque préfixe manquant, choisit l'ITM lexicographiquement premier comme représentant et publie
l'agrégat explicite en dernier. Une famille sans BAM est consignée comme exclue ; tout autre
blocker arrête la production. Cette commande ne produit aucun pixel.

Ne pas passer cet agrégat par `promote-armor-set-job` : il référence directement un mélange audité
de membres legacy V2/x2 réutilisés et de membres XN V3/x2. Un membre explicite dépassant la limite
du monolithe est automatiquement écrit comme registry-set, puis ses records sont aplatis lors de
la construction du Character complet. Chaque resref doit néanmoins tenir dans un shard.

Exécuter `extract --resume` puis `build --resume` sur les seuls membres sans build valide. Exécuter
ensuite `prepare --resume` une seule fois sur l'agrégat pour construire le set global et le runtime.
La boucle PowerShell canonique et les gates de reprise sont dans
[`CHARACTER_COMPLETE_X2_RUNBOOK.md`](CHARACTER_COMPLETE_X2_RUNBOOK.md) ; ne pas réinventer cet
ordonnancement pour chaque animation ID.

## Créer un job MonsterIcewind

Copier `sprite/jobs/goblin-mgo1-xbr2x.json`. Modifier `job_id`, `animation`,
`source_dir`, `run_dir` et `qa`. Utiliser `monster-icewind-bg2ee-2.7.3.0` uniquement pour une
animation `0xE000`. Arrêter pour toute autre classe moteur non prise en charge.

## Exécuter un job

Toutes les commandes partent de la racine du dépôt.

### 1. Préflight

```powershell
python pipeline/scripts/run_creature_sprite_x2.py plan --job sprite/jobs/<job>.json
```

Exiger :

```text
runtime_profile_supported=true
baldur_real_compatible=true
scalepix_exists=true
game_launch_is_never_automatic=true
release_manifest_is_out_of_scope=true
```

Pour Character, exiger aussi :

```text
animation_identity_compatible=true
animation_identity.ids_symbol=<symbole demandé>
animation_identity.ini=<ID>.INI
animation_identity.bam_prefix=<préfixe attendu>
animation_identity.resource_count=<inventaire exact du calque>
```

Le corps complet compte 23 ressources. Un équipement peut n’exposer que les séquences réellement
fournies par le jeu ; l’inventaire exact est persisté dans les manifestes source et build.

### 2. Extraction, upscale, runtime et vérification

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare `
  --job sprite/jobs/<job>.json `
  --resume
```

Exiger `status=prepared-verified` et `override_collisions=0`.

Lire seulement :

- `<source_dir>/manifest.json` ;
- `<run_dir>/build/build-manifest.json` ;
- `<run_dir>/runtime/runtime-manifest.json` ;
- `<run_dir>/build/qa/*-comparison.png`.

Exiger :

```text
algorithm=XBR/xbr2X
scale=2
passes=1
antialias=false
xbr_blend=false
dimensions_exact_x2=frame_count
frames_exactly_remapped_to_source_palette=frame_count
partial_alpha_pixels=0
new_colors=0
runtime.status=built-tested
runtime.tests_status=passed
```

Utiliser `--force` uniquement pour remplacer les sorties exactes du job courant. Ne pas utiliser
`--keep-x2-frames` hors diagnostic.

### Bundle de calques Character

Le schéma historique `armor-set-v1` est conservé pour rétrocompatibilité, mais accepte désormais
les jobs de corps, casque, bouclier et arme. Préparer d'abord chaque membre. Créer un bundle
seulement si les membres ont le même ID, symbole `ANIMATE.IDS`, profil, jeu et hash de
`BaldurReal.exe`. Le bundle refuse les codes corporels ou préfixes dupliqués et concatène les
registres V2 sans modifier les BAM.

Cette concaténation monolithique concerne seulement un set sans bloc top-level `upscale`. Un set
explicite suit `SPRITE_UPSCALE_XN_FOUNDATION.md` : registres XN V3 shardés, index
`CreatureSprites-XN.set`, validation SHA256/CRC32 et chargement lazy. En x2, le builder peut
promouvoir les registres V2 membres déjà construits vers V3 sans relancer xBR ni modifier leurs
records et payloads.

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare `
  --job sprite/jobs/<character>-character-set-xbr2x.json `
  --resume
```

Le bundle est ensuite installé, testé, restauré et validé avec les commandes standard. Ne jamais
reprendre l'ancien bundle abrégé de quelques équipements comme définition d'un Character complet.
La référence guerrière humaine est
`sprite/jobs/human-female-fighter-complete-xn-xbr2x.json` : elle contient toutes les familles avec
BAM déclarées par l'inventaire canonique ; les familles sans BAM restent des exclusions explicites.
Lire les comptes de ressources, frames et shards dans les manifestes générés plutôt que les recopier
dans cette documentation. `qa-log` exige au moins une composition `NEAREST` pour chaque préfixe
avant `record-qa --result pass`.

Le runtime Character BG2EE 2.7.3 surveille jusqu’à quatre cellules : corps, arme,
offhand/bouclier et casque, aux offsets manifestés `D00`, `1360`, `1888` et `1DB0`. À chaque
rendu, il capture les événements `CVidPalette::Realize` du callsite validé dans l’ordre moteur,
résout de nouveau la frame active, reproduit le composite CPU natif x2 en recopiant chaque couleur
palette non nulle dans l’ordre moteur tout en conservant son alpha, aligne par les centres BAM,
puis remplace une seule fois le composite final. La taille logique doit être exactement
l’union des calques actifs plus la bordure native d’un pixel. Un calque actif non enregistré, une
capture manquante, un encodage divergent, un dépassement de huit événements ou une taille finale
différente impose le fallback natif du personnage entier. Une cellule candidate non rendue ne
bloque pas la composition.

Pour une arme, inclure aussi les BAM de main gauche `OA7`, `OA8`, `OA9` et `OG1` lorsqu'ils
existent. Ils appartiennent au même préfixe d'animation ITM que les suffixes standards et sont
obligatoires pour couvrir le dual-wield ; ne pas les classer comme ressources inattendues.

Le runtime Character ne doit jamais modifier le backing GL du composite natif. Conserver seulement
un cache CPU borné de 32 composites. Pour chaque dessin : mémoriser l’ID logique natif, créer un ID
moteur privé avec `DrawGenTexture(sampler)`, le lier, matérialiser son backing logique, uploader les
pixels x2, imposer `sampler`, `CLAMP_TO_EDGE` et niveau maximal zéro, appeler le rendu original,
restaurer l’ID natif, puis appeler `DrawDeleteTexture` sur l’ID privé. Toute sortie postérieure à
`DrawGenTexture` doit restaurer l’ID natif et marquer l’ID privé `delete-pending`. Ne conserver aucun
ID Character entre deux dessins. Avant l’upload, valider l’ID `1..511` contre la table manifestée
`glTextureTable` : nom GL non nul, `delete-pending=0`, backing secondaire `+0x24=0`, puis après
`TexImage`, nom GL lié, backing secondaire nul et dimensions logiques exactement égales au
descripteur. Si `DrawGenTexture` recycle un ID privé dont `+0x24` est non nul, valider le champ avec
la signature manifestée de `DrawFlush`, vérifier la table RW, zéroïser uniquement ce sélecteur sans
supprimer son nom GL potentiellement partagé, puis relire le descripteur. Tout échec impose le
fallback natif et la suppression de l’ID privé. Ne jamais hooker
`DrawClearTextures` (`0x413330`) pour invalider les caches : ce wrapper est appelé en continu,
parfois plusieurs fois par frame ; il flush le batch puis libère uniquement les slots déjà marqués
`delete-pending`. Oublier depuis ce point des IDs encore vivants épuise les 511 slots utilisables,
provoque des réuploads en boucle, des textures UI noires et l'effondrement des FPS.

`sampler=NEAREST` hors diagnostic. `sampler=LINEAR` seulement lorsque
`EnableCreatureSpriteLinearFiltering=true`; appliquer alors les exclusions de QA de la section
`Échantillonnage d'affichage : NEAREST / LINEAR`.

### 3. Installation QA réversible

Fermer `BaldurReal`, `Baldur` et `InfinityLoader`. Restaurer d'abord tout autre test sprite actif.

Les commandes ci-dessous concernent le registre V2 historique et le flag alias
`EnableCreatureSpriteX2Test`. Un job portant `upscale` doit utiliser les scripts xN et le registre V3
décrits dans `SPRITE_UPSCALE_XN_FOUNDATION.md`.

L'installateur historique refuse désormais tout `CreatureSprites-XN.set` ou
`CreatureSprites-XN.registry` présent dans le jeu : le runtime donne priorité à XN et masquerait
sinon le pack V2 soumis à la QA. Restaurer d'abord le test xN concerné.

```powershell
python pipeline/scripts/run_creature_sprite_x2.py install --job sprite/jobs/<job>.json
```

Exiger `status=installed-pending-qa`. Le script doit vérifier les hashes, refuser les collisions
corporelles dans `override`, sauvegarder DLL/INI/registre, installer le registre externe, activer
`EnableCreatureSpriteX2Test=true` et laisser le jeu fermé.

### 4. QA ingame

Demander à l’utilisateur :

```text
Lance <GameRoot>\InfinityLoader.exe, charge <zone QA>, teste <CRE QA>, puis ferme le jeu.
```

Contrôler : actions et directions, palettes, taille, centre, point d’appui, cadence, alpha,
ombres, tints, clipping, corps avec équipement, plusieurs créatures, sauvegarde/chargement,
changement de zone, sommeil, ouverture/fermeture d’inventaire, stabilité et performances. Équiper
et retirer successivement chaque ITM couvert. Vérifier qu’aucune autre animation ID ni variante
d’armure ou d’équipement n’est remplacée. Après chaque reset d’écran, exiger un rendu net sans
redémarrage. Refuser toute session contenant `Engine texture pool reset observed`, des zones UI
noires, `No GL texture is bound` en rafale ou une cadence dégradée.

### 5. Preuve technique

```powershell
python pipeline/scripts/run_creature_sprite_x2.py qa-log `
  --job sprite/jobs/<job>.json `
  --write-report
```

Exiger `technical_pass=true` : session postérieure à l’installation, pack exact, scope exact,
animation atteinte, palette propriétaire capturée et au moins une ligne
`Composing creature sprite <PREFIXE>... transient replacement ... (NEAREST, delete-pending after
queued draw)` pour chaque préfixe Character. Exiger aussi `runtime_health_pass=true`, zéro reset de
pool, zéro warning de texture non liée, zéro rejet du backing privé, zéro échec de remplacement et
aucun ancien upload in-place.

### 6. Enregistrer la décision utilisateur

Après réponse explicite uniquement :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py record-qa `
  --job sprite/jobs/<job>.json `
  --result pass `
  --note "<validation utilisateur exacte>"
```

Utiliser `--result fail` pour un défaut. `pass` produit `validated-installed`. Aucun résultat QA ne
modifie le manifeste de release.

### 7. Restaurer

```powershell
python pipeline/scripts/run_creature_sprite_x2.py restore --job sprite/jobs/<job>.json
```

Fermer le jeu avant restauration.

## Invariants bloquants

- Exiger une ligne `sprite_families.csv` unique correspondant au job ; conserver son `family_id`.
- Croiser job, `ANIMATE.IDS`, `<ID>.INI`, préfixe BAM, manifeste source, manifeste build et
  manifeste runtime.
- Refuser profil/animation incompatibles : Character=`0x5000|0x6000`, MonsterIcewind=`0xE000`.
- Refuser source différente du KEY/BIF, inventaire incomplet, resref non corporel, cycle ou lookup
  invalide, géométrie modifiée, sortie non `2W×2H`, alpha partiel, nouvelle couleur ou palette
  dont la provenance d'indice ne restitue pas exactement le RGBA xBR.
- Refuser un monolithe ou shard x2 >128 Mio, x4 >512 Mio, >128 ressources par registre,
  >4096 frames par resref,
  ou un registry-set dépassant 64 shards, 8192 ressources, 1 048 576 frames et 8 Gio cumulés.
- Refuser exécutable, RVA, signature, renderer, contexte ou encodage GL incompatibles.
- Pour Character, refuser le composite x2 si un calque réellement rendu manque au registre ou si
  l’union calculée ne correspond pas à la taille logique finale fournie par le moteur.
- Pour Character, interdire tout cache d’ID moteur et toute mutation du backing natif. Utiliser un
  ID privé `DrawGenTexture` par dessin, valider son descripteur complet, rendre, restaurer l’ID natif,
  puis appeler `DrawDeleteTexture` sur l’ID privé.
- Refuser test actif, jeu ouvert et collision `override`.
- Au runtime, rendre le BAM natif à la moindre anomalie.

## Limites Character

- Traiter chaque animation ID et chaque calque dans un job séparé ; utiliser un bundle pour les
  charger simultanément.
- Le runtime accepte corps, arme, offhand/bouclier et casque ; le bundle doit couvrir tous les
  calques susceptibles d’être actifs ensemble. Le paperdoll reste hors périmètre.
- Un job d’équipement ne couvre que la famille BAM prouvée par son ITM stock et son INI Character.
- Conserver tous les arguments de dessin x1 ; backing physique x2 `NEAREST`.

## Release

- Ne jamais modifier `$mapSpecs`, `content.json`, le staging ou l’archive sans accord affirmatif.
- Considérer `validated-installed` comme un statut QA, pas comme une éligibilité automatique.
- Ne proposer aucun asset produit par ce pipeline : il est x2 et reste inéligible au manifeste de
  release.
- Ne jamais proposer `installed-pending-qa`, `qa-failed`, `override`, capture ou sauvegarde.

Question obligatoire en fin de tâche ingame :

```text
La tâche `<nom>` est terminée. Veux-tu que j'intègre au manifeste de release les éléments validés par cette tâche ?
```
