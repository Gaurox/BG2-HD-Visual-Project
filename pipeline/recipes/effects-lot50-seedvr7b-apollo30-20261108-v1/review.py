"""Build synchronized canvas review from verified RGBA; no UI automation."""
import hashlib
import json
import shutil
import time
import argparse
from pathlib import Path
import numpy as np
from PIL import Image
from temporal import ROOT,BATCH,load,save

OUT=BATCH/'review'
NATIVE=ROOT/'effects/batches/lot50-native-animated-board-20261108-v1'

def png(array):
    key=hashlib.sha256(array.tobytes()+str(array.shape).encode()).hexdigest()
    p=OUT/'images'/(key+'.png')
    if not p.exists():Image.fromarray(array).save(p,compress_level=3)
    return 'images/'+p.name

def card(a):
    record=OUT/'data'/(a['resref']+'.json')
    if record.exists():return load(record)
    name=a['resref'];stage=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run']/'02-interpolation'
    m=load(stage/'manifest.json');s=load(ROOT/m['parent']['spatial_manifest'])
    cw,ch=s['aligned_canvas_size_x1'];anchor=[s['frames'][0]['canvas_offset_x1'][i]+s['frames'][0]['centre_x1'][i] for i in range(2)]
    native=next(c for c in load(NATIVE/'catalog.json')['assets'] if c['resref']==name)
    native_image='native/'+name+'.png';shutil.copyfile(NATIVE/native['image'],OUT/native_image)
    rows=[]
    for f in m['frames']:
        w,h=f['physical_size_x4'];raw=np.frombuffer((stage/f['straight_raw_rgba_x4']).read_bytes(),np.uint8).reshape(h,w,4)
        row=dict(image=png(raw),x=(anchor[0]-f['centre_x1'][0])*4,y=(anchor[1]-f['centre_x1'][1])*4,w=w,h=h)
        if f.get('neutral_raw_rgba_x4'):
            row['neutral']=png(np.frombuffer((stage/f['neutral_raw_rgba_x4']).read_bytes(),np.uint8).reshape(h,w,4))
        rows.append(row)
    profiles=[dict(id=v['id'],cycle=v['cycle'],loop=v['loop_closed'],native=v['native_slots'],frames=v['timeline_frame_indices'],duration=v['duration_seconds']) for v in m['timing']['cycles']]
    result=dict(ordinal=a['ordinal'],resref=name,profile=a['profile'],sigma=a['sigma_x4'],feather=a['inner_feather_x4'],
                width=cw*4,height=ch*4,native=dict(image=native_image,width=native['width'],height=native['height'],cols=native['cols']),
                profiles=profiles,frames=rows,green=a.get('green_index'))
    save(record,result);return result

def build():
    for folder in ('data','native','images'):(OUT/folder).mkdir(parents=True,exist_ok=True)
    records=[]
    for a in load(BATCH/'batch.json')['assets']:
        if (BATCH/'verification'/(a['resref']+'.json')).exists():records.append(card(a))
    template=Path(__file__).with_name('board.html').read_text(encoding='utf-8')
    target=OUT/'index.html';partial=OUT/'index.partial.html'
    partial.write_text(template.replace('__CARDS__',json.dumps(records,ensure_ascii=False)),encoding='utf-8');partial.replace(target)
    save(OUT/'review.json',dict(count=len(records),assets=[dict(resref=r['resref'],profiles=len(r['profiles'])) for r in records]))
    return len(records)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');args=p.parse_args()
    previous=-1
    while True:
        count=build()
        if count!=previous:print('Review ready',count,'/50',flush=True);previous=count
        if count==50 or not args.wait:break
        time.sleep(15)
