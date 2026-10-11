"""v8 targeted warm-patch blur.

Seed  = union over the loop of very-bright warm cores (V>92), largest component
        -> reliably the coulure core, never a disconnected bright pool patch.
Grow  = binary_propagation of the seed through the warm region that is bright at
        some point in the loop (Vmax>grow_T & warm) -> the seed expands to the
        full coulure extent but cannot jump to a separate bright region.
Then small margin dilation + feather. Blur radius default 5.
No seed anywhere (A, D) -> empty mask -> untouched.
"""
import numpy as np
from PIL import Image
from scipy.ndimage import (gaussian_filter, binary_dilation, binary_closing,
                           binary_fill_holes, binary_propagation, label)

RADIUS = 5

def _hsv_stack(frames_rgb):
    return np.stack([np.asarray(Image.fromarray(r).convert("HSV"), np.uint8) for r in frames_rgb])

def union_mask(frames_rgb, seed_T=92, grow_T=76, min_seed=140,
               margin_dil=3, feather=4.0):
    hsv = _hsv_stack(frames_rgb)                 # (N,H,W,3)
    H = hsv[..., 0]; S = hsv[..., 1]; V = hsv[..., 2]
    warm_any = (((H < 34) | (H > 228)) & (S > 60)).any(0)
    Vmax = V.max(0).astype(np.float32)
    warm_grow = (Vmax > grow_T) & warm_any
    warm_grow = binary_closing(warm_grow, iterations=1)

    seed = np.zeros(Vmax.shape, bool)
    for i in range(hsv.shape[0]):
        wm = ((H[i] < 34) | (H[i] > 228)) & (S[i] > 60)
        seed |= (V[i] > seed_T) & wm
    seed = binary_closing(seed, iterations=1)
    lab, n = label(seed)
    if n == 0:
        return np.zeros(Vmax.shape, np.float32)
    sizes = np.array([(lab == k).sum() for k in range(1, n + 1)])
    if sizes.max() < min_seed:
        return np.zeros(Vmax.shape, np.float32)
    seed = (lab == int(sizes.argmax()) + 1)

    grown = binary_propagation(seed, mask=(warm_grow | seed))
    grown = binary_fill_holes(binary_closing(grown, iterations=2))
    grown = binary_dilation(grown, iterations=margin_dil).astype(np.float32)
    return np.clip(gaussian_filter(grown, feather), 0, 1)

def process_sequence(frames_rgba, radius=RADIUS, **mk):
    M = union_mask([a[:, :, :3] for a in frames_rgba], **mk)[..., None]
    out = []
    for a in frames_rgba:
        rgb = a[:, :, :3].astype(np.float32)
        blur = np.stack([gaussian_filter(rgb[..., c], radius) for c in range(3)], -1)
        merged = np.rint(rgb * (1 - M) + blur * M).clip(0, 255).astype(np.uint8)
        out.append(np.dstack([merged, a[:, :, 3]]))
    return out, M[..., 0]
