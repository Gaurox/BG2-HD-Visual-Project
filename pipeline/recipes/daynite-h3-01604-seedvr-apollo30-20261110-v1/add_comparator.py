from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
path = ROOT / 'video/tools/comparator.html'
text = path.read_text(encoding='utf-8')
marker = 'sourceItems.push(...resultItems.map(item=>({...item})));'
assert text.count(marker) == 1
stem = '../daynite/runs/daynite-h3-01604-seedvr-apollo30-20261110-v1/'
items = [
    ('DAYNITE — H3 01604 + SeedVR + Apollo8 · 1080p30 · son original',
     'DAYNITE-H3-01604-SeedVR2-Apollo8-1080p30-son-original-v1.mp4', 30),
    ('DAYNITE — H3 01604 + SeedVR · 1080p24 · son original',
     'DAYNITE-H3-01604-SeedVR2-1080p24-son-original-v1.mp4', 24),
    ('DAYNITE — H3 01604 · fondus corrigés 16:9 · son original · 24 fps',
     'DAYNITE-H3-01604-fondus-corriges-16x9-son-original-24fps-v2.mp4', 24),
]
if items[0][1] not in text:
    lines = []
    for name, file, fps in items:
        assert (ROOT / 'video/daynite/runs/daynite-h3-01604-seedvr-apollo30-20261110-v1' / file).is_file()
        lines.append(f" {{name:'{name}',url:'{stem}{file}',fps:{fps}}}")
    insertion = 'resultItems.unshift(\n' + ',\n'.join(lines) + '\n);\n'
    path.write_text(text.replace(marker, insertion + marker), encoding='utf-8')
print('Three H3 corrected 16:9 / SeedVR24 / SeedVR+Apollo30 options available on both sides.')
