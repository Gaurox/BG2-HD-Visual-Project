"""Build a non-destructive x4 alpha-feather experiment for AM0602F.

Only the alpha channel is changed.  RGB bytes and the canonical upscale run stay
untouched.  Runtime buffers keep the RGBA8/top-to-bottom layout expected by IEE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_SOURCE = (
    PROJECT_ROOT
    / "animations"
    / "runs"
    / "ar0602-all-bam-seedvr7b-lab-x4"
    / "resources"
    / "AM0602F"
    / "02_upscale_x4"
    / "rgba"
)
FRAME_COUNT = 9
SIZE = (660, 780)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_atomic(image: Image.Image, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    image.save(temporary, format="PNG", compress_level=9)
    temporary.replace(path)


def inner_feather(alpha: np.ndarray, radius: float) -> np.ndarray:
    """Fade strictly inside the existing alpha boundary.

    Padding makes pixels touching the canvas border see the transparent exterior.
    Boundary pixels become transparent, then a smoothstep ramp reaches the source
    alpha at ``radius`` physical x4 pixels toward the interior.
    """

    inside = alpha > 0
    padded = np.pad(inside, 1, mode="constant", constant_values=False)
    distance = distance_transform_edt(padded)[1:-1, 1:-1]
    ramp = np.clip((distance - 1.0) / radius, 0.0, 1.0)
    ramp = ramp * ramp * (3.0 - 2.0 * ramp)
    return np.rint(alpha.astype(np.float32) * ramp).astype(np.uint8)


def canvas_edge_fade(size: tuple[int, int], radius: float) -> np.ndarray:
    """Return a smooth alpha multiplier fading inward from all canvas edges."""

    width, height = size
    yy, xx = np.indices((height, width))
    distance = np.minimum.reduce((xx, width - 1 - xx, yy, height - 1 - yy))
    ramp = np.clip(distance.astype(np.float32) / radius, 0.0, 1.0)
    return ramp * ramp * (3.0 - 2.0 * ramp)


def checkerboard(size: tuple[int, int], cell: int = 16) -> Image.Image:
    width, height = size
    yy, xx = np.indices((height, width))
    cells = ((xx // cell) + (yy // cell)) % 2
    base = np.where(cells[..., None] == 0, 54, 82).astype(np.uint8)
    rgb = np.repeat(base, 3, axis=2)
    return Image.fromarray(rgb, "RGB").convert("RGBA")


def comparison(original: Image.Image, feathered: Image.Image, label: str, path: Path) -> None:
    label_height = 30
    canvas = Image.new("RGBA", (SIZE[0] * 2, SIZE[1] + label_height), (30, 30, 30, 255))
    for index, image in enumerate((original, feathered)):
        background = checkerboard(SIZE)
        background.alpha_composite(image)
        canvas.alpha_composite(background, (index * SIZE[0], label_height))
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 8), "alpha actuel", fill=(255, 255, 255, 255))
    draw.text((SIZE[0] + 10, 8), label, fill=(255, 255, 255, 255))
    save_atomic(canvas, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=SCRIPT_DIR)
    parser.add_argument("--inner-radius", type=float, default=8.0)
    parser.add_argument("--canvas-radius", type=float, default=0.0)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    if args.inner_radius <= 0:
        raise SystemExit("--inner-radius doit etre strictement positif")
    if args.canvas_radius < 0:
        raise SystemExit("--canvas-radius ne peut pas etre negatif")

    expected = [f"frame_{index:03d}.png" for index in range(FRAME_COUNT)]
    missing = [name for name in expected if not (source / name).is_file()]
    if missing:
        raise SystemExit(f"frames source absentes: {', '.join(missing)}")

    directories = {
        "rgba": output / "rgba",
        "alpha": output / "alpha",
        "raw": output / "raw_rgba",
        "preview": output / "preview",
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    canvas_fade = canvas_edge_fade(SIZE, args.canvas_radius) if args.canvas_radius else None
    records = []
    original_zero = None
    feathered_zero = None
    for index, name in enumerate(expected):
        source_path = source / name
        with Image.open(source_path) as opened:
            original = opened.convert("RGBA")
        if original.size != SIZE:
            raise SystemExit(f"{name}: taille {original.size}, attendu {SIZE}")

        pixels = np.asarray(original).copy()
        source_alpha = pixels[:, :, 3]
        softened_alpha = inner_feather(source_alpha, args.inner_radius)
        if canvas_fade is not None:
            softened_alpha = np.rint(softened_alpha.astype(np.float32) * canvas_fade).astype(np.uint8)
        if np.any(softened_alpha > source_alpha):
            raise SystemExit(f"{name}: le nouveau masque deborde du masque source")
        pixels[:, :, 3] = softened_alpha
        softened = Image.fromarray(pixels, "RGBA")

        rgba_path = directories["rgba"] / name
        alpha_path = directories["alpha"] / name
        raw_name = f"AAX4-AM0602F-frame{index:03d}.rgba"
        raw_path = directories["raw"] / raw_name
        save_atomic(softened, rgba_path)
        save_atomic(Image.fromarray(softened_alpha, "L"), alpha_path)
        temporary_raw = raw_path.with_suffix(raw_path.suffix + ".partial")
        temporary_raw.write_bytes(pixels.tobytes(order="C"))
        temporary_raw.replace(raw_path)

        records.append(
            {
                "frame": index,
                "source": source_path.as_posix(),
                "source_sha256": sha256(source_path),
                "rgba": rgba_path.relative_to(output).as_posix(),
                "rgba_sha256": sha256(rgba_path),
                "alpha": alpha_path.relative_to(output).as_posix(),
                "alpha_sha256": sha256(alpha_path),
                "runtime_asset": raw_path.relative_to(output).as_posix(),
                "runtime_sha256": sha256(raw_path),
                "runtime_bytes": raw_path.stat().st_size,
                "source_opaque_pixels": int(np.count_nonzero(source_alpha == 255)),
                "feathered_pixels": int(np.count_nonzero((softened_alpha > 0) & (softened_alpha < 255))),
                "transparent_boundary_pixels": int(np.count_nonzero((source_alpha > 0) & (softened_alpha == 0))),
            }
        )
        if index == 0:
            original_zero = original
            feathered_zero = softened

    assert original_zero is not None and feathered_zero is not None
    label = f"fondu objet {args.inner_radius:g} px x4"
    if args.canvas_radius:
        label += f" + bord canvas {args.canvas_radius:g} px x4"
    comparison(original_zero, feathered_zero, label, directories["preview"] / "frame_000-comparison.png")

    alpha_comparison = Image.new("L", (SIZE[0] * 2, SIZE[1]))
    alpha_comparison.paste(original_zero.getchannel("A"), (0, 0))
    alpha_comparison.paste(feathered_zero.getchannel("A"), (SIZE[0], 0))
    save_atomic(alpha_comparison, directories["preview"] / "frame_000-alpha-comparison.png")

    manifest = {
        "schema": "bg2-upscale-animation-alpha-feather-test-v1",
        "status": "completed",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "resref": "AM0602F",
        "scale": 4,
        "physical_size": list(SIZE),
        "frame_count": FRAME_COUNT,
        "alpha_operation": {
            "type": "inner-distance-feather-plus-canvas-edge-feather",
            "radius_physical_x4": args.inner_radius,
            "radius_logical_x1": args.inner_radius / 4.0,
            "canvas_edge_radius_physical_x4": args.canvas_radius,
            "canvas_edge_radius_logical_x1": args.canvas_radius / 4.0,
            "curve": "smoothstep",
            "outside_source_mask": 0,
            "rgb_policy": "unchanged",
        },
        "frames": records,
    }
    manifest_path = output / "manifest.json"
    temporary_manifest = manifest_path.with_suffix(".json.partial")
    temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary_manifest.replace(manifest_path)
    suffix = f", bord canvas {args.canvas_radius:g} px x4" if args.canvas_radius else ""
    print(f"AM0602F: {FRAME_COUNT} frames construites, fondu interieur {args.inner_radius:g} px x4{suffix}")
    print(f"Sortie: {output}")


if __name__ == "__main__":
    main()
