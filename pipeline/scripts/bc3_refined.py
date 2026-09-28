"""Refined BC3 (DXT5) encoder: principal-axis endpoints refined by least squares.

Pillow's DXT5 encoder leaves a visible 4x4 block grid on smooth liquid textures (AR3000 teal
overlay page: step at block boundaries 1.24 vs 0.45 inside blocks, 0.64/0.66 before encoding).
This encoder fits each colour block on its principal axis, refines both RGB565 endpoints by
least squares on the assigned palette weights (keeps the best of each pass) and encodes the
alpha block with the 8-level mode. Output is a raw BC3 payload (16 bytes per block, row major),
the same layout Pillow writes after its DDS header.
"""
from __future__ import annotations

import numpy as np

_W4 = np.array([1.0, 0.0, 2 / 3, 1 / 3], np.float32)       # weight of c0 for index 0..3


def _to565(c):
    q = np.empty(c.shape[:-1], np.uint32)
    r = np.clip(np.rint(c[..., 0] * 31 / 255), 0, 31).astype(np.uint32)
    g = np.clip(np.rint(c[..., 1] * 63 / 255), 0, 63).astype(np.uint32)
    b = np.clip(np.rint(c[..., 2] * 31 / 255), 0, 31).astype(np.uint32)
    q[...] = (r << 11) | (g << 5) | b
    return q


def _from565(q):
    r = ((q >> 11) & 31).astype(np.float32)
    g = ((q >> 5) & 63).astype(np.float32)
    b = (q & 31).astype(np.float32)
    return np.stack([(r * 527 + 23) // 64, (g * 259 + 33) // 64, (b * 527 + 23) // 64], -1).astype(np.float32)


def _palette(q0, q1):
    c0, c1 = _from565(q0), _from565(q1)
    return np.stack([c0, c1, (2 * c0 + c1) / 3, (c0 + 2 * c1) / 3], 1)     # N,4,3


def _assign(pixels, pal):
    d = ((pixels[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1)      # N,16,4
    idx = d.argmin(-1)
    return idx, np.take_along_axis(d, idx[..., None], -1)[..., 0].sum(-1)


def _encode_colour(pixels):
    n = pixels.shape[0]
    mean = pixels.mean(1)
    centred = pixels - mean[:, None, :]
    cov = np.einsum('nki,nkj->nij', centred, centred)
    axis = np.ones((n, 3), np.float32) / np.sqrt(3)
    for _ in range(8):                                                   # power iteration
        axis = np.einsum('nij,nj->ni', cov, axis)
        axis /= np.maximum(np.linalg.norm(axis, axis=1, keepdims=True), 1e-6)
    t = np.einsum('nki,ni->nk', centred, axis)
    lo, hi = t.min(1), t.max(1)
    inset = (hi - lo) / 32
    e0 = mean + (hi - inset)[:, None] * axis
    e1 = mean + (lo + inset)[:, None] * axis
    best_q0, best_q1 = _to565(e0), _to565(e1)
    best_idx, best_err = _assign(pixels, _palette(best_q0, best_q1))
    for _ in range(3):                                                   # least-squares refit
        w = _W4[best_idx]                                                # N,16
        a, b = w, 1 - w
        aa, bb, ab = (a * a).sum(1), (b * b).sum(1), (a * b).sum(1)
        ax = np.einsum('nk,nkc->nc', a, pixels)
        bx = np.einsum('nk,nkc->nc', b, pixels)
        det = aa * bb - ab * ab
        ok = np.abs(det) > 1e-6
        det = np.where(ok, det, 1.0)
        c0 = (ax * bb[:, None] - bx * ab[:, None]) / det[:, None]
        c1 = (bx * aa[:, None] - ax * ab[:, None]) / det[:, None]
        c0 = np.where(ok[:, None], c0, e0)
        c1 = np.where(ok[:, None], c1, e1)
        q0, q1 = _to565(np.clip(c0, 0, 255)), _to565(np.clip(c1, 0, 255))
        idx, err = _assign(pixels, _palette(q0, q1))
        better = err < best_err
        best_q0 = np.where(better, q0, best_q0)
        best_q1 = np.where(better, q1, best_q1)
        best_idx = np.where(better[:, None], idx, best_idx)
        best_err = np.where(better, err, best_err)
    # BC3 colour blocks are always 4-colour; keep c0 >= c1 for decoders that check order.
    swap = best_q0 < best_q1
    q0 = np.where(swap, best_q1, best_q0)
    q1 = np.where(swap, best_q0, best_q1)
    idx = np.where(swap[:, None], np.array([1, 0, 3, 2])[best_idx], best_idx)
    equal = q0 == q1
    idx = np.where(equal[:, None], 0, idx)
    bits = (idx.astype(np.uint32) << (2 * np.arange(16, dtype=np.uint32))).sum(1).astype(np.uint32)
    return q0.astype(np.uint16), q1.astype(np.uint16), bits


def _encode_alpha(alpha):
    a0 = alpha.max(1)
    a1 = alpha.min(1)
    out = np.zeros((alpha.shape[0], 8), np.uint8)
    out[:, 0], out[:, 1] = a0, a1
    span = (a0.astype(np.float32) - a1)
    flat = span == 0
    # 8-level mode (a0 > a1): palette index 0=a0, 1=a1, 2..7 = (7-i)/7 a0 + (i-1)/7 a1 ... remapped
    levels = np.stack([a0, a1] + [((7 - k) * a0.astype(np.float32) + k * a1) / 7 for k in range(1, 7)], 1)
    d = np.abs(alpha[:, :, None].astype(np.float32) - levels[:, None, :])
    idx = d.argmin(-1).astype(np.uint64)
    idx[flat] = 0
    packed = (idx << (3 * np.arange(16, dtype=np.uint64))).sum(1).astype(np.uint64)
    for k in range(6):
        out[:, 2 + k] = ((packed >> np.uint64(8 * k)) & np.uint64(255)).astype(np.uint8)
    return out


def encode_bc3(rgba: np.ndarray, rows_per_chunk: int = 64) -> bytes:
    """rgba: (H, W, 4) uint8 with H and W multiples of 4. Returns the raw BC3 payload."""
    h, w = rgba.shape[:2]
    if h % 4 or w % 4:
        raise ValueError('BC3 needs dimensions multiple of 4')
    out = np.zeros((h // 4, w // 4, 16), np.uint8)
    for r0 in range(0, h // 4, rows_per_chunk):
        r1 = min(h // 4, r0 + rows_per_chunk)
        chunk = rgba[r0 * 4:r1 * 4].reshape(r1 - r0, 4, w // 4, 4, 4).transpose(0, 2, 1, 3, 4)
        blocks = chunk.reshape(-1, 16, 4)
        colour = blocks[:, :, :3].astype(np.float32)
        q0, q1, bits = _encode_colour(colour)
        alpha = _encode_alpha(blocks[:, :, 3])
        payload = np.zeros((blocks.shape[0], 16), np.uint8)
        payload[:, :8] = alpha
        payload[:, 8:10] = q0.view(np.uint8).reshape(-1, 2)
        payload[:, 10:12] = q1.view(np.uint8).reshape(-1, 2)
        payload[:, 12:16] = bits.view(np.uint8).reshape(-1, 4)
        out[r0:r1] = payload.reshape(r1 - r0, w // 4, 16)
    return out.tobytes()
