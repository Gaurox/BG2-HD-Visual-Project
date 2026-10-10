"""Five source BAMs -> independent spatial runs; no game/index/release writes."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

TAG = 'portails-cinq-20261010-v1'
JOBS = [('BDFORCEW', 'rebout', 16), ('OHDLPORT', 'xbr', 0),
        ('OHHPORT', 'xbr', 0), ('OHRSGATE', 'rebout', 16), ('SPDIMNDR', 'rebout', 2)]
BATCH = ROOT / 'animations/batches' / TAG


def command(args, logfile):
    print('RUN ' + ' '.join(map(str, args)), flush=True)
    with logfile.open('a', encoding='utf-8') as log:
        subprocess.run(list(map(str, args)), cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)


def main():
    BATCH.mkdir(parents=True, exist_ok=True)
    records = []
    for ref, method, radius in JOBS:
        run_id = f'{ref.lower()}-{method}-spatial-20261010-v1'
        run = ROOT / f'animations/ressources/{ref}/runs/{run_id}'
        log = BATCH / f'{ref}-spatial.log'
        if not run.exists():
            command([sys.executable, '-B', ROOT / 'pipeline/scripts/run_animation_upscale.py',
                     '--resref', ref, '--run', run_id, '--prepare-only', '--pad', '0'], log)
        if not (run / '03_runtime_pack/manifest.json').exists():
            if method == 'rebout':
                command([get_path('chainner_python'), '-B', ROOT / 'pipeline/scripts/run_animation_reboutcx_x4.py',
                         '--run-root', run, '--resref', ref, '--resume'], log)
            else:
                command([sys.executable, '-B', ROOT / 'pipeline/scripts/run_animation_small_subject_xbr2.py',
                         '--run-root', run, '--resref', ref, '--xbr-blend', '--second-pass', 'nearest', '--resume'], log)
            command([sys.executable, '-B', ROOT / 'pipeline/scripts/build_animation_runtime_pack.py', run], log)
        records.append({'resref': ref, 'method': method, 'spatial_run': run.relative_to(ROOT).as_posix(),
                        'inner_feather_x4': radius})
        print('SPATIAL COMPLETED ' + ref, flush=True)
        (BATCH / 'spatial-jobs.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
