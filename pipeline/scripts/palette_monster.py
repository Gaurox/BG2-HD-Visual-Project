"""Scoped Monster Q3m K6 x2 producer. plan=CPU read-only; run=inference; pack=V6 leaves. No install/QA."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import importlib.metadata
import json
import os
from pathlib import Path

import numpy as np

from palette_monster_contract import ROOT, get_profile
from palette_monster_work_plan import Cache, WorkPlan, require
from palette_work_plan import file_sha, write_json
from reboutcx_batch import load_model, prepare_inference_rgb
from reboutcx_batch_p12 import infer_float_crops
from reboutcx_multipal import inference_context
from workspace_paths import get_path


def backend_for_run(cache_root):
    path = Path(cache_root) / "backend.json"
    if not path.exists():
        return inference_context()  # First production run only; never called by plan/tests.
    context = json.loads(path.read_text())
    require(file_sha(get_path("reboutcx_model", required=True)) == context["model_sha256"], "cached inference model changed")
    for name, expected in context["kernels"].items():
        require(file_sha(ROOT / "pipeline/scripts" / name) == expected, f"inference kernel changed: {name}")
    for name, expected in context["dependencies"].items():
        require(importlib.metadata.version(name) == expected, f"inference dependency changed: {name}")
    # Torch metadata is read without importing Torch or initializing CUDA on all-hit resumes.
    require(importlib.metadata.version("torch") == context["torch"], "inference Torch version changed")
    return context


class Processor:
    def __init__(self, cache, workers):
        require(inference_context() == cache.recipe["inference"], "GPU/backend differs from persistent cache")
        import torch
        from chainner_ext import ResizeFilter, resize
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        torch.set_num_threads(4)
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True)
        self.descriptor, _ = load_model(get_path("reboutcx_model", required=True), device="cuda:0", fp16=True)
        self.resize, self.box, self.cache = resize, ResizeFilter.Box, cache
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.stats = Counter()

    def process(self, works):
        guides = {self.cache.plan.key(w): self.cache.plan.guide(w) for w in works}
        groups = defaultdict(list)
        for work in works:
            row = work.row
            groups[row["padded_height"], row["padded_width"]].extend((work, p) for p in range(6))
        completed, tasks = {}, []
        for canvas, requests in sorted(groups.items()):
            for start in range(0, len(requests), 86):
                batch = requests[start:start+86]
                rgbs = [prepare_inference_rgb(w.frame, get_profile(w.row["profile_id"]).fitting[p, :, :3]) for w, p in batch]
                require(all(rgb is not None for rgb in rgbs), "model queue contains transparent frame")
                crops, _ = infer_float_crops(self.descriptor, rgbs, canvas=canvas, fp16=True)
                self.stats["neural_targets"] += len(batch)
                for (work, p), crop in zip(batch, crops, strict=True):
                    target = self.resize(crop, (work.width*2, work.height*2), self.box, False)
                    key = self.cache.plan.key(work)
                    targets = completed.setdefault(key, {})
                    targets[p] = np.ascontiguousarray(np.clip(target, 0, 1), dtype=np.float32)
                    if len(targets) == 6:
                        tasks.append(self.pool.submit(self.encode, work, guides.pop(key), np.stack([targets[k] for k in range(6)])))
                        del completed[key]
                    if len(tasks) >= 8:
                        tasks.pop(0).result()
        for task in tasks: task.result()
        require(not completed and not guides, "incomplete K6 batch")

    def encode(self, work, guide, targets):
        self.cache.save(work, get_profile(work.row["profile_id"]).encode(guide, targets))

    def close(self): self.pool.shutdown(wait=True)


def produce(plan, resources, cache, *, workers=4, processor_factory=Processor):
    plan.validate_sources(resources)
    stats, pending, processor = Counter(), [], None
    def flush():
        nonlocal processor
        if pending:
            if processor is None: processor = processor_factory(cache, workers)
            processor.process(pending)
            stats["model_work"] += len(pending)
            pending.clear()
    try:
        with cache.exclusive():
            for row in plan.work_rows(resources):
                work = plan.work(row)
                stats["selected_work"] += 1
                if cache.contains(work):
                    stats["cache_hits"] += 1
                    continue
                if not row["needs_model"]:
                    require(work.frame.indices.shape == (1, 1) and work.frame.indices[0, 0] == 2, "unknown special work")
                    g = plan.guide(work)
                    f = np.zeros_like(g)
                    cache.save(work, dict(guide=g, I=g.copy(), F=f, dep=get_profile(row["profile_id"]).dependency_mask(g, f)))
                    stats["special_work"] += 1
                else:
                    pending.append(work)
                if len(pending) == 64:
                    flush()
                    print(json.dumps(dict(stats)), flush=True)
            flush()
    finally:
        if processor is not None: processor.close()
    return dict(stats)


def pack(plan, resources, cache, output):
    import palette_registry as v6
    plan.validate_sources(resources)
    output = Path(output)
    require(not output.exists(), "use a new pack directory; sealed/historical output is immutable")
    output.mkdir(parents=True)
    reports = []
    for resource in resources:
        material = plan.materialize(resource, cache)
        info = v6.write(output / (resource["resref"] + ".registry"), 2, [material],
                        class_profile_id=resource["profile_id"], decode_rule_id=2)
        reports.append(dict(resref=resource["resref"], profile_id=resource["profile_id"],
                            frames=resource["frame_count"], cycles=resource["cycle_count"], sha256=info["sha256"]))
    write_json(output / "leaves.json", dict(schema="bg2-monster-q3m-v6-leaves-v1", cache_namespace=cache.namespace,
               resources=reports, status="generated-not-native-verified", ingame_validated=False))
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run", "pack"))
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--refs", nargs="+")
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=4)
    args = parser.parse_args()
    plan = WorkPlan()
    try:
        resources = plan.resources(args.ids, args.refs)
        if args.command == "plan":
            rows = plan.work_rows(resources)
            model = sum(bool(r["needs_model"]) for r in rows)
            print(json.dumps(dict(resources=[r["resref"] for r in resources], frames=sum(r["frame_count"] for r in resources),
                  cycles=sum(r["cycle_count"] for r in resources), work=len(rows), model_work=model,
                  special_work=len(rows)-model, neural_targets=model*6, production_started=False)))
            return
        require(args.cache is not None, "--cache required")
        context_path = args.cache / "backend.json"
        if args.command == "pack":
            require(context_path.is_file() and args.output is not None, "pack requires existing cache backend and --output")
        context = backend_for_run(args.cache)
        cache = Cache(plan, args.cache, context)
        if args.command == "run":
            # The namespace lock prevents concurrent encoders; backend metadata is immutable once written.
            with cache.exclusive():
                if context_path.exists(): require(json.loads(context_path.read_text()) == context, "backend identity conflict")
                else: write_json(context_path, context)
            print(json.dumps(produce(plan, resources, cache, workers=args.workers)), flush=True)
        else:
            print(json.dumps(pack(plan, resources, cache, args.output)), flush=True)
    finally:
        plan.close()


if __name__ == "__main__": main()
