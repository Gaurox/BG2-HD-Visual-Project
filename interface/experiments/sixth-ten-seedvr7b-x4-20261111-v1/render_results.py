"""Display the ten x4 outputs in two numbered contact sheets."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
results = json.loads((HERE / 'results.json').read_text(encoding='utf-8'))['results']
sources = json.loads((HERE / 'sources.json').read_text(encoding='utf-8'))
labels = {r['resref']: r['label'] for r in sources}
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 24)
small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
for group in range(2):
    canvas = Image.new('RGB', (1500, 1500), '#272621')
    draw = ImageDraw.Draw(canvas)
    for i, row in enumerate(results[group * 5:group * 5 + 5]):
        x, y = i % 2 * 750, i // 2 * 500
        draw.text((x + 18, y + 14), f'{row["number"]}. {labels[row["resref"]]}', font=font, fill='white')
        draw.text((x + 18, y + 46), f'{row["resref"]} — SeedVR 7B x4', font=small, fill='#c7c2b8')
        im = Image.open(HERE / row['output']).convert('RGBA')
        im.thumbnail((700, 410), Image.Resampling.LANCZOS)
        bg = Image.new('RGBA', im.size, '#45443d')
        bg.alpha_composite(im)
        canvas.paste(bg.convert('RGB'), (x + 25 + (700 - im.width) // 2, y + 80 + (410 - im.height) // 2))
    canvas.save(HERE / 'comparison' / f'results-{group * 5 + 1:02}-{group * 5 + 5:02}.png')
