"""Generate pinned Water/Boom source knots and actual native colour fixtures."""
from pathlib import Path
import hashlib
import io
import json
import struct
import sys
import zlib
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from bam_export import decode_bam
from workspace_paths import get_path
SOURCE = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee'
OUT = ROOT / 'projectiles/analysis/residual-four-20261110-v1'


def array(values):
    return ',\n'.join('  ' + ','.join(f'0x{v:08x}u' for v in values[i:i+8]) for i in range(0, len(values), 8))


def main():
    assert not (OUT / 'source-palettes.json').exists()
    OUT.mkdir(parents=True, exist_ok=True)
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}
    game = get_path('bg2ee_game_root', required=True)
    proof, sources, fixtures = {}, {}, {}

    def read(n, typ):
        raw = resolve_resource(bifs, key[n, typ])[0]
        over = game / 'override' / (n + ('.bam' if typ == 1000 else '.bmp'))
        if over.exists():
            live = over.read_bytes()
            if typ == 1000:
                unpack = lambda b: zlib.decompress(b[12:]) if b[:4] == b'BAMC' else b
                s, l = unpack(raw), unpack(live)
                so, lo = struct.unpack_from('<I', s, 16)[0], struct.unpack_from('<I', l, 16)[0]
                assert s[so:so+1024] == l[lo:lo+1024]
            else:
                assert raw == live
        proof[n] = dict(stock_sha256=hashlib.sha256(raw).hexdigest().upper(), active_palette_exact=True)
        return raw

    for name, expected in [('SHWATER', list(range(1,215))), ('SPBOOM', list(range(4,16)))]:
        packed = read(name, 1000)
        raw = zlib.decompress(packed[12:]) if packed[:4] == b'BAMC' else packed
        off = struct.unpack_from('<I', raw, 16)[0]
        pal = [int.from_bytes(raw[off+4*i:off+4*i+3], 'little') for i in range(256)]
        frames, _, tr = decode_bam(raw)
        used = sorted(set(int(i) for frame, *_ in frames for i in np.unique(frame)) - {tr})
        assert used == expected and len({pal[i] for i in used}) == len(used)
        sources[name] = pal
        fixtures[name+'base'] = [p | 0xff000000 for p in pal]
        proof[name].update(used_indices=used, used_RGB_unique=True, transparent_index=tr)
    for i in range(1,8):
        name = f'SHWATER{i}'
        raw = read(name, 1)
        assert raw[:2] == b'BM' and struct.unpack_from('<H', raw, 28)[0] == 8
        offset = 14 + struct.unpack_from('<I', raw, 14)[0]
        pixels = struct.unpack_from('<I', raw, 10)[0]
        count = (pixels - offset) // 4
        assert count == 217
        target = fixtures['SHWATERbase'].copy()
        for j in range(count):
            target[j] = int.from_bytes(raw[offset+4*j:offset+4*j+3], 'little') | 0xff000000
        fixtures[name] = target
        proof[name].update(BMP_palette_entries=count, all_used_indices_populated=True,
                           unused_tail='fixture filled from source; transfer must ignore indices215..255')
    ramps = np.asarray(Image.open(io.BytesIO(read('MPALETTE', 1))).convert('RGB'))
    assert ramps.shape == (256,12,3)
    for colour in (67,65,69):
        target = fixtures['SPBOOMbase'].copy()
        for i, rgb in enumerate(ramps[colour]):
            target[4+i] = int(rgb[0])<<16 | int(rgb[1])<<8 | int(rgb[2]) | 0xff000000
        fixtures[f'SPBOOM{colour}'] = target
    header = '#pragma once\n#include <array>\n#include <cstdint>\nnamespace iee::core::effect_indexed_palette {\n'
    for name, pal in sources.items():
        header += f'// {name}: stock BAM SHA256 {proof[name]["stock_sha256"]}; native-used indices pinned below.\n'
        header += f'inline constexpr std::array<std::uint32_t,256> {name.lower()}Source{{\n{array(pal)}\n}};\n'
    header += '}\n'
    (SOURCE / 'src/iee/core/effect_residual_projectile_palettes.h').write_text(header, encoding='utf-8')
    header = '#pragma once\n#include "iee/core/area_animation_lighting.h"\n'
    for name, pal in fixtures.items():
        header += f'inline constexpr iee::core::area_lighting::Palette fixture{name}{{\n{array(pal)}\n}};\n'
    (SOURCE / 'tests/effect_residual_projectile_palette_fixtures.h').write_text(header, encoding='utf-8')
    (OUT / 'source-palettes.json').write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    print('Pinned Water214 used indices/7 BMPs; Boom12 indices/3 native range colours; no image changes.')


if __name__ == '__main__':
    main()
