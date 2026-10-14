"""Record completed production and review without inferring acceptance or installation."""
from pathlib import Path
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

BATCH = ROOT / 'effects/batches/lot33-seedvr7b-apollo30-20261014-v1'
FINAL = BATCH / 'production-result.json'
if FINAL.exists():
    raise RuntimeError('Final result already recorded; use a new version')
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest().upper()
read_csv = lambda p: list(csv.DictReader(p.open(encoding='utf-8-sig', newline='')))
batch = load(BATCH / 'batch.json')
verification = load(BATCH / 'verification.json')
preview = load(BATCH / 'preview/preview.json')
assert verification['checked'] == verification['passed'] == len(batch['assets']) == 33
assert not verification['failures']
assert len(preview['assets']) == 33 and preview['grid_video']['fps'] == 30
assert all(a['video']['fps'] == 30 for a in preview['assets'])
assert sum(a['phases_30fps'] for a in verification['assets']) == 2202
assert sum(a['native_frames'] for a in verification['assets']) == 1054
before = {r['asset_key']: r for r in read_csv(BATCH / 'processing-before.csv')}
current = read_csv(ROOT / 'effects/index/processing.csv')
scope = {a['resref']: a for a in batch['assets']}
for row in current:
    old = before[row['asset_key']]
    name = row['asset_key'].rsplit(':', 1)[-1]
    if name in scope:
        assert row['spatial_run'] == scope[name]['spatial_run']
        assert row['interpolation_run'] == scope[name]['treatment_run']
        assert all(row[k] == old[k] for k in row if k not in {
            'spatial_run', 'spatial_state', 'interpolation_run', 'interpolation_state'})
    else:
        assert row == old, name
game = get_path('bg2ee_game_root', required=True)
installed = load(BATCH / 'installed-before.sha256.json')
assert all(sha(game / name) == digest for name, digest in installed.items())
final_files = ['batch.json', 'verification.json', 'preview/index.html',
               'preview/preview.json', 'preview/lot33-animated-30fps.mp4',
               'preview/lot33-animated.gif', 'preview/lot33-poster.png']
FINAL.write_text(json.dumps({
    'schema': 'bg2-effects-lot33-production-result-v1', 'status': 'produced-verified',
    'assets': 33, 'model': 'seedvr2_7b_int8_convrot.safetensors', 'scale': 4,
    'native_frames': 1054, 'native_slots': 1101, 'phases_30fps': 2202,
    'target_fps': [30, 1], 'technical_checks_passed': 33,
    'unit_pack_raw_bytes': verification['total_raw_bytes'],
    'registered_production': True, 'qa_selection_installation_release_unchanged': True,
    'installed_renderer_shaders_and_resource_metadata_unchanged': True,
    'artifact_sha256': {name: sha(BATCH / name) for name in final_files},
    'visual_qa': 'pending-user-review', 'installation': 'not requested; current game preserved',
    'preview': 'preview/index.html', 'individual_videos': 33,
    'grid_video_fps': 30, 'gif_preview_fps': 12,
}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('33/33 verified; 1054 source frames, 2202 phases at 30 FPS; game and QA/release preserved')
