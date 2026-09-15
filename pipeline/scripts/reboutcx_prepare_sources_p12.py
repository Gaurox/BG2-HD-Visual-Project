"""Prepare new P12 jobs from sealed xBR sources; no P8 writes or GPU reference run."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import time
import numpy as np
from reboutcx_full import read_json,relative,resolve_path_reference,sha256_file
from reboutcx_full_p12 import RUN_ID,BATCH_CONTRACT,validate_job
from reboutcx_playable_p12 import QUEUE_SCHEMA,load_queue
from reboutcx_character_family import load_template,member_layer,parent_context_for_family
from reboutcx_catalog import animation_component_resrefs
from run_creature_sprite_x2 import decode_bam


def write_new(path,value):
    if path.exists():
        if read_json(path)!=value:
            raise RuntimeError(f"existing preparation differs: {path}")
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(value,stream,indent=2)
        stream.write("\n")


def prepare(family_job_path,parent=None):
    started = time.perf_counter()
    family = read_json(family_job_path)
    animation = family["animation_id"]
    source_path = resolve_path_reference(family["source_family_job"],required=True)
    if sha256_file(source_path)!=family["source_family_job_sha256"]:
        raise RuntimeError("source family job changed")
    source = read_json(source_path)
    root = source_path.parents[3]
    if source["animation"]["id"]!=animation or root.name.split('-')[0].lower()!=animation[2:].lower():
        raise RuntimeError("source family identity differs")
    template_path,template = load_template(family)
    parent = parent if parent is not None else parent_context_for_family(family)
    if sha256_file(resolve_path_reference(family["parent_catalog_pointer"]))!=family["parent_catalog_pointer_sha256"]:
        raise RuntimeError("source parent pointer changed")
    if parent["pointer"]["generation_id"]!=family["parent"]["generation_id"]:
        raise RuntimeError("source parent generation differs")
    by_resrefs = {frozenset(names):index for index,names in animation_component_resrefs(parent,animation).items()}
    if len(by_resrefs)!=len(source["members"]):
        raise RuntimeError("ambiguous source component membership")
    records,seen = [],set()
    for reference in source["members"]:
        member_path = resolve_path_reference(reference,required=True)
        member = read_json(member_path)
        if member["animation"]["id"]!=animation:
            raise RuntimeError("component has another animation")
        layer,armor,item = member_layer(member)
        prefix = str(member["animation"]["bam_prefix"]).upper()
        source_manifest = resolve_path_reference(member["paths"]["source_dir"],required=True)/"manifest.json"
        manifest = read_json(source_manifest)
        if (manifest["animation_id"]!=animation or manifest["runtime_profile"]!="character-bg2ee-2.7.3.0"
                or manifest["layer"]["kind"]!=layer or manifest["bam_prefix"].upper()!=prefix):
            raise RuntimeError("source manifest contract differs")
        inventory = [{"name":b["name"].upper()} for b in manifest["bams"]]
        index = by_resrefs.get(frozenset(b["name"] for b in inventory))
        if index is None or index in seen:
            raise RuntimeError("source RESREF set missing or duplicated in parent")
        seen.add(index)
        witness = None
        for bam in manifest["bams"]:
            bam_path = source_manifest.parent/bam["canonical_bam"]
            if sha256_file(bam_path)!=bam["canonical_bam_sha256"]:
                raise RuntimeError("witness BAM changed")
            decoded,_palette,_tr = decode_bam(bam_path.read_bytes())
            for frame,(indices,_cx,_cy,tr) in enumerate(decoded):
                marker = indices.size==1 and int(indices.flat[0])==template["null_frame_marker"]
                if not marker and np.any(indices!=tr):
                    witness = (bam["name"].upper(),frame)
                    break
            if witness is not None:
                break
        if witness is None:
            raise RuntimeError("component has no visible comparison frame")
        component_root = source_manifest.parent.parent
        job = {"schema":template["schema"],"job_id":f"character-{animation[2:].lower()}-{component_root.name}-{prefix.lower()}-{RUN_ID}",
            "installable":False,"scope":"full-animation","animation_id":animation,"runtime_profile":"character-bg2ee-2.7.3.0",
            "layer":layer,"source_inventory":inventory,"source_manifest_sha256":sha256_file(source_manifest),
            "paths":{"source_manifest":relative(source_manifest),"run_dir":relative(component_root/"runs"/RUN_ID),
                **{k:template["paths"][k] for k in ("chainner_python","reboutcx_model","scalepix")}},
            **{k:copy.deepcopy(template[k]) for k in ("tools","reboutcx","semantic_classes_id","null_frame_marker","palette_reference")},
            "reboutcx_batch":copy.deepcopy(BATCH_CONTRACT),
            "p12_source_job":{"path":relative(member_path),"sha256":sha256_file(member_path),"kind":"sealed-xbr-source-job"},
            "preparation":{"contract_template":relative(template_path),"contract_template_sha256":sha256_file(template_path),
                "source_family_job":relative(source_path),"source_family_job_sha256":sha256_file(source_path),
                "script":relative(Path(__file__)),"script_sha256":sha256_file(Path(__file__)),
                "reference_inference":"not-required-by-P12; comparison frame selected from native source"},
            "qa":{"background":"dark-light-green-checkerboard-quadrants","groups":[{"name":prefix.lower()+"-reference",
                "resref":witness[0],"frames":[witness[1]],"duration_ms":400}]}}
        job["armor_code" if layer=="body" else "item_resref"] = armor if layer=="body" else item
        validate_job(job)
        path = component_root/"jobs"/(RUN_ID+".json")
        if resolve_path_reference(job["paths"]["run_dir"]).exists():
            raise RuntimeError("new-family preparation requires new P12 output directories")
        write_new(path,job)
        records.append({"bam_prefix":prefix,"component_index":index,"job":relative(path),"sha256":sha256_file(path),
            "source_frames":int(manifest["total_frames"]),"source_manifest":relative(source_manifest),
            "source_manifest_sha256":sha256_file(source_manifest)})
    destination = root/"family-runs/complete-reboutcx-p12-v1"
    queue = destination/"jobs"/(root.name+"-p12-v1.json")
    write_new(queue,{"schema":QUEUE_SCHEMA,"installable":False,"members":[{"job":r["job"],"sha256":r["sha256"]} for r in records]})
    assert len(load_queue(queue))==len(records)
    prepared = {"schema":"bg2-upscale-reboutcx-p12-source-preparation-v1","animation_id":animation,"family":relative(root),
        "queue":relative(queue),"queue_sha256":sha256_file(queue),"parent_generation":parent["pointer"]["generation_id"],
        "source_family_job":relative(source_path),"source_family_job_sha256":sha256_file(source_path),
        "components":len(records),"source_frames":sum(r["source_frames"] for r in records),"members":records}
    write_new(destination/"prepared.json",prepared)
    return {k:v for k,v in prepared.items() if k!="members"}|{"prepare_seconds":time.perf_counter()-started}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family_job",type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.family_job)))
