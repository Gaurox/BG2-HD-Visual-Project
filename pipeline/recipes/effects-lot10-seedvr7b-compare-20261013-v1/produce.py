"""Explicit 10-BAM 7B comparison; resumable stages, sealed outputs never overwritten."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/effects-lot10-seedvr7b-compare-20261013-v1'
SCRIPTS = ROOT / 'pipeline/scripts'
sys.path.insert(0, str(SCRIPTS))
import effect_workflow as workflow


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def command(stage, asset, args):
    path = BATCH / 'logs' / (asset['resref'] + '-' + stage + '.log')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as log:
        log.write('\n' + json.dumps(args) + '\n'); log.flush()
        completed = subprocess.run([sys.executable, '-B', *args], cwd=ROOT,
                                   stdout=log, stderr=subprocess.STDOUT)
    if completed.returncode:
        raise RuntimeError(f'{stage} failed ({completed.returncode}); {path}')


def sealed(asset, key):
    resource = ROOT / 'effects/ressources' / asset['resref']
    path = resource / 'runs' / asset[key] / 'run.json'
    if not path.exists():
        return False
    descriptor = json.loads(path.read_text(encoding='utf-8'))
    if descriptor.get('result', {}).get('sealed'):
        stage = 'spatial' if key == 'spatial_run' else 'interpolation'
        checked = workflow.verify_run_descriptor(ROOT, resource, asset['resref'], asset[key],
                                                 stage=stage, spatial_run=asset['spatial_run'])
        if not checked['ok']:
            raise RuntimeError(f"Invalid sealed run {asset[key]}: {checked['errors']}")
        return True
    return False


def produce(asset, stage):
    name = asset['resref']
    if stage == 'spatial':
        if sealed(asset, 'spatial_run'):
            return
        args = ['pipeline/scripts/run_effect_spatial.py', '--resref', name,
                '--workflow', 'pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json',
                '--recipe-id', 'seedvr2-7b-int8-lab-x4', '--run-id', asset['spatial_run'],
                '--timeout-seconds', '1800', '--run']
        if (ROOT / 'effects/ressources' / name / 'runs' / asset['spatial_run']).exists():
            args.append('--resume')
        command(stage, asset, args)
        assert sealed(asset, 'spatial_run')
    elif stage == 'temporal':
        assert sealed(asset, 'spatial_run')
        if not sealed(asset, 'apollo_run'):
            command('apollo', asset, ['pipeline/scripts/run_effect_interpolation.py',
                    '--resref', name, '--spatial-run', asset['spatial_run'],
                    '--run-id', asset['apollo_run'], '--recipe-id',
                    'apollo8-rgb-left-alpha-one-shot-dedup', '--native-fps', '15',
                    '--target-fps', '30', '--one-shot', '--alpha-phase', 'left',
                    '--deduplicate', '--run'])
        assert sealed(asset, 'apollo_run')
        if not sealed(asset, 'treatment_run'):
            command('treatment', asset, ['pipeline/scripts/run_effect_visual_treatment.py',
                    '--resref', name, '--interpolation-run', asset['apollo_run'],
                    '--run-id', asset['treatment_run'], '--sigma-x4', '1.2',
                    '--inner-feather-x4', '12', '--run'])
        assert sealed(asset, 'treatment_run')
        pack = ROOT / asset['pack']
        if not (pack / 'manifest.json').is_file():
            command('pack', asset, ['pipeline/scripts/build_effect_runtime_pack.py',
                    '--resref', name, '--spatial-run', asset['spatial_run'],
                    '--interpolation-run', asset['treatment_run'], '--deduplicate',
                    '--output', asset['pack'], '--run'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['spatial', 'temporal'])
    parser.add_argument('--resref', action='append')
    parser.add_argument('--wait-spatial', action='store_true')
    args = parser.parse_args()
    batch = json.loads((BATCH / 'batch.json').read_text(encoding='utf-8'))
    assets = [a for a in batch['assets'] if not args.resref or a['resref'] in args.resref]
    inventory = {r['resref']: r for r in csv.DictReader(
        (ROOT / 'effects/index/bam-assets.csv').open(encoding='utf-8-sig'))}
    state_path = BATCH / (args.stage + '-progress.json')
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    failures = []
    for i, asset in enumerate(assets, 1):
        name = asset['resref']
        print(f'{args.stage} {i}/{len(assets)} {name}', flush=True)
        state[name] = {'state': 'running', 'started_utc': datetime.now(timezone.utc).isoformat()}
        write(state_path, state)
        try:
            source = ROOT / asset['source']
            assert hashlib.sha256(source.read_bytes()).hexdigest().upper() == inventory[name]['source_sha256'].upper()
            if args.stage == 'temporal' and args.wait_spatial:
                deadline = time.monotonic() + 3600
                while not sealed(asset, 'spatial_run'):
                    if time.monotonic() > deadline:
                        raise RuntimeError('spatial producer did not complete in one hour')
                    time.sleep(5)
            produce(asset, args.stage)
            state[name]['state'] = 'completed'
        except Exception as exc:
            failures.append(name)
            state[name].update(state='failed', error=str(exc))
            print(f'FAILED {name}: {exc}', flush=True)
        state[name]['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write(state_path, state)
    print(json.dumps({'stage': args.stage, 'processed': len(assets), 'failures': failures}), flush=True)
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
