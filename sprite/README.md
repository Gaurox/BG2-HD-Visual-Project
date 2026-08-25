# Sprites de créature et calques Character — point d'entrée agent

Utiliser ce document pour toute analyse, évolution de pipeline ou production x2/x4 portant sur un
sprite de créature, un corps Character ou un calque d'équipement Character. Ne pas utiliser les
dossiers d'extraction historiques comme source d'identité.

## Ordre de lecture obligatoire

1. Lire [`index/README.md`](index/README.md), puis vérifier
   [`index/manifest.json`](index/manifest.json).
2. Identifier l'animation dans [`index/sprite_animations.csv`](index/sprite_animations.csv).
3. Sélectionner le calque et le préfixe dans
   [`index/sprite_families.csv`](index/sprite_families.csv).
4. Auditer les BAM liés dans [`index/sprite_resources.csv`](index/sprite_resources.csv).
5. Pour un équipement, résoudre l'ITM dans [`index/sprite_items.csv`](index/sprite_items.csv).
6. Lire [`SPRITE_UPSCALE_XN_FOUNDATION.md`](SPRITE_UPSCALE_XN_FOUNDATION.md) pour tout job portant
   un bloc `upscale` explicite ou toute cible x4.
7. Pour produire un personnage et tous ses équipements x2, exécuter sans branchement libre
   [`CHARACTER_COMPLETE_X2_RUNBOOK.md`](CHARACTER_COMPLETE_X2_RUNBOOK.md).
8. Appliquer [`SPRITE_UPSCALE_PIPELINE.md`](SPRITE_UPSCALE_PIPELINE.md) au workflow historique x2
   sans bloc `upscale`. Appliquer [`UPSCALE_XBR2X.md`](UPSCALE_XBR2X.md) aux seules frames x2.

## Sources de vérité

| Question | Source |
|---|---|
| ID, symbole `ANIMATE.IDS`, classe moteur, INI, resrefs et codes de hauteur | `sprite_animations.csv` |
| Corps, code d'armure, casque, bouclier, arme, préfixe et décision technique | `sprite_families.csv` |
| BAM, cadres, cycles, géométrie, palette, coût registre et collisions | `sprite_resources.csv` |
| Type ITM, code d'animation et familles Character candidates | `sprite_items.csv` |
| Installation analysée, hashes, limites et totaux | `manifest.json` |
| Exécution reproductible d'un Character complet x2 | `CHARACTER_COMPLETE_X2_RUNBOOK.md` |
| Création, build, installation réversible et QA | `SPRITE_UPSCALE_PIPELINE.md` |
| Échelle x2/x4 explicite, registres V3, registry-set, install/restore et gates | `SPRITE_UPSCALE_XN_FOUNDATION.md` |

Ne jamais déduire un préfixe BAM depuis le nom du personnage, son portrait, une apparence visuelle
ou le nom d'un dossier historique. Priorité d'identité : ID lu dans CRE/sauvegarde, symbole
`ANIMATE.IDS`, INI stock, ligne d'index correspondante.

## Gate de sélection

Pour un job de production, exiger dans `sprite_families.csv` :

```text
runtime_supported=yes
pipeline_ready=yes
blocker=<vide>
override_collision=<vide>
```

Pour une évolution de pipeline, sélectionner volontairement une famille `pipeline_ready=no`,
prendre chaque valeur de `blocker` comme critère d'acceptation, modifier le scanner si le contrat
change, puis régénérer l'index. Ne pas installer le test tant que les diagnostics automatisables
ne sont pas repassés à `pipeline_ready=yes`.

## Requêtes PowerShell minimales

```powershell
$animations = Import-Csv sprite/index/sprite_animations.csv
$families = Import-Csv sprite/index/sprite_families.csv
$resources = Import-Csv sprite/index/sprite_resources.csv
$items = Import-Csv sprite/index/sprite_items.csv

$animations | Where-Object animation_id -eq '0xFFFF'
$families | Where-Object animation_id -eq '0xFFFF'
$families | Where-Object blocker -match 'runtime-profile-unsupported'
$items | Where-Object item_resref -eq 'ITEMREF'
```

Régénérer après changement de `chitin.key`, du schéma, des règles de classification, des limites
du runtime ou du remappage palette :

```powershell
python pipeline/scripts/build_sprite_inventory.py
python -m unittest pipeline.tests.test_sprite_inventory pipeline.tests.test_creature_sprite_x2_pipeline
```

Le scanner lit les données stock KEY/BIF. Il ne lit dans `override` que les noms nécessaires au
signalement des collisions et n'écrit jamais dans le jeu.
