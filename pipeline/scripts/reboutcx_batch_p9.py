"""P9-only CUDA micro-batches; the P8 module remains immutable for sealed runs."""

from __future__ import annotations

from typing import Any

import numpy as np

# Re-export the P8-proven helpers without modifying their evidence-bearing file.
from reboutcx_batch import (  # noqa: F401
    is_null_frame,
    load_model,
    load_palette_profiles,
    prepare_inference_rgb,
)


def infer_x4_box_x2_padded_batch(
    descriptor: Any,
    rgb_u8_batch: list[np.ndarray],
    *,
    canvas_height: int,
    canvas_width: int,
    fp16: bool,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """P9 contract: pad top-left, CUDA inference, crop, float32 BOX x2."""
    import torch
    from chainner_ext import ResizeFilter, resize

    if not rgb_u8_batch or canvas_height < 1 or canvas_width < 1:
        raise RuntimeError("P9 batch requires inputs and a positive canvas")
    source = np.zeros((len(rgb_u8_batch), canvas_height, canvas_width, 3), dtype=np.float32)
    dimensions: list[tuple[int, int]] = []
    for index, item in enumerate(rgb_u8_batch):
        rgb = np.asarray(item, dtype=np.uint8)
        if rgb.ndim != 3 or rgb.shape[2] != 3:
            raise RuntimeError("P9 batch input must be HWC RGB")
        height, width = rgb.shape[:2]
        if height > canvas_height or width > canvas_width:
            raise RuntimeError("P9 batch canvas is too small")
        source[index, :height, :width] = rgb
        dimensions.append((height, width))
    tensor = torch.from_numpy(source.transpose(0, 3, 1, 2)).cuda()
    tensor = tensor.half() if fp16 else tensor.float()
    with torch.inference_mode():
        output = descriptor(tensor).float().clamp(0, 1).cpu().numpy()
    results: list[tuple[np.ndarray, np.ndarray]] = []
    for item, (height, width) in zip(output, dimensions, strict=True):
        x4 = np.ascontiguousarray(
            item[:, : height * 4, : width * 4].transpose(1, 2, 0), dtype=np.float32
        )
        if x4.shape != (height * 4, width * 4, 3):
            raise RuntimeError("P9 batch crop dimensions differ")
        x2 = resize(x4, (width * 2, height * 2), ResizeFilter.Box, False)
        results.append(
            (
                np.rint(x4 * 255.0).astype(np.uint8),
                np.rint(np.clip(x2, 0, 1) * 255.0).astype(np.uint8),
            )
        )
    return results
