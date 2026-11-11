"""Prepare 8 MOS + 2 BAM families, preserving native frame geometry and alpha."""
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if (HERE / 'sources.json').exists():
    raise SystemExit('Existing source manifest; use a new run.')
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from mos_decode import decode_mos, decode_pvrz_page

bifs, entries = load_key()
index = {(n.upper(), k): loc for n, k, loc in entries}
proposal = json.loads((ROOT / 'interface/analysis/fifth-ten-20261111-v1/proposal.json').read_text(encoding='utf-8'))
template = json.loads((ROOT / 'interface/experiments/menus-seedvr-x4-7b-3b-20261110-v1/workflows/INVENTOR-7b-x4.api.json').read_text())
for folder in ('sources', 'inputs', 'workflows', 'outputs', 'comparison', 'jobs'):
    (HERE / folder).mkdir(exist_ok=True)
pages = {}


def page_image(page):
    if page not in pages:
        pages[page] = decode_pvrz_page(resolve_resource(bifs, index[f'MOS{page:04}', 1028])[0])
    return pages[page]


rows = []
graphs = {'first-five': {}, 'second-five': {}}
for graph in graphs.values():
    for node_id in ('66:51', '66:52'):
        graph[node_id] = template[node_id]
for item in proposal['items']:
    n = item['resref']
    kind = 1000 if n in ('DONATE', 'INNROOMS') else 1004
    raw, container = resolve_resource(bifs, index[n, kind])
    frames = []
    if kind == 1004:
        raw = zlib.decompress(raw[12:]) if raw[:4] == b'MOSC' else raw
        assert raw[:8] == b'MOS V2  '
        w, h, count, offset = struct.unpack_from('<4I', raw, 8)
        blocks = [struct.unpack_from('<7I', raw, offset + i * 28) for i in range(count)]
        frames.append((0, decode_mos(raw, page_image).convert('RGBA'), blocks))
    else:
        assert raw[:8] == b'BAM V2  '
        count, cycles, bc, fo, co, bo, pal = struct.unpack_from('<7I', raw, 8)
        for i in range(count):
            w, h, cx, cy, packed = struct.unpack_from('<HHhhI', raw, fo + i * 12)
            first, amount = packed & 65535, packed >> 16
            blocks = [struct.unpack_from('<7I', raw, bo + j * 28) for j in range(first, first + amount)]
            im = Image.new('RGBA', (w, h))
            for page, sx, sy, bw, bh, dx, dy in blocks:
                im.paste(page_image(page).crop((sx, sy, sx + bw, sy + bh)), (dx, dy))
            frames.append((i, im, blocks))
    for frame, im, blocks in frames:
        job = n if kind == 1004 else f'{n}-frame-{frame:02}'
        w, h = im.size
        pw, ph = (w + 63) // 64 * 64, (h + 63) // 64 * 64
        source = HERE / 'sources' / f'{job}-x1.png'
        im.save(source)
        input_name = f'UI50-20261111-{job}-padded.png'
        Image.fromarray(np.pad(np.array(im), ((0, ph - h), (0, pw - w), (0, 0)), mode='edge')).save(HERE / 'inputs' / input_name)
        row = dict(**item, job=job, frame=frame, kind='MOS' if kind == 1004 else 'BAM', container=container,
                   native_size=[w, h], padded_size=[pw, ph], expected_x4=[w * 4, h * 4], blocks=blocks,
                   source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        rows.append(row)
        group = 'first-five' if item['number'] <= 5 else 'second-five'
        graph = graphs[group]
        remap = {node_id: node_id if node_id in ('66:51', '66:52') else f'{job}__{node_id}' for node_id in template}
        for node_id, node in template.items():
            if node_id in ('66:51', '66:52'):
                continue
            node = json.loads(json.dumps(node))
            for key, value in node['inputs'].items():
                if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and value[0] in remap:
                    node['inputs'][key] = [remap[value[0]], value[1]]
            if node_id == '1':
                node['inputs']['image'] = input_name
            elif node_id == '9':
                node['inputs']['filename_prefix'] = f'BG2_UI50_7B_20261111/{job}-7b-x4'
            graph[remap[node_id]] = node
for name, graph in graphs.items():
    (HERE / 'workflows' / f'{name}-7b-x4.api.json').write_text(json.dumps(graph, indent=2) + '\n')
(HERE / 'sources.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{len(proposal["items"])} resources, {len(rows)} inference inputs, 2 shared-model workflows')
