"""Read-only fixed-86 cost model over sealed P11 inputs; no rendering or CUDA."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import struct
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"pipeline/scripts"))
from reboutcx_full import read_json, resolve_path_reference, sha256_file
from run_creature_sprite_x2 import decode_bam
from reboutcx_cache_p12 import context_key


def probe(family, max_seconds):
    started = time.perf_counter()
    components, frequency, dimensions = [], Counter(), {}
    tools = {}
    baseline_pixels = baseline_frames = resources = 0
    for path in sorted(family.glob("*/runs/reboutcx-p11-q32-group86-v1/manifest.json")):
        manifest = read_json(path)
        job = read_json(resolve_path_reference(manifest["job"]))
        palette_sha = manifest["palette_reference"]["profiles"][0]["palette_rgb_sha256"]
        scalepix = resolve_path_reference(job["paths"]["scalepix"])
        if scalepix not in tools:
            tools[scalepix] = sha256_file(scalepix)
        context = context_key(job,manifest["semantic_classes"],tools[scalepix])
        source = resolve_path_reference(manifest["source_manifest"])
        bams = {b["name"].upper():b for b in read_json(source)["bams"]}
        records = {r["resref"]:r for r in manifest["resources"]}
        groups = []
        for names in manifest["method"]["resource_groups"]:
            group = []
            for name in names:
                if time.perf_counter()-started > max_seconds:
                    raise TimeoutError("P12 slot probe exceeded its read-only time budget")
                decoded,native_palette,_ = decode_bam((source.parent/bams[name]["canonical_bam"]).read_bytes())
                # Equivalent identity for these native BAMs: RGBA is fully determined
                # by indices/native palette/tr. Avoid rebuilding RGBA for this cost model.
                template = hashlib.sha256(context+palette_sha.encode()+native_palette.tobytes())
                resources += 1
                for index,((indices,cx,cy,tr),record) in enumerate(zip(decoded,records[name]["frame_records"],strict=True)):
                    if record["model_bypassed"]:
                        continue
                    h,w = indices.shape
                    digest = template.copy()
                    digest.update(struct.pack("<IIB",w,h,tr))
                    digest.update(indices)
                    key = digest.digest()
                    canvas = ((h+31)//32*32,(w+31)//32*32)
                    group.append((key,canvas))
                    frequency[key] += 1
                    dimensions[key] = h*w
                    baseline_frames += 1
                    baseline_pixels += canvas[0]*canvas[1]
            groups.append(group)
        components.append(groups)
    if not components:
        raise RuntimeError("no sealed P11 family runs found")

    def simulate(groups):
        seen, remaining = set(), frequency.copy()
        stats = Counter()
        retained = peak = 0
        for group in groups:
            buckets = Counter()
            for key,canvas in group:
                remaining[key] -= 1
                if key not in seen:
                    seen.add(key)
                    stats["computed_frames"] += 1
                    stats["useful_padded_pixels"] += canvas[0]*canvas[1]
                    buckets[canvas] += 1
                    if remaining[key]:
                        # RGB/guide/indices/reps plus conservative Python overhead.
                        retained += dimensions[key]*22+8192
                        peak = max(peak,retained)
                elif not remaining[key]:
                    retained -= dimensions[key]*22+8192
            for (h,w),n in buckets.items():
                slots = ((n+85)//86)*86
                stats["gpu_slots"] += slots
                stats["gpu_slot_pixels"] += slots*h*w
                stats["filler_frames"] += slots-n
        assert retained == 0
        ratio = stats["gpu_slot_pixels"]/baseline_pixels
        return {**stats,"pixel_ratio_to_p11":ratio,"estimated_peak_ready_bytes":peak,
            "gpu_only_wall_model_seconds":329.632947-236.618063*(1-ratio),
            "assumption":"unlimited retention, selected group order, linear pixel cost; excludes admission and scheduling overhead"}

    flat = [g for component in components for g in component]
    reverse = [g for component in reversed(components) for g in component]
    interleaved = [component[i] for i in range(max(map(len,components))) for component in components if i<len(component)]
    scenarios = {name:simulate(groups) for name,groups in (("component_order",flat),("reverse_components",reverse),("interleaved_groups",interleaved))}
    return {"components":len(components),"resources":resources,"groups":len(flat),
        "logical_model_frames":baseline_frames,"p11_padded_pixels":baseline_pixels,
        "unique_pixel_keys":len(frequency),"duplicate_frames":sum(n-1 for n in frequency.values()),
        "scenarios":scenarios,"seconds":time.perf_counter()-started,
        "production_runs":0,"cuda_calls":0,"temporary_files":0,
        "note":"Sensitivity scenarios, not a simulation of the three actual concurrent renderers or a measured speedup."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family",type=Path)
    parser.add_argument("--max-seconds",type=float,default=7)
    args = parser.parse_args()
    print(json.dumps(probe(args.family,args.max_seconds)))
