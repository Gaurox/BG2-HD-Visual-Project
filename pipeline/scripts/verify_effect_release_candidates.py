"""Verify effect candidate selection, native routes and exact content projection."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from effect_storage import physical_frames,NAME as STORAGE_NAME


def v3_records(raw):
    magic,version,scale,count,reserved=struct.unpack_from('<8sIIII',raw)
    assert (magic,version,scale,reserved)==(b'IEEEFX4\0',3,4,0)
    off=24;result={}
    for _ in range(count):
        start=off;name=raw[off:off+8].rstrip(b'\0').decode()
        nf,nc=struct.unpack_from('<II',raw,off+8);off+=16+8*nf
        for _ in range(nc):
            n,=struct.unpack_from('<I',raw,off);off+=4+4*n
        phases,=struct.unpack_from('<I',raw,off+16);off+=20+4*nc*phases
        n,=struct.unpack_from('<I',raw,off);off+=4
        for _ in range(n):
            _,length=struct.unpack_from('<II',raw,off);off+=8+4*length
        assert name not in result
        result[name]=raw[start:off]
    assert off==len(raw)
    return result


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify_crop(pack_root, pack, crop, frames, manifest_hash, check, root):
    assert crop['format'] == 'IEECROP2'
    logical_count = len(pack['frames'])
    assert crop['physical_frame_count'] == len(frames)
    files = {f['name']: f for f in crop['files']}
    assert len(crop['files']) == 2 and files.keys() == {'EffectCrops-X4.index', 'EffectCrops-X4.rgba'}
    index_path = check(dict(files['EffectCrops-X4.index'], path=(pack_root/'EffectCrops-X4.index').relative_to(root).as_posix()))
    check(dict(files['EffectCrops-X4.rgba'], path=(pack_root/'EffectCrops-X4.rgba').relative_to(root).as_posix()))
    index = index_path.read_bytes()
    header = struct.Struct('<8sII32s32s')
    record = struct.Struct('<I6HQ')
    storage_hash = (bytes.fromhex(pack['storage']['sha256']) if pack.get('storage')
                    else hashlib.sha256(b'').digest())
    assert header.unpack_from(index) == (b'IEECROP2', len(frames), logical_count,
                                         bytes.fromhex(pack['registry_sha256']), storage_hash)
    logical_ids = {f['asset']: i for i, f in enumerate(pack['frames'])}
    offset = 0
    for frame, row in zip(frames, record.iter_unpack(index[header.size:]), strict=True):
        canonical, width, height, x, y, w, h, start = row
        assert canonical == logical_ids[frame['asset']] and [width, height] == frame['physical_size_x4']
        assert start == offset and x+w <= width and y+h <= height
        assert (w and h) or not any((x, y, w, h))
        offset += w*h*4
    assert offset == files['EffectCrops-X4.rgba']['bytes']
    proof = load(check(crop['reconstruction_evidence']))
    assert proof['logical_frames_verified'] == logical_count and proof['physical_frames_byte_exact'] == len(frames)
    for name in (pack['registry'], 'manifest.json', *files, *([STORAGE_NAME] if pack.get('storage') else [])):
        assert proof['files'][name]['bytes'] == (pack_root/name).stat().st_size
        expected_hash = files[name]['sha256'] if name in files else (
            pack['registry_sha256'] if name == pack['registry'] else
            pack['storage']['sha256'] if name == STORAGE_NAME else manifest_hash)
        assert proof['files'][name]['sha256'].upper() == expected_hash.upper()
    return crop['files']


def verify(root, content_path=None):
    release = root/'releases/BG2-HD-Upscale'
    candidates = load(release/'manifests/effect-release-candidates.json')['candidates']
    renderer = load(release/'manifests/renderer-bundle.json')
    dll = next(f for f in renderer['files'] if f['path']=='InfinityEngine-Enhancer.dll')
    expected = {}
    selected_names = set()
    def check(e):
        path=(root/e['path']).resolve()
        assert path.is_relative_to(root.resolve()), path
        if 'bytes' in e: assert path.stat().st_size==e['bytes'], path
        with path.open('rb') as stream:
            assert hashlib.file_digest(stream,'sha256').hexdigest().upper()==e['sha256'].upper(),path
        return path
    for c in candidates:
        if c['approval_status']!='approved-for-release': continue
        mp=root/c['runtime_pack']['path']/c['runtime_pack']['manifest']
        check(dict(path=mp.relative_to(root).as_posix(),sha256=c['runtime_pack']['manifest_sha256']))
        pack=load(mp)
        refs={r['resref'] for r in pack['resources']}
        assert len(refs)==pack['resource_count']
        proof=None
        if 'integration_evidence' in c:
            proof=load(check(c['integration_evidence']))
            assert proof['runtime_resources']==len(refs)
            assert proof['runtime_backings']==len(pack['frames'])
            assert proof['runtime_files']==c['runtime_files']
            assert renderer['bundle_id']==c['renderer_contract']['bundle_id']
            assert dll['sha256']==c['renderer_contract']['dll_sha256']
            assert not refs.intersection(proof['excluded_comparison_runtime_refs'])
            origin=pack['source_packs'][0]
            origin_path=check(dict(path=origin['path']+'/manifest.json',sha256=origin['manifest_sha256']))
            source_pack=load(origin_path)
            source_resources={r['resref']:r for r in source_pack['resources']}
            source_frames={(f['resref'],f['resource_frame']):f for f in source_pack['frames']}
            source_registry=check(dict(path=origin['path']+'/'+source_pack['registry'],sha256=source_pack['registry_sha256'])).read_bytes()
            source_records=v3_records(source_registry)
            mapping={r['resref']:r['release_source_runtime_ref'] for r in pack['resources']}
            for r in pack['resources']:
                original=source_resources[mapping[r['resref']]]
                cleaned={k:v for k,v in r.items() if k not in ('resref','release_source_runtime_ref')}
                assert cleaned=={k:v for k,v in original.items() if k!='resref'},r['resref']
            for f in pack['frames']:
                original=source_frames[mapping[f['resref']],f['resource_frame']]
                for key in ('sha256','bytes','logical_size_x1','physical_size_x4'):
                    assert f[key]==original[key],(f['asset'],key)
            expected_registry=struct.pack('<8sIIII',b'IEEEFX4\0',3,4,len(refs),0)+b''.join(
                r['resref'].encode().ljust(8,b'\0')+source_records[mapping[r['resref']]][8:] for r in pack['resources'])
            assert hashlib.sha256(expected_registry).hexdigest().upper()==pack['registry_sha256'],'Changed effect clock/geometry/cycle records'
        selection_by_name={s['resref']:s for s in proof['selected_assets']} if proof else {}
        for r in c['resources']:
            check(dict(path=r['qa_evidence'],sha256=r['qa_evidence_sha256']))
            assert r['resref'] not in selected_names
            selected_names.add(r['resref'])
            if proof:
                bound=selection_by_name.pop(r['resref'])
                selected=load(check(bound['selection']))
                assert selected['mode']=='x4'
                assert selected['selected_run']==r['selected_run']==bound['selected_run']
                assert selected['qa_evidence']['sha256']==r['qa_evidence_sha256']==bound['qa_evidence']['sha256']
                assert bound['release_runtime_ref'] in refs
        assert not selection_by_name
        if proof:
            current={p.stem for p in (root/'effects/index/selections').glob('*.json') if load(p)['mode']=='x4'}
            assert selected_names==current, 'Accepted effects missing from release'
            routes=load(check(proof['native_pro_routes']))
            check(proof['projectile_closure']);check(proof['cow_qa'])
            native_files={f['destination']:f for f in c['runtime_files']}
            for route in routes:
                assert route['runtime_bam'] in refs
                if route['patched']:
                    f=native_files['override/'+route['owner']+'.pro']
                    raw=bytearray((root/f['source']).read_bytes())
                    assert raw[0x104:0x10c].rstrip(b'\0').decode().upper()==route['runtime_bam']
                    original_ref=route['palette_job'].rsplit('-p',1)[0]
                    raw[0x104:0x10c]=original_ref.encode().ljust(8,b'\0')
                    assert hashlib.sha256(raw).hexdigest().upper()==route['source_sha256'],'PRO changed beyond BAM reference'
        files=[dict(name=c['runtime_pack']['manifest'],bytes=mp.stat().st_size,sha256=c['runtime_pack']['manifest_sha256']),
               dict(name=pack['registry'],bytes=pack['registry_bytes'],sha256=pack['registry_sha256'])]
        frames = physical_frames(mp.parent, pack)
        crop = c['runtime_pack'].get('crop')
        if crop:
            files += verify_crop(mp.parent, pack, crop, frames, c['runtime_pack']['manifest_sha256'], check, root)
        else:
            files += [dict(name=f['asset'],bytes=f['bytes'],sha256=f['sha256']) for f in frames]
        if pack.get('storage'):
            st=pack['storage'];check(dict(path=(mp.parent/STORAGE_NAME).relative_to(root).as_posix(),bytes=st['bytes'],sha256=st['sha256']))
            files.append(dict(name=STORAGE_NAME,bytes=st['bytes'],sha256=st['sha256']))
        for f in files:
            dest='iee-assets/effects/'+f['name']
            assert dest not in expected
            expected[dest]=dict(source=(mp.parent/f['name']).relative_to(root).as_posix(),bytes=f['bytes'],sha256=f['sha256'],component_id=c['component_id'],payload_group=c['payload_group'])
        for f in c.get('runtime_files',[]):
            assert f['destination'] not in expected
            check(dict(path=f['source'],bytes=f['bytes'],sha256=f['sha256']))
            expected[f['destination']]=dict(source=f['source'],bytes=f['bytes'],sha256=f['sha256'],component_id=c['component_id'],payload_group=c['payload_group'])
            raw=(root/f['source']).read_bytes()
            assert raw[:8] in (b'BAM V1  ',b'BAMC V1 ',b'VVC V1.0',b'PRO V1.0'),f['source']
            if f['destination'].endswith('.vvc'):
                assert raw[8:16].rstrip(b'\0').decode().upper() in refs
            elif f['destination'].endswith('.pro'):
                assert raw[0x104:0x10c].rstrip(b'\0').decode().upper() in refs
    if content_path:
        entries=[e for e in load(content_path)['entries'] if e['kind']=='effect']
        actual={e['destination']:e for e in entries}
        assert len(actual)==len(entries)==len(expected),'Incomplete/duplicate effect content projection'
        for dest,wanted in expected.items():
            entry=actual[dest]
            for key,value in wanted.items(): assert entry[key]==value,(dest,key)
        destination_counts=Counter(e['destination'] for e in load(content_path)['entries'])
        for dest in expected:
            assert destination_counts[dest]==1,('Effect destination collision',dest)
    return dict(status='passed',accepted_effects=len(selected_names),projected_files=len(expected),content_verified=bool(content_path))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--content',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.workspace_root,args.content),indent=2))
