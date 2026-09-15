"""P10 normalized CUDA input; float32 crops are reduced/quantized by CPU workers."""
from __future__ import annotations

import time
from typing import Any

import numpy as np


def pack_normalized(rgb_batch: list[np.ndarray], height: int, width: int) -> np.ndarray:
    if not rgb_batch or height < 1 or width < 1:
        raise RuntimeError("P10 requires frames and a positive canvas")
    source = np.zeros((len(rgb_batch), height, width, 3), dtype=np.float32)
    for index, rgb in enumerate(rgb_batch):
        if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
            raise RuntimeError("P10 expects uint8 HWC RGB")
        h, w = rgb.shape[:2]
        if h < 1 or w < 1 or h > height or w > width:
            raise RuntimeError("P10 input does not fit its canvas")
        source[index, :h, :w] = rgb
    # Match P8: float32 division BEFORE FP16 conversion, including zero padding.
    source /= 255.0
    return source


def infer_float_crops(descriptor: Any, rgb_batch: list[np.ndarray], *,
                     canvas: tuple[int, int], fp16: bool) -> tuple[list[np.ndarray], dict]:
    import torch

    started = time.perf_counter()
    source = pack_normalized(rgb_batch, *canvas)
    packed = time.perf_counter()
    tensor = torch.from_numpy(source.transpose(0, 3, 1, 2)).cuda()
    tensor = tensor.half() if fp16 else tensor.float()
    copied = time.perf_counter()
    begin = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    with torch.inference_mode():
        begin.record()
        prediction = descriptor(tensor)
        end.record()
        output = prediction.float().clamp(0, 1).cpu().numpy()
    downloaded = time.perf_counter()
    end.synchronize()
    if output.shape != (len(rgb_batch), 3, canvas[0] * 4, canvas[1] * 4):
        raise RuntimeError("P10 model returned an unexpected padded shape")
    crops = [np.ascontiguousarray(item[:, :rgb.shape[0] * 4, :rgb.shape[1] * 4]
                                 .transpose(1, 2, 0), dtype=np.float32)
             for item, rgb in zip(output, rgb_batch, strict=True)]
    return crops, {
        "pack_seconds": packed - started,
        "h2d_submit_seconds": copied - packed,
        "model_cuda_seconds": begin.elapsed_time(end) / 1000.0,
        # This wall time includes model wait, cast, clamp and the blocking D2H copy.
        "model_wait_and_d2h_seconds": downloaded - copied,
        "crop_seconds": time.perf_counter() - downloaded,
        "dispatch_wall_seconds": time.perf_counter() - started,
    }
