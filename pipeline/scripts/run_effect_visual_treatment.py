"""Derive a 30 FPS effect trial with light Gaussian RGB blur and inner alpha fade.

Reuse the animation treatment functions. Keep geometry/timing and shared empty
frames. Output RGB is premultiplied for Blended; preview it over black as RGB.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

import effect_workflow as workflow
from derive_animation_visual_treatment import (
    apply_geometry_preserving_rgb_gaussian, apply_inner_contour_fade,
)
from run_effect_interpolation import INTERPOLATION_SCHEMA, visible_frame_digest
from run_effect_spatial import file_evidence, write_json

ROOT = Path(__file__).resolve().parents[2]


def produce(resref: str, parent_run: str, run_id: str, sigma: float, feather: float,
            *, run: bool, register: bool) -> dict:
    resref, _asset, _tracking, resource = workflow.load_asset(ROOT, resref)
    parent_run = workflow.validate_run_id(parent_run)
    run_id = workflow.validate_run_id(run_id)
    parent = resource / "runs" / parent_run
    descriptor = json.loads((parent / "run.json").read_text(encoding="utf-8"))
    output = next(item for item in descriptor["outputs"] if item["role"] == "interpolation-manifest")
    source_path = ROOT / output["path"]
    source = json.loads(source_path.read_text(encoding="utf-8"))
    spatial_run = source["parent"]["spatial_run"]
    verified = workflow.verify_run_descriptor(ROOT, resource, resref, parent_run,
                                             stage="interpolation", spatial_run=spatial_run)
    if not verified["ok"]:
        raise RuntimeError("parent invalide: " + "; ".join(verified["errors"]))
    if source["schema"] != INTERPOLATION_SCHEMA or source["timing"]["target_fps"] != [30, 1]:
        raise RuntimeError("un parent d'interpolation 30 FPS est requis")
    if not 0 < sigma <= 2 or not 0 < feather <= 16:
        raise RuntimeError("flou/fondu hors du domaine léger")
    destination = resource / "runs" / run_id
    recipe_id = "gaussian-light-inner-contour-fade"
    if not run:
        return {"resref": resref, "run_id": run_id, "source_interpolation_run": parent_run,
                "sigma_x4": sigma, "inner_feather_x4": feather, "write": False}
    workflow.new_run(ROOT, resref, "interpolation", recipe_id, run_id, write=True)
    created = workflow.utc_now()
    spatial_descriptor = ROOT / source["parent"]["run_descriptor"]
    spatial_output = next(item for item in json.loads(spatial_descriptor.read_text(encoding="utf-8"))["outputs"]
                          if item["role"] == "spatial-manifest")
    spatial = json.loads((ROOT / spatial_output["path"]).read_text(encoding="utf-8"))
    canvas = tuple(v * 4 for v in spatial["aligned_canvas_size_x1"])
    inputs = [dict(spatial_output, role="parent-spatial-output"),
              file_evidence(ROOT, "source-interpolation-descriptor", parent / "run.json"),
              file_evidence(ROOT, "source-interpolation-manifest", source_path)]
    recipe = {
        "schema": "bg2-upscale-effect-visual-treatment-recipe-v1", "recipe_id": recipe_id,
        "source_interpolation_run": parent_run, "sigma_x4": sigma, "inner_feather_x4": feather,
        "blur": "coverage-normalized Gaussian; no geometry expansion",
        "fade": "inner smoothstep distance ramp; alpha_final <= alpha_source",
        "rgb_encoding": "premultiplied", "timing": "copied verbatim",
        "tools": [file_evidence(ROOT, "producer", Path(__file__)),
                  file_evidence(ROOT, "animation-treatment", ROOT / "pipeline/scripts/derive_animation_visual_treatment.py")],
    }
    write_json(destination / "recipe.json", recipe)

    def run_descriptor(status: str, sealed: bool, outputs=(), notes=None) -> dict:
        result = {"status": status, "sealed": sealed}
        if sealed: result["completed_at_utc"] = workflow.utc_now()
        if notes is not None: result["notes"] = notes
        return {
            "$schema": "docs/workspace-run.schema.json", "schema_version": 1,
            "run_id": run_id, "domain": "effects", "asset_ids": [f"effects:bam:{resref}"],
            "pipeline": {"id": workflow.STAGES["interpolation"], "version": "effect-visual-treatment.v1",
                         "recipe_path": workflow.relative_path(ROOT, destination / "recipe.json"),
                         "recipe_sha256": workflow.sha256_file(destination / "recipe.json")},
            "inputs": inputs, "outputs": list(outputs),
            "provenance": {"created_at_utc": created, "generator": workflow.relative_path(ROOT, Path(__file__)),
                           "command": ["run_effect_visual_treatment.py", "--resref", resref,
                                       "--interpolation-run", parent_run, "--run-id", run_id,
                                       "--sigma-x4", str(sigma), "--inner-feather-x4", str(feather)],
                           "parents": [spatial_run]},
            "result": result,
        }

    write_json(destination / "run.json", run_descriptor("running", False))
    stage = destination / "02-interpolation"
    (stage / "frames-rgba").mkdir(parents=True)
    transformed = {}
    stored = {}
    records = []
    visible = {}
    audit = source.get("duplicate_audit", {})
    allowed_duplicates = {tuple(pair) for pair in audit.get("native_repeat_duplicates", audit.get("native_hold_duplicates", []))}
    native_hold_duplicates = []
    empty = 0
    source_flux = target_flux = 0.0
    try:
        for frame in source["frames"]:
            record = copy.deepcopy(frame)
            key = (frame["raw_rgba_x4_sha256"], tuple(frame["physical_size_x4"]), tuple(frame["centre_x1"]))
            if key not in transformed:
                source_png = source_path.parent / frame["rgba_x4"]
                if workflow.sha256_file(source_png) != frame["rgba_x4_sha256"].upper():
                    raise RuntimeError("frame parent modifiée")
                pixels = np.asarray(Image.open(source_png).convert("RGBA"), dtype=np.uint8)
                if not np.isin(pixels[:, :, 3], [0, 255]).all():
                    raise RuntimeError("cette recette attend l'alpha binaire du run 3B/Apollo")
                blurred = apply_geometry_preserving_rgb_gaussian(pixels, sigma)
                result, _ = apply_inner_contour_fade(blurred, feather, "premultiplied")
                assert result.shape == pixels.shape
                assert np.all(result[:, :, 3] <= pixels[:, :, 3])
                assert np.all(result[:, :, :3] <= result[:, :, 3:4])
                source_flux += float(pixels[:, :, :3].sum())
                target_flux += float(result[:, :, :3].sum())
                transformed[key] = Image.fromarray(result)
            image = transformed[key]
            identity = (image.size, tuple(frame["centre_x1"]), hashlib.sha256(image.tobytes()).hexdigest())
            if identity not in stored:
                name = f"frames-rgba/frame_{frame['frame']:03d}"
                png, raw = stage / (name + ".png"), stage / (name + ".rgba")
                image.save(png, format="PNG", compress_level=9)
                raw.write_bytes(image.tobytes())
                stored[identity] = {"rgba_x4": name + ".png", "raw_rgba_x4": name + ".rgba",
                                    "rgba_x4_sha256": workflow.sha256_file(png),
                                    "raw_rgba_x4_sha256": workflow.sha256_file(raw), "bytes": raw.stat().st_size}
            record.update(stored[identity])
            record["source_interpolation_frame"] = {
                "run_id": parent_run, "frame": frame["frame"],
                "rgba": workflow.relative_path(ROOT, source_path.parent / frame["rgba_x4"]),
                "sha256": frame["rgba_x4_sha256"],
            }
            record.pop("apollo_rgb", None)
            record.pop("apollo_rgb_sha256", None)
            record["alpha_phase_source"] = "inner-feather-of-native-left-mask"
            crop = frame["runtime_crop_box_x4"]
            digest = visible_frame_digest(image, canvas, (crop[0], crop[1]))
            if digest is None: empty += 1
            elif digest in visible:
                pair = (visible[digest], frame["frame"])
                if pair not in allowed_duplicates:
                    raise RuntimeError(f"doublon lumineux sans pause native après traitement: {pair}")
                native_hold_duplicates.append(list(pair))
            else: visible[digest] = frame["frame"]
            records.append(record)
        final = copy.deepcopy(source)
        final.update({"created_utc": workflow.utc_now(), "frames": records,
                      "rgb_encoding": "premultiplied", "visual_treatment": recipe,
                      "alpha_policy": "inner smoothstep contour fade of native-left alpha",
                      "native_anchor_policy": "native phases and geometry preserved; RGB Gaussian + contour fade",
                      "duplicate_audit": {"method": "SHA-256 anchored RGBA pixels",
                                          "visible_phase_count": len(visible), "empty_phase_count": empty,
                                          "exact_visible_duplicates": native_hold_duplicates,
                                          "native_hold_duplicates": native_hold_duplicates,
                                          "native_repeat_duplicates": native_hold_duplicates,
                                          "unexpected_visible_duplicates": [], "stored_rgba_frame_count": len(stored),
                                          "unique_rgba_frame_count": len(stored), "deduplicate_outputs": True},
                      "source_interpolation": inputs[-1],
                      "brightness_change_percent": 100 * (target_flux / source_flux - 1)})
        assert final["timing"] == source["timing"]
        write_json(stage / "manifest.json", final)
        outputs = [file_evidence(ROOT, "interpolation-manifest", stage / "manifest.json")]
        write_json(destination / "run.json", run_descriptor("completed", True, outputs))
    except Exception as exc:
        write_json(destination / "run.json", run_descriptor("failed", False, notes=str(exc)))
        raise
    receipt = {"resref": resref, "run_id": run_id, "sigma_x4": sigma, "inner_feather_x4": feather,
               "duplicate_audit": final["duplicate_audit"], "brightness_change_percent": final["brightness_change_percent"]}
    if register:
        receipt["registration"] = workflow.register_run(ROOT, resref, "interpolation", run_id, write=True)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resref", required=True)
    parser.add_argument("--interpolation-run", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--sigma-x4", type=float, default=0.6)
    parser.add_argument("--inner-feather-x4", type=float, default=4.0)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--register", action="store_true")
    args = parser.parse_args()
    if args.register and not args.run: parser.error("--register exige --run")
    print(json.dumps(produce(args.resref, args.interpolation_run, args.run_id, args.sigma_x4,
                             args.inner_feather_x4, run=args.run, register=args.register),
                     ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
