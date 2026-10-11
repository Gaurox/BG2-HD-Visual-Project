"""Prototype: corner-aware Taubin smoothing of a binary alpha contour.

Taubin smoothing is a two-pass geometric filter.  It removes the high-frequency
right-angle oscillation of a pixel staircase without the overshoot of a fitted
cubic spline; the negative pass compensates for the normal shrinkage of a
simple moving-average filter.
"""

from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw


def resample_closed(points: np.ndarray, spacing: float) -> np.ndarray:
    loop = np.vstack((points, points[0]))
    lengths = np.hypot(np.diff(loop[:, 0]), np.diff(loop[:, 1]))
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    sample_at = np.arange(0.0, cumulative[-1], spacing)
    return np.column_stack((np.interp(sample_at, cumulative, loop[:, 0]),
                            np.interp(sample_at, cumulative, loop[:, 1])))


def curvature_anchors(points: np.ndarray, window: int, turn_threshold: float) -> np.ndarray:
    """Keep broad, intentional corners; pixel-scale stair turns are ignored."""
    before = np.roll(points, window, axis=0) - points
    after = np.roll(points, -window, axis=0) - points
    cosine = np.sum(before * after, axis=1) / (np.linalg.norm(before, axis=1)
                                                * np.linalg.norm(after, axis=1) + 1e-9)
    # Straight continuation has vectors pointing in opposite directions (-1).
    return cosine > turn_threshold


def smooth(points: np.ndarray, anchors: np.ndarray, iterations: int, lam: float, mu: float) -> np.ndarray:
    result = points.copy()
    for _ in range(iterations):
        for weight in (lam, mu):
            laplacian = (np.roll(result, 1, axis=0) + np.roll(result, -1, axis=0)) * 0.5 - result
            candidate = result + weight * laplacian
            candidate[anchors] = points[anchors]
            result = candidate
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--iterations", type=int, default=18)
    parser.add_argument("--spacing", type=float, default=1.0)
    parser.add_argument("--anchor-window", type=int, default=14)
    parser.add_argument("--turn-threshold", type=float, default=-0.45)
    parser.add_argument("--supersample", type=int, default=4)
    args = parser.parse_args()
    if args.iterations < 1 or args.spacing <= 0 or args.anchor_window < 2 or args.supersample < 1:
        raise SystemExit("invalid Taubin parameters")

    alpha = Image.open(args.source).convert("L")
    binary = np.asarray(alpha) > 127
    paths = plt.contour(binary.astype(np.uint8), levels=[0.5]).get_paths()
    plt.close()
    contour = max((path.vertices for path in paths), key=len)
    if np.allclose(contour[0], contour[-1]):
        contour = contour[:-1]
    samples = resample_closed(contour, args.spacing)
    anchors = curvature_anchors(samples, args.anchor_window, args.turn_threshold)
    curve = smooth(samples, anchors, args.iterations, lam=0.34, mu=-0.35)

    high = Image.new("L", (alpha.width * args.supersample, alpha.height * args.supersample), 0)
    ImageDraw.Draw(high).polygon([tuple(point * args.supersample) for point in curve], fill=255)
    high.resize(alpha.size, Image.Resampling.LANCZOS).save(args.output)
    print(f"input vertices={len(contour)}, resampled={len(samples)}, anchored={int(anchors.sum())}")
    print(f"wrote {args.output}: iterations={args.iterations}, anchor-window={args.anchor_window}")


if __name__ == "__main__":
    main()
