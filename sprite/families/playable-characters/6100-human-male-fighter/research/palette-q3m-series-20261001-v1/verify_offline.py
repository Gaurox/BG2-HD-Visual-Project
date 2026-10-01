"""Verify all 0x6100 source geometry, I/F roundtrips and native 18-palette decodes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

RUN = Path(__file__).resolve().parent
ROOT = next(p for p in RUN.parents if (p / "pipeline/scripts/palette_playable.py").is_file())
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import numpy as np
from palette_complete import Oracle
from palette_oracle import read_bam_p8
from palette_p2 import golden
from palette_work_plan import WorkPlan, ResultCache, write_json
import palette_registry as v6
import run_creature_sprite_x2 as registry


def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=int, choices=(2, 4), required=True)
    parser.add_argument("--pack", type=Path, required=True)
    args = parser.parse_args()
    scale, pack = args.scale, args.pack.resolve()
    proof_path = RUN / f"x{scale}-verification.json"
    assert not proof_path.exists(), "Final proof is immutable"
    plan = WorkPlan().validate_sources()
    cache = ResultCache(plan, scale)
    control = json.loads((RUN / "native-control.json").read_text())
    executable = ROOT / control["executable"]
    assert sha(executable) == control["executable_sha256"]
    assert sha(ROOT / "engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp") == control["engine_source_sha256"]
    catalog = pack / "CreatureSprites-XN.catalog"
    index = registry.read_sealed_catalog_index(catalog, sha(catalog))
    assert index["scale"] == scale and [r["animation_id"] for r in index["animations"]] == ["0x6100"]
    resources = plan.resources(["0x6100"])
    assert len(resources) == 656 and index["total_resources"] == 656 and index["total_frames"] == 180337
    assert {r["resref"] for r in resources} == {r["resref"] for r in index["directory"]}
    shards = {d["resref"]: index["shards"][d["shard_index"]] for d in index["directory"]}
    palettes = golden()[0]
    assert palettes.shape == (18, 256, 4)
    complete = Oracle(RUN / f"x{scale}-oracles", palettes)
    working = Oracle(RUN / f"x{scale}-working-set-oracles", palettes)
    rows, first, decoded_pixels = [], None, 0
    started = time.monotonic()
    try:
        for n, resource in enumerate(resources, 1):
            source = ROOT / resource["canonical_path"]
            assert sha(source) == resource["canonical_sha256"]
            bam = read_bam_p8(source.read_bytes())
            materialized = plan.materialize(resource, cache)
            assert len(bam["frames"]) == len(materialized["frames"])
            assert materialized["cycles"] == [c["frame_indices"] for c in bam["cycles"]]
            shard = shards[resource["resref"]]
            leaf = pack / Path(shard["registry"]).name
            info = v6.inspect(leaf, include_frames=True)
            assert info["version"] == 6 and info["scale"] == scale
            assert info["sha256"].lower() == shard["sha256"].lower()
            got = info["frame_data"][0]
            assert got["source_sha256"] == resource["canonical_sha256"] and got["cycles"] == materialized["cycles"]
            assert len(got["frames"]) == len(bam["frames"])
            for original, expected, actual in zip(bam["frames"], materialized["frames"], got["frames"], strict=True):
                h, w = original["indices"].shape
                geometry = (w, h, original["center_x"], original["center_y"], bam["transparent"])
                assert expected["geometry"] == geometry == actual["geometry"]
                reps = np.full(256, 65535, np.uint16)
                values, offsets = np.unique(original["indices"], return_index=True)
                reps[values] = offsets
                assert np.array_equal(reps, expected["representatives"]) and np.array_equal(reps, actual["representatives"])
                assert expected["I"].tobytes() == actual["I"]
                assert (expected["F"].tobytes() if np.any(expected["F"]) else b"") == actual["F"]
                assert expected["dep"].tobytes() == actual["dep"]
                decoded_pixels += expected["I"].size
            complete.append(materialized)
            head = dict(materialized, frames=materialized["frames"][:1])
            working.append(head)
            if first is None:
                first = head
            rows.append(dict(resref=resource["resref"], source_sha256=resource["canonical_sha256"],
                             frames=len(got["frames"]), registry_bytes=info["registry_bytes"],
                             registry_sha256=info["sha256"].lower(), roundtrip_identical=True))
            print(json.dumps(dict(phase="source-and-plane-roundtrip", scale=scale, resources=n, total=656)), flush=True)
        working.append(first)
    finally:
        complete.close_chunk()
        working.close_chunk()
        plan.close()
    results = []
    for group, oracle in (("complete", complete), ("working-set", working)):
        for n, item in enumerate(oracle.records):
            path = oracle.directory / item["path"]
            assert sha(path) == item["sha256"]
            process = subprocess.run([str(executable), "--pack-complete", str(pack), str(path)], cwd=ROOT, capture_output=True, text=True)
            log = RUN / "captures" / f"x{scale}-{group}-{n}-native.log"
            assert not log.exists()
            log.write_text(process.stdout + process.stderr, encoding="utf-8")
            if process.returncode:
                raise RuntimeError(process.stdout + process.stderr)
            metrics = json.loads(process.stdout.splitlines()[-1])
            assert metrics["pack_frames"] == item["frames"] and metrics["palettes"] == 18
            assert metrics["peak_resident_I_F_bytes"] <= 134217728 and metrics["peak_metadata_bytes"] <= 134217728
            results.append(dict(group=group, oracle=item, native_test=metrics, log_sha256=sha(log)))
            print(json.dumps(dict(phase="native-reference-decode", scale=scale, group=group, **metrics)), flush=True)
    full = [r["native_test"] for r in results if r["group"] == "complete"]
    assert sum(r["pack_frames"] for r in full) == 180337
    assert sum(r["decoded_pixels"] for r in full) == decoded_pixels * 18
    assert sum(r["native_test"]["pack_frames"] for r in results if r["group"] == "working-set") == 657
    proof = dict(schema="bg2-playable-q3m-series-offline-verification-v1", status="passed-offline-ready-for-manual-game",
                 animation_id="0x6100", scale=scale, method="Q3m", k=6, boundary_mixing=False, dithering=False,
                 resources=rows, resource_count=656, frames=180337, decoded_pixels=decoded_pixels,
                 complete_decoded_pixel_comparisons=decoded_pixels * 18,
                 reference_decodings=sum(r["native_test"]["pack_frames"] for r in results) * 18,
                 native_pack_tests=results, catalog=pack.relative_to(ROOT).as_posix(), catalog_sha256=sha(catalog),
                 source_plan_sha256=plan.descriptor["sha256"], result_namespace=cache.namespace,
                 native_control_sha256=sha(RUN / "native-control.json"), verification_script_sha256=sha(Path(__file__)),
                 elapsed_seconds=time.monotonic() - started, ingame_validated=False, visual_qa_accepted=False,
                 limitations=["Oracle alpha is synthetic; live palettes, effects and GL require ingame QA."])
    write_json(proof_path, proof)
    print(json.dumps(dict(phase="offline-verified", scale=scale, frames=180337, decoded_pixels=decoded_pixels)), flush=True)


if __name__ == "__main__":
    main()
