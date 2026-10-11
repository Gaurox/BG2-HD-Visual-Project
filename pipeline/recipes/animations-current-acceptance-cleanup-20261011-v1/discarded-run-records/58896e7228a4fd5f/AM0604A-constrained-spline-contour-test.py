"""Prototype: spline smoothing constrained to a narrow band around an alpha contour.

Unlike a free B-spline, the curve is not allowed to drift farther than the
chosen number of source pixels from the original silhouette.  This retains the
large-scale shape and prevents thin peninsulas from turning into tongues.
"""

from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import splprep, splev
from scipy.spatial import cKDTree


def resample_closed(points: np.ndarray, spacing: float) -> np.ndarray:
    loop = np.vstack((points, points[0]))
    distances = np.hypot(np.diff(loop[:, 0]), np.diff(loop[:, 1]))
    cumulative = np.concatenate(([0.0], np.cumsum(distances)))
    positions = np.arange(0.0, cumulative[-1], spacing)
    return np.column_stack((np.interp(positions, cumulative, loop[:, 0]),
                            np.interp(positions, cumulative, loop[:, 1])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--fit-error", type=float, default=2.0)
    parser.add_argument("--max-deviation", type=float, default=1.25,
                        help="maximum distance from the original contour, in source pixels")
    parser.add_argument("--sample-spacing", type=float, default=1.5)
    parser.add_argument("--supersample", type=int, default=4)
    args = parser.parse_args()
    if args.fit_error <= 0 or args.max_deviation <= 0 or args.sample_spacing <= 0:
        raise SystemExit("parameters must be positive")

    alpha = Image.open(args.source).convert("L")
    binary = np.asarray(alpha) > 127
    contours = plt.contour(binary.astype(np.uint8), levels=[0.5]).get_paths()
    plt.close()
    if not contours:
        raise SystemExit("no silhouette contour found")
    contour = max((path.vertices for path in contours), key=len)
    samples = resample_closed(contour, args.sample_spacing)
    tck, _ = splprep([samples[:, 0], samples[:, 1]],
                      s=len(samples) * args.fit_error ** 2, per=True, k=3)
    curve = np.asarray(splev(np.linspace(0.0, 1.0, len(samples) * 3, endpoint=False), tck)).T

    # The contour is sampled densely so nearest-point projection also applies
    # to the middle of a source segment, not only to its corners.
    source_band = resample_closed(contour, 0.20)
    distances, nearest = cKDTree(source_band).query(curve)
    outside_band = distances > args.max_deviation
    if np.any(outside_band):
        direction = curve[outside_band] - source_band[nearest[outside_band]]
        curve[outside_band] = (source_band[nearest[outside_band]]
                               + direction / distances[outside_band, None] * args.max_deviation)

    high = Image.new("L", (alpha.width * args.supersample, alpha.height * args.supersample), 0)
    ImageDraw.Draw(high).polygon([tuple(point * args.supersample) for point in curve], fill=255)
    high.resize(alpha.size, Image.Resampling.LANCZOS).save(args.output)
    print(f"input vertices={len(contour)}, samples={len(samples)}, curve={len(curve)}")
    print(f"constrained points={int(np.count_nonzero(outside_band))}/{len(curve)}")
    print(f"wrote {args.output}: fit-error={args.fit_error}, max-deviation={args.max_deviation}")


if __name__ == "__main__":
    main()
