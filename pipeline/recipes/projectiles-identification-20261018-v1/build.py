"""One native travel frame per BAM; identification only, no production mutation."""
from pathlib import Path
import csv
import hashlib
import io
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam, native_palette_alpha
from export_bam_frames import read_bam, cycle_metadata
from bg2lib import load_key, resolve_resource
from palette_oracle import scalar_palette

OUT = ROOT / 'projectiles/previews/identification-20261018-v1'


def rows(path):
    with (ROOT / path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    consumers = [c for c in rows('effects/index/consumers.csv')
                 if c['owner_route'] == 'projectile' and c['relation'] == 'travel-animation']
    sources = {r['asset_key']: r for r in rows('effects/index/bam-assets.csv')}
    states = {r['asset_key']: r for r in rows('effects/index/processing.csv')}
    pro_sources = {r['asset_key']: r for r in rows('projectiles/index/resources.csv')}
    bifs, entries = load_key()
    lookup = {(n.upper(), t): loc for n, t, loc in entries}

    def bmp(name):
        raw, _ = resolve_resource(bifs, lookup[name.upper(), 1])
        return Image.open(io.BytesIO(raw)), sha(raw)

    ramp_image, ramp_sha = bmp('MPALETTE')
    ramps = np.asarray(ramp_image.convert('RGB'))
    records, images, exclusions = [], [], []
    for key in sorted({c['asset_key'] for c in consumers}):
        name = key.rsplit(':', 1)[-1]
        if name.startswith('CG'):
            exclusions.append({'bam': name, 'reason': 'casting-school symbol, outside flight inventory'})
            continue
        owners = [c for c in consumers if c['asset_key'] == key]
        owners.sort(key=lambda c: (c['consumer_key'].split(':')[-1] != name,
                                  c['consumer_key'].split(':')[-1][0].isdigit(), c['consumer_key']))
        owner = owners[0]
        source = sources[key]
        packed = (ROOT / source['extracted_path']).read_bytes()
        assert sha(packed).upper() == source['source_sha256'].upper()
        pro = pro_sources[owner['consumer_key']]
        assert sha((ROOT / pro['extracted_path']).read_bytes()).upper() == owner['source_sha256'].upper()
        raw = read_bam(ROOT / source['extracted_path'])
        frames, palette, tr = decode_bam(raw)
        palette_kind, palette_source = 'embedded', {'bam_sha256': sha(raw)}
        if owner['color_enabled'] == '1':
            colors = [int(v) for v in owner['colors'].split(';')]
            palette = scalar_palette(ramps[colors])
            palette_kind = 'seven-native-ranges'
            palette_source = {'bmp': 'MPALETTE', 'sha256': ramp_sha, 'colors': colors}
        elif owner['palette']:
            external, bmp_sha = bmp(owner['palette'])
            table = external.getpalette()
            assert table and len(table) >= 768
            palette = np.array(table[:768], np.uint8).reshape(256, 3)
            palette_kind = 'external-bmp'
            palette_source = {'bmp': owner['palette'], 'sha256': bmp_sha}
        cycles = cycle_metadata(raw, len(frames))
        cycle = int(owner['cycles'].split(';')[0])
        eligible = cycles[cycle]['frame_indices']
        assert eligible

        def score(fi):
            idx = frames[fi][0]
            rgb = palette[idx][idx != tr].astype(np.int64)
            return int(rgb.max(axis=1).sum()) if len(rgb) else 0

        fi = max(eligible, key=score)
        if score(fi) == 0:
            exclusions.append({'bam': name, 'reason': 'black-only travel mask, no standalone RGB appearance'})
            continue
        idx, cx, cy, _ = frames[fi]
        alpha = native_palette_alpha(raw, tr)[idx]
        rgba = Image.fromarray(np.dstack((palette[idx], alpha)))
        bbox = rgba.getbbox()
        assert bbox
        image = rgba.crop(bbox)
        scale = min(4, 246 // image.width, 158 // image.height)
        if scale >= 1:
            image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
            display_scale = f'x{scale}'
        else:
            original = image.size
            image.thumbnail((246, 158), Image.Resampling.NEAREST)
            display_scale = f'x{image.width / original[0]:.2f}'
        ordinal = len(records) + 1
        records.append({'number': ordinal, 'bam': name,
            'representative_projectile': owner['consumer_key'].split(':')[-1],
            'source': source['extracted_path'], 'source_sha256': sha(packed),
            'cycle_zero_based': cycle, 'frame_zero_based': fi,
            'frame_dimensions': [idx.shape[1], idx.shape[0]], 'frame_center': [cx, cy],
            'visible_bbox': list(bbox), 'display_scale': display_scale,
            'palette_kind': palette_kind, 'palette_source': palette_source,
            'palette_rgb_sha256': sha(palette.tobytes()), 'consumer': owner,
            'all_travel_consumers': [c['consumer_key'] for c in owners],
            'production_snapshot': {k: states[key][k] for k in
                ('spatial_state', 'interpolation_state', 'qa_state', 'installation_state')}})
        images.append(image)

    assert 45 <= len(records) <= 55
    cols, tw, th, top = 7, 280, 238, 112
    sheet = Image.new('RGB', (cols * tw, top + ((len(records) + cols - 1) // cols) * th + 36), '#121720')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 22)
    small = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 16)
    title = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 30)
    draw.text((18, 10), f'{len(records)} PROJECTILES  /  identification des sources natives', font=title, fill='white')
    draw.text((18, 52), 'Une frame de vol par BAM | nom BAM en blanc / projectile PRO en bleu | agrandissement sans IA', font=small, fill='#c5d1df')
    draw.text((18, 78), 'Une palette PRO representative ; variantes partagees listees dans le CSV. Teinte / eclairage du jeu non simules.', font=small, fill='#94a4b8')
    for k, (record, im) in enumerate(zip(records, images)):
        x, y = k % cols * tw, top + k // cols * th
        draw.rounded_rectangle((x + 5, y + 3, x + tw - 5, y + th - 4), radius=8, fill='#202938')
        draw.text((x + 14, y + 10), f'{record["number"]:02d}  {record["bam"]}', font=font, fill='white')
        draw.text((x + 14, y + 39), f'PRO {record["representative_projectile"]}', font=small, fill='#90c5eb')
        # Dark checker allows the source's own opaque/black pixels to remain visible.
        for yy in range(160):
            for xx in range(248):
                v = 47 if ((xx // 12 + yy // 12) % 2) else 52
                sheet.putpixel((x + 16 + xx, y + 62 + yy), (v, v + 3, v + 7))
        sheet.paste(im, (x + (tw - im.width) // 2, y + 62 + (160 - im.height) // 2), im)
        draw.text((x + 18, y + 218), f'c{record["cycle_zero_based"]} f{record["frame_zero_based"]}  {record["display_scale"]}', font=small, fill='#b0becf')
    draw.text((18, sheet.height - 28), 'Index c/f a partir de 0 | inventaire visuel : comprend des BAM deja traites dans effects | 2026-10-18', font=small, fill='#94a4b8')
    sheet.save(OUT / 'planche-projectiles.png')
    manifest = {'schema': 'bg2-projectiles-identification-v1', 'date': '2026-10-18',
        'status': 'source-identification-only', 'count': len(records),
        'selection': 'All direct PRO travel BAMs except casting-school symbols and black-only masks; one representative PRO palette per BAM.',
        'preview_contract': 'Native palette alpha on dark checker, visible crop, nearest resize; native geometry unchanged in source. No runtime blend/tint simulation.',
        'exclusions': exclusions, 'assets': records}
    (OUT / 'selection.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (OUT / 'selection.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['numero', 'BAM', 'PRO_exemple', 'cycle_0', 'frame_0', 'palette', 'etat_spatial', 'autres_PRO'])
        for r in records:
            writer.writerow([r['number'], r['bam'], r['representative_projectile'], r['cycle_zero_based'],
                r['frame_zero_based'], r['palette_kind'], r['production_snapshot']['spatial_state'],
                ';'.join(c.split(':')[-1] for c in r['all_travel_consumers'])])
    print(json.dumps({'count': len(records), 'sheet': str(OUT / 'planche-projectiles.png'), 'exclusions': exclusions}))


if __name__ == '__main__':
    main()
