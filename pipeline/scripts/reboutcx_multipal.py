"""P1 float-target inference with the existing P12 fixed86/q32 kernel and keys."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time

import numpy as np

from reboutcx_batch import load_model, prepare_inference_rgb
from reboutcx_batch_p12 import infer_float_crops
from reboutcx_cache_p12 import frame_key
from run_creature_sprite_x2 import (
    direct_upscale_contract, has_duplicate_used_rgba_indices, map_output,
    run_xbr, xbr_provenance_indices,
)
from workspace_paths import get_path

INFERENCE_ID = "reboutcx-multipal-float32-p12-fixed86-q32-box-v1"
SCRIPTS = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part")
    with temporary.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
    temporary.replace(path)


def inference_context() -> dict:
    import torch
    return {"id": INFERENCE_ID, "model_sha256": sha256_file(get_path("reboutcx_model", required=True)),
            "batch_size": 86, "canvas_quantum": 32, "fp16": True,
            "target": "float32[0,1]; direct x4; BOX float32 to x2 before encoding",
            "torch": str(torch.__version__), "device": torch.cuda.get_device_name(0),
            "dependencies": {name: importlib.metadata.version(name)
                             for name in ("numpy", "scipy", "spandrel", "chainner_ext")},
            "kernels": {name: sha256_file(SCRIPTS / name) for name in
                        ("reboutcx_batch.py", "reboutcx_batch_p10.py", "reboutcx_batch_p12.py")}}


def prepare_guides(frames: dict, output: Path) -> dict:
    scalepix = get_path("mmpx_scalepix", required=True)
    context = {"scalepix_sha256": sha256_file(scalepix),
               "adapter_sha256": sha256_file(SCRIPTS / "xbr2x_batch.js"),
               "mapping_sha256": sha256_file(SCRIPTS / "run_creature_sprite_x2.py")}
    keys = list(frames)
    for scale in (2, 4):
        missing = [key for key in keys if not (output / "guides" / f"{key}-x{scale}.npz").exists()]
        if not missing:
            continue
        rendered = run_xbr([frames[key] for key in missing], scalepix, "node", direct_upscale_contract(scale))
        for key, (width, height, rgba) in zip(missing, rendered, strict=True):
            frame = frames[key]
            provenance = xbr_provenance_indices(frame, scale) if has_duplicate_used_rgba_indices(frame) else None
            guide, _ = map_output(frame, rgba, provenance)
            save_npz(output / "guides" / f"{key}-x{scale}.npz", guide=guide.reshape(height, width))
    return context


def infer_targets(frames: dict, palettes: dict, output: Path, context: dict) -> tuple[dict, dict]:
    from chainner_ext import ResizeFilter, resize
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    import torch
    torch.set_num_threads(4)
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    context_bytes = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).digest()
    references, pending = {}, {}
    cache_dir = output / "targets"
    for name, palette in palettes.items():
        references[name] = {}
        for key, frame in frames.items():
            digest = frame_key(frame, palette, context_bytes).hex()
            path = cache_dir / f"{digest}.npz"
            references[name][key] = path.relative_to(output).as_posix()
            if not path.exists():
                pending.setdefault(digest, (path, frame, palette))
    timings = defaultdict(float)
    timings["logical_requests"] = len(frames) * len(palettes)
    timings["unique_targets"] = len({p for by_frame in references.values() for p in by_frame.values()})
    timings["missing_targets"] = len(pending)
    if not pending:
        return references, dict(timings)
    descriptor, versions = load_model(get_path("reboutcx_model", required=True), device="cuda:0", fp16=True)
    groups = defaultdict(list)
    for record in pending.values():
        frame = record[1]
        groups[((frame.height + 31)//32*32, (frame.width + 31)//32*32)].append(record)
    completed, started = 0, time.perf_counter()
    for canvas, records in sorted(groups.items()):
        for first in range(0, len(records), 86):
            batch = records[first:first+86]
            rgbs = [prepare_inference_rgb(frame, palette) for _, frame, palette in batch]
            if any(rgb is None for rgb in rgbs):
                raise ValueError("inference corpus contains fully transparent frame")
            crops, measured = infer_float_crops(descriptor, rgbs, canvas=canvas, fp16=True)
            for label, value in measured.items():
                timings[label] += value
            for (path, frame, _), crop in zip(batch, crops, strict=True):
                x2 = resize(crop, (frame.width*2, frame.height*2), ResizeFilter.Box, False)
                save_npz(path, x4=crop, x2=np.ascontiguousarray(np.clip(x2, 0, 1), dtype=np.float32))
            completed += len(batch)
            print(f"targets {completed}/{len(pending)}; elapsed {time.perf_counter()-started:.1f}s", flush=True)
    timings["total_wall_seconds"] = time.perf_counter()-started
    # Repeat one real input with the same fixed N/canvas contract before closing.
    _, check_frame, check_palette = next(iter(pending.values()))
    canvas = ((check_frame.height+31)//32*32, (check_frame.width+31)//32*32)
    repeat, _ = infer_float_crops(descriptor, [prepare_inference_rgb(check_frame, check_palette)],
                                  canvas=canvas, fp16=True)
    check_path = next(iter(pending.values()))[0]
    with np.load(check_path, allow_pickle=False) as data:
        delta = float(np.max(np.abs(data["x4"]-repeat[0])))
    timings["repeat_target_max_abs_delta"] = delta
    if delta != 0:
        raise RuntimeError(f"P12 target repeat is not bit-exact: {delta}")
    timings["versions"] = versions
    return references, dict(timings)
