"""Audit only the four reported cloud cycles; installed files stay read-only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam
from export_bam_frames import cycle_metadata
from workspace_paths import get_path


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


game = get_path('bg2ee_game_root', required=True)
vanilla_receipt = json.loads((ROOT / 'effects/installations/vanilla-cloud-tests-20261017-v2/installation.json')
                             .read_text(encoding='utf-8'))
vanilla = Path(vanilla_receipt['game_root'])
manifest_path = game / 'iee-assets/effects/manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
results = []
for ref, vvc, cycle, mode in [('BDWOFOGA', 'Z580269', 4, 'loop'),
                              ('SPCLOUDK', 'Z580278', 2, 'once'),
                              ('SPCLOUDS', 'Z580290', 2, 'once'),
                              ('SPDFOGA', 'Z580300', 1, 'once')]:
    source = ROOT / 'effects/ressources' / ref / 'source.bam'
    original = source.read_bytes()
    native_record = next(f for f in vanilla_receipt['files'] if f['bam'] == ref)
    assert digest(original) == native_record['native_bam_sha256']
    data = zlib.decompress(original[12:]) if original[:4] == b'BAMC' else original
    frames, rgb, transparent = decode_bam(data)
    palette_offset = struct.unpack_from('<I', data, 16)[0]
    palette = np.frombuffer(data, np.uint8, count=1024, offset=palette_offset).reshape(256, 4)
    carrier = (game / 'override' / f'{ref}.bam').read_bytes()
    carrier = zlib.decompress(carrier[12:]) if carrier[:4] == b'BAMC' else carrier
    carrier_palette = struct.unpack_from('<I', carrier, 16)[0]
    assert carrier[carrier_palette:carrier_palette+1024] == data[palette_offset:palette_offset+1024]
    # Native PaletteResource 42D9F7-42DA36: use A=1..254; A=0/255
    # selects the default/global opacity; transparent green index is cleared.
    expected_alpha = palette[:, 3].copy()
    expected_alpha[(expected_alpha == 0) | (expected_alpha == 255)] = 255
    expected_alpha[transparent] = 0
    native_cycle = cycle_metadata(data, len(frames))[cycle]['frame_indices']
    slot = len(native_cycle) // 2
    native_index = native_cycle[slot]
    indices = frames[native_index][0]
    graded = expected_alpha[indices]
    binary = np.where(indices == transparent, 0, 255).astype(np.uint8)
    resource = next(r for r in manifest['resources'] if r['resref'] == ref)
    run = ROOT / 'effects/ressources' / ref / 'runs' / resource['interpolation_run'] / '02-interpolation'
    interpolation = json.loads((run / 'manifest.json').read_text(encoding='utf-8'))
    sample = next(f for f in interpolation['frames'] if f['cycle'] == cycle and f['mode'] == mode
                  and f['phase'] == slot * 2)
    source_name = (run / sample['straight_raw_rgba_x4']).relative_to(ROOT).as_posix()
    installed = next(f for f in manifest['frames'] if f['resref'] == ref and f['source'] == source_name)
    rgba_raw = (game / 'iee-assets/effects' / installed['asset']).read_bytes()
    assert digest(rgba_raw) == installed['sha256']
    rgba = np.frombuffer(rgba_raw, np.uint8).reshape(-1, 4)
    vvc_bytes = (game / 'override' / f'{vvc}.vvc').read_bytes()
    assert vvc_bytes == (vanilla / 'override' / f'{vvc}.vvc').read_bytes()
    assert struct.unpack_from('<H', vvc_bytes, 0x18)[0] == 0
    nonzero = binary > 0
    affected = nonzero & (graded < 255)
    unique = palette[1:, 3]
    results.append({
        'bam': ref, 'vvc': vvc, 'cycle': cycle, 'profile': mode,
        'vvc_sha256': digest(vvc_bytes), 'vvc_identical_vanilla_hd': True,
        'source_bam_sha256': digest(original), 'source_matches_vanilla_bif_receipt': True,
        'installed_carrier_palette_identical': True,
        'palette_alpha_nontransparent_range': [int(unique.min()), int(unique.max())],
        'palette_alpha_nontransparent_distinct': int(len(np.unique(unique))),
        'sample_native_slot': slot, 'sample_native_frame': native_index,
        'native_visible_pixels': int(nonzero.sum()),
        'native_pixels_changed_to_opaque_by_export': int(affected.sum()),
        'native_alpha_median': float(np.median(graded[nonzero])),
        'binary_alpha_median': float(np.median(binary[nonzero])),
        'installed_encoding': resource['rgb_encoding'],
        'installed_sample': installed['asset'], 'installed_sample_sha256': installed['sha256'],
        'installed_nonzero_alpha_pixels': int((rgba[:, 3] > 0).sum()),
        'installed_alpha_255_pixels': int((rgba[:, 3] == 255).sum()),
    })
log_path = game / 'InfinityEngine-Enhancer.log'
log_bytes = log_path.read_bytes()
lines = log_bytes.decode('utf-8', errors='replace').splitlines()
filtered = [l for l in lines if l.startswith('[2026-10-17 15:46:') and
            ('EFX_STREAM_DIAGNOSTIC' in l or 'EFX_GPU' in l or 'Effect GPU' in l)]
(OUT / 'session-1546-effects.log').write_text('\n'.join(filtered) + '\n', encoding='utf-8')
evidence = {
    'utc': datetime.now(timezone.utc).isoformat(), 'game_executed': False,
    'installed_files_modified': False,
    'dll_sha256': digest((game / 'InfinityEngine-Enhancer.dll').read_bytes()),
    'active_manifest_sha256': digest(manifest_path.read_bytes()),
    'log_source': str(log_path), 'log_source_sha256': digest(log_bytes), 'clouds': results,
    'screenshots': [{'path': str(p), 'sha256': digest(p.read_bytes())} for p in
                    [Path(r'E:/Steam/userdata/5536307/760/remote/257350/screenshots') / f'{n}_1.jpg'
                     for n in ['20261017154631', '20261017154637', '20261017154645', '20261017154652']]],
}
with (OUT / 'evidence.json').open('x', encoding='utf-8') as stream:
    stream.write(json.dumps(evidence, indent=2) + '\n')
for r in results:
    print(r['bam'], 'paletteA=', r['palette_alpha_nontransparent_range'],
          'sample medianA=', r['native_alpha_median'], '->', r['binary_alpha_median'],
          'changed pixels=', r['native_pixels_changed_to_opaque_by_export'],
          '/', r['native_visible_pixels'], 'VVC identical=', r['vvc_identical_vanilla_hd'])
