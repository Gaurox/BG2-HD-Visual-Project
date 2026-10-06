"""Reconcile installed correction; retained329 IDs accepted, new G2 requires user QA."""
import copy,csv,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;IDS=['0x7312','0x7313']
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');receipt=load(HERE/'ingame-installation/active-test.json')
baseline=load(HERE/'baseline.json');proof=load(HERE/'catalog-proof.json');verification=load(HERE/'verification.json');game=get_path('bg2ee_game_root',required=True)
prefix=HERE.relative_to(ROOT).as_posix();assert not(HERE/'installed-verification.json').exists()
assert receipt['status']=='installed-G2-native-palettes-pending-ingame-qa' and verification['passed']
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
assert file_sha(game/baseline['catalog_relative'])==gen['catalog']['sha256']
for r in baseline['preserved']:assert file_sha(game/r['relative_path']).upper()==r['sha256'].upper()
for s in baseline['candidate_shards']:assert file_sha(game/s['registry']).upper()==s['sha256'].upper()
for d in gen['inherited_QA_decisions']:assert file_sha(ROOT/d['path'])==d['sha256']
assert len(receipt['created_leaves'])==14 and proof['retained_ids']==329
write_json(HERE/'installed-verification.json',dict(passed=True,catalog_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],
    created_leaves=14,changed_existing_files=baseline['changed_files'],preserved_files_sha256_verified=len(baseline['preserved']),retained_ids=329,
    retained_routes=proof['retained_routes'],MFIE_accepted_bytes_preserved=True,runtime_changed=False,remaining_user_QA_ids=IDS,ingame_QA=False,release=False))
# First attempt completed inference and two special encodings, then rejected an invalid mode name.
# The resume reused every target and produced all756 ordinary encodings; record without rewriting old evidence.
events=[]
for line in (HERE/'production.log').read_text(encoding='utf-8-sig').splitlines():
    if line.startswith('{'):
        try:events.append(json.loads(line))
        except json.JSONDecodeError:pass
initial=next(e for e in events if e.get('stage')=='plan');targets=[e for e in events if e.get('stage')=='neural-targets'];guides=[e for e in events if e.get('stage')=='guides']
assert initial['hits']==1084 and initial['missing']==758 and targets[-1]['done']==targets[-1]['total']==4536
encoding=load(HERE/'encoding.json');assert encoding['stats']['new_encoded_work']==756 and encoding['stats']['unique_target_cache_hits']==4536
write_json(HERE/'production-resume-evidence.json',dict(initial_encoded_hits=1084,initial_missing_encoded=758,new_guides=guides[-1]['done'],new_neural_targets=4536,
    new_special_encoded_work=2,first_attempt_stop='unknown palette encoder mode cuda-guarded-v1 after targets complete',
    corrected_mode='gpu-grouped-guarded-v1',resume_encoded_hits=1086,resume_new_encoded_work=756,resume_target_hits=4536,
    acquired_encoded_cache_SHA_verified=encoding['acquired_hits_verified'],inference_repeated_on_resume=False))
generation_ref=prefix+'/current-generation.json';snapshot=prefix+'/installation-verification.json';receiptref=prefix+'/ingame-installation/active-test.json'
production_ref=prefix+'/production-generation.json';state='family-complete-installed-G2-corrected-native-verified-two-user-retests-pending'
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path);others=copy.deepcopy([f for f in tracking['families'] if f['engine_section']!='monster'])
family=next(f for f in tracking['families'] if f['engine_section']=='monster');family['state']=state
visual=family['current_visual_QA'];assert len(visual['animation_ids'])==77
visual.update(state='accepted-retained-75-current-contracts-two-new-G2-assets-await-user-QA',animation_ids=gen['retained_Monster_user_QA_ids'],
    excluded_animation_ids=IDS,known_technical_defect_animation_ids=[],corrected_assets_pending_user_QA_ids=IDS,
    retained_by_catalog_proof=prefix+'/catalog-proof.json',technical_audit_reference=prefix+'/verification.json')
assert len(visual['animation_ids'])==75 and '0x7314' in visual['animation_ids'] and visual['MFIE_ingame_QA']
family['current_installation'].update(state='installed-G2-corrected-two-user-retests-pending',reference=snapshot,receipt=receiptref,
    generation_reference=generation_ref,dll_sha256=gen['dll']['sha256'],catalogue_sha256=gen['catalog']['sha256'],qa_ingame=False,
    correction_animation_ids=IDS,retained_catalog_proof=prefix+'/catalog-proof.json',known_technical_defect_animation_ids=[],
    corrected_assets_pending_user_QA_ids=IDS,retained_Monster_user_QA_ids=gen['retained_Monster_user_QA_ids'])
for item in (family['current_full_production'],next(r for r in tracking['current_recipe_complete_productions'] if r['family']=='monster')):
    item.update(reference=production_ref,parent_full_production_reference=gen['production_generation']['path'],state=state,qa_ingame=False,
        native_palette_correction=dict(animation_ids=IDS,resources=27,frames=11774,changed_bindings=14,changed_bank_frames=5292,
            selection=gen['correction_selection']['path'],production=prefix+'/production.json',verification=prefix+'/verification.json'),
        installation_reference=receiptref,installation_snapshot=snapshot,installation_generation_reference=generation_ref,
        remaining_user_QA_animation_ids=IDS,technical_defect_animation_ids=[],technical_verification_reference=prefix+'/verification.json',
        prepared_correction_reference=prefix+'/current-generation.json',runtime_stability_verification=prefix+'/verification.json')
family['current_technical_correction'].update(state='corrected-installed-native-verified-awaiting-user-QA',verification_reference=prefix+'/verification.json',
    generation_reference=generation_ref,production_reference=prefix+'/production.json',inference_started=True,production_complete=True,
    installation=True,installation_reference=snapshot,new_assets_require_ingame_retest=True,open_native_palette_defects=0)
family['current_colour_witness']['installation_reference']=snapshot
tracking['engine_integration'].update(installed_candidate_reference=generation_ref,latest_installation_verification_reference=snapshot)
tracking['queue_totals'].update(current_recipe_ingame_accepted_families=13,current_recipe_ingame_accepted_animation_ids=176,
    current_recipe_partial_user_accepted_animation_ids=75,remaining_user_QA_animation_ids=2,known_technical_defect_animation_ids=0,
    corrected_pending_user_QA_animation_ids=2,remaining_complete_available_family_productions=0,
    partial_QA_counting_rule='75 Monster IDs retain exact accepted contracts including MFIE; changed G2 assets7312/7313 need new user QA; prior77 decisions immutable; total active accepted329 with CharacterV6, installed331')
assert others==[f for f in tracking['families'] if f['engine_section']!='monster'];write_json(path,tracking)
path=ROOT/'sprite/index/q3m-work-items.csv';raw=path.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in gen['animation_ids']:out.append(line);continue
    row['q3m_v7_installation_reference']=receiptref
    if row['animation_id'] in IDS:row.update(q3m_v7_full_production_reference=production_ref,queue_state='current-recipe-complete-installed-G2-native-palettes-corrected-user-QA-pending',
        colour_variant_state='v7-four-partners-eight-levels-no-SDF-x2-G1-palette1-G2-palette2-native-verified-retest-pending')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row);out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==gen['animation_ids'];path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
attributes=ROOT/'.gitattributes';text=attributes.read_text(encoding='utf-8');entry=prefix+'/** -text -whitespace'
if entry not in text:attributes.write_text(text+'\n'+entry+'\n',encoding='utf-8',newline='\n')
write_json(HERE/'summary.json',dict(production_complete=True,installed=True,native_verification_passed=True,corrected_ids=IDS,changed_G2_resources=14,
    corrected_G2_frames=5292,retained_ids=329,MFIE_user_QA_preserved=True,runtime_changed=False,open_native_palette_defects=0,
    selected_recipe_installed_ids=331,selected_recipe_current_user_accepted_ids=329,new_user_retests=IDS,release=False))
print(json.dumps(dict(installed=True,native_defects_corrected=2,user_retests=IDS,retained_accepted_ids=329,tracking_updated=True)),flush=True)
