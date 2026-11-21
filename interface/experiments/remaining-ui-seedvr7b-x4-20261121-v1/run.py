"""Resume the remaining UI production run against the local ComfyUI API."""
import argparse
import copy
import hashlib
import html
import json
import os
import struct
import sys
import time
import zlib
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam, native_palette_alpha
from bg2lib import GAME_DIR, load_key, resolve_resource
from mos_decode import decode_mos, decode_pvrz_page

PREFIX = 'BG2-UI-remaining-20261121-v1'
PENDING = {'not-assessed', 'partial-existing-x4'}
TEMPLATE = ROOT / 'interface/experiments/menus-seedvr-x4-7b-3b-20261110-v1/workflows/INVENTOR-7b-x4.api.json'
TRACKER = ROOT / 'interface/index/work-tracking.json'
SERVER = 'http://127.0.0.1:8188'
RECIPE = dict(model='seedvr2_7b_int8_convrot.safetensors', scale=4,
              color_correction='lab', seed=959948902156062, steps=1, cfg=1,
              sampler='euler', scheduler='simple')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blocks_at(data, offset, first, count):
    return [struct.unpack_from('<7I', data, offset + i * 28) for i in range(first, first + count)]


def native_frames(data, page):
    signature = data[:8]
    if signature.startswith(b'MOS '):
        image = decode_mos(data, page).convert('RGBA')
        blocks = []
        if signature == b'MOS V2  ':
            _, _, count, offset = struct.unpack_from('<4I', data, 8)
            blocks = blocks_at(data, offset, 0, count)
        else:
            rgb = np.asarray(image)[:, :, :3]
            image.putalpha(Image.fromarray((~np.all(rgb == (0, 255, 0), axis=2)).astype(np.uint8) * 255))
        return [(image, None, blocks)], []

    if signature == b'BAM V1  ':
        decoded, rgb, transparent = decode_bam(data)
        alpha = native_palette_alpha(data, transparent)
        _, cycle_count, _ = struct.unpack_from('<HBB', data, 8)
        offset, _, lookup = struct.unpack_from('<III', data, 12)
        cycles = []
        for i in range(cycle_count):
            count, first = struct.unpack_from('<HH', data, offset + len(decoded) * 12 + i * 4)
            cycles.append(list(struct.unpack_from(f'<{count}H', data, lookup + first * 2)))
        frames = [(Image.fromarray(np.dstack((rgb[idx], alpha[idx]))), [cx, cy], [])
                  for idx, cx, cy, _ in decoded]
        return frames, cycles

    assert signature == b'BAM V2  ', signature
    count, cycle_count, _, frames_offset, cycles_offset, blocks_offset = struct.unpack_from('<6I', data, 8)
    cycles = []
    for i in range(cycle_count):
        length, first = struct.unpack_from('<HH', data, cycles_offset + i * 4)
        cycles.append(list(range(first, first + length)))
    frames = []
    for i in range(count):
        width, height, cx, cy, first, length = struct.unpack_from('<HHhhHH', data, frames_offset + i * 12)
        blocks = blocks_at(data, blocks_offset, first, length)
        image = Image.new('RGBA', (width, height))
        for number, sx, sy, w, h, dx, dy in blocks:
            image.paste(page(number).crop((sx, sy, sx + w, sy + h)), (dx, dy))
        frames.append((image, [cx, cy], blocks))
    return frames, cycles


def tiles(width, height):
    if ((width + 63) // 64) * ((height + 63) // 64) <= 200 and max(width, height) <= 1536:
        return [(0, 0, width, height)]
    # Spread the tile starts evenly to avoid a thin last tile.
    def starts(length):
        count = max(1, (length - 96 + 607) // 608)
        return [round(i * (length - 704) / (count - 1)) for i in range(count)] if count > 1 else [0]
    return [(x, y, min(x + 704, width), min(y + 704, height))
            for y in starts(height) for x in starts(width)]


def prepare():
    if (RUN / 'sources.json').exists():
        return read(RUN / 'sources.json')
    for folder in ('sources', 'inputs', 'workflows', 'jobs', 'raw', 'outputs'):
        (RUN / folder).mkdir(exist_ok=True)
    bifs, entries = load_key()
    index = {(name.upper(), kind): locator for name, kind, locator in entries}
    game = Path(GAME_DIR)
    overrides = [Path.home() / "Documents/Baldur's Gate II - Enhanced Edition/override",
                 game / 'lang/fr_FR/override', game / 'override']

    def resource(name, ext, kind):
        for folder in overrides:
            path = folder / f'{name}.{ext}'
            if path.exists():
                return path.read_bytes(), str(path)
        return resolve_resource(bifs, index[name, kind])

    @lru_cache(maxsize=24)
    def page(number):
        return decode_pvrz_page(resource(f'MOS{number:04}', 'pvrz', 1028)[0])

    rows = []
    jobs = {}
    seen = {}
    resources = read(TRACKER)['resources']
    retained = {}
    for item in resources:
        if item['production']['state'] not in {'complete-existing-x4', 'complete-selected-x4'}:
            continue
        for path in item['production'].get('evidence', []):
            out = ROOT / path
            if out.suffix != '.png' or out.parent.name != item['resref'] or not out.is_file():
                continue
            job = out.stem.removesuffix('-seedvr-7b-x4')
            if job == out.stem:
                continue
            source = out.parents[2] / 'sources' / f'{job}-x1.png'
            frame = str(int(job.rsplit('-', 1)[-1])) if '-frame-' in job else '0'
            if not source.is_file() or sha(out) != item['production'].get('sha256_by_frame', {}).get(frame):
                continue
            with Image.open(source) as image:
                image = image.convert('RGBA')
                key = (image.size, hashlib.sha256(image.tobytes()).hexdigest())
            retained[key] = path

    for item in resources:
        current = item['production']
        if current['state'] not in PENDING:
            continue
        name, kind = item['resref'], item['kind']
        raw, container = resource(name, kind.lower(), 1004 if kind == 'MOS' else 1000)
        data = zlib.decompress(raw[12:]) if raw[:4] in (b'MOSC', b'BAMC') else raw
        frames, cycles = native_frames(data, page)
        assert len(frames) == item['source']['frames'], name
        for frame, (image, center, blocks) in enumerate(frames):
            key = name if kind == 'MOS' else f'{name}-frame-{frame:02}'
            source = RUN / 'sources' / f'{key}-x1.png'
            image.save(source)
            width, height = image.size
            identity = (image.size, hashlib.sha256(image.tobytes()).hexdigest())
            row = dict(resref=name, category=item['category'], key=key, frame=frame, container=str(container),
                       version=data[:8].decode().strip(), native_size=[width, height], center_native=center,
                       cycles=cycles, blocks=blocks, source_sha256=sha(source), tiles=[])
            rows.append(row)
            reuse = current['evidence'][0] if name == 'BIGLOGO' and frame == 0 else retained.get(identity)
            if reuse:
                with Image.open(ROOT / reuse) as previous:
                    assert previous.size == (width * 4, height * 4), (key, previous.size)
                row['reuse'] = reuse
                continue
            if identity in seen:
                row['identical_to'] = seen[identity]
                continue
            seen[identity] = key
            pixels = np.array(image)
            alpha = pixels[:, :, 3]
            if not np.any(alpha):
                row['empty'] = True
                continue
            if np.any(alpha == 0):
                # Give the network neighbouring RGB under transparent pixels; alpha is carried separately.
                nearest = distance_transform_edt(alpha == 0, return_distances=False, return_indices=True)
                pixels[:, :, :3] = pixels[nearest[0], nearest[1], :3]
            boxes = tiles(width, height)
            for i, (x, y, right, bottom) in enumerate(boxes):
                suffix = f'-tile-{i+1:02}' if len(boxes) > 1 else ''
                job = key + suffix
                pw, ph = (right - x + 63) // 64 * 64, (bottom - y + 63) // 64 * 64
                input_name = f'{PREFIX}-{job}.png'
                padded = np.pad(pixels[y:bottom, x:right], ((0, ph - bottom + y), (0, pw - right + x), (0, 0)),
                                mode='edge')
                Image.fromarray(padded).save(RUN / 'inputs' / input_name)
                tile = dict(job=job, box=[x, y, right, bottom], padded=[pw, ph], input=input_name)
                row['tiles'].append(tile)
                jobs[job] = tile

    # Limit each Comfy prompt to a few assets, sharing model loaders. All prompts
    # are queued in one campaign so a failing prompt does not invalidate the rest.
    ordered = list(jobs.values())
    first = {'DLGDIVI': 0, 'GUWBTP10': 1, 'GUIW12_1': 2, 'GU20BKMD-tile-01': 3}
    ordered.sort(key=lambda t: first.get(t['job'], 4))
    groups = [ordered[:1], ordered[1:4]]
    groups.extend(ordered[i:i + 4] for i in range(4, len(ordered), 4))
    template = read(TEMPLATE)
    shared = {'66:51', '66:52'}
    batches = []
    for number, group in enumerate(groups, 1):
        graph = {node: template[node] for node in shared}
        names = {}
        for tile in group:
            job = tile['job']
            ids = {node: node if node in shared else f'{job}__{node}' for node in template}
            names[ids['9']] = job
            for node_id, original in template.items():
                if node_id in shared:
                    continue
                node = copy.deepcopy(original)
                for key, value in node['inputs'].items():
                    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and value[0] in ids:
                        node['inputs'][key] = [ids[value[0]], value[1]]
                if node_id == '1':
                    node['inputs']['image'] = tile['input']
                if node_id == '9':
                    node['inputs']['filename_prefix'] = f'{PREFIX}/{job}-7b-x4'
                graph[ids[node_id]] = node
        filename = f'workflow-{number:02}.json'
        write(RUN / 'workflows' / filename, graph)
        batches.append(dict(workflow=filename, nodes=names, inputs=[tile['input'] for tile in group]))
    manifest = dict(rows=rows, batches=batches, recipe=RECIPE)
    write(RUN / 'sources.json', manifest)
    print(f'{len(rows)} native frames, {len(jobs)} inference inputs, {len(batches)} prompts', flush=True)
    return manifest


def submit(manifest, limit=None):
    receipts = RUN / 'jobs/submitted.json'
    submitted = read(receipts) if receipts.exists() else {}
    with requests.Session() as session:
        for batch in manifest['batches'][:limit]:
            name = batch['workflow']
            if name in submitted:
                continue
            for filename in batch['inputs']:
                with (RUN / 'inputs' / filename).open('rb') as image:
                    response = session.post(f'{SERVER}/upload/image',
                                            files={'image': (filename, image, 'image/png')},
                                            data={'type': 'input', 'overwrite': 'false'}, timeout=90)
                    response.raise_for_status()
                    uploaded = response.json()
                    assert uploaded['name'] == filename and not uploaded.get('subfolder'), uploaded
            response = session.post(f'{SERVER}/prompt', json={'prompt': read(RUN / 'workflows' / name)},
                                    timeout=60)
            if not response.ok:
                raise RuntimeError(response.text)
            submitted[name] = response.json()['prompt_id']
            write(receipts, submitted)
            print(f'Queued {name}: {submitted[name]}', flush=True)


def collect(manifest):
    submitted = read(RUN / 'jobs/submitted.json')
    failure = []
    with requests.Session() as session:
        history_response = session.get(f'{SERVER}/history', params={'max_items': 100}, timeout=30)
        history_response.raise_for_status()
        history = history_response.json()
        for batch in manifest['batches']:
            prompt = submitted.get(batch['workflow'])
            record = history.get(prompt, {})
            if record.get('status', {}).get('status_str') == 'error':
                failure.append(dict(workflow=batch['workflow'], prompt_id=prompt,
                                    status=record.get('status')))
            for node, job in batch['nodes'].items():
                target = RUN / 'raw' / f'{job}.png'
                files = record.get('outputs', {}).get(node, {}).get('images', [])
                if target.is_file() or not files:
                    continue
                response = session.get(f'{SERVER}/view', params=files[0], timeout=120)
                response.raise_for_status()
                tmp = target.with_suffix('.tmp')
                tmp.write_bytes(response.content)
                with Image.open(tmp) as img:
                    img.verify()
                tmp.replace(target)
    return failure


def merge(row):
    width, height = row['native_size']
    footprint = (width * 4, height * 4)
    if row.get('empty'):
        return Image.new('RGB', footprint)
    if len(row['tiles']) == 1:
        tile, = row['tiles']
        with Image.open(RUN / 'raw' / f"{tile['job']}.png") as image:
            assert image.size == tuple(v * 4 for v in tile['padded']), (tile['job'], image.size)
            return image.convert('RGB').crop((0, 0, *footprint))

    canvas = np.zeros((footprint[1], footprint[0], 3), np.float32)
    weights = np.zeros(canvas.shape[:2], np.float32)
    for tile in row['tiles']:
        x, y, right, bottom = (v * 4 for v in tile['box'])
        w, h = right - x, bottom - y
        with Image.open(RUN / 'raw' / f"{tile['job']}.png") as image:
            assert image.size == tuple(v * 4 for v in tile['padded']), (tile['job'], image.size)
            rgb = np.asarray(image.convert('RGB').crop((0, 0, w, h)))
        axis_x, axis_y = np.ones(w, np.float32), np.ones(h, np.float32)
        for axis, start, end, size in ((axis_x, x, right, footprint[0]), (axis_y, y, bottom, footprint[1])):
            ramp = np.linspace(0.001, 1, min(384, axis.size), dtype=np.float32)
            if start:
                axis[:len(ramp)] *= ramp
            if end < size:
                axis[-len(ramp):] *= ramp[::-1]
        weight = axis_y[:, None] * axis_x[None, :]
        canvas[y:bottom, x:right] += rgb * weight[:, :, None]
        weights[y:bottom, x:right] += weight
    assert np.all(weights > 0), row['key']
    canvas /= weights[:, :, None]
    return Image.fromarray(np.rint(canvas).clip(0, 255).astype(np.uint8))


def finalize(manifest, failures):
    result_path = RUN / 'results.json'
    prior = read(result_path)['results'] if result_path.exists() else []
    results = {r['key']: r for r in prior}
    for row in manifest['rows']:
        key = row['key']
        if key in results:
            continue
        reference = row.get('identical_to')
        if reference and reference not in results:
            continue
        if any(not (RUN / 'raw' / f"{tile['job']}.png").exists() for tile in row['tiles']):
            continue
        if row.get('reuse'):
            target = ROOT / row['reuse']
        elif reference:
            target = ROOT / results[reference]['output']
        else:
            directory = RUN / 'outputs' / row['resref']
            directory.mkdir(exist_ok=True)
            target = directory / f'{key}-seedvr-7b-x4.png'
            image = merge(row)
            with Image.open(RUN / 'sources' / f'{key}-x1.png') as source:
                native_alpha = source.getchannel('A').resize(image.size, Image.Resampling.NEAREST)
            image.putalpha(native_alpha)
            temporary = target.with_suffix('.tmp')
            image.save(temporary, format='PNG', compress_level=3)
            temporary.replace(target)
        with Image.open(target) as image:
            assert image.size == tuple(v * 4 for v in row['native_size']), (key, image.size)
            with Image.open(RUN / 'sources' / f'{key}-x1.png') as source:
                alpha = source.getchannel('A').resize(image.size, Image.Resampling.NEAREST)
            exact = image.convert('RGBA').getchannel('A').tobytes() == alpha.tobytes()
            assert exact or (row['resref'] == 'BIGLOGO' and row['frame'] == 0), key
        results[key] = dict(**row, output=target.relative_to(ROOT).as_posix(), sha256=sha(target),
                            alpha_native_preserved=exact)
    expected = defaultdict(int)
    completed = defaultdict(int)
    for row in manifest['rows']:
        expected[row['resref']] += 1
    for row in results.values():
        completed[row['resref']] += 1
    complete = sorted(name for name, count in expected.items() if completed[name] == count)
    payload = dict(recipe=manifest['recipe'], expected_resources=len(expected), complete_resources=complete,
                   expected_frames=len(manifest['rows']), failures=failures, results=list(results.values()))
    write(result_path, payload)
    print(f'{len(complete)}/{len(expected)} resources; {len(results)}/{len(manifest["rows"])} frames; '
          f'{len(failures)} failed prompts', flush=True)
    return payload


def review(results):
    groups = defaultdict(list)
    for row in results['results']:
        groups[row['category']].append(row)
    directory = RUN / 'review'
    directory.mkdir(exist_ok=True)
    font = ImageFont.truetype('arial.ttf', 20)
    links = []
    for category, rows in sorted(groups.items()):
        rows.sort(key=lambda row: (row['resref'], row['frame']))
        for page_number, start in enumerate(range(0, len(rows), 16), 1):
            segment = rows[start:start + 16]
            board = Image.new('RGB', (1480, 55 + ((len(segment) + 2) // 3) * 193), '#202323')
            draw = ImageDraw.Draw(board)
            draw.text((20, 14), f'{category}  |  original / x4', font=font, fill='white')
            for index, row in enumerate(segment):
                x, y = 16 + (index % 3) * 490, 48 + (index // 3) * 193
                draw.text((x, y), row['key'], font=font, fill='white')
                width, height = row['native_size']
                scale = min(227 / width, 151 / height, 4)
                display_size = (max(1, round(width * scale)), max(1, round(height * scale)))
                for i, path in enumerate((RUN / 'sources' / f"{row['key']}-x1.png", ROOT / row['output'])):
                    with Image.open(path) as image:
                        preview = image.convert('RGBA')
                    preview = preview.resize(display_size, Image.Resampling.LANCZOS if i else Image.Resampling.NEAREST)
                    board.paste(preview, (x + i * 238, y + 26), preview)
            path = directory / f'{category}-{page_number:02}.jpg'
            board.save(path, quality=91)
            assets = []
            for row in segment:
                target = Path(os.path.relpath(ROOT / row['output'], directory)).as_posix()
                assets.append(f'<a href="{html.escape(target)}">{html.escape(row["key"])}</a>')
            links.append(f'<h2>{path.stem}</h2><img loading="lazy" src="{path.name}" alt="{path.stem}">'
                         f'<p>{" · ".join(assets)}</p>')
    (directory / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Interface x4</title>'
        '<style>body{background:#202323;color:white;margin:auto;max-width:1480px;font-family:system-ui}'
        'img{width:100%;height:auto}a{color:#d8eaff}</style>'
        f'<h1>Interface x4</h1><p>{len(results["complete_resources"])} ressources complètes, '
        f'{len(results["results"])} frames. Original à gauche, x4 à droite.</p>' + ''.join(links),
        encoding='utf-8')


def register(manifest):
    results = read(RUN / 'results.json')
    if len(results['complete_resources']) != results['expected_resources']:
        raise SystemExit('Complete the campaign before registering the candidates.')
    grouped = defaultdict(list)
    for frame in results['results']:
        path = ROOT / frame['output']
        assert sha(path) == frame['sha256'], path
        grouped[frame['resref']].append(frame)
    tracker = read(TRACKER)
    evidence = (RUN / 'results.json').relative_to(ROOT).as_posix()
    for item in tracker['resources']:
        name = item['resref']
        if name not in grouped:
            continue
        state = item['production']['state']
        if state == 'complete-awaiting-review-x4' and evidence in item['production']['evidence']:
            continue
        assert state in PENDING, (name, state)
        frames = sorted(grouped[name], key=lambda frame: frame['frame'])
        assert len(frames) == item['source']['frames'], name
        recipe = manifest['recipe']
        if name == 'BIGLOGO':
            recipe = {'0': 'Topaz Gigapixel 8.4.1 Recovery v2 Detail50 x4 preserve',
                      '1': manifest['recipe'], '2': manifest['recipe']}
        item['production'] = dict(
            state='complete-awaiting-review-x4', recipe=recipe,
            evidence=list(dict.fromkeys([evidence] + [frame['output'] for frame in frames])),
            frames=len(frames),
            sha256_by_frame={str(frame['frame']): frame['sha256'] for frame in frames},
            coverage='All native frames; individual recipes/reuse documented in results.json.')
        item['next_action'] = 'review-remaining-ui-campaign'
    tracker['updated_on'] = '2026-11-21'
    write(TRACKER, tracker)
    sys.path.insert(0, str(ROOT / 'interface/tracking'))
    from manage import export
    export(tracker)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'submit', 'collect', 'monitor', 'review', 'register'])
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    manifest = prepare()
    if args.action == 'submit':
        submit(manifest, args.limit)
    elif args.action == 'register':
        register(manifest)
    elif args.action == 'review':
        review(read(RUN / 'results.json'))
    elif args.action in {'collect', 'monitor'}:
        while True:
            result = finalize(manifest, collect(manifest))
            if len(result['results']) == result['expected_frames'] or args.action == 'collect':
                review(result)
                break
            if result['failures']:
                queue = requests.get(f'{SERVER}/queue', timeout=30).json()
                if not queue.get('queue_running') and not queue.get('queue_pending'):
                    review(result)
                    break
            time.sleep(20)


if __name__ == '__main__':
    main()
