"""Explicit P12 queues, longest jobs first, one GPU owner, asynchronous verification."""
from __future__ import annotations

import argparse
import json
import multiprocessing
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, ThreadPoolExecutor, wait
from pathlib import Path

from reboutcx_full_p12 import (RUN_ID, derive_job, execute, read_json, relative,
                             resolve_path_reference, sha256_file, validate_job, verify)
from reboutcx_runtime_p12 import Runtime

from reboutcx_plan_p12 import plan_cache

QUEUE_SCHEMA = "bg2-upscale-reboutcx-p12-queue-v1"


def prepare_queue(family_jobs: list[Path], destination: Path) -> dict:
    if destination.exists():
        raise RuntimeError("queue already exists; choose a new queue version")
    sources = []
    for path in family_jobs:
        family = read_json(path)
        prepared = resolve_path_reference(family["paths"]["run_dir"]) / "prepared.json"
        # Never bootstrap, audit or prepare P8 in the P12 controller.
        for member in read_json(prepared)["members"]:
            source = resolve_path_reference(member["job"], required=True)
            if read_json(source).get("runtime_profile") != "character-bg2ee-2.7.3.0":
                raise RuntimeError("P12 playable queue requires Character component jobs")
            sources.append(source)
    jobs = [derive_job(source) for source in dict.fromkeys(sources)]
    queue = {"schema": QUEUE_SCHEMA, "installable": False,
             "members": [{"job": relative(path), "sha256": sha256_file(path)} for path in jobs]}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(queue, stream, indent=2)
        stream.write("\n")
    return queue


def load_queue(path: Path) -> list[Path]:
    queue = read_json(path)
    if queue.get("schema") != QUEUE_SCHEMA or queue.get("installable") is not False:
        raise RuntimeError("invalid P12 queue")
    jobs, outputs, model_contract = [], set(), None
    for member in queue["members"]:
        job_path = resolve_path_reference(member["job"], required=True).resolve()
        if sha256_file(job_path) != member["sha256"]:
            raise RuntimeError("P12 queue job hash differs")
        job = read_json(job_path)
        validate_job(job)
        if job.get("runtime_profile") != "character-bg2ee-2.7.3.0":
            raise RuntimeError("P12 queue is restricted to Character jobs")
        model = (str(resolve_path_reference(job["paths"]["reboutcx_model"]).resolve()),
                 job["reboutcx"]["model_sha256"], job["reboutcx"]["device"],
                 job["reboutcx"]["fp16"])
        if model_contract is not None and model_contract != model:
            raise RuntimeError("P12 queue contains multiple model/device/precision contracts")
        model_contract = model
        output = resolve_path_reference(job["paths"]["run_dir"]).resolve()
        if output in outputs:
            raise RuntimeError("P12 queue contains duplicate output directories")
        outputs.add(output)
        jobs.append(job_path)
    return sorted(jobs, key=lambda p: (-priority(p), str(p)))


def priority(path: Path) -> float:
    job = read_json(path)
    source_job = resolve_path_reference(job["p12_source_job"]["path"], required=True)
    if sha256_file(source_job) != job["p12_source_job"]["sha256"]:
        raise RuntimeError("source job changed after P12 derivation")
    original = read_json(source_job)
    source_run = resolve_path_reference(original["paths"]["run_dir"])
    historical = source_run.with_name("reboutcx-p9-batch86-v1") / "manifest.json"
    if historical.is_file():
        timing = read_json(historical)["timing_seconds"]
        return sum(float(value) for value in timing.values())
    # COMPS39 is a known heavy tail even when no historical timing exists.
    if str(job.get("item_resref", "")).upper() == "COMPS39" or "comps39-" in str(path).lower():
        return 1e12
    source = resolve_path_reference(job["paths"]["source_manifest"], required=True)
    return sum((source.parent / bam["canonical_bam"]).stat().st_size
               for bam in read_json(source)["bams"]) / 1e6


def run_queue(path: Path, *, components: int = 3, pre_workers: int = 2,
              post_workers: int = 3, memory_mib: int = 4096, cache_mib: int = 1024, log_dir: Path | None = None) -> dict:
    jobs = load_queue(path)
    if not jobs:
        raise RuntimeError("P12 queue is empty")
    if not 1 <= components <= 3:
        raise ValueError("component concurrency must be between one and three")
    # An append-free, exclusive session log; every invocation gets its own version.
    logs = log_dir if log_dir is not None else Path(__file__).resolve().parents[2] / "sprite/.work/reboutcx-p12-production"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / f"session-{time.time_ns()}.jsonl"
    started, completed, total_frames = time.perf_counter(), 0, 0
    context = multiprocessing.get_context("spawn")
    with log_path.open("x", encoding="utf-8") as log, Runtime(
            pre_workers=pre_workers, post_workers=post_workers, memory_mib=memory_mib, cache_mib=cache_mib) as runtime, \
            ThreadPoolExecutor(max_workers=components) as renders, \
            ProcessPoolExecutor(max_workers=1, mp_context=context) as verifier:
        def emit(event: str, **fields):
            record = {"event": event, "elapsed_seconds": time.perf_counter() - started, **fields}
            line = json.dumps(record)
            log.write(line + "\n")
            log.flush()
            print(line, flush=True)

        active, checks, index = {}, {}, 0
        logical_frames = source_frames = gpu_slots = filler_frames = 0
        emit("start", queue=relative(path), queue_sha256=sha256_file(path), jobs=len(jobs))
        try:
            admission, cache_plan = plan_cache(jobs)
            runtime.cache.declare_counts(admission)
            del admission
            emit("cache-plan", **cache_plan)
            while index < len(jobs) or active or checks:
                # Completed renders leave their slot immediately. Verification has its own worker.
                # At most two queued checks plus the already active renders.
                while index < len(jobs) and len(active) < components and len(checks) < 2:
                    job_path = jobs[index]
                    index += 1
                    output = resolve_path_reference(read_json(job_path)["paths"]["run_dir"])
                    if (output / "manifest.json").is_file():
                        checks[verifier.submit(verify, job_path)] = (job_path, time.perf_counter(), True)
                    else:
                        active[renders.submit(execute, job_path, runtime)] = job_path
                        emit("render-start", job=relative(job_path))
                done, _ = wait([*active, *checks], return_when=FIRST_COMPLETED)
                for future in done:
                    if future in active:
                        job_path = active.pop(future)
                        manifest = future.result()
                        total_frames += manifest["coverage"]["unique_model_frames"]
                        logical_frames += manifest["coverage"]["logical_model_frames"]
                        source_frames += manifest["coverage"]["frames"]
                        gpu_slots += manifest["coverage"]["gpu_slots"]
                        filler_frames += manifest["coverage"]["gpu_filler_frames"]
                        checks[verifier.submit(verify, job_path)] = (job_path, time.perf_counter(), False)
                        emit("render-finished", job=relative(job_path),
                             **runtime.execution_reports.pop(str(job_path.resolve())))
                    else:
                        job_path, tick, existing = checks.pop(future)
                        result = future.result()
                        completed += 1
                        emit("verified", job=relative(job_path), existing=existing,
                             verification_queue_and_wall_seconds=time.perf_counter() - tick,
                             manifest_sha256=result["manifest_sha256"])
        except BaseException as error:
            for future in [*active, *checks]:
                future.cancel()
            emit("failed", error=str(error), completed=completed)
            raise
        elapsed = time.perf_counter() - started
        report = {"completed": completed, "new_model_frames": total_frames,
                  "wall_through_verification_seconds": elapsed,
                  "actual_model_frames_per_second": total_frames / elapsed,
                  "logical_model_frames": logical_frames, "logical_model_frames_per_second": logical_frames / elapsed,
                  "source_frames": source_frames, "source_frames_per_second": source_frames / elapsed,
                  "gpu_slots": gpu_slots, "gpu_filler_frames": filler_frames,
                  "cache": runtime.cache.snapshot(), "cache_plan": cache_plan,
                  "model_load_seconds_once": runtime.model_load_seconds,
                  "peak_reserved_resource_bytes": runtime.memory.peak,
                  "log": relative(log_path)}
        emit("complete", **report)
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--family-job", type=Path, action="append", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    for name in ("plan", "run"):
        cmd = commands.add_parser(name)
        cmd.add_argument("queue", type=Path)
        if name == "run":
            cmd.add_argument("--components", type=int, choices=range(1, 4), default=3)
            cmd.add_argument("--pre-workers", type=int, default=2)
            cmd.add_argument("--post-workers", type=int, default=3)
            cmd.add_argument("--memory-mib", type=int, default=4096)
            cmd.add_argument("--cache-mib", type=int, default=1024)
    args = parser.parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare_queue(args.family_job, args.output)))
    elif args.command == "plan":
        print(json.dumps({"jobs_in_execution_order": [relative(p) for p in load_queue(args.queue)]}, indent=2))
    else:
        run_queue(args.queue, components=args.components, pre_workers=args.pre_workers,
                  post_workers=args.post_workers, memory_mib=args.memory_mib, cache_mib=args.cache_mib)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
