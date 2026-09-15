"""Inventory pending-family P12 pixel identities; CPU/source reads and research files only.

No production jobs, model inference, sprite output, derived catalogue or installation.
The optional two legacy families use the common pinned contract as an explicit projection.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from reboutcx_full import (read_json, relative, resolve_path_reference, sha256_file,
                          semantic_classes_for_job, load_palette_profiles, is_null_frame)
from reboutcx_cache_p12 import context_key, frame_key, PIXEL_CONTRACT
from reboutcx_character_family import load_template, member_layer
from run_creature_sprite_x2 import SourceFrame, decode_bam

ROOT = Path(__file__).resolve().parents[2]
PROGRESS = ROOT / "sprite/catalogs/creature-x2-reboutcx/jobs/playable-characters-reboutcx-progress-p12-v1.json"


def dump_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def bits(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


def run(destination):
    start = time.perf_counter()
    destination = destination.resolve()
    destination.relative_to(ROOT / "docs/measurements")
    destination.mkdir(parents=True, exist_ok=False)
    progress = read_json(PROGRESS)
    catalog_path = ROOT / progress["xbr_source_catalog"]
    assert sha256_file(catalog_path) == progress["xbr_source_catalog_sha256"]
    original_ids = {read_json(ROOT / p)["animation"]["id"] for p in read_json(catalog_path)["members"]
                    if p.startswith("sprite/families/playable-characters/")}
    assert len(original_ids) == 76
    pending = progress["pending_animation_ids"]
    families, components, resources, contexts = [], [], [], {}
    resource_ids, checked_payloads, pinned = {}, set(), {}
    common_template = None

    def pin(path, expected=None):
        digest = sha256_file(path)
        if expected is not None:
            assert digest == expected, relative(path)
        pinned[relative(path)] = digest
        return digest

    pin(PROGRESS)
    pin(catalog_path)
    scripts = [Path(__file__), *[ROOT / "pipeline/scripts" / name for name in (
        "reboutcx_cache_p12.py", "reboutcx_plan_p12.py", "reboutcx_full_p12.py",
        "reboutcx_runtime_p12.py", "reboutcx_runtime_p10.py", "reboutcx_batch.py",
        "reboutcx_quantize.py", "run_creature_sprite_x2.py", "reboutcx_character_family.py")]]
    for script in scripts:
        pin(script)
    for fid, aid in enumerate(pending):
        root = next((ROOT / "sprite/families/playable-characters").glob(aid[2:].lower() + "-*"))
        assert not list(root.glob("*/runs/reboutcx*/manifest.json")), f"existing pending output: {aid}"
        source_path = next(root.glob("family-runs/complete-xn-xbr2x/jobs/*.json"))
        source = read_json(source_path)
        family_jobs = list(root.glob("family-runs/complete-reboutcx-p8-v1/jobs/*.json"))
        if family_jobs:
            assert len(family_jobs) == 1
            family_job = read_json(family_jobs[0])
            pin(family_jobs[0])
            pin(source_path, family_job["source_family_job_sha256"])
            template_path, template = load_template(family_job)
            if common_template is None:
                common_template = (template_path, template)
            projected = False
        else:
            assert aid in ("0x6102", "0x6110") and common_template is not None
            template_path, template = common_template
            pin(source_path)
            projected = True
        pin(template_path)
        template_sha = sha256_file(template_path)
        if template_sha not in contexts:
            classes, _ = semantic_classes_for_job(template)
            profiles, _ = load_palette_profiles(template)
            palette = profiles[0]["palette"] if profiles else None
            tool = resolve_path_reference(template["paths"]["scalepix"], required=True)
            context = context_key(template, classes, sha256_file(tool))
            contexts[template_sha] = {"template": relative(template_path), "classes": classes,
                "context": context, "palette": palette, "marker": int(template["null_frame_marker"]),
                "scalepix_sha256": sha256_file(tool)}
        ctx = contexts[template_sha]
        palette_sha = hashlib.sha256(ctx["palette"].tobytes()).hexdigest() if ctx["palette"] is not None else "native"
        family = {"animation_id": aid, "family": relative(root), "in_original_76": aid in original_ids,
                  "source_job": relative(source_path), "template_sha256": template_sha,
                  "projected_common_contract": projected, "components": len(source["members"]),
                  "source_frames": 0, "source_resources": 0, "canonical_resources": 0,
                  "logical_model_frames": 0, "logical_q32_pixels": 0,
                  "unique_model_frames": 0, "unique_q32_pixels": 0,
                  "null_canonical_frames": 0, "transparent_canonical_frames": 0}
        families.append(family)
        for member_reference in source["members"]:
            member_path = ROOT / member_reference
            member = read_json(member_path)
            assert member["animation"]["id"] == aid
            pin(member_path)
            manifest_path = resolve_path_reference(member["paths"]["source_dir"]) / "manifest.json"
            manifest = read_json(manifest_path)
            pin(manifest_path)
            assert manifest["animation_id"] == aid and manifest["runtime_profile"] == "character-bg2ee-2.7.3.0"
            component = {"id": len(components), "family_index": fid,
                "prefix": manifest["bam_prefix"], "layer": member_layer(member)[0],
                "source_job": member_reference, "source_manifest": relative(manifest_path), "resources": []}
            components.append(component)
            seen = {}
            assert sum(b["frame_count"] for b in manifest["bams"]) == manifest["total_frames"]
            family["source_frames"] += manifest["total_frames"]
            for bam in manifest["bams"]:
                canonical_path = manifest_path.parent / bam["canonical_bam"]
                source_bam = manifest_path.parent / bam["source"]
                for path, expected in ((canonical_path, bam["canonical_bam_sha256"]), (source_bam, bam["source_sha256"])):
                    if path not in checked_payloads:
                        assert sha256_file(path) == expected, relative(path)
                        checked_payloads.add(path)
                # Whole-resource clones are already bypassed inside each P12 component.
                original_identity = (bam["canonical_bam_sha256"], bam["source_sha256"])
                canonical_resref = seen.setdefault(original_identity, bam["name"])
                eligible = canonical_resref == bam["name"]
                identity = (ctx["context"].hex(), palette_sha, bam["canonical_bam_sha256"])
                rid = resource_ids.get(identity)
                if rid is None:
                    rid = len(resources)
                    resource_ids[identity] = rid
                    resources.append({"id": rid, "sample_bam": relative(canonical_path),
                        "canonical_bam_sha256": bam["canonical_bam_sha256"], "template_sha256": template_sha,
                        "context_sha256": ctx["context"].hex(), "reference_palette_sha256": palette_sha,
                        "frame_count": bam["frame_count"], "canonical_consumers": []})
                assert resources[rid]["frame_count"] == bam["frame_count"]
                component["resources"].append({"resref": bam["name"], "resource_id": rid,
                    "canonical_resref": canonical_resref})
                if eligible:
                    resources[rid]["canonical_consumers"].append([component["id"], bam["name"]])
                family["source_resources"] += 1
                family["canonical_resources"] += eligible
        print(json.dumps({"phase": "sources", "family": aid, "families": fid+1,
                          "resource_templates": len(resources), "seconds": time.perf_counter()-start}), flush=True)
    metadata_seconds = time.perf_counter() - start

    # key -> [width,height,needs_model,family_mask,logical_occurrences,resource/frame references]
    groups = {}
    for resource in resources:
        rid = resource["id"]
        owners = Counter(components[c]["family_index"] for c, _ in resource["canonical_consumers"])
        mask = sum(1 << f for f in owners)
        ctx = contexts[resource["template_sha256"]]
        decoded, native_palette, _ = decode_bam((ROOT / resource["sample_bam"]).read_bytes())
        assert len(decoded) == resource["frame_count"]
        model_frames = null_frames = transparent_frames = q32_pixels = 0
        for index, (indices, cx, cy, tr) in enumerate(decoded):
            h, w = indices.shape
            assert 1 <= w <= 4096 and 1 <= h <= 4096
            rgba = np.empty((h, w, 4), dtype=np.uint8)
            rgba[:, :, :3] = native_palette[indices]
            rgba[:, :, 3] = np.where(indices == tr, 0, 255).astype(np.uint8)
            frame = SourceFrame("inventory", index, w, h, cx, cy, tr, indices, native_palette, rgba.tobytes())
            if is_null_frame(frame, ctx["marker"]):
                null_frames += 1
                continue
            needs_model = bool(np.any(indices != tr))
            model_frames += needs_model
            transparent_frames += not needs_model
            q32_pixels += ((w+31)//32*32)*((h+31)//32*32)*needs_model
            key = frame_key(frame, ctx["palette"], ctx["context"])
            if key not in groups:
                groups[key] = [w, h, needs_model, 0, 0, []]
            group = groups[key]
            assert group[:3] == [w, h, needs_model]
            group[3] |= mask
            group[4] += sum(owners.values())
            group[5].append([rid, index])
        resource.update(model_frames=model_frames, null_frames=null_frames,
                        transparent_frames=transparent_frames, q32_pixels=q32_pixels)
        for fid, count in owners.items():
            families[fid]["logical_model_frames"] += count*model_frames
            families[fid]["logical_q32_pixels"] += count*q32_pixels
            families[fid]["null_canonical_frames"] += count*null_frames
            families[fid]["transparent_canonical_frames"] += count*transparent_frames
        if (rid+1) % 200 == 0 or rid+1 == len(resources):
            print(json.dumps({"phase": "frame-keys", "resources": rid+1, "total": len(resources),
                              "groups": len(groups), "seconds": time.perf_counter()-start}), flush=True)
    scan_seconds = time.perf_counter() - start - metadata_seconds
    primary_mask = sum(1 << i for i, f in enumerate(families) if f["in_original_76"])
    all_mask = (1 << len(families))-1
    cohorts = defaultdict(Counter)
    scope_totals = {"pending_in_76": Counter(), "all_pending_78": Counter()}
    memory_events = {name: Counter() for name in scope_totals}
    group_file = destination / "frame-groups.jsonl.gz"
    with group_file.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as stream:
        for key, (w, h, model, mask, occurrences, references) in sorted(groups.items()):
            native, padded = w*h, ((w+31)//32*32)*((h+31)//32*32)
            for fid in bits(mask):
                families[fid]["unique_model_frames"] += model
                families[fid]["unique_q32_pixels"] += model*padded
            for name, selection in (("pending_in_76", primary_mask), ("all_pending_78", all_mask)):
                selected = mask & selection
                n = selected.bit_count()
                if not n:
                    continue
                totals = scope_totals[name]
                totals["unique_cache_frames"] += 1
                totals["unique_model_frames"] += model
                totals["unique_model_native_pixels"] += model*native
                totals["unique_model_q32_pixels"] += model*padded
                totals["family_unique_model_frames"] += model*n
                totals["family_unique_model_native_pixels"] += model*native*n
                totals["family_unique_model_q32_pixels"] += model*padded*n
                totals["cross_family_groups"] += n > 1
                totals["cross_family_model_groups"] += model and n > 1
                totals["additional_model_frames_avoided"] += model*(n-1)
                totals["additional_native_pixels_avoided"] += model*native*(n-1)
                totals["additional_q32_pixels_avoided"] += model*padded*(n-1)
                if n > 1:
                    # x2 guide uint8 + indices uint8 + RGB uint8: 4*(1+1+3) bytes/native pixel.
                    payload = 20*native
                    totals["shared_dense_payload_bytes"] += payload
                    fids = list(bits(selected))
                    memory_events[name][fids[0]] += payload
                    memory_events[name][fids[-1]] -= payload
                    cohort = cohorts[(name, selected)]
                    cohort.update(groups=1, model_groups=int(model), model_frames_avoided=int(model)*(n-1),
                                  q32_pixels_avoided=int(model)*padded*(n-1), dense_payload_bytes=payload)
            record = {"key": key.hex(), "size": [w, h], "model": model,
                      "families": list(bits(mask)), "logical_occurrences": occurrences,
                      "representative": references[0], "references": references}
            stream.write((json.dumps(record, separators=(",", ":"))+"\n").encode())
    for name, selection in (("pending_in_76", primary_mask), ("all_pending_78", all_mask)):
        chosen = [families[i] for i in bits(selection)]
        totals = scope_totals[name]
        totals.update(families=len(chosen), components=sum(f["components"] for f in chosen),
                      source_frames=sum(f["source_frames"] for f in chosen),
                      source_resources=sum(f["source_resources"] for f in chosen),
                      canonical_resources=sum(f["canonical_resources"] for f in chosen),
                      logical_model_frames=sum(f["logical_model_frames"] for f in chosen),
                      logical_q32_pixels=sum(f["logical_q32_pixels"] for f in chosen))
        totals["within_family_model_frames_avoided"] = totals["logical_model_frames"]-totals["family_unique_model_frames"]
        retained = peak = 0
        for fid in range(len(families)):
            retained += memory_events[name][fid]
            peak = max(peak, retained)
        assert retained == 0
        totals["sequential_family_boundary_payload_peak_bytes"] = peak
        totals["additional_model_reduction_fraction"] = totals["additional_model_frames_avoided"]/totals["family_unique_model_frames"]
        totals["additional_q32_reduction_fraction"] = totals["additional_q32_pixels_avoided"]/totals["family_unique_model_q32_pixels"]
        assert totals["family_unique_model_frames"] == sum(f["unique_model_frames"] for f in chosen)
        assert totals["unique_model_frames"]+totals["additional_model_frames_avoided"] == totals["family_unique_model_frames"]
    cohort_rows = [{"scope": scope, "family_indices": list(bits(mask)),
                    "animation_ids": [families[i]["animation_id"] for i in bits(mask)], **counts}
                   for (scope, mask), counts in cohorts.items()]
    cohort_rows.sort(key=lambda r: (r["scope"], -r["q32_pixels_avoided"], r["animation_ids"]))
    context_records = {key: {k: v for k, v in value.items() if k not in ("context", "palette")}
                       | {"context_sha256": value["context"].hex(),
                          "reference_palette_sha256": hashlib.sha256(value["palette"].tobytes()).hexdigest()
                          if value["palette"] is not None else "native"}
                       for key, value in contexts.items()}
    inventory = {"schema": "reboutcx-pending-source-inventory-v1", "pixel_contract": PIXEL_CONTRACT,
                 "families": families, "components": components, "resources": resources,
                 "contexts": context_records, "pinned_inputs": pinned}
    dump_new(destination / "source-inventory.json", inventory)
    dump_new(destination / "sharing-cohorts.json", cohort_rows)
    # Only small pinned metadata/code files are reread at completion; all BAM bytes were checked above.
    for reference, expected in pinned.items():
        assert sha256_file(resolve_path_reference(reference)) == expected, reference
    summary = {"schema": "reboutcx-pending-frame-groups-analysis-v1", "status": "source-inventory-only",
               "baseline_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "progress_snapshot": relative(PROGRESS), "progress_sha256": pinned[relative(PROGRESS)],
               "scopes": scope_totals, "resource_templates_decoded": len(resources),
               "pixel_groups": len(groups), "payload_files_hash_checked": len(checked_payloads),
               "metadata_seconds": metadata_seconds, "scan_seconds": scan_seconds,
               "total_seconds": time.perf_counter()-start,
               "artifacts": {p.name: {"sha256": sha256_file(p), "bytes": p.stat().st_size}
                             for p in destination.iterdir() if p.is_file()},
               "limits": ["No inference or output-equivalence measurement; sufficient source identity only.",
                          "Family-cache baseline assumes no eviction; cross-family savings are additional to intra-family reuse.",
                          "No reuse from completed families counted.",
                          "q32 pixels exclude N=86 filler slots; not an end-to-end speedup.",
                          "Dense cache payload omits metrics, representatives, Python overhead and active buffers.",
                          "0x6102/0x6110 are outside original 76 and projected using the common pinned template."]}
    dump_new(destination / "summary.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    run(parser.parse_args().destination)
