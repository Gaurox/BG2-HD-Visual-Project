"""Final user confirmation: acquired family QA + last G2 assets + common runtime."""
import copy,csv,datetime,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
COMMON=HERE.parent/'q3m-all-sprite-playback-x2-20261007-v1'
G2=HERE.parent/'q3m-monster-g2-palettes-x2-20261007-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import write_json,file_sha
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
M_QA=ROOT/'sprite/index/qa-decisions/monsters/2026-10-07-accepted-full-monster-q3m-v7-x2-nearest-v4.json'
R_QA=ROOT/'sprite/index/qa-decisions/runtime/2026-10-07-accepted-common-sprite-playback-x2-v1.json'
assert not M_QA.exists() and not R_QA.exists() and not(HERE/'acceptance-summary.json').exists()
gen=load(COMMON/'current-generation.json');mgen=load(G2/'current-generation.json')
install=load(COMMON/'installation-verification.json');verify=load(COMMON/'runtime-verification.json')
assert install['status']=='installed-common-playback-corrected-pending-ingame-confirmation' and verify['passed']
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==gen['catalog_sha256']
cat=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',gen['catalog_sha256'])
ids=mgen['animation_ids'];assert len(ids)==77
routes=sorted((r for r in cat['directory'] if r['animation_id'] in ids),key=lambda r:(r['animation_id'],r['resref']))
shards=[cat['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
assert len(routes)==1040 and len(shards)==1037
inventory=HERE/'accepted-monster-asset-scope.csv'
with inventory.open('x',encoding='utf-8',newline='') as out:
    w=csv.writer(out,lineterminator='\n');w.writerow(['animation_id','resref','registry','sha256','resource_ordinal','frame_count'])
    for r in routes:
        s=cat['shards'][r['shard_index']];w.writerow([r['animation_id'],r['resref'],s['registry'],s['sha256'],r['resource_ordinal'],s['frame_count']])
now=datetime.datetime.now(datetime.timezone.utc).isoformat();mref=M_QA.relative_to(ROOT).as_posix();rref=R_QA.relative_to(ROOT).as_posix()
runtime_contract=dict(dll=gen['dll'],runtime=gen['runtime'],catalogue_sha256=gen['catalog_sha256'],
    world_scale=2,world_filter='Nearest',common_native_playback=True,sprite_bytes_unchanged_by_runtime_fix=True)
prior=copy.deepcopy(mgen['inherited_QA_decisions'])
for q in prior:assert file_sha(ROOT/q['path'])==q['sha256']
write_json(M_QA,dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',
    recorded_at_utc=now,recorded_on='2026-10-07',
    scope=dict(kind='installed-native-family-complete-available',engine_family='monster',animation_ids=ids,
        excluded_animation_ids=[],source_absent_animation_ids=mgen.get('source_absent_animation_ids',[]),
        models=62,colour_variants=77,scale=2,SDF=False,resources=1037,resource_bindings=1040,
        physical_frames=sum(s['frame_count'] for s in shards)),
    visual_qa=dict(authority='user',result='pass',user_statement="c'est bon confirmé",
        context='confirmation following common runtime installation; Character animations and QMON7313 attack requested; closes last7312/7313 G2 retests',
        previously_accepted_ids=mgen['retained_Monster_user_QA_ids'],newly_confirmed_asset_ids=['0x7312','0x7313'],
        acceptance_basis='75 acquired accepted IDs + final user confirmation of corrected G2 assets; no new individual77-ID session inferred'),
    runtime_contract=runtime_contract,asset_scope=dict(inventory=identity(inventory),
        installed_leaf_identity_verification=identity(COMMON/'installation-verification.json')),
    provenance=dict(inherited_QA_decisions=prior,production_generation=identity(G2/'production-generation.json'),
        installation_candidate=identity(COMMON/'current-generation.json'),G2_native_verification=identity(G2/'verification.json')),
    installation_changed=False,release=False))
tracking_path=ROOT/'sprite/index/q3m-work-tracking.json';t=load(tracking_path)
others=copy.deepcopy([f for f in t['families'] if f['engine_section']!='monster'])
inherited=[]
for p in t['current_recipe_complete_productions']+t['selected_recipe_complete_productions']:
    q=p.get('qa_reference') or p.get('accepted_qa_reference')
    if q and p['family']!='monster':inherited.append(dict(family=p['family'],qa=identity(ROOT/q)))
write_json(R_QA,dict(schema='bg2-upscale-common-sprite-runtime-qa-decision-v1',status='accepted',qa_state='passed',recorded_at_utc=now,
    scope=dict(kind='shared-runtime-fix-user-confirmation',animation_ids=gen['animation_ids'],families=15,
        confirmation_targets=['Character cycle transitions including6110','QMON7313 G2 attack'],
        all331_individually_retested_in_latest_session=False),
    visual_qa=dict(authority='user',user_statement="c'est bon confirmé",result='pass',
        context='confirmation of installed common CVidCell playback fix and final requested ingame checks',
        new_session_log_trace_claimed=False),runtime_contract=runtime_contract,
    provenance=dict(native_verification=identity(COMMON/'runtime-verification.json'),
        installed_verification=identity(COMMON/'installation-verification.json'),
        inherited_family_QA=inherited,final_monster_QA=identity(M_QA)),
    production_changed=False,installation_changed=False,release=False))
f=next(f for f in t['families'] if f['engine_section']=='monster')
f['state']='selected-recipe-complete-installed-ingame-accepted'
f['current_visual_QA']=dict(state='accepted-full-available-family-x2-nearest-common-native-playback',animation_ids=ids,
    excluded_animation_ids=[],qa_reference=mref,qa_references=[q['path'] for q in prior]+[mref],qa_ingame=True,
    runtime_QA_reference=rref,catalogue_sha256=gen['catalog_sha256'],corrected_assets_pending_user_QA_ids=[],
    known_technical_defect_animation_ids=[],MFIE_ingame_QA=True)
f['current_installation'].update(state='installed-ingame-accepted',reference=(COMMON/'installation-verification.json').relative_to(ROOT).as_posix(),
    receipt=(COMMON/'ingame-installation/active-test.json').relative_to(ROOT).as_posix(),
    generation_reference=(COMMON/'current-generation.json').relative_to(ROOT).as_posix(),dll_sha256=gen['dll']['sha256'],
    qa_ingame=True,qa_reference=mref,runtime_QA_reference=rref,corrected_assets_pending_user_QA_ids=[])
for p in (f['current_full_production'],next(p for p in t['current_recipe_complete_productions'] if p['family']=='monster')):
    p.update(state='selected-recipe-complete-installed-ingame-accepted',qa_ingame=True,qa_reference=mref,
        remaining_user_QA_animation_ids=[],runtime_QA_reference=rref,
        installation_reference=(COMMON/'ingame-installation/active-test.json').relative_to(ROOT).as_posix(),
        installation_snapshot=(COMMON/'installation-verification.json').relative_to(ROOT).as_posix(),
        installation_generation_reference=(COMMON/'current-generation.json').relative_to(ROOT).as_posix())
    p['visual_QA_references']=[q['path'] for q in prior]+[mref]
f['current_technical_correction'].update(state='corrected-installed-ingame-accepted',new_assets_require_ingame_retest=False,
    qa_reference=mref,runtime_QA_reference=rref)
f['current_colour_witness']['qa_reference']=mref
t['current_shared_runtime_correction'].update(state='installed-native-verified-ingame-confirmed',new_runtime_ingame_QA=True,
    qa_reference=rref,remaining_G2_asset_QA_ids=[])
t['queue_totals'].update(current_recipe_ingame_accepted_families=14,current_recipe_ingame_accepted_animation_ids=253,
    current_recipe_partial_user_accepted_animation_ids=0,remaining_user_QA_animation_ids=0,corrected_pending_user_QA_animation_ids=0,
    partial_QA_counting_rule='All77 Monster IDs accepted cumulatively; no partial IDs remaining; with retained CharacterV6 all331 selected IDs accepted',
    selected_recipe_ingame_accepted_families=15,selected_recipe_ingame_accepted_animation_ids=331)
t['final_selected_recipe_status']=dict(state='complete-produced-installed-ingame-accepted',families=15,animation_ids=331,
    improved_recipe_families=14,improved_recipe_ids=253,retained_Character_V6_ids=78,
    remaining_production_families=[],remaining_ingame_QA_ids=[],runtime_QA_reference=rref,monster_QA_reference=mref,
    release=False,release_integration_inferred=False)
assert others==[f for f in t['families'] if f['engine_section']!='monster']
write_json(tracking_path,t)
# Preserve CSV bytes of all other families; update only77 Monster work rows.
p=ROOT/'sprite/index/q3m-work-items.csv';raw=p.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in ids:out.append(line);continue
    row.update(queue_state='selected-recipe-complete-installed-ingame-accepted',colour_variant_state='v7-four-partners-eight-levels-x2-native-palettes-installed-ingame-accepted',
        q3m_v7_installation_reference=(COMMON/'ingame-installation/active-test.json').relative_to(ROOT).as_posix())
    s=io.StringIO(newline='');csv.DictWriter(s,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row);out.append(s.getvalue());changed.append(row['animation_id'])
assert changed==ids;p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
# Live receipt is mutable; the original installation proof remains immutable.
p=COMMON/'ingame-installation/active-test.json';receipt=load(p)
receipt.update(status='installed-ingame-accepted',ingame_QA=True,user_confirmation="c'est bon confirmé",qa_reference=rref,confirmed_at_utc=now)
write_json(p,receipt)
for path,entry in (
    (ROOT/'sprite/SUIVI_Q3M.md','- **État final validé — 2026-10-07 : 15 familles /331 IDs produits, installés et acceptés ingame** (14 familles améliorées/253 IDs +Character V6/78). Monster77 complet et correctif CVidCell commun confirmés ; aucun calcul ni retest restant dans le périmètre retenu. QA historiques conservées ; release non modifiée. [Décisions finales](../docs/measurements/q3m-sprites-final-accepted-x2-20261007-v1/README.md).'),
    (ROOT/'sprite/index/README.md','- **État final validé 2026-10-07 : 15 familles /331 IDs produits/installés/acceptés**, Monster77 et runtime commun confirmés ; aucun lot/retest restant du périmètre retenu. [QA finale](../../docs/measurements/q3m-sprites-final-accepted-x2-20261007-v1/README.md).')):
    text=path.read_text(encoding='utf-8');lines=text.splitlines(True)
    path.write_text(lines[0]+'\n'+entry+'\n'+''.join(lines[1:]),encoding='utf-8',newline='\n')
path=ROOT/'.gitattributes';text=path.read_text(encoding='utf-8');entry=HERE.relative_to(ROOT).as_posix()+'/** -text -whitespace'
if entry not in text:path.write_text(text+'\n'+entry+'\n',encoding='utf-8',newline='\n')
write_json(HERE/'acceptance-summary.json',dict(status='selected-sprite-scope-complete-ingame-accepted',recorded_at_utc=now,
    user_statement="c'est bon confirmé",families=15,animation_ids=331,improved_recipe_ids=253,Character_V6_ids=78,
    monster_ids=77,remaining_production_families=0,remaining_ingame_QA_ids=0,monster_QA=identity(M_QA),runtime_QA=identity(R_QA),
    installed_dll_sha256=gen['dll']['sha256'],installed_catalog_sha256=gen['catalog_sha256'],
    installation_changed=False,production_changed=False,release=False))
print(json.dumps(dict(accepted=True,families=15,ids=331,remaining_retests=0,release_changed=False)),flush=True)
