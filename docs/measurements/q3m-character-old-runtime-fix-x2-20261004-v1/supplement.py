"""Native Character_old dependencies omitted by body-prefix discovery; scoped V7 delta."""
import hashlib,json,sqlite3,struct,sys,runpy
from collections import Counter
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from run_creature_sprite_x2 import KeyIndex,canonical_bam,bam_cycles,decode_bam,SourceFrame
from analyze_playable_frame_dedup import identities
from palette_q3m_partners import Profile
from q3m_family_witnesses import produce,pack,exclusive
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path

CACHE=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'
OUTPUT=ROOT/'sprite/.work'/HERE.name/'isolated'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def plan():
    game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game);entries=index.resource_map(1000)
    rows=load(ROOT/'docs/measurements/q3m-character-old-full-x2-20261004-v1/selection.json')['witnesses']
    inventory={r['animation_id']:r for r in __import__('csv').DictReader((ROOT/'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig'))}
    # Active native INIs bind WPM to every visible equipment-capable body.
    # Sarevok's WPL is hidden and helmet disabled. No unused WPL family is produced.
    consumers={}
    for row in rows:
        ini=json.loads(inventory[row['animation_id']]['ini_sections_json'])['character_old']
        refs=set()
        if ini.get('shadow','CSHD'):refs.update(r for r in entries if r.startswith(ini.get('shadow','CSHD')))
        if ini.get('equip_helmet')=='1' or ini.get('hide_weapons','0')!='1':
            assert ini['height_code']==ini['height_code_helmet']=='WPM'
            refs.update(r for r in entries if r.startswith('WPM'))
        # Preserve fallback-constructor Sarevok dependencies too, without altering his body.
        if row['animation_id']=='0x6404':refs.update(r for r in entries if r.startswith('SSHD'))
        consumers[row['animation_id']]=sorted(refs)
    refs=sorted({ref for rr in consumers.values() for ref in rr})
    pointer=load(ROOT/'sprite/index/palette-work-plan.json');db=sqlite3.connect(f"file:{(ROOT/pointer['path']).as_posix()}?mode=ro",uri=True)
    fits=np.stack([np.frombuffer(r[0],np.uint8).reshape(256,3) for r in db.execute('SELECT rgb_u8_256x3 FROM profile_palettes ORDER BY palette_ordinal')]);db.close()
    om=runpy.run_path(str(ROOT/'docs/measurements/q3m-monster-contract-x2-20261002-v1/build_contract.py'));oracle=om['NativeFixed']((game/'BaldurReal.exe').read_bytes())
    profiles={};works={};resources=[];sources=[]
    for ref in refs:
        live=game/'override'/(ref+'.bam')
        assert not live.exists(),f'Unexpected native override {ref}'
        raw,source=index.resolve(entries[ref]);bam,_=canonical_bam(raw);decoded,rgb,tr=decode_bam(bam)
        nf,nc=struct.unpack_from('<HB',bam,8);po=struct.unpack_from('<I',bam,16)[0]
        palette=np.frombuffer(bam,np.uint8,1024,po).reshape(256,4).copy();kind=int(ref.startswith('WPM'))
        pk=(kind,palette.tobytes())
        if pk not in profiles:
            fitting=fits if kind else np.stack([oracle.realize(palette,f,t)[:,:3] for _,f,t in om['FITS']])
            profiles[pk]=Profile(kind,palette,fitting)
        profile=profiles[pk];frames=[]
        assert tr==0 and nf==len(decoded)
        for fi,(indices,cx,cy,_) in enumerate(decoded):
            h,w=indices.shape;assert 0<w*h<65535
            if not kind:assert set(np.unique(indices))<={0,1},f'Non-shadow material {ref}'
            inp,src,*_=identities(indices,rgb,tr);key=hashlib.sha256(bytes.fromhex(profile.identity)+src).hexdigest()
            frame=SourceFrame(ref,fi,w,h,cx,cy,tr,indices,rgb,np.dstack((rgb[indices],np.where(indices==0,0,255).astype(np.uint8))).tobytes())
            if key in works:
                old=works[key]['frame'];assert np.array_equal(old.indices,indices) and np.array_equal(old.palette[indices],rgb[indices])
            else:works[key]=dict(frame=frame,profile=profile,input_key=inp.hex(),source_key=src.hex())
            frames.append(dict(key=key,geometry=(w,h,cx,cy,0),frame_index=fi))
        cycles=[c['frame_indices'] for c in bam_cycles(bam)];assert nc==len(cycles)
        aid=next(a for a,rr in consumers.items() if ref in rr)
        witness=dict(animation_id=aid,owner=6,native_kind=kind,family='character_old')
        sha=hashlib.sha256(bam).hexdigest()
        resources.append(dict(witness=witness,resref=ref,source_sha256=sha,frames=frames,cycles=cycles,profile=profile))
        sources.append(dict(resref=ref,source=source,canonical_sha256=sha,frames=nf,cycles=nc,native_kind=kind))
    summary=dict(schema='bg2-character-old-native-dependencies-v1',consumers=consumers,sources=sources,physical_resources=len(resources),physical_frames=sum(len(r['frames']) for r in resources),unique_encoded_work=len(works),prefix_counts=dict(Counter(r[:4] if r.startswith(('CSHD','SSHD')) else r[:3] for r in refs)),SDF=False)
    return resources,works,summary

if __name__=='__main__':
    resources,works,summary=plan();print(json.dumps({k:v for k,v in summary.items() if k not in ('consumers','sources')}),flush=True)
    if len(sys.argv)>1 and sys.argv[1]=='plan':write_json(HERE/'dependencies.json',summary)
    else:
        assert not (HERE/'production.json').exists(),'sealed output requires new run'
        with exclusive(CACHE):
            old={p:file_sha(p) for p in (CACHE/'encoded').rglob('*.npz') if p.stem in works}
            stats,directory=produce(resources,works,CACHE)
            assert all(file_sha(p)==sha for p,sha in old.items())
            result=pack(resources,works,OUTPUT)
        write_json(HERE/'dependencies.json',summary)
        write_json(HERE/'production.json',dict(plan=summary,stats=stats,pack=result,pack_directory=OUTPUT.relative_to(ROOT).as_posix(),acquired_encoded_unchanged=len(old),encoder_namespace=directory.name,SDF=False,ingame_QA=False))
        print(json.dumps(dict(stage='complete',stats=stats,resources=result['resources'],frames=result['frames'])),flush=True)
