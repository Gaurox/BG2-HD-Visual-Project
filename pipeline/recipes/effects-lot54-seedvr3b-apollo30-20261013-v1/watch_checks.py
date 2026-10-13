"""Verify newly completed assets once, then render their individual previews."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import time
import verify

ROOT, BATCH = verify.ROOT, verify.BATCH
RECIPES = Path(__file__).parent


def main():
    deadline = time.monotonic() + 7200
    while time.monotonic() < deadline:
        assets = verify.load(BATCH / 'batch.json')['assets']; ready = 0; failed = []
        for asset in assets:
            if not (ROOT / asset['pack'] / 'manifest.json').is_file(): continue
            path = BATCH / 'checks' / (asset['resref']+'.json')
            previous = verify.load(path) if path.exists() else {}
            inputs = {'pack_manifest_sha256': verify.workflow.sha256_file(ROOT / asset['pack'] / 'manifest.json')}
            for key in ['spatial_run', 'apollo_run', 'treatment_run']:
                inputs[key] = verify.workflow.sha256_file(ROOT / 'effects/ressources' / asset['resref'] / 'runs' / asset[key] / 'run.json')
            if not previous.get('passed') or previous.get('checked_inputs') != inputs:
                try:
                    previous = verify.verify(asset)
                except Exception as exc:
                    previous = {'resref': asset['resref'], 'passed': False, 'error': repr(exc)}
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps(previous, indent=2)+'\n', encoding='utf-8')
                print(asset['resref'], 'PASS' if previous['passed'] else previous['error'], flush=True)
            if previous['passed']:
                ready += 1
                if not (BATCH / 'preview/videos' / (asset['resref']+'.mp4')).exists():
                    subprocess.run([sys.executable, '-B', str(RECIPES / 'preview.py'), '--ready-only',
                                    '--resref', asset['resref']], cwd=ROOT, check=True)
            else:
                failed.append(asset['resref'])
        (BATCH / 'check-progress.json').write_text(json.dumps({'verified': ready, 'failures': failed})+'\n', encoding='utf-8')
        if ready == 54:
            print('All 54 assets verified and individual videos rendered', flush=True); return 0
        time.sleep(10)
    return 1


if __name__ == '__main__': raise SystemExit(main())
