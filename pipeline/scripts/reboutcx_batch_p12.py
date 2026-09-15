"""Fixed N=86 CUDA execution; fillers stay on the GPU and are never quantized."""
from __future__ import annotations
import time
import numpy as np
from reboutcx_batch_p10 import pack_normalized


def infer_float_crops(descriptor, rgb_batch, *, canvas, fp16):
    import torch
    count = len(rgb_batch)
    if not 1 <= count <= 86:
        raise RuntimeError("P12 requires one to 86 real inputs")
    started = time.perf_counter()
    filler = np.zeros((1, 1, 3), dtype=np.uint8)
    source = pack_normalized([*rgb_batch, *([filler] * (86-count))], *canvas)
    packed = time.perf_counter()
    tensor = torch.from_numpy(source.transpose(0,3,1,2)).cuda()
    tensor = tensor.half() if fp16 else tensor.float()
    copied = time.perf_counter()
    begin, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    with torch.inference_mode():
        begin.record()
        prediction = descriptor(tensor)
        end.record()
        if prediction.shape != (86,3,canvas[0]*4,canvas[1]*4):
            raise RuntimeError("P12 model returned an unexpected padded shape")
        output = prediction[:count].float().clamp(0,1).cpu().numpy()
    downloaded = time.perf_counter()
    end.synchronize()
    crops = [np.ascontiguousarray(item[:,:rgb.shape[0]*4,:rgb.shape[1]*4].transpose(1,2,0))
             for item,rgb in zip(output,rgb_batch,strict=True)]
    return crops, {"pack_seconds":packed-started,"h2d_submit_seconds":copied-packed,
        "model_cuda_seconds":begin.elapsed_time(end)/1000,
        "model_wait_and_d2h_seconds":downloaded-copied,
        "crop_seconds":time.perf_counter()-downloaded,"dispatch_wall_seconds":time.perf_counter()-started,
        "gpu_slots":86,"gpu_filler_frames":86-count}
