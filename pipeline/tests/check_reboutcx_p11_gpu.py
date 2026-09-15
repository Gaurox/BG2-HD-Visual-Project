"""Bounded padding probe: real frames, batch 86; no jobs/runs or image files."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from reboutcx_full import read_json, resolve_path_reference, reconstruct_rgba
from reboutcx_batch import load_palette_profiles
from reboutcx_quantize import semantic_classes_for_job
from reboutcx_runtime_p10 import Runtime, prepare_resource, postprocess_batch
from run_creature_sprite_x2 import SourceFrame, decode_bam


def check(family: Path) -> dict:
    start = time.perf_counter()
    counts, samples = Counter(), {}
    for path in sorted(family.glob("*/runs/reboutcx-p10-stream86-v1/manifest.json")):
        manifest = read_json(path)
        for resource in manifest["resources"]:
            if resource["reused_render_from"]:
                continue
            for frame in resource["frame_records"]:
                if frame["model_bypassed"]:
                    continue
                h, w = frame["height"], frame["width"]
                shape = ((h + 15) // 16 * 16, (w + 15) // 16 * 16)
                counts[shape] += 1
                samples.setdefault(shape, (manifest["job"], resource["resref"], frame["source_frame"]))
    selected = sorted(counts, key=lambda s: -counts[s] * ((s[0]+63)//64*64) * ((s[1]+63)//64*64))[:6]
    cases = []
    gpu_start = None
    with Runtime(pre_workers=1, post_workers=1, process_pools=False) as runtime:
        for shape in selected:
            job_path, name, index = samples[shape]
            job = read_json(resolve_path_reference(job_path))
            source = resolve_path_reference(job["paths"]["source_manifest"], required=True)
            bam = next(b for b in read_json(source)["bams"] if b["name"].upper() == name)
            decoded, palette, _ = decode_bam((source.parent / bam["canonical_bam"]).read_bytes())
            indices, cx, cy, tr = decoded[index]
            h, w = indices.shape
            frame = SourceFrame(name, index, w, h, cx, cy, tr, indices, palette,
                                reconstruct_rgba(indices, palette, tr).tobytes())
            profiles, _ = load_palette_profiles(job)
            reference = profiles[0]["palette"] if profiles else None
            classes, _ = semantic_classes_for_job(job)
            states, _ = prepare_resource({"frames": [frame]}, resolve_path_reference(job["paths"]["scalepix"]),
                                         job["tools"].get("node", "node"), job["null_frame_marker"], reference, classes)
            state = states[index]
            model = resolve_path_reference(job["paths"]["reboutcx_model"], required=True)
            runtime.model_info(model, device=job["reboutcx"]["device"], fp16=True)
            gpu_start = gpu_start or time.perf_counter()
            results, timings, by_canvas = {}, {}, {}
            for quantum in (64, 32, 16):
                canvas = ((h + quantum - 1)//quantum*quantum, (w + quantum - 1)//quantum*quantum)
                if canvas not in by_canvas:
                    # Warm the shape with two frames, then explicitly time one full micro-lot.
                    runtime.infer([state["rgb"]] * 2, canvas, True).result()
                    crops, elapsed = runtime.infer([state["rgb"]] * 86, canvas, True).result()
                    output, _ = postprocess_batch([(index, state["guide"], state["palette"], np.unique(indices),
                                                  tr, crops[0], True)], classes)
                    del crops
                    by_canvas[canvas] = (output[0], elapsed)
                results[quantum], timings[quantum] = by_canvas[canvas]
            lookup = np.full(256, -1, dtype=np.int16)
            for number, values in enumerate(classes.values()):
                lookup[values] = number
            visible = state["guide"] != tr
            border = np.zeros_like(visible)
            border[-4:, :] = True
            border[:, -4:] = True
            differences = {}
            for quantum, (_index, quantized, _metrics, target) in results.items():
                np.testing.assert_array_equal(quantized == tr, ~visible)
                np.testing.assert_array_equal(lookup[quantized], lookup[state["guide"]])
                assert set(np.unique(quantized)) <= set(np.unique(indices))
                changed = (quantized != results[64][1]) & visible
                delta = np.abs(target.astype(np.int16) - results[64][3].astype(np.int16))
                differences[quantum] = {"changed_visible_indices": int(changed.sum()), "visible_pixels": int(visible.sum()),
                    "changed_bottom_right_border_indices": int((changed & border).sum()),
                    "visible_rgb_absolute_delta_mean_u8": float(delta[visible].mean()),
                    "visible_rgb_absolute_delta_max_u8": int(delta[visible].max())}
            cases.append({"job": job_path, "resref": name, "frame": index, "native_shape": [h, w],
                          "shape_family_frames": counts[shape], "batch_size": 86,
                          "timings": timings, "differences_from_p10_padding": differences})
            if time.perf_counter() - gpu_start > 8:
                break
    return {"status": "padding-probe-contracts-passed", "cases": cases,
            "sampled_shape_family_frames": sum(c["shape_family_frames"] for c in cases),
            "total_family_model_frames": sum(counts.values()), "model_load_seconds": runtime.model_load_seconds,
            "total_seconds": time.perf_counter() - start, "temporary_files_created": 0,
            "production_runs": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", type=Path)
    print(json.dumps(check(parser.parse_args().family)))
