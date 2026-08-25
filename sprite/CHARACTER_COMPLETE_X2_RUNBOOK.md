# Runbook LLM — Character complet x2

Ce document est la procédure d'exécution canonique pour produire puis installer toutes les familles
visuelles x2 d'un même animation ID Character : corps, armures, casques, armes, armes de main gauche
et boucliers. Les contrats techniques restent dans
[`SPRITE_UPSCALE_PIPELINE.md`](SPRITE_UPSCALE_PIPELINE.md) et
[`SPRITE_UPSCALE_XN_FOUNDATION.md`](SPRITE_UPSCALE_XN_FOUNDATION.md). Ne pas refaire leur analyse
pour chaque personnage lorsque les gates ci-dessous passent.

## Validation de référence

Référence ingame du 25 août 2026 :

- job : `sprite/jobs/human-female-fighter-complete-xn-xbr2x.json` ;
- animation : `0x6110 FIGHTER_FEMALE_HUMAN` ;
- résultat utilisateur : tous les équipements disponibles testés sont corrects, aucun bug observé,
  fonctionnement global du composite Character x2 validé ;
- pipeline opérationnel validé pour réutilisation : oui ;
- statut du pack : `installed-pending-qa`, vérification exhaustive encore ouverte ;
- éligibilité release : aucune, car le pack est x2 et n'est pas `validated-installed`.

Cette validation autorise la réutilisation du processus pour d'autres animation IDs Character. Elle
n'autorise pas `record-qa --result pass` pour cette référence et ne valide aucun sprite x4.

## Entrées obligatoires

Définir depuis `sprite/index/sprite_animations.csv` et le contexte QA :

```powershell
$animationId = '0xFFFF'
$idsSymbol = 'SYMBOL_ANIMATE_IDS'
$jobStem = 'character-name'
$qaArea = 'ARxxxx'
$qaCreature = 'CRE_OR_PLAYER'
$seedJob = "sprite/jobs/$jobStem-body1-xbr2x.json"
$aggregateJob = "sprite/jobs/$jobStem-complete-xn-xbr2x.json"
```

Exécuter toutes les commandes depuis la racine du dépôt. Ne pas modifier à la main les préfixes,
les suffixes BAM, les listes d'ITM, le facteur d'échelle ou le sharding.

## Procédure déterministe

### 1. Créer le membre modèle du bon animation ID

Si aucun job x2 compatible de cet animation ID n'existe, le créer ainsi :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py new-character-job `
  --job $seedJob `
  --template-job sprite/jobs/human-female-fighter-chfb1-xbr2x.json `
  --scale 2 `
  --ids-symbol $idsSymbol `
  --animation-id $animationId `
  --armor-code 1 `
  --name "$idsSymbol — Character complet x2" `
  --qa-area $qaArea `
  --qa-creature $qaCreature
if ($LASTEXITCODE -ne 0) { throw 'Échec de création du membre modèle' }
```

Si un job compatible existe déjà, affecter son chemin à `$seedJob` et ne pas le recréer.

### 2. Générer l'inventaire de jobs complet

Pour une nouvelle cible uniquement :

```powershell
python pipeline/scripts/generate_character_complete_x2_jobs.py `
  --animation-id $animationId `
  --template-job $seedJob `
  --job-stem $jobStem `
  --aggregate-job $aggregateJob
if ($LASTEXITCODE -ne 0) { throw 'Échec de génération du Character complet' }
```

Pour reprendre une cible déjà générée, réutiliser `$aggregateJob` sans `--force`. Le générateur :

- résout exclusivement les familles depuis `sprite/index/sprite_families.csv` ;
- réutilise les jobs x2 compatibles par préfixe ;
- produit un job par famille visuelle avec BAM ;
- choisit un ITM stock représentatif par famille d'équipement ;
- consigne les familles sans BAM dans `inventory.excluded_families` ;
- bloque toute famille non vide portant encore un blocker ;
- publie l'agrégat seulement après validation de tous les descripteurs.

Gate automatique :

```powershell
$aggregate = Get-Content -LiteralPath $aggregateJob -Raw | ConvertFrom-Json
if (@($aggregate.members).Count -ne [int]$aggregate.inventory.included_family_count) {
  throw 'Nombre de membres différent de l’inventaire inclus'
}
$badExclusions = @($aggregate.inventory.excluded_families | Where-Object reason -ne 'no-bam-resources')
if ($badExclusions.Count -ne 0) { throw 'Exclusion Character non autorisée' }
$planRaw = @(python pipeline/scripts/run_creature_sprite_x2.py plan --job $aggregateJob)
if ($LASTEXITCODE -ne 0) { throw 'Préflight du Character complet refusé' }
$plan = (($planRaw -join "`n") | ConvertFrom-Json)
foreach ($gate in @(
  'runtime_profile_supported',
  'baldur_real_compatible',
  'game_launch_is_never_automatic',
  'release_manifest_is_out_of_scope'
)) {
  if ($plan.$gate -ne $true) { throw "Gate refusé : $gate" }
}
if ($plan.registry_layout_policy -ne 'auto-shard-explicit-xn') {
  throw 'Politique de sharding inattendue'
}
```

Exiger dans le plan `runtime_profile_supported=true`, `baldur_real_compatible=true`,
`game_launch_is_never_automatic=true`, `release_manifest_is_out_of_scope=true` et
`registry_layout_policy=auto-shard-explicit-xn`.

### 3. Construire tous les membres, puis l'agrégat

La boucle suivante est la séquence normale. `--resume` réutilise les extractions et registres x2
valides ; il ne relance pas xBR sans nécessité. Le builder choisit seul monolithe ou registry-set.

```powershell
$aggregate = Get-Content -LiteralPath $aggregateJob -Raw | ConvertFrom-Json
foreach ($memberJob in @($aggregate.members)) {
  python pipeline/scripts/run_creature_sprite_x2.py extract --job $memberJob --resume
  if ($LASTEXITCODE -ne 0) { throw "Extraction refusée : $memberJob" }
  python pipeline/scripts/run_creature_sprite_x2.py build --job $memberJob --resume
  if ($LASTEXITCODE -ne 0) { throw "Build refusé : $memberJob" }
}
python pipeline/scripts/run_creature_sprite_x2.py prepare --job $aggregateJob --resume
if ($LASTEXITCODE -ne 0) { throw 'Préparation de l’agrégat refusée' }
```

Exiger `status=prepared-verified`, `override_collisions=0`, un runtime `built-tested` et zéro
ressource dupliquée. Ne pas construire le runtime séparément pour chaque membre.

### 4. Installer pour QA

Fermer `BaldurReal`, `Baldur` et `InfinityLoader`, puis restaurer tout autre test sprite actif.

```powershell
python pipeline/scripts/run_creature_sprite_x2.py install --job $aggregateJob
if ($LASTEXITCODE -ne 0) { throw 'Installation QA refusée' }
$statusRaw = @(python pipeline/scripts/run_creature_sprite_x2.py status --job $aggregateJob)
if ($LASTEXITCODE -ne 0) { throw 'Lecture du statut QA refusée' }
$status = (($statusRaw -join "`n") | ConvertFrom-Json)
if ($status.status -ne 'installed-pending-qa') { throw 'Statut QA installé inattendu' }
```

Exiger `status=installed-pending-qa`. L'installateur sauvegarde et restaure transactionnellement les
DLL, INI et registres ; il accepte plusieurs sections INI du même nom, mais refuse une même clé
dupliquée.

### 5. QA et décision

L'agent ne lance jamais le jeu. Demander à l'utilisateur de lancer `InfinityLoader.exe`, puis de
tester :

- chaque variante corporelle/armure listée par les membres `body` ;
- un ITM représentatif de chaque famille dans `qa.items` ;
- arme, main gauche/bouclier et casque simultanément ;
- taille, pivots, alignement, directions, actions, palettes, changements d'équipement et stabilité.

Après fermeture du jeu :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py qa-log --job $aggregateJob --write-report
```

Conserver `installed-pending-qa` pour une validation temporaire ou partielle. Exécuter
`record-qa --result pass` seulement après accord utilisateur explicite et `technical_pass=true` pour
tous les préfixes. Cette décision reste distincte du manifeste de release.

### 6. Restaurer

```powershell
python pipeline/scripts/run_creature_sprite_x2.py restore --job $aggregateJob
```

## Arrêts obligatoires

Arrêter sans improviser si le générateur ou le runner signale : identité incohérente, famille non
vide bloquée, collision `override`, resref trop volumineux pour un shard, manifeste incompatible,
hash du jeu différent, test sprite concurrent, processus du jeu ouvert, test runtime en échec ou
preuve technique incomplète. Corriger la source canonique ou le pipeline ; ne jamais contourner le
gate dans un job.
