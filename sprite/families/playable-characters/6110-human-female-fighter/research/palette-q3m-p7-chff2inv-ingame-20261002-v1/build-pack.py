"""Package existing CHFF2INV I/F planes; no model inference or world catalog write."""
from pathlib import Path
import hashlib
import json
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[6]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import numpy as np
import palette_registry
from palette_oracle import read_bam_p8

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    out=Path(__file__).resolve().parent
    if (out/'pack.json').exists(): raise ValueError('Frozen pack: use a fresh run')
    pilot=out.parent/'palette-q3m-p7-chff2inv-20261002-v1'
    source=ROOT/'sprite/Etudes_Sprite_codex_claude/CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/vanilla_inventory/CHFF2INV.BAM'
    expected='d7f3e6361216d3273e7f09e00ce8cdc77d9fcbc9fef20b5dab051bc6e2a23672'
    if sha(source)!=expected: raise ValueError('Source changed')
    bam=read_bam_p8(source.read_bytes())
    records=[]
    inputs=[]
    for n,frame in enumerate(bam['frames']):
        path=pilot/f'part-{n}-q3m-x2.npz'
        required=['84bad826c0092296b4fdeb543f93ba49a53fc908adc3938345ad09c6ff26fd3d',
                  '8482eb9d257b5b9627ca879a5ddb705322daf13c4b266018fdcd3cb75f679f18'][n]
        if sha(path)!=required: raise ValueError('Frozen logical planes changed')
        with np.load(path,allow_pickle=False) as data:
            geometry=data['native_geometry'].tolist()
            reps=np.full(256,65535,np.uint16)
            values,offsets=np.unique(frame['indices'].ravel(),return_index=True)
            reps[values]=offsets
            records.append(dict(geometry=geometry,representatives=reps,guide=data['guide'].copy(),
                                I=data['I'].copy(),F=data['F'].copy(),dep=data['dep_mask'].copy()))
        inputs.append(dict(path=str(path.relative_to(ROOT)).replace('\\','/'),sha256=required))
    work=out/'work'; work.mkdir(exist_ok=True)
    pack=work/'CHFF2INV-Q3m-X2.registry'
    palette_registry.write(pack,2,[dict(resref='CHFF2INV',source_sha256=expected,
        frames=records,cycles=[[0,0,1,1]])],compress=False,retain_zero_f=True)
    # Independent byte oracle from every observed native palette, stored BGRA.
    session=out.parent/'palette-q3m-p7-ui-measurement-20261002-v1/session.log'
    palettes=[]
    for line in session.read_text(encoding='utf-8').splitlines():
        if 'P7_UI_PALETTE ' not in line or ' colors=' not in line: continue
        value=re.search(r' colors=([0-9A-Fa-f]{2048})\b',line).group(1)
        palette=np.asarray([int(value[n:n+8],16) for n in range(0,2048,8)],dtype='<u4')
        palettes.append(palette)
    successor=np.arange(256,dtype=np.uint16)
    for a,b in [(n,n+11) for n in range(4,88,12)]+[(n,n+7) for n in range(88,256,8)]:
        successor[a:b]=np.arange(a+1,b+1)
    oracle=work/'measured-palettes.oracle'
    with oracle.open('xb') as stream:
        stream.write(struct.pack('<8sI',b'P7ORCL01',len(palettes)))
        for palette in palettes:
            stream.write(palette.tobytes())
            colors=palette.view(np.uint8).reshape(256,4).copy(); colors[0]=0
            for frame in records:
                i,f=frame['I'],frame['F']
                decoded=np.empty((*i.shape,4),np.uint8)
                decoded[:,:,:3]=((colors[i,:3].astype(np.uint16)*(8-f[:,:,None])+
                    colors[successor[i],:3].astype(np.uint16)*f[:,:,None]+4)//8).astype(np.uint8)
                decoded[:,:,3]=colors[i,3]
                stream.write(decoded.tobytes())
    result=dict(schema='bg2-p7-chff2inv-runtime-pack-v1',resref='CHFF2INV',frames=2,scale=2,
        source_sha256=expected,planes=inputs,nn_inferences=0,world_catalog_modified=False,
        pack=dict(path=str(pack.relative_to(ROOT)).replace('\\','/'),sha256=sha(pack),bytes=pack.stat().st_size),
        oracle=dict(path=str(oracle.relative_to(ROOT)).replace('\\','/'),sha256=sha(oracle),
                    palettes=len(palettes),decodes=len(palettes)*2,session_sha256=sha(session), palette_origin='CHFF1INV measured native palettes reused for byte-decoder oracle; CHFF2INV live capture pending'),
        ui_sampler='Nearest',world_filter='Box',ingame_qa=False)
    (out/'pack.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
