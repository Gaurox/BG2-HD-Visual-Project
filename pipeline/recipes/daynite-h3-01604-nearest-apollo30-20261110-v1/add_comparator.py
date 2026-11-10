from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'video/daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1'
path = ROOT / 'video/tools/comparator.html'
text = path.read_text(encoding='utf-8')
marker = 'sourceItems.push(...resultItems.map(item=>({...item})));'
assert text.count(marker) == 1
items = [
    ('DAYNITE — H3 01604 · NEAREST + Apollo8 · 1080p30 · son original',
     'DAYNITE-H3-01604-NEAREST-Apollo8-1080p30-son-original-v1.mp4', 30),
    ('DAYNITE — H3 01604 · NEAREST seul · 1080p24 · son original',
     'DAYNITE-H3-01604-NEAREST-1080p24-son-original-v1.mp4', 24),
]
if items[0][1] not in text:
    lines = []
    for name, file, fps in items:
        assert (RUN / file).is_file()
        url = '../daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1/' + file
        lines.append(f" {{name:'{name}',url:'{url}',fps:{fps}}}")
    path.write_text(text.replace(marker, 'resultItems.unshift(\n' + ',\n'.join(lines) +
                                '\n);\n' + marker), encoding='utf-8')
print('Nearest24 and Nearest+Apollo30 available on both sides.')
