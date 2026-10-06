"""Verify installed MFIE delta and reconcile active pointers; QA proofs immutable."""
import copy,csv,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');receipt=load(HERE/'ingame-installation/active-test.json')
baseline=load(HERE/'baseline.json');verification=load(HERE/'verification.json');proof=load(HERE/'catalog-proof.json')
game=get_path('bg2ee_game_root',required=True);prefix=HERE.relative_to(ROOT).as_posix()
assert not(HERE/'installed-verification.json').exists()
assert receipt['status']=='installed-MFIE-native-palettes-pending-ingame-qa' and verification['passed'] and proof['passed']
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
assert file_sha(game/baseline['catalog_relative'])==gen['catalog']['sha256']
for r in baseline['preserved']:assert file_sha(game/r['relative_path']).upper()==r['sha256'].upper()
for s in baseline['candidate_shards']:assert file_sha(game/s['registry']).upper()==s['sha256'].upper()
for d in gen['partial_visual_QA']['decisions']:assert file_sha(ROOT/d['path'])==d['sha256']
assert len(receipt['created_leaves'])==6 and proof['retained_ids']==330
write_json(HERE/'installed-verification.json',dict(passed=True,dll_sha256=gen['dll']['sha256'],catalog_sha256=gen['catalog']['sha256'],
    changed_existing_files=baseline['changed_files'],created_leaves=6,preserved_files_sha256_verified=len(baseline['preserved']),
    retained_catalog_proof=prefix+'/catalog-proof.json',retained_ids=330,retained_routes=63015,
    MFIE_resources=14,MFIE_frames=5888,user_accepted_ids=76,remaining_user_QA_ids=['0x7314'],MFIE_ingame_QA=False,release=False))
generation_ref=prefix+'/current-generation.json';snapshot=prefix+'/installation-verification.json';receiptref=prefix+'/ingame-installation/active-test.json'
production_ref=prefix+'/production-generation.json';state='family-complete-installed-MFIE-native-palettes-v3-partial-visual-QA-76-one-retest-pending'
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path)
others=copy.deepcopy([f for f in tracking['families'] if f['engine_section']!='monster'])
family=next(f for f in tracking['families'] if f['engine_section']=='monster');family['state']=state
qa=family['current_visual_QA'];assert len(qa['animation_ids'])==76 and '0x7314' not in qa['animation_ids']
# Preserve the historical QA catalog/DLL contracts; add only a retention proof for the new installation.
qa.update(retained_by_catalog_proof=prefix+'/catalog-proof.json',MFIE_palette_v2_user_result='still-vanilla',MFIE_ingame_QA=False,
    MFIE_current_retest_generation=generation_ref)
family['current_installation'].update(state='installed-MFIE-native-palettes-v3-one-retest-pending',reference=snapshot,receipt=receiptref,
    generation_reference=generation_ref,dll_sha256=gen['dll']['sha256'],catalogue_sha256=gen['catalog']['sha256'],qa_ingame=False,
    correction_animation_ids=['0x7314'],retained_catalog_proof=prefix+'/catalog-proof.json')
for item in (family['current_full_production'],next(r for r in tracking['current_recipe_complete_productions'] if r['family']=='monster')):
    assert item['qa_ingame'] is False
    item.update(reference=production_ref,parent_full_production_reference=gen['production_generation']['path'],state=state,
        native_palette_correction=dict(animation_ids=['0x7314'],resources=14,frames=5888,changed_bindings=6,
            selection=prefix+'/selection.json',production=prefix+'/production.json',verification=prefix+'/verification.json'),
        installation_reference=receiptref,installation_snapshot=snapshot,installation_generation_reference=generation_ref,
        remaining_user_QA_animation_ids=['0x7314'],runtime_stability_verification=prefix+'/verification.json')
family['current_colour_witness']['installation_reference']=snapshot
tracking['engine_integration'].update(installed_candidate_reference=generation_ref,latest_installation_verification_reference=snapshot)
tracking['queue_totals'].update(current_recipe_partial_user_accepted_animation_ids=76,remaining_user_QA_animation_ids=1,
    partial_QA_counting_rule='73 Monster IDs accepted on original runtime +3 on stability v1; 76 retained unchanged; MFIE vanilla in palette-v2, native-bank-v3 installed/retest pending; distinct from176 full-family improved IDs')
assert others==[f for f in tracking['families'] if f['engine_section']!='monster'];write_json(path,tracking)
path=ROOT/'sprite/index/q3m-work-items.csv';raw=path.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True)
fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in gen['animation_ids']:out.append(line);continue
    row['q3m_v7_installation_reference']=receiptref
    if row['animation_id']=='0x7314':
        row.update(q3m_v7_full_production_reference=production_ref,queue_state='current-recipe-complete-installed-MFIE-native-palettes-v3-ingame-QA-pending',
            colour_variant_state='v7-four-partners-eight-levels-no-SDF-x2-MFIE-native-G1-253-G2-252-retest-pending')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row)
    out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==gen['animation_ids'];path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
path=ROOT/'sprite/SUIVI_Q3M.md';text=path.read_text(encoding='utf-8')
lines=text.splitlines(keepends=True)
for i,line in enumerate(lines):
    if line.startswith('- **Monster état courant :'):
        lines[i]='- **Monster état courant : 76/77 IDs validés**, acquis conservés ; **MFIE7314 corrigé/installé, retest ingame seul restant**. Trace palette-v2 : G1 natif MFIEG31/253, production erronée MFIEG3B/252 ; SetSequence G1→palette1/G2→palette2. [Correction native-v3](../docs/measurements/q3m-mfie-native-palettes-x2-20261007-v3/README.md) : six ressources G1 remplacées, huit réutilisées ; 381 hits/541 encodages manquants, dont un spécial. 5 888 frames K6×3 formats +64 746 gardes vérifiées ; 330 autres IDs/63 015 routes identiques. QA MFIE non déduite, aucune release.\n'
    elif line.startswith('| `monster` |'):
        lines[i]=line.replace('seul MFIE7314 reste à retester avec palette-v2','seul MFIE7314 reste à retester avec native-palettes-v3')
    elif line.startswith('- Production améliorée complète :'):
        lines[i]=line.replace('76 IDs acceptés ; MGCL7F0B/NSOL7F2C/NSHD7F36 validés sur stabilité-v1 ; MFIE7314 encore vanilla en v1, palette-v2 installé pour retest','76 IDs acceptés ; MFIE7314 native-palettes-v3 installé, retest seul restant')
path.write_text(''.join(lines),encoding='utf-8',newline='\n')
path=ROOT/'sprite/index/README.md';text=path.read_text(encoding='utf-8');lines=text.splitlines(keepends=True)
for i,line in enumerate(lines):
    if line.startswith('- **Monster courant :'):
        lines[i]='- **Monster courant : 76/77 IDs validés**, décisions QA historiques conservées. **MFIE7314 native-palettes-v3 installé, retest seul restant** : [cause/correction/preuves](../../docs/measurements/q3m-mfie-native-palettes-x2-20261007-v3/README.md), G1 MFIEG31/253 ; G2 MFIEG3B/252 ; six feuilles G1 nouvelles. 330 autres IDs identiques. Les lignes datées ci-dessous restent historiques.\n'
path.write_text(''.join(lines),encoding='utf-8',newline='\n')
attributes=ROOT/'.gitattributes';text=attributes.read_text(encoding='utf-8');line=f'{prefix}/** -text -whitespace'
if line not in text:attributes.write_text(text+'\n'+line+'\n',encoding='utf-8',newline='\n')
write_json(HERE/'summary.json',dict(installed=True,corrected_animation_ids=['0x7314'],changed_bindings=6,reused_bindings=8,
    compatible_encoded_hits=381,missing_encoded=541,user_accepted_ids_retained=76,remaining_user_QA_ids=['0x7314'],MFIE_v2_still_vanilla=True,
    MFIE_v3_ingame_QA=False,other_ids_preserved=330,tracking_updated=True,release=False))
print(json.dumps(dict(installed=True,user_accepted_ids_retained=76,retests=1,tracking_updated=True)),flush=True)
