"""Create a manually requested, periodic-spline alpha mask for one asset.

This tool only writes the requested PNG.  It never modifies a runtime pack,
an override, a map build, or the source alpha.  The caller must explicitly use
the resulting mask in a separate asset build after visual review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import splprep, splev


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resample_closed(points: np.ndarray, spacing: float) -> np.ndarray:
    loop = np.vstack((points, points[0]))
    distances = np.hypot(np.diff(loop[:, 0]), np.diff(loop[:, 1]))
    cumulative = np.concatenate(([0.0], np.cumsum(distances)))
    positions = np.arange(0.0, cumulative[-1], spacing)
    if len(positions) < 4:
        return points
    return np.column_stack((np.interp(positions, cumulative, loop[:, 0]),
                            np.interp(positions, cumulative, loop[:, 1])))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a single-silhouette periodic spline alpha mask; does not install it.")
    parser.add_argument("source", type=Path, help="input alpha PNG, grayscale or RGBA")
    parser.add_argument("output", type=Path, help="new output PNG; must not already exist")
    parser.add_argument("--fit-error", type=float, default=1.0,
                        help="smoothing tolerance in source pixels; AR0604 validated value: 1.0")
    parser.add_argument("--sample-spacing", type=float, default=1.5,
                        help="contour resampling step in source pixels")
    parser.add_argument("--threshold", type=int, default=127)
    parser.add_argument("--supersample", type=int, default=4)
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit(f"source absent: {args.source}")
    if args.output.exists():
        raise SystemExit(f"refus d'écraser une sortie existante: {args.output}")
    if args.fit_error <= 0 or args.sample_spacing <= 0 or not 0 <= args.threshold <= 255 or args.supersample < 1:
        raise SystemExit("paramètres spline invalides")

    alpha = Image.open(args.source).convert("L")
    binary = np.asarray(alpha) > args.threshold
    paths = plt.contour(binary.astype(np.uint8), levels=[0.5]).get_paths()
    plt.close()
    if not paths:
        raise SystemExit("aucun contour alpha détecté")
    # Asset pipeline: the largest closed silhouette is deliberately selected.
    # Multi-ring maps (holes/secondary states) must use build_spline_map_alpha.py.
    contour = max((path.vertices for path in paths), key=len)
    if np.allclose(contour[0], contour[-1]):
        contour = contour[:-1]
    samples = resample_closed(contour, args.sample_spacing)
    if len(samples) < 4:
        raise SystemExit("contour insuffisant pour une spline périodique")
    tck, _ = splprep([samples[:, 0], samples[:, 1]],
                      s=len(samples) * args.fit_error ** 2, per=True, k=3)
    curve = np.asarray(splev(np.linspace(0.0, 1.0, len(samples) * 3, endpoint=False), tck)).T

    high = Image.new("L", (alpha.width * args.supersample, alpha.height * args.supersample), 0)
    ImageDraw.Draw(high).polygon([tuple(point * args.supersample) for point in curve], fill=255)
    result = high.resize(alpha.size, Image.Resampling.LANCZOS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output)
    print(json.dumps({
        "method": "single-silhouette periodic spline",
        "source": str(args.source.resolve()),
        "source_sha256": sha256(args.source),
        "output": str(args.output.resolve()),
        "size": [alpha.width, alpha.height],
        "threshold": args.threshold,
        "fit_error": args.fit_error,
        "sample_spacing": args.sample_spacing,
        "supersample": args.supersample,
        "input_vertices": len(contour),
        "fit_samples": len(samples),
        "curve_points": len(curve),
        "installation": "not performed",
    }, indent=2))


if __name__ == "__main__":
    main()
