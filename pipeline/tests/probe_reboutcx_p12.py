"""Bounded read-only P12 research probes. No production jobs, runs or model writes."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from reboutcx_full import read_json, resolve_path_reference
from bam_export import decode_bam


def duplicates(family: Path, max_seconds: float) -> dict:
    start = time.perf_counter()
    components = []
    for path in sorted(family.glob("*/runs/reboutcx-p11-q32-group86-v1/manifest.json")):
        m = read_json(path)
        source = resolve_path_reference(m["source_manifest"])
        bams = {b["name"].upper(): source.parent / b["canonical_bam"] for b in read_json(source)["bams"]}
        resources = [r for r in m["resources"] if not r["reused_render_from"]]
        groups = {name: i for i, names in enumerate(m["method"]["resource_groups"]) for name in names}
        palette = m["palette_reference"]["profiles"][0]["palette_rgb_sha256"]
        components.append((path.parent.parent.parent.name, m, bams, resources, groups, palette))
    # Round-robin resources: even a time-limited scan covers diverse components.
    work = [(c, c[3][i]) for i in range(max(len(c[3]) for c in components)) for c in components if i < len(c[3])]
    sets = {name: set() for name in ("resource", "group", "component", "family")}
    counts = Counter()
    per_component = {}
    outputs = {}
    frequency = Counter()
    dimensions = {}
    full_transform = set()
    scanned_bams = 0
    for (name, m, bams, resources, groups, palette), resource in work:
        if time.perf_counter() - start >= max_seconds:
            break
        resref = resource["resref"]
        frames, source_palette, _transparent = decode_bam(bams[resref].read_bytes())
        assert len(frames) == len(resource["frame_records"])
        native_palette_bytes = source_palette.tobytes()
        classes_key = json.dumps(m["semantic_classes"], sort_keys=True)
        scanned_bams += 1
        local = per_component.setdefault(name, Counter())
        for (indices, _cx, _cy, tr), f in zip(frames, resource["frame_records"], strict=True):
            if f["model_bypassed"]:
                continue
            h, w = indices.shape
            assert (h, w) == (f["height"], f["width"])
            canvas = ((h + 31)//32*32, (w + 31)//32*32)
            fingerprint = (h, w, tr, palette, hashlib.sha256(indices).digest())
            frequency[fingerprint] += 1
            dimensions[fingerprint] = h * w
            transform_key = (fingerprint, native_palette_bytes, classes_key)
            if transform_key in full_transform:
                counts["full_transform_duplicate_frames"] += 1
                counts["full_transform_duplicate_padded_pixels"] += canvas[0] * canvas[1]
            full_transform.add(transform_key)
            # Sufficient identity of normalized/filled model input; not a maximal RGB dedup.
            keys = {"resource": (name, resref, fingerprint), "group": (name, groups[resref], fingerprint),
                    "component": (name, fingerprint), "family": fingerprint}
            counts["frames"] += 1
            counts["padded_pixels"] += canvas[0] * canvas[1]
            local["frames"] += 1
            for scope, key in keys.items():
                if key in sets[scope]:
                    counts[scope + "_duplicate_frames"] += 1
                    counts[scope + "_duplicate_padded_pixels"] += canvas[0] * canvas[1]
                    if scope == "component":
                        local["duplicate_frames"] += 1
                else:
                    sets[scope].add(key)
            previous = outputs.setdefault(fingerprint, (f["guide_sha256"], f["indices_sha256"]))
            if previous[0] == f["guide_sha256"] and previous[1] != f["indices_sha256"]:
                counts["same_input_and_guide_different_output_hash"] += 1
    return {"kind": "model-input-identity-lower-bound", "counts": dict(counts),
            "cache_sizes": {"all_unique_x2_rgb_u8_bytes": sum(dimensions.values()) * 12,
                "repeated_inputs_only_x2_rgb_u8_bytes": sum(dimensions[k] for k,n in frequency.items() if n > 1) * 12,
                "unique_repeated_inputs": sum(n > 1 for n in frequency.values())},
            "components_observed": len(per_component), "per_component": per_component,
            "resources_scanned": scanned_bams, "resources_available": len(work),
            "complete": scanned_bams == len(work), "seconds": time.perf_counter() - start,
            "scope_note": "Duplicates already removed by P11 whole-resource reuse are excluded. Positions/centres do not affect model RGB. Native palette may affect guides, which remain per-frame.",
            "files_created": 0, "cuda_calls": 0}


def gpu(family: Path, max_seconds: float) -> dict:
    start = time.perf_counter()
    import torch
    from reboutcx_batch import load_palette_profiles
    from reboutcx_batch_p10 import pack_normalized
    from reboutcx_quantize import semantic_classes_for_job
    from reboutcx_runtime_p10 import Runtime, prepare_resource, postprocess_batch
    from reboutcx_full import reconstruct_rgba
    from run_creature_sprite_x2 import SourceFrame
    from chainner_ext import ResizeFilter, resize
    probe = read_json(family / "family-runs/complete-reboutcx-p11-v1/measurements/padding-probe-v1.json")
    cases = []
    with Runtime(pre_workers=1, post_workers=1, process_pools=False) as runtime:
        for sample in (probe["cases"][1], probe["cases"][0]):
            job = read_json(resolve_path_reference(sample["job"]))
            source = resolve_path_reference(job["paths"]["source_manifest"])
            bam = next(b for b in read_json(source)["bams"] if b["name"].upper() == sample["resref"])
            frames, colors, _ = decode_bam((source.parent / bam["canonical_bam"]).read_bytes())
            index = sample["frame"]
            indices, cx, cy, tr = frames[index]
            h,w = indices.shape
            frame = SourceFrame(sample["resref"], index, w, h, cx, cy, tr, indices, colors,
                                reconstruct_rgba(indices, colors, tr).tobytes())
            profiles,_ = load_palette_profiles(job)
            classes,_ = semantic_classes_for_job(job)
            state = prepare_resource({"frames": [frame]}, resolve_path_reference(job["paths"]["scalepix"]),
                job["tools"].get("node", "node"), job["null_frame_marker"], profiles[0]["palette"], classes)[0][index]
            canvas = ((h+31)//32*32,(w+31)//32*32)
            runtime.model_info(resolve_path_reference(job["paths"]["reboutcx_model"]), device="cuda:0", fp16=True)

            def experiment():
                cpu = torch.from_numpy(pack_normalized([state["rgb"]]*86,*canvas).transpose(0,3,1,2))
                tensor = cpu.cuda().half()
                records, reference = [], None
                with torch.inference_mode():
                    for name in ("p11", "channels_last_weights", "contiguous_input", "p11_repeat"):
                        layout = torch.channels_last if name == "channels_last_weights" else torch.contiguous_format
                        torch.nn.utils.convert_conv2d_weight_memory_format(runtime.descriptor.model, layout)
                        source_tensor = tensor.contiguous() if name == "contiguous_input" else tensor
                        warm = runtime.descriptor(source_tensor)
                        del warm
                        torch.cuda.synchronize()
                        times = []
                        for _ in range(2):
                            begin,end = torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
                            begin.record(); prediction = runtime.descriptor(source_tensor); end.record(); end.synchronize()
                            times.append(begin.elapsed_time(end)/1000)
                        crop = prediction[0,:,:h*4,:w*4].float().clamp(0,1).permute(1,2,0).contiguous().cpu().numpy()
                        reference = crop.copy() if reference is None else reference
                        output,_ = postprocess_batch([(index,state["guide"],state["palette"],np.unique(indices),tr,crop,True)],classes)
                        records.append({"variant":name,"model_seconds":times,"mean_seconds":float(np.mean(times)),
                            "crop_max_absolute_difference":float(np.abs(crop-reference).max()),
                            "quantized_sha256":hashlib.sha256(output[0][1]).hexdigest()})
                    # BOX on the GPU, then uint8 before transfer: compare exact current CPU target.
                    current = prediction.float().clamp(0,1)
                    tick = time.perf_counter()
                    reduced = torch.nn.functional.avg_pool2d(current,2)
                    reduced = (reduced*255).round().clamp(0,255).to(torch.uint8)
                    target = reduced[0,:,:h*2,:w*2].permute(1,2,0).contiguous().cpu().numpy()
                    box_seconds = time.perf_counter()-tick
                    expected = np.rint(np.clip(resize(crop,(w*2,h*2),ResizeFilter.Box,False),0,1)*255).astype(np.uint8)
                return {"canvas":canvas,"batch":86,"input_already_channels_last":tensor.is_contiguous(memory_format=torch.channels_last),
                        "variants":records,"gpu_box_and_transfer_seconds":box_seconds,
                        "gpu_box_transfer_frames":1,
                        "gpu_box_changed_u8_channels":int(np.count_nonzero(target!=expected)),
                        "gpu_box_max_u8_difference":int(np.abs(target.astype(int)-expected.astype(int)).max())}
            cases.append(runtime.gpu.submit(experiment).result())
            if time.perf_counter()-start >= max_seconds:
                break
        return {"kind":"short-steady-layout-and-box-probe","cases":cases,"seconds":time.perf_counter()-start,
                "torch":torch.__version__,"cudnn":torch.backends.cudnn.version(),"gpu":torch.cuda.get_device_name(0),
                "model_load_seconds":runtime.model_load_seconds,"production_runs":0,"files_created":0,
                "note":"Two real inputs repeated to 86; one warm and two timed batches per variant; no family throughput extrapolation from two shapes."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["duplicates", "gpu"])
    parser.add_argument("family", type=Path)
    parser.add_argument("--max-seconds", type=float, default=6)
    args = parser.parse_args()
    print(json.dumps((duplicates if args.command == "duplicates" else gpu)(args.family, args.max_seconds)))
