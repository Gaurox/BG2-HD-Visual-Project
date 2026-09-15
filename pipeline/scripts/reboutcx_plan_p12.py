"""Read-only admission pass for a P12 session; counts remain in RAM only."""
from __future__ import annotations
from collections import Counter
import hashlib
import time
import numpy as np
from reboutcx_full import (read_json, resolve_path_reference, sha256_file,
    semantic_classes_for_job, load_palette_profiles, is_null_frame)
from run_creature_sprite_x2 import SourceFrame, decode_bam
from reboutcx_cache_p12 import frame_key, context_key


def plan_cache(jobs):
    started = time.perf_counter()
    counts = Counter()
    resources = frames_count = 0
    tool_hashes = {}
    for job_path in jobs:
        job = read_json(job_path)
        output = resolve_path_reference(job["paths"]["run_dir"])
        if (output / "manifest.json").is_file():
            continue
        source = resolve_path_reference(job["paths"]["source_manifest"], required=True)
        if sha256_file(source) != job["source_manifest_sha256"]:
            raise RuntimeError("source manifest changed before P12 cache planning")
        source_manifest = read_json(source)
        if [b["name"].upper() for b in source_manifest["bams"]] != [b["name"].upper() for b in job["source_inventory"]]:
            raise RuntimeError("P12 cache source inventory differs")
        classes, _ = semantic_classes_for_job(job)
        profiles, _ = load_palette_profiles(job)
        palette = profiles[0]["palette"] if profiles else None
        scalepix = resolve_path_reference(job["paths"]["scalepix"], required=True)
        if scalepix not in tool_hashes:
            tool_hashes[scalepix] = sha256_file(scalepix)
        context = context_key(job, classes, tool_hashes[scalepix])
        seen = set()
        for bam in source_manifest["bams"]:
            path = source.parent / bam["canonical_bam"]
            raw = path.read_bytes()
            identity = (hashlib.sha256(raw).hexdigest().upper(), sha256_file(source.parent / bam["source"]))
            if identity in seen:
                continue
            seen.add(identity)
            decoded, native_palette, _tr = decode_bam(raw)
            resources += 1
            for index, (indices,cx,cy,tr) in enumerate(decoded):
                h,w = indices.shape
                if not (1 <= w <= 4096 and 1 <= h <= 4096):
                    raise RuntimeError("invalid frame dimensions in P12 cache plan")
                rgba = np.empty((h,w,4), dtype=np.uint8)
                rgba[:,:,:3] = native_palette[indices]
                rgba[:,:,3] = np.where(indices==tr,0,255).astype(np.uint8)
                frame = SourceFrame(bam["name"], index,w,h,cx,cy,tr,indices,native_palette,rgba.tobytes())
                if not is_null_frame(frame,int(job["null_frame_marker"])):
                    counts[frame_key(frame,palette,context)] += 1
                    frames_count += 1
    repeated = {key:n for key,n in counts.items() if n > 1}
    return repeated, {"seconds":time.perf_counter()-started,"resources":resources,"cache_eligible_frames":frames_count,
        "unique_frames":len(counts),"repeated_keys":len(repeated),"duplicate_frames":sum(n-1 for n in repeated.values()),
        "count_storage":"session-RAM-only"}
