from pathlib import Path
import base64, io, json, sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam, native_palette_alpha
from export_bam_frames import read_bam, cycle_metadata
from bg2lib import load_key, resolve_resource
from palette_oracle import scalar_palette

out = Path(__file__).parent
old = json.loads((ROOT / 'projectiles/previews/identification-20261018-v1/selection.json').read_text(encoding='utf-8'))
bifs, entries = load_key()
lookup = {(n.upper(), t): loc for n, t, loc in entries}
def resource(name, kind):
    return resolve_resource(bifs, lookup[name.upper(), kind])[0]
ramps = np.asarray(Image.open(io.BytesIO(resource('MPALETTE', 1))).convert('RGB'))
items = []
for record in old['assets'] + [{'number': 50, 'bam': 'BGLRYU', 'representative_projectile': 'BGLRY', 'special': True}]:
    raw = resource('BGLRYU', 1000) if record.get('special') else read_bam(ROOT / record['source'])
    if raw[:4] == b'BAMC':
        import zlib
        raw = zlib.decompress(raw[12:])
    frames, palette, tr = decode_bam(raw)
    if not record.get('special'):
        owner = record['consumer']
        if owner['color_enabled'] == '1':
            palette = scalar_palette(ramps[[int(v) for v in owner['colors'].split(';')]])
        elif owner['palette']:
            im = Image.open(io.BytesIO(resource(owner['palette'], 1)))
            palette = np.array(im.getpalette()[:768], np.uint8).reshape(256, 3)
    alpha = native_palette_alpha(raw, tr)
    cycles = cycle_metadata(raw, len(frames))
    encoded = []
    for idx, cx, cy, _ in frames:
        image = Image.fromarray(np.dstack((palette[idx], alpha[idx])))
        buf = io.BytesIO(); image.save(buf, format='PNG')
        encoded.append({'src': 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode(), 'cx': cx, 'cy': cy, 'w': image.width, 'h': image.height})
    cycle_ids = [c['frame_indices'] for c in cycles]
    assert cycle_ids and all(all(i < len(encoded) for i in c) for c in cycle_ids)
    items.append({'n': record['number'], 'bam': record['bam'], 'pro': record['representative_projectile'],
        'state': 'source nouvelle à confirmer' if record.get('special') else record['production_snapshot']['spatial_state'],
        'note': 'Fumée potentielle : chemin moteur à confirmer' if record.get('special') else ('Alias exact de SPIPLAAI : ne pas relancer' if record['bam'] == 'SPIPLARI' else ''),
        'owners': [] if record.get('special') else [x.split(':')[-1] for x in record['all_travel_consumers']],
        'frames': encoded, 'cycles': cycle_ids, 'initial': 0 if record.get('special') else record['cycle_zero_based']})
assert len(items) == 50
template = (out / 'template.html').read_text(encoding='utf-8')
(out / 'planche.html').write_text(template.replace('/*DATA*/', json.dumps(items, ensure_ascii=False, separators=(',', ':'))), encoding='utf-8')
(out / 'selection.json').write_text(json.dumps([{k:v for k,v in x.items() if k not in ('frames','cycles')} | {'cycles': len(x['cycles']), 'images': len(x['frames'])} for x in items], ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('50 cartes,', sum(len(x['frames']) for x in items), 'images')
