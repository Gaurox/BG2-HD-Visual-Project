"""Record explicit user acceptance without rewriting production/install proofs."""
import datetime,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
qa_path=ROOT/'sprite/index/qa-decisions/ambient/2026-10-04-accepted-full-available-ambient-q3m-v7-x2-catmullrom-v1.json'
assert not qa_path.exists()
full=ROOT/'docs/measurements/q3m-ambient-full-x2-20261004-v1'
generation=load(full/'current-generation.json');baseline=load(full/'baseline.json');installed=load(full/'installation-verification.json')
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/baseline['catalog_relative'])==generation['catalog']['sha256']
catalog=registry.read_sealed_catalog_index(game/baseline['catalog_relative'],generation['catalog']['sha256'])
selection=load(full/'selection.json');ids=sorted(w['animation_id'] for w in selection['witnesses'])
routes=[r for r in catalog['directory'] if r['animation_id'] in ids]
resources=[catalog['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
assert len(ids)==18 and len(routes)==39 and len(resources)==34 and sum(s['frame_count'] for s in resources)==2580
for s in resources:assert file_sha(game/s['registry']).upper()==s['sha256']
runtime=[p for p in baseline['preserved'] if p['relative_path'] in
    ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl')]
assert len(runtime)==5
for p in runtime:assert file_sha(game/p['relative_path']).lower()==p['sha256'].lower()
assert installed['native_combined_test']['passed'] and not generation['SDF']
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',
    recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope=dict(kind='installed-native-family-complete-available',engine_family='ambient',animation_ids=ids,
        excluded_animation_ids=selection['source_absent_animation_ids'],source_absent=load(ROOT/'docs/measurements/q3m-ambient-selection-x2-20261004-v1/analysis.json')['absent'],
        variant_id='q3m-v7-k6-four-partners-eight-levels-x2-catmullrom-no-SDF',scale=2,models=16,resources=34,frames=2580,logical_resource_bindings=39),
    visual_qa=dict(result='pass',authority='user',
        user_statement='tout validé. met a jour le suivi et committe. puis identifie une nouvelle famille à traiter',
        individual_scenario_details='not specified by user'),
    runtime_contract=dict(runtime=generation['runtime'],dll=generation['dll'],ini_sha256=baseline['ini_sha256'],
        catalogue_sha256=generation['catalog']['sha256'],owner=12,world_filter='CatmullRom',SDF=False,native_geometry=True,
        installed_runtime_files=runtime),
    provenance=dict(selected_generation=identity(full/'current-generation.json'),production=identity(full/'production.json'),
        installation_snapshot=identity(full/'installation-verification.json'),verification=identity(full/'verification.json')),
    resources=resources,resource_bindings=routes,release=False)
write_json(qa_path,qa);ref=qa_path.relative_to(ROOT).as_posix()
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path)
totals=tracking['queue_totals'];assert totals['current_recipe_ingame_accepted_families']==5 and totals['current_recipe_ingame_accepted_animation_ids']==40
totals.update(current_recipe_ingame_accepted_families=6,current_recipe_ingame_accepted_animation_ids=58)
visual=dict(state='accepted-full-available',animation_ids=ids,models=16,resources=34,frames=2580,qa_reference=ref,
    catalogue_sha256=generation['catalog']['sha256'])
family=next(f for f in tracking['families'] if f['engine_section']=='ambient')
full_entry=next(f for f in tracking['current_recipe_complete_productions'] if f['family']=='ambient')
for entry in (family['current_full_production'],full_entry):
    entry.update(state='family-complete-available-produced-installed-ingame-accepted',qa_ingame=True,qa_reference=ref,visual_QA=visual)
family['current_visual_QA']=visual
tracking['colour_variants']['state']=tracking['colour_variants']['state'].replace('-Ambient-V7-no-SDF-installed-','-Ambient-V7-no-SDF-accepted-')
write_json(path,tracking)
path=ROOT/'sprite/index/q3m-work-items.csv';rows=path.read_text(encoding='utf-8-sig').splitlines(keepends=True);count=0
for i,row in enumerate(rows):
    if row.split(',',1)[0] in ids:
        assert ',ambient,' in row
        rows[i]=row.replace('current-recipe-complete-installed-ingame-pending','current-recipe-complete-installed-ingame-accepted').replace(
            'v7-full-x2-no-SDF-installed-ingame-pending','v7-full-x2-no-SDF-installed-ingame-accepted');count+=1
assert count==18;path.write_text(''.join(rows),encoding='utf-8')
write_json(HERE/'acceptance-summary.json',dict(qa=identity(qa_path),accepted_ids=18,accepted_resources=34,accepted_frames=2580,
    installed_catalog_sha256=generation['catalog']['sha256'],installed_runtime_files_verified=5,release=False))
print(json.dumps(dict(accepted_family='ambient',ids=18,resources=34,frames=2580,accepted_families=6,accepted_recipe_ids=58)))
