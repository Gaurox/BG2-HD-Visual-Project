"""Read-only checks of the latest user-controlled game session."""
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

game = get_path('bg2ee_game_root', required=True)
parser = argparse.ArgumentParser()
parser.add_argument('--log', type=Path, default=game / 'InfinityEngine-Enhancer.log')
arguments = parser.parse_args()
lines = arguments.log.read_text(encoding='utf-8', errors='replace').splitlines()
first = max(i for i, line in enumerate(lines) if 'Infinity Engine Enhancer initializing...' in line)
session = lines[first:]
text = '\n'.join(session)
reserved = next((i for i, s in enumerate(session) if 'Core hook trampolines reserved before asset loading' in s), -1)
effects = next((i for i, s in enumerate(session) if 'Prepared effect animation x4 runtime pack: resources=97' in s), -1)
areas = sorted(set(re.findall(r'(?:Map telemetry marker:|Map texture telemetry \(area total\):).*?area=([A-Z0-9]+)', text)))
tilesets = {name: int(scale) for scale, name in re.findall(r'Detected (\d+)x tileset (0x[0-9A-F]+)', text)}
page_pattern = (r'TILE_PAGE_DIAG tileset=(0x[0-9A-F]+).*?uv=\((-?\d+), (-?\d+)\) '
                r'pvr=(\S+) pvrTexture=(-?\d+) pvrSize=(\d+)x(\d+) texId=(-?\d+)')
pages = []
for name, u, v, pvr, texture, width, height, bound in re.findall(page_pattern, text):
    u, v, texture, width, height, bound = map(int, (u, v, texture, width, height, bound))
    dimension = 64 * tilesets.get(name, 0)
    pages.append({'tileset': name, 'pvr': pvr, 'uv': [u, v], 'pvr_size': [width, height],
                  'scale': tilesets.get(name), 'texture': texture, 'bound_texture': bound,
                  'passed': dimension > 0 and u >= 0 and v >= 0 and
                            u + dimension <= width and v + dimension <= height and texture == bound})
errors = [s for s in session if '[error]' in s]
hooks_ready = 'All hooks installed successfully' in text
draw_counts = [int(n) for n in re.findall(r'decodedTileDraws=(\d+)', text)]
result = {
    'session_start': session[0], 'source_start_line': first + 1, 'source_end_line': len(lines),
    'corrected_startup': reserved >= 0, 'core_reserved_before_effects': 0 <= reserved < effects,
    'all_hooks_installed': hooks_ready, 'errors': errors,
    'effect_resources': 97 if effects >= 0 else None,
    'effect_filter_nearest': 'gpuTextureCapacity=64, filter=NEAREST' in text,
    'areas': areas, 'tilesets': tilesets, 'page_samples': pages,
    'maximum_decoded_tile_draws': max(draw_counts, default=0),
    'creature_composite_hd_samples': sum('Composing creature sprite ' in s and 'scale=x' in s for s in session),
    'visual_acceptance': 'not inferred from logs',
}
result['technical_map_rendering_passed'] = bool(
    result['core_reserved_before_effects'] and hooks_ready and not errors and
    areas and pages and all(p['passed'] for p in pages) and
    any(p['scale'] == 4 for p in pages) and result['maximum_decoded_tile_draws'] > 0)
print(json.dumps(result, ensure_ascii=False, indent=2))
