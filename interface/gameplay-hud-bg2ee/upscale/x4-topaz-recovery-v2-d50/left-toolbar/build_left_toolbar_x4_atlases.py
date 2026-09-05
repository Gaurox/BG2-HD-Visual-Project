"""Extract and package the two PVRZ atlases behind BG2EE's left toolbar.

GUILS10.BAM only supplies frame geometry. Its 17 buttons and their four states
are sampled from MOS0140 and MOS0141, so these pages are intentionally
upscaled as complete atlases. The game archives are never written.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "scripts"))
from bg2lib import load_key, resolve_resource  # noqa: E402
from mos_decode import decode_pvrz_page  # noqa: E402


ROOT = Path(__file__).resolve().parent
SCALE = 4
PAGES = (140, 141)
TYPE_PVRZ = 1028


def resource_index() -> tuple[list[str], dict[tuple[str, int], int]]:
    bifs, entries = load_key()
    return bifs, {(name.upper(), resource_type): locator for name, resource_type, locator in entries}


def extract() -> None:
    bifs, index = resource_index()
    source = ROOT / "sources" / "pages"
    source.mkdir(parents=True, exist_ok=True)
    for page in PAGES:
        name = f"MOS{page:04d}"
        data, _ = resolve_resource(bifs, index[(name, TYPE_PVRZ)])
        image = decode_pvrz_page(data).convert("RGBA")
        output = source / f"{name}-x1.png"
        image.save(output)
        print(f"extracted {output.name}: {image.width}x{image.height}")


def package() -> None:
    source = ROOT / "sources" / "pages"
    upscaled = ROOT / "upscale-topaz-recovery-v2-d50"
    assets = ROOT / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for page in PAGES:
        name = f"MOS{page:04d}"
        with Image.open(source / f"{name}-x1.png") as original_opened:
            original = original_opened.convert("RGBA")
        expected = (original.width * SCALE, original.height * SCALE)
        # Topaz retains the source suffix, producing e.g. MOS0140-x1-x4.png.
        with Image.open(upscaled / f"{name}-x1-x4.png") as opened:
            image = opened.convert("RGBA")
        if image.size != expected:
            raise RuntimeError(f"{name}: {image.size}, attendu {expected}")
        image.save(assets / f"HUD-{name}-x4-preview.png")
        buffer = io.BytesIO()
        image.save(buffer, format="DDS", pixel_format="DXT5")
        dds = buffer.getvalue()
        expected_bytes = 128 + image.width * image.height
        if dds[:4] != b"DDS " or len(dds) != expected_bytes:
            raise RuntimeError(f"DDS DXT5 invalide pour {name}")
        output = assets / f"HUD-{name}-x4.dxt5"
        output.write_bytes(dds[128:])
        print(f"packaged {output.name}: {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", action="store_true")
    args = parser.parse_args()
    package() if args.package else extract()
