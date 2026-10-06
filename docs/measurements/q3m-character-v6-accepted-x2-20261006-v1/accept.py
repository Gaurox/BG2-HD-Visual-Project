"""Record explicit Character V6 acceptance; inspect catalog routes, change tracking only."""
import csv
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha, write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry

load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
QA = ROOT/'sprite/index/qa-decisions/character/2026-10-06-accepted-full-character-q3m-v6-x2-nearest-v1.json'
REF = QA.relative_to(ROOT).as_posix()
assert not QA.exists(), 'immutable QA decision already exists'
items_path = ROOT/'sprite/index/q3m-work-items.csv'
with items_path.open(encoding='utf-8-sig', newline='') as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
char = [r for r in rows if r['engine_family']=='character']
ids = sorted(r['animation_id'] for r in char)
assert len(ids)==78 and all(int(r['source_bam_count'])>0 for r in char)
pointer = ROOT/'docs/measurements/playable-q3m-x2-ingame-20261002-v1/current-generation.json'
generation = load(pointer)
old_path = ROOT/generation['generation_dir']/'CreatureSprites-XN.catalog'
old = registry.read_sealed_catalog_index(old_path, generation['catalog_sha256'])
game = get_path('bg2ee_game_root', required=True)
active_path = game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
active_sha = file_sha(active_path)
active = registry.read_sealed_catalog_index(active_path, active_sha)
routes = lambda catalog: {(r['animation_id'], r['resref']): catalog['shards'][r['shard_index']]['sha256']
                         for r in catalog['directory'] if r['animation_id'] in ids}
before, installed = routes(old), routes(active)
assert before==installed and len(before)==50190
assert len(set(before.values()))==4510
ini = game/'InfinityEngine-Enhancer.ini'
filter_name = re.search(r'^\s*CreatureSpriteFilter\s*=\s*(\w+)\s*$', ini.read_text(encoding='utf-8-sig'), re.M).group(1)
assert filter_name=='Nearest'
identity = lambda p: dict(path=p.relative_to(ROOT).as_posix(), sha256=file_sha(p), bytes=p.stat().st_size)
qa = dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1', status='accepted', qa_state='passed',
    recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope=dict(kind='installed-native-family-complete-available', engine_family='character',
               animation_ids=ids, excluded_animation_ids=[], variant_id='q3m-v6-K6-one-partner-eight-levels-x2-nearest-no-SDF',
               scale=2, resources=4510, native_frames=1564054, logical_resource_bindings=50190,
               body_armor_equipment=True, paperdolls_UI='separate; no new acceptance'),
    visual_qa=dict(result='pass', authority='user',
        user_statement='OK on valide char v6. Les gains v7 sont presque invisibles. Reste donc uniquement Icewind ? Combien de créatures à traiter ?',
        preceding_ingame_feedback="Je pensais que char était terminé, ils dme semblent tous OK ingame. Qu'est-ce qu'il leur manque exactement",
        individual_scenario_details='not specified by user; full-family acceptance explicit',
        comparative_frame='docs/measurements/q3m-character-frame-v6-v7-x2-20261006-v1/comparison.json'),
    runtime_contract=dict(registry_version=6, class_profile_id=1, decode_rule_id=1, owner=1,
        colour='K6-one-ramp-successor-eight-levels/live-native-palettes', world_filter=filter_name, SDF=False,
        installed_catalogue_sha256=active_sha, character_production_catalogue_sha256=generation['catalog_sha256'].lower(),
        runtime_DLL_sha256=file_sha(game/'InfinityEngine-Enhancer.dll'), ini_sha256=file_sha(ini)),
    provenance=dict(production=identity(pointer),
        installation_reference='docs/measurements/playable-q3m-x2-ingame-20261002-v1/ingame-installation/active-test.json',
        acquired_installed_verification=identity(pointer.parent/'verification.json'),
        current_catalogue_check=dict(character_routes=50190, unique_leaf_identities=4510, matches_complete_V6_production=True,
                                    scope='sealed catalogue membership and leaf identities; no new full payload hash scan'),
        comparison=identity(ROOT/'docs/measurements/q3m-character-frame-v6-v7-x2-20261006-v1/comparison.json')),
    method_decision=dict(retain_complete_V6=True, full_V7_migration='not-requested; no longer outstanding',
                         V7_witness='historical candidate retained; no QA promotion', V10_SDF_stock='unchanged, uninstalled'),
    installation_changed=False, release=False)
write_json(QA, qa)
tracking_path = ROOT/'sprite/index/q3m-work-tracking.json'
tracking = load(tracking_path)
totals_before = dict(tracking['queue_totals'])
family = next(f for f in tracking['families'] if f['engine_section']=='character')
assert 'current_full_production' not in family
production = dict(family='character', reference=pointer.relative_to(ROOT).as_posix(), animation_ids=ids,
    registry_version=6, scale=2, resources=4510, physical_frames=1564054,
    state='selected-recipe-complete-produced-installed-ingame-accepted', qa_ingame=True, qa_reference=REF,
    installation_reference=qa['provenance']['installation_reference'], release=False,
    recipe_exception='retain-V6-one-partner-eight-levels; full-V7-migration-not-requested')
family['current_full_production'] = production
family['current_visual_QA'] = dict(state='accepted-full-family-V6-x2-Nearest-no-SDF',
                                  animation_ids=ids, qa_reference=REF, qa_ingame=True)
tracking['method']['family_recipe_exceptions'] = dict(character=dict(method='Q3m-K6-one-partner-eight-levels',
    registry_version=6, scale=2, decision='retain-complete-V6-user-accepted', qa_reference=REF))
tracking['selected_recipe_complete_productions'] = [production]
tracking['selected_recipe_complete_productions_role'] = 'accepted exceptions only; combine with current_recipe_complete_productions, deduplicate IDs/families'
tracking['remaining_full_production_families'] = ['monster_icewind']
tracking['remaining_full_production_counting'] = 'sources present; Character V6 accepted exception; production only, independent of installation and QA'
assert tracking['queue_totals']==totals_before, 'improved-recipe counts must exclude V6 exception'
write_json(tracking_path, tracking)
for row in char:
    assert not row['q3m_v7_full_production_reference'] and not row['q3m_v7_installation_reference']
    row['queue_state'] = 'selected-recipe-complete-installed-ingame-accepted'
    row['colour_variant_state'] = 'v6-one-partner-eight-levels-x2-installed-ingame-accepted-retained-user-choice'
with items_path.open('w', encoding='utf-8', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
followup = ROOT/'sprite/SUIVI_Q3M.md'
lines = followup.read_text(encoding='utf-8').splitlines()
for i,line in enumerate(lines):
    if line.startswith('| `character` |'):
        lines[i] = '| `character` | 78/78 | 78 | **Famille complète V6 K6 x2 sans SDF installée et validée ingame, conservée par choix utilisateur** ; un partenaire/huit niveaux, filtre Nearest. Corps/armures/armes/casques/boucliers ; migration V7 non demandée. |'
    if line.startswith('- Production améliorée complète :'):
        lines.insert(i+1, '- Character : **78 IDs V6 complets installés/acceptés le 2026-10-06**, exception explicite à la recette améliorée. Total des recettes retenues : **291 IDs/14 familles produites**, 214 IDs/13 familles installés et acceptés ; Monster reste production seule. **Seul lot complet à produire : Icewind**, 40 modèles de base/44 IDs disponibles ; 88 IDs sans source exclus. [Décision Character V6](../docs/measurements/q3m-character-v6-accepted-x2-20261006-v1/README.md).')
        break
followup.write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(json.dumps(dict(accepted='character-V6', ids=78, qa=REF, remaining_family='monster_icewind',
                      improved_recipe_counts_unchanged=True, installed_files_changed=False)))
