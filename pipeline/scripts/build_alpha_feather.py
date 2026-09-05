"""Build a reversible alpha correction for a completed x4 animation run.

Validated recipe (AM0602F, AM0205A-D): multiply alpha by one or more
smoothstep ramps —

  - inner-distance feather: fades to 0 within `--inner-radius-x4` px of the
    mask's own silhouette edge (canvas exterior counts as transparent), for a
    hard outline around the object itself;
  - canvas-edge feather: fades to 0 within `--canvas-radius-x4` px of the four
    outer canvas edges, for a visible frame-rectangle boundary;
  - luminance feather: fades to 0 for pixels whose RGB mean luminance falls
    below `--luminance-low`, ramping up to full source alpha at
    `--luminance-high`. Useful when a baked-in background fills most of the
    canvas at roughly uniform, distinctly darker brightness than the object
    itself (a distance-based fade alone would also erode the object);
  - radial feather (validated on FLAME2S): fades to 0 outside an ellipse
    centred on each frame's own `centre_x1` anchor, full source alpha inside
    `--radial-inner-x4`, reaching 0 at `--radial-outer-x-x4` /
    `--radial-outer-y-x4` (independent horizontal/vertical radii for an oval).
    For a light source whose native sprite is too small to have a soft glow
    of its own, this turns a hard baked-in square into a deliberate round
    halo instead of trying to erase it.

RGB bytes are preserved exactly; the fade can only ever lower alpha, never
raise it (`alpha_final <= alpha_source`).

Reads a resource's ``02_upscale_x4`` stage from a completed animation run and
writes a standalone correction into
``animations/ressources/<RESREF>/runs/<run-id>/`` (or an explicit legacy path).
Never touches the source run or its runtime pack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

import animation_paths

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPSCALE_SCHEMA = "bg2-upscale-animation-frames-v1"
SCHEMA = "bg2-upscale-animation-alpha-feather-test-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    image.save(temporary, format="PNG", compress_level=9)
    temporary.replace(path)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def inner_feather_ramp(alpha: np.ndarray, radius: float) -> np.ndarray:
    """Ramp fading strictly inside the existing alpha silhouette.

    Padding makes pixels touching the canvas border see the transparent
    exterior, so an object that reaches the frame edge still fades there.
    """
    inside = alpha > 0
    padded = np.pad(inside, 1, mode="constant", constant_values=False)
    distance = distance_transform_edt(padded)[1:-1, 1:-1]
    ramp = np.clip((distance - 1.0) / radius, 0.0, 1.0)
    return ramp * ramp * (3.0 - 2.0 * ramp)


def canvas_edge_ramp(width: int, height: int, radius: float) -> np.ndarray:
    """Ramp fading strictly inward from the four outer canvas edges."""
    yy, xx = np.indices((height, width))
    distance = np.minimum.reduce((xx, width - 1 - xx, yy, height - 1 - yy))
    ramp = np.clip(distance.astype(np.float32) / radius, 0.0, 1.0)
    return ramp * ramp * (3.0 - 2.0 * ramp)


def luminance_ramp(rgb: np.ndarray, low: float, high: float) -> np.ndarray:
    """Ramp fading out pixels whose mean RGB luminance falls below `low`."""
    luminance = rgb.astype(np.float32).mean(axis=2)
    ramp = np.clip((luminance - low) / (high - low), 0.0, 1.0)
    return ramp * ramp * (3.0 - 2.0 * ramp)


def radial_ramp(
    width: int,
    height: int,
    center_x: float,
    center_y: float,
    inner_fraction: float,
    outer_radius_x: float,
    outer_radius_y: float,
) -> np.ndarray:
    """Ramp fading to 0 outside an ellipse centred on (center_x, center_y).

    `outer_radius_x`/`outer_radius_y` place the ellipse boundary (alpha 0).
    Full source alpha is kept out to `inner_fraction` (0-1) of that boundary;
    a smoothstep taper covers the rest, out to the edge.
    """
    yy, xx = np.indices((height, width)).astype(np.float32)
    dx = (xx - center_x) / outer_radius_x
    dy = (yy - center_y) / outer_radius_y
    ellipse_distance = np.sqrt(dx * dx + dy * dy)
    ramp = np.clip((1.0 - ellipse_distance) / max(1e-6, 1.0 - inner_fraction), 0.0, 1.0)
    return ramp * ramp * (3.0 - 2.0 * ramp)


def checkerboard(width: int, height: int, cell: int = 16) -> Image.Image:
    yy, xx = np.indices((height, width))
    cells = ((xx // cell) + (yy // cell)) % 2
    base = np.where(cells[..., None] == 0, 54, 82).astype(np.uint8)
    rgb = np.repeat(base, 3, axis=2)
    return Image.fromarray(rgb, "RGB").convert("RGBA")


def write_preview(original: Image.Image, faded: Image.Image, label: str, path: Path) -> None:
    width, height = original.size
    header = 30
    preview = Image.new("RGBA", (width * 2, height + header), (30, 30, 30, 255))
    for index, image in enumerate((original, faded)):
        background = checkerboard(width, height)
        background.alpha_composite(image)
        preview.alpha_composite(background, (index * width, header))
    draw = ImageDraw.Draw(preview)
    draw.text((10, 8), "sortie upscale", fill=(255, 255, 255, 255))
    draw.text((width + 10, 8), label, fill=(255, 255, 255, 255))
    save_png(preview, path)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resref", required=True)
    parser.add_argument("--run", required=True, help="identifiant ou chemin du run source")
    parser.add_argument("--runs-root", type=Path, help="racine explicite pour une reprise legacy")
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument(
        "--output-run",
        help="identifiant du nouveau run mono-resref dans le layout courant",
    )
    output_group.add_argument(
        "--output",
        type=Path,
        help="chemin explicite, réservé à la reprise legacy",
    )
    parser.add_argument(
        "--inner-radius-x4", type=float, default=0.0,
        help="fondu de silhouette (contour du masque), 0 = desactive",
    )
    parser.add_argument(
        "--canvas-radius-x4", type=float, default=0.0,
        help="fondu de bordure du canvas rectangulaire, 0 = desactive",
    )
    parser.add_argument(
        "--luminance-low", type=float, default=None,
        help="fondu par luminance RGB: alpha 0 en dessous de ce niveau (0-255)",
    )
    parser.add_argument(
        "--luminance-high", type=float, default=None,
        help="fondu par luminance RGB: alpha source atteint a partir de ce niveau (0-255)",
    )
    parser.add_argument(
        "--radial-outer-x-x4", type=float, default=None,
        help="fondu radial/ovale: demi-rayon horizontal (alpha 0) autour du centre de l'asset",
    )
    parser.add_argument(
        "--radial-outer-y-x4", type=float, default=None,
        help="fondu radial/ovale: demi-rayon vertical (alpha 0) autour du centre de l'asset",
    )
    parser.add_argument(
        "--radial-inner-fraction", type=float, default=0.3,
        help="fondu radial: fraction (0-1) du rayon exterieur gardee a pleine opacite avant le degrade",
    )
    args = parser.parse_args()

    resref = args.resref.upper()
    source_run = (
        (args.runs_root / args.run).resolve()
        if args.runs_root is not None
        else animation_paths.resolve_existing_run(args.run, [resref])
    )
    source_root = source_run / "resources" / resref / "02_upscale_x4"
    output = (
        animation_paths.resolve_run_destination(args.output_run, [resref])
        if args.output_run
        else args.output.resolve()
    )
    require(args.inner_radius_x4 >= 0, "Le rayon interieur ne peut pas etre negatif.")
    require(args.canvas_radius_x4 >= 0, "Le rayon de canvas ne peut pas etre negatif.")
    use_luminance = args.luminance_low is not None or args.luminance_high is not None
    if use_luminance:
        require(
            args.luminance_low is not None and args.luminance_high is not None,
            "--luminance-low et --luminance-high doivent etre fournis ensemble.",
        )
        require(0 <= args.luminance_low < args.luminance_high <= 255, "bornes de luminance invalides.")
    use_radial = args.radial_outer_x_x4 is not None or args.radial_outer_y_x4 is not None
    if use_radial:
        require(
            args.radial_outer_x_x4 is not None and args.radial_outer_y_x4 is not None,
            "--radial-outer-x-x4 et --radial-outer-y-x4 doivent etre fournis ensemble.",
        )
        require(args.radial_outer_x_x4 > 0 and args.radial_outer_y_x4 > 0, "rayons radiaux invalides.")
        require(0 <= args.radial_inner_fraction < 1, "--radial-inner-fraction doit etre dans [0,1[.")
    require(
        args.inner_radius_x4 > 0 or args.canvas_radius_x4 > 0 or use_luminance or use_radial,
        "Au moins un fondu (interieur, canvas, luminance ou radial) doit etre actif.",
    )
    require(not output.exists() or not any(output.iterdir()), f"sortie non vide : {output}")

    source_manifest_path = source_root / "manifest.json"
    require(source_manifest_path.is_file(), f"manifest d'upscale absent : {source_manifest_path}")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8-sig"))
    require(
        source_manifest.get("schema") == UPSCALE_SCHEMA and source_manifest.get("status") == "completed",
        "run source incomplet ou schema incompatible.",
    )
    require(int(source_manifest.get("scale", 0)) == 4, "seul le canal runtime x4 est pris en charge.")

    source_frames = sorted(source_manifest.get("frames") or [], key=lambda item: int(item["frame"]))
    frame_count = len(source_frames)
    require(frame_count > 0, "aucune frame dans le run source.")

    directories = {
        "rgba": output / "rgba",
        "alpha": output / "alpha",
        "raw": output / "raw_rgba",
        "preview": output / "preview",
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    label_parts = []
    if args.inner_radius_x4:
        label_parts.append(f"objet {args.inner_radius_x4:g}px")
    if args.canvas_radius_x4:
        label_parts.append(f"canvas {args.canvas_radius_x4:g}px")
    if use_luminance:
        label_parts.append(f"lum {args.luminance_low:g}-{args.luminance_high:g}")
    if use_radial:
        label_parts.append(f"radial {args.radial_outer_x_x4:g}x{args.radial_outer_y_x4:g}px")
    label = "fondu " + " + ".join(label_parts)

    records: list[dict[str, Any]] = []
    preview_original: Image.Image | None = None
    preview_faded: Image.Image | None = None
    canvas_ramp_cache: dict[tuple[int, int], np.ndarray] = {}
    for index, frame in enumerate(source_frames):
        require(int(frame["frame"]) == index, "index de frame non contigu.")
        raw_relative = str(frame["raw_rgba_xn"])
        raw_source = (source_root / raw_relative).resolve()
        physical_width, physical_height = (int(value) for value in frame["physical_size_xn"])
        expected_bytes = physical_width * physical_height * 4
        require(
            raw_source.is_file()
            and raw_source.stat().st_size == expected_bytes
            and sha256(raw_source) == str(frame["raw_rgba_xn_sha256"]).lower(),
            f"asset brut source incoherent : {raw_source}",
        )
        asset_name = f"AAX4-{resref}-frame{index:03d}.rgba"

        source_pixels = np.frombuffer(raw_source.read_bytes(), dtype=np.uint8).reshape(
            (physical_height, physical_width, 4)
        )
        pixels = source_pixels.copy()
        source_alpha = source_pixels[:, :, 3]
        faded = source_alpha.astype(np.float32)
        if args.inner_radius_x4:
            faded = faded * inner_feather_ramp(source_alpha, args.inner_radius_x4)
        if args.canvas_radius_x4:
            key = (physical_width, physical_height)
            if key not in canvas_ramp_cache:
                canvas_ramp_cache[key] = canvas_edge_ramp(physical_width, physical_height, args.canvas_radius_x4)
            faded = faded * canvas_ramp_cache[key]
        if use_luminance:
            faded = faded * luminance_ramp(source_pixels[:, :, :3], args.luminance_low, args.luminance_high)
        if use_radial:
            centre_x1 = frame.get("centre_x1")
            require(isinstance(centre_x1, list) and len(centre_x1) == 2, f"{asset_name}: centre_x1 absent du manifeste source.")
            center_x = float(centre_x1[0]) * 4.0
            center_y = float(centre_x1[1]) * 4.0
            faded = faded * radial_ramp(
                physical_width, physical_height, center_x, center_y,
                args.radial_inner_fraction, args.radial_outer_x_x4, args.radial_outer_y_x4,
            )
        faded_alpha = np.rint(faded).astype(np.uint8)
        require(bool(np.all(faded_alpha <= source_alpha)), f"{asset_name}: alpha etendu hors du masque source.")
        pixels[:, :, 3] = faded_alpha
        require(
            bool(np.array_equal(pixels[:, :, :3], source_pixels[:, :, :3])),
            f"{asset_name}: RGB modifie.",
        )

        rgba = Image.fromarray(pixels, "RGBA")
        rgba_path = directories["rgba"] / f"frame_{index:03d}.png"
        alpha_path = directories["alpha"] / f"frame_{index:03d}.png"
        raw_path = directories["raw"] / asset_name
        save_png(rgba, rgba_path)
        save_png(Image.fromarray(faded_alpha, "L"), alpha_path)
        temporary_raw = raw_path.with_suffix(raw_path.suffix + ".part")
        temporary_raw.write_bytes(pixels.tobytes(order="C"))
        temporary_raw.replace(raw_path)

        records.append({
            "frame": index,
            "source_runtime_asset": raw_relative,
            "source_runtime_sha256": sha256(raw_source),
            "source_runtime_bytes": raw_source.stat().st_size,
            "runtime_asset": raw_path.relative_to(output).as_posix(),
            "runtime_sha256": sha256(raw_path),
            "runtime_bytes": raw_path.stat().st_size,
            "rgba": rgba_path.relative_to(output).as_posix(),
            "rgba_sha256": sha256(rgba_path),
            "alpha": alpha_path.relative_to(output).as_posix(),
            "alpha_sha256": sha256(alpha_path),
            "source_alpha_opaque_pixels": int(np.count_nonzero(source_alpha == 255)),
            "fade_changed_alpha_pixels": int(np.count_nonzero(faded_alpha != source_alpha)),
            "source_alpha_nonzero_canvas_border_pixels": int(
                np.count_nonzero(source_alpha[0, :])
                + np.count_nonzero(source_alpha[-1, :])
                + np.count_nonzero(source_alpha[1:-1, 0])
                + np.count_nonzero(source_alpha[1:-1, -1])
            ),
        })
        if index == 0:
            preview_original = Image.fromarray(source_pixels, "RGBA")
            preview_faded = rgba

    require(preview_original is not None and preview_faded is not None, "preview impossible.")
    write_preview(preview_original, preview_faded, label, directories["preview"] / "frame_000-comparison.png")

    operation_names = []
    if args.inner_radius_x4:
        operation_names.append("inner-distance-feather")
    if args.canvas_radius_x4:
        operation_names.append("canvas-edge-feather")
    if use_luminance:
        operation_names.append("luminance-feather")
    if use_radial:
        operation_names.append("radial-feather")
    operation_type = "-plus-".join(operation_names)

    physical_sizes = {tuple(int(v) for v in frame["physical_size_xn"]) for frame in source_frames}
    manifest = {
        "schema": SCHEMA,
        "status": "completed",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "resref": resref,
        "scale": 4,
        "frame_count": frame_count,
        "physical_size_x4": list(next(iter(physical_sizes))) if len(physical_sizes) == 1 else None,
        "source_run": source_root.as_posix(),
        "source_run_manifest_sha256": sha256(source_manifest_path),
        "alpha_operation": {
            "type": operation_type,
            "radius_physical_x4": args.inner_radius_x4 or None,
            "radius_logical_x1": (args.inner_radius_x4 / 4.0) if args.inner_radius_x4 else None,
            "canvas_edge_radius_physical_x4": args.canvas_radius_x4 or None,
            "canvas_edge_radius_logical_x1": (args.canvas_radius_x4 / 4.0) if args.canvas_radius_x4 else None,
            "edges": ["top", "right", "bottom", "left"] if args.canvas_radius_x4 else None,
            "luminance_low": args.luminance_low,
            "luminance_high": args.luminance_high,
            "radial_outer_x_physical_x4": args.radial_outer_x_x4,
            "radial_outer_y_physical_x4": args.radial_outer_y_x4,
            "radial_inner_fraction": args.radial_inner_fraction if use_radial else None,
            "curve": "smoothstep",
            "outside_source_mask": 0,
            "rgb_policy": "unchanged",
            "alpha_constraint": "final<=source",
        },
        "frames": records,
    }
    write_json(manifest, output / "manifest.json")
    print(f"{resref}: {frame_count} frames construites, {label}.")


if __name__ == "__main__":
    main()
