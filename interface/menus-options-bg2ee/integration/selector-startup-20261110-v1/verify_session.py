"""Read the latest renderer session and check the selector's first-upload order."""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = next(p for p in Path(__file__).resolve().parents if (p / 'pipeline/scripts').is_dir())
sys.path.insert(0, str(REPO / 'pipeline/scripts'))
from workspace_paths import get_path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path)
args = parser.parse_args()
path = get_path('bg2ee_game_root') / 'InfinityEngine-Enhancer.log'
lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
start = max(i for i, line in enumerate(lines) if 'InfinityEngine-Enhancer loaded (config applied)' in line)
session = lines[start:]
# LOGOTOB frame 0 uses MOS0182; MOS0183 is first demanded by hover frame 1.
required = {'MOS0181', 'MOS0182', 'MOS0258', 'MOS0259'}
hover_pages = {'MOS0183'}
prepared = {m[1] for line in session if (m := re.search(r'Prepared reversible (MOS\d+)\.PVRZ x4', line))}
replaced = {m[1] for line in session if (m := re.search(r'Replacing (MOS\d+)\.PVRZ with x4', line))}
ready = next((i for i, line in enumerate(session) if 'Selector x4 compressed upload hook ready before native PVR Demand' in line or 'Installed GL shader probes' in line), None)
first_upload = next((i for i, line in enumerate(session) if 'Replacing MOS' in line), None)
result = dict(session_start=session[0], required_pages=sorted(required), prepared=sorted(prepared),
              replaced=sorted(replaced), missing=sorted(required - replaced),
              hover_pages_observed=sorted(hover_pages & replaced),
              hook_before_first_replacement=ready is not None and first_upload is not None and ready < first_upload,
              relevant_log=[line for line in session if any(key in line for key in (
                  'Prepared reversible MOS', 'Replacing MOS', 'Selector x4',
                  'Installed GL shader probes', 'Renderer startup barrier'))])
result['passed'] = not result['missing'] and result['hook_before_first_replacement'] and prepared == required | hover_pages | {'MOS0184', 'MOS0185'}
if args.output:
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
print(json.dumps(result, indent=2, ensure_ascii=False))
raise SystemExit(0 if result['passed'] else 2)
