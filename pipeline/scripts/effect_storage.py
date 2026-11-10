"""Optional exact-registry-bound physical frame indirection for effect packs."""
import hashlib
import struct
import re

NAME='EffectStorage-X4.index'
HEADER=struct.Struct('<8sIIII')
MAGIC=b'IEEFXS1\0'

def validate_layout(registry,frames):
    magic,version,scale,count,reserved=struct.unpack_from('<8sIIII',registry)
    if (magic,scale,reserved)!=(b'IEEEFX4\0',4,0) or version not in (1,2,3):raise ValueError('Invalid logical registry')
    off=24;logical=0
    for _ in range(count):
        ref=registry[off:off+8].rstrip(b'\0').decode('ascii');nf,nc=struct.unpack_from('<II',registry,off+8);off+=16
        if not re.fullmatch(r'[A-Z0-9_]{1,8}',ref):raise ValueError('Unsafe registry resref')
        if not (1<=nf<=4096 and 1<=nc<=256):raise ValueError('Invalid registry counts')
        for i in range(nf):
            w,h=struct.unpack_from('<II',registry,off);off+=8
            if logical>=len(frames):raise ValueError('Missing logical frames')
            f=frames[logical];logical+=1
            expected=f'EFX4-{ref}-frame{i:03d}.rgba'
            if f['asset']!=expected or f.get('logical_size_x1')!=[w,h] or f.get('physical_size_x4')!=[w*4,h*4] or f['bytes']!=w*h*64:
                raise ValueError('Storage manifest frame traversal/dimensions differ from registry')
        for _ in range(nc):
            n,=struct.unpack_from('<I',registry,off);off+=4+4*n
        if version>=2:
            phases,=struct.unpack_from('<I',registry,off+16);off+=20+4*nc*phases
        if version>=3:
            n,=struct.unpack_from('<I',registry,off);off+=4
            for _ in range(n):
                _,length=struct.unpack_from('<II',registry,off);off+=8+4*length
    if off!=len(registry) or logical!=len(frames):raise ValueError('Registry/logical frame inventory differs')

def encode(registry,ids):
    return HEADER.pack(MAGIC,1,len(ids),len(registry),0)+registry+struct.pack(f'<{len(ids)}I',*ids)

def read_map(root,manifest,registry=None):
    frames=manifest['frames'];storage=manifest.get('storage')
    if not storage:
        if (root/NAME).exists():raise ValueError('Undeclared effect storage index')
        return list(range(len(frames)))
    if storage['index']!=NAME or storage.get('version')!=1:raise ValueError('Unsafe storage index name/version')
    raw=(root/NAME).read_bytes();registry=registry if registry is not None else (root/manifest['registry']).read_bytes()
    validate_layout(registry,frames)
    if len(raw)<HEADER.size:raise ValueError('Truncated storage index')
    if len(raw)!=storage['bytes'] or hashlib.sha256(raw).hexdigest().upper()!=storage['sha256']:
        raise ValueError('Storage index hash/size differs')
    if HEADER.unpack_from(raw)!=(MAGIC,1,len(frames),len(registry),0) or raw[24:24+len(registry)]!=registry or len(raw)!=24+len(registry)+len(frames)*4:
        raise ValueError('Storage index registry binding differs')
    ids=list(struct.unpack_from(f'<{len(frames)}I',raw,24+len(registry)))
    for i,j in enumerate(ids):
        if j>=len(ids) or ids[j]!=j:raise ValueError('Noncanonical storage index')
        for key in ('sha256','bytes','physical_size_x4','logical_size_x1'):
            if frames[i].get(key)!=frames[j].get(key):raise ValueError(f'Storage frame identity differs: {i}/{j}/{key}')
    if storage['physical_frame_count']!=len(set(ids)):raise ValueError('Storage physical inventory differs')
    return ids

def physical_frames(root,manifest):
    ids=read_map(root,manifest)
    return [f for i,f in enumerate(manifest['frames']) if ids[i]==i]

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--pack',type=Path,required=True);a=p.parse_args()
    m=json.loads((a.pack/'manifest.json').read_text(encoding='utf-8-sig'));ids=read_map(a.pack,m)
    print(json.dumps(dict(physical_ids=[i for i,j in enumerate(ids) if i==j])))
