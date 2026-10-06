"""Record successor installation and partial visual QA without full-family promotion."""
import copy,csv,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');receipt=load(HERE/'ingame-installation/active-test.json')
qa=load(HERE/'partial-QA.json');baseline=load(HERE/'baseline.json');game=get_path('bg2ee_game_root',required=True)
assert receipt['status']=='installed-corrected-runtime-pending-ingame-qa'
assert not(HERE/'installed-verification.json').exists()
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
for r in baseline['preserved']:assert file_sha(game/r['relative_path']).upper()==r['sha256'].upper()
write_json(HERE/'installed-verification.json',dict(passed=True,dll_sha256=gen['dll']['sha256'],catalog_sha256=gen['catalog']['sha256'],
    changed_files=['InfinityEngine-Enhancer.dll'],preserved_files_sha256_verified=len(baseline['preserved']),monster_leaves=1037,neutral_CRE=77,
    prior_visual_accepted_ids=73,remaining_user_QA_ids=qa['excluded_ids'],corrected_runtime_ingame_QA=False,release=False))
prefix=HERE.relative_to(ROOT).as_posix();generation_ref=prefix+'/current-generation.json';snapshot=prefix+'/installation-verification.json';receiptref=prefix+'/ingame-installation/active-test.json'
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path)
others=copy.deepcopy([f for f in tracking['families'] if f['engine_section']!='monster'])
family=next(f for f in tracking['families'] if f['engine_section']=='monster')
state='family-complete-installed-corrected-runtime-partial-visual-QA-73-four-retests-pending'
visual=dict(state='accepted-partial-73-as-tested-prior-runtime',qa_reference=qa['qa_reference'],animation_ids=qa['accepted_ids'],models=60,
    excluded_animation_ids=qa['excluded_ids'],dll_sha256=qa['accepted_dll_sha256'],catalogue_sha256=gen['catalog']['sha256'],
    corrected_runtime_ingame_QA=False,runtime_verification_reference=prefix+'/runtime-verification.json')
family['state']=state;family['current_visual_QA']=visual
family['current_installation'].update(state='installed-corrected-runtime-four-retests-pending',reference=snapshot,receipt=receiptref,
    generation_reference=generation_ref,dll_sha256=gen['dll']['sha256'],qa_ingame=False,prior_partial_QA_reference=qa['qa_reference'])
for item in (family['current_full_production'],next(r for r in tracking['current_recipe_complete_productions'] if r['family']=='monster')):
    assert item['qa_ingame'] is False
    item.update(state=state,installation_reference=receiptref,installation_snapshot=snapshot,installation_generation_reference=generation_ref,
        partial_visual_QA_reference=qa['qa_reference'],remaining_user_QA_animation_ids=qa['excluded_ids'],runtime_stability_verification=prefix+'/runtime-verification.json')
family['current_colour_witness'].update(state='visual-accepted-via-partial-family-QA-corrected-runtime-installed',installation_reference=snapshot,qa_reference=qa['qa_reference'])
tracking['engine_integration'].update(installed_candidate_reference=generation_ref,latest_installation_verification_reference=snapshot)
tracking['queue_totals'].update(current_recipe_partial_user_accepted_animation_ids=73,remaining_user_QA_animation_ids=4,
    partial_QA_counting_rule='73 Monster IDs accepted on prior runtime; distinct from 176 full-family improved IDs; corrected runtime ingame confirmation pending')
assert tracking['queue_totals']['current_recipe_ingame_accepted_animation_ids']==176
assert others==[f for f in tracking['families'] if f['engine_section']!='monster']
write_json(path,tracking)
path=ROOT/'sprite/index/q3m-work-items.csv';raw=path.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True)
fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in gen['animation_ids']:out.append(line);continue
    assert row['engine_family']=='monster'
    accepted=row['animation_id'] in qa['accepted_ids']
    row.update(q3m_v7_installation_reference=receiptref,
        queue_state='current-recipe-complete-installed-visual-accepted-prior-runtime-stability-pending' if accepted else 'current-recipe-complete-installed-corrected-ingame-QA-pending',
        colour_variant_state='v7-four-partners-eight-levels-no-SDF-x2-visual-accepted-runtime-confirmation-pending' if accepted else 'v7-four-partners-eight-levels-no-SDF-x2-corrected-ingame-QA-pending')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row)
    out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==gen['animation_ids'];path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
path=ROOT/'sprite/SUIVI_Q3M.md';text=path.read_text(encoding='utf-8')
old='**Famille disponible complète Q3m V7 x2 améliorée sans SDF installée, QA ingame en attente**'
new='**Famille disponible complète Q3m V7 x2 améliorée sans SDF installée ; 73 IDs acceptés visuellement sur le runtime précédent, quatre retests après correction DLL**'
assert text.count(old)==1;text=text.replace(old,new)
old='Monster 77 IDs/62 modèles en attente de QA'
new='Monster 77 IDs/62 modèles installé : 73 IDs acceptés sur le runtime testé ; 7314/7F0B/7F2C/7F36 à retester avec la DLL corrigée'
assert text.count(old)==1;text=text.replace(old,new)
marker='## Queue / références\n'
text=text.replace(marker,marker+'\n- Monster stabilité 2026-10-07 : **DLL corrigée installée**, owner3 attente des métadonnées +Loop/Clamp natifs ; Burning Man palette252, lecture bornée, aucun index/partenaire utilisé dans la queue absente. **73 IDs/60 modèles acceptés tels que testés** ; MFIE7314/MGCL7F0B/NSOL7F2C/NSHD7F36 à retester (clic/actions/fins de cycles). Tests hôte : 1 040 liaisons/56 383 cycles/1 240 346 cas natifs, 79 ressources/40 358 frames K6×3 formats, régression Icewind 1 140 ressources. Catalogue/sprites/CRE/Nearest inchangés ; aucune nouvelle QA runtime déduite. [Preuves/QA partielle](../docs/measurements/q3m-monster-stability-x2-20261007-v1/README.md).\n',1)
path.write_text(text,encoding='utf-8',newline='\n')
path=ROOT/'sprite/index/README.md';text=path.read_text(encoding='utf-8');marker='## Tables\n'
text=text.replace(marker,marker+'\n- Monster 2026-10-07 : **73 IDs validés par l’utilisateur sur le runtime précédent**, décision immuable [QA partielle](qa-decisions/monsters/2026-10-07-accepted-partial-monster-73-q3m-v7-x2-nearest-v1.json). **DLL de stabilité corrigée installée**, sprites/catalogue identiques ; quatre retests MFIE7314/MGCL7F0B/NSOL7F2C/NSHD7F36. [Diagnostic, tests, installation](../../docs/measurements/q3m-monster-stability-x2-20261007-v1/README.md). Compteurs de familles entièrement acceptées ci-dessous inchangés ; QA du runtime corrigé non déduite.\n',1)
path.write_text(text,encoding='utf-8',newline='\n')
attributes=ROOT/'.gitattributes';text=attributes.read_text(encoding='utf-8');line=f'{prefix}/** -text -whitespace'
if line not in text:attributes.write_text(text+'\n# Monster stability successor and immutable partial visual QA.\n'+line+'\nsprite/index/qa-decisions/monsters/2026-10-07-accepted-partial-monster-73-q3m-v7-x2-nearest-v1.json -text -whitespace\n',encoding='utf-8',newline='\n')
write_json(HERE/'summary.json',dict(installed=True,changed_files=1,prior_visual_accepted_ids=73,prior_visual_accepted_models=60,
    remaining_user_QA_ids=qa['excluded_ids'],corrected_runtime_ingame_QA=False,full_family_QA=False,sprites_recalculated=0,release=False))
print(json.dumps(dict(installed=True,prior_visual_accepted_ids=73,retests=4,tracking_updated=True)),flush=True)
