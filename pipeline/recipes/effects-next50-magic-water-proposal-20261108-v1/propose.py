"""Select50 unstarted distinct visuals; native animated board only, no production."""
import csv
import hashlib
import importlib.util
import json
import struct
import sys
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bam_export import decode_bam,native_palette_alpha
from export_bam_frames import read_bam,cycle_metadata

OUT=ROOT/'effects/batches/lot50-magic-water-proposal-20261108-v1'
GROUPS={
 'portails-manifestations':'AM3000G AM6200C AM6200D AMDEMGT HARPDISC SPARMOR2 SPDIMDR1 SPDIMDR2 SPMIRROI SPRESURI SPWIRBLA WHIRL01 WHIRLY'.split(),
 'rayons-impacts-protections':'HIHEDGE SHAREAB SPBASEWT SPCCOLDE SPCCWOUI SPCHROMI SPCSPRAI SPENTAXI SPGENHLB SPHLYSMT SPHOLMIG SPHOLYWD SPRWRA2I SPSDIMSP SPSNRAYI SPUNHBLT'.split(),
 'ombres-poussiere-precipitations':'DUST SNOWFAL1 SNOWFAL2 SPSDRABU SPSDRAE2 SPSHADOW TRAVELB'.split(),
 'eau-bulles-ondes':'BUBBLES1 BUBLES FOUNT2 FOUNTN RIPPLE_1 RIPPLE_2 RIPPLE_3 SPLASH WTRBODY2 WTRDROP1'.split(),
 'matieres-toiles':'TRBLOBA TRBLOBB WEBBOMB WEBC'.split(),
}

def rows(p):
    with (ROOT/p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(b):return hashlib.sha256(b).hexdigest().upper()
def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    OUT.mkdir(parents=True,exist_ok=True);assert not (OUT/'batch.json').exists()
    before=sha((ROOT/'effects/index/processing.csv').read_bytes())
    state={r['asset_key'].rsplit(':',1)[-1]:r for r in rows('effects/index/processing.csv')}
    work={r['resref']:r for r in rows('effects/index/work-items.csv')}
    sources={r['resref']:r for r in rows('effects/index/bam-assets.csv')}
    consumers=rows('effects/index/consumers.csv')
    audit={r['resref']:r for r in json.loads((ROOT/'effects/research/remaining183-audit-20261028-v1/audit.json').read_text(encoding='utf-8'))['rows']}
    anim={r['resref']:r for r in rows('animations/index/animation_upscale_registry.csv')}
    completed={a['canonical_sha256'] for n,a in work.items() if state[n]['spatial_state'] not in {'not-started','blocked'}}
    assets=[];duplicates=[];fingerprints=set();tiles=[]
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',14)
    for group,names in GROUPS.items():
        for n in names:
            w=work[n];s=state[n];src=sources[n]
            assert s['spatial_state']=='not-started' and not s['selected_run'],n
            assert w['canonical_sha256'] not in completed and not anim.get(n,{}).get('selected_run'),n
            for domain,other,old_state in audit[n]['visual_matches']:
                if domain=='effects':assert state[other]['spatial_state'] in {'not-started','blocked'},(n,other,'already produced visual')
                elif domain=='animations':assert not anim.get(other,{}).get('selected_run'),(n,other,'selected animation')
            source=ROOT/src['extracted_path'];raw=read_bam(source)
            assert sha(source.read_bytes())==src['source_sha256'].upper() and sha(raw)==w['canonical_sha256'],n
            frames,pal,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr);cycles=cycle_metadata(raw,len(frames))
            l=min(-cx for _,cx,_,_ in frames);t=min(-cy for _,_,cy,_ in frames)
            r=max(idx.shape[1]-cx for idx,cx,_,_ in frames);b=max(idx.shape[0]-cy for idx,_,cy,_ in frames)
            fingerprint=hashlib.sha256();keys=[];scores=[];black=green=graded=covered=0
            for idx,cx,cy,_ in frames:
                rgba=np.dstack((pal[idx],alpha[idx]));rgba[rgba[:,:,3]==0]=0
                fingerprint.update(struct.pack('<IIii',idx.shape[1],idx.shape[0],cx,cy));fingerprint.update(rgba.tobytes())
                canvas=np.zeros((b-t,r-l,4),np.uint8);x,y=-cx-l,-cy-t;canvas[y:y+idx.shape[0],x:x+idx.shape[1]]=rgba
                keys.append(sha(canvas.tobytes()));rgb=pal[idx][alpha[idx]>0].astype(int);covered+=len(rgb)
                scores.append(int(rgb.sum()));black+=int((rgb.max(1)<=8).sum()) if len(rgb) else 0
                green+=int(((rgb[:,0]==0)&(rgb[:,1]==255)&(rgb[:,2]==0)).sum()) if len(rgb) else 0
                graded+=int(((alpha[idx]>0)&(alpha[idx]<255)).sum())
            fingerprint.update(json.dumps(cycles,sort_keys=True,separators=(',',':')).encode());visual=fingerprint.hexdigest().upper()
            assert visual not in fingerprints,(n,'duplicate full RGBA/geometry/cycles in selection');fingerprints.add(visual)
            ca=[]
            for c in cycles:
                kk=[keys[i] for i in c['frame_indices']]
                ca.append(dict(cycle=c['cycle'],native_slots=len(kk),distinct_anchored_rgba=len(set(kk)),repeated_slots=len(kk)-len(set(kk)),constant=bool(kk) and len(set(kk))==1))
            duplicates.append(dict(resref=n,cycles=ca))
            aliases=[nn for nn,ww in work.items() if nn!=n and ww['canonical_sha256']==w['canonical_sha256']]
            owners=[c for c in consumers if c['asset_key'].rsplit(':',1)[-1] in [n]+aliases]
            assets.append(dict(ordinal=len(assets)+1,resref=n,asset_key=w['asset_key'],group=group,source=src['extracted_path'],
                source_sha256=sha(source.read_bytes()),canonical_sha256=sha(raw),strict_visual_sha256=visual,
                reuse_aliases=aliases,source_frames=len(frames),native_cycles=cycles,native_fps=w['native_fps'],playback_hint=w['playback'],
                native_canvas=[r-l,b-t],consumers=owners,usage_evidence='indexed-consumer' if owners else 'unresolved',
                normal_palette_alpha_levels=sorted(map(int,np.unique(alpha))),native_graded_pixels=graded,
                nearblack_covered_percent=round(100*black/max(covered,1),3),exact_green_covered_percent=round(100*green/max(covered,1),3),
                production=s,processing_started=False))
            tile=Image.new('RGB',(256,180),(30,37,49));d=ImageDraw.Draw(tile);d.text((6,5),f'{len(assets):02} {n} {len(frames)}f',font=font,fill='white')
            picks=[]
            for i in sorted(range(len(frames)),key=lambda i:scores[i],reverse=True):
                if all(abs(i-j)>max(1,len(frames)//6) for j in picks):picks.append(i)
                if len(picks)==3:break
            for j,i in enumerate(sorted(picks)):
                idx=frames[i][0];im=Image.fromarray(np.dstack((pal[idx],alpha[idx])));im.thumbnail((80,140),Image.Resampling.NEAREST)
                tile.paste(im,(j*85+(85-im.width)//2,30+(140-im.height)//2),im)
            tiles.append(tile)
    assert len(assets)==50 and len(fingerprints)==50
    summary=dict(distinct_productions=50,covered_resrefs=len({n for a in assets for n in [a['resref']]+a['reuse_aliases']}),
        groups={k:len(v) for k,v in GROUPS.items()},source_frames=sum(a['source_frames'] for a in assets),
        native_cycles=sum(len(a['native_cycles']) for a in assets),playable_cycles=sum(bool(c['frame_indices']) for a in assets for c in a['native_cycles']),
        native_slots=sum(c['native_slots'] for a in duplicates for c in a['cycles']),repeated_slots=sum(c['repeated_slots'] for a in duplicates for c in a['cycles']),
        assets_with_repeats=sum(any(c['repeated_slots'] for c in a['cycles']) for a in duplicates),usage=dict(Counter(a['usage_evidence'] for a in assets)))
    save('batch.json',dict(schema='bg2-effects-batch-proposal-v1',date='2026-11-08',status='proposed-source-only',summary=summary,assets=assets,
        excluded='Previous productions/reuses,DEMB/MSOLG1 characters,fish,trees,static glyphs and architectural map parts.',
        limits=['Not50proven active spells; indexed consumers or unknown usage are recorded per asset.','Native cycles are alternatives, not a concatenated sequence.','No source modification, production, QA, installation or release.']))
    save('native-duplicate-audit.json',dict(summary=summary,assets=duplicates))
    (OUT/'preview').mkdir()
    for page in range(2):
        im=Image.new('RGB',(1280,945),(12,17,25));ImageDraw.Draw(im).text((10,8),f'Nouveau lot50 magie/eau - sources natives - {page+1}/2',font=font,fill='white')
        for i,tile in enumerate(tiles[page*25:(page+1)*25]):im.paste(tile,((i%5)*256,45+(i//5)*180))
        im.save(OUT/f'preview/native-{page+1}.png')
    spec=importlib.util.spec_from_file_location('next50_native_board',ROOT/'pipeline/recipes/effects-lot50-animated-board-20261108-v1/build.py')
    board=importlib.util.module_from_spec(spec);spec.loader.exec_module(board)
    board.PROPOSAL=OUT/'batch.json';board.OUT=OUT/'review';board.__file__=str(Path(__file__))
    board.main()
    assert sha((ROOT/'effects/index/processing.csv').read_bytes())==before
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
