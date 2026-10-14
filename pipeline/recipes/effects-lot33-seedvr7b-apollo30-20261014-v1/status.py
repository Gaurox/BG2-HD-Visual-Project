"""Compact read-only progress for the running lot33 batch."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/lot33-seedvr7b-apollo30-20261014-v1'
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
batch = load(BATCH / 'batch.json')
report = {'assets': len(batch['assets']), 'spatial_completed': 0,
          'source_frames_written': 0, 'source_frames_total': sum(a['frames'] for a in batch['assets']),
          'temporal_completed': 0, 'checked': 0, 'current': [], 'failures': []}
for stage in ['spatial', 'temporal']:
    p = BATCH / (stage + '-progress.json')
    data = load(p) if p.is_file() else {}
    report[stage + '_completed'] = sum(v['state'] == 'completed' for v in data.values())
    report['failures'].extend({'resref': k, 'stage': stage, 'error': v.get('error')}
                              for k, v in data.items() if v['state'] == 'failed')
    for a in batch['assets']:
        spatial = ROOT / 'effects/ressources' / a['resref'] / 'runs' / a['spatial_run'] / '01-spatial-x4/manifest.json'
        frame_count = len(load(spatial).get('frames', [])) if spatial.is_file() else 0
        if stage == 'spatial':
            report['source_frames_written'] += frame_count
        if data.get(a['resref'], {}).get('state') == 'running':
            report['current'].append({'stage': stage, 'resref': a['resref'],
                                       'source_frames': frame_count, 'source_total': a['frames']})
report['checked'] = sum(load(p).get('passed', False) for p in (BATCH / 'checks').glob('*.json'))
print(json.dumps(report, ensure_ascii=True), flush=True)
