# Publier et installer un lot de sprites

Choisir le mode dans [`PROCESSING.md`](PROCESSING.md). xBR ajoute les nouvelles animations au
catalogue canonique ; ReboutCX remplace des composants de cette base dans un catalogue dérivé.

## Mode xBR — ajout canonique

Créer/préparer le membre ciblé. Pour Monster/MonsterIcewind/MonsterQuadrant/MultiNew :

```powershell
$familyId = '<family_id>'
$layout = python pipeline/scripts/generate_sprite_family_append.py layout `
  --family-id $familyId | ConvertFrom-Json
$member = [string]$layout.member_job

python pipeline/scripts/generate_sprite_family_append.py member `
  --job $member --template-job <job-xbr-compatible> `
  --family-id $familyId --qa-area <AREA> --qa-creature <CRE_RESREF>
python pipeline/scripts/extract_sprite_sources.py --family-id $familyId --run
python pipeline/scripts/materialize_sprite_sources.py --job $member --run
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job $member
```

Pour Character, créer l'agrégat avec `generate_character_complete_x2_jobs.py`, puis extraire,
matérialiser et exécuter `prepare-data --resume` sur son job. Une famille MultiNew peut utiliser
plusieurs shards ; limite 128 ressources par shard.

Créer le delta depuis le pointeur xBR canonique :

```powershell
$append = "sprite/catalogs/creature-x2-nearest/jobs/append-$($layout.folder_slug)-v1.json"
python pipeline/scripts/generate_sprite_family_append.py catalog-append `
  --job $append --member-job $member `
  --name 'Catalogue sprites x2 — ajout <lot>' --require-prepared
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job $append
```

Répéter `--member-job` pour un lot. Un delta ajoute des IDs ; il ne remplace pas un ID parent.

## Mode ReboutCX — remplacement dérivé

Le composant xBR cible doit déjà appartenir au parent canonique. Après le `run` et le `verify` de
chaque job ReboutCX, créer un nouveau job sous `catalogs/creature-x2-reboutcx/jobs/` avec :

- parent xBR épinglé par génération/hashes ;
- remplacements cumulatifs à conserver ;
- pour chaque remplacement : `animation_id`, owner, index/digests/shards/resrefs xBR exacts et
  manifeste ReboutCX scellé ;
- sélection par `(animation_id, component_index)` ; un composant partagé reste xBR pour les autres
  animations.

```powershell
python pipeline/scripts/reboutcx_catalog.py build <job-catalogue-reboutcx>
python pipeline/scripts/reboutcx_catalog.py verify <job-catalogue-reboutcx>
```

Ne jamais modifier le pointeur xBR. `build` refuse une génération existante ; utiliser `verify`
pour la reprendre.

## Installation et QA

Fermer BG2EE et InfinityLoader.

xBR :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py install --job <job-catalogue-xbr> `
  --creature-sprite-filter Nearest
python pipeline/scripts/run_creature_sprite_x2.py status --job <job-catalogue-xbr>
```

ReboutCX :

```powershell
& pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile <job-catalogue-reboutcx> -EnableDerivedInstall -VerifyOnly
& pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile <job-catalogue-reboutcx> -EnableDerivedInstall
& pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile <job-catalogue-reboutcx> -EnableDerivedInstall -VerifyOnly
```

Restauration du catalogue précédent, jeu et InfinityLoader fermés :

```powershell
& pipeline/scripts/Restore-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile <job-catalogue-actif>
```

Tester des préfixes/compositions représentatifs. Après verdict utilisateur, créer une décision
immuable sous `sprite/index/qa-decisions/<groupe>/` limitée aux octets réellement testés. Ajouter un
candidat release seulement sur demande ; aucun rebuild global, TP2, staging ou package ici.
