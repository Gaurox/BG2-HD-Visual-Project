"""Read-only comparison after one completed P12 family; writes one new measurement."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"pipeline/scripts"))
from reboutcx_full import read_json,resolve_path_reference,sha256_file,relative
from run_creature_sprite_x2 import REGISTRY_HEADER_BYTES,REGISTRY_RESOURCE_HEADER_BYTES,REGISTRY_FRAME_HEADER_BYTES


def compare_registry(a,b,classes,selected=None):
    if selected is None:
        selected = set(np.linspace(0,len(a["frame_records"])-1,min(8,len(a["frame_records"])),dtype=int).tolist())
    count = Counter(resources=1)
    lookup = np.full(256,-1,dtype=np.int16)
    for index,values in enumerate(classes.values()):
        lookup[values] = index
    with resolve_path_reference(a["component"]["path"]).open("rb") as old, \
            resolve_path_reference(b["component"]["path"]).open("rb") as new:
        assert old.read(REGISTRY_HEADER_BYTES+REGISTRY_RESOURCE_HEADER_BYTES)==new.read(REGISTRY_HEADER_BYTES+REGISTRY_RESOURCE_HEADER_BYTES)
        for index in range(len(a["frame_records"])):
            old_header,new_header = old.read(REGISTRY_FRAME_HEADER_BYTES),new.read(REGISTRY_FRAME_HEADER_BYTES)
            assert old_header==new_header, (a["resref"],index,"geometry/representatives")
            _w,_h,_cx,_cy,tr,size = struct.unpack_from("<HHhhB3xI",old_header)
            if index not in selected:
                old.seek(size,1)
                new.seek(size,1)
                continue
            left,right = np.frombuffer(old.read(size),dtype=np.uint8),np.frombuffer(new.read(size),dtype=np.uint8)
            assert len(left)==len(right)==size
            np.testing.assert_array_equal(left==tr,right==tr)
            np.testing.assert_array_equal(lookup[left],lookup[right])
            visible = left!=tr
            count.update(frames=1,pixels=size,visible_pixels=int(visible.sum()),changed_visible_indices=int(np.count_nonzero((left!=right)&visible)))
        assert old.read()==new.read(),(a["resref"],"cycles")
    return count


def check_changed_frames(family):
    started,counts = time.perf_counter(),Counter()
    for path in sorted(family.glob("*/runs/reboutcx-p12-cache86-v1/manifest.json")):
        new = read_json(path)
        old = read_json(path.parent.with_name("reboutcx-p11-q32-group86-v1")/"manifest.json")
        for a,b in zip(old["resources"],new["resources"],strict=True):
            selected = {i for i,(fa,fb) in enumerate(zip(a["frame_records"],b["frame_records"],strict=True))
                        if fa["indices_sha256"]!=fb["indices_sha256"]}
            if selected:
                counts.update(compare_registry(a,b,new["semantic_classes"],selected))
    assert counts["frames"]==31,counts
    report = {**counts,"alpha_classes_geometry_cycles_and_source_representatives_equal":True,
        "selection":"all 31 frame occurrences whose index hash differs from P11",
        "seconds":time.perf_counter()-started,"production_runs":0,"temporary_files":0}
    output = family/"family-runs/complete-reboutcx-p12-v1/measurements/changed-frames-contract-v1.json"
    with output.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(report,stream,indent=2)
        stream.write("\n")
    return report


def measure(family,session):
    started = time.perf_counter()
    measurement_dir = family/"family-runs/complete-reboutcx-p12-v1/measurements"
    baseline = read_json(measurement_dir/"baseline-before-p12-v1.json")
    previous = read_json(family/"family-runs/complete-reboutcx-p11-v1/measurements/throughput-p11-v1.json")
    events = [json.loads(s) for s in session.read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"]=="complete" and not any(e["event"]=="failed" for e in events)
    result = events[-1]
    verified = {e["job"]:e for e in events if e["event"]=="verified"}
    assert len(verified)==result["completed"]==65
    assert all(not e["existing"] for e in verified.values())
    assert result["source_frames"]==180494 and result["logical_model_frames"]==146066
    queue = resolve_path_reference(baseline["queue"])
    assert sha256_file(queue)==events[0]["queue_sha256"]
    assert {m["job"] for m in read_json(queue)["members"]}==set(verified)
    stages, sample, members = Counter(),Counter(),[]
    changed = source_frames = logical = actual = slots = fillers = 0
    code = {}
    for job,evidence in verified.items():
        path = resolve_path_reference(read_json(resolve_path_reference(job))["paths"]["run_dir"])/"manifest.json"
        assert sha256_file(path)==evidence["manifest_sha256"]
        new = read_json(path)
        old = read_json(path.parent.with_name("reboutcx-p11-q32-group86-v1")/"manifest.json")
        for key in ("source_manifest_sha256","animation_id","runtime_profile","layer","model_sha256","target_scale","semantic_classes","palette_reference"):
            assert new[key]==old[key],(job,key)
        assert [r["resref"] for r in old["resources"]]==[r["resref"] for r in new["resources"]]
        old_resources = {r["resref"]:r for r in old["resources"]}
        new_resources = {r["resref"]:r for r in new["resources"]}
        for name,a in old_resources.items():
            b = new_resources[name]
            assert a["reused_render_from"]==b["reused_render_from"]
            for fa,fb in zip(a["frame_records"],b["frame_records"],strict=True):
                for key in ("source_frame","width","height","center_x","center_y","transparent_index","guide_sha256","model_bypassed"):
                    assert fa[key]==fb[key],(job,name,key)
                changed += fa["indices_sha256"]!=fb["indices_sha256"]
        canonical = [r for r in old["resources"] if not r["reused_render_from"]]
        largest = max(canonical,key=lambda r:sum(f["width"]*f["height"] for f in r["frame_records"]))
        for name in dict.fromkeys([canonical[0]["resref"],largest["resref"]]):
            sample.update(compare_registry(old_resources[name],new_resources[name],new["semantic_classes"]))
        coverage = new["coverage"]
        source_frames += coverage["frames"]
        logical += coverage["logical_model_frames"]
        actual += coverage["unique_model_frames"]
        slots += coverage["gpu_slots"]
        fillers += coverage["gpu_filler_frames"]
        stages.update(new["timing_seconds"])
        for entry in new["code"].values():
            code[(entry["path"],entry["sha256"])]=None
        members.append({"job":job,"manifest":relative(path),"manifest_sha256":evidence["manifest_sha256"],
            "verified_at_seconds":evidence["elapsed_seconds"],"source_frames":coverage["frames"],
            "logical_model_frames":coverage["logical_model_frames"],"computed_model_frames":coverage["unique_model_frames"]})
    assert (source_frames,logical,actual,slots,fillers)==(result["source_frames"],result["logical_model_frames"],result["new_model_frames"],result["gpu_slots"],result["gpu_filler_frames"])
    assert slots==actual+fillers
    for path,expected in baseline["prior_manifests"].items():
        assert sha256_file(resolve_path_reference(path))==expected,path
    for path,expected in code:
        assert sha256_file(resolve_path_reference(path))==expected,path
    assert not list(family.glob("*/runs/.reboutcx-p12-cache86-v1.tmp-*"))
    wall = result["wall_through_verification_seconds"]
    p11 = previous["p11_wall_seconds"]
    report = {"schema":"reboutcx-family-throughput-measurement-v3","animation_id":"0x5211",
        "status":"65-components-produced-and-technically-verified-pending-human-review",
        "scope":"one-family-only; no-derived-catalog-install-release","implementation_commit":baseline["commit"],
        "components":65,"source_frames":source_frames,"logical_model_frames":logical,"computed_model_frames":actual,
        "avoided_model_frames":logical-actual,"avoided_model_frames_percent":(logical-actual)/logical*100,
        "changed_frame_index_hashes_vs_p11":changed,"p11_wall_seconds":p11,"p12_wall_seconds":wall,
        "speedup_vs_p11":p11/wall,"throughput_gain_vs_p11_percent":(p11/wall-1)*100,
        "time_reduction_vs_p11_percent":(1-wall/p11)*100,"seconds_saved_vs_p11":p11-wall,
        "p11_logical_model_frames_per_second":logical/p11,"p12_logical_model_frames_per_second":logical/wall,
        "gpu_slots":slots,"gpu_filler_frames":fillers,"cache":result["cache"],"cache_plan":result["cache_plan"],
        "model_load_seconds_once":result["model_load_seconds_once"],"peak_reserved_resource_bytes":result["peak_reserved_resource_bytes"],
        "stage_seconds_sums":dict(stages),"parameters":baseline["parameters"],"queue":relative(queue),
        "queue_sha256":sha256_file(queue),"session":relative(session),"session_sha256":sha256_file(session),
        "comparability":{"source_model_palette_classes_coverage_and_all_guides_equal":True,
            "previous_manifests_unchanged":len(baseline["prior_manifests"]),"p12_pinned_code_hashes_unchanged":True,
            "clocks":"perf_counter through last independent verification, P12 admission included; queue preparation/sorting excluded",
            "limitations":"one family against historical P11, no repeated A/B; concurrent stage sums are not additive; fixed N=86 may change numerical results"},
        "sample_contract_comparison":{**sample,"changed_visible_indices_percent":100*sample["changed_visible_indices"]/sample["visible_pixels"],
            "alpha_classes_geometry_cycles_and_source_representatives_equal":True,
            "selection":"first canonical and largest-native-pixel canonical per component; 8 evenly spaced frames each"},
        "members":members,"measurement_seconds":time.perf_counter()-started}
    output = measurement_dir/"throughput-p12-v1.json"
    with output.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(report,stream,indent=2)
        stream.write("\n")
    return {k:v for k,v in report.items() if k not in ("members","comparability")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family",type=Path)
    parser.add_argument("session",type=Path,nargs="?")
    parser.add_argument("--changed-frames",action="store_true")
    args = parser.parse_args()
    if not args.changed_frames and args.session is None:
        parser.error("session is required unless --changed-frames is selected")
    print(json.dumps(check_changed_frames(args.family) if args.changed_frames else measure(args.family,args.session)))
