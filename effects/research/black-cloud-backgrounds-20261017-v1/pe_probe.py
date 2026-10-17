"""Read-only PE inspection; never runs game code or changes installed files."""
from pathlib import Path
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

raw = (get_path('bg2ee_game_root', required=True) / 'BaldurReal.exe').read_bytes()
pe = struct.unpack_from('<I', raw, 0x3C)[0]
count, optional = struct.unpack_from('<H', raw, pe + 6)[0], struct.unpack_from('<H', raw, pe + 20)[0]
image_base = struct.unpack_from('<Q', raw, pe + 48)[0]
sections = [struct.unpack_from('<8sIIII', raw, pe + 24 + optional + i * 40) for i in range(count)]
decoder = Cs(CS_ARCH_X86, CS_MODE_64)
for name, rva, size in [('VidPaletteRealize', 0x421430, 0x2200),
                         ('VvcRender', 0x254B00, 0x6F0),
                         ('ProjectileRender', 0x233F20, 0x750),
                         ('FxRender', 0x29DF60, 0x400),
                         ('PaletteDispatch', 0x42D2F0, 0x90),
                         ('PaletteResource', 0x42D350, 0x1800)]:
    section = next(s for s in sections if s[2] <= rva < s[2] + s[3])
    offset = section[4] + rva - section[2]
    lines = [f'{i.address-image_base:08X}  {i.mnemonic:8} {i.op_str}'
             for i in decoder.disasm(raw[offset:offset + size], image_base + rva)]
    (Path(__file__).parent / f'{name}.asm').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(name, len(lines))
