"""Read-only residual usage audit: native resources + effective overrides, CPU only."""
import csv, hashlib, json, re, struct, sys, time, zlib
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import bg2lib
from workspace_paths import get_path
from export_bam_frames import read_bam,cycle_metadata
from bam_export import decode_bam,native_palette_alpha
import numpy as np
from PIL import Image,ImageDraw

OUT=ROOT/'effects/research/residual-usage-audit-20261109-v2'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
    with (ROOT/p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(raw):return hashlib.sha256(raw).hexdigest().upper()
def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    assert not (OUT/'scan-summary.json').exists();OUT.mkdir(parents=True,exist_ok=True)
    inputs={p:sha((ROOT/p).read_bytes()) for p in ['effects/index/processing.csv','projectiles/index/work-tracking.json','animations/index/animation_upscale_registry.csv','sprite/index/q3m-work-tracking.json']}
    state={r['asset_key'].rsplit(':',1)[-1]:r for r in rows('effects/index/processing.csv')}
    names=sorted(n for n,r in state.items() if r['spatial_state'] in ('not-started','blocked'))
    assert len(names)==67
    assets={r['resref']:r for r in rows('effects/index/bam-assets.csv')}
    pat=re.compile(b'|'.join(re.escape(n.encode()) for n in sorted(names,key=len,reverse=True)))
    types={0x3e9:'WED',0x3ea:'CHU',0x3ed:'ITM',0x3ee:'SPL',0x3ef:'BCS',0x3f0:'IDS',0x3f1:'CRE',0x3f2:'ARE',0x3f3:'DLG',0x3f4:'2DA',0x3f5:'GAM',0x3f6:'STO',0x3f7:'WMP',0x3f8:'EFF',0x3f9:'BS',0x3fa:'CHR',0x3fb:'VVC',0x3fc:'VEF',0x3fd:'PRO',0x3fe:'BIO',0x802:'INI',0x409:'LUA',0x3ff:'WBM'}
    # Resource types are verified by signatures; WBM is excluded from binary scans.
    types.pop(0x3ff)
    refs=defaultdict(list);counts=Counter();scanned_bytes=0;duplicates=[]
    game=get_path('bg2ee_game_root');bifs,entries=bg2lib.load_key();index={(n.upper(),t):l for n,t,l in entries}
    override={p.name.upper():p for p in (game/'override').iterdir() if p.is_file()}
    def scan(raw,owner,typ,origin,effective):
        nonlocal scanned_bytes
        counts[typ]+=1;scanned_bytes+=len(raw)
        for m in pat.finditer(raw.upper()):
            end=m.end();n=m.group().decode().upper()
            # Fixed resrefs need no left boundary (preceding binary field can be ASCII).
            # A right ASCII suffix means this is another resource, not an exact name.
            if len(n)<8 and end<len(raw) and (48<=raw[end]<=57 or 65<=raw[end]<=90 or 97<=raw[end]<=122 or raw[end]==95):continue
            off=m.start();snippet=raw[max(0,off-24):min(len(raw),end+24)]
            refs[n].append(dict(owner=owner,type=typ,offset=off,origin=origin,effective=effective,
                padded_resref=raw[off:off+8]==n.encode().ljust(8,b'\0'),
                context_hex=snippet.hex(),context_ascii=''.join(chr(v) if 32<=v<127 else '.' for v in snippet),
                owner_sha256=sha(raw)))
    grouped=defaultdict(list)
    for n,t,l in entries:
        if t in types:grouped[(l>>20)&0xfff].append((n,t,l))
    for i,(bi,items) in enumerate(grouped.items()):
        # bg2lib.resolve_resource scans the BIF directory per resource (quadratic).
        # Index this archive once, without changing the generic library or game.
        buf=bg2lib.get_bif_buffer(bifs[bi]);assert buf[:4]==b'BIFF'
        count,_,table=struct.unpack_from('<III',buf,8)
        directory={}
        for j in range(count):
            loc,off,size,typ,_=struct.unpack_from('<IIIHH',buf,table+j*16)
            directory[loc&0x3fff]=(off,size)
        for n,t,l in items:
            off,size=directory[l&0x3fff];raw=buf[off:off+size];ext=types[t]
            scan(raw,n.upper(),ext,bifs[bi],(n+'.'+ext).upper() not in override)
        bg2lib._bif_cache.clear()
        if i%10==0:print('native BIF',i+1,'/',len(grouped),'resources',sum(counts.values()),flush=True)
    allowed=set(types.values())|{'LUA','SQL','TXT'}
    for filename,p in override.items():
        typ=p.suffix[1:].upper()
        if typ in allowed:scan(p.read_bytes(),p.stem.upper(),typ,'override/'+p.name,True)
    # Executable literal names and local renderer literals: signals, not proof of all dynamic calls.
    literals=[]
    for p in game.glob('*.exe'):
        raw=p.read_bytes()
        for m in pat.finditer(raw.upper()):
            n=m.group().decode().upper();end=m.end()
            if end<len(raw) and chr(raw[end]).isalnum():continue
            literals.append({'resref':n,'file':p.name,'offset':m.start(),'file_sha256':sha(raw)})
    save('references.json',dict(refs));save('executable-literals.json',literals)
    source_rows=[];sheet=Image.new('RGB',(6*210,12*190),'#252a30');draw=ImageDraw.Draw(sheet)
    for k,n in enumerate(names):
        r=assets[n];p=ROOT/r['extracted_path'];x=(k%6)*210;y=(k//6)*190
        draw.text((x+5,y+5),n,fill='white')
        item={'resref':n,'source_state':r['source_state'],'state':state[n],'references':refs[n]}
        if p.is_file():
            raw=read_bam(p);fs,pal,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr)
            h=hashlib.sha256();h.update(json.dumps(cycle_metadata(raw,len(fs)),sort_keys=True).encode())
            stats=[];best=None;score=-1
            for idx,cx,cy,_ in fs:
                rgba=np.dstack((pal[idx],alpha[idx]));rgba[rgba[:,:,3]==0]=0
                h.update(struct.pack('<IIii',idx.shape[1],idx.shape[0],cx,cy));h.update(rgba.tobytes())
                opaque=rgba[:,:,3]>0;rgb=rgba[:,:,:3][opaque]
                stats.append(dict(size=[idx.shape[1],idx.shape[0]],visible=int(opaque.sum()),
                                  max_rgb=int(rgb.max()) if rgb.size else 0))
                if opaque.sum()>score:best=Image.fromarray(rgba);score=opaque.sum()
            item.update(source_sha256=sha(p.read_bytes()),canonical_sha256=sha(raw),visual_sha256=h.hexdigest().upper(),
                        frames=len(fs),cycles=len(cycle_metadata(raw,len(fs))),frame_statistics=stats)
            if best:
                best.thumbnail((195,150),Image.Resampling.NEAREST);sheet.paste(best,(x+(210-best.width)//2,y+25),best)
            draw.text((x+5,y+174),f'{len(fs)} frames / {item["cycles"]} cycles',fill='#d3d9de')
            item['key_source_present']=(n,0x3e8) in index;item['override_bam_present']=n+'.BAM' in override
        else:draw.text((x+5,y+70),'SOURCE MISSING',fill='#ff9999')
        source_rows.append(item)
    sheet.save(OUT/'native-residual-contact-sheet.png');save('sources.json',source_rows)
    assert inputs=={p:sha((ROOT/p).read_bytes()) for p in inputs}
    save('scan-summary.json',dict(candidate_rows=len(names),resource_counts=dict(counts),scanned_bytes=scanned_bytes,
        native_bif_count=len(grouped),references={n:len(v) for n,v in refs.items()},unchanged_inputs=inputs,
        limitations=['Raw exact-name references require field interpretation; not every hit is an animation call.',
                    'No reference found does not prove absence of generated/hardcoded names.',
                    'No GPU, inference, installation, release or authority writes.']))
    print('DONE',sum(counts.values()),'resources',scanned_bytes,'bytes;',len(source_rows),'sources',flush=True)

if __name__=='__main__':main()
