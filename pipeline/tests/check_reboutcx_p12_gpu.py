"""Two real inputs: cold/hot cache, fixed-batch slot/neighbour invariance, no runs."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"pipeline/scripts"))
from reboutcx_full import read_json,resolve_path_reference,reconstruct_rgba,sha256_array,sha256_file
from reboutcx_batch import load_palette_profiles
from reboutcx_quantize import semantic_classes_for_job
from reboutcx_cache_p12 import context_key
from reboutcx_runtime_p12 import Runtime,GroupWindow,process_group
from run_creature_sprite_x2 import SourceFrame,decode_bam


def check(family):
    started = time.perf_counter()
    samples = read_json(family/"family-runs/complete-reboutcx-p11-v1/measurements/padding-probe-v1.json")["cases"]
    cases = []
    with Runtime(pre_workers=1,post_workers=1,process_pools=False) as runtime:
        for sample in (samples[1],samples[0]):
            job = read_json(resolve_path_reference(sample["job"]))
            source = resolve_path_reference(job["paths"]["source_manifest"])
            bam = next(b for b in read_json(source)["bams"] if b["name"].upper()==sample["resref"])
            decoded,palette,_ = decode_bam((source.parent/bam["canonical_bam"]).read_bytes())
            indices,cx,cy,tr = decoded[sample["frame"]]
            h,w = indices.shape
            frame = SourceFrame(bam["name"],sample["frame"],w,h,cx,cy,tr,indices,palette,
                                reconstruct_rgba(indices,palette,tr).tobytes())
            classes,_ = semantic_classes_for_job(job)
            profiles,_ = load_palette_profiles(job)
            reference = profiles[0]["palette"]
            scalepix = resolve_path_reference(job["paths"]["scalepix"])
            context = context_key(job,classes,sha256_file(scalepix))
            runtime.model_info(resolve_path_reference(job["paths"]["reboutcx_model"]),device="cuda:0",fp16=True)

            def transform(f):
                resources = [{"source":{"name":f.resref},"frames":[f]}]
                window = GroupWindow(runtime,scalepix=scalepix,node=job["tools"].get("node","node"),
                    marker=job["null_frame_marker"],palette=reference,classes=classes,cache_context=context)
                start = time.perf_counter()
                try:
                    states,pre = window.get(resources)
                    timing = process_group(runtime,resources,states,fp16=True,classes=classes,required_qa={f.resref:{f.index}})
                    return states[f.resref][f.index],{**pre,**timing},time.perf_counter()-start
                finally:
                    window.close()

            runtime.cache.clear()
            cold,cold_t,cold_seconds = transform(frame)
            other = copy.deepcopy(frame)
            other.resref,other.index,other.center_x = "CACHEHOT",0,cx+7
            hot,hot_t,hot_seconds = transform(other)
            np.testing.assert_array_equal(cold["quantized"],hot["quantized"])
            np.testing.assert_array_equal(cold["target_rgb"],hot["target_rgb"])
            assert hot_t.get("model_frames",0)==0 and hot["frame"].center_x==cx+7
            runtime.cache.clear()
            again,_,_ = transform(other)
            np.testing.assert_array_equal(cold["quantized"],again["quantized"])
            np.testing.assert_array_equal(cold["target_rgb"],again["target_rgb"])
            from reboutcx_batch import prepare_inference_rgb
            rgb = prepare_inference_rgb(frame,reference)
            canvas = ((h+31)//32*32,(w+31)//32*32)
            baseline,_ = runtime.infer([rgb],canvas,True).result()
            zero = np.zeros((1,1,3),dtype=np.uint8)
            neighbour = np.full((h,w,3),37,dtype=np.uint8)
            for background in (zero,neighbour):
                shifted,_ = runtime.infer([background]*85+[rgb],canvas,True).result()
                np.testing.assert_array_equal(baseline[0],shifted[85])
                del shifted
            lookup = np.full(256,-1,dtype=np.int16)
            for number,values in enumerate(classes.values()):
                lookup[values] = number
            np.testing.assert_array_equal(cold["quantized"]==tr,cold["guide"]==tr)
            np.testing.assert_array_equal(lookup[cold["quantized"]],lookup[cold["guide"]])
            assert set(np.unique(cold["quantized"])) <= set(np.unique(indices))
            previous = read_json(resolve_path_reference(job["paths"]["run_dir"])/"manifest.json")
            evidence = next(r for r in previous["resources"] if r["resref"]==frame.resref)["frame_records"][frame.index]
            assert sha256_array(cold["guide"])==evidence["guide_sha256"]
            cases.append({"resref":frame.resref,"frame":frame.index,"canvas":canvas,
                "cold_seconds":cold_seconds,"hot_seconds":hot_seconds,"cold_real_model_frames":cold_t["model_frames"],
                "cold_gpu_slots":cold_t["gpu_slots"],"hot_model_frames":hot_t.get("model_frames",0),
                "cold_hot_and_recold_exact":True,"slot_0_vs_85_and_neighbours_exact":True,
                "alpha_classes_and_source_indices_preserved":True,"p11_guide_unchanged":True})
    return {"status":"p12-gpu-cache-and-fixed-batch-check-passed","cases":cases,
            "seconds":time.perf_counter()-started,"production_runs":0,"temporary_files":0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family",type=Path)
    print(json.dumps(check(parser.parse_args().family)))
