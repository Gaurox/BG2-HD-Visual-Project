"""FPIT1L: bake two world masks into already-premultiplied Aura12 outputs.

Multiply RGBA by coverage once; never premultiply RGB by alpha a second time.
Native geometry, timelines and source packs remain unchanged.
"""
from pathlib import Path
import json
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import run_animation_upscale_30fps_v2 as v2
import build_blended_rgb_neutral_pack as neutral
from derive_area_animation_pack import rebuild_manifest
import split_animation_pack_by_area as splitter

SOURCE = ROOT / "animations/packs-par-zone/fpit1l-reboutcx-apo8-aura12-sparkguard1-20261010-v1/AR5203"


def main():
    v2.validate_v2_pack(SOURCE)
    for x, y in [(597, 1762), (552, 1702)]:
        mask_path = ROOT / f"animations/masques-occlusion/FPIT1L/mir-camps-20261010-v1/AR5203-{x}-{y}-wed-aa4.png"
        info = v2.load_json(mask_path.with_suffix(".json"))
        assert v2.sha256_file(mask_path) == info["mask_sha256"]
        mask = neutral.load_occlusion_mask(mask_path)
        output = ROOT / f"animations/packs-par-zone/fpit1l-aura12-sparkguard1-wed83-{x}-{y}-20261010-v1"
        assert not output.exists(), output
        leaf = output / "AR5203"
        shutil.copytree(SOURCE, leaf)
        shutil.copyfile(mask_path, output / "occlusion-mask.png")
        manifest = v2.load_json(leaf / "manifest.json")
        for resource in manifest["resources"]:
            assert resource["resref"] == "FPIT1L"
            resource["position"] = [x, y]
            assets = {a["name"]: a for a in resource["assets"]}
            for frame in resource["frames"]:
                w, h = frame["physical_size_x4"]
                path = leaf / frame["asset"]
                pixels = np.frombuffer(path.read_bytes(), np.uint8).reshape(h, w, 4).copy()
                assert np.all(pixels[..., :3] <= pixels[..., 3, None])
                cx, cy = frame["centre_x1"]
                occluded = neutral.frame_occlusion(mask, tuple(info["origin_x4"]), ((x-cx)*4, (y-cy)*4), w, h)
                pixels = np.rint(pixels.astype(float) * (1-occluded)[..., None]).astype(np.uint8)
                assert np.all(pixels[..., :3] <= pixels[..., 3, None])
                path.write_bytes(pixels.tobytes())
                frame["sha256"] = v2.sha256_file(path)
                assets[frame["asset"]]["sha256"] = frame["sha256"]
        manifest["derived_from"] = {"pack": str(SOURCE.relative_to(ROOT)).replace("\\", "/"), "manifest_sha256": v2.sha256_file(SOURCE / "manifest.json")}
        record = neutral.occlusion_mask_record("../occlusion-mask.png", v2.sha256_file(mask_path), tuple(info["origin_x4"]), (x, y))
        manifest["premultiplied_occlusion"] = {"operation": "RGBA *= world coverage; no second premultiplication", "occlusion_mask": record, "geometry": info}
        rebuild_manifest(leaf, manifest)
        v2.validate_v2_pack(leaf)
        index = {"schema": splitter.INDEX_SCHEMA, "status": "completed", "created_utc": v2.utc_now(), "source_pack": str(SOURCE.relative_to(ROOT)).replace("\\", "/"), "source_pack_manifest_sha256": v2.sha256_file(SOURCE / "manifest.json"), "area_count": 1, "runtime_budget_bytes": v2.MAX_RAW_BYTES, "largest_area_raw_bytes": manifest["raw_bytes"], "total_raw_bytes": manifest["raw_bytes"], "areas_over_budget": [], "resrefs_without_area": [], "areas": [{"area_id": "AR5203", "directory": "AR5203", "resrefs": ["FPIT1L"], "resource_count": 1, "frame_count": manifest["frame_count"], "raw_bytes": manifest["raw_bytes"], "registry_sha256": manifest["registry_sha256"], "manifest_sha256": v2.sha256_file(leaf / "manifest.json"), "over_runtime_budget": False}], "premultiplied_occlusion": manifest["premultiplied_occlusion"]}
        v2.write_json(output / "manifest.json", index)
        print(json.dumps({"output": str(output), "position": [x, y]}))


if __name__ == "__main__":
    main()
