"""Versioned board revision; preserve prior50 board and all43 unaffected cards."""
import copy
import importlib.util
import json
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from correct import ROOT,BASE,OUT,NAMES,load,save,rel

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/recipes/effects-lot50-seedvr7b-apollo30-20261108-v1'))
spec=importlib.util.spec_from_file_location('alpha_review',ROOT/'pipeline/recipes/effects-lot50-seedvr7b-apollo30-20261108-v1/review.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
REVISION='revisions/black-transparent-20261108-v1'
BOARD=BASE/'review';review.OUT=BOARD/REVISION;review.BATCH=OUT

def rebase(r,prefix):
    r=copy.deepcopy(r);r['native']['image']=prefix+r['native']['image']
    for f in r['frames']+r.get('seedFrames',[]):
        for key in ('image','neutral'):
            if key in f:f[key]=prefix+f[key]
    return r

def main():
    current=load(OUT/'production.json');original={r['resref']:r for r in load(BOARD/'current-cards.json')['assets']}
    for p in ('data','native','images'):(review.OUT/p).mkdir(parents=True,exist_ok=True)
    plans={a['resref']:a for directory in (BASE,ROOT/'effects/batches/lot50-xbr-small-20261108-v1') for a in load(directory/'batch.json')['assets']}
    corrected={}
    for a in current['assets']:
        n=a['resref']
        if n not in NAMES:continue
        plan={**plans[n],**a};r=review.card(plan);r=rebase(r,'/'+REVISION+'/')
        previous=rebase(original[n],'/')
        r.update(method=original[n]['method'],beforeAlpha=True,seedFrames=previous['frames'],seedProfiles=previous['profiles'])
        corrected[n]=r
    records=[corrected.get(n,rebase(r,'/')) for n,r in original.items()]
    assert len(records)==50 and len(corrected)==7
    source=BOARD/'index-before-black-transparent-20261108-v1.html'
    if not source.exists():shutil.copyfile(BOARD/'index.html',source)
    html=source.read_text(encoding='utf-8')
    start=html.index('const records=')+len('const records=');end=html.index(', $=s=>',start)
    html=html[:start]+json.dumps(records,ensure_ascii=False)+html[end:]
    html=html.replace('Comparatif natif / traité, cycles et horloge synchronisés.','Sept corrections de transparence noire actives :29,31,35,36,41,42,50. Bouton « Voir avant correction » sur ces cartes. Comparatif natif / traité, cycles et horloge synchronisés.')
    html=html.replace("${a.seedFrames?'<button class=\"method\">Voir SeedVR</button>':''}","${a.seedFrames?'<button class=\"method\">'+(a.beforeAlpha?'Voir avant correction':'Voir SeedVR')+'</button>':''}")
    html=html.replace("(useSeed?'SeedVR7B':'xBR4X')+' x4 · Apollo30'","(useSeed?(a.beforeAlpha?'Avant correction':'SeedVR7B'):(a.method||'xBR4X'))+' x4 · Apollo30'")
    html=html.replace("methodButton.textContent=useSeed?'Voir xBR':'Voir SeedVR'","methodButton.textContent=useSeed?(a.beforeAlpha?'Voir corrigé':'Voir xBR'):(a.beforeAlpha?'Voir avant correction':'Voir SeedVR')")
    html=html.replace("${a.green!==null?' · masque vert dérivé':''}","${a.green!==null?' · masque vert dérivé':''}${a.beforeAlpha?' · noir transparent corrigé':''}")
    (review.OUT/'index.html').write_text(html,encoding='utf-8')
    save(review.OUT/'current-cards.json',dict(assets=records))
    target=REVISION+'/index.html?v=alpha7'
    (BOARD/'index.html').write_text(f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={target}"><title>Lot50 · transparence corrigée</title><a href="{target}">Ouvrir la planche50 corrigée</a>',encoding='utf-8')
    # One common anchor per effect, before/after on terrain. Images remain full alignment.
    sheet=Image.new('RGB',(1000,190*7),(27,34,44));d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
    for row,a in enumerate([a for a in current['assets'] if a['resref'] in NAMES]):
        n=a['resref'];r=corrected[n];profile=r['profiles'][0];phase=min(12,len(profile['frames'])-1)
        for col,(frames,label) in enumerate([(r['seedFrames'],'Avant'),(r['frames'],'Corrige')]):
            f=frames[profile['frames'][phase]];im=Image.new('RGBA',(r['width'],r['height']));tile=Image.open(BOARD/f['image'].lstrip('/'));im.paste(tile,(f['x'],f['y']))
            bg=Image.new('RGBA',im.size,(110,94,70,255));bg.alpha_composite(im);bg.thumbnail((450,150),Image.Resampling.NEAREST)
            sheet.paste(bg.convert('RGB'),(col*500+10,row*190+30));d.text((col*500+10,row*190+5),f'{a["ordinal"]:02} {n} · {label}',font=font,fill='white')
    sheet.save(OUT/'before-after-terrain.png')
    save(OUT/'publication.json',dict(cards=50,corrected=sorted(NAMES),url='http://127.0.0.1:8797/'+target,revision=rel(review.OUT/'index.html'),unchanged_cards=43))
    print('Published50,7corrected,43unchanged. '+target,flush=True)

if __name__=='__main__':main()
