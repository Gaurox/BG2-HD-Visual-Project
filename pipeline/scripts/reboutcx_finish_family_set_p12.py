"""Seal measurements and a new progress snapshot after the explicit ten-family run."""
from __future__ import annotations
from collections import Counter
import copy
import json
from pathlib import Path
import time
from reboutcx_full import read_json,relative,resolve_path_reference,sha256_file
from reboutcx_full_p12 import RUN_ID
from reboutcx_prepare_sources_p12 import write_new

ROOT = Path(__file__).resolve().parents[2]


def finish(plan_path):
    started = time.perf_counter()
    plan = read_json(plan_path)
    summary_path = plan_path.parent/"batch-summary.json"
    summary = read_json(summary_path)
    assert summary["status"]=="ten-families-produced-and-verified"
    assert summary["plan_sha256"]==sha256_file(plan_path)
    previous_path = resolve_path_reference(plan["progress_before"])
    assert sha256_file(previous_path)==plan["progress_before_sha256"]
    previous = read_json(previous_path)
    planned = {f["animation_id"]:f for f in plan["families"]}
    assert len(planned)==10 and list(planned)==previous["pending_animation_ids"][:10]
    assert [f["animation_id"] for f in summary["families"]]==list(planned)
    completed = copy.deepcopy(previous["completed"])
    stages,totals = Counter(),Counter()
    code,inputs = {},{}
    family_reports = []
    for execution in summary["families"]:
        aid = execution["animation_id"]
        family = planned[aid]
        root = resolve_path_reference(family["family"])
        prepared = read_json(root/"family-runs/complete-reboutcx-p12-v1/prepared.json")
        session_path = resolve_path_reference(execution["session"])
        assert sha256_file(session_path)==execution["session_sha256"]
        events = [json.loads(line) for line in session_path.read_text().splitlines()]
        result = events[-1]
        assert result==execution["result"] and result["event"]=="complete"
        assert events[0]["queue_sha256"]==family["queue_sha256"]
        assert sha256_file(resolve_path_reference(family["queue"]))==family["queue_sha256"]
        verified = {e["job"]:e for e in events if e["event"]=="verified"}
        assert len(verified)==result["completed"]==family["components"]==len(prepared["members"])
        assert result["source_frames"]<=family["source_frames"]
        attempts = execution.get("attempts",[{"session":execution["session"],"sha256":execution["session_sha256"],"terminal_event":result}])
        for attempt in attempts:
            assert sha256_file(resolve_path_reference(attempt["session"]))==attempt["sha256"]
        family_wall = execution.get("wall_including_recovery_seconds",result["wall_through_verification_seconds"])
        assert result["cache"]["inflight_entries"]==0
        components,coverage = [],Counter()
        for member in prepared["members"]:
            job_path = resolve_path_reference(member["job"])
            assert sha256_file(job_path)==member["sha256"]
            evidence = verified[member["job"]]
            assert evidence["existing"] is False or len(attempts)>1
            job = read_json(job_path)
            manifest_path = resolve_path_reference(job["paths"]["run_dir"])/"manifest.json"
            assert sha256_file(manifest_path)==evidence["manifest_sha256"]
            manifest = read_json(manifest_path)
            assert manifest["animation_id"]==aid and manifest["job_sha256"]==member["sha256"]
            assert manifest["status"]=="completed-pending-human-review" and manifest["installable"] is False
            assert manifest["source_manifest_sha256"]==member["source_manifest_sha256"]
            inputs[(member["source_manifest"],member["source_manifest_sha256"])]=None
            inputs[(job["p12_source_job"]["path"],job["p12_source_job"]["sha256"])]=None
            inputs[(job["preparation"]["script"],job["preparation"]["script_sha256"])]=None
            inputs[(job["preparation"]["contract_template"],job["preparation"]["contract_template_sha256"])]=None
            for entry in manifest["code"].values():
                code[(entry["path"],entry["sha256"])]=None
            coverage.update(manifest["coverage"])
            stages.update(manifest["timing_seconds"])
            components.append({"component_index":member["component_index"],"manifest":relative(manifest_path),
                "manifest_sha256":evidence["manifest_sha256"]})
        assert len({c["component_index"] for c in components})==len(components)
        assert coverage["frames"]==family["source_frames"]
        assert coverage["logical_model_frames"]>=result["logical_model_frames"]
        assert coverage["unique_model_frames"]>=result["new_model_frames"]
        if len(attempts)==1:
            assert coverage["logical_model_frames"]==result["logical_model_frames"]
            assert coverage["unique_model_frames"]==result["new_model_frames"]
        assert coverage["gpu_slots"]==coverage["unique_model_frames"]+coverage["gpu_filler_frames"]
        assert not list(root.glob("*/runs/.reboutcx-p12-cache86-v1.tmp-*"))
        completed.append({"animation_id":aid,"family":family["family"],"method":RUN_ID,"components":components,
            "verification_session":execution["session"],"verification_session_sha256":execution["session_sha256"]})
        family_report = {"animation_id":aid,"family":family["family"],"components":len(components),
            "source_frames":coverage["frames"],"logical_model_frames":coverage["logical_model_frames"],
            "computed_model_frames":coverage["unique_model_frames"],"avoided_model_frames":coverage["model_cache_hit_frames"],
            "wall_through_verification_seconds":family_wall,
            "logical_model_frames_per_second":coverage["logical_model_frames"]/family_wall,
            "cache_peak_bytes":result["cache"]["peak_retained_bytes"],"cache_evictions":result["cache"].get("evictions",0),
            "cache_plan_seconds":result["cache_plan"]["seconds"],"session":execution["session"],
            "session_sha256":execution["session_sha256"],"attempts":attempts,
            "last_session_existing_components":sum(e["existing"] for e in verified.values()),
            "time_note":"family wall includes recovery gaps; cache peak and admission timing refer to final session"}
        family_reports.append(family_report)
        totals.update(components=len(components),source_frames=coverage["frames"],logical_model_frames=coverage["logical_model_frames"],
            computed_model_frames=coverage["unique_model_frames"],avoided_model_frames=coverage["model_cache_hit_frames"],
            wall_through_verification_seconds=family_wall)
        write_new(root/"family-runs/complete-reboutcx-p12-v1/measurements/production-p12-v1.json",family_report)
    # Preserve previous production evidence, then record the already verified P12 pilot.
    for family in previous["completed"]:
        for member in family["components"]:
            assert sha256_file(resolve_path_reference(member["manifest"]))==member["manifest_sha256"]
    pilot = next(f for f in completed if f["animation_id"]=="0x5211")
    pilot_measurement = read_json(resolve_path_reference(pilot["family"])/"family-runs/complete-reboutcx-p12-v1/measurements/throughput-p12-v1.json")
    pilot_hashes = {m["manifest"]:m["manifest_sha256"] for m in pilot_measurement["members"]}
    for component in pilot["components"]:
        path = resolve_path_reference(component["manifest"]).parent.with_name(RUN_ID)/"manifest.json"
        reference = relative(path)
        assert sha256_file(path)==pilot_hashes[reference]
        component.update(manifest=reference,manifest_sha256=pilot_hashes[reference])
    pilot["method"] = RUN_ID
    for path,expected in [*code,*inputs]:
        assert sha256_file(resolve_path_reference(path))==expected,path
    snapshot = copy.deepcopy(previous)
    snapshot["snapshot_id"] = "p12-v1"
    snapshot["completed"] = sorted(completed,key=lambda f:int(f["animation_id"],16))
    snapshot["pending_animation_ids"] = [a for a in previous["pending_animation_ids"] if a not in planned]
    snapshot["totals"].update(completed_families=len(completed),pending_families=len(snapshot["pending_animation_ids"]),
        reboutcx_components=sum(len(f["components"]) for f in completed))
    assert len(completed)==33 and len(snapshot["pending_animation_ids"])==45
    assert len(completed)+len(snapshot["pending_animation_ids"])==snapshot["totals"]["playable_families"]
    assert totals["components"]==summary["components"]==plan["components"]==638
    assert totals["source_frames"]==summary["source_frames"]==plan["source_frames"]
    snapshot["previous_snapshot"]={"path":relative(previous_path),"sha256":sha256_file(previous_path)}
    snapshot["production_batch"]={"path":relative(summary_path),"sha256":sha256_file(summary_path)}
    status_path = ROOT/"sprite/catalogs/creature-x2-reboutcx/jobs/playable-characters-reboutcx-progress-p12-v1.json"
    write_new(status_path,snapshot)
    report = {"status":"ten-new-families-produced-and-verified","totals":dict(totals),"families":family_reports,
        "batch_wall_seconds":summary["wall_seconds"],"prepare_seconds":plan["prepare_seconds"],
        "aggregate_logical_model_frames_per_second":totals["logical_model_frames"]/totals["wall_through_verification_seconds"],
        "stage_seconds_sums":dict(stages),"stage_sums_overlap":True,"parameters":plan["parameters"],
        "progress_snapshot":relative(status_path),"progress_snapshot_sha256":sha256_file(status_path),
        "progress_totals":snapshot["totals"],"previous_component_manifests_unchanged":sum(len(f["components"]) for f in previous["completed"]),
        "pinned_code_and_inputs_unchanged":len(code)+len(inputs),"validation_seconds":time.perf_counter()-started,
        "boundaries":snapshot["boundaries"]}
    write_new(plan_path.parent/"production-report.json",report)
    return {k:v for k,v in report.items() if k not in ("families","stage_seconds_sums")}


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan",type=Path)
    print(json.dumps(finish(parser.parse_args().plan)))
