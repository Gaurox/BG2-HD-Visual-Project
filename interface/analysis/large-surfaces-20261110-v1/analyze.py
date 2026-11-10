"""Inventory native UI references for the large-surface-only scope; no game writes."""
import csv
import json
import re
import struct
import sys
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = next(p for p in Path(__file__).resolve().parents if (p / 'pipeline/scripts').is_dir())
sys.path.insert(0, str(REPO / 'pipeline/scripts'))
from bg2lib import GAME_DIR, load_key, resolve_resource
from mos_decode import decode_mos, decode_pvrz_page
from bam_export import decode_bam

ROOT = Path(__file__).resolve().parent
bifs, entries = load_key()
index = {(n.upper(), kind): locator for n, kind, locator in entries}
game = Path(GAME_DIR)


def resource(name, kind, ext):
    override = game / 'override' / (name + '.' + ext)
    if override.exists():
        return override.read_bytes(), 'override'
    if (name, kind) not in index:
        return None, None
    return resolve_resource(bifs, index[name, kind])


pages = {}


def page_image(page):
    if page not in pages:
        pages[page] = decode_pvrz_page(resource(f'MOS{page:04d}', 1028, 'pvrz')[0])
    return pages[page]


ui, _ = resource('UI', 1032, 'menu')
menu, awaiting, refs = 'PREAMBLE', False, []
for number, line in enumerate(ui.decode('utf-8-sig').splitlines(), 1):
    if re.match(r'^\s*menu\s*$', line):
        awaiting = True
    match = re.match(r'^\s*name\s+["\']([^"\']+)', line)
    if awaiting and match:
        menu, awaiting = match[1], False
    match = re.match(r'^\s*(mosaic|bam|bitmap|scrollbar)\s+(?:["\']([^"\']+)["\']|(\w+))', line)
    if match and (name := (match[2] or match[3]).upper()) != 'LUA':
        refs.append(dict(menu=menu, property=match[1], resref=name, ui_line=number))

rows, images = [], {}
control_mos = {'GUISLDR'}
small_mos = {'DLGDIVI', 'PAPERSEP', 'PCHAPTER', 'GUWBTP10', 'GUWBTP20'}
research_mos = {'GUWBTP30'}
for name in sorted({r['resref'] for r in refs if r['property'] == 'mosaic'}):
    data, source = resource(name, 1004, 'mos')
    uses = [r for r in refs if r['resref'] == name and r['property'] == 'mosaic']
    if data is None:
        rows.append(dict(resref=name, kind='MOS', width=0, height=0, frames=0, source=None,
                         menus=sorted({r['menu'] for r in uses}), ui_lines=[r['ui_line'] for r in uses],
                         pages=[], status='unresolved-reference'))
        continue
    if data[:4] == b'MOSC':
        data = zlib.decompress(data[12:])
    image = decode_mos(data, page_image)
    dependencies = []
    if data[:8] == b'MOS V2  ':
        count, offset = struct.unpack_from('<II', data, 16)
        dependencies = sorted({struct.unpack_from('<I', data, offset + j * 28)[0] for j in range(count)})
    status = ('exclude-controls' if name in control_mos else 'exclude-small-decoration' if name in small_mos
              else 'exclude-debug' if name in research_mos else 'keep-surface-candidate')
    rows.append(dict(resref=name, kind='MOS', width=image.width, height=image.height, frames=1,
                     source=source, menus=sorted({r['menu'] for r in uses}), ui_lines=[r['ui_line'] for r in uses],
                     pages=dependencies, status=status))
    images[name] = image

for name in sorted({r['resref'] for r in refs if r['property'] == 'bam'}):
    data, source = resource(name, 1000, 'bam')
    if data is None:
        continue
    if data[:4] == b'BAMC':
        data = zlib.decompress(data[12:])
    dependencies = []
    if data[:8] == b'BAM V2  ':
        count, _, _, offset, _, block_offset, _ = struct.unpack_from('<7I', data, 8)
        frames = []
        for i in range(count):
            w, h, _, _, packed = struct.unpack_from('<HHhhI', data, offset + i * 12)
            first, amount = packed & 65535, packed >> 16
            blocks = [struct.unpack_from('<7I', data, block_offset + j * 28) for j in range(first, first + amount)]
            frames.append((w, h, blocks))
        w, h, blocks = max(frames, key=lambda f: f[0] * f[1])
        dependencies = sorted({b[0] for _, _, frame_blocks in frames for b in frame_blocks})
        if w * h < 35000:
            continue
        image = Image.new('RGBA', (w, h))
        for page, sx, sy, bw, bh, dx, dy in blocks:
            image.paste(page_image(page).crop((sx, sy, sx + bw, sy + bh)), (dx, dy))
    elif data[:8] == b'BAM V1  ':
        count = struct.unpack_from('<H', data, 8)[0]
        offset = struct.unpack_from('<I', data, 12)[0]
        dimensions = [struct.unpack_from('<HH', data, offset + i * 12) for i in range(count)]
        w, h = max(dimensions, key=lambda f: f[0] * f[1])
        if w * h < 35000:
            continue
        decoded, rgb, transparent = decode_bam(data)
        frame = max(decoded, key=lambda f: f[0].size)[0]
        import numpy as np
        image = Image.fromarray(np.dstack([rgb[frame], (frame != transparent).astype(np.uint8) * 255]), 'RGBA')
    else:
        continue
    uses = [r for r in refs if r['resref'] == name and r['property'] == 'bam']
    rows.append(dict(resref=name, kind='BAM', width=w, height=h, frames=count, source=source,
                     menus=sorted({r['menu'] for r in uses}), ui_lines=[r['ui_line'] for r in uses],
                     pages=dependencies, status='user-decision-pending'))
    images[name] = image

# Preserve supplementary catalogue rows collected during visual review.
previous_inventory = ROOT / 'inventory.json'
if previous_inventory.exists():
    known = {row['resref'] for row in rows}
    rows.extend(row for row in json.loads(previous_inventory.read_text(encoding='utf-8'))['resources']
                if row['resref'] not in known)

decisions_path = ROOT / 'decisions.json'
if decisions_path.exists():
    decisions = json.loads(decisions_path.read_text(encoding='utf-8'))
    for decision in decisions['decisions']:
        for row in rows:
            if row['resref'] not in decision['resrefs']:
                continue
            if decision['decision'] == 'do-not-treat':
                row['status'] = 'exclude-user-confirmed'
            elif decision['decision'] == 'keep-existing-upscale':
                row['status'] = 'keep-existing-x4-user-confirmed'
            else:
                row['status'] = ('keep-large-decoration-user-confirmed' if row['kind'] == 'MOS'
                                 else 'keep-large-art-user-confirmed-soft-alpha' if row['resref'] == 'DONATE'
                                 else 'keep-large-art-user-confirmed')

(ROOT / 'previews').mkdir(exist_ok=True)
for name, image in images.items():
    image.save(ROOT / 'previews' / (name + '.png'))
with (ROOT / 'resources.csv').open('w', encoding='utf-8-sig', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
(ROOT / 'inventory.json').write_text(json.dumps(dict(schema='bg2-ui-large-surface-scope-v1',
    status=decisions.get('state', 'interactive-visual-review-in-progress') if decisions_path.exists()
           else 'interactive-visual-review-in-progress', static_references=refs, resources=rows,
    limits=['Static UI.menu references only; engine/Lua-selected chapter images and world maps require separate routing.',
            'A MOS may contain painted slot/button ornament; keep-surface-candidate is not blanket pixel approval.',
            'Small BAM controls intentionally omitted; no production/installation/release changes.']), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
ordered = ['INVENTOR', 'GUIREC2', 'STONEOPT', 'GUITUTB', 'GUICHISD', 'GUICGB', 'GUIMGB', 'GUIPRB',
           'GUIINVHI', 'GUISTBSC', 'GUISTROB', 'QUESTBAK', 'GUILOAD', 'GUISMBM', 'GUIMOVB', 'GUICONNB']
sheet = Image.new('RGB', (1600, 1380), '#242321')
draw = ImageDraw.Draw(sheet)
for i, name in enumerate(ordered):
    x, y = (i % 4) * 400, (i // 4) * 345
    draw.text((x + 12, y + 8), name, font=font, fill='white')
    image = images[name].copy()
    image.thumbnail((376, 275), Image.Resampling.LANCZOS)
    sheet.paste(image, (x + 12, y + 40), image)
    dimensions = images[name].size
    draw.text((x + 12, y + 317), f'{dimensions[0]} x {dimensions[1]} — source native', font=small, fill='#cccccc')
sheet.save(ROOT / 'surfaces-overview.png')
print(json.dumps(dict(resources=len(rows), statuses={s: sum(r['status'] == s for r in rows) for s in sorted({r['status'] for r in rows})}, large_bam=[r['resref'] for r in rows if r['kind'] == 'BAM'])))
