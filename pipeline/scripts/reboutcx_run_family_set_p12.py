"""Run exactly one explicit set of ten prepared families, sequentially; no shutdown."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from reboutcx_full import read_json,relative,resolve_path_reference,sha256_file
from reboutcx_prepare_sources_p12 import write_new

ROOT = Path(__file__).resolve().parents[2]


def run(plan_path,*,resume=False):
    plan = read_json(plan_path)
    families = plan["families"]
    if len(families)!=10 or len({f["animation_id"] for f in families})!=10:
        raise RuntimeError("expected ten distinct families")
    for family in families:
        queue = resolve_path_reference(family["queue"])
        if sha256_file(queue)!=family["queue_sha256"]:
            raise RuntimeError("selected family queue changed")
        for member in read_json(queue)["members"]:
            job = read_json(resolve_path_reference(member["job"]))
            if job["animation_id"]!=family["animation_id"] or (not resume and resolve_path_reference(job["paths"]["run_dir"]).exists()):
                raise RuntimeError("set requires only new runs in the selected families")
    logs = ROOT/"sprite/.work/reboutcx-p12-production"
    batch_logs = logs/(plan_path.parent.name+"-batch")
    batch_logs.mkdir(parents=True,exist_ok=True)
    journal_path = batch_logs/"families.jsonl"
    history = [json.loads(s) for s in journal_path.read_text().splitlines()] if resume else []
    records = [r for r in history if r["event"]=="family-complete"]
    done = {r["animation_id"] for r in records}
    batch_epoch = journal_path.stat().st_ctime if resume else time.time()
    started = time.perf_counter()-(time.time()-batch_epoch)
    with journal_path.open("a" if resume else "x",encoding="utf-8",newline="\n") as journal:
        def emit(record):
            line = json.dumps(record)
            journal.write(line+"\n")
            journal.flush()
            print(line,flush=True)
        for index,family in enumerate(families,1):
            if family["animation_id"] in done:
                continue
            previous = set(logs.glob("session-*.jsonl"))
            output = batch_logs/(family["animation_id"]+(f"-resume-{time.time_ns()}" if resume else "")+"-stdout.log")
            tick = time.perf_counter()
            emit({"event":"family-start","number":index,"animation_id":family["animation_id"],
                  "elapsed_seconds":tick-started,"queue":family["queue"],"stdout":relative(output)})
            with output.open("x",encoding="utf-8") as stream:
                process = subprocess.run([sys.executable,"-B",str(ROOT/"pipeline/scripts/reboutcx_playable_p12.py"),
                    "run",family["queue"],"--components","3","--pre-workers","2","--post-workers","3",
                    "--memory-mib","4096","--cache-mib","1024"],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            current = set(logs.glob("session-*.jsonl"))-previous
            if process.returncode or len(current)!=1:
                emit({"event":"failed","animation_id":family["animation_id"],"returncode":process.returncode,"stdout":relative(output)})
                raise RuntimeError("family execution failed; inspect the recorded stdout")
            session = current.pop()
            events = [json.loads(line) for line in session.read_text(encoding="utf-8").splitlines()]
            result = events[-1]
            if (result["event"]!="complete" or result["completed"]!=family["components"]
                    or result["source_frames"]>family["source_frames"] or events[0]["queue_sha256"]!=family["queue_sha256"]):
                raise RuntimeError("completed family coverage differs from the selected source")
            attempts = []
            for candidate in sorted(logs.glob("session-*.jsonl")):
                with candidate.open(encoding="utf-8") as source:
                    first = json.loads(source.readline())
                if first["queue_sha256"]!=family["queue_sha256"]:
                    continue
                attempt_events = [json.loads(s) for s in candidate.read_text().splitlines()]
                attempts.append({"session":relative(candidate),"sha256":sha256_file(candidate),"terminal_event":attempt_events[-1]})
            first_epoch = int(Path(attempts[0]["session"]).stem.split('-')[1])/1e9
            final_epoch = int(session.stem.split('-')[1])/1e9+result["wall_through_verification_seconds"]
            record = {"event":"family-complete","number":index,"animation_id":family["animation_id"],
                "elapsed_seconds":time.perf_counter()-started,"process_wall_seconds":time.perf_counter()-tick,
                "session":relative(session),"session_sha256":sha256_file(session),"result":result,
                "attempts":attempts,"wall_including_recovery_seconds":final_epoch-first_epoch}
            records.append(record)
            emit(record)
    summary = {"schema":"reboutcx-p12-family-set-result-v1","status":"ten-families-produced-and-verified",
        "plan":relative(plan_path),"plan_sha256":sha256_file(plan_path),"families":records,
        "components":sum(r["result"]["completed"] for r in records),
        "source_frames":sum(f["source_frames"] for f in families),
        "wall_seconds":time.perf_counter()-started}
    write_new(plan_path.parent/"batch-summary.json",summary)
    return {k:v for k,v in summary.items() if k!="families"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan",type=Path)
    parser.add_argument("--resume",action="store_true")
    args=parser.parse_args()
    print(json.dumps(run(args.plan,resume=args.resume)))
