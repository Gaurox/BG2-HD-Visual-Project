# Append catalogue par famille de sprites

## But

Ajouter une famille x2 déjà upscalée au catalogue cumulatif sans modifier le job catalogue actif,
sans lancer le jeu et sans modifier le manifeste de release.

## Sources de vérité

| Objet | Source |
|---|---|
| Identité et gate famille | `sprite/index/sprite_families.csv` |
| BAM, cycles, palette, collision | `sprite/index/sprite_resources.csv` |
| État catalogue actif | `sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/runs/catalog-xbr2x-x2/ingame-installation/active-test.json` |
| Contrat catalogue / install / rollback | `sprite/README.md`, jobs courants et manifests du catalogue |
| Générateur | `pipeline/scripts/generate_sprite_family_append.py` |

## Gates obligatoires

Sélectionner exactement un `family_id`. Exiger :

```text
runtime_supported=yes
pipeline_ready=yes
blocker=<vide>
override_collision=<vide>
resource_count>0
frame_count>0
```

Pour MonsterIcewind, exiger :

```text
runtime_profile=monster-icewind-bg2ee-2.7.3.0
animation_id=0xE000..0xEFFF
layer_kind=body
variant_kind=base-resref
```

Refuser toute autre valeur. Ne jamais déduire le préfixe depuis un nom de créature ou un dossier.

Pour Character, ne pas utiliser la phase `member` de ce générateur. Produire l'agrégat complet avec
`generate_character_complete_x2_jobs.py`, puis le passer directement à `catalog-append`. L'agrégat
doit porter une provenance `inventory`, un membre par famille incluse et un
`qa.required_bam_prefixes` non vide.

Pour convertir un catalogue historique sans ajouter de contenu, utiliser `catalog-qa-refresh` vers
un nouveau fichier `qa-refresh-<nom>-vN.json`. Cette commande conserve les membres, `job_id` et
`run_dir`, et rend explicites les préfixes représentatifs ; elle ne modifie jamais le job actif.

```powershell
python pipeline/scripts/generate_sprite_family_append.py catalog-qa-refresh `
  --job sprite/catalogs/creature-x2-nearest/jobs/qa-refresh-<nom>-v1.json `
  --catalog-job <catalog-job-actif> `
  --name 'Catalogue x2 — QA représentative explicite' `
  --dry-run
```

## Phase 1 — job membre

Résoudre le chemin V2 ; ne pas choisir un chemin plat sous `sprite/jobs/`.

```powershell
$familyId = '<family_id>'
$layout = python pipeline/scripts/generate_sprite_family_append.py layout `
  --family-id $familyId | ConvertFrom-Json
$member = [string]$layout.member_job

python pipeline/scripts/generate_sprite_family_append.py member `
  --job $member `
  --template-job sprite/families/monster-icewind/e4xx-goblins/e400-mgo1-goblin-axe/catalog-x2-nearest/jobs/goblin-mgo1-xbr2x-catalog.json `
  --family-id $familyId `
  --qa-area <AREA> `
  --qa-creature <CRE_RESREF> `
  --dry-run
```

Vérifier le JSON retourné. Retirer `--dry-run`, puis :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py plan --job $member
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job $member
python pipeline/scripts/run_creature_sprite_x2.py verify --job $member
```

Exiger `prepared-verified`, xBR/x2, `antialias=false`, `xbr_blend=false`,
`partial_alpha_pixels=0`, `new_colors=0`, `override_collisions=0`, runtime testé.

## Phase 2 — job catalogue d'append

Lire le job catalogue depuis l'état actif ; ne pas le choisir manuellement.

`$member` peut être soit un job MonsterIcewind unitaire préparé, soit un agrégat Character complet
préparé. Le résultat indique `added_member_kind=family` ou `character-complete`.

```powershell
$catalogRun = 'sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/runs/catalog-xbr2x-x2'
$state = Get-Content "$catalogRun/ingame-installation/active-test.json" -Raw | ConvertFrom-Json
if ($state.status -notin @('installed-pending-qa', 'validated-installed', 'qa-failed')) {
  throw "Etat catalogue non appendable : $($state.status)"
}
# `job_file` peut être scellé sous son chemin historique ; le générateur le résout via
# sprite/index/path-migrations.json avant lecture.
$baseCatalog = [string]$state.job_file
$appendCatalog = "sprite/catalogs/creature-x2-nearest/jobs/append-$($layout.folder_slug)-v1.json"

python pipeline/scripts/generate_sprite_family_append.py catalog-append `
  --job $appendCatalog `
  --catalog-job $baseCatalog `
  --member-job $member `
  --name 'Catalogue progressif créatures x2 NEAREST — ajout <famille>' `
  --require-prepared `
  --dry-run
```

Retirer `--dry-run` après revue. Le générateur doit conserver `job_id` et `paths.run_dir`, ajouter
exactement un membre/ID et ne jamais écraser le job de base.

## Phase 3 — construire et installer

Fermer `InfinityLoader.exe`, `Baldur.exe` et `BaldurReal.exe`.

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job $appendCatalog
python pipeline/scripts/run_creature_sprite_x2.py verify --job $appendCatalog

powershell -NoProfile -ExecutionPolicy Bypass -File `
  pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 `
  -JobFile $appendCatalog `
  -VerifyOnly

python pipeline/scripts/run_creature_sprite_x2.py install --job $appendCatalog
python pipeline/scripts/run_creature_sprite_x2.py status --job $appendCatalog
```

Exiger `installed-pending-qa`, `active_identity_matches_job=true`,
`active_generation_is_sealed=true` et `installed_files_match=true`.

QA ingame : manuelle, sur toutes les animations du catalogue. Enregistrer ensuite `record-qa`.
Pour Character, le gate de composition porte sur les préfixes représentatifs scellés dans
`qa.required_bam_prefixes`, pas sur toutes les combinaisons d'équipement. Les contrôles de santé,
palette, payload, animation, hashes et absence de quarantaine restent exhaustifs.
Ne modifier le manifeste de release qu'après accord utilisateur explicite et uniquement pour un
élément `validated-installed`.

## Extension

`catalog-append` est commun aux profils. Pour un nouveau profil ou calque, ajouter un adaptateur
de création de membre fondé sur les champs exacts de `sprite_families.csv` et ses tests ; ne pas
modifier la phase d'append.

## Test

Ne pas l'exécuter automatiquement. Demander « tests ciblés / tous / aucun » conformément à
[`../docs/TEST_SELECTION.md`](../docs/TEST_SELECTION.md). Si ciblés est choisi :

```powershell
python -m unittest pipeline.tests.test_generate_sprite_family_append
```
