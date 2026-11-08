"""Publish native/current comparison with retained SeedVR option on xBR alternatives."""
import argparse
import importlib.util
import json
import time
from pathlib import Path
from temporal import ROOT,BATCH,load,save
HERE=Path(__file__).resolve().parent
ALT=ROOT/'effects/batches/lot50-xbr-small-20261108-v1'
OUT=BATCH/'review'
spec=importlib.util.spec_from_file_location('variant_review',HERE/'review.py')
variant=importlib.util.module_from_spec(spec);spec.loader.exec_module(variant)
variant.BATCH=ALT;variant.OUT=OUT/'variants/xbr'

def build(final=False):
    for d in ('data','native','images'):(variant.OUT/d).mkdir(parents=True,exist_ok=True)
    alternatives={}
    for a in load(ALT/'batch.json')['assets']:
        if not (ALT/'runtime-verification'/f'{a["resref"]}.json').exists():continue
        r=variant.card(a)
        r['native']['image']='variants/xbr/'+r['native']['image']
        for f in r['frames']:
            for key in ('image','neutral'):
                if key in f:f[key]='variants/xbr/'+f[key]
        alternatives[a['resref']]=r
    records=[]
    for a in load(BATCH/'batch.json')['assets']:
        path=OUT/'data'/f'{a["resref"]}.json'
        if not path.exists():continue
        seed=load(path)
        if a['resref'] in alternatives:
            r=alternatives[a['resref']]
            r.update(method='xBR4X',seedFrames=seed['frames'],seedProfiles=seed['profiles'])
        else:r=seed;r['method']='SeedVR7B'
        records.append(r)
    template=(HERE/'board.html').read_text(encoding='utf-8')
    template=template.replace('50 effets · SeedVR7B x4 + Apollo30','50 effets · x4 + Apollo30')
    template=template.replace('Comparatif natif / traité, cycles et horloge synchronisés.',f'Comparatif natif / traité, cycles et horloge synchronisés. {len(alternatives)} variantes xBR pour petits motifs ; SeedVR reste accessible sur leurs cartes.')
    template=template.replace('SeedVR7B x4 · Apollo30','${a.method||\'SeedVR7B\'} x4 · Apollo30')
    template=template.replace('<div class="caption">SeedVR7B x4 · Apollo30</div>','<div class="caption resultCaption">${a.method||\'SeedVR7B\'} x4 · Apollo30</div>')
    template=template.replace('<div class="caption">${a.method||\'SeedVR7B\'} x4 · Apollo30</div>','<div class="caption resultCaption">${a.method||\'SeedVR7B\'} x4 · Apollo30</div>')
    template=template.replace('<span class="phaseText"></span>','${a.seedFrames?\'<button class="method">Voir SeedVR</button>\':\'\'}<span class="phaseText"></span>')
    needle='cards.push(c)}'
    replacement="""if(a.seedFrames){const methodButton=el.querySelector('.method');const xbrFrames=a.frames,xbrProfiles=a.profiles;let useSeed=false;methodButton.onclick=()=>{useSeed=!useSeed;a.frames=useSeed?a.seedFrames:xbrFrames;a.profiles=useSeed?a.seedProfiles:xbrProfiles;c.setProfile(c.profile);el.querySelector('.resultCaption').textContent=(useSeed?'SeedVR7B':'xBR4X')+' x4 · Apollo30';methodButton.textContent=useSeed?'Voir xBR':'Voir SeedVR'}};cards.push(c)}"""
    assert needle in template;template=template.replace(needle,replacement)
    text=template.replace('__CARDS__',json.dumps(records,ensure_ascii=False))
    (OUT/'comparison.html').write_text(text,encoding='utf-8')
    if final:(OUT/'index.html').write_text(text,encoding='utf-8')
    save(OUT/'comparison.json',dict(count=len(records),xbr_count=len(alternatives),seedvr_count=len(records)-len(alternatives),assets=[dict(resref=r['resref'],method=r['method']) for r in records]))
    save(OUT/'current-cards.json',dict(assets=records))
    return len(records),len(alternatives)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');p.add_argument('--final',action='store_true');args=p.parse_args();previous=None
    while True:
        result=build(args.final)
        if result!=previous:print('Comparative review',result,flush=True);previous=result
        if result==(50,len(load(ALT/'batch.json')['assets'])) or not args.wait:break
        time.sleep(15)
