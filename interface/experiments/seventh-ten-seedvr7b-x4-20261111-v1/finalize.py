"""Finalize 10 outputs for ten resources, exact crop and original alpha."""
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
if (HERE / 'results.json').exists():
    raise SystemExit('Existing finalized results; use a new run.')
rows = json.loads((HERE / 'sources.json').read_text(encoding='utf-8'))
downloads = json.loads((HERE / 'jobs/downloads.json').read_text(encoding='utf-8-sig'))
files = {}
for group in downloads:
    for file in group['files']:
        filename = parse_qs(urlparse(file['url']).query)['filename'][0]
        files[filename.split('-7b-x4_')[0]] = Path(file['path'])
exclusions = json.loads((HERE / 'native-controls.json').read_text())['rectangles_native_xyxy']
results = []
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 23)
for row in rows:
    job = row['job']
    source = Image.open(HERE / 'sources' / f'{job}-x1.png').convert('RGBA')
    native = source.resize(tuple(row['expected_x4']), Image.Resampling.NEAREST)
    raw = Image.open(files[job]).convert('RGBA')
    assert raw.size == tuple(v * 4 for v in row['padded_size'])
    im = raw.crop((0, 0, *row['expected_x4']))
    preserved = exclusions.get(row['resref'], [])
    for rect in preserved:
        box = tuple(v * 4 for v in rect)
        im.paste(native.crop(box), box)
        assert im.crop(box).tobytes() == native.crop(box).tobytes()
    im.putalpha(native.getchannel('A'))
    assert im.getchannel('A').tobytes() == native.getchannel('A').tobytes()
    folder = HERE / 'outputs' / row['resref']
    folder.mkdir(exist_ok=True)
    out = folder / f'{job}-seedvr-7b-x4.png'
    im.save(out)
    alpha = np.array(im.getchannel('A'))
    results.append(dict(number=row['number'], resref=row['resref'], job=job, frame=row['frame'],
                        kind=row['kind'], output=out.relative_to(HERE).as_posix(), size=list(im.size),
                        sha256=hashlib.sha256(out.read_bytes()).hexdigest(), blocks=row['blocks'],
                        alpha_intermediate_pixels=int(((alpha > 0) & (alpha < 255)).sum()),
                        alpha_native_preserved=True, native_controls_rectangles=preserved))
    board = Image.new('RGB', (1024, 1000), '#292923')
    d = ImageDraw.Draw(board)
    d.text((16, 10), f'{row["number"]}. {job}', font=font, fill='white')
    for col, (pic, label) in enumerate(((native, 'Original agrandi x4'), (im, 'SeedVR 7B x4'))):
        d.text((col * 512 + 16, 50), label, font=font, fill='white')
        preview = pic.copy()
        preview.thumbnail((480, 520), Image.Resampling.LANCZOS)
        bg = Image.new('RGBA', preview.size, '#55554c')
        bg.alpha_composite(preview)
        board.paste(bg.convert('RGB'), (col * 512 + 16 + (480 - preview.width) // 2, 90))
        # Matched central/edge crop at one x4 output pixel per board pixel.
        x = 0
        y = 0
        crop = pic.crop((x, y, x + 480, y + 300))
        bg = Image.new('RGBA', crop.size, '#55554c')
        bg.alpha_composite(crop)
        d.text((col * 512 + 16, 645), 'Zoom à 100 %', font=font, fill='white')
        board.paste(bg.convert('RGB'), (col * 512 + 16, 685))
    board.save(HERE / 'comparison' / f'{job}-original-7b.png')
manifest = dict(schema='bg2-ui-mixed-seedvr7b-batch-v1', state='produced-awaiting-preview-review',
                recipe=dict(model='seedvr2_7b_int8_convrot.safetensors', scale=4, color_correction='lab',
                            seed=959948902156062, steps=1, cfg=1, sampler='euler', scheduler='simple'),
                results=results, resources=sorted({r['resref'] for r in rows}),
                qa='awaiting user preview review; not installed', release='unchanged')
(HERE / 'results.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{len(results)} outputs verified; native dimensions and alpha preserved')
