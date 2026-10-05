"""Publish only the MultiNew runtime/installation references; keep QA pending."""
import csv, io, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import write_json,file_sha
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
receipt=load(HERE/'ingame-installation/active-test.json')
assert receipt['status'] in ('installed-pending-ingame-qa','restored-parent-runtime')
restored=receipt['status']=='restored-parent-runtime'
active=ROOT/'docs/measurements/q3m-multi-new-frame-stability-20261005-v1' if restored else HERE
gen=load(active/'current-generation.json')
assert file_sha(get_path('bg2ee_game_root',required=True)/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
reference=active.relative_to(ROOT).as_posix()+'/current-generation.json'
snapshot=active.relative_to(ROOT).as_posix()+'/installation-verification.json'
receiptref=active.relative_to(ROOT).as_posix()+'/ingame-installation/active-test.json'
p=ROOT/'sprite/index/q3m-work-tracking.json'; tracking=load(p)
totals=dict(tracking['queue_totals'])
family=next(f for f in tracking['families'] if f['engine_section']=='multi_new')
assert not family['current_full_production']['qa_ingame']
family['current_full_production'].update(reference=reference,runtime_reference=gen['runtime']['path'],
    installation_reference=receiptref,installation_snapshot=snapshot)
family['current_installation'].update(reference=snapshot,receipt=receiptref,
    dll_sha256=gen['dll']['sha256'],catalogue_sha256=gen['catalog']['sha256'])
family['current_colour_witness']['installation_reference']=snapshot
entry=next(e for e in tracking['current_recipe_complete_productions'] if e['family']=='multi_new')
entry.update(family['current_full_production'])
tracking['engine_integration'].update(installed_candidate_reference=reference,
    latest_installation_verification_reference=snapshot)
assert tracking['queue_totals']==totals
write_json(p,tracking)
p=ROOT/'sprite/index/q3m-work-items.csv'; raw=p.read_bytes()
lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]])); out=[lines[0]]; changed=0
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['engine_family']!='multi_new':out.append(line);continue
    row.update(q3m_v7_full_production_reference=reference,q3m_v7_installation_reference=receiptref)
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row)
    out.append(stream.getvalue());changed+=1
assert changed==10
p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
print('MultiNew runtime/installation pointers updated; counts and QA decisions unchanged.')
