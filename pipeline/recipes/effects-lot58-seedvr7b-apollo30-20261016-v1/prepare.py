"""Prepare the authorized lot58 and audit native duplicates per cycle."""
from pathlib import Path
import collections
import hashlib
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/lot58-seedvr7b-apollo30-20261016-v1'
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam
from export_bam_frames import read_bam, cycle_metadata


def main():
    proposal = ROOT / 'effects/batches/lot58-energy-fixedpalette-proposal-20261016-v1/batch.json'
    manifest = json.loads(proposal.read_text(encoding='utf-8'))
    assets = []
    reports = []
    for original in manifest['assets']:
        a = dict(original)
        name = a['resref']
        raw = read_bam(ROOT / a['source'])
        frames, palette, transparent = decode_bam(raw)
        a['native_cycles'] = cycle_metadata(raw, len(frames))
        a['spatial_run'] = f'{name.lower()}-seedvr7b-x4-20261016-v1'
        a['interpolation_run'] = f'{name.lower()}-apollo30-retimed-strict-20261016-v1'
        a['pack'] = f'effects/ressources/{name}/packs/{name.lower()}-7b-x4-apollo30-20261016-v1'
        bounds = (min(-cx for _, cx, _, _ in frames), min(-cy for _, _, cy, _ in frames),
                  max(-cx + idx.shape[1] for idx, cx, _, _ in frames),
                  max(-cy + idx.shape[0] for idx, _, cy, _ in frames))
        l, t, r, b = bounds
        identities = []
        blank = []
        for idx, cx, cy, _ in frames:
            canvas = np.zeros((b-t, r-l, 4), np.uint8)
            x, y = -cx-l, -cy-t
            canvas[y:y+idx.shape[0], x:x+idx.shape[1], :3] = palette[idx]
            canvas[y:y+idx.shape[0], x:x+idx.shape[1], 3] = (idx != transparent).astype(np.uint8)*255
            canvas[canvas[:, :, 3] == 0] = 0
            identities.append(hashlib.sha256(canvas.tobytes()).hexdigest().upper())
            blank.append(not canvas[:, :, :3].any())
        cycles = []
        for c in a['native_cycles']:
            slots = c['frame_indices']
            hashes = [identities[k] for k in slots]
            seen = {}
            repeats = []
            for position, h in enumerate(hashes):
                if h in seen:
                    repeats.append({'slot': position, 'first_slot': seen[h], 'source_record': slots[position]})
                else:
                    seen[h] = position
            cycles.append({'cycle': c['cycle'], 'native_slots': len(slots),
                           'distinct_anchored_rgba_poses': len(set(hashes)),
                           'duplicate_slots': repeats,
                           'adjacent_duplicate_slots': [i for i in range(1,len(hashes)) if hashes[i] == hashes[i-1]],
                           'blank_rgb_slots': [i for i,k in enumerate(slots) if blank[k]],
                           'constant_native_cycle': len(set(hashes)) <= 1})
        reports.append({'resref': name, 'cycles': cycles})
        assets.append(a)
    summary = {'assets': len(assets), 'cycles': sum(len(a['cycles']) for a in reports),
               'cycles_with_duplicate_native_poses': sum(bool(c['duplicate_slots']) for a in reports for c in a['cycles']),
               'assets_with_duplicate_native_poses': sum(any(c['duplicate_slots'] for c in a['cycles']) for a in reports),
               'repeated_native_slots': sum(len(c['duplicate_slots']) for a in reports for c in a['cycles']),
               'constant_native_cycles': sum(c['constant_native_cycle'] for a in reports for c in a['cycles'])}
    BATCH.mkdir(parents=True, exist_ok=True)
    batch = {'schema': 'bg2-effects-production-batch-v1', 'date': '2026-10-16',
             'proposal': proposal.relative_to(ROOT).as_posix(), 'assets_count': len(assets),
             'spatial_batch': BATCH.relative_to(ROOT).as_posix(),
             'authorization': 'User: full lot58, SeedVR7B x4, Apollo30; remove repeated native poses and redistribute over unchanged original duration.',
             'assets': assets}
    for filename, value in [('batch.json', batch), ('native-duplicate-audit.json', {'summary':summary,'assets':reports})]:
        path = BATCH / filename
        if path.exists():
            assert json.loads(path.read_text(encoding='utf-8')) == value, path
        else:
            path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
