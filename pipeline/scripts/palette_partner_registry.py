"""IEECSXN V7/V8 x2: native Q3m partners, optional V8 contour coverage."""
from __future__ import annotations
import hashlib
from pathlib import Path
import re
import struct
import zlib
import numpy as np
import palette_registry as v6
import run_creature_sprite_x2 as registry
from palette_q3m_partners import Profile, RULE, PROFILE_BYTES

VERSION = 7
CONTOUR_VERSION = 8
SDF_VERSION = 9
from sprite_sdf_registry import validate as validate_sdf


def require(ok, message):
    if not ok: raise ValueError('V7 ' + message)


def native_empty(ref, version, kind, w, h):
    return (w,h) == (0,0) and version == VERSION and kind == 0 and ref in ('MWYVG22','MWYVG23','MWYVG24','MTANG21E')


def write(path, resources, profile, *, compress=True, version=VERSION):
    path = Path(path); temporary = path.with_suffix(path.suffix+'.part')
    require(not path.exists() and not temporary.exists(), 'fresh leaf destination required')
    require(1 <= len(resources) <= registry.MAX_RESOURCES, 'resource count')
    require(version in (VERSION, CONTOUR_VERSION, SDF_VERSION), 'version')
    try:
        with temporary.open('xb') as output, v6._Codec(compress=True) as codec:
            output.write(struct.pack('<8s6I', registry.XN_REGISTRY_MAGIC, version, 2, len(resources), 0xffff, profile.id, RULE))
            seen = set()
            for resource in resources:
                ref = resource['resref']; require(re.fullmatch(r'[A-Z0-9_]{1,8}', ref) and ref not in seen, 'resref')
                seen.add(ref); frames, cycles = resource['frames'], resource['cycles']
                require(1 <= len(frames) <= registry.MAX_FRAMES_PER_RESOURCE and 1 <= len(cycles) <= registry.MAX_CYCLES_PER_RESOURCE, 'counts')
                source = bytes.fromhex(resource['source_sha256']); require(len(source) == 32, 'source SHA256')
                output.write(struct.pack('<8s32sII', ref.encode().ljust(8,b'\0'), source, len(frames), len(cycles)))
                output.write(profile.metadata())
                for frame in frames:
                    w,h,cx,cy,tr = frame['geometry']; i, code = frame['I'], frame['F']
                    empty = native_empty(ref,version,profile.kind,w,h)
                    require(((0 < w <= 65535 and 0 < h <= 65535) or empty) and tr == 0 and -32768 <= cx < 32768 and -32768 <= cy < 32768, 'geometry')
                    require(i.shape == (h*2,w*2), 'physical x2 extent')
                    if empty:
                        require(i.dtype == code.dtype == np.uint8 and i.shape == code.shape == frame['guide'].shape == (0,0) and frame['dep'].dtype == np.uint8 and frame['dep'].shape == (32,) and not np.any(frame['dep']), 'empty planes/dependencies')
                    else:profile.validate(i, code, frame['guide'], frame['dep'])
                    reps = np.asarray(frame['representatives'], dtype=np.uint16)
                    require(reps.shape == (256,) and np.all((reps == 0xffff) | (reps < w*h)), 'representatives')
                    coverage = frame.get('A')
                    require(coverage is None or version == CONTOUR_VERSION, 'coverage requires V8')
                    if coverage is not None:
                        require(coverage.dtype == np.uint8 and coverage.shape == i.shape, 'coverage extent/type')
                        require(np.all(coverage[profile.classes[i] < (3 if profile.kind == 0 else 4)] == 255), 'coverage changes a special class')
                    sdf,material=frame.get('S'),frame.get('M')
                    if version==SDF_VERSION:
                        require(profile.kind in (0,1), 'V9 native palette kind')
                        validate_sdf(i,sdf,material)
                    else:require(sdf is None and material is None,'SDF requires V9')
                    alpha_present = coverage is not None and bool(np.any(coverage != 255))
                    present = bool(np.any(code)); require(i.size*(1+present) <= registry.MAX_LAZY_FRAME_INDEX_BYTES, 'frame bound')
                    stored, codecs = [], []
                    for plane in (i.tobytes(), code.tobytes() if present else b'', coverage.tobytes() if alpha_present else b'', sdf.tobytes() if version==SDF_VERSION else b'', material.tobytes() if version==SDF_VERSION else b''):
                        zipped = codec.encode(plane) if compress and plane else plane
                        use = len(zipped) < len(plane); stored.append(zipped if use else plane); codecs.append(int(use))
                    output.write(v6.FRAME.pack(w,h,cx,cy,tr,codecs[0],int(present),2 if version==SDF_VERSION else int(alpha_present),len(stored[0]),*reps.tolist(),frame['dep'].tobytes(),len(stored[1]),codecs[1]))
                    if version == CONTOUR_VERSION: output.write(struct.pack('<IB3x',len(stored[2]),codecs[2]))
                    if version==SDF_VERSION:
                        for k in (3,4):output.write(struct.pack('<IB3x',len(stored[k]),codecs[k]))
                    output.write(stored[0]); output.write(stored[1])
                    if version == CONTOUR_VERSION: output.write(stored[2])
                    if version==SDF_VERSION:output.write(stored[3]);output.write(stored[4])
                for cycle in cycles:
                    require(len(cycle) <= registry.MAX_CYCLE_SLOTS and all(0 <= v <= 0xffff for v in cycle), 'native u16 cycle lookup')
                    output.write(struct.pack('<I',len(cycle))); output.write(struct.pack(f'<{len(cycle)}I',*cycle))
        require(temporary.stat().st_size <= registry.maximum_registry_bytes(2), 'leaf bound')
        info = inspect(temporary); temporary.replace(path); return info
    except BaseException:
        if temporary.exists(): temporary.unlink()
        raise


def inspect(path, *, include_frames=False):
    path = Path(path); size = path.stat().st_size
    require(32 < size <= registry.maximum_registry_bytes(2), 'file size')
    raw = path.read_bytes(); pos = 0
    def take(n):
        nonlocal pos
        require(0 <= n <= len(raw)-pos, 'truncated input'); data = raw[pos:pos+n]; pos += n; return data
    magic, version, scale, count, animation, pid, rule = struct.unpack('<8s6I',take(32))
    require(magic == registry.XN_REGISTRY_MAGIC and version in (VERSION,CONTOUR_VERSION,SDF_VERSION) and scale == 2 and animation == 0xffff and pid in (8,9) and rule == RULE and 1 <= count <= registry.MAX_RESOURCES, 'header')
    resources, frames_total, indices_total, coverage_total, sdf_total = [], 0, 0, 0, 0
    with v6._Codec(compress=False) as decoder:
        for _ in range(count):
            header = take(48); name = header[:8].split(b'\0')[0]
            require(re.fullmatch(rb'[A-Z0-9_]{1,8}',name) and header[:8] == name.ljust(8,b'\0'), 'resource name')
            ref = name.decode(); require(ref not in [r['resref'] for r in resources], 'duplicate resource')
            nf,nc = struct.unpack_from('<II',header,40)
            require(1 <= nf <= registry.MAX_FRAMES_PER_RESOURCE and 1 <= nc <= registry.MAX_CYCLES_PER_RESOURCE, 'resource counts')
            metadata = take(PROFILE_BYTES); kind = struct.unpack_from('<I',metadata)[0]
            profile = Profile(kind, np.frombuffer(metadata,np.uint8,1024,4).reshape(256,4), np.zeros((6,256,3),np.uint8), np.frombuffer(metadata,np.uint8,1024,1028).reshape(256,4))
            require(profile.id == pid, 'resource palette kind/profile differs')
            frames = []
            for _ in range(nf):
                h = take(v6.FRAME_BYTES); w,he,cx,cy,tr,ic,flags,res,si = struct.unpack_from('<HHhhBBBBI',h)
                sf,fc = struct.unpack_from('<IB',h,560); n = w*he*4
                empty = native_empty(ref,version,kind,w,he)
                require(((w > 0 and he > 0) or empty) and tr == 0 and flags in (0,1) and res in ((2,) if version==SDF_VERSION else ((0,1) if version==CONTOUR_VERSION else (0,))) and h[565:568] == bytes(3) and n*(1+flags) <= registry.MAX_LAZY_FRAME_INDEX_BYTES, 'frame header')
                if empty:require(ic == flags == si == sf == fc == 0 and h[528:560] == bytes(32), 'empty storage/dependencies')
                sa,ac = 0,0
                if version == CONTOUR_VERSION:
                    ah=take(8);sa,ac=struct.unpack_from('<IB',ah)
                    require(ah[5:]==bytes(3) and (res or (sa==0 and ac==0)), 'coverage header')
                sdf_headers=[];sn=(w*2+12)*(he*2+12)
                if version==SDF_VERSION:
                    require(kind in (0,1),'V9 native kind')
                    for length in (sn,sn*4):
                        sh=take(8);sz,sc=struct.unpack_from('<IB',sh)
                        require(sh[5:]==bytes(3) and ((sc==0 and sz==length) or (sc==1 and 0<sz<length)),'SDF header')
                        sdf_headers.append((sz,sc,length))
                    sdf_total+=sn*5
                    require(sdf_total<=registry.MAX_LAZY_FRAME_INDEX_BYTES,'resident SDF limit')
                reps = np.frombuffer(h,'<u2',256,16); require(np.all((reps == 0xffff) | (reps < w*he)), 'representatives')
                ip = v6._decode_plane(ic,take(si),n,decoder)
                if flags: fp = v6._decode_plane(fc,take(sf),n,decoder)
                else: require(sf == 0 and fc == 0, 'absent blend storage'); fp = bytes(n)
                i = np.frombuffer(ip,np.uint8).reshape(he*2,w*2); f = np.frombuffer(fp,np.uint8).reshape(i.shape)
                if not empty:profile.validate(i,f,dep=np.frombuffer(h,np.uint8,32,528))
                if version==CONTOUR_VERSION:
                    a=np.frombuffer(v6._decode_plane(ac,take(sa),n,decoder),np.uint8).reshape(i.shape) if res else np.full(i.shape,255,np.uint8)
                    require(np.all(a[profile.classes[i] < (3 if kind==0 else 4)]==255), 'coverage changes a special class')
                if version==SDF_VERSION:
                    sp=[]
                    for sz,sc,length in sdf_headers:sp.append(v6._decode_plane(sc,take(sz),length,decoder))
                    s=np.frombuffer(sp[0],np.uint8).reshape(he*2+12,w*2+12)
                    m=np.frombuffer(sp[1],'<u4').reshape(s.shape)
                    validate_sdf(i,s,m)
                coverage_total += n if version==CONTOUR_VERSION and res else 0
                require(coverage_total <= registry.MAX_LAZY_FRAME_INDEX_BYTES, 'resident coverage limit')
                frames_total += 1; indices_total += n
                require(indices_total <= registry.maximum_registry_bytes(2), 'decoded index limit')
                if include_frames:
                    frame=dict(geometry=(w,he,cx,cy,tr),I=i.copy(),F=f.copy(),dep=h[528:560],representatives=reps.copy())
                    if version==CONTOUR_VERSION:frame['A']=a.copy()
                    if version==SDF_VERSION:frame['S']=s.copy();frame['M']=m.copy()
                    frames.append(frame)
            cycles = []
            for _ in range(nc):
                slots = struct.unpack('<I',take(4))[0]; require(slots <= registry.MAX_CYCLE_SLOTS, 'cycle bound')
                values = list(struct.unpack(f'<{slots}I',take(slots*4)))
                require(all(v <= 0xffff for v in values), 'native u16 cycle lookup')
                cycles.append(values)
            resources.append(dict(resref=ref,source_sha256=header[8:40].hex(),frame_count=nf,cycle_count=nc,profile=profile,frames=frames,cycles=cycles))
    require(pos == len(raw), 'trailing bytes')
    info = dict(version=version,scale=2,registry_magic='IEECSXN',animation_id='0xFFFF',sha256=hashlib.sha256(raw).hexdigest().upper(),crc32=zlib.crc32(raw)&0xffffffff,resource_count=count,frame_count=frames_total,index_bytes=indices_total,registry_bytes=size,class_profile_id=pid,decode_rule_id=rule)
    if version==CONTOUR_VERSION:info['coverage_bytes']=coverage_total
    if version==SDF_VERSION:info['sdf_bytes']=sdf_total
    if include_frames: info['resources'] = resources
    return info
