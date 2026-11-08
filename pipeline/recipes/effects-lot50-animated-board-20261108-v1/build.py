"""Native source review only; no production or installation writes."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam, native_palette_alpha
from export_bam_frames import read_bam, cycle_metadata

PROPOSAL = ROOT / 'effects/batches/lot50-fire-smoke-proposal-20261028-v1/batch.json'
OUT = ROOT / 'effects/batches/lot50-native-animated-board-20261108-v1'


def main():
    proposal = json.loads(PROPOSAL.read_text(encoding='utf-8'))
    states = {r['asset_key']: r for r in csv.DictReader(
        (ROOT / 'effects/index/processing.csv').open(encoding='utf-8-sig', newline=''))}
    assert not (OUT / 'index.html').exists(), 'Use a new version to replace an existing board'
    (OUT / 'images').mkdir(parents=True, exist_ok=True)
    assets = []
    for a in proposal['assets']:
        state = states[a['asset_key']]
        assert state['spatial_state'] == 'not-started' and not state['selected_run'], a['resref']
        source = ROOT / a['source']
        assert hashlib.sha256(source.read_bytes()).hexdigest().upper() == a['source_sha256']
        raw = read_bam(source)
        frames, palette, transparent = decode_bam(raw)
        alpha = native_palette_alpha(raw, transparent)
        left = min(-cx for _, cx, _, _ in frames)
        top = min(-cy for _, _, cy, _ in frames)
        right = max(-cx + idx.shape[1] for idx, cx, _, _ in frames)
        bottom = max(-cy + idx.shape[0] for idx, _, cy, _ in frames)
        w, h = right-left, bottom-top
        cols = max(1, min(len(frames), 2048 // w))
        sheet = Image.new('RGBA', (cols*w, ((len(frames)+cols-1)//cols)*h))
        for i, (indices, cx, cy, _) in enumerate(frames):
            rgba = np.dstack((palette[indices], alpha[indices]))
            rgba[rgba[:, :, 3] == 0] = 0
            sheet.paste(Image.fromarray(rgba), ((i % cols)*w-cx-left, (i//cols)*h-cy-top))
        image = f"images/{a['resref']}.png"
        sheet.save(OUT / image)
        cycles = cycle_metadata(raw, len(frames))
        assert cycles == a['native_cycles']
        assets.append(dict(ordinal=a['ordinal'], resref=a['resref'], group=a['group'],
                           width=w, height=h, cols=cols, image=image, cycles=cycles,
                           frames=len(frames), source=a['source'], source_sha256=a['source_sha256'],
                           state=state['spatial_state']))
    catalog = dict(date='2026-11-08', proposal=str(PROPOSAL.relative_to(ROOT)).replace('\\', '/'),
                   count=len(assets), assets=assets, preview_fps=15,
                   timing='15 FPS preview assumption; native cadence unresolved; all native slots preserved')
    (OUT / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    template = Path(__file__).with_name('board.html').read_text(encoding='utf-8')
    (OUT / 'index.html').write_text(template.replace('__CATALOG__', json.dumps(catalog, ensure_ascii=False)), encoding='utf-8')
    print(json.dumps(dict(output=str(OUT), count=len(assets), cycles=sum(len(a['cycles']) for a in assets),
                          frames=sum(a['frames'] for a in assets), slots=sum(len(c['frame_indices']) for a in assets for c in a['cycles'])), indent=2))


if __name__ == '__main__':
    main()
