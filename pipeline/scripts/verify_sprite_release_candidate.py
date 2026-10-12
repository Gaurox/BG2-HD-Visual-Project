"""Verify a flat, acquired Q3m selection without producing pixels or changing QA."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

from run_creature_sprite_x2 import read_sealed_catalog_index


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def contained(root: Path, relative: str) -> Path:
    path = root / relative
    if path.is_symlink() or path.resolve().relative_to(root).as_posix() != relative:
        raise ValueError(f'Noncanonical sprite path: {relative}')
    return path


def checked_record(root: Path, record: dict) -> Path:
    path = contained(root, record['path'])
    if sha256(path) != record['sha256'].upper():
        raise ValueError(f'Sprite evidence hash differs: {record["path"]}')
    return path


def verify(root: Path, register: dict) -> dict:
    bundle = json.loads((root / 'releases/BG2-HD-Upscale/manifests/renderer-bundle.json').read_text())
    dll = next(f for f in bundle['files'] if f['path'] == 'InfinityEngine-Enhancer.dll')
    renderer = root / 'releases/BG2-HD-Upscale/bg2hd/renderer'
    for f in bundle['files']:
        path = renderer / f['path']
        if path.stat().st_size != f['bytes'] or sha256(path) != f['sha256'].upper():
            raise ValueError(f'Renderer payload differs: {f["path"]}')
    summary = {}
    destinations = set()
    for candidate in register['candidates']:
        if candidate['approval_status'] != 'approved-for-release':
            raise ValueError('Unapproved candidate')
        if candidate['runtime_contract']['dll_sha256'].upper() != dll['sha256'].upper():
            raise ValueError('Candidate uses a different renderer DLL')
        if candidate['runtime_contract']['filter'] != 'Nearest':
            raise ValueError('Q3m release requires Nearest')
        inventory = json.loads(checked_record(root, candidate['source_pack']).read_text())
        for evidence in candidate['qa_approval']['evidence']:
            checked_record(root, evidence)
        if inventory['scale'] != 2 or inventory['display_filter'] != 'Nearest':
            raise ValueError('Invalid inventory scale/filter')
        actual = {}
        versions = set()
        total = 0
        for record in inventory['files']:
            path = contained(root, record['source'])
            if path.stat().st_size != record['bytes'] or sha256(path) != record['sha256'].upper():
                raise ValueError(f'Sprite payload differs: {record["source"]}')
            if record['destination'] in destinations:
                raise ValueError(f'Duplicate destination: {record["destination"]}')
            destinations.add(record['destination'])
            if path.name in actual:
                raise ValueError(f'Duplicate sprite basename: {path.name}')
            actual[path.name] = record
            total += record['bytes']
            if path.suffix == '.registry':
                with path.open('rb') as stream:
                    magic, version, scale = struct.unpack('<8sII', stream.read(16))
                expected_magic = b'IEECSXN\0'
                if magic != expected_magic or scale != 2:
                    raise ValueError(f'Invalid registry header: {path.name}')
                versions.add(version)
        expected_ids = set(candidate['asset_scope']['animation_ids'])
        if candidate['kind'] == 'sprite':
            catalog_record = actual['CreatureSprites-XN.catalog']
            index = read_sealed_catalog_index(root / catalog_record['source'], catalog_record['sha256'])
            ids = {a['animation_id'] for a in index['animations']}
            if ids != expected_ids or set(inventory['animation_ids']) != ids:
                raise ValueError('Catalog animation scope differs from acquired selection')
            required = {'CreatureSprites-XN.catalog'}
            for shard in index['shards']:
                name = Path(shard['registry']).name
                required.add(name)
                record = actual[name]
                if record['sha256'].upper() != shard['sha256'] or record['bytes'] != shard['registry_bytes']:
                    raise ValueError(f'Catalog leaf differs: {name}')
            if set(actual) != required or versions != {6, 7, 9}:
                raise ValueError('Unexpected Q3m leaves/versions')
            families = [e for e in candidate['qa_approval']['evidence'] if e['kind'] == 'family-qa']
            acquired = set()
            for evidence in families:
                decision = json.loads((root / evidence['path']).read_text())
                if decision.get('status') != 'accepted' or decision.get('qa_state') != 'passed':
                    raise ValueError('Family QA is not accepted')
                if set(decision['scope']['animation_ids']) != set(evidence['animation_ids']):
                    raise ValueError('Declared family IDs differ from immutable QA')
                acquired.update(evidence['animation_ids'])
            if len(families) != 15 or acquired != ids:
                raise ValueError('Incomplete acquired family QA coverage')
        else:
            evidence = next(e for e in candidate['qa_approval']['evidence'] if e['kind'] == 'paperdoll-qa')
            decision = json.loads((root / evidence['path']).read_text())
            names = {name.removesuffix('-Q3m-X2.registry') for name in actual}
            if decision['status'] != 'accepted' or decision['qa_state'] != 'passed' or names != set(decision['scope']['resrefs']):
                raise ValueError('Paperdoll scope differs from acquired UI QA')
            if versions != {6} or expected_ids != {'0x6110'}:
                raise ValueError('Unexpected paperdoll version/body scope')
        if len(actual) != candidate['asset_scope']['file_count'] or total != candidate['asset_scope']['bytes']:
            raise ValueError('Sprite inventory totals differ')
        summary[candidate['kind']] = {'files': len(actual), 'bytes': total, 'animation_ids': len(expected_ids), 'versions': sorted(versions)}
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--candidates', type=Path)
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    candidates = args.candidates or root / 'releases/BG2-HD-Upscale/manifests/sprite-release-candidates.json'
    summary = verify(root, json.loads(candidates.read_text(encoding='utf-8-sig')))
    print(json.dumps({'passed': True, 'physical': summary, 'new_ingame_qa': False, 'GPU_production': False}))


if __name__ == '__main__':
    main()
