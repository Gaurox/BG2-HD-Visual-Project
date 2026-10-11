"""Prototype: trace an alpha silhouette with Potrace Bézier curves, then rasterise it.

Potrace selects a compact mix of straight segments, corners and Bézier arcs.
This is intentionally different from the previous globally smoothed spline:
corners may remain corners instead of being pulled into an overshooting arc.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.append(str(WORKSPACE / ".tools" / "potracer"))
import potrace  # noqa: E402


def sample_curve(curve, samples_per_segment: int = 24) -> np.ndarray:
    def point(value) -> np.ndarray:
        return np.asarray((value.x, value.y), dtype=np.float64)

    current = point(curve.start_point)
    points = [current]
    for segment in curve:
        if segment.is_corner:
            points.extend((point(segment.c), point(segment.end_point)))
        else:
            p0 = current
            p1 = point(segment.c1)
            p2 = point(segment.c2)
            p3 = point(segment.end_point)
            t = np.linspace(0.0, 1.0, samples_per_segment + 1)[1:, None]
            points.extend((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
                          + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)
        current = point(segment.end_point)
    return np.asarray(points)


def signed_area(points: np.ndarray) -> float:
    loop = np.vstack((points, points[0]))
    return 0.5 * float(np.sum(loop[:-1, 0] * loop[1:, 1] - loop[1:, 0] * loop[:-1, 1]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--alphamax", type=float, default=0.55,
                        help="corner threshold: lower values preserve more real corners")
    parser.add_argument("--opttolerance", type=float, default=0.20,
                        help="Bézier fitting tolerance in source pixels")
    parser.add_argument("--turdsize", type=int, default=2,
                        help="discard isolated blobs smaller than this many pixels")
    parser.add_argument("--supersample", type=int, default=4)
    args = parser.parse_args()
    if not 0 <= args.alphamax <= 1 or args.opttolerance <= 0 or args.turdsize < 0 or args.supersample < 1:
        raise SystemExit("invalid Potrace parameters")

    alpha = Image.open(args.source).convert("L")
    binary = np.asarray(alpha) > 127
    path = potrace.Bitmap(binary).trace(turdsize=args.turdsize, alphamax=args.alphamax,
                                        opticurve=True, opttolerance=args.opttolerance)
    rings = [sample_curve(curve) for curve in path if len(curve)]
    if not rings:
        raise SystemExit("Potrace did not produce a contour")

    # Potrace emits its outer contour clockwise in image coordinates.  Draw
    # the largest ring first, then erase any oppositely oriented holes.
    high = Image.new("L", (alpha.width * args.supersample, alpha.height * args.supersample), 0)
    draw = ImageDraw.Draw(high)
    for ring in sorted(rings, key=lambda item: abs(signed_area(item)), reverse=True):
        draw.polygon([tuple(np.rint(point * args.supersample).astype(int)) for point in ring],
                     fill=255 if signed_area(ring) < 0 else 0)
    high.resize(alpha.size, Image.Resampling.LANCZOS).save(args.output)
    segments = sum(len(curve) for curve in path)
    print(f"curves={len(rings)}, segments={segments}, source contour pixels={int(binary.sum())}")
    print(f"wrote {args.output}: alphamax={args.alphamax}, opttolerance={args.opttolerance}")


if __name__ == "__main__":
    main()
