"""Verify the candidate archive or the assets installed by WeiDU on a clean copy."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile


def extract(package, game, resume=False):
    with ZipFile(package) as archive:
        expected = {}
        for line in archive.read('checksums.sha256').decode().splitlines():
            digest, name = line.split('  ', 1)
            expected[name] = digest.upper()
        names = archive.namelist()
        if len(names) != len(expected)+1 or set(names) != set(expected) | {'checksums.sha256'}:
            raise ValueError('Package inventory differs')
        for i, name in enumerate(names, 1):
            rel = PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:
                raise ValueError(f'Unsafe archive name: {name}')
            path = game.joinpath(*rel.parts)
            if not path.resolve().is_relative_to(game):
                raise ValueError(f'Path outside test game: {name}')
            if resume and name in expected and path.is_file():
                with path.open('rb') as current:
                    if hashlib.file_digest(current, 'sha256').hexdigest().upper() == expected[name]:
                        continue
            path.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            with archive.open(name) as src, path.open('xb') as dst:
                for block in iter(lambda: src.read(8 << 20), b''):
                    digest.update(block)
                    dst.write(block)
            if name in expected and digest.hexdigest().upper() != expected[name]:
                raise ValueError(f'ZIP member checksum differs: {name}')
            if i%5000 == 0:
                print(f'{i}/{len(names)} fichiers extraits et vérifiés', flush=True)
    print(f'ZIP members verified: {len(expected)}', flush=True)


def verify_install(game):
    manifests = game/'bg2hd/manifests'
    entries = json.loads((manifests/'content.json').read_bytes())['entries']
    components = json.loads((manifests/'components.json').read_bytes())['components']
    expected_components = {str(c['id']) for c in components}
    log = (game/'WeiDU.log').read_text(encoding='utf-8-sig', errors='replace')
    installed = set(re.findall(r'(?im)^~BG2HD/BG2HD\.TP2~ #\d+ #(\d+)', log))
    if installed != expected_components:
        raise ValueError(f'WeiDU components differ: missing={expected_components-installed}, extra={installed-expected_components}')
    final = {}
    for row in sorted(entries, key=lambda x: (x['install_order'], x['component_id'])):
        path = row['destination']
        if path.casefold() in final and not row.get('replaces_component_output'):
            raise ValueError(f'Unexpected overwritten destination: {path}')
        final[path.casefold()] = row

    def check(row):
        path = game/row['destination']
        if path.stat().st_size != row['bytes']:
            raise ValueError(f'Installed size differs: {row["destination"]}')
        with path.open('rb') as src:
            if hashlib.file_digest(src, 'sha256').hexdigest().upper() != row['sha256']:
                raise ValueError(f'Installed checksum differs: {row["destination"]}')

    with ThreadPoolExecutor(max_workers=8) as pool:
        for count, _ in enumerate(pool.map(check, final.values()), 1):
            if count%5000 == 0:
                print(f'{count}/{len(final)} assets installés vérifiés', flush=True)
    renderer = json.loads((manifests/'renderer-bundle.json').read_bytes())['files']
    dll = next(row for row in renderer if row['path']=='InfinityEngine-Enhancer.dll')
    check({**dll, 'destination': dll['path']})
    for path in ('iee-assets/effects/EffectCrops-X4.rgba', 'iee-assets/effects/EffectTiles-X4.rgba'):
        if (game/path).exists():
            raise ValueError(f'Stale effects blob was installed: {path}')
    result = {'weidu_components': len(installed), 'installed_destinations_verified': len(final),
              'installed_renderer_sha256': dll['sha256'], 'ingame_validation': 'pending'}
    report = json.dumps(result, indent=2) + '\n'
    (game.parent/'verified-install.json').write_text(report, encoding='utf-8')
    print(report, end='')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('--extract', type=Path)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    game = args.game.resolve(strict=True)
    if not (game/'chitin.key').is_file():
        raise ValueError('Test game directory is missing chitin.key')
    if args.extract:
        extract(args.extract, game, args.resume)
    else:
        verify_install(game)
