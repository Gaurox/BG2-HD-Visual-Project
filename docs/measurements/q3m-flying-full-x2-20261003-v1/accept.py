"""Record explicit user acceptance of the exact installed flying family once."""
import csv,hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
from run_creature_sprite_x2 import read_sealed_catalog_index

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def identity(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path),bytes=path.stat().st_size)
qa_path=ROOT/'sprite/index/qa-decisions/flying/2026-10-03-accepted-full-flying-q3m-v7-k6-x2-box-v1.json'
assert not qa_path.exists(),'decision already exists; do not overwrite'
generation=load(HERE/'current-generation.json');receipt_path=HERE/'ingame-installation/active-test.json'
receipt=load(receipt_path);game=get_path('bg2ee_game_root',required=True)
assert receipt['status']=='installed-pending-ingame-qa'
for relative,expected in ((receipt['catalog_relative'],generation['catalog']['sha256']),
                          ('InfinityEngine-Enhancer.dll',generation['dll']['sha256']),
                          ('InfinityEngine-Enhancer.ini',receipt['ini_sha256'])):
    assert file_sha(game/relative)==expected.lower(),'active installed identity differs'
assert file_sha(ROOT/generation['production']['path'])==generation['production']['sha256']
assert file_sha(ROOT/generation['runtime']['path'])==generation['runtime']['sha256']
catalog=read_sealed_catalog_index(game/receipt['catalog_relative'],generation['catalog']['sha256'])
ids=generation['animation_ids'];leaves=[]
for shard in receipt['new_shards']:
    assert file_sha(game/shard['registry']).upper()==shard['sha256']
    routes=[r for r in catalog['directory'] if r['shard_index']==shard['index']]
    assert routes and {r['animation_id'] for r in routes}<=set(ids)
    leaves.append(dict(resref=routes[0]['resref'],animation_ids=sorted(r['animation_id'] for r in routes),
        registry=shard['registry'],sha256=shard['sha256'].lower(),frames=shard['frame_count'],bytes=shard['registry_bytes']))
leaves.sort(key=lambda r:r['resref']);assert len(leaves)==4 and sum(r['frames'] for r in leaves)==243
scope_digest=hashlib.sha256(json.dumps(leaves,sort_keys=True,separators=(',',':')).encode()).hexdigest()
decision=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',
    recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    scope=dict(kind='installed-complete-native-family',engine_family='flying',animation_ids=ids,
               variant_id='q3m-v7-k6-four-partners-eight-levels-x2-box',scale=2,resources=4,frames=243,
               resource_bindings=5,ordered_resource_sha256=scope_digest,resources_order='resref ascending'),
    visual_qa=dict(result='pass',authority='user',
        user_statement='famille validée. commite. identifie une autre famille',
        scenario='user acceptance of the complete installed flying family after installation and CLUA handoff',
        individual_scenario_details='not specified by user',test_commands_provided=['EAGLE','SEAGUL','VULTURE','BIRD']),
    runtime_contract=dict(runtime=generation['runtime'],dll=generation['dll'],ini_sha256=receipt['ini_sha256'],
        catalogue_sha256=generation['catalog']['sha256'],owner=15,native_palette_kind=0,class_profile_id=8,
        decode_rule_id=3,palette='live-native',world_filter='Box',native_geometry=True,
        shared_alias=dict(resref='ABIRG1',animation_ids=['0xD300','0xD400'])),
    provenance=dict(selected_generation=identity(HERE/'current-generation.json'),production=generation['production'],
        installed_receipt=identity(receipt_path),installation_snapshot=identity(HERE/'installation-verification.json'),
        comparison_acceptance=identity(HERE/'visual-acceptance.json')),
    resources=leaves,release_state='not-promoted')
write_json(qa_path,decision)
reference=qa_path.relative_to(ROOT).as_posix()
tracking_path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(tracking_path)
family=next(f for f in tracking['families'] if f['engine_section']=='flying')
for full in (family['current_full_production'],next(f for f in tracking['current_recipe_complete_productions'] if f['family']=='flying')):
    full.update(state='family-complete-produced-installed-ingame-accepted',qa_ingame=True,qa_reference=reference)
family['current_colour_witness'].update(state='ingame-accepted-via-complete-family',qa_reference=reference)
tracking['queue_totals']['current_recipe_ingame_accepted_families']=1
tracking['queue_totals']['current_recipe_ingame_accepted_animation_ids']=5
tracking['colour_variants']['state']='V7-x2-flying-accepted-Ogre-installed-other-families-pilot'
write_json(tracking_path,tracking)
items_path=ROOT/'sprite/index/q3m-work-items.csv'
with items_path.open(encoding='utf-8-sig',newline='') as stream:
    reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
for row in rows:
    if row['engine_family']=='flying':row.update(queue_state='current-recipe-complete-ingame-accepted',colour_variant_state='v7-family-complete-ingame-accepted')
with items_path.open('w',encoding='utf-8',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
print(json.dumps(dict(qa_reference=reference,accepted_ids=ids,resources=4,frames=243)))
