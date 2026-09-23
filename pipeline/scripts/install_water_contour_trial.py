"""Install a prepared AR1600 contour trial, with drift checks and rollback.

Plan only by default; --run installs the reviewed PVRZ files. No engine changes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess

from workspace_paths import ROOT, get_path
from build_water_contour_trial import read, require, sha, write


def stopped():
    shell = shutil.which('powershell.exe')
    require(shell is not None, 'PowerShell unavailable')
    result = subprocess.run([shell, '-NoProfile', '-Command',
        '$p = Get-Process -Name Baldur,BaldurReal,InfinityLoader -ErrorAction SilentlyContinue; '
        'if ($p) { $p | Select-Object Id,ProcessName | ConvertTo-Json -Compress; exit 1 }; exit 0'],
        capture_output=True, text=True)
    require(result.returncode == 0, 'Close BG2EE and InfinityLoader before installation: '+result.stdout)
    return shell


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate', required=True, type=Path)
    ap.add_argument('--receipt', required=True, type=Path)
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    run = args.candidate.resolve(strict=True)
    run.relative_to(ROOT/'maps')
    receipt = args.receipt.resolve()
    receipt.relative_to(ROOT/'pipeline/water/manifests')
    require(not receipt.exists(), 'Receipt already exists')
    plan, build = read(run/'prepare.json'), read(run/'build.json')
    manifest = read(run/'override-candidate/manifest.json')
    require(build['area'] == plan['area'] == manifest['area'] == 'AR1600', 'Unexpected map')
    require(build['prepare_sha256'] == sha((run/'prepare.json').read_bytes()), 'Preparation drift')
    game = get_path('bg2ee_game_root', required=True)
    pages = {p['name']: p for p in build['pages']}
    require(set(pages) == set(manifest['files']), 'Manifest/file set mismatch')
    for name, row in manifest['files'].items():
        require(bool(re.fullmatch(r'A1600\d{2}\.PVRZ', name)), 'File outside AR1600 scope')
        data = (run/'override-candidate'/name).read_bytes()
        require(len(data) == row['bytes'] and sha(data) == row['sha256'] == pages[name]['after_sha256'],
                'Candidate drift: '+name)
        require(pages[name]['unselected_blocks_byte_exact'], 'Unbounded asset change')
    for name, digest in plan['source_pages'].items():
        require(sha((game/'override'/name).read_bytes()) == digest, 'Source drift: '+name)
    for name, digest in plan['protected'].items():
        require(sha((game/name).read_bytes()) == digest, 'Protected runtime drift: '+name)
    registry = read(ROOT/'pipeline/water/requests/ar1600-water-30fps-20260923-v1/registry-v3.json')
    identities = [e for e in registry['entries'] if e['wed']['resref'] == 'AR1600']
    require(len(identities) == 2, 'Expected normal/rain temporal identities')
    for entry in identities:
        require(not entry['base_tis']['pages'], 'Base page hashes require a registry rebuild')
        require(entry['temporal_overlay']['target_fps'] == 30, 'Temporal contract differs')
        expected = {entry['wed']['resref']+'.WED': entry['wed']['sha256'],
                    entry['base_tis']['resref']+'.TIS': entry['base_tis']['sha256'],
                    entry['overlay']['tis_resref']+'.TIS': entry['overlay']['tis_sha256']}
        expected.update({p['resref']+'.PVRZ': p['sha256'] for p in entry['overlay']['pages']})
        for name, digest in expected.items():
            require(sha((game/'override'/name).read_bytes()) == digest, 'Temporal identity drift: '+name)
    stopped()
    print(json.dumps({'mode': 'install' if args.run else 'plan', 'pages': len(pages),
                     'area': 'AR1600', 'rect_x1': plan['rect_x1'], 'temporal_identity': 'preserved'}), flush=True)
    if not args.run:
        return
    backup = ROOT/'backups/water'/run.name
    require(not backup.exists(), 'Backup run already exists')
    saved_dir = backup/('override-backup-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    saved_dir.mkdir(parents=True)
    records = []
    for name, row in manifest['files'].items():
        source = game/'override'/name
        require(sha(source.read_bytes()) == pages[name]['before_sha256'], 'Live drift before backup: '+name)
        shutil.copy2(source, saved_dir/name)
        require(sha((saved_dir/name).read_bytes()) == pages[name]['before_sha256'], 'Backup verification failed')
        records.append({'Name': name, 'PresentBefore': True,
                        'PreviousSha256': pages[name]['before_sha256'].lower(),
                        'InstalledSha256': row['sha256'].lower()})
    write(saved_dir/'install-backup.json', {'schema': 'bg2-upscale-area-override-install-backup-v1',
          'created_utc': datetime.now(timezone.utc).isoformat(), 'GameRoot': str(game),
          'SourceRoot': str(run/'override-candidate'), 'Files': records})
    try:
        stopped()
        for name in pages:
            require(sha((game/'override'/name).read_bytes()) == pages[name]['before_sha256'],
                    'Live drift immediately before installation: '+name)
        for name in pages:
            shutil.copy2(run/'override-candidate'/name, game/'override'/name)
        for name, row in manifest['files'].items():
            require(sha((game/'override'/name).read_bytes()) == row['sha256'], 'Installed hash mismatch: '+name)
        for name, digest in plan['protected'].items():
            require(sha((game/name).read_bytes()) == digest, 'Protected file changed: '+name)
        for name, digest in plan['source_pages'].items():
            if name not in pages:
                require(sha((game/'override'/name).read_bytes()) == digest, 'Untargeted source page changed: '+name)
    except Exception:
        stopped()
        receipts = list(backup.glob('*/install-backup.json'))
        if len(receipts) == 1:
            previous = read(receipts[0])
            for row in previous['Files']:
                name = row['Name']
                require(row['PresentBefore'], 'Unexpected new asset in rollback')
                require(sha((game/'override'/name).read_bytes()) in
                        {row['PreviousSha256'].upper(), row['InstalledSha256'].upper()}, 'Live drift blocks rollback')
                require(sha((receipts[0].parent/name).read_bytes()) == row['PreviousSha256'].upper(), 'Backup drift')
            for row in previous['Files']:
                shutil.copy2(receipts[0].parent/row['Name'], game/'override'/row['Name'])
        raise
    saved = next(backup.glob('*/install-backup.json'))
    write(receipt, {'schema': 'bg2-water-contour-installed-v1',
        'status': 'installed-pending-user-ingame-qa', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'area': 'AR1600', 'rect_x1': plan['rect_x1'], 'run': str(run.relative_to(ROOT)),
        'build_sha256': sha((run/'build.json').read_bytes()), 'files': pages,
        'protected_unchanged': plan['protected'], 'temporal_normal_rain_target_fps': 30,
        'backup_receipt': str(saved.relative_to(ROOT)), 'qa': 'pending-user',
        'release': 'not modified', 'installer_sha256': sha(Path(__file__).read_bytes())})
    print('Verified installation; receipt: '+str(receipt), flush=True)


if __name__ == '__main__':
    main()
