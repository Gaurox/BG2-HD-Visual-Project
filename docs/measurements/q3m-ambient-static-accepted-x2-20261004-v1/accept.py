"""Record explicit user acceptance of the exact installed composed family."""
import csv, datetime, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):
    return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
qa_path=ROOT/'sprite/index/qa-decisions/ambient_static/2026-10-04-accepted-full-ambient-static-horse-eye-v3-q3m-v7-x2-catmullrom-v1.json'
assert not qa_path.exists()
full=ROOT/'docs/measurements/q3m-ambient-static-full-x2-20261004-v1'
horse=ROOT/'docs/measurements/q3m-horse-eye-ingame-x2-20261004-v1'
generation=load(horse/'current-generation.json'); baseline=load(horse/'baseline.json')
installed=load(horse/'installation-verification.json')
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/baseline['catalog_relative'])==generation['catalog']['sha256']
catalog=registry.read_sealed_catalog_index(game/baseline['catalog_relative'],generation['catalog']['sha256'])
selection=load(full/'selection.json'); ids=sorted(w['animation_id'] for w in selection['witnesses'])
routes=[r for r in catalog['directory'] if r['animation_id'] in ids]
assert len(routes)==26 and len(ids)==13
selected_shards=sorted({r['shard_index'] for r in routes})
assert len(selected_shards)==26
resources=[catalog['shards'][i] for i in selected_shards]
assert sum(s['frame_count'] for s in resources)==1144
for s in resources:
    assert file_sha(game/s['registry']).upper()==s['sha256']
previous=ROOT/'sprite/index/qa-decisions/ambient_static/2026-10-04-accepted-12-models-except-horse-q3m-v7-x2-catmullrom-v1.json'
subset=load(previous)
assert {s['sha256'] for s in subset['resources']} <= {s['sha256'] for s in resources}
runtime_preserved=[p for p in baseline['preserved'] if p['relative_path'] in
    ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl')]
assert len(runtime_preserved)==5
for p in runtime_preserved:
    assert file_sha(game/p['relative_path']).lower()==p['sha256'].lower()
assert generation['dll']['sha256']==baseline['dll_sha256'] and installed['native_combined_test']['passed']
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',
    recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope=dict(kind='installed-native-family-complete-with-resource-replacement',engine_family='ambient_static',
        animation_ids=ids,excluded_animation_ids=[],
        variant_id='q3m-v7-k6-four-partners-eight-levels-x2-catmullrom-no-SDF-horse-eye-v3',
        scale=2,resources=26,frames=1144),
    visual_qa=dict(result='pass',authority='user',
        user_statement='parfait famille validée  ! mets le suivi a jour et commite.\nensuite propose une autre famille complete',
        individual_scenario_details='not specified by user'),
    runtime_contract=dict(runtime=generation['runtime'],dll=generation['dll'],ini_sha256=baseline['ini_sha256'],
        catalogue_sha256=generation['catalog']['sha256'],owner=13,world_filter='CatmullRom',SDF=False,
        native_geometry=True,installed_runtime_files=runtime_preserved),
    provenance=dict(base_selected_generation=identity(full/'current-generation.json'),
        base_production=identity(full/'production.json'),base_installation_snapshot=identity(full/'installation-verification.json'),
        required_horse_replacement_generation=identity(horse/'current-generation.json'),
        current_installation_snapshot=identity(horse/'installation-verification.json'),
        prior_subset_acceptance=identity(previous)),
    resources=resources,resource_bindings=routes,release=False)
write_json(qa_path,qa)
qa_ref=qa_path.relative_to(ROOT).as_posix()
path=ROOT/'sprite/index/q3m-work-tracking.json'; tracking=load(path)
tracking['queue_totals']['current_recipe_ingame_accepted_families']=4
tracking['queue_totals']['current_recipe_ingame_accepted_animation_ids']=22
visual=dict(state='accepted-full-with-horse-eye-v3-replacement',animation_ids=ids,resources=26,frames=1144,
    qa_reference=qa_ref,catalogue_sha256=generation['catalog']['sha256'])
family=next(f for f in tracking['families'] if f['engine_section']=='ambient_static')
full_entry=next(f for f in tracking['current_recipe_complete_productions'] if f['family']=='ambient_static')
for entry in (family['current_full_production'],full_entry):
    entry.update(state='family-complete-installed-with-horse-eye-v3-ingame-accepted',qa_ingame=True,
        qa_reference=qa_ref,visual_QA=visual,acceptance_requires_current_resource_replacements=True)
family['current_visual_QA']=visual
for entry in (family,full_entry):
    replacement=entry['current_resource_replacements'][0]
    assert replacement['reference']==generation['production']['path'].replace(
        'q3m-horse-eye-directions-20261004-v3/candidate.json','q3m-horse-eye-ingame-x2-20261004-v1/current-generation.json')
    replacement.update(state='horse-front-eye-v3-installed-ingame-accepted',qa_ingame=True,qa_reference=qa_ref)
write_json(path,tracking)
csv_path=ROOT/'sprite/index/q3m-work-items.csv'; rows=csv_path.read_text(encoding='utf-8-sig').splitlines(keepends=True)
for i,row in enumerate(rows):
    if row.startswith('0xB100,HORSE,ambient_static,'):
        rows[i]=row.replace('v7-x2-front-eye-v3-installed-ingame-QA-pending','v7-x2-front-eye-v3-installed-ingame-accepted')
csv_path.write_text(''.join(rows),encoding='utf-8')
write_json(HERE/'acceptance-summary.json',dict(qa=identity(qa_path),accepted_ids=13,accepted_resources=26,
    accepted_frames=1144,installed_catalog_sha256=generation['catalog']['sha256'],
    prior_24_accepted_leaves_preserved=True,installed_runtime_files_verified=5,release=False))
print(json.dumps(dict(accepted_family='ambient_static',ids=13,resources=26,frames=1144,
    recipe_accepted_families=4,recipe_accepted_ids=22,qa_reference=qa_ref)))
