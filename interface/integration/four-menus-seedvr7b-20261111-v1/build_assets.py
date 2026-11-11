"""Patch selected MOS rectangles only; preserve other DXT5 blocks exactly."""
import hashlib
import io
import json
import struct
import sys
import zlib
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from mos_decode import decode_pvrz_page, pvr_to_dds_bytes
from workspace_paths import get_path


def fnv(data):
    value = 14695981039346656037
    for b in data:
        value = ((value ^ b) * 1099511628211) & 0xffffffffffffffff
    return value


def expand_native(raw, width, height):
    # Each native pixel becomes a constant 4x4 DXT5 block, reusing its exact
    # native endpoints and indices. No lossy recompression outside HD regions.
    result = bytearray(width * height * 16)
    repeat_alpha = sum(1 << (3 * i) for i in range(16))
    for y in range(height // 4):
        for x in range(width // 4):
            block = raw[(y * (width // 4) + x) * 16:][:16]
            alphas = int.from_bytes(block[2:8], 'little')
            colors = int.from_bytes(block[12:16], 'little')
            for py in range(4):
                for px in range(4):
                    i = py * 4 + px
                    constant = (block[:2] + (((alphas >> (i * 3)) & 7) * repeat_alpha).to_bytes(6, 'little')
                                + block[8:12] + (((colors >> (i * 2)) & 3) * 0x55555555).to_bytes(4, 'little'))
                    off = ((y * 4 + py) * width + x * 4 + px) * 16
                    result[off:off + 16] = constant
    return result


def main():
    if (HERE / 'assets.json').exists():
        raise SystemExit('Existing installation manifest: preserve these assets, create a new run for a rebuild.')
    bifs, entries = load_key()
    index = {(n.upper(), kind): loc for n, kind, loc in entries}
    def read(n, kind):
        return resolve_resource(bifs, index[n, kind])[0]
    run = ROOT / 'interface/experiments/menus-seedvr-x4-7b-3b-20261110-v1'
    selected = ('INVENTOR', 'QUESTBAK', 'GUIREC2', 'STONEOPT')
    pages = {}
    for name in selected:
        data = read(name, 1004)
        if data[:4] == b'MOSC':
            data = zlib.decompress(data[12:])
        assert data[:8] == b'MOS V2  '
        w, h, count, offset = struct.unpack_from('<4I', data, 8)
        output = run / f'seedvr-7b-x4/{name}/{name}-seedvr-7b-x4.png'
        image = Image.open(output).convert('RGBA')
        assert image.size == (w * 4, h * 4)
        for i in range(count):
            page, sx, sy, bw, bh, dx, dy = struct.unpack_from('<7I', data, offset + i * 28)
            pages.setdefault(page, []).append((name, image, sx, sy, bw, bh, dx, dy))
    assets = HERE / 'assets'
    fixtures = HERE / 'native-fixtures'
    assets.mkdir(exist_ok=True)
    fixtures.mkdir(exist_ok=True)
    manifest = []
    for page, blocks in sorted(pages.items()):
        raw_pvrz = read(f'MOS{page:04}', 1028)
        pvr = zlib.decompress(raw_pvrz[4:])
        header = list(struct.unpack_from('<13I', pvr))
        assert header[2] == 11 and header[11] == 1
        h, w = header[6:8]
        raw = pvr[52 + header[12]:]
        assert len(raw) == w * h
        (fixtures / f'MOS{page:04}.dxt5').write_bytes(raw)
        stem = 'MAINMENU-MOS0181' if page == 181 else f'GAMEPLAY7B-MOS{page:04}'
        baseline = (get_path('bg2ee_game_root') / 'iee-assets' / f'{stem}-x4.dxt5') if page == 181 else None
        original = baseline.read_bytes() if baseline else bytes(expand_native(raw, w, h))
        assert len(original) == w * h * 16
        atlas = Image.new('RGBA', (w * 4, h * 4))
        mask = bytearray(w * h)
        rectangles = []
        for name, image, sx, sy, bw, bh, dx, dy in blocks:
            atlas.paste(image.crop((dx * 4, dy * 4, (dx + bw) * 4, (dy + bh) * 4)), (sx * 4, sy * 4))
            for y in range(sy, sy + bh):
                assert not any(mask[y * w + sx:y * w + sx + bw]), 'Overlapping selected regions'
                mask[y * w + sx:y * w + sx + bw] = b'\1' * bw
            rectangles.append(dict(resref=name, rect=[sx, sy, bw, bh]))
        dds = io.BytesIO()
        atlas.save(dds, format='DDS', pixel_format='DXT5')
        encoded = dds.getvalue()[128:]
        result = bytearray(original)
        for rect in rectangles:
            sx, sy, bw, bh = rect['rect']
            for y in range(sy, sy + bh):
                off = (y * w + sx) * 16
                result[off:off + bw * 16] = encoded[off:off + bw * 16]
        assert all(result[i * 16:i * 16 + 16] == original[i * 16:i * 16 + 16]
                   for i, selected_block in enumerate(mask) if not selected_block)
        # Verify the exact lossless native fallback on every non-shared page.
        if not baseline:
            header[6], header[7], header[12] = h * 4, w * 4, 0
            expanded_dds, _, _ = pvr_to_dds_bytes(struct.pack('<13I', *header) + original)
            decoded = Image.open(io.BytesIO(expanded_dds)).convert('RGBA')
            assert decoded.tobytes() == decode_pvrz_page(raw_pvrz).resize((w * 4, h * 4), Image.Resampling.NEAREST).tobytes()
        target = assets / (stem + '-x4.dxt5')
        target.write_bytes(result)
        manifest.append(dict(page=page, stem=stem, width=w, height=h, fnv1a64=f'{fnv(raw):016X}',
                             source_sha256=hashlib.sha256(raw).hexdigest(), asset=target.name,
                             sha256=hashlib.sha256(result).hexdigest(), rectangles=rectangles,
                             baseline_sha256=hashlib.sha256(original).hexdigest(),
                             baseline='installed selector x4' if baseline else 'lossless native x4',
                             untouched_blocks_exact=True))
        print(page, manifest[-1]['fnv1a64'], 'untouched blocks preserved', flush=True)
    (HERE / 'assets.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
