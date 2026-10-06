"""Render one acquired CHFB1 frame: sealed V6 versus sealed V7; no inference."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from palette_work_plan import WorkPlan, file_sha, write_json
from palette_q3m_partners import Profile
import palette_frac_encode as v6
import palette_registry as leaf6
import palette_partner_registry as leaf7
import run_creature_sprite_x2 as registry

load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
POINTER6 = ROOT / 'docs/measurements/playable-q3m-x2-ingame-20261002-v1/current-generation.json'
POINTER7 = ROOT / 'docs/measurements/q3m-families-engine-x2-20261003-v2/current-generation.json'


def source(plan, ref):
    resource = plan.db.execute('SELECT * FROM resources WHERE resref=?', (ref,)).fetchone()
    assert resource is not None
    member = plan.db.execute('SELECT 1 FROM model_resources JOIN models USING(model_id) WHERE resource_id=? AND animation_id=?',
                             (resource['resource_id'], '0x6110')).fetchone()
    assert member is not None
    return resource


def native(plan, resource, fi):
    row = plan.db.execute('SELECT f.*,q.* FROM frames f JOIN processing_queue q USING(work_id) WHERE f.resource_id=? AND f.frame_index=?',
                          (resource['resource_id'], fi)).fetchone()
    assert row is not None
    indices = np.frombuffer(zlib.decompress(row['indices_zlib']), np.uint8).reshape(row['height'], row['width'])
    return row, indices


def rgba_palette(plan):
    palette = np.column_stack((plan.fitting()[0], np.full(256, 255, np.uint8)))
    palette[0] = 0
    palette[1, 3] = 128
    return palette


def candidates(plan):
    cards = []
    palette = rgba_palette(plan)
    for ref in ('CHFB1G1', 'CHFB1G11', 'CHFB1G12', 'CHFB1G13', 'CHFB1G14', 'CHFB1G15'):
        resource = source(plan, ref)
        for ci in (0, 4, 8, 9, 13, 17, 18, 22, 26):
            cycle = plan.db.execute('SELECT * FROM cycles WHERE resource_id=? AND cycle_index=?', (resource['resource_id'], ci)).fetchone()
            if not cycle or not cycle['slot_count']: continue
            slots = struct.unpack(f"<{cycle['slot_count']}H", cycle['frame_indices_le_u16'])
            fi = slots[len(slots)//2]
            if fi >= resource['frame_count']: continue
            row, indices = native(plan, resource, fi)
            if row['height'] < 35 or np.count_nonzero(indices > 3) < 30: continue
            rgba = palette[indices]
            image = Image.fromarray(rgba, 'RGBA').resize((row['width']*4, row['height']*4), Image.Resampling.NEAREST)
            card = Image.new('RGB', (220, 300), (40, 49, 62))
            ImageDraw.Draw(card).text((7, 7), f'{ref} / {fi} / cycle {ci}', fill='white')
            card.paste(image, ((220-image.width)//2, 30), image)
            cards.append(card)
    sheet = Image.new('RGB', (220*6, 300*((len(cards)+5)//6)), (20, 26, 35))
    for i, card in enumerate(cards): sheet.paste(card, ((i%6)*220, (i//6)*300))
    destination = ROOT / 'sprite/.work/q3m-character-frame-v6-v7-x2-20261006-v1/candidates.png'
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination)
    print(json.dumps(dict(candidates=len(cards), path=destination.as_posix())))


def acquired_frame(pointer, version, ref, fi):
    generation = load(pointer)
    if version == 6:
        directory = ROOT / generation['generation_dir']
        catalog_path = directory / 'CreatureSprites-XN.catalog'
        catalog_sha = generation['catalog_sha256']
    else:
        directory = ROOT / generation['pack_directory']
        catalog_path = ROOT / generation['catalog']['path']
        catalog_sha = generation['catalog']['sha256']
    catalog = registry.read_sealed_catalog_index(catalog_path, catalog_sha)
    route = next(r for r in catalog['directory'] if r['animation_id'] == '0x6110' and r['resref'] == ref)
    shard = catalog['shards'][route['shard_index']]
    path = directory / Path(shard['registry']).name
    leaf = (leaf6 if version == 6 else leaf7).inspect(path, include_frames=True)
    assert leaf['sha256'].lower() == shard['sha256'].lower()
    resources = leaf['frame_data'] if version == 6 else leaf['resources']
    resource = next(r for r in resources if r['resref'] == ref)
    return resource, resource['frames'][fi], dict(pointer=pointer.relative_to(ROOT).as_posix(),
             catalog_sha256=catalog_sha.lower(), leaf=path.relative_to(ROOT).as_posix(), leaf_sha256=leaf['sha256'].lower())


def compare(plan, ref, fi):
    resource = source(plan, ref)
    row, indices = native(plan, resource, fi)
    source_bgra = np.frombuffer(resource['palette_bgra'], np.uint8).reshape(256, 4)
    profile = Profile(1, source_bgra, plan.fitting())
    p = rgba_palette(plan)
    r6, f6, origin6 = acquired_frame(POINTER6, 6, ref, fi)
    r7, f7, origin7 = acquired_frame(POINTER7, 7, ref, fi)
    geometry = (row['width'], row['height'], row['center_x'], row['center_y'], 0)
    assert tuple(f6['geometry']) == tuple(f7['geometry']) == geometry
    assert r6['cycles'] == r7['cycles']
    assert r6['source_sha256'].lower() == r7['source_sha256'].lower() == resource['canonical_sha256'].lower()
    assert r7['profile'].metadata() == profile.metadata()
    profile.validate(f7['I'], f7['F'], dep=np.frombuffer(f7['dep'], np.uint8))
    shape = (row['height']*2, row['width']*2)
    f6['I'] = np.frombuffer(f6['I'], np.uint8).reshape(shape)
    f6['F'] = np.frombuffer(f6['F'], np.uint8).reshape(shape) if f6['F'] else np.zeros(shape, np.uint8)
    a, b = v6.decode(f6['I'], f6['F'], p), profile.decode(f7['I'], f7['F'], p)
    assert a.shape == b.shape == (row['height']*2, row['width']*2, 4)
    assert np.array_equal(a[..., 3], b[..., 3])
    zoom = 6
    images = [Image.fromarray(x, 'RGBA') for x in (a, b)]
    for name, image in zip(('v6-x2.png', 'v7-x2.png'), images): image.save(HERE/name)
    enlarged = [im.resize((im.width*zoom, im.height*zoom), Image.Resampling.NEAREST) for im in images]
    for original, scaled in zip((a, b), enlarged):
        assert np.array_equal(np.asarray(scaled), np.repeat(np.repeat(original, zoom, axis=0), zoom, axis=1))
    panel_width = max(410, enlarged[0].width+72)
    panel_height = enlarged[0].height+120
    sheet = Image.new('RGB', (panel_width*2+24, panel_height+96), (22, 28, 37))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 24)
    small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 17)
    draw.text((24, 12), 'Guerrière humaine — sans équipement', fill=(238, 242, 248), font=font)
    draw.text((24, 48), f'{ref} · frame {fi} · même palette K6 #0 · zoom entier ×6 du rendu x2', fill=(170, 184, 201), font=small)
    for n, (label, image) in enumerate(zip(('V6 — 1 partenaire / 8 niveaux', 'V7 — 4 partenaires / 8 niveaux'), enlarged)):
        left = 12+n*(panel_width+12)
        draw.rectangle((left, 86, left+panel_width-1, sheet.height-35), fill=(40, 49, 62))
        draw.text((left+16, 98), label, fill='white', font=small)
        sheet.paste(image, (left+(panel_width-image.width)//2, 148), image)
    draw.text((24, sheet.height-27), 'PNG sans perte · agrandissement Nearest · aucune interpolation ni SDF · simulation hors jeu', fill=(170, 184, 201), font=small)
    destination = HERE/'comparison-v6-v7-nearest-x6.png'
    sheet.save(destination)
    assert np.array_equal(np.asarray(Image.open(destination)), np.asarray(sheet))
    changed = np.any(a[..., :3] != b[..., :3], axis=2) & (a[..., 3] > 0)
    body = a[..., 3] == 255
    stats = dict(changed_visible_pixels=int(changed.sum()), body_pixels=int(body.sum()),
                 changed_body_pixels=int((changed & body).sum()), max_channel_delta=int(np.abs(a.astype(np.int16)-b.astype(np.int16)).max()))
    cycles = []
    for cycle in plan.db.execute('SELECT * FROM cycles WHERE resource_id=? ORDER BY cycle_index', (resource['resource_id'],)):
        for slot, frame in enumerate(struct.unpack(f"<{cycle['slot_count']}H", cycle['frame_indices_le_u16'])):
            if frame == fi: cycles.append(dict(cycle=cycle['cycle_index'], slot=slot))
    write_json(HERE/'comparison.json', dict(schema='bg2-character-single-frame-v6-v7-comparison-v1',
        animation_id='0x6110', body='CHFB1', equipment=False, resref=ref, frame_index=fi,
        geometry=list(geometry), cycle_positions=cycles, palette='acquired synthetic Character K6 #0',
        palette_rgba_sha256=hashlib.sha256(p.tobytes()).hexdigest(), fitting_rgb_sha256=hashlib.sha256(plan.fitting().tobytes()).hexdigest(),
        native_scale=2, display_zoom=zoom, display_filter='Nearest', SDF=False,
        v6=origin6, v7=origin7, inference_count=0, encoding_count=0, stats=stats,
        files=[dict(path=path.name, bytes=path.stat().st_size, sha256=file_sha(path)) for path in
               (HERE/'v6-x2.png', HERE/'v7-x2.png', destination)], ingame_capture=False, ingame_QA=False))
    print(json.dumps(dict(path=destination.as_posix(), stats=stats)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', action='store_true')
    parser.add_argument('--resref', default='CHFB1G12')
    parser.add_argument('--frame', type=int, default=5)
    args = parser.parse_args()
    plan = WorkPlan()
    try:
        candidates(plan) if args.candidates else compare(plan, args.resref, args.frame)
    finally:
        plan.close()
