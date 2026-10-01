"""Canonical Q3m entry for playable Characters: required dedup plan + shared I/F.

`plan` is CPU/read-only when the plan is present. `run` explicitly starts GPU
production. `pack` only assembles existing results into an experimental catalog.
No command installs, assigns QA or changes release assets.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import numpy as np

import analyze_playable_frame_dedup as analysis
from palette_complete import PixelProcessor
import palette_frac_encode as encoder
import palette_registry as v6
from palette_work_plan import (ACTIVE, CACHE_ROOT, POINTER_SCHEMA, ROOT, ResultCache,
                               WorkPlan, file_sha, write_json)
from reboutcx_cache_p12 import frame_key
from reboutcx_multipal import inference_context
import run_creature_sprite_x2 as registry
from workspace_paths import get_path


def known_seed_runs():
    root = ROOT / "sprite/families/playable-characters/6110-human-female-fighter/research"
    result = []
    for name in ("palette-q3m-p3-20261001-v3-full-6110", "palette-q3m-p3-20261001-v5-full-x4-6110"):
        path = root / name
        if all((path / n).is_file() for n in ("recipe.json", "coverage.json", "verification.json")):
            result.append(dict(path=path.relative_to(ROOT).as_posix(),
                               sha256={n: file_sha(path / n) for n in ("recipe.json", "coverage.json", "verification.json")}))
    return result


def activate(path, pointer=ACTIVE):
    """Select a verified source snapshot; never mutate the snapshot itself."""
    path = Path(path).resolve()
    path.relative_to(ROOT)
    db = analysis.sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    meta = {k: json.loads(v) for k, v in db.execute("SELECT * FROM metadata")}
    analysis.require(meta["schema"] == analysis.SCHEMA and meta["status"] == "complete-source-analysis-not-generated", "unfinished source plan")
    analysis.require(db.execute("PRAGMA integrity_check").fetchone() == ("ok",) and not db.execute("PRAGMA foreign_key_check").fetchall(), "source plan integrity failed")
    db.close()
    for relative, expected in meta["source_pins"].items():
        analysis.require(file_sha(ROOT / relative) == expected, f"plan source changed: {relative}")
    descriptor = dict(schema=POINTER_SCHEMA, role="source-work-plan-not-production-or-QA",
                      path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size, sha256=file_sha(path),
                      summary=meta["summary"]["counts"], analysis=path.parent.relative_to(ROOT).as_posix(),
                      consumer="pipeline/scripts/palette_playable.py", trusted_seed_runs=known_seed_runs())
    write_json(pointer, descriptor)
    return descriptor


def restore_plan():
    destination = ROOT / "docs/measurements" / f"playable-palettized-frame-dedup-restored-{time.time_ns()}"
    analysis.scan(destination)
    analysis.verify(destination / "processing-plan.sqlite")
    (destination / ".gitignore").write_text("processing-plan.sqlite\n", encoding="utf-8")
    return activate(destination / "processing-plan.sqlite")


def active_plan():
    analysis.require(ACTIVE.is_file(), "missing active source-plan pointer; use palette_playable.py activate <verified.sqlite>")
    pointer = json.loads(ACTIVE.read_text())
    if not (ROOT / pointer["path"]).is_file():
        print("Required dedup plan missing: rebuilding source analysis on CPU before production", flush=True)
        restore_plan()
    return WorkPlan().validate_sources()


class SharedPixelProcessor(PixelProcessor):
    """Retain the proven pixel math; change only task identity and result location."""
    def __init__(self, plan, cache, workers):
        context = inference_context()
        analysis.require(context == plan.profile["inference"], "inference environment differs from active Q3m plan; rebuild the plan")
        self.plan = plan
        super().__init__(cache.root, plan.fitting(), context, workers, cache.scale)
        analysis.require(self.cache == cache.directory, "producer did not bind the shared cache")

    def key(self, frame):
        return self.plan.key(frame)


def seed_verified_run(plan, cache, record, *, resrefs=None, work_ids=None):
    """Adopt existing Q3m bytes from hash-pinned, native-verified V6 leaves.

    Old loose NPZ arrays alone are never a proof of Q3m: I/F/dep must match a
    verified V6 leaf. The NPZ supplies the guide; if absent, recompute xBR only.
    """
    path = plan.root / record["path"]
    if not path.is_dir() or not (path / "work/leaves").is_dir():
        return Counter(unavailable_runs=1)
    for name, expected in record["sha256"].items():
        analysis.require(file_sha(path / name) == expected, f"trusted Q3m seed metadata changed: {path / name}")
    recipe = json.loads((path / "recipe.json").read_text())
    proof = json.loads((path / "verification.json").read_text())
    if recipe["scale"] != cache.scale:
        return Counter()
    for value in (recipe, proof):
        analysis.require((value["method"], value["k"], value["boundary_mixing"], value["dithering"]) == ("Q3m", 6, False, False), "seed is not the current Q3m method")
    analysis.require(proof["status"] == "passed-offline-ready-for-manual-game", "seed lacks completed native verification")
    analysis.require(recipe["inference"] == plan.profile["inference"], "seed inference context differs")
    analysis.require(proof["recipe_sha256"].lower() == record["sha256"]["recipe.json"] and
                     proof["coverage_sha256"].lower() == record["sha256"]["coverage.json"], "seed proof does not cover its metadata")
    analysis.require("pipeline/scripts/palette_frac_encode.py" in proof["source_sha256"], "seed proof has no encoder identity")
    for name in ("palette_frac_encode.py", "reboutcx_quantize.py", "xbr2x_batch.js"):
        reference = "pipeline/scripts/" + name
        if reference in proof["source_sha256"]:
            analysis.require(proof["source_sha256"][reference].lower() == plan.profile["code_sha256"][name], "seed pixel code differs")
    # Each descriptor identifies the same six row selections as the active recipe;
    # fitting bytes are the pinned P1 fixture with entry zero restored to green.
    anchor = json.loads(analysis.ANCHOR.read_text())
    analysis.require(recipe["palettes"] == anchor["palettes"], "seed fitting palettes differ")
    fitting = plan.fitting()
    legacy_context = hashlib.sha256(json.dumps(recipe["inference"], sort_keys=True).encode() + fitting.tobytes()
                                    + (b"/direct-x4" if cache.scale == 4 else b"")).digest()
    resources = {r["resref"]: r for r in plan.resources([recipe["animation_id"]])}
    coverage = json.loads((path / "coverage.json").read_text())["resources"]
    counts = Counter()
    for report in coverage:
        ref = report["resref"]
        if resrefs is not None and ref not in resrefs:
            continue
        resource = resources[ref]
        analysis.require(report["source_sha256"].lower() == resource["canonical_sha256"], "seed source identity differs")
        rows = plan.db.execute("""SELECT f.*,q.* FROM frames f JOIN processing_queue q USING(work_id)
                                  WHERE resource_id=? ORDER BY frame_index""", (resource["resource_id"],)).fetchall()
        pending = []
        for row in rows:
            if work_ids is not None and row["work_id"] not in work_ids:
                continue
            frame = plan.frame(row, resref=ref, index=row["frame_index"], centre=(row["center_x"], row["center_y"]), palette_bgra=resource["palette_bgra"])
            if not cache.contains(frame):
                pending.append((row, frame))
        if not pending:
            continue
        leaf = path / "work/leaves" / f"{ref}.registry"
        if not leaf.is_file():
            counts["unavailable_resources"] += 1
            continue
        analysis.require(file_sha(leaf).upper() == report["registry_sha256"].upper(), "verified seed leaf changed")
        leaf_info = v6.inspect(leaf, include_frames=True)
        analysis.require(leaf_info["scale"] == cache.scale and len(leaf_info["frame_data"]) == 1, "seed leaf scope differs")
        native = leaf_info["frame_data"][0]
        analysis.require(native["resref"] == ref and native["source_sha256"] == resource["canonical_sha256"] and len(native["frames"]) == len(rows), "seed frame/source coverage differs")
        for row, frame in pending:
            if cache.contains(frame):
                continue
            decoded = native["frames"][row["frame_index"]]
            shape = (frame.height * cache.scale, frame.width * cache.scale)
            i = np.frombuffer(decoded["I"], np.uint8).reshape(shape).copy()
            f = np.frombuffer(decoded["F"], np.uint8).reshape(shape).copy() if decoded["F"] else np.zeros(shape, np.uint8)
            dep = np.frombuffer(decoded["dep"], np.uint8).copy()
            analysis.require(decoded["geometry"] == (frame.width, frame.height, frame.center_x, frame.center_y, frame.transparent), "seed native geometry differs")
            reps = np.full(256, 65535, np.uint16)
            values, offsets = np.unique(frame.indices, return_index=True); reps[values] = offsets
            analysis.require(np.array_equal(decoded["representatives"], reps), "seed representatives differ")
            loose = path / "work/encoded" / (frame_key(frame, None, legacy_context).hex() + ".npz")
            if loose.is_file():
                with np.load(loose, allow_pickle=False) as data:
                    analysis.require(all(np.array_equal(data[name], expected) for name, expected in (("I", i), ("F", f), ("dep", dep))), "loose seed cache differs from verified leaf")
                    guide = data["guide"].copy()
            elif not np.any(frame.indices != frame.transparent) or (frame.indices.shape == (1, 1) and int(frame.indices[0, 0]) == 2):
                guide = np.repeat(np.repeat(frame.indices, cache.scale, 0), cache.scale, 1)
            else:
                output = registry.run_xbr([frame], get_path("mmpx_scalepix", required=True), "node", registry.direct_upscale_contract(cache.scale))[0]
                provenance = registry.xbr_provenance_indices(frame, cache.scale) if registry.has_duplicate_used_rgba_indices(frame) else None
                guide, _ = registry.map_output(frame, output[2], provenance)
                guide = guide.reshape(shape)
            cache.save(frame, dict(guide=guide, I=i, F=f, dep=dep))
            counts["seeded_unique_results"] += 1
        counts["verified_seed_resources"] += 1
        print(json.dumps(dict(phase="seed-verified-q3m", resref=ref, **counts)), flush=True)
    return counts


def produce(plan, cache, ids=None, workers=4, *, processor_factory=SharedPixelProcessor):
    """Global queue once; no inference for hits, markers or source aliases."""
    counts, pending, processor = Counter(), [], None
    def flush():
        nonlocal processor
        if not pending:
            return
        if processor is None:
            processor = processor_factory(plan, cache, workers)
        processor.process(pending)
        for frame in pending:
            cache.load(frame)
        counts["new_unique_results"] += len(pending)
        pending.clear()
    try:
        for row in plan.work_rows(ids):
            frame = plan.frame(row)
            counts["selected_unique_work"] += 1
            if cache.contains(frame):
                counts["reused_unique_results"] += 1
            elif not row["needs_model"]:
                guide = np.repeat(np.repeat(frame.indices, cache.scale, 0), cache.scale, 1)
                f = np.zeros_like(guide)
                cache.save(frame, dict(guide=guide, I=guide, F=f, dep=encoder.dependency_mask(guide, f)))
                counts["special_unique_results"] += 1
            else:
                pending.append(frame)
                if len(pending) == 64:
                    flush()
                    print(json.dumps(dict(phase="unique-q3m", **counts)), flush=True)
        flush()
        if processor is not None:
            counts.update(processor.stats)
    finally:
        if processor is not None:
            processor.pool.shutdown(wait=True)
    analysis.require(counts["selected_unique_work"] == counts["reused_unique_results"] + counts["new_unique_results"] + counts["special_unique_results"], "work queue did not complete")
    return dict(counts)


def pack(plan, cache, output, ids=None):
    """One V6 shard/native resource, reused by every selected model; no GPU."""
    output = Path(output)
    analysis.require(not output.exists(), "experimental pack output must be new")
    chosen, _ = plan.selection(ids)
    for row in plan.work_rows(ids):
        analysis.require((cache.directory / (row["work_key"] + ".npz")).is_file(), "shared results incomplete; run Q3m production first")
    output.mkdir(parents=True)
    infos, components, logical, directories, resource_components = [], [], [], [], {}
    storage = dict(shard_registry_version=6, stored_index_bytes=0, stored_fraction_bytes=0, fraction_bytes=0,
                   compressed_frame_count=0, raw_frame_count=0, compressed_fraction_count=0, fractional_frame_count=0)
    for n, resource in enumerate(plan.resources(ids)):
        materialized = plan.materialize(resource, cache)
        temporary = output / f"resource-{n:05d}.registry"
        info = v6.write(temporary, cache.scale, [materialized])
        leaf = output / registry.catalog_shard_filename(info["sha256"])
        temporary.rename(leaf)
        info = v6.inspect(leaf, include_resource_records=True)
        infos.append(info)
        components.append(dict(index=n, digest=registry.catalog_component_digest(cache.scale, [registry.catalog_shard_entry_bytes(info, leaf)]),
                               shard_start=n, shard_count=1, resource_count=1, frame_count=info["frame_count"],
                               index_bytes=info["index_bytes"], registry_bytes=info["registry_bytes"]))
        logical.append(registry.catalog_source_component_sha256(cache.scale, info["resource_records"]))
        resource_components[resource["resource_id"]] = n
        for key in storage:
            if key != "shard_registry_version":
                storage[key] += info[key]
        print(f"pack {n+1} {resource['resref']}", flush=True)
    animations = []
    for animation in chosen:
        membership = []
        for resource in plan.resources([animation]):
            component = resource_components[resource["resource_id"]]
            membership.append(component)
            directories.append(dict(animation_id=animation, resref=resource["resref"], component_index=component, shard_index=component, resource_ordinal=0))
        animations.append(dict(animation_id=animation, owner=1, component_indices=membership))
    result = registry.write_registry_catalog_index(output / registry.XN_REGISTRY_CATALOG_FILENAME, cache.scale,
                                                  animations, components, infos, directories, logical, storage)
    registry.read_sealed_catalog_index(output / registry.XN_REGISTRY_CATALOG_FILENAME, result["sha256"])
    write_json(output / "pack.json", dict(schema="bg2-playable-q3m-experimental-pack-v1", status="generated-not-native-or-ingame-verified",
               source_plan_sha256=plan.descriptor["sha256"], result_namespace=cache.namespace,
               scale=cache.scale, animations=chosen, resources=len(infos), catalog=result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "restore-plan", "activate", "run", "pack"))
    parser.add_argument("--scale", type=int, choices=(2, 4), default=4)
    parser.add_argument("--animation-id", action="append")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    if args.command == "restore-plan":
        print(json.dumps(restore_plan(), ensure_ascii=False)); return
    if args.command == "activate":
        analysis.require(args.database is not None, "activate requires --database")
        print(json.dumps(activate(args.database), ensure_ascii=False)); return
    plan = active_plan()
    try:
        if args.command == "plan":
            chosen, _ = plan.selection(args.animation_id)
            counts = Counter()
            for row in plan.work_summaries(args.animation_id):
                counts.update(unique_work=1, model_work=row["needs_model"])
            print(json.dumps(dict(animations=chosen, scale=args.scale, **counts))); return
        cache = ResultCache(plan, args.scale)
        with cache.exclusive():
            if args.command == "run":
                print("Q3m production: required global dedup plan, shared persistent results, GPU only for missing model work", flush=True)
                seeded = Counter()
                selected_work = {r["work_id"] for r in plan.work_summaries(args.animation_id)}
                for record in plan.descriptor.get("trusted_seed_runs", []):
                    seeded.update(seed_verified_run(plan, cache, record, work_ids=selected_work))
                counts = produce(plan, cache, args.animation_id, args.workers)
                write_json(cache.root / "last-run.json", dict(status="encoded-not-native-or-ingame-verified", source_plan_sha256=plan.descriptor["sha256"], seeded=dict(seeded), counts=counts))
                print(json.dumps(counts))
            else:
                analysis.require(args.output is not None, "pack requires --output")
                args.output.resolve().relative_to(ROOT)
                print(json.dumps(pack(plan, cache, args.output, args.animation_id)))
    finally:
        plan.close()


if __name__ == "__main__":
    main()
