"""Verify acquired map selections and exact final water assemblies for local release."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

def safe_path(root: Path, value: str) -> Path:
    require(bool(value) and '\\' not in value, f'Non-canonical path: {value}')
    path = root / value
    require(not Path(value).is_absolute() and '..' not in Path(value).parts, f'Outside workspace: {value}')
    require(path.resolve().is_relative_to(root.resolve()), f'Outside workspace: {value}')
    for parent in [path, *path.parents]:
        if parent == root:
            break
        require(not parent.is_symlink() and not (parent.exists() and getattr(parent.stat(), 'st_file_attributes', 0) & 0x400), f'Reparse point: {parent}')
    return path

def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()

def verify(root: Path, candidates: Path, assemblies: Path, content: Path | None = None, metadata_only: bool = False) -> dict:
    manifest = read(assemblies)
    require(manifest.get('schema_version') == 1 and manifest.get('state') == 'approved-for-local-release', 'Unapproved map assembly manifest')
    with candidates.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    variants = manifest['variants']
    require(len(rows) == len({r['area'] for r in rows}), 'Duplicate map candidate')
    require(len(variants) == len({v['area'] for v in variants}), 'Duplicate map assembly')
    by = {v['area']: v for v in variants}
    require({r['area'] for r in rows} == set(by), 'Map candidates/assemblies coverage differs')
    with (root/'areas.csv').open(encoding='utf-8-sig', newline='') as stream:
        catalog = {r['area_id']: r for r in csv.DictReader(stream)}
    all_accepted = {r['area_id'] for r in catalog.values() if r['status'] == 'validated-installed'} | {r['area_id']+'N' for r in catalog.values() if r['status_nuit'] == 'validated-installed'}
    require(set(by) | set(manifest['catalog']['shared_tilesets']) == all_accepted, 'Accepted maps missing from explicit selection/shared tileset contract')
    for alias,target in manifest['catalog']['shared_tilesets'].items():
        require(alias not in by and target in by, f'Invalid shared tileset selection: {alias}/{target}')
    liquid = {m['wed']: m for m in read(root/'pipeline/water/ingame-map-tracking-v1.json')['maps'] if m['qa_state'] == 'validated-ingame'}
    require({v['area'] for v in variants if v['water']} == set(liquid), 'Active liquid QA coverage differs')
    animation = read(root/'releases/BG2-HD-Upscale/manifests/animation-release-candidates.json')
    wedges = {c['area']: c['occlusion_contract'] for c in animation['candidates'] if c.get('occlusion_contract') and c['approval_status'] == 'approved-for-release'}
    files_by_area: dict[str, dict] = {}
    destinations: dict[str, str] = {}
    qa_seen: set[str] = set()
    hashes: dict[tuple, str] = {}
    expected_projection: dict[tuple[str, str], dict] = {}
    def checked(path: Path, size: int, sha: str) -> None:
        require(re.fullmatch(r'[A-F0-9]{64}', sha) is not None, f'Invalid SHA: {path}')
        require(path.is_file() and path.stat().st_size == size, f'Missing file/size differs: {path}')
        if not metadata_only:
            st=path.stat();key=(st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
            if key not in hashes:
                hashes[key]=digest(path)
            require(hashes[key] == sha, f'File hash differs: {path}')
    for row in rows:
        area=row['area'];v=by[area]
        require(re.fullmatch(r'(AR|OH)\d{4}N?', area) is not None, f'Invalid area: {area}')
        base=area.removesuffix('N');night=area.endswith('N');c=catalog[base]
        require(v['qa_state']=='acquired' and not v['new_ingame_qa'], f'QA scope differs: {area}')
        require(c['status_nuit' if night else 'status']=='validated-installed', f'Unaccepted catalog map: {area}')
        for key in ('source_path','catalog_source_path','model'):
            require(row[key] == v[key], f'Candidate/assembly {key} differs: {area}')
        require(int(row['component_id'])==v['component_id'] and row['include_wed']==str(v['include_wed']).lower(), f'Candidate identity differs: {area}')
        require(v['source_path'].startswith(f'maps/{base}/runs/'), f'Pack identity differs: {area}')
        require(v['catalog_source_path'].startswith(f'maps/{base}/runs/'), f'Catalog identity differs: {area}')
        run=v['catalog_source_path'].split('/')[3]
        require(run in c['runs_nuit' if night else 'runs'].split(';'), f'Wrong acquired catalog run: {area}')
        if v['water']:
            require(set(liquid[area]['qa_evidence_ids']).issubset({e['id'] for e in v['qa_evidence']}), f'Missing liquid QA: {area}')
        for evidence in v['qa_evidence']:
            if evidence['path'] not in qa_seen:
                p=safe_path(root,evidence['path'])
                # Two retained historical JSON files have CRLF locally and LF in Git.
                # Both exact encodings are pinned; no payload hash is normalized.
                accepted_hashes={evidence['sha256']}
                if evidence.get('git_blob_sha256'):
                    accepted_hashes.add(evidence['git_blob_sha256'])
                require(p.is_file() and digest(p) in accepted_hashes, f'QA evidence differs: {p}')
                qa_seen.add(evidence['path'])
        files={f['name']:f for f in v['files']}
        require(len(files)==len(v['files']) and area+'.TIS' in files, f'Duplicate files or missing base TIS: {area}')
        files_by_area[area]=files
        pack=safe_path(root,v['source_path'])
        expected_names={f['name'] for f in v['files'] if Path(f['source']).parent.as_posix()==v['source_path']}
        actual_names={p.name for p in pack.iterdir() if p.is_file() and p.suffix.upper() in ('.TIS','.PVRZ','.WED') and (v['include_wed'] or p.suffix.upper()!='.WED')}
        require(actual_names==expected_names, f'Undeclared/incomplete map pack: {area}')
        for name,f in files.items():
            require(Path(name).name==name and Path(name).suffix.upper() in ('.TIS','.PVRZ','.WED'), f'Unsafe map filename: {name}')
            p=safe_path(root,f['source']);checked(p,f['bytes'],f['sha256'])
            if p.parent != pack:
                w=wedges.get(area)
                require(w is not None and f['source']==w['source'] and f['sha256']==w['sha256'] and name==area+'.WED', f'Undeclared external WED/source: {area}/{name}')
            require(name.upper() not in destinations, f'Cross-map destination collision: {name}')
            destinations[name.upper()]=area
            expected_projection[(area,f['source'])]={'component_id':v['component_id'],'sha256':f['sha256'],'bytes':f['bytes'],'destination':'override/'+name,'payload_group':'map-'+base.lower()}
    runtime=manifest['runtime'];registry_path=safe_path(root,runtime['registry'])
    require(digest(registry_path)==runtime['registry_sha256'], 'Runtime registry changed')
    registry=read(registry_path)
    require(len(registry['entries'])==runtime['entries'] and {e['wed']['resref'] for e in registry['entries']}==set(liquid), 'Runtime identities/QA differ')
    for e in registry['entries']:
        fs=files_by_area[e['wed']['resref']];o=e['overlay'];b=e['base_tis']
        required=[(e['wed']['resref']+'.WED',e['wed']['sha256']),(b['resref']+'.TIS',b['sha256']),(o['tis_resref']+'.TIS',o['tis_sha256'])]
        required += [(p['resref']+'.PVRZ',p['sha256']) for p in o['pages']+b.get('pages',[])]
        for name,sha in required:
            require(name in fs and fs[name]['sha256']==sha.upper(), f'Runtime guard/overlay absent or differs: {e["wed"]["resref"]}/{name}')
    dll=root/'releases/BG2-HD-Upscale/bg2hd/renderer/InfinityEngine-Enhancer.dll'
    require(digest(dll)==runtime['dll_sha256'], 'Accepted renderer DLL changed')
    config=read(root/'releases/BG2-HD-Upscale/manifests/runtime-compatibility.json')['owned_ini_keys']['core-steam']['Shaders']
    require(all(config.get(k)==v for k,v in runtime['owned_ini_keys'].items()), 'Installer water activation/strength differs from validated configuration')
    if content:
        actual={(e['area'],e['source']):e for e in read(content)['entries'] if e['kind']=='map'}
        require(len(actual)==len([e for e in read(content)['entries'] if e['kind']=='map']), 'Duplicate map content entries')
        require(set(actual)==set(expected_projection), 'Map content projection incomplete or contains extra files')
        for key,expected in expected_projection.items():
            require(all(actual[key][k]==v for k,v in expected.items()), f'Map content projection differs: {key}')
    return {'valid':True,'variants':len(by),'liquid_weds':len(liquid),'files':len(expected_projection),'qa_evidence':len(qa_seen),'runtime_entries':len(registry['entries']),'physical_hashes_verified':not metadata_only}

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root', type=Path, default=ROOT)
    parser.add_argument('--candidates', type=Path)
    parser.add_argument('--assemblies', type=Path)
    parser.add_argument('--content', type=Path)
    parser.add_argument('--metadata-only', action='store_true', help='Projection check after compiler physical hashing; staging still rehashes sources.')
    args=parser.parse_args();root=args.workspace_root.resolve();release=root/'releases/BG2-HD-Upscale'
    try:
        result=verify(root,args.candidates or release/'manifests/map-release-candidates.csv',args.assemblies or release/'manifests/map-release-assemblies.json',args.content,args.metadata_only)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'valid':False,'error':str(exc)}));return 1
    print(json.dumps(result,sort_keys=True));return 0

if __name__=='__main__':
    raise SystemExit(main())
