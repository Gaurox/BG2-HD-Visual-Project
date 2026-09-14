# Ajouter un lot au catalogue sprites

But : produire un delta installable sans relire ni reconstruire les générations déjà acceptées.

## 1. Créer et préparer les nouveaux membres

Sélectionner le `family_id` exact dans `sprite/index/sprite_families.csv`.

Exiger pour chaque famille : `runtime_supported=yes`, `pipeline_ready=yes`, `blocker` vide,
`override_collision` vide et des ressources non vides.

Monster/MonsterIcewind/MonsterQuadrant/MultiNew :

```powershell
$familyId = '<family_id>'
$layout = python pipeline/scripts/generate_sprite_family_append.py layout `
  --family-id $familyId | ConvertFrom-Json
$member = [string]$layout.member_job

python pipeline/scripts/generate_sprite_family_append.py member `
  --job $member --template-job <job-xbr2x-compatible> `
  --family-id $familyId --qa-area <AREA> --qa-creature <CRE_RESREF>
python pipeline/scripts/extract_sprite_sources.py --family-id $familyId --run
python pipeline/scripts/materialize_sprite_sources.py --job $member --run
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job $member
```

Une famille MultiNew peut dépasser 128 ressources : le registre-set accepte jusqu'à 1024
ressources et conserve la limite de 128 par shard.

Character : produire l'agrégat complet avec `generate_character_complete_x2_jobs.py`, puis extraire,
matérialiser et lancer `prepare-data --resume`. Ne jamais hériter la QA d'un autre Character.

## 2. Créer le delta

Le générateur prend automatiquement le `current-generation.json` canonique et son job de
provenance scellé. Il ne consulte pas `active-test.json`.

```powershell
$append = "sprite/catalogs/creature-x2-nearest/jobs/append-$($layout.folder_slug)-v1.json"
python pipeline/scripts/generate_sprite_family_append.py catalog-append `
  --job $append --member-job $member `
  --name 'Catalogue progressif créatures x2 — ajout <lot>' `
  --require-prepared
```

Répéter `--member-job` pour grouper plusieurs nouvelles animations dans un même delta. Le
générateur refuse un ID déjà présent et épingle les hashes du parent. `--catalog-job` reste réservé
à une reprise explicite depuis un autre job ou pointeur de génération.

## 3. Installer et décider

Fermer le jeu et InfinityLoader, puis :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job $append
python pipeline/scripts/run_creature_sprite_x2.py install --job $append `
  --creature-sprite-filter Nearest
python pipeline/scripts/run_creature_sprite_x2.py status --job $append
```

Tester uniquement les nouveaux membres et leurs préfixes représentatifs. Après acceptation
explicite, créer une décision immuable sous `sprite/index/qa-decisions/<groupe>/` qui épingle la
génération, le manifeste, la portée et le verdict. Une décision acceptée n'est jamais rejouée sauf
changement des octets/du runtime ou réouverture explicite.

Ajouter ensuite seulement le candidat à
`releases/BG2-HD-Upscale/manifests/sprite-release-candidates.json`. La compilation globale et
`verify --full-verify` restent réservés à la finalisation du patch.

Test facultatif après modification du générateur :

```powershell
python -m unittest pipeline.tests.test_generate_sprite_family_append
```
