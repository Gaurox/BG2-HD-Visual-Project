# Runbook agent — comparer des variantes d'upscale de sprite

## Objet

Appliquer ce runbook pour produire, installer, comparer, restaurer et conserver plusieurs variantes
d'un même sprite sans modifier les builds ni les états antérieurs.

Sources de vérité obligatoires :

```text
identité et sélection    sprite/index/manifest.json et sprite/index/*.csv
contrat x2 historique   sprite/docs/archive/SPRITE_UPSCALE_PIPELINE.md
contrat xN/x4 V3        sprite/docs/archive/SPRITE_UPSCALE_XN_FOUNDATION.md
contrat xBR             sprite/docs/archive/UPSCALE_XBR2X.md
état de production      <run_dir>/build/build-manifest.json
état runtime            <run_dir>/runtime/runtime-manifest.json
état ingame             <run_dir>/ingame-test/active-test.json
résultat comparatif     document d'essai dédié au sprite
```

Ne jamais déduire un resref ou un préfixe depuis l'apparence. Ne jamais prendre un rapport d'essai
comme état ingame courant : lire `active-test.json` et recalculer les hashes des cibles.

## Gate de sélection

Résoudre l'animation, la famille et les ressources selon
[`sprite/README.md`](../../README.md). Exiger :

```text
runtime_supported=yes
pipeline_ready=yes
blocker=<vide>
override_collision=<vide>
```

Pour un test corporel Character sans armure, sélectionner `layer_kind=body` et `armor_code=1`.
Pendant la QA, ne rien équiper dans les emplacements armure, arme, main gauche/bouclier et casque.

## Choisir la variante

| Variante | Production | Registre | Filtre | Usage |
|---|---|---|---|---|
| x2 sans AA | `XBR/xbr2X`, x2, 1 passe, `antialias=false`, `xbr_blend=false` | V3 pour un job explicite | `NEAREST` | baseline et QA |
| x2 sans AA + LINEAR | aucun rebuild ; même registre x2 | inchangé | `LINEAR` | comparaison locale uniquement |
| x2 AA | `XBR/xbr2X`, x2, 1 passe, `antialias=true`, `xbr_blend=true` | V4 à recettes de palette | `NEAREST` | expérimental, mono-corps |
| x4 sans AA | appel direct `XBR/xbr4X`, x4, 1 passe, `antialias=false`, `xbr_blend=false` | V3, échelle 4 | `NEAREST` | comparaison x4 et QA |

Interdictions :

- ne jamais produire x4 par deux passes xBR2X ;
- ne jamais router une sortie AA vers le registre V2/V3 à indices simples ;
- ne jamais utiliser `LINEAR` pour `record-qa --result pass` ;
- ne jamais comparer simultanément un corps cible et des overlays d'équipement natifs ou issus d'un
  autre pack ;
- ne jamais traiter x2 AA comme une option booléenne du runner xN standard. Le chemin V4 doit
  conserver la provenance exacte des indices et vérifier le RGBA reproduit.

Le chemin AA actuel est limité à `CDMB1`. Pour un autre sprite, dériver un job, un runner, un build
moteur, un registre et une transaction dédiés à partir du prototype documenté dans
[`SPRITE_UPSCALE_XBR2X_AA_TEST.md`](SPRITE_UPSCALE_XBR2X_AA_TEST.md). Ne pas modifier le prototype
`CDMB1` pour changer sa cible.

## Isoler les variantes

Créer des chemins uniques pour chaque variante :

```text
sprite/families/<profile>/<family>/<unique-sprite>/jobs/<sprite>-<variant>.json
sprite/families/<profile>/<family>/<unique-sprite>/source/
sprite/families/<profile>/<family>/<unique-sprite>/runs/<variant>/
sprite/.work/cmake/<profile>/<short-cache-key>/
sprite/families/<profile>/<family>/<unique-sprite>/runs/<variant>/ingame-test/
```

Exiger les invariants suivants avant `prepare` :

```text
job_id unique
paths.source_dir unique
paths.run_dir unique
paths.engine_build unique
job.upscale exact
```

`new-character-job` recopie `paths.engine_build` depuis le template. Modifier ce champ dans le
nouveau job pour pointer vers un dossier CMake dédié avant la première production.

Un manifeste source est lié à son `job_id`, à son contrat et à ses hashes. Si le nouveau job change
d'identité ou de variante, utiliser son `source_dir` séparé et relancer `extract --resume`. Ne pas
copier un ancien `manifest.json` dans ce dossier. Le runner peut reprendre les fichiers qu'il a lui-
même validés ; il doit refuser un manifeste lié à un autre job.

Ne jamais utiliser `--force` sur le job, le source, le run ou le build moteur d'une variante
antérieure. Conserver les builds après restauration ingame pour permettre leur réactivation.

## Créer un job x2 ou x4 non-AA

Depuis la racine du dépôt :

```powershell
$job = 'sprite/families/playable-characters/<animation-id>-<character-type>/<unique-sprite>/jobs/<sprite>-xbr2x.json' # ou <sprite>-xbr4x.json
$template = 'sprite/families/playable-characters/6110-human-female-fighter/chfb1/jobs/human-female-fighter-chfb1-xbr2x.json'

python pipeline/scripts/run_creature_sprite_x2.py new-character-job `
  --job $job `
  --template-job $template `
  --ids-symbol <SYMBOLE_ANIMATE_IDS> `
  --animation-id 0xFFFF `
  --armor-code 1 `
  --name '<nom QA>' `
  --qa-area <ARxxxx> `
  --qa-creature <CRE> `
  --scale <2|4>
```

Le nom du job doit finir par `-xbr2x.json` pour x2 et `-xbr4x.json` pour x4. Après génération,
modifier uniquement les champs de configuration propres à la variante, notamment
`paths.engine_build`. Ne pas modifier l'identité résolue par le générateur.

Pour un calque d'équipement Character :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py new-character-equipment-job `
  --job $job `
  --template-job $template `
  --ids-symbol <SYMBOLE_ANIMATE_IDS> `
  --animation-id 0xFFFF `
  --layer-kind <helmet|shield|weapon> `
  --item-resref <ITM_STOCK> `
  --name '<nom QA>' `
  --qa-area <ARxxxx> `
  --qa-creature <CRE> `
  --scale <2|4>
```

Pour un Character complet x2, appliquer
[`CHARACTER_COMPLETE_X2_RUNBOOK.md`](CHARACTER_COMPLETE_X2_RUNBOOK.md). Commencer toute nouvelle
méthode par un seul corps `armor_code=1` avant de l'étendre aux armures et équipements.

Pour un sprite non-Character, partir d'un job du même profil runtime documenté dans
[`SPRITE_UPSCALE_PIPELINE.md`](SPRITE_UPSCALE_PIPELINE.md). Modifier seulement `job_id`, identité,
chemins isolés, QA et contrat `upscale`. Arrêter si aucun profil runtime compatible n'existe.

## Produire et vérifier x2/x4 non-AA

```powershell
python pipeline/scripts/run_creature_sprite_x2.py plan --job $job
python pipeline/scripts/run_creature_sprite_x2.py prepare --job $job --resume
python pipeline/scripts/run_creature_sprite_x2.py verify --job $job
```

Lire les totaux dans les manifestes du run. Ne pas recopier comme constantes ceux d'un autre
sprite. Exiger :

```text
status=prepared-verified
override_collisions=0
algorithm=XBR/xbr{scale}X
scale=<2|4>
passes=1
antialias=false
xbr_blend=false
registry_magic=IEECSXN
registry_version=3
registry_scale=<2|4>
dimensions_exact_x{scale}=frame_count
frames_exactly_remapped_to_source_palette=frame_count
partial_alpha_pixels=0
new_colors=0
runtime.status=built-tested
runtime.tests_status=passed
```

Pour x4, exiger explicitement un seul appel `xbr4X`. Pour un layout `set`, appliquer toutes les
gates d'index, shards, SHA256 et CRC32 de
[`SPRITE_UPSCALE_XN_FOUNDATION.md`](SPRITE_UPSCALE_XN_FOUNDATION.md).

## Produire et vérifier x2 AA

Ne pas généraliser le prototype sans conserver son contrat V4. Pour `CDMB1` uniquement :

```powershell
$job = 'sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr2x-aa/jobs/dwarf-male-fighter-cdmb1-aa-xbr2x.json'

python pipeline/scripts/run_creature_sprite_x2_aa.py plan --job $job
python pipeline/scripts/run_creature_sprite_x2_aa.py prepare --job $job --resume
python pipeline/scripts/run_creature_sprite_x2_aa.py verify --job $job
```

Exiger en plus des gates du document AA :

```text
registry_version=4
registry_layout=monolith
sampling=NEAREST
chaque provenance d'indice xBR conservée
RGBA Scalepix reproduit exactement par les recettes de palette
```

Les indices de palette qui partagent un même RGBA restent distincts. Aucun indice n'est fusionné ou
choisi arbitrairement. L'alpha partiel est autorisé et compté seulement pour ce test V4 mono-calque.

## Choisir le mode d'installation ingame

Fermer `InfinityLoader`, `Baldur` et `BaldurReal` avant toute mutation.

### Aucun test sprite actif

Pour x2/x4 non-AA V3, utiliser l'installation standard du runner :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py install --job $job
python pipeline/scripts/run_creature_sprite_x2.py status --job $job
```

L'installateur standard doit refuser un autre état sprite actif. Ne pas contourner ce refus.

Pour ajouter plusieurs animations dans une installation persistante unique, ne pas enchaîner les
installations standard et ne pas dériver un overlay. Construire un catalogue cumulatif et appliquer
[`SPRITE_UPSCALE_CATALOG_RUNBOOK.md`](SPRITE_UPSCALE_CATALOG_RUNBOOK.md). Son installateur accepte
seulement un import initial exact ou un append strict d'un catalogue qu'il possède ; il conserve
les layouts standard masqués pour restauration.

Pour le prototype AA V4, utiliser toujours son runner dédié, même sans parent :

```powershell
python pipeline/scripts/run_creature_sprite_x2_aa.py install --job $job
python pipeline/scripts/run_creature_sprite_x2_aa.py status --job $job
```

### Un test parent doit rester conservé

Utiliser une transaction d'overlay imbriquée dédiée à la variante. Les scripts AA et x4 existants
sont des prototypes `CDMB1`, pas des installateurs génériques :

```text
pipeline/scripts/Install-CreatureSprite-AA-Variant-Test.ps1
pipeline/scripts/Restore-CreatureSprite-AA-Variant-Test.ps1
pipeline/scripts/Install-CreatureSprite-X4-Variant-Test.ps1
pipeline/scripts/Restore-CreatureSprite-X4-Variant-Test.ps1
```

Pour une autre cible, dériver une paire `Install/Restore` dédiée et ses tests. Ne pas modifier les
scripts d'un essai antérieur pour changer leur cible.

Pour dériver la transaction :

1. copier les deux scripts spécialisés sous de nouveaux noms ;
2. remplacer les assertions figées de `job_id`, `animation.id`, `bam_prefix`, `run_dir`, méthode,
   échelle, version et layout de registre par les valeurs du nouveau contrat ;
3. remplacer le filtre de collisions `override` par le préfixe canonique du nouveau job ;
4. attribuer un schéma d'état propre à la variante et écrire son identité depuis le job validé ;
5. conserver sans affaiblissement les contrôles de chemin sous `GameRoot`, hashes, limites de
   cibles, publication atomique, mutex, parent unique et restauration exacte ;
6. ajouter un test dédié sous `pipeline/tests/` qui vérifie le contrat du job, l'isolation des
   chemins, les assertions d'installation et les gates de restauration ;
7. exécuter le préflight d'installation, l'installation, le préflight de restauration et la
   restauration sur une copie de test avant le premier essai ingame.

Le prototype x4 spécialisé accepte seulement un monolithe V3. Pour un nouveau layout `set`, dériver
la capture et la validation dynamique des shards depuis les installateurs xN standard ; ne pas
supprimer la restriction du prototype sans ajouter les gates d'index, SHA256 et CRC32.

Contrat minimal de l'overlay imbriqué :

1. accepter au maximum un état parent `installed-pending-qa` ou `validated-installed` sur le même
   `GameRoot` ;
2. ne jamais modifier le fichier d'état du parent ;
3. revalider job, build, runtime, `BaldurReal.exe` et hashes des fichiers à installer ;
4. capturer DLL, INI, registre X2, monolithe XN, index XN et tous les shards XN présents ;
5. enregistrer présence, absence, hash et backup de chaque cible ;
6. publier atomiquement `status=installing` avant la première mutation ;
7. retirer les layouts concurrents, puis installer un seul layout complet ;
8. imposer dans l'INI de test :

```ini
[Shaders]
EnableCreatureSpriteUpscaleTest = true
EnableCreatureSpriteX2Test = false
EnableCreatureSpriteLinearFiltering = false
```

9. vérifier les hashes installés, puis publier `status=installed-pending-qa` ;
10. en cas d'erreur après la première mutation, restaurer les cibles depuis l'état publié.

L'état de la variante doit contenir `parent_active_tests`, `backup_root`, la liste exhaustive
`targets`, les hashes source/installés et la méthode complète. L'installation doit disposer d'un
mode `VerifyOnly` sans mutation et partager le verrou global du `GameRoot` avec les installateurs
standard.

## Basculer NEAREST et LINEAR

`LINEAR` est un filtre d'affichage du backing déjà produit. Ne reconstruire ni PNG, ni BAM, ni
registre, ni palette.

Dans `<GameRoot>\InfinityEngine-Enhancer.ini`, sous `[Shaders]`, conserver une occurrence :

```ini
; NEAREST, baseline et QA
EnableCreatureSpriteLinearFiltering = false
```

Pour la comparaison locale, remplacer uniquement `false` par `true`. Ne pas ajouter une seconde
occurrence. Fermer le jeu avant modification, relancer via
`<GameRoot>\InfinityLoader.exe`, puis exiger dans `<GameRoot>\InfinityEngine-Enhancer.log` :

```text
filter=NEAREST
```

ou :

```text
filter=LINEAR
```

Avant `qa-log` ou `record-qa`, remettre `false`, relancer et produire une nouvelle session de log
`NEAREST`. Une observation `LINEAR` n'est jamais `validated-installed`.

## Restaurer et réactiver une variante

Pour une installation standard :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py restore --job $job
```

Pour une installation catalogue, la même commande route vers son restaurateur LIFO : elle remet
exactement la génération catalogue précédente ou l'état importé. Appliquer le préflight et les
gates de [`SPRITE_UPSCALE_CATALOG_RUNBOOK.md`](SPRITE_UPSCALE_CATALOG_RUNBOOK.md) ; ne pas utiliser
un restaurateur d'overlay `CDMB1` sur l'état propriétaire du catalogue.

Pour un overlay imbriqué, exécuter d'abord le préflight du restaurateur dédié :

```powershell
powershell -ExecutionPolicy Bypass -File <Restore-Variant-Test.ps1> `
  -JobFile $job `
  -VerifyOnly
```

Exiger que les fichiers courants et chaque backup correspondent à l'état. Restaurer ensuite :

```powershell
powershell -ExecutionPolicy Bypass -File <Restore-Variant-Test.ps1> `
  -JobFile $job
```

Pour une transaction `installing` ou `restoring` interrompue, inspecter `active-test.json` et
`backup_root`, puis utiliser `-RecoverInterrupted`. Ne pas utiliser la récupération sur un état
sain.

Après restauration, exiger :

```text
chaque cible antérieure présente avec son hash antérieur, ou absente comme avant
aucun shard ou registre ajouté par la variante
état parent inchangé
build, runtime, manifeste et backups de la variante conservés
```

Pour réactiver une variante conservée, relancer son préflight d'installation puis son installateur.
Ne pas recopier manuellement ses fichiers dans le jeu.

## QA comparative ingame

Appliquer la politique de [`sprite/README.md`](../../README.md#politique-de-qa-ingame-pilotée). Aucun script ne
lance le jeu automatiquement ; un contrôle interactif par l'agent exige une autorisation utilisateur
explicite pour la session courante.

Tester une seule cible visuelle à la fois. Pour un corps sans armure, retirer tous les équipements
visuels avant la capture.

Conserver entre variantes :

```text
même sauvegarde et même personnage
même zone
même position et orientation
même zoom et cadrage
même animation ou frame observable
même configuration de couleurs
```

Vérifier au minimum :

- attente, marche, attaque, réception d'un coup et mort ;
- directions disponibles ;
- changement de couleurs de personnage ;
- contours, diagonales, petits détails et stabilité temporelle ;
- absence de halo, pixels transparents incorrects, couleurs figées et calques décalés ;
- log sans erreur de registre, shard, palette, recette, composition, texture ou fallback inattendu.

Nommer ou consigner chaque capture avec variante, filtre, date UTC, zone, pose et personnage.
Comparer uniquement le sprite cible. Une capture démontre un résultat visuel ; elle ne remplace ni
les hashes, ni les gates, ni le log runtime.

Pour une QA formelle d'un job xN standard `NEAREST` seulement :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py qa-log --job $job
python pipeline/scripts/run_creature_sprite_x2.py record-qa `
  --job $job `
  --result pass `
  --note '<couverture et preuve>'
```

Exiger la couverture complète du job, les fichiers installés conformes à l'état et les compositions
attendues dans une même session de log. Sinon conserver `installed-pending-qa`.
Le prototype AA V4 ne fournit pas `qa-log` ou `record-qa` et reste expérimental.

## Compte rendu d'essai

Créer un document dédié au sprite et y enregistrer uniquement :

```text
périmètre et condition d'équipement
variantes testées et liens vers leurs jobs/manifests/états
preuves visuelles et log utilisées
défauts observés
classement comparatif
décision : abandonner, conserver disponible, étendre ou soumettre à QA
```

Ne pas dupliquer les hashes, nombres de frames, nombres de ressources ou états ingame courants :
lier les manifestes et `active-test.json` canoniques. Ne jamais intégrer une variante
`pending-qa`, `LINEAR`, issue d'une capture ou d'un dossier temporaire au manifeste de release.

Référence d'essai : [`CDMB1_UPSCALE_VARIANT_TRIALS.md`](CDMB1_UPSCALE_VARIANT_TRIALS.md).
