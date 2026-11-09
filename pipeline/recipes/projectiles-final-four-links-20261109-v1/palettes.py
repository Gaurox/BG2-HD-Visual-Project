"""Pin native source palettes/BMPs; emit constants/fixtures, never image assets."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from workspace_paths import get_path

OUT = ROOT / 'projectiles/analysis/final-four-links-20261109-v1'
SOURCE = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee'


def palette(raw):
    return [int.from_bytes(raw[i:i + 3], 'little') for i in range(0, 1024, 4)]


def array(values):
    return ',\n'.join('  ' + ','.join(f'0x{v:08x}u' for v in values[i:i + 8]) for i in range(0, len(values), 8))


def main():
    assert not (OUT / 'source-palettes.json').exists()
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}
    game = get_path('bg2ee_game_root', required=True)
    arrays, fixtures, proof = {}, {}, {}
    for name in ['SHAIR', 'SHEARTH', 'HLYMITE']:
        raw, _ = resolve_resource(bifs, key[name, 1000])
        source_hash = hashlib.sha256(raw).hexdigest().upper()
        source = zlib.decompress(raw[12:]) if raw[:4] == b'BAMC' else raw
        po = struct.unpack_from('<I', source, 16)[0]
        pal = palette(source[po:po + 1024])
        active = game / 'override' / (name + '.bam')
        if active.exists():
            live = active.read_bytes()
            live = zlib.decompress(live[12:]) if live[:4] == b'BAMC' else live
            p = struct.unpack_from('<I', live, 16)[0]
            assert live[p:p + 1024] == source[po:po + 1024]
        arrays[name] = pal
        fixtures[name] = [v | 0xff000000 for v in pal]
        proof[name] = dict(source_SHA256=source_hash, active_source_palette_exact=True,
                           unique_nontransparent_RGB=len(set(pal[1:])), transparent_index=source[11])
    for name in ['SHAIR4', 'SHEARTH6']:
        raw, _ = resolve_resource(bifs, key[name, 1])
        assert raw[:2] == b'BM' and struct.unpack_from('<H', raw, 28)[0] == 8
        fixtures[name] = [v | 0xff000000 for v in palette(raw[54:1078])]
        proof[name] = dict(BMP_SHA256=hashlib.sha256(raw).hexdigest().upper())
    header = '#pragma once\n#include <array>\n#include <cstdint>\n#include <utility>\nnamespace iee::core::effect_indexed_palette {\n'
    for name, pal in arrays.items():
        header += f'// Native {name}, BAM SHA256 {proof[name]["source_SHA256"]}\n'
        header += f'inline constexpr std::array<std::uint32_t,256> {name.lower()}Source{{\n{array(pal)}\n}};\n'
    pairs = [(i, j) for i in range(1, 256) for j in range(i + 1, 256)
             if arrays['HLYMITE'][i] == arrays['HLYMITE'][j]]
    header += f'inline constexpr std::array<std::pair<unsigned,unsigned>,{len(pairs)}> hlymiteDuplicatePairs{{{{'
    header += ','.join('{' + f'{i},{j}' + '}' for i, j in pairs) + '}};\n}\n'
    proof['HLYMITE']['duplicate_RGB_pairs'] = pairs
    (SOURCE / 'src/iee/core/effect_native_projectile_palettes.h').write_text(header, encoding='utf-8')
    header = '#pragma once\n#include "iee/core/area_animation_lighting.h"\n// Native base palettes and exact BMP variants, generated from KEY/BIF.\n'
    for name, pal in fixtures.items():
        header += f'inline constexpr iee::core::area_lighting::Palette fixture{name}{{\n{array(pal)}\n}};\n'
    (SOURCE / 'tests/effect_native_projectile_palette_fixtures.h').write_text(header, encoding='utf-8')
    (OUT / 'source-palettes.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print('Pinned 3 native source palettes and SHAIR4/SHEARTH6 BMP fixtures; no pixels changed.')


if __name__ == '__main__':
    main()
