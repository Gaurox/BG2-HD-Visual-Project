"""Write the water install receipt or user QA decision in one uniform format.

    python pipeline/scripts/record_water_decision.py install --area AR0404 --kind contour \
        --run maps/water-batches/runs/ar0404-contour-matte-20260924-v1 \
        --override-backup backups/water/ar0404-contour-matte-20260924-v1/override-backup-<stamp>
    python pipeline/scripts/record_water_decision.py qa --area AR0404 --kind contour \
        --selection pipeline/water/manifests/ar0404-contour-installed-20260924-v1.json \
        --result validated --quote "<message exact de l'utilisateur>"

``install`` checks that every candidate file is live byte for byte; ``qa`` refuses a
decision about bytes that are no longer installed.  Files land in
``pipeline/water/manifests/<area>-<kind>-{installed,user-qa}-<date>-vN.json``, never
overwriting an earlier version.  QA is recorded only from an explicit user message.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / 'pipeline/water/manifests'
KINDS = ('spatial', 'temporal-30fps', 'contour')
RESULTS = ('validated', 'validated-with-reserve', 'rejected')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def rel(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def next_path(folder, area, kind, what, day):
    stem = f'{area.lower()}-{kind}-{what}-{day}'
    n = 1
    while (folder / f'{stem}-v{n}.json').exists():
        n += 1
    return folder / f'{stem}-v{n}.json'


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    return path


def live_mismatches(files, override):
    return [name for name, row in files.items()
            if not (override / name).is_file() or sha(override / name) != row['sha256'].upper()]


def install_record(area, kind, run, override, backup, runtime=None, manifest=None, note=None):
    run = Path(run).resolve()
    manifest = Path(manifest) if manifest else next(
        (p for p in (run / 'override-candidate/manifest.json', run / 'candidate/manifest.json') if p.is_file()), None)
    if manifest is None:
        raise SystemExit('candidate manifest not found; pass --candidate-manifest')
    files = json.loads(Path(manifest).read_text(encoding='utf-8-sig'))['files']
    bad = live_mismatches(files, override)
    if bad:
        raise SystemExit(f'not installed byte for byte: {bad}')
    backup = Path(backup)
    receipt = backup if backup.name == 'install-backup.json' else backup / 'install-backup.json'
    if not receipt.is_file():
        raise SystemExit(f'override backup receipt missing: {receipt}')
    record = {'schema': 'bg2-water-installed-v1', 'area': area.upper(), 'kind': kind,
              'status': 'installed-pending-user-ingame-qa',
              'recorded_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'run': rel(run), 'candidate_manifest': {'path': rel(manifest), 'sha256': sha(manifest)},
              'files': {n: {'sha256': r['sha256'].upper(), 'bytes': r.get('bytes')} for n, r in files.items()},
              'override_backup_receipt': rel(receipt), 'qa': 'pending-user-ingame', 'release': 'not-requested'}
    for key, name in (('build.json', 'build_report'), ('prepare.json', 'prepare')):
        if (run / key).is_file():
            record[name] = {'path': rel(run / key), 'sha256': sha(run / key)}
    if runtime:
        runtime = Path(runtime)
        data = json.loads(runtime.read_text(encoding='utf-8-sig'))
        record['runtime'] = {'receipt': rel(runtime), 'dll_sha256': data['installed_sha256'],
                             'registry': data.get('registry')}
    if note:
        record['note'] = note
    return record


def qa_record(area, kind, selection, quote, result, override, reserve=None, weather=None):
    selection = Path(selection)
    installed = json.loads(selection.read_text(encoding='utf-8-sig'))
    if installed.get('area', area).upper() != area.upper():
        raise SystemExit('selection belongs to another area')
    bad = live_mismatches(installed['files'], override) if 'files' in installed else []
    if bad:
        raise SystemExit(f'selection no longer installed: {bad}')
    if result == 'validated-with-reserve' and not reserve:
        raise SystemExit('--reserve is required with validated-with-reserve')
    return {'schema': 'bg2-water-user-qa-v1', 'area': area.upper(), 'kind': kind,
            'recorded_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'source': 'user-message', 'quote': quote, 'result': result, 'reserve': reserve,
            'weather_and_variant_observed': weather or 'not-specified-by-user',
            'selection': {'path': rel(selection), 'sha256': sha(selection)}, 'release': 'not-requested'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('install', 'qa'):
        p = sub.add_parser(name)
        p.add_argument('--area', required=True)
        p.add_argument('--kind', required=True, choices=KINDS)
        p.add_argument('--game-root', type=Path)
    i = sub.choices['install']
    i.add_argument('--run', required=True, type=Path)
    i.add_argument('--override-backup', required=True, type=Path)
    i.add_argument('--runtime-receipt', type=Path, help='Install-WaterRuntime.ps1 receipt (30 fps runs)')
    i.add_argument('--candidate-manifest', type=Path)
    i.add_argument('--note')
    q = sub.choices['qa']
    q.add_argument('--selection', required=True, type=Path)
    q.add_argument('--quote', required=True, help="user's message, verbatim")
    q.add_argument('--result', required=True, choices=RESULTS)
    q.add_argument('--reserve')
    q.add_argument('--weather', help='variant/weather actually observed, if the user said so')
    args = parser.parse_args()
    game = args.game_root
    if game is None:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from workspace_paths import get_path
        game = get_path('bg2ee_game_root', required=True)
    override = Path(game) / 'override'
    day = date.today().strftime('%Y%m%d')
    if args.command == 'install':
        data = install_record(args.area, args.kind, args.run, override, args.override_backup,
                              args.runtime_receipt, args.candidate_manifest, args.note)
        path = save(next_path(MANIFESTS, args.area, args.kind, 'installed', day), data)
    else:
        data = qa_record(args.area, args.kind, args.selection, args.quote, args.result, override,
                         args.reserve, args.weather)
        path = save(next_path(MANIFESTS, args.area, args.kind, 'user-qa', day), data)
    print(rel(path))


if __name__ == '__main__':
    main()
