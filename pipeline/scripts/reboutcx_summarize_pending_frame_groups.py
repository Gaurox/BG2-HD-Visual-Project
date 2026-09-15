"""Explain and validate a source-only frame-group inventory; no production execution."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from reboutcx_full import read_json, relative, sha256_file, semantic_classes_for_job, load_palette_profiles
from reboutcx_cache_p12 import context_key, frame_key
from run_creature_sprite_x2 import SourceFrame, decode_bam
from reboutcx_inventory_pending_frame_groups import dump_new, ROOT


def record(path, value):
    if path.exists():
        assert read_json(path) == value, f"existing research artifact differs: {path}"
    else:
        dump_new(path, value)


def run(directory):
    start = time.perf_counter()
    summary = read_json(directory / "summary.json")
    for filename, evidence in summary["artifacts"].items():
        assert sha256_file(directory / filename) == evidence["sha256"]
    inventory = read_json(directory / "source-inventory.json")
    families, components, resources = (inventory[k] for k in ("families", "components", "resources"))
    primary = {i for i, f in enumerate(families) if f["in_original_76"]}
    resource_layers = {r["id"]: {components[c]["layer"] for c, _ in r["canonical_consumers"]
                                 if components[c]["family_index"] in primary} for r in resources}
    cohort_details = defaultdict(lambda: {"layers": Counter(), "example": None})
    work = {i: {"animation_id": families[i]["animation_id"], "family": families[i]["family"],
                "unique_model_frames_in_family": families[i]["unique_model_frames"],
                "new_model_frames": 0, "reused_from_earlier_families": 0,
                "new_q32_pixels": 0} for i in primary}
    totals = Counter()
    samples = []
    with gzip.open(directory / "frame-groups.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            group = json.loads(line)
            selected = sorted(set(group["families"]) & primary)
            assert selected
            w, h = group["size"]
            assert group["representative"] in group["references"]
            union = set()
            occurrences = 0
            layers = set()
            for rid, index in group["references"]:
                resource = resources[rid]
                assert 0 <= index < resource["frame_count"]
                owners = resource["canonical_consumers"]
                union.update(components[c]["family_index"] for c, _ in owners)
                occurrences += len(owners)
                layers.update(resource_layers[rid])
            assert union == set(group["families"])
            assert occurrences == group["logical_occurrences"]
            totals["groups"] += 1
            if group["model"]:
                padded = ((w+31)//32*32)*((h+31)//32*32)
                totals.update(unique_model_frames=1, family_unique_model_frames=len(selected),
                              unique_model_q32_pixels=padded,
                              additional_model_frames_avoided=len(selected)-1)
                work[selected[0]]["new_model_frames"] += 1
                work[selected[0]]["new_q32_pixels"] += padded
                for fid in selected[1:]:
                    work[fid]["reused_from_earlier_families"] += 1
            if len(selected) > 1:
                details = cohort_details[tuple(selected)]
                details["layers"]["+".join(sorted(layers))] += int(group["model"])
                if details["example"] is None:
                    details["example"] = group
                if len(samples) < 12 and len(group["references"]) > 1 and group["model"]:
                    samples.append(group)
    expected = summary["scopes"]["pending_in_76"]
    for k, count in totals.items():
        assert count == (summary["pixel_groups"] if k == "groups" else expected[k]), k
    for item in work.values():
        assert item["new_model_frames"]+item["reused_from_earlier_families"] == item["unique_model_frames_in_family"]
    artifact_check_seconds = time.perf_counter()-start

    # Independently reconstruct two native SourceFrames for twelve recorded identities.
    decoded_cache, context_cache = {}, {}
    def reconstruct(reference):
        rid, index = reference
        r = resources[rid]
        if rid not in decoded_cache:
            decoded_cache[rid] = decode_bam((ROOT / r["sample_bam"]).read_bytes())
        decoded, palette, _ = decoded_cache[rid]
        indices, cx, cy, tr = decoded[index]
        h, w = indices.shape
        rgba = np.empty((h, w, 4), np.uint8)
        rgba[:, :, :3] = palette[indices]
        rgba[:, :, 3] = np.where(indices == tr, 0, 255).astype(np.uint8)
        template_sha = r["template_sha256"]
        if template_sha not in context_cache:
            spec = inventory["contexts"][template_sha]
            template = read_json(ROOT / spec["template"])
            classes, _ = semantic_classes_for_job(template)
            profiles, _ = load_palette_profiles(template)
            context_cache[template_sha] = (context_key(template, classes, spec["scalepix_sha256"]), profiles[0]["palette"])
        context, reference_palette = context_cache[template_sha]
        frame = SourceFrame("check", index, w, h, cx, cy, tr, indices, palette, rgba.tobytes())
        return frame, frame_key(frame, reference_palette, context).hex()
    for group in samples:
        a, ka = reconstruct(group["references"][0])
        b, kb = reconstruct(group["references"][-1])
        assert ka == kb == group["key"]
        assert (a.width, a.height, a.transparent) == (b.width, b.height, b.transparent)
        assert np.array_equal(a.indices, b.indices) and np.array_equal(a.palette, b.palette) and a.rgba == b.rgba
    pixel_check_seconds = time.perf_counter()-start-artifact_check_seconds

    component_sets = defaultdict(list)
    for c in components:
        if c["family_index"] in primary:
            signature = tuple(sorted(r["resource_id"] for r in c["resources"] if r["resref"] == r["canonical_resref"]))
            component_sets[signature].append(c["id"])
    component_groups = []
    for signature, members in component_sets.items():
        fids = sorted({components[c]["family_index"] for c in members})
        if len(fids) > 1:
            component_groups.append({"animation_ids": [families[i]["animation_id"] for i in fids],
                "component_ids": members, "prefixes": sorted({components[c]["prefix"] for c in members}),
                "layers": sorted({components[c]["layer"] for c in members}), "resource_ids": list(signature)})
    component_groups.sort(key=lambda r: (-len(r["animation_ids"]), r["prefixes"]))
    cohorts = read_json(directory / "sharing-cohorts.json")
    for cohort in cohorts:
        if cohort["scope"] == "pending_in_76":
            details = cohort_details[tuple(cohort["family_indices"])]
            cohort["model_groups_by_layer_combination"] = dict(details["layers"])
            cohort["example_group"] = details["example"]
    record(directory / "group-details.json", {"sharing_cohorts": cohorts, "whole_component_source_groups": component_groups})
    record(directory / "family-work-plan.json", {"scope": "pending_in_76", "order": "ascending animation ID",
        "note": "Analytical assignment only; no executable production queue. Representative pixels may be read from any group member.",
        "families": [work[i] for i in sorted(work)]})

    # Fit to the eight completed P12 families with no interrupted/resumed execution.
    prior_path = ROOT / "docs/measurements/reboutcx-p12-next10-20260915-v1/production-report.json"
    prior = read_json(prior_path)
    calibration, individual, manifest_hashes = Counter(), [], {}
    for f in prior["families"]:
        if len(f["attempts"]) != 1:
            continue
        row = Counter()
        for path in (ROOT / f["family"]).glob("*/runs/reboutcx-p12-cache86-v1/manifest.json"):
            manifest_hashes[relative(path)] = sha256_file(path)
            m = read_json(path)
            for k in ("model_cuda_seconds", "dispatch_wall_seconds", "padded_model_pixels", "gpu_slot_pixels"):
                row[k] += m["timing_seconds"].get(k, 0)
        row.update(wall_seconds=f["wall_through_verification_seconds"], source_frames=f["source_frames"])
        individual.append({"animation_id": f["animation_id"], **row})
        calibration.update(row)
    active_rate = calibration["dispatch_wall_seconds"]/calibration["padded_model_pixels"]
    model_rate = calibration["model_cuda_seconds"]/calibration["padded_model_pixels"]
    residual_rate = (calibration["wall_seconds"]-calibration["dispatch_wall_seconds"])/calibration["source_frames"]
    projections = {}
    for name, scope in summary["scopes"].items():
        baseline = active_rate*scope["family_unique_model_q32_pixels"]+residual_rate*scope["source_frames"]
        model_saved = model_rate*scope["additional_q32_pixels_avoided"]
        dispatch_saved = active_rate*scope["additional_q32_pixels_avoided"]
        projections[name] = {"baseline_seconds": baseline,
            "projected_seconds_dispatch_scenario": baseline-dispatch_saved,
            "projected_seconds_model_only_scenario": baseline-model_saved,
            "saved_seconds_model_only_scenario": model_saved,
            "saved_seconds_dispatch_scenario": dispatch_saved,
            "dense_payload_gib": scope["shared_dense_payload_bytes"]/1024**3,
            "sequential_boundary_peak_gib": scope["sequential_family_boundary_payload_peak_bytes"]/1024**3}
    dump_new(directory / "work-estimate.json", {"status": "conditional-projection-not-measured-speedup",
        "calibration_report": relative(prior_path), "calibration_report_sha256": sha256_file(prior_path),
        "calibration_families": individual, "calibration_manifest_hashes": manifest_hashes,
        "calibration_totals": dict(calibration), "active_seconds_per_q32_pixel": active_rate,
        "cuda_seconds_per_q32_pixel": model_rate, "residual_seconds_per_source_frame": residual_rate,
        "formulas": {"baseline": "active_rate * family_unique_q32_pixels + residual_rate * source_frames",
                     "saved_range": "[cuda_rate, active_rate] * additional_q32_pixels_avoided"},
        "projections": projections,
        "assumptions": ["GPU cost and filler ratio extrapolated from eight LOW-family P12 measurements.",
                        "Residual outside GPU worker kept unchanged; does not measure CPU critical-path changes.",
                        "New cache planning, serialization, disk/RAM overhead and Windows retries excluded.",
                        "No GPU model or production test run; no cache capacity guarantee."]})
    validation = {"status": "passed", "source_analysis_sha256": sha256_file(directory / "summary.json"),
        "script": relative(Path(__file__)), "script_sha256": sha256_file(Path(__file__)),
        "all_groups_and_references_checked": summary["pixel_groups"], "counts": totals,
        "artifact_check_seconds": artifact_check_seconds, "native_pixel_pairs_checked": len(samples),
        "native_pixel_check_seconds": pixel_check_seconds, "group_keys_sample": [g["key"] for g in samples],
        "whole_component_groups": len(component_groups), "total_seconds": time.perf_counter()-start}
    dump_new(directory / "validation.json", validation)
    print(json.dumps({"validation": validation, "projections": projections}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    run(parser.parse_args().directory)
