"""Read-only selector audit. Run from repository root; output must be a new directory."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

from PIL import Image, ImageDraw

REPO = next(p for p in Path(__file__).resolve().parents if (p / 'pipeline/scripts').is_dir())
sys.path.insert(0, str(REPO / 'pipeline/scripts'))
from bg2lib import GAME_DIR, load_key, resolve_resource
from mos_decode import decode_mos_v2, decode_pvrz_page


def fnv(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return f'{value:016X}'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output
    out.mkdir(parents=True, exist_ok=False)
    game = Path(GAME_DIR)
    root = REPO / 'interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50'
    selector = root / 'selection-des-trois-jeux'
    bifs, entries = load_key()
    index = {(name.upper(), kind): locator for name, kind, locator in entries}

    def resource(name, kind, ext):
        original, bif = resolve_resource(bifs, index[name.upper(), kind])
        override = game / 'override' / f'{name}.{ext}'
        return (override.read_bytes() if override.exists() else original), bif, str(override) if override.exists() else None

    page_images = {}

    def page_image(page):
        if page not in page_images:
            page_images[page] = decode_pvrz_page(resource(f'MOS{page:04d}', 1028, 'pvrz')[0])
        return page_images[page]

    cpp = (REPO / 'engine/InfinityEngine-Enhancer/source-patchee/src/iee/biglogo_ui_upscale.cpp').read_text()
    registered = {int(p): f for p, f in re.findall(r'\{"MOS(\d+)\.PVRZ".*?0x([0-9A-F]+)ull', cpp, re.S)}
    pages = []
    for page in (152, 153, 181, 182, 183, 184, 185, 258, 259):
        name = f'MOS{page:04d}'
        compressed, bif, override = resource(name, 1028, 'pvrz')
        pvr = zlib.decompress(compressed[4:])
        meta = struct.unpack_from('<I', pvr, 48)[0]
        payload = pvr[52 + meta:]
        height, width = struct.unpack_from('<II', pvr, 24)
        stem = f'{"MAINMENU" if page in (181, 258) else "SELECTOR"}-{name}-x4.dxt5'
        production, installed = selector / 'assets' / stem, game / 'iee-assets' / stem
        old = selector / 'sources/pages' / f'{name}-x1.png'
        old_match = None
        if old.exists():
            with Image.open(old) as im:
                old_match = im.convert('RGBA').tobytes() == page_image(page).convert('RGBA').tobytes()
        pages.append(dict(page=name, source_bif=bif, override=override, width=width, height=height,
                          dxt5_bytes=len(payload), dxt5_fnv=fnv(payload), pvrz_fnv=fnv(compressed),
                          registered_fnv=registered.get(page), fingerprint_matches=registered.get(page) == fnv(payload),
                          source_pixels_match_historical_png=old_match,
                          production=str(production.relative_to(REPO)) if production.exists() else None,
                          production_sha256=sha(production), installed_sha256=sha(installed),
                          installed_matches_production=sha(production) == sha(installed) if production.exists() else None))

    resources, previews = [], []
    names = [('START3EE', 'fond, titre BG2EE, couvertures, titres imprimes, logo D&D', 1004),
             ('LOGOSOA', 'embleme Shadows of Amn', 1000), ('LOGOTOB', 'embleme Throne of Bhaal', 1000),
             ('LOGOTBP', 'embleme Black Pits II', 1000), ('GUIOSTUL', 'bouton Credits', 1000),
             ('GUIOSTUM', 'bouton Quitter', 1000), ('GUIOSTUR', 'bouton Options', 1000),
             ('MAINEEAN', 'lot historique hors menu START actuel', 1000)]
    for name, role, kind in names:
        data, bif, override = resource(name, kind, 'mos' if kind == 1004 else 'bam')
        frames, cycles = [], []
        if kind == 1004:
            w, h, count, offset = struct.unpack_from('<4I', data, 8)
            blocks = [struct.unpack_from('<7I', data, offset + i * 28) for i in range(count)]
            frames = [(w, h, blocks)]
        else:
            fc, cc, bc, fo, co, bo, _ = struct.unpack_from('<7I', data, 8)
            cycles = [struct.unpack_from('<HH', data, co + i * 4) for i in range(cc)]
            for i in range(fc):
                w, h, _, _, packed = struct.unpack_from('<HHhhI', data, fo + i * 12)
                blocks = [struct.unpack_from('<7I', data, bo + j * 28) for j in range(packed & 65535, (packed & 65535) + (packed >> 16))]
                frames.append((w, h, blocks))
        dependencies = sorted({block[0] for _, _, blocks in frames for block in blocks})
        resources.append(dict(resref=name, role=role, source_bif=bif, source_sha256=hashlib.sha256(data).hexdigest(),
                              override=override, frames=len(frames), cycles=cycles, pages=dependencies,
                              sizes=sorted({(w, h) for w, h, _ in frames}), active_in_START=name != 'MAINEEAN'))
        w, h, blocks = frames[0]
        image = Image.new('RGBA', (w, h))
        for p, sx, sy, bw, bh, dx, dy in blocks:
            image.paste(page_image(p).crop((sx, sy, sx + bw, sy + bh)), (dx, dy))
        previews.append((name, image))

    config_path = game / 'InfinityEngine-Enhancer.ini'
    config_text = config_path.read_text(errors='replace')
    installed_dll = (game / 'InfinityEngine-Enhancer.dll').read_bytes()
    for page in pages:
        for field in ('registered_fnv', 'dxt5_fnv'):
            page[field + '_in_installed_dll'] = struct.pack('<Q', int(page[field], 16)) in installed_dll if page[field] else None
    fonts = []
    for kind, ext in ((1000, 'bam'), (1024, 'fnt'), (1034, 'ttf')):
        data, bif, override = resource('STONESML', kind, ext)
        fonts.append(dict(resref='STONESML', format=ext, source_bif=bif, size=len(data), override=override))
    flags = {}
    for key in ('EnableBigLogoX4Test', 'EnableMainMenuX4Test', 'EnableMenuX2Test'):
        match = re.search(r'^\s*' + key + r'\s*=\s*(\S+)', config_text, re.M | re.I)
        flags[key] = dict(explicit=match.group(1) if match else None, effective=bool(match and match.group(1).lower() in ('true', '1')))
    ui, _, _ = resource('UI', 1032, 'menu')
    lines = ui.decode('utf-8-sig').splitlines()
    start = next(i for i, line in enumerate(lines) if re.search(r"name\s+'START'\s*$", line))
    end = next(i for i in range(start + 1, len(lines)) if re.search(r"name\s+'START_MAIN'\s*$", lines[i]))
    (out / 'UI-START.txt').write_text('\n'.join(f'{i+1}: {lines[i]}' for i in range(start - 2, end - 2)) + '\n', encoding='utf-8')
    report = dict(schema='bg2-selector-analysis-v1', date='2026-11-10', mode='read-only game audit',
                  game_root='config://bg2ee_game_root', game_config_sha256=sha(config_path),
                  installed_renderer_sha256=sha(game / 'InfinityEngine-Enhancer.dll'),
                  flags=flags, pages=pages, resources=resources, fonts=fonts,
                  text=dict(button_style='STONESML 10pt; BGEE.lua:2884',
                            version_style='STONESML label with point override 10; UI.menu:7300',
                            translations='L_fr_FR.lua:204,565,591 (cp1252)',
                            buttons=['CRÉDITS', 'QUITTER LA PARTIE', 'OPTIONS'],
                            version='versionString supplied by engine; no raster upscale'),
                  topaz_exports=len(list((selector / 'upscale-topaz-recovery-v2-d50').glob('*.png'))))
    (out / 'audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for name, rows in [('pages', pages), ('resources', resources)]:
        with (out / f'{name}.csv').open('w', newline='', encoding='utf-8-sig') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    canvas = Image.new('RGB', (1500, 1040), '#222222')
    draw = ImageDraw.Draw(canvas)
    bg = previews[0][1].convert('RGB').resize((900, 675))
    canvas.paste(bg, (10, 30))
    draw.text((10, 10), 'START3EE : fond natif complet (logo D&D et titres inclus)', fill='white')
    for i, (name, im) in enumerate(previews[1:]):
        x, y = (930, 10 + i * 142) if i < 4 else (10 + (i - 4) * 490, 750)
        draw.text((x, y), f'{name} - frame 0 native', fill='white')
        im = im.copy()
        im.thumbnail((460, 118), Image.Resampling.LANCZOS)
        canvas.paste(im, (x, y + 20), im)
    canvas.save(out / 'assets-overview.png')
    print(json.dumps({'output': str(out), 'resources': len(resources), 'pages': len(pages),
                      'installed_exact': sum(p['installed_matches_production'] is True for p in pages),
                      'fingerprint_mismatches': [p['page'] for p in pages if p['registered_fnv'] and not p['fingerprint_matches']]}))


if __name__ == '__main__':
    main()
