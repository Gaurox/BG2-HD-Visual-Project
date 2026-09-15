"""Two real frames, normalized reference comparison, no run/job/output creation."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))


def check(job_path: Path) -> dict:
    started = time.perf_counter()
    import numpy as np
    import torch
    from chainner_ext import ResizeFilter, resize
    from reboutcx_batch import load_palette_profiles, prepare_inference_rgb
    from reboutcx_full import read_json, resolve_path_reference
    from reboutcx_runtime_p10 import Runtime, postprocess_batch
    from reboutcx_quantize import semantic_classes_for_job, quantize_classed_oklab
    from run_creature_sprite_x2 import SourceFrame, decode_bam

    job = read_json(job_path)
    source = resolve_path_reference(job["paths"]["source_manifest"], required=True)
    bam = read_json(source)["bams"][0]
    decoded, source_palette, transparent = decode_bam((source.parent / bam["canonical_bam"]).read_bytes())
    profiles, _ = load_palette_profiles(job)
    palette = profiles[0]["palette"]
    classes, _ = semantic_classes_for_job(job)
    frames, rgbs = [], []
    for index, (indices, cx, cy, tr) in enumerate(decoded):
        h, w = indices.shape
        if h * w < 4:
            continue
        frame = SourceFrame(bam["name"], index, w, h, cx, cy, tr, indices, source_palette, b"")
        rgb = prepare_inference_rgb(frame, palette)
        if rgb is not None:
            frames.append(frame)
            rgbs.append(rgb)
        if len(frames) == 2:
            break
    if len(frames) != 2:
        raise RuntimeError("sample resource lacks two nonempty frames")
    canvas = (max((f.height + 63) // 64 * 64 for f in frames),
              max((f.width + 63) // 64 * 64 for f in frames))
    with Runtime(pre_workers=1, post_workers=1, process_pools=False) as runtime:
        model = resolve_path_reference(job["paths"]["reboutcx_model"], required=True)
        runtime.model_info(model, device=job["reboutcx"]["device"], fp16=job["reboutcx"]["fp16"])
        crops, timing = runtime.infer(rgbs, canvas, job["reboutcx"]["fp16"]).result()

        def reference():
            # Independent float32 normalization and zero-padding, same two-frame batch.
            source = np.stack([np.pad(rgb.astype(np.float32) / 255.0,
                              ((0, canvas[0] - rgb.shape[0]), (0, canvas[1] - rgb.shape[1]), (0, 0)))
                               for rgb in rgbs])
            tensor = torch.from_numpy(source.transpose(0, 3, 1, 2)).cuda()
            tensor = tensor.half() if job["reboutcx"]["fp16"] else tensor.float()
            with torch.inference_mode():
                prediction = runtime.descriptor(tensor).float().clamp(0, 1).cpu().numpy()
            return [np.ascontiguousarray(p[:, :f.height * 4, :f.width * 4].transpose(1, 2, 0))
                    for p, f in zip(prediction, frames, strict=True)]

        expected = runtime.gpu.submit(reference).result()
        for actual, original in zip(crops, expected, strict=True):
            np.testing.assert_array_equal(actual, original)
        for f, crop, original in zip(frames, crops, expected, strict=True):
            # Synthetic guide isolates BOX/quantization equivalence; no xBR production.
            guide = np.repeat(np.repeat(f.indices, 2, 0), 2, 1)
            target = np.rint(np.clip(resize(original, (f.width * 2, f.height * 2), ResizeFilter.Box, False), 0, 1) * 255).astype(np.uint8)
            wanted, _ = quantize_classed_oklab(target, guide, palette, np.unique(f.indices), classes, transparent_index=f.transparent)
            result, _ = postprocess_batch([(f.index, guide, palette, np.unique(f.indices), f.transparent, crop, True)], classes)
            np.testing.assert_array_equal(result[0][1], wanted)
            np.testing.assert_array_equal(result[0][3], target)
        return {"status": "two-frame-reference-passed", "distinct_frames": len(frames),
                "canvas": canvas, "model_load_seconds": runtime.model_load_seconds,
                "gpu_batch_timings": timing, "total_seconds": time.perf_counter() - started,
                "files_created": 0, "production_runs": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    print(json.dumps(check(parser.parse_args().job)))
