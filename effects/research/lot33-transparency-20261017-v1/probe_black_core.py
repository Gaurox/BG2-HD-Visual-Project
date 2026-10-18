"""Inspect SPMETSWM black-core signal; source/spatial/temporal stay read-only."""
import json
import sys
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam
from export_bam_frames import read_bam

OUT = Path(__file__).parent
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
base = ROOT / 'effects/ressources/SPMETSWM/runs'
stage = base / 'spmetswm-apollo30-native-retimed-20261017-v1/02-interpolation'
m = load(stage / 'manifest.json')
sp = load(ROOT / m['parent']['spatial_manifest'])
fs, pal, tr = decode_bam(read_bam(ROOT / 'effects/ressources/SPMETSWM/source.bam'))
cw, ch = sp['aligned_canvas_size_x1']
cores, sources = {}, {}
for k, (idx, *_) in enumerate(fs):
    x, y = sp['frames'][k]['canvas_offset_x1']
    rgb = np.zeros((ch, cw, 3), np.uint8)
    rgb[y:y+idx.shape[0], x:x+idx.shape[1]] = pal[idx]
    mask = np.zeros((ch, cw), bool)
    mask[y:y+idx.shape[0], x:x+idx.shape[1]] = (pal[idx].max(2) == 0) & (idx != tr)
    cores[k] = np.repeat(np.repeat(distance_transform_edt(np.pad(mask, 1))[1:-1, 1:-1] > 2, 4, 0), 4, 1)
    sources[k] = np.repeat(np.repeat(rgb, 4, 0), 4, 1)
rows = []
worst = None
for f in m['frames']:
    w, h = f['physical_size_x4']
    rgba = np.fromfile(stage / f['raw_rgba_x4'], np.uint8).reshape(h, w, 4)
    left, right = f['temporal_source_frames']
    l, t, r, b = f['runtime_crop_box_x4']
    core = (cores[left] & cores[right])[t:b, l:r] & (rgba[:, :, 3] > 0)
    peak = int(rgba[:, :, :3].max(2)[core].max()) if core.any() else 0
    record = {'frame': f['frame'], 'source_frames': [left, right], 'peak_rgb': peak,
              'pixels_over8': int((rgba[:, :, :3].max(2)[core] > 8).sum())}
    rows.append(record)
    if worst is None or peak > worst[0]:
        worst = peak, f, rgba, core
peak, f, rgba, core = worst
l, t, r, b = f['runtime_crop_box_x4']
left, right = f['temporal_source_frames']
images = [sources[left][t:b, l:r], sources[right][t:b, l:r], rgba[:, :, :3],
          np.where(core[:, :, None], rgba[:, :, :3], 0)]
sheet = Image.new('RGB', (1200, 360), (32, 36, 42))
draw = ImageDraw.Draw(sheet)
for col, (pixels, label) in enumerate(zip(images, ['source left', 'source right', 'final RGB', 'intersection black cores >2px'])):
    im = Image.fromarray(pixels); im.thumbnail((290, 320), Image.Resampling.NEAREST)
    sheet.paste(im, (col*300+(290-im.width)//2, 30+(320-im.height)//2))
    draw.text((col*300+5, 5), label, fill='white')
sheet.save(OUT / 'spmetswm-black-core.png')
result = {'asset': 'SPMETSWM', 'peak': peak, 'worst_frame': f['frame'], 'frames': rows,
          'interpretation': 'Black-core overlap is a diagnostic, not a proof of leakage: interpolation can move visible flame through pixels black in both endpoint images. No generated alpha/black threshold correction inferred.'}
(OUT / 'spmetswm-black-core.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k != 'frames'}))
