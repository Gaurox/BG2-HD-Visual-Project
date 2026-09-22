"""Assemble isolated liquid-family candidates; never install or change game files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_new(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def record(path: Path):
    return {'present': path.is_file(), 'sha256': digest(path) if path.is_file() else None,
            'bytes': path.stat().st_size if path.is_file() else None}


def pages(tis: Path):
    data = tis.read_bytes()
    if data[:8] != b'TIS V1  ':
        raise ValueError(f'Invalid TIS: {tis}')
    count, size, offset, dimension = struct.unpack_from('<4I', data, 8)
    if len(data) != offset + count * size:
        raise ValueError(f'TIS length mismatch: {tis}')
    if size != 12 and dimension == 256:
        raise ValueError(f'x4 trial requires PVRZ TIS entries: {tis}')
    if size != 12:
        return [], dimension, count
    prefix = tis.stem[0] + tis.stem[2:]
    result = sorted({struct.unpack_from('<I', data, offset + i * 12)[0]
                     for i in range(count)} - {0xFFFFFFFF})
    return [f'{prefix}{page:02d}.PVRZ' for page in result], dimension, count


def scope_names(request, override: Path):
    names = set()
    for target in request['targets']:
        area = target['wed']
        names.update([area + '.WED', area + '.TIS'])
        page_names, dimension, _ = pages(override / (area + '.TIS'))
        if dimension != 256:
            raise ValueError(f'{area}: installed base is not x4')
        names.update(page_names)
    return names


def protected_names(request, override: Path):
    names = {'fpSEAM.glsl', 'fpTone.glsl'}
    for target in request['targets']:
        for slot in target['slots']:
            for resref in (slot['source'], slot['source'] + 'R'):
                name = resref + '.TIS'
                names.add(name)
                if (override / name).is_file():
                    names.update(pages(override / name)[0])
    return names


def snapshot(run: Path, game: Path, request):
    override = game / 'override'
    names = scope_names(request, override)
    protected = protected_names(request, override)
    aliases = {slot[key] for target in request['targets'] for slot in target['slots']
               for key in ('alias', 'rain_alias')}
    for alias in aliases:
        prefix = alias[0] + alias[2:]
        if (override / (alias + '.TIS')).exists() or any(override.glob(prefix + '*.PVRZ')):
            raise ValueError(f'Alias already used: {alias}')
    value = {'schema': 'bg2-liquid-trial-live-before-v1',
             'created_utc': datetime.now(timezone.utc).isoformat(),
             'game_root': str(game), 'request_sha256': digest(run / 'request.json'),
             'files': {name: record(override / name) for name in sorted(names)},
             'protected_override': {name: record(override / name) for name in sorted(protected)},
             'protected_runtime': {name: record(game / name) for name in
                                   ('InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini')}}
    write_new(run / 'live-before.json', value)
    print(f'Snapshot: {len(names)} scoped files; {len(protected)} protected resources', flush=True)


def verify_before(run: Path, game: Path, candidate_name='override-candidate'):
    before = read(run / 'live-before.json')
    if before['request_sha256'] != digest(run / 'request.json'):
        raise ValueError('Request changed after snapshot')
    for section, folder in [('files', game / 'override'),
                            ('protected_override', game / 'override'),
                            ('protected_runtime', game)]:
        for name, expected in before[section].items():
            if record(folder / name) != expected:
                raise ValueError(f'Live drift before installation: {name}')
    manifest_path = run / candidate_name / 'manifest.json'
    if manifest_path.is_file():
        for name in read(manifest_path)['files']:
            if name not in before['files'] and (game / 'override' / name).exists():
                raise ValueError(f'New resource appeared before installation: {name}')
    return before


def unique_asset(directory: Path, name: str):
    matches = [p for p in directory.rglob(name) if p.is_file()]
    if not matches:
        raise FileNotFoundError(name)
    if len({digest(p) for p in matches}) != 1:
        raise ValueError(f'Ambiguous generated asset: {name}')
    return matches[0]


def assemble(run: Path, game: Path, vanilla: Path, request, bases_root: Path, overlays_root: Path,
             candidate_name: str):
    import bg2lib
    from water_wed import replace_overlay_resref, validate_polygons
    bg2lib.KEY_PATH = str(game / 'chitin.key')
    _, game_resources = bg2lib.load_key()
    game_names = {n.upper() for n, _, _ in game_resources}
    bg2lib.GAME_DIR = str(vanilla)
    bg2lib.KEY_PATH = str(vanilla / 'chitin.key')
    bg2lib._bif_cache.clear()
    bifs, resources = bg2lib.load_key()
    index = {(n.upper(), kind): locator for n, kind, locator in resources}
    reserved_names = game_names | {n.upper() for n, _, _ in resources}
    alias_names = []
    for target in request['targets']:
        for slot in target['slots']:
            for key in ('alias', 'rain_alias'):
                alias = slot[key].upper()
                alias_names.extend([alias + '.TIS', alias[0] + alias[2:] + '00.PVRZ'])
    if len(alias_names) != len(set(alias_names)):
        raise ValueError('Duplicate alias or generated page namespace')
    if any(Path(name).stem in reserved_names for name in alias_names):
        raise ValueError('Alias collides with an archived game/vanilla resource')
    before = verify_before(run, game, candidate_name)
    candidate = run / candidate_name
    candidate.mkdir(exist_ok=False)
    files = {}
    report = []

    def add(source: Path, area: str, kind: str):
        name = source.name
        if name in files:
            raise ValueError(f'Duplicate target: {name}')
        if name not in before['files'] and source.stem.upper() in reserved_names:
            raise ValueError(f'New resource collides with archived game/vanilla asset: {name}')
        target = candidate / name
        shutil.copy2(source, target)
        files[name] = {'bytes': target.stat().st_size, 'sha256': digest(target)}
        report.append({'name': name, 'area': area, 'kind': kind,
                       'source': source.relative_to(ROOT).as_posix(),
                       'before': record(game / 'override' / name), **files[name]})

    for target in request['targets']:
        area = target['wed']
        base = bases_root / 'maps' / area
        base_tis = base / (area + '.TIS')
        page_names, dimension, _ = pages(base_tis)
        if dimension != 256:
            raise ValueError(f'Base candidate is not x4: {area}')
        for name in [area + '.TIS', *page_names]:
            source = base / name
            previous = before['files'].get(name)
            if previous is None:
                prefix = area[0] + area[2:]
                page_suffix = source.stem[len(prefix):]
                if (source.suffix.upper() != '.PVRZ' or not source.stem.startswith(prefix)
                        or not page_suffix.isdigit() or len(source.stem) > 8
                        or (game / 'override' / name).exists()):
                    raise ValueError(f'New base page is outside unused map namespace: {name}')
                previous = {'present': False, 'sha256': None, 'bytes': None}
            if record(source) != previous:
                add(source, area, 'base-composition-repair')
        data, archive = bg2lib.resolve_resource(bifs, index[area, 0x3E9])
        original = data
        geometry = validate_polygons(data)
        for slot in target['slots']:
            data = replace_overlay_resref(data, slot['slot'], slot['alias'])
            for key in ('alias', 'rain_alias'):
                alias = slot[key]
                tis = unique_asset(overlays_root, alias + '.TIS')
                page_names, dimension, count = pages(tis)
                if dimension != 256:
                    raise ValueError(f'Overlay is not x4: {alias}')
                stock = slot['source'] + ('R' if key == 'rain_alias' else '')
                _, stock_count, _, _ = bg2lib.resolve_tileset_resource(bifs, index[stock, 0x3EB])
                if count != stock_count:
                    raise ValueError(f'Authored frame count changed: {alias}')
                for source in [tis, *[unique_asset(overlays_root, p) for p in page_names]]:
                    if len(source.stem) > 8:
                        raise ValueError(f'Resref too long: {source.name}')
                    if (game / 'override' / source.name).exists():
                        raise ValueError(f'Alias collision at assembly: {source.name}')
                    add(source, area, 'isolated-liquid-overlay')
        restored = data
        for slot in target['slots']:
            restored = replace_overlay_resref(restored, slot['slot'], slot['source'])
        if restored != original or validate_polygons(data) != geometry:
            raise ValueError(f'WED changed outside overlay resrefs: {area}')
        wed_path = run / 'weds' / (area + '.WED')
        wed_path.parent.mkdir(exist_ok=True)
        wed_path.write_bytes(data)
        add(wed_path, area, 'native-wed-alias-only')
    write_new(candidate / 'manifest.json', {
        'schema': 'bg2-upscale-area-animation-override-assets-v1', 'status': 'completed',
        'area': ','.join(t['wed'] for t in request['targets']),
        'files': files, 'qa': 'pending-user-ingame', 'release': 'not-requested'})
    report_name = 'assembly-report.json' if candidate_name == 'override-candidate' else candidate_name + '-assembly-report.json'
    write_new(run / report_name, {'schema': 'bg2-liquid-trial-assembly-v1',
        'status': 'candidate-ready-pending-installation', 'files': report,
        'bases_root': bases_root.relative_to(ROOT).as_posix(),
        'overlays_root': overlays_root.relative_to(ROOT).as_posix(),
        'runtime': 'unchanged; isolated aliases use native fallback',
        'wed_invariant': 'original vanilla byte-identical outside dry overlay resrefs',
        'qa': 'pending-user-ingame', 'release': 'not-requested'})
    print(f'Assembled {len(files)} changed/new files for {len(request["targets"])} WEDs', flush=True)


def verify_installed(run: Path, game: Path, candidate_name='override-candidate'):
    before = read(run / 'live-before.json')
    manifest = read(run / candidate_name / 'manifest.json')
    for name, expected in manifest['files'].items():
        got = record(game / 'override' / name)
        if not got['present'] or got['sha256'] != expected['sha256'] or got['bytes'] != expected['bytes']:
            raise ValueError(f'Installed asset mismatch: {name}')
    for section, folder in [('files', game / 'override'),
                            ('protected_override', game / 'override'), ('protected_runtime', game)]:
        for name, expected in before[section].items():
            if section == 'files' and name in manifest['files']:
                continue
            if record(folder / name) != expected:
                raise ValueError(f'Protected/unchanged file drift: {name}')
    print(f'Installation bytes verified: {len(manifest["files"])}; shared resources/runtime preserved', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--vanilla-root', type=Path, required=True)
    parser.add_argument('--bases-root', type=Path, help='Completed immutable base repair run')
    parser.add_argument('--overlays-root', type=Path, help='Completed immutable overlay build run')
    parser.add_argument('--candidate-name', default='override-candidate', help='New candidate directory name inside the run')
    parser.add_argument('--stage', choices=['snapshot', 'assemble', 'verify-before', 'verify-installed'], required=True)
    args = parser.parse_args()
    if (Path(args.candidate_name).name != args.candidate_name
            or not args.candidate_name.startswith('override-candidate')
            or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.candidate_name)):
        raise ValueError('Invalid candidate directory name')
    run, game, vanilla = args.run.resolve(), args.game_root.resolve(), args.vanilla_root.resolve()
    if ROOT not in run.parents or game == vanilla:
        raise ValueError('Output must be in workspace; game and vanilla must be distinct')
    request = read(run / 'request.json')
    bases_root = (args.bases_root or run / 'bases').resolve()
    overlays_root = (args.overlays_root or run / 'overlays').resolve()
    if args.stage == 'assemble' and any(run not in p.parents for p in (bases_root, overlays_root)):
        raise ValueError('Selected asset runs must be inside trial run')
    if args.stage == 'snapshot': snapshot(run, game, request)
    elif args.stage == 'assemble': assemble(run, game, vanilla, request, bases_root, overlays_root, args.candidate_name)
    elif args.stage == 'verify-before': verify_before(run, game, args.candidate_name); print('Baseline unchanged')
    else: verify_installed(run, game, args.candidate_name)


if __name__ == '__main__':
    main()
