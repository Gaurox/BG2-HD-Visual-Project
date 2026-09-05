# Inventaire normalisé des sprites BG2EE — contrat agent

Utiliser cet index comme source de vérité pour toute identité de sprite, famille BAM, variante
Character, équipement et diagnostic automatisable du pipeline x2/x4. Ne pas remplacer ces relations
par une déduction depuis un nom de PNJ ou un dossier historique.

Le scanner sépare les ressources présentes de leur compatibilité avec le pipeline actuel. Il lit
les ressources stock depuis `chitin.key` et les BIF ; il ne lit dans `override` que les noms de
fichiers nécessaires au signalement des collisions et n'écrit jamais dans le jeu.

## Régénération

Régénérer depuis la racine du dépôt après changement du jeu, du schéma, des règles de résolution,
des suffixes acceptés, du remappage palette ou des limites runtime :

```powershell
python pipeline/scripts/build_sprite_inventory.py
```

Après la génération, demander « tests ciblés / tous / aucun ». Le test ciblé, seulement après ce
choix, est `python -m unittest pipeline.tests.test_sprite_inventory`. Voir
[`../../docs/TEST_SELECTION.md`](../../docs/TEST_SELECTION.md).

La provenance exacte de l'installation analysée, ses hashes, les limites appliquées, l'usage des
animations par les CRE stock, les totaux et les projections déterministes de registry-set x2/x4 sont dans
[`manifest.json`](manifest.json).

Lire `manifest.json` pour toute décision courante. Un document peut conserver un instantané daté de
benchmark ou de capacité s'il le marque `non canonique` et fournit sa commande de reproduction ; il
ne doit jamais utiliser cet instantané comme gate opérationnel.

## Tables

- [`sprite_animations.csv`](sprite_animations.csv) : une ligne par ID de l'union `ANIMATE.IDS` et
  des INI numériques. Elle conserve le symbole, la classe moteur, toutes les clés qui pilotent les
  variantes Character ou Monster et le profil runtime actuellement disponible. Les colonnes
  fréquentes sont exposées directement ; `ini_sections_json` conserve sans perte toutes les autres
  clés propres aux classes moteur (sons, quadrants, armes superposées, etc.).
- [`sprite_families.csv`](sprite_families.csv) : une ligne par couple animation/calque/préfixe BAM.
  Pour Character, les corps sont déclinés par code d'armure et les équipements par type et code
  d'animation ITM. Cette table porte la décision `pipeline_ready` et ses motifs détaillés.
- [`sprite_resources.csv`](sprite_resources.csv) : une ligne par BAM relié à une famille. Le BAM est
  réellement décodé pour mesurer cadres, cycles, dimensions, centres, pixels, coût exact estimé du
  registre V2 x2, plus grosse frame native et doublons d'indices RGBA effectivement utilisés dans
  une même frame. Le champ de
  coût conserve volontairement sa sémantique x2 ; le manifeste fournit la formule de projection x4
  sans créer les pixels et décrit les limites du registre-set.
- [`sprite_items.csv`](sprite_items.csv) : une ligne par ITM stock. Elle relie type `ITEMCAT.IDS`,
  code d'animation, calque visuel, préfixes Character candidats, familles résolues et familles
  actuellement traitables.
- [`manifest.json`](manifest.json), bloc `stock_cre_usage` : usage des animations par toutes les
  ressources CRE du KEY/BIF stock. Le scanner lit le type `0x03F1`, vérifie la signature/version CRE
  et extrait l'ID `u16-le` à l'offset `0x28`. Les listes `fully_pipeline_ready_*`,
  `runtime_supported_without_bam_*`, `runtime_supported_blocked_*` et `runtime_unsupported_*` sont
  générées depuis les mêmes tables et règles que les CSV. Les champs `nonzero_*` excluent la valeur
  spéciale `0x0000` sans masquer le nombre de CRE qui l'utilisent. Les blocs `with_bam_*` et
  `without_bam_*` empêchent de confondre un ID référencé par un CRE avec une animation possédant des
  assets stock.

Les relations utilisent `animation_id`, `family_id`, `bam_resref` et `item_resref`. Les listes dans
une cellule sont séparées par `;` ; le fichier CSV lui-même reste séparé par des virgules et encodé
en UTF-8 avec BOM.

## Lecture des diagnostics

Interpréter `runtime_supported=yes` comme la capacité du hook moteur à reconnaître cette classe
d'animation (`Character 0x5000/0x6000` ou `MonsterIcewind 0xE000`).
`pipeline_ready=yes` exige en plus : ressources présentes et décodables, suffixes acceptés,
provenance d'indice palette vérifiable, aucune collision `override`, et respect des limites de 128 ressources,
4 096 frames par BAM et 128 Mio par registre x2. Le format xN applique un plafond centralisé
équivalent de 512 Mio en x4 afin de conserver la même capacité logique malgré le coût pixel ×4.
Plusieurs shards V3 peuvent appartenir à un même
`CreatureSprites-XN.set` ; ses plafonds, son ordre de priorité et sa politique fail-closed sont dans
`manifest.json`. Une projection n'est valide que si sa plus grosse frame upscalée tient aussi dans
le cache lazy borné à 128 Mio.

Les principales valeurs de `blocker` sont :

- `runtime-profile-unsupported` : assets inventoriés, mais classe moteur non branchée ;
- `no-bam-resources` : INI connu mais ressources absentes de cette installation ;
- `missing-required-suffixes` ou `unexpected-character-suffixes` : contrat Character incomplet ;
- `resource-limit`, `per-resource-frame-limit` ou `registry-size-limit` : limite de registre ;
- `*-override-collision` : une ressource de même identité existe dans `override`.

`duplicate_used_rgba_frames` et ses exemples restent des diagnostics : le runner propage l'indice
source selon les décisions xBR puis vérifie que cette provenance restitue exactement le RGBA xBR.
Des indices distincts de même RGBA ne sont donc pas fusionnés et ne constituent plus un blocker.

Ne jamais traduire `pipeline_ready=yes` en validation ingame. Cette valeur couvre uniquement les
prérequis automatisables connus. Exiger ensuite un job, une installation réversible et la QA décrite
dans [`../README.md`](../README.md). Pour un ajout au catalogue cumulatif, appliquer exclusivement
[`../FAMILY_APPEND.md`](../FAMILY_APPEND.md).

## Requêtes de décision

```powershell
$a = Import-Csv sprite/index/sprite_animations.csv
$f = Import-Csv sprite/index/sprite_families.csv
$r = Import-Csv sprite/index/sprite_resources.csv
$i = Import-Csv sprite/index/sprite_items.csv

$a | Where-Object animation_id -eq '0xFFFF'
$f | Where-Object animation_id -eq '0xFFFF'
$f | ForEach-Object { $_.blocker -split ';' } | Where-Object { $_ } |
  Group-Object | Sort-Object Count -Descending
$r | Where-Object blocker -ne ''
$i | Where-Object item_resref -eq 'ITEMREF'

$m = Get-Content sprite/index/manifest.json -Raw | ConvertFrom-Json
$m.stock_cre_usage | Select-Object cre_resource_count, animation_id_count, `
  with_bam_animation_id_count, without_bam_animation_id_count, `
  without_bam_nonzero_animation_id_count, `
  fully_pipeline_ready_animation_id_count, fully_pipeline_ready_cre_resource_count, `
  fully_pipeline_ready_cre_coverage_percent, runtime_supported_without_bam_animation_id_count, `
  runtime_supported_blocked_animation_id_count, runtime_unsupported_animation_id_count, `
  runtime_unsupported_nonzero_animation_id_count
```
