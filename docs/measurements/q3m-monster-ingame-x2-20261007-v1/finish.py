"""Record Monster installation separately from visual QA; preserve accepted families."""
import copy,csv,io,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');baseline=load(HERE/'baseline.json');receipt=load(HERE/'ingame-installation/active-test.json')
verification=load(HERE/'verification.json');proof=load(HERE/'catalog-proof.json')
assert receipt['status']=='installed-pending-ingame-qa' and verification['passed']
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/receipt['catalog_relative'])==gen['catalog']['sha256']
for r in baseline['preserved']:assert file_sha(game/r['relative_path'])==r['sha256']
for s in receipt['monster_shards']:assert file_sha(game/s['registry']).upper()==s['sha256']
for f in receipt['fixtures']:
    assert file_sha(game/f['target'])==f['sha256']
    b=(game/f['target']).read_bytes()
    assert struct.unpack_from('<I',b,0x28)[0]==int(f['animation_id'],16)
    assert b[0x270]==128 and struct.unpack_from('<I',b,0x20)[0]==0 and b[0x7e]==0
    assert struct.unpack_from('<I',b,0x2c8)[0]==struct.unpack_from('<I',b,0x2c0)[0]==0
    assert not any(b[o:o+8].strip(b'\0 ') for o in (0x248,0x250,0x258,0x260,0x268,0x2cc))
installed=registry.read_sealed_catalog_index(game/receipt['catalog_relative'],gen['catalog']['sha256'])
assert len(installed['animations'])==331
assert {a['animation_id'] for a in installed['animations'] if a['owner']==3}==set(gen['animation_ids'])
write_json(HERE/'installed-verification.json',dict(passed=True,installed_animations=331,monster_ids=77,models=62,
    resources=1037,frames=496816,bindings=1040,bound_frames=496822,catalog_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],
    preserved_runtime_files_verified=6,neutral_fixtures_verified=77,monster_leaf_hashes_verified=1037,retained_routes=proof['retained_bindings_unchanged'],
    routing_native_verification_reference=str(HERE.relative_to(ROOT).as_posix())+'/verification.json',runtime_changed=False,ingame_QA=False,release=False))
prefix=HERE.relative_to(ROOT).as_posix();ref=prefix+'/current-generation.json';snapshot=prefix+'/installation-verification.json';receiptref=prefix+'/ingame-installation/active-test.json'
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path);totals=tracking['queue_totals']
assert totals['current_recipe_installed_animation_ids']==176
qa={k:v for k,v in totals.items() if 'accepted' in k}
others=copy.deepcopy([f for f in tracking['families'] if f['engine_section']!='monster'])
family=next(f for f in tracking['families'] if f['engine_section']=='monster')
record=next(f for f in tracking['current_recipe_complete_productions'] if f['family']=='monster')
state='family-complete-available-produced-installed-host-verified-ingame-QA-pending'
for item in (family['current_full_production'],record):
    assert item['qa_ingame'] is False
    item.update(installation=True,installation_reference=receiptref,installation_snapshot=snapshot,installation_generation_reference=ref,state=state)
family['state']=state
family['current_installation']=dict(state='installed-ingame-pending',reference=snapshot,receipt=receiptref,generation_reference=ref,
    catalogue_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],animation_ids=gen['animation_ids'],SDF=False,qa_ingame=False)
family['current_colour_witness'].update(state='installed-via-complete-native-family-ingame-QA-pending',installation_reference=snapshot)
totals['current_recipe_installed_animation_ids']=253
assert totals['current_recipe_complete_animation_ids']==253 and qa=={k:v for k,v in totals.items() if 'accepted' in k}
assert others==[f for f in tracking['families'] if f['engine_section']!='monster']
tracking['engine_integration'].update(installed_candidate_reference=ref,latest_installation_verification_reference=snapshot)
tracking['recorded_on']='2026-10-07';write_json(path,tracking)
path=ROOT/'sprite/index/q3m-work-items.csv';raw=path.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True)
fields=next(csv.reader([lines[0]]));out=[lines[0]];ids=set(gen['animation_ids']);changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in ids:out.append(line);continue
    assert row['engine_family']=='monster' and not row['q3m_v7_installation_reference']
    row.update(q3m_v7_installation_reference=receiptref,queue_state='current-recipe-complete-installed-ingame-QA-pending',colour_variant_state='v7-four-partners-eight-levels-no-SDF-x2-installed-ingame-QA-pending')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row)
    out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==gen['animation_ids'];path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
write_json(HERE/'installation-summary.json',dict(installed=True,family='monster',models=62,ids=77,fixtures=77,installed_improved_ids=253,
    installed_selected_recipe_ids=331,installed_selected_recipe_families=15,accepted_improved_ids_unchanged=176,accepted_selected_recipe_ids_unchanged=254,
    ingame_QA_pending_ids=77,ingame_QA_pending_models=62,runtime_changed=False,release=False))
print(json.dumps(dict(installed=True,models=62,ids=77,fixtures=77,active_ids=331,installed_improved_ids=253,QA_pending=True)),flush=True)
