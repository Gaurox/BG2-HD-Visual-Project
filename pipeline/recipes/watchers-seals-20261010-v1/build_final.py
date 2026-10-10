"""AM3019A/AM3020D/AM3022D: immutable per-area QA packs, no installation.

Inputs: Rebout/SeedVR -> Apollo runs already completed; AM3022D spline8 run.
WED masks: stock covers 67/69 and 11, world-space x4, supersample4,
4px fade on visible side. RGB: AM3019A premultiplied once; others straight.
"""
from pathlib import Path
import json
import hashlib
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import run_animation_upscale_30fps_v2 as v2
import split_animation_pack_by_area as split
import build_blended_rgb_neutral_pack as neutral
import merge_area_pack_resources as merge
import combine_area_pack_splits as combine
from export_bam_frames import read_bam
from bam_export import decode_bam
from bg2lib import load_key, resolve_resource

TAG = "watchers-seals-trois-animations-20261010-v1"
PACKS = ROOT / "animations/packs-par-zone"
JOBS = [
    ("AM3019A", "AR3019", (2277, 1802), [67, 69],
     "am3019a-reboutcx-apo8-holds-20261010-v1", "ReboutCX x4", 8, "premultiply"),
    ("AM3020D", "AR3020", (604, 771), [11],
     "am3020d-seedvr-apo8-holds-20261010-v1", "SeedVR2 7B INT8/LAB x4 seed3020", 0, "zero"),
    ("AM3022D", "AR3022", (1550, 1690), [],
     "am3022d-reboutcx-apo8-splinefit1-feather8-20261010-v1", "ReboutCX x4", 8, "preserve"),
]


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def artifact(path):
    return {"path": rel(path), "sha256": v2.sha256_file(path)}


def world_mask(ref, area, position, indexes):
    bifs, entries = load_key()
    entry = next(e for e in entries if e[0].upper() == area and e[1] == 0x3E9)
    data, bif = resolve_resource(bifs, entry[2])
    secondary = struct.unpack_from("<I", data, 0x14)[0]
    count, polygons_offset, vertices_offset = struct.unpack_from("<III", data, secondary)
    polygons = []
    for index in indexes:
        assert index < count
        start, n, flags, height, *_ = struct.unpack_from("<IIBBHHHH", data, polygons_offset + index * 18)
        assert flags & 8 and n >= 3
        vertices = [struct.unpack_from("<HH", data, vertices_offset + 4 * (start + k)) for k in range(n)]
        polygons.append({"index": index, "flags": hex(flags), "vertices": vertices})
    frames, _, _ = decode_bam(read_bam(ROOT / f"animations/ressources/{ref}/source.bam"))
    x, y = position
    left = min(x - cx for idx, cx, cy, tr in frames) - 8
    top = min(y - cy for idx, cx, cy, tr in frames) - 8
    right = max(x - cx + idx.shape[1] for idx, cx, cy, tr in frames) + 8
    bottom = max(y - cy + idx.shape[0] for idx, cx, cy, tr in frames) + 8
    width, height = (right - left) * 4, (bottom - top) * 4
    raster = Image.new("L", (width * 4, height * 4))
    draw = ImageDraw.Draw(raster)
    for polygon in polygons:
        draw.polygon([((vx - left) * 16, (vy - top) * 16) for vx, vy in polygon["vertices"]], fill=255)
    covered = np.asarray(raster) > 0
    distance = distance_transform_edt(~covered) / 4
    t = np.clip(distance / 4, 0, 1)
    keep = np.rint(255 * t * t * (3 - 2 * t)).astype(np.uint8)
    mask = Image.fromarray(keep).resize((width, height), Image.Resampling.BOX)
    directory = ROOT / f"animations/masques-occlusion/{ref}/{TAG}"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{area}-{x}-{y}-wed-aa4.png"
    if path.with_suffix(".json").exists():
        info = v2.load_json(path.with_suffix(".json"))
        assert v2.sha256_file(path) == info["mask_sha256"]
        assert info["wed_sha256"] == hashlib.sha256(data).hexdigest()
        return path, info
    mask.save(path)
    info = {"schema": "bg2-upscale-animation-world-occlusion-mask-v1", "status": "completed",
            "resref": ref, "area": area, "position_x1": list(position),
            "origin_x4": [left * 4, top * 4], "size_x4": [width, height],
            "mask": rel(path), "mask_sha256": v2.sha256_file(path),
            "encoding": "flattened-white-keeps-black-removes", "wed_sha256": hashlib.sha256(data).hexdigest(),
            "wed_source": bif, "polygons": polygons, "antialias_supersample": 4,
            "visible_side_feather_x4": 4}
    v2.write_json(path.with_suffix(".json"), info)
    return path, info


def main():
    complete = PACKS / (TAG + "-complete-v2")
    selected_roots = []
    batch = {"schema": "bg2-upscale-animation-batch-production-v1", "status": "completed",
             "created_utc": v2.utc_now(), "areas": [], "resources": [],
             "qa_status": "pending-ingame", "release_status": "not-selected"}
    for ref, area, position, indexes, run_id, spatial, radius, mode in JOBS:
        run = ROOT / f"animations/ressources/{ref}/runs/{run_id}"
        source_split = PACKS / (ref.lower() + "-watchers-source-20261010-v1")
        split.split(run / "03_runtime_pack", source_split, ROOT / "animations/index/occurrences.csv", source_split.exists())
        masks = []
        if indexes:
            path, info = world_mask(ref, area, position, indexes)
            treated = PACKS / (ref.lower() + "-watchers-final-20261010-v1")
            neutral.build(source_split, treated, {ref}, treated.exists(), mode, None, radius,
                          neutral.load_occlusion_mask(path), tuple(info["origin_x4"]), position, path)
            masks = [{"metadata": rel(path.with_suffix(".json")),
                      "metadata_sha256": v2.sha256_file(path.with_suffix(".json")),
                      "mask": rel(path), "mask_sha256": info["mask_sha256"],
                      "origin_x4": info["origin_x4"], "position_x1": list(position)}]
        else:
            treated = source_split
        leaf = treated / area
        # Select just this asset: authoring runs can also contain untimed donor resources.
        selected = PACKS / (TAG + "-selected-" + area)
        merge.merge([str(leaf) + "::" + ref], area, selected, selected.exists())
        selected_roots.append(selected)
        final = selected / area
        manifest, resources = v2.validate_v2_pack(final)
        resource = next(r for r in resources if r["resref"] == ref)
        assert len(resources) == 1
        cycles = [{"cycle": c["cycle"], "phases": len(c["timeline_frame_indices"]),
                   "duration_seconds": len(c["timeline_frame_indices"]) / 30} for c in resource["cycles"]]
        wrapper = ROOT / f"animations/ressources/{ref}/runs/{ref.lower()}-watchers-final-20261010-v1"
        wrapper.mkdir(parents=True, exist_ok=False)
        recipe = {"spatial": spatial, "temporal": "Apollo8 15->30; native cycles/holds; aligned inputs",
                  "inner_feather_x4": radius, "rgb_policy": mode,
                  "alpha": "Spline Fit1 multi-contours feather8" if ref == "AM3022D" else "native nearest; local WED AA4 fade4",
                  "wed_polygons": indexes}
        contract = {"registry_version": 3, "frame_count": resource["frame_count"], "fps": 30,
                    "native_geometry_preserved": True, "cycles": cycles}
        record = {"schema": "bg2-upscale-animation-visual-treatment-v1", "status": "completed",
                  "created_utc": v2.utc_now(), "resref": ref, "resrefs": [ref],
                  "source_run": rel(run), "source_run_manifest_sha256": v2.sha256_file(run / "manifest.json"),
                  "source_pack": rel(leaf), "source_pack_manifest_sha256": v2.sha256_file(leaf / "manifest.json"),
                  "recipe": recipe, "occlusion_masks": masks, "runtime_contract": contract,
                  "qa_status": "pending-ingame", "release_status": "not-selected"}
        v2.write_json(wrapper / "manifest.json", record)
        batch["areas"].append(area)
        batch["resources"].append({"resref": ref, "areas": [area],
                                  "source": artifact(ROOT / f"animations/ressources/{ref}/source.bam"),
                                  "production": artifact(wrapper / "manifest.json"),
                                  "runtime_frames": resource["frame_count"], "cycles": cycles,
                                  "recipe": recipe, "occlusion_masks": masks})
        print(json.dumps({"resref": ref, "pack": rel(final), "cycles": cycles}), flush=True)
    combine.combine(selected_roots, complete, False)
    batch["complete_pack"] = artifact(complete / "manifest.json")
    for entry in batch["resources"]:
        path = ROOT / entry["production"]["path"]
        record = v2.load_json(path)
        record["output_split_root"] = rel(complete)
        record["output_manifest_sha256"] = batch["complete_pack"]["sha256"]
        v2.write_json(path, record)
        entry["production"] = artifact(path)
    batch["recipe_script"] = artifact(Path(__file__))
    directory = ROOT / "animations/batches" / TAG
    directory.mkdir(exist_ok=False)
    v2.write_json(directory / "manifest.json", batch)


if __name__ == "__main__":
    main()
