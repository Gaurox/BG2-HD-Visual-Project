"""Derive Korgan L/M/S BMPs from the final painting; no anisotropic resize."""
import csv
import hashlib
import json
import struct
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MASTER = ROOT / 'portraits/experiments/korgan-imagegen-large-20261111-v2/NKORGANL-regenerated-7x11.png'


def main():
    manifest = HERE / 'assets.json'
    if manifest.exists():
        raise RuntimeError('Already prepared; use a new version for different assets')
    with (ROOT / 'portraits/inventaire_portraits.csv').open(encoding='utf-8-sig', newline='') as f:
        native = next(row for row in csv.DictReader(f) if row['portrait'] == 'NKORGAN')
    assets = HERE / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    rows = []
    with Image.open(MASTER) as opened:
        master = opened.convert('RGB')
    assert master.size == (791, 1243) and master.width * 11 == master.height * 7
    for suffix in 'LMS':
        s = suffix.lower()
        nw, nh = int(native['largeur_px_' + s]), int(native['hauteur_px_' + s])
        size = master.size if suffix == 'L' else (nw * 4, nh * 4)
        width, height = master.size
        if width / height > size[0] / size[1]:
            crop_width = height * size[0] / size[1]
            box = ((width - crop_width) / 2, 0, (width + crop_width) / 2, height)
        else:
            crop_height = width * size[1] / size[0]
            box = (0, (height - crop_height) / 2, width, (height + crop_height) / 2)
        assert abs((box[2] - box[0]) / (box[3] - box[1]) - size[0] / size[1]) < 1e-12
        image = master.copy() if suffix == 'L' else master.resize(size, Image.Resampling.LANCZOS, box=box)
        name = 'NKORGAN' + suffix
        bmp = assets / (name + '.bmp')
        image.save(bmp, format='BMP')
        if suffix != 'L':
            image.save(assets / (name + '.png'))
        data = bmp.read_bytes()
        assert struct.unpack_from('<H', data, 28)[0] == 24
        assert struct.unpack_from('<I', data, 30)[0] == 0
        with Image.open(bmp) as reread:
            assert reread.mode == 'RGB' and reread.size == size
            assert reread.tobytes() == image.tobytes()
            if suffix == 'L':
                assert reread.tobytes() == master.tobytes()
        rows.append(dict(resource=name, file='assets/' + bmp.name, width=size[0], height=size[1],
                         native_size=[nw, nh], scale='master unchanged' if suffix == 'L' else 4,
                         master_crop_box=list(box), resampling='none' if suffix == 'L' else 'Lanczos, uniform scale',
                         bits_per_pixel=24, compression='BI_RGB', bytes=len(data),
                         sha256=hashlib.sha256(data).hexdigest()))
    manifest.write_text(json.dumps(dict(schema='bg2-korgan-portrait-test-assets-v1',
        master=MASTER.relative_to(ROOT).as_posix(), master_sha256=hashlib.sha256(MASTER.read_bytes()).hexdigest(),
        assets=rows, qa='pending-ingame'), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
