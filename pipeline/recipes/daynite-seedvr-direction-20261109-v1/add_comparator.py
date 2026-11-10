from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'video/daynite/runs/daynite-seedvr-direction-20261109-v1'
reports={d:json.loads((RUN/(d+'-production.json')).read_text())for d in ['forward','reverse']}
assert all(r['state']=='verified-comparison-ready'for r in reports.values())
items=[]
for direction,fps in [('reverse',30),('forward',30),('reverse',15),('forward',15)]:
    key='apollo30'if fps==30 else'seed15';p=ROOT/reports[direction]['outputs'][key];assert p.is_file()
    label='INVERSE → remis à l’endroit'if direction=='reverse'else'DIRECT témoin même version'
    items.append({'name':f'DAYNITE — {label} · {fps} fps','url':'../daynite/runs/daynite-seedvr-direction-20261109-v1/'+p.name,'fps':fps})
p=ROOT/'video/tools/comparator.html';s=p.read_text(encoding='utf-8');marker='// DAYNITE DIRECTION TRIAL\n';assert marker not in s
s=s.replace('sourceItems.push(...resultItems.map',marker+'resultItems.unshift(...'+json.dumps(items,ensure_ascii=False,indent=1)+');\nsourceItems.push(...resultItems.map',1);p.write_text(s,encoding='utf-8')
print('Controlled direct and reverse-normalized 15/30 comparisons added.')
