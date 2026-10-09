"""AM5500D: validated contour-aura body recipe + measured detached-ember guard.

Working production recipe; native geometry/timeline unchanged. Small components
<=128 x4 pixels retain their peak with feather1/aura1/border1, instead of the
body's feather24/aura5/border14. RGB stays premultiplied exactly once.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import build_animation_contour_aura_pack as aura

SOURCE = ROOT / "animations/packs-par-zone/am5500d-reboutcx-apo8-x4-30fps-20261009-v1"
OUTPUT = ROOT / "animations/packs-par-zone/am5500d-reboutcx-apo8-aura24-sparkguard1-20261009-v1"
GUARD = {
    "max_component_pixels_x4": 128,
    "connectivity": 4,
    "inner_feather_x4": 1,
    "aura_sigma_x4": 1,
    "aura_gain": 0.9,
    "border_margin_x4": 1,
    "composition": "max-premultiplied-rgb-and-alpha",
}
transform_body = aura.transform_pixels
transform_area_original = aura.transform_area
reports = []


def transform_guard(raw, width, height, **parameters):
    body_bytes, stats = transform_body(raw, width, height, **parameters)
    source = np.frombuffer(raw, np.uint8).reshape(height, width, 4)
    components, count = label(source[..., 3] > 0)
    sizes = np.bincount(components.ravel())
    ids = [i for i in range(1, count + 1) if sizes[i] <= GUARD["max_component_pixels_x4"]]
    small = np.isin(components, ids)
    body = np.frombuffer(body_bytes, np.uint8).reshape(source.shape).copy()
    peak_ratios = []
    if small.any():
        ember_source = source.copy()
        ember_source[~small, 3] = 0
        guarded_bytes, _ = transform_body(
            ember_source.tobytes(), width, height,
            inner_feather_x4=GUARD["inner_feather_x4"],
            aura_sigma_x4=GUARD["aura_sigma_x4"],
            aura_gain=GUARD["aura_gain"],
            border_margin_x4=GUARD["border_margin_x4"],
        )
        guarded = np.frombuffer(guarded_bytes, np.uint8).reshape(source.shape)
        body = np.maximum(body, guarded)
        source_luma = source[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
        output_luma = body[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
        for i in ids:
            mask = components == i
            peak = source_luma[mask].max()
            if peak > 1:
                peak_ratios.append(float(output_luma[mask].max() / peak))
    assert np.all(body[..., :3] <= body[..., 3, None]), "premultiplied RGB contract"
    reports.append({"frame": len(reports), "components": len(ids), "peak_ratios": peak_ratios})
    stats["final_alpha_nonzero_pixels"] = int((body[..., 3] > 0).sum())
    stats["aura_expanded_pixels"] = int(((body[..., 3] > 0) & (source[..., 3] == 0)).sum())
    stats["aura_rgb_dilated_pixels"] = stats["aura_expanded_pixels"]
    return body.tobytes(), stats


def transform_area_guard(*args, **kwargs):
    manifest, stats = transform_area_original(*args, **kwargs)
    manifest["contour_aura"]["small_component_guard"] = GUARD
    return manifest, stats


def main():
    partial = OUTPUT.with_name(OUTPUT.name + ".partial")
    assert OUTPUT.is_relative_to(ROOT) and partial.is_relative_to(ROOT)
    assert not OUTPUT.exists() and not partial.exists(), "immutable destination already exists"
    aura.transform_pixels = transform_guard
    aura.transform_area = transform_area_guard
    result = aura.build(
        SOURCE, partial, {"AM5500D"}, inner_feather_x4=24,
        aura_sigma_x4=5, aura_gain=0.9, border_margin_x4=14, resume=False,
    )
    ratios = [ratio for frame in reports for ratio in frame["peak_ratios"]]
    report = {
        "schema": "bg2-upscale-animation-small-component-guard-v1",
        "resref": "AM5500D", "parameters": GUARD, "frames": reports,
        "guarded_components": len(ratios),
        "min_peak_ratio": min(ratios), "mean_peak_ratio": float(np.mean(ratios)),
        "recipe_script": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "recipe_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    aura.v2.write_json(partial / "spark-guard-report.json", report)
    result["contour_aura"]["small_component_guard"] = GUARD
    result["small_component_guard_report"] = "spark-guard-report.json"
    result["small_component_guard_report_sha256"] = aura.v2.sha256_file(partial / "spark-guard-report.json")
    aura.v2.write_json(partial / "manifest.json", result)
    aura.v2.validate_v2_pack(partial / "AR5500")
    partial.rename(OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "frames": len(reports),
                      "guarded_components": len(ratios),
                      "min_peak_ratio": min(ratios), "mean_peak_ratio": float(np.mean(ratios))}))


if __name__ == "__main__":
    main()
