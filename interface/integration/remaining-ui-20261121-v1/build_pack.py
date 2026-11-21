"""Build the reversible in-game UI review pack from the 133 verified candidates."""
import hashlib
import io
import json
import re
import struct
import sys
import zlib
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / 'interface/experiments/remaining-ui-seedvr7b-x4-20261121-v1'
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import GAME_DIR, load_key, resolve_resource

MAX_SIDE = 1024
MAX_PIECE = 1012
PAGE_START = 7000
GAME = Path(GAME_DIR)
PACK = HERE / 'pack'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fnv(data):
    value = 14695981039346656037
    for byte in data:
        value = (value ^ byte) * 1099511628211 & 0xFFFFFFFFFFFFFFFF
    return value


def mos(size, blocks):
    return b'MOS V2  ' + struct.pack('<4I', *size, len(blocks), 24) + b''.join(
        struct.pack('<7I', *block) for block in blocks)


def bam(frames, source_cycles, blocks_by_key):
    entries = []
    blocks = []
    cycles = []
    for frame in frames:
        frame_blocks = blocks_by_key[frame['key']]
        entries.append((*frame['native_size'], *frame['center_native'], len(blocks), len(frame_blocks)))
        blocks.extend(frame_blocks)
    frame_entries = entries.copy()
    for sequence in source_cycles:
        first = sequence[0] if sequence else 0
        if sequence != list(range(first, first + len(sequence))):
            first = len(entries)
            entries.extend(frame_entries[i] for i in sequence)
        cycles.append((len(sequence), first))
        assert entries[first:first + len(sequence)] == [frame_entries[i] for i in sequence]
    cycle_offset = 32 + 12 * len(entries)
    block_offset = cycle_offset + 4 * len(cycles)
    return (b'BAM V2  ' + struct.pack('<6I', len(entries), len(cycles), len(blocks), 32,
                                     cycle_offset, block_offset)
            + b''.join(struct.pack('<HHhhHH', *entry) for entry in entries)
            + b''.join(struct.pack('<HH', *cycle) for cycle in cycles)
            + b''.join(struct.pack('<7I', *block) for block in blocks))


class Page:
    def __init__(self, number):
        self.number = number
        self.shelves = []
        self.bottom = 4
        self.right = 4
        self.pieces = []

    def place(self, piece):
        row, x, y, w, h = piece
        pw, ph = (w + 3) // 4 * 4 + 8, (h + 3) // 4 * 4 + 8
        for shelf in self.shelves:
            if shelf[1] >= ph and shelf[2] + pw <= MAX_SIDE:
                break
        else:
            if self.bottom + ph > MAX_SIDE:
                return None
            shelf = [self.bottom, ph, 0]
            self.shelves.append(shelf)
            self.bottom += ph
        px, py = shelf[2] + 4, shelf[0] + 4
        shelf[2] += pw
        self.right = max(self.right, shelf[2])
        self.pieces.append((row, x, y, w, h, px, py))
        return self.number, px, py, w, h, x, y


def dxt(image):
    buffer = io.BytesIO()
    image.save(buffer, format='DDS', pixel_format='DXT5')
    data = buffer.getvalue()
    assert data[84:88] == b'DXT5' and len(data) == 128 + image.width * image.height
    return data[128:]


@lru_cache(maxsize=3)
def open_rgba(path):
    with Image.open(path) as image:
        return image.convert('RGBA')


def put_piece(atlas, path, scale, x, y, w, h, px, py):
    region = open_rgba(path).crop(tuple(v * scale for v in (x, y, x + w, y + h)))
    pixels = np.pad(np.asarray(region), ((4 * scale, 4 * scale), (4 * scale, 4 * scale), (0, 0)),
                    mode='edge')
    atlas.paste(Image.fromarray(pixels), ((px - 4) * scale, (py - 4) * scale))


def page_images(page):
    width, height = (max(64, 1 << (size - 1).bit_length()) for size in (page.right, page.bottom))
    base = Image.new('RGBA', (width, height))
    high = Image.new('RGBA', (width * 4, height * 4))
    # A texel block outside all MOS/BAM rectangles keeps page fingerprints distinct.
    color = (page.number & 255, page.number >> 8, 255, 255)
    base.paste(color, (0, 0, 4, 4))
    high.paste(color, (0, 0, 16, 16))
    exact_alpha = np.ones((height, width), dtype=bool)
    for row, x, y, w, h, px, py in page.pieces:
        put_piece(base, RUN / 'sources' / f"{row['key']}-x1.png", 1, x, y, w, h, px, py)
        put_piece(high, ROOT / row['output'], 4, x, y, w, h, px, py)
        if not row['alpha_native_preserved']:
            exact_alpha[py - 4:py + h + 4, px - 4:px + w + 4] = False
    source = dxt(base)
    output = np.frombuffer(dxt(high), dtype=np.uint8).copy().reshape(height, width, 16)
    alpha = np.asarray(base.getchannel('A'))[exact_alpha]
    # One native pixel maps to one x4 DXT5 block. Equal endpoints and zero
    # indices represent its alpha exactly for all sixteen expanded pixels.
    output[exact_alpha, 0] = alpha
    output[exact_alpha, 1] = alpha
    output[exact_alpha, 2:8] = 0
    assert np.array_equal(output[exact_alpha, 0], alpha)
    pvr_header = struct.pack('<13I', 0x03525650, 0, 11, 0, 0, 0, height, width, 1, 1, 1, 1, 0)
    pvr = pvr_header + source
    pvrz = struct.pack('<I', len(pvr)) + zlib.compress(pvr, 6)
    return width, height, source, pvrz, output.tobytes()


def build_gallery(rows, blocks_by_key, emit):
    entries = []
    for index, frame in enumerate(rows, 1):
        resref = frame['resref']
        cycle = None
        for sequence_number, sequence in enumerate(frame['cycles']):
            if frame['frame'] in sequence:
                cycle = (sequence_number, sequence.index(frame['frame']))
                break
        mosaic = resref if frame['version'].startswith('MOS') else ''
        if not mosaic and cycle is None:
            mosaic = f'BGQ{index:04}'
            emit(f'override/{mosaic}.MOS', mos(frame['native_size'], blocks_by_key[frame['key']]))
        entries.append(dict(index=index, key=frame['key'], resref=resref, mosaic=mosaic,
                            native_size=frame['native_size'], version=frame['version'], bam_sequence_frame=cycle))
    lua_rows = []
    for item in entries:
        title = f"{item['key']}  |  {item['version']}  |  {item['index']} / {len(entries)}"
        seq, frame = item['bam_sequence_frame'] or (0, 0)
        use_bam = 'true' if item['bam_sequence_frame'] is not None else 'false'
        w, h = item['native_size']
        lua_rows.append(f'  {{"{item["mosaic"]}", "{item["resref"]}", "{title}", {use_bam}, {seq}, {frame}, {w}, {h}}},')
    lua = """BG2UIQA = {
  index = 1,
  loaded = false,
  rows = {
""" + '\n'.join(lua_rows) + """
  }
}
function BG2UIQA.current()
  return BG2UIQA.rows[BG2UIQA.index]
end
function BG2UIQA.layout()
  local row = BG2UIQA.current()
  local ratio = math.min(784 / row[7], 544 / row[8], 1)
  local w = math.max(1, math.floor(row[7] * ratio))
  local h = math.max(1, math.floor(row[8] * ratio))
  local x, y = math.floor((800 - w) / 2), 42 + math.floor((544 - h) / 2)
  Infinity_SetArea("BG2_UI_REVIEW_MOS", x, y, w, h)
  Infinity_SetArea("BG2_UI_REVIEW_BAM", x, y, w, h)
end
function BG2UIQA.move(delta)
  BG2UIQA.index = (BG2UIQA.index + delta - 1) % #BG2UIQA.rows + 1
  BG2UIQA.layout()
end
function BG2UIQA.load()
  if BG2UIQA.loaded then return end
  local loadMenu = EEex_Menu_LoadFile or EEex_LoadMenuFile
  loadMenu("BG2UIQA")
  BG2UIQA.loaded = true
  print("[BG2UIQA] Menu loaded, " .. #BG2UIQA.rows .. " entries")
end
function BG2UIReview(index)
  BG2UIQA.load()
  if index then
    local number = tonumber(index)
    if number then BG2UIQA.index = math.min(#BG2UIQA.rows, math.max(1, math.floor(number))) end
  end
  Infinity_PushMenu("BG2_UI_REVIEW")
end
if EEex_Menu_AddAfterMainFileLoadedListener then
  EEex_Menu_AddAfterMainFileLoadedListener(function()
    BG2UIQA.loaded = false
    BG2UIQA.load()
  end)
elseif EEex_AddPostResetListener then
  EEex_AddPostResetListener(function() BG2UIQA.loaded = false end)
end
"""
    emit('override/M_BG2UQA.lua', lua.encode('ascii'))
    controls = []
    for x, label, action in ((5, '<< 10', 'BG2UIQA.move(-10)'), (150, '<', 'BG2UIQA.move(-1)'),
                             (290, '>', 'BG2UIQA.move(1)'), (430, '10 >>', 'BG2UIQA.move(10)'),
                             (650, 'Fermer', "Infinity_PopMenu('BG2_UI_REVIEW')")):
        controls.append(f"""
  button
  {{
    area {x} 592 132 36
    text "{label}"
    text style "button"
    text align center center
    action "{action}"
  }}
""")
    menu = """menu
{
  name 'BG2_UI_REVIEW'
  align center center
  modal
  onOpen "BG2UIQA.layout()"
  label
  {
    area 0 0 800 36
    text lua "BG2UIQA.current()[3]"
    text style "title"
    text align center center
  }
  label
  {
    name "BG2_UI_REVIEW_MOS"
    area 8 42 784 544
    enabled "not BG2UIQA.current()[4]"
    mosaic lua "BG2UIQA.current()[1]"
    scaleToClip
  }
  label
  {
    name "BG2_UI_REVIEW_BAM"
    area 8 42 784 544
    enabled "BG2UIQA.current()[4]"
    bam lua "BG2UIQA.current()[2]"
    sequence lua "BG2UIQA.current()[5]"
    frame lua "BG2UIQA.current()[6]"
    scaleToClip
  }
""" + ''.join(controls) + '}\n'
    emit('override/BG2UIQA.menu', menu.encode('ascii'))
    return entries


def main():
    if (HERE / 'pack.json').exists():
        raise SystemExit('Existing pack manifest; use a new version.')
    result = json.loads((RUN / 'results.json').read_text(encoding='utf-8'))
    rows = result['results']
    assert len(rows) == result['expected_frames'] == 153 and len(result['complete_resources']) == 133
    bifs, keys = load_key()
    key_lookup = {(name.upper(), kind): locator for name, kind, locator in keys}
    occupied = {name.upper() for name, _, _ in keys}
    localized = GAME / 'lang/fr_FR/override'
    user_override = Path.home() / "Documents/Baldur's Gate II - Enhanced Edition/override"
    for folder in (GAME / 'override', localized, user_override):
        if folder.is_dir():
            occupied.update(path.stem.upper() for path in folder.iterdir())
    pieces = []
    frames_by_name = defaultdict(list)
    for row in rows:
        name, width, height = row['resref'], *row['native_size']
        assert re.fullmatch(r'[A-Z0-9_-]{1,8}', name), name
        assert sha((ROOT / row['output']).read_bytes()) == row['sha256']
        assert sha((RUN / 'sources' / f"{row['key']}-x1.png").read_bytes()) == row['source_sha256']
        ext = row['version'][:3]
        assert not any((folder / f'{name}.{ext}').exists() for folder in (localized, user_override)), name
        frames_by_name[name].append(row)
        for y in range(0, height, MAX_PIECE):
            for x in range(0, width, MAX_PIECE):
                pieces.append((row, x, y, min(MAX_PIECE, width-x), min(MAX_PIECE, height-y)))

    pages = []
    blocks_by_key = defaultdict(list)
    numbers = (n for n in range(PAGE_START, 10000) if f'MOS{n:04}' not in occupied)
    for piece in sorted(pieces, key=lambda p: (-p[-1], -p[-2], p[0]['key'], p[2], p[1])):
        for page in pages:
            block = page.place(piece)
            if block is not None:
                break
        else:
            page = Page(next(numbers))
            pages.append(page)
            block = page.place(piece)
        assert block is not None
        blocks_by_key[piece[0]['key']].append(block)
    files = {}

    def emit(name, content):
        path = PACK / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        files[name] = sha(content)

    registry = []
    atlas_records = []
    fingerprints = set()
    for page in pages:
        width, height, source, pvrz, output = page_images(page)
        fingerprint = fnv(source)
        assert (width, height, fingerprint) not in fingerprints
        fingerprints.add((width, height, fingerprint))
        registry.append(f'{page.number} {width} {height} {fingerprint:016X}')
        emit(f'override/MOS{page.number:04}.PVRZ', pvrz)
        emit(f'iee-assets/UIREVIEW-MOS{page.number:04}-x4.dxt5', output)
        atlas_records.append(dict(page=page.number, width=width, height=height,
                                  fnv1a64=f'{fingerprint:016X}',
                                  frames=sorted({piece[0]['key'] for piece in page.pieces})))
        print(f'MOS{page.number:04}: {width}x{height}, {len(page.pieces)} regions', flush=True)
    emit('iee-assets/ui-review-atlases.txt', ('\n'.join(registry) + '\n').encode('ascii'))

    resources = {}
    for name, frames in sorted(frames_by_name.items()):
        frames.sort(key=lambda frame: frame['frame'])
        fmt = frames[0]['version']
        if fmt.startswith('MOS'):
            assert len(frames) == 1
            data = mos(frames[0]['native_size'], blocks_by_key[name])
        else:
            data = bam(frames, frames[0]['cycles'], blocks_by_key)
        path = f'override/{name}.{fmt[:3]}'
        emit(path, data)
        resources[name] = dict(source_format=fmt, installed_format=fmt[:3] + ' V2',
                               frames=len(frames), path=path,
                               atlas_pages=sorted({block[0] for frame in frames
                                                  for block in blocks_by_key[frame['key']]}))
    gallery_rows = sorted(rows, key=lambda row: (row['category'], row['resref'], row['frame']))
    gallery = build_gallery(gallery_rows, blocks_by_key, emit)
    assert all(item['mosaic'].upper() not in occupied for item in gallery if item['mosaic'].startswith('BGQ'))
    assert not {'BG2UIQA', 'M_BG2UQA'} & occupied

    ui_file = GAME / 'override' / 'UI.MENU'
    ui_base = ui_file.read_bytes() if ui_file.exists() else resolve_resource(bifs, key_lookup['UI', 1032])[0]
    routes = defaultdict(list)
    current_menu = None
    waiting = False
    for number, line in enumerate(ui_base.decode('utf-8-sig').splitlines(), 1):
        if re.fullmatch(r'\s*menu\s*', line):
            waiting = True
        match = re.match(r'^\s*name\s+["\']([^"\']+)', line)
        if waiting and match:
            current_menu = match[1]
            waiting = False
        match = re.match(r'^\s*(mosaic|bam)\s+(?:["\']([^"\']+)|([\w-]+))', line)
        if match:
            name = (match[2] or match[3]).upper()
            kind = 'MOS' if match[1] == 'mosaic' else 'BAM'
            if name in resources and resources[name]['installed_format'].startswith(kind):
                routes[name].append([current_menu, number])
    pack = dict(files=files, resources=resources, pages=atlas_records, gallery=gallery, native_ui_refs=routes)
    (HERE / 'pack.json').write_text(json.dumps(pack, indent=2) + '\n', encoding='utf-8')
    print(f'{len(resources)} resources, {len(pages)} pages, {len(gallery)} gallery entries', flush=True)


if __name__ == '__main__':
    main()
