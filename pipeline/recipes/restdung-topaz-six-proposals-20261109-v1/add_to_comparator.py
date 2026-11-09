from pathlib import Path
import json
import os

ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/'video/restdung/runs/restdung-topaz-six-shared-20261109-v1'
report=json.loads((WORK/'production.json').read_text())
verification=json.loads((WORK/'interpolation-verification.json').read_text())
assert report['state']=='completed' and len(verification['interpolation'])==6
page=ROOT/'video/tools/comparator.html'
labels={
    'T1':'Proteus → Proteus → Apollo · 1080p30',
    'T2':'Proteus → Gaia → Apollo · 1080p30',
    'T3':'Proteus doux → Gaia → Apollo · 1080p30',
    'T4':'Proteus → Lanczos → Apollo · 1080p30',
    'T5':'Proteus → Apollo → Gaia · 1080p30',
    'T6':'Proteus → Gaia → Aion · 1080p30',
}
items=[]
for tid,label in labels.items():
    item=report['finals'][tid]
    assert item['state']=='verified'
    path=ROOT/item['path'];assert path.is_file()
    items.append({'name':f'{tid} — {label}','url':os.path.relpath(path,page.parent).replace('\\','/'),'fps':30})
start='// BEGIN RESTDUNG T1-T6\n';end='// END RESTDUNG T1-T6\n'
text=page.read_text(encoding='utf-8')
if start in text:
    before,rest=text.split(start,1);_,after=rest.split(end,1);text=before+after
block=start+'resultItems.unshift(...'+json.dumps(items,ensure_ascii=False,indent=1)+');\n'+end
text=text.replace('sourceItems.push(...resultItems.map',block+'sourceItems.push(...resultItems.map',1)
old="renderLoop();seek(Math.min(t,duration()-0.01));"
new="frameRate=Math.max(sourceItems[Number($('sourceSelect').value)].fps||15,resultItems[Number($('resultSelect').value)].fps||15);renderLoop();seek(Math.min(t,duration()-0.01));"
if new not in text:
    assert old in text
    text=text.replace(old,new,1)
page.write_text(text,encoding='utf-8')
print('Added T1..T6 to BOTH selectors; default source preserved.')
