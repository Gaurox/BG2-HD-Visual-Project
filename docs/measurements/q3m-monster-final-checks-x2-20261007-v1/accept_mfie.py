"""Record user's final MFIE acceptance; keep technical G2 defects separate from QA."""
import copy,csv,datetime,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;PARENT=HERE.parent/'q3m-mfie-native-palettes-x2-20261007-v3'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
gen=load(PARENT/'current-generation.json');checks=load(HERE/'checks.json');baseline=load(PARENT/'baseline.json');game=get_path('bg2ee_game_root',required=True)
assert checks['MFIE_live_native_palette_accepted'] and checks['MFIE_live_HD_composition_observed'] and checks['native_bank_guard']['G2_defect_confirmed']
qa_path=ROOT/'sprite/index/qa-decisions/monsters/2026-10-07-accepted-MFIE-native-palettes-q3m-v7-x2-nearest-v3.json';assert not qa_path.exists()
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
cat=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',gen['catalog']['sha256'])
routes=sorted((r for r in cat['directory'] if r['animation_id'] in gen['animation_ids']),key=lambda r:(r['animation_id'],r['resref']))
shards=[cat['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
assert len(routes)==1040 and len(shards)==1037 and sum(s['frame_count'] for s in shards)==496816
for s in shards:assert file_sha(game/s['registry']).upper()==s['sha256']
for r in baseline['preserved']:assert file_sha(game/r['relative_path']).upper()==r['sha256'].upper()
mfie=[r for r in routes if r['animation_id']=='0x7314'];assert len(mfie)==14
def inventory(path,selected):
    with path.open('x',encoding='utf-8',newline='') as out:
        writer=csv.writer(out,lineterminator='\n');writer.writerow(['animation_id','resref','registry','sha256','frame_count','resource_ordinal'])
        for r in selected:
            s=cat['shards'][r['shard_index']];writer.writerow([r['animation_id'],r['resref'],s['registry'],s['sha256'],s['frame_count'],r['resource_ordinal']])
inventory(HERE/'MFIE-accepted-assets.csv',mfie);inventory(HERE/'monster-current-assets.csv',routes)
prior=[];accepted=set()
for item in gen['partial_visual_QA']['decisions']:
    p=ROOT/item['path'];assert file_sha(p)==item['sha256'];d=load(p);assert d['status']=='accepted'
    accepted.update(d['scope']['animation_ids']);prior.append(item['path'])
assert len(accepted)==76 and '0x7314' not in accepted
ref=qa_path.relative_to(ROOT).as_posix();prefix=HERE.relative_to(ROOT).as_posix();qa_refs=prior+[ref]
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',recorded_on='2026-10-07',
    recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),timezone='Europe/Paris',
    scope=dict(kind='installed-native-family-final-ID-retest',engine_family='monster',animation_ids=['0x7314'],models=1,colour_variants=1,
        resources=14,resource_bindings=14,frames=5888,scale=2,SDF=False),
    visual_qa=dict(result='pass',authority='user',user_statement='validé. fais les dernières vérif dont tu parles',
        context='MFIE retest after native G1 MFIEG31/253 and G2 MFIEG3B/252 correction v3',accepted_as_installed=True,
        detailed_actions_tested='not specified by user; native cycle/palette checks recorded independently'),
    runtime_contract=dict(runtime=gen['runtime'],dll=gen['dll'],catalogue_sha256=gen['catalog']['sha256'],owner=3,world_filter='Nearest',
        colour='Q3m K6 four partners/eight levels x2',SDF=False,metadata_wait=True,native_loop_clamp=True),
    asset_scope=dict(inventory=identity(HERE/'MFIE-accepted-assets.csv'),physical_leaf_count=14,binding_count=14,physical_leaf_hashes_verified=14),
    provenance=dict(installed_generation=identity(PARENT/'current-generation.json'),installed_verification=identity(PARENT/'installed-verification.json'),
        native_verification=identity(PARENT/'verification.json'),session_evidence=identity(HERE/'session-evidence.txt'),
        native_checks=identity(HERE/'checks.json')),release=False)
write_json(qa_path,qa);accepted.add('0x7314');assert accepted==set(gen['animation_ids'])
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path);others=copy.deepcopy([f for f in tracking['families'] if f['engine_section']!='monster'])
family=next(f for f in tracking['families'] if f['engine_section']=='monster');visual=family['current_visual_QA']
# Keep historical catalog/runtime fields and references; the new acceptance covers MFIE v3 alone.
visual.update(state='accepted-all-77-by-immutable-decisions-with-open-G2-technical-audit',animation_ids=gen['animation_ids'],qa_references=qa_refs,
    excluded_animation_ids=[],MFIE_ingame_QA=True,MFIE_qa_reference=ref,MFIE_accepted_catalogue_sha256=gen['catalog']['sha256'],
    technical_audit_reference=prefix+'/checks.json',known_technical_defect_animation_ids=['0x7312','0x7313'])
state='family-complete-installed-user-accepted-77-G2-technical-correction-prepared'
family['state']=state
family['current_installation'].update(state='installed-user-accepted-with-two-G2-technical-defects',qa_ingame=True,qa_references=qa_refs,
    known_technical_defect_animation_ids=['0x7312','0x7313'])
for item in (family['current_full_production'],next(r for r in tracking['current_recipe_complete_productions'] if r['family']=='monster')):
    item.update(state=state,qa_ingame=True,visual_QA_references=qa_refs,remaining_user_QA_animation_ids=[],
        technical_defect_animation_ids=['0x7312','0x7313'],technical_verification_reference=prefix+'/checks.json',
        prepared_correction_reference=prefix+'/correction-plan.json')
    item.pop('partial_visual_QA_references',None)
family['current_colour_witness']['state']='installed-user-accepted-with-complete-Monster-QA-union'
tracking['queue_totals'].update(current_recipe_ingame_accepted_families=14,current_recipe_ingame_accepted_animation_ids=253,
    current_recipe_partial_user_accepted_animation_ids=0,remaining_user_QA_animation_ids=0,known_technical_defect_animation_ids=2,
    partial_QA_counting_rule='Monster77 accepted by union of73 original +3 stability-v1 +MFIE1 native-palette-v3 decisions; included in253 full-family improved accepted IDs; G2 technical defects7312/7313 recorded separately')
tracking['recorded_on']='2026-10-07'
assert others==[f for f in tracking['families'] if f['engine_section']!='monster'];write_json(path,tracking)
path=ROOT/'sprite/index/q3m-work-items.csv';raw=path.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in ('0x7312','0x7313','0x7314'):out.append(line);continue
    if row['animation_id']=='0x7314':row.update(queue_state='current-recipe-complete-installed-visual-accepted-exact-tested-contract',
        colour_variant_state='v7-four-partners-eight-levels-no-SDF-x2-MFIE-native-G1-253-G2-252-user-accepted')
    else:row.update(queue_state='current-recipe-complete-installed-user-accepted-G2-palette-technical-defect',
        colour_variant_state='v7-four-partners-eight-levels-no-SDF-x2-user-QA-preserved-G2-wrong-bank-correction-prepared')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row);out.append(stream.getvalue())
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
# The immutable installation snapshot remains pending-at-install-time; only its active receipt advances.
receipt_path=PARENT/'ingame-installation/active-test.json';receipt=load(receipt_path)
assert receipt['status']=='installed-MFIE-native-palettes-pending-ingame-qa'
receipt.update(status='installed-MFIE-user-accepted',MFIE_ingame_QA=True,MFIE_qa_reference=ref,qa_references=qa_refs,
    user_accepted_ids=77,technical_defect_animation_ids=['0x7312','0x7313'],technical_check_reference=prefix+'/checks.json')
write_json(receipt_path,receipt)
write_json(HERE/'acceptance-summary.json',dict(MFIE_qa=identity(qa_path),qa_references=qa_refs,user_accepted_ids=77,
    accepted_improved_families=14,accepted_improved_ids=253,accepted_with_character_v6_families=15,accepted_with_character_v6_ids=331,
    physical_leaves_verified=1037,preserved_files_verified=len(baseline['preserved']),catalog_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],
    known_technical_defect_ids=['0x7312','0x7313'],technical_defects_do_not_rewrite_user_QA=True,correction_prepared=True,correction_inference_started=False,release=False))
attributes=ROOT/'.gitattributes';text=attributes.read_text(encoding='utf-8')
for entry in (prefix+'/** -text -whitespace',ref+' -text -whitespace'):
    if entry not in text:text+='\n'+entry+'\n'
attributes.write_text(text,encoding='utf-8',newline='\n')
print(json.dumps(dict(MFIE_user_accepted=True,Monster_accepted_ids=77,improved_accepted_ids=253,G2_technical_defects=2)),flush=True)
