"""Read the latest user-controlled session; require the new initial-cache marker."""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

parser = argparse.ArgumentParser()
parser.add_argument('--log', type=Path, default=get_path('bg2ee_game_root', required=True) / 'InfinityEngine-Enhancer.log')
args = parser.parse_args()
base = ROOT / 'pipeline/recipes/renderer-hooks-startup-repair-20261014-v1/runtime_check.py'
result = json.loads(subprocess.check_output([sys.executable, '-B', str(base), '--log', str(args.log)], encoding='utf-8'))
text = args.log.read_text(encoding='utf-8', errors='replace')
text = text[text.rfind('Infinity Engine Enhancer initializing...'):]
result['initial_map_cache_refresh_requests'] = re.findall(
    r'^.*Map initial cache refresh requested before native render:.*$', text, re.MULTILINE)
result['initial_cache_fix_active'] = bool(result['initial_map_cache_refresh_requests'])
result['technical_map_and_initial_refresh_passed'] = bool(
    result['technical_map_rendering_passed'] and result['initial_cache_fix_active'])
print(json.dumps(result, ensure_ascii=False, indent=2))
