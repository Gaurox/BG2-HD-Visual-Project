"""Update active installation and 76 accepted IDs; keep MFIE unresolved."""
import copy,csv,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');receipt=load(HERE/'ingame-installation/active-test.json');qa=load(HERE/'partial-QA.json')
baseline=load(HERE/'baseline.json');game=get_path('bg2ee_game_root',required=True)
assert not(HERE/'installed-verification.json').exists()
assert receipt['status']=='installed-corrected-runtime-pending-ingame-qa' and file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
for r in baseline['preserved']:assert file_sha(game/r['relative_path']).upper()==r['sha256'].upper()
write_json(HERE/'installed-verification.json',dict(passed=True,dll_sha256=gen['dll']['sha256'],catalog_sha256=gen['catalog']['sha256'],
    changed_files=['InfinityEngine-Enhancer.dll'],preserved_files_sha256_verified=len(baseline['preserved']),monster_leaves=1037,neutral_CRE=77,
    user_accepted_ids=76,remaining_user_QA_ids=['0x7314'],MFIE_ingame_QA=False,release=False))
prefix=HERE.relative_to(ROOT).as_posix();generation_ref=prefix+'/current-generation.json';snapshot=prefix+'/installation-verification.json';receiptref=prefix+'/ingame-installation/active-test.json'
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path)
others=copy.deepcopy([f for f in tracking['families'] if f['engine_section']!='monster'])
family=next(f for f in tracking['families'] if f['engine_section']=='monster');state='family-complete-installed-MFIE-palette-v2-partial-visual-QA-76-one-retest-pending'
family['state']=state
family['current_visual_QA']=dict(state='accepted-partial-76-exact-tested-contracts',animation_ids=qa['accepted_ids'],qa_references=qa['qa_references'],
    excluded_animation_ids=['0x7314'],catalogue_sha256=gen['catalog']['sha256'],MFIE_ingame_QA=False,
    MFIE_palette_v1_user_result='still-vanilla',runtime_verification_reference=prefix+'/runtime-verification.json')
family['current_installation'].update(state='installed-MFIE-palette-v2-one-retest-pending',reference=snapshot,receipt=receiptref,generation_reference=generation_ref,
    dll_sha256=gen['dll']['sha256'],qa_ingame=False,partial_QA_references=qa['qa_references'])
family['current_installation'].pop('prior_partial_QA_reference',None)
for item in (family['current_full_production'],next(r for r in tracking['current_recipe_complete_productions'] if r['family']=='monster')):
    assert item['qa_ingame'] is False
    item.update(state=state,installation_reference=receiptref,installation_snapshot=snapshot,installation_generation_reference=generation_ref,
        partial_visual_QA_references=qa['qa_references'],remaining_user_QA_animation_ids=['0x7314'],runtime_stability_verification=prefix+'/runtime-verification.json')
    item.pop('partial_visual_QA_reference',None)
family['current_colour_witness']['installation_reference']=snapshot
tracking['engine_integration'].update(installed_candidate_reference=generation_ref,latest_installation_verification_reference=snapshot)
tracking['queue_totals'].update(current_recipe_partial_user_accepted_animation_ids=76,remaining_user_QA_animation_ids=1,
    partial_QA_counting_rule='73 Monster IDs accepted on original runtime +3 accepted on stability v1; distinct from176 full-family improved IDs; MFIE remains vanilla in v1, palette-v2 retest pending')
assert others==[f for f in tracking['families'] if f['engine_section']!='monster'];write_json(path,tracking)
path=ROOT/'sprite/index/q3m-work-items.csv';raw=path.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in gen['animation_ids']:out.append(line);continue
    accepted=row['animation_id'] in qa['accepted_ids']
    row.update(q3m_v7_installation_reference=receiptref,
        queue_state='current-recipe-complete-installed-visual-accepted-exact-tested-contract' if accepted else 'current-recipe-complete-installed-MFIE-palette-v2-ingame-QA-pending',
        colour_variant_state='v7-four-partners-eight-levels-no-SDF-x2-user-accepted-pixels-preserved' if accepted else 'v7-four-partners-eight-levels-no-SDF-x2-MFIE-still-vanilla-v1-palette-v2-pending')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row);out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==gen['animation_ids'];path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
path=ROOT/'sprite/SUIVI_Q3M.md';text=path.read_text(encoding='utf-8')
text=text.replace('73 IDs acceptés visuellement sur le runtime précédent, quatre retests après correction DLL','76 IDs acceptés visuellement sur leurs contrats testés ; seul MFIE7314 reste à retester avec palette-v2')
text=text.replace('73 IDs acceptés sur le runtime testé ; 7314/7F0B/7F2C/7F36 à retester avec la DLL corrigée','76 IDs acceptés ; MGCL7F0B/NSOL7F2C/NSHD7F36 validés sur stabilité-v1 ; MFIE7314 encore vanilla en v1, palette-v2 installé pour retest')
marker='## Queue / références\n'
text=text.replace(marker,marker+'\n- **Monster état courant : 76/77 IDs validés par l’utilisateur**, MGCL7F0B/NSOL7F2C/NSHD7F36 retests acceptés ; QA immutable additionnelle v2. **MFIE7314 encore vanilla avec stabilité-v1**, capture palette refusée. DLL palette-v2 installée : comparer252 entrées définies même si CVidCell annonce256, ignorer queue seulement si dépendances I/F absentes ; trace MFIE_PALETTE bornée8. Cause palette live exacte non mesurée par ancien journal. [Diagnostic/candidat](../docs/measurements/q3m-mfie-palette-stability-x2-20261007-v2/README.md). QA ingame MFIE en attente, aucun recalcul/release.\n',1)
path.write_text(text,encoding='utf-8',newline='\n')
path=ROOT/'sprite/index/README.md';text=path.read_text(encoding='utf-8');marker='## Tables\n'
text=text.replace(marker,marker+'\n- **Monster courant : 76/77 IDs validés**, dont [trois retests stabilité-v1](qa-decisions/monsters/2026-10-07-accepted-three-monster-stability-retests-q3m-v7-x2-nearest-v2.json). **MFIE7314 seul ouvert**, toujours vanilla en v1 ; [palette-v2 +trace ciblée installé](../../docs/measurements/q3m-mfie-palette-stability-x2-20261007-v2/README.md), retest ingame requis. Les lignes datées ci-dessous conservent les constats des sessions précédentes.\n',1)
path.write_text(text,encoding='utf-8',newline='\n')
attributes=ROOT/'.gitattributes';text=attributes.read_text(encoding='utf-8');line=f'{prefix}/** -text -whitespace'
if line not in text:attributes.write_text(text+'\n'+line+'\nsprite/index/qa-decisions/monsters/2026-10-07-accepted-three-monster-stability-retests-q3m-v7-x2-nearest-v2.json -text -whitespace\n',encoding='utf-8',newline='\n')
write_json(HERE/'summary.json',dict(installed=True,changed_files=1,user_accepted_ids=76,remaining_user_QA_ids=['0x7314'],MFIE_v1_still_vanilla=True,
    MFIE_v2_ingame_QA=False,exact_live_palette_refusal_not_known=True,full_family_QA=False,sprites_recalculated=0,release=False))
print(json.dumps(dict(installed=True,user_accepted_ids=76,retests=1,tracking_updated=True)),flush=True)
