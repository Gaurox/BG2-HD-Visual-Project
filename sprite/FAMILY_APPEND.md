# Append catalogue par famille de sprites

## But

Ajouter une famille x2 déjà upscalée au catalogue cumulatif sans modifier le job catalogue actif,
sans lancer le jeu et sans modifier le manifeste de release.

## Sources de vérité

| Objet | Source |
|---|---|
| Identité et gate famille | `sprite/index/sprite_families.csv` |
| Classement | `sprite/index/family-groups.csv` via `pipeline/scripts/sprite_layout.py` |
| Cycle de vie | `sprite/index/processing.csv` |
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

### Bootstrap d'un Character sans job existant

Réutiliser seulement la recette xBR2x d'un membre Character compatible. L'identité, les familles,
les chemins et les représentants ITM viennent de l'inventaire cible. La QA cible est obligatoire et
n'est jamais héritée d'un autre Character.

```powershell
python pipeline/scripts/generate_character_complete_x2_jobs.py `
  --animation-id 0xFFFF `
  --character-root sprite/families/playable-characters/ffff-<type> `
  --bootstrap-template-job <job-membre-character-xbr2x> `
  --job-stem <type> `
  --aggregate-job sprite/families/playable-characters/ffff-<type>/family-runs/complete-xn-xbr2x/jobs/<type>-complete-xn-xbr2x.json `
  --qa-area <AREA> `
  --qa-creature <CRE_RESREF>
```

Sans `--run`, la commande planifie et n'écrit rien. Après revue, répéter avec `--run`. Ne jamais
utiliser `--force` pour remplacer un job ou agrégat sans décision explicite.

Extraire puis matérialiser les sources avant `prepare` :

```powershell
python pipeline/scripts/extract_sprite_sources.py --animation-id 0xFFFF
python pipeline/scripts/extract_sprite_sources.py --animation-id 0xFFFF --run
python pipeline/scripts/materialize_sprite_sources.py --job <agregat-character>
python pipeline/scripts/materialize_sprite_sources.py --job <agregat-character> --run
```

L'extraction remplit le store central. La matérialisation crée uniquement les manifestes et liens
physiques attendus par le runner ; elle ne produit aucun pixel ni run.

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
python pipeline/scripts/extract_sprite_sources.py --family-id $familyId
python pipeline/scripts/extract_sprite_sources.py --family-id $familyId --run
python pipeline/scripts/materialize_sprite_sources.py --job $member
python pipeline/scripts/materialize_sprite_sources.py --job $member --run
python pipeline/scripts/run_creature_sprite_x2.py plan --job $member
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job $member
python pipeline/scripts/run_creature_sprite_x2.py verify --job $member
```

Exiger `prepared-verified`, xBR/x2, `antialias=false`, `xbr_blend=false`,
`partial_alpha_pixels=0`, `new_colors=0`, `override_collisions=0`, runtime testé.

Batch Character : lancer `prepare-data --resume --defer-full-verify` sur chaque agrégat. Il produit
`data-prepared-unverified`, diffère la gate exhaustive et le runtime au catalogue.

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

Ajouter plusieurs animations dans un seul descriptor : répéter `--member-job <agregat>`. Le
générateur refuse tout membre ou `animation_id` dupliqué et valide le catalogue complet avant écriture.

Retirer `--dry-run` après revue. Le générateur doit conserver `job_id` et `paths.run_dir`, ajouter
exactement un membre/ID et ne jamais écraser le job de base.

## Phase 3 — construire et installer

Fermer `InfinityLoader.exe`, `Baldur.exe` et `BaldurReal.exe`.

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume `
  --defer-full-verify --job $appendCatalog
python pipeline/scripts/run_creature_sprite_x2.py verify --full-verify `
  --keep-going --job $appendCatalog

# Après correction des scopes en erreur uniquement :
python pipeline/scripts/run_creature_sprite_x2.py verify --resume `
  --keep-going --job $appendCatalog

python pipeline/scripts/run_creature_sprite_x2.py install --job $appendCatalog `
  --creature-sprite-filter Nearest
python pipeline/scripts/run_creature_sprite_x2.py status --job $appendCatalog
```

`install` exige la preuve scellée et ne déclenche aucun fallback exhaustif. `--full-verify` reste
disponible pour imposer un nouveau scan complet. PowerShell direct sans preuve reste exhaustif.

Exiger `installed-pending-qa`, `active_identity_matches_job=true`,
`active_generation_is_sealed=true` et `installed_files_match=true`.
Pour un contrôle Catmull–Rom explicitement demandé, remplacer `Nearest` par `CatmullRom` ; l'état
actif, l'INI et la restauration sont alors liés à cette valeur.

QA ingame : manuelle, sur toutes les animations du catalogue. Enregistrer ensuite `record-qa`.
Pour Character, le gate de composition porte sur les préfixes représentatifs scellés dans
`qa.required_bam_prefixes`, pas sur toutes les combinaisons d'équipement. Les contrôles de santé,
palette, payload, animation, hashes et absence de quarantaine restent exhaustifs.
Ne modifier le manifeste de release qu'après accord utilisateur explicite et uniquement pour un
élément `validated-installed`.

Après installation catalogue, projeter ses preuves scellées dans l'autorité :

```powershell
python pipeline/scripts/sync_sprite_processing.py --reconcile-active
python pipeline/scripts/sync_sprite_processing.py --reconcile-active --run
```

Ce mode met à jour production/sélection/QA/installation des membres actifs. Il ne modifie ni QA
au-delà du statut actif, ni release. Sans `--reconcile-active`, les lignes existantes restent intactes.

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
