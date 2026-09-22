"""AR3021-only CPU preparation/assembly; GPU dispatch and installation stay external.

prepare: copy immutable x1 inputs, record three SeedVR none commands, or reuse
         an existing preparation without changing it.
assemble: combine new SeedVR RGB with accepted native-frame Spline4 alpha;
          produce an AreaTest-compatible v2 pack using Native playback and
          straight RGB (AR3021 ARE flags 0x1141 do not include Blended bit 1).
No animation index/selection/lock, source asset, game or runtime is modified.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pipeline/scripts").is_dir())
LOCAL: Path
SOURCE = ROOT / "animations/batches/ar3021-illithids-seedvr7b-lab-x4-20260911"
ALPHA_PACK = ROOT / "animations/packs-par-zone/ar3021-illithids-apo8-x4-30fps-v2-spline-fit1-feather4-20260911/AR3021"
ALPHA_MANIFEST_HASH = "ba54341f94d942017d5658edce6ded8ebfa9791e0fce2197da9478bee311b593"
RESREFS = ("AM3021D", "AM3021E", "AM3021F")
PLAN: Path
VANILLA: Path
sys.path.insert(0, str(ROOT / "pipeline/scripts"))

import numpy as np
import run_animation_upscale_30fps_v2 as runtime
import bg2lib


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def check_alpha_source():
    require(digest(ALPHA_PACK / "manifest.json") == ALPHA_MANIFEST_HASH,
            "accepted Spline4 alpha manifest changed")
    manifest = load(ALPHA_PACK / "manifest.json")
    resources = {r["resref"]: r for r in manifest["resources"]}
    require(set(resources) == set(RESREFS), "AR3021 alpha resource set changed")
    return resources


def verify_vanilla_sources():
    """Compare canonical decompressed BAM bytes to the named vanilla KEY/BIF."""
    previous_game, previous_key, previous_cache = bg2lib.GAME_DIR, bg2lib.KEY_PATH, bg2lib._bif_cache
    try:
        bg2lib.GAME_DIR = str(VANILLA)
        bg2lib.KEY_PATH = str(VANILLA / "chitin.key")
        bg2lib._bif_cache = {}
        bifs, entries = bg2lib.load_key()
        lookup = {(name.upper(), kind): locator for name, kind, locator in entries}
        result = {"vanilla_root": str(VANILLA), "resources": []}
        for resref in RESREFS:
            encoded, archive = bg2lib.resolve_resource(bifs, lookup[resref, 0x3E8])
            if encoded[:8] == b"BAMCV1  ":
                decoded = zlib.decompress(encoded[12:])
                require(len(decoded) == struct.unpack_from("<I", encoded, 8)[0], "BAMC size mismatch")
            else:
                decoded = encoded
            canonical = ROOT / "animations/ressources" / resref / "source.bam"
            require(decoded == canonical.read_bytes(), f"canonical BAM differs from vanilla: {resref}")
            result["resources"].append({"resref": resref, "archive": archive,
                                        "encoded_sha256": hashlib.sha256(encoded).hexdigest(),
                                        "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
                                        "canonical_source": str(canonical), "canonical_byte_identical": True})
        are, archive = bg2lib.resolve_resource(bifs, lookup["AR3021", 0x3F2])
        count, offset = struct.unpack_from("<II", are, 0xAC)
        occurrences = []
        for index in range(count):
            position = offset + index * 76
            resref = are[position + 0x28:position + 0x30].split(b"\0")[0].decode("ascii")
            flags = struct.unpack_from("<I", are, position + 0x34)[0]
            require(resref in RESREFS and flags == 0x1141 and not flags & 2,
                    f"AR3021 occurrence requires a different RGB policy: {resref}/{flags:#x}")
            occurrences.append({"resref": resref, "flags": f"0x{flags:08X}", "blended_bit_1": False})
        require(len(occurrences) == 3 and {o["resref"] for o in occurrences} == set(RESREFS),
                "AR3021 occurrence set changed")
        result["are"] = {"archive": archive, "sha256": hashlib.sha256(are).hexdigest(),
                          "occurrences": occurrences}
        return result
    finally:
        bg2lib.GAME_DIR, bg2lib.KEY_PATH, bg2lib._bif_cache = previous_game, previous_key, previous_cache


def reuse_preparation():
    plan = load(PLAN)
    require(plan.get("schema") == "bg2-liquid-local-ar3021-preparation-v1" and plan.get("area") == "AR3021",
            "incompatible existing preparation")
    require({r["resref"] for r in plan["resources"]} == set(RESREFS), "foreign existing resource")
    check_alpha_source()
    verify_vanilla_sources()
    for record in plan["resources"]:
        frames_manifest = Path(record["frame_manifest"])
        frames_manifest.resolve().relative_to(LOCAL)
        require(digest(frames_manifest) == record["frame_manifest_sha256"], "existing frame manifest changed")
        for frame in load(frames_manifest)["frames"]:
            for channel in ("rgb", "alpha", "rgba"):
                require(digest(frames_manifest.parent / channel / frame["file"]) == frame[f"{channel}_sha256"],
                        "existing frame bytes changed")
        for donor in record["alpha_donors"]:
            require(digest(ALPHA_PACK / donor["donor_asset"]) == donor["donor_sha256"], "alpha donor changed")
    require(load(LOCAL / "gpu-jobs.json") == plan["gpu_jobs"], "recorded GPU jobs changed")
    print(json.dumps({"status": "reused-unchanged", "preparation": str(PLAN), "gpu_dispatched": False,
                      "assembly_rgb_policy": "straight RGB; zero only where alpha==0"}))


def prepare():
    if PLAN.exists():
        reuse_preparation()
        return
    vanilla_evidence = verify_vanilla_sources()
    donors = check_alpha_source()
    source_run = load(SOURCE / "manifest.json")
    sources = {r["resref"]: r for r in source_run["resources"]}
    records, jobs = [], []
    for resref in RESREFS:
        source = sources[resref]
        original = SOURCE / source["frames_x1"]
        require(digest(original / "manifest.json") == source["frame_manifest_sha256"],
                f"x1 frame manifest changed: {resref}")
        require(digest(Path(source["canonical_source"])) == source["source_sha256"],
                f"BAM source changed: {resref}")
        frame_manifest = load(original / "manifest.json")
        require(frame_manifest["frame_count"] == 10 and
                frame_manifest["cycles"][0]["frame_indices"] == list(range(10)),
                f"unexpected native cycle: {resref}")
        frames_dir = LOCAL / "resources" / resref / "01_frames_x1"
        require(not frames_dir.exists(), f"input destination already exists: {frames_dir}")
        frame_checks = []
        for frame, donor in zip(frame_manifest["frames"], donors[resref]["frames"][:10], strict=True):
            index = int(frame["frame"])
            require(donor["frame"] == index and donor["logical_size_x1"] == frame["source_size"]
                    and donor["centre_x1"] == frame["centre"], f"native alpha geometry: {resref}/{index}")
            for channel in ("rgb", "alpha", "rgba"):
                file = original / channel / frame["file"]
                require(digest(file) == frame[f"{channel}_sha256"],
                        f"x1 {channel} changed: {resref}/{index}")
            require(digest(ALPHA_PACK / donor["asset"]) == donor["sha256"],
                    f"accepted alpha donor changed: {resref}/{index}")
            frame_checks.append({"frame": index, "donor_asset": donor["asset"],
                                 "donor_sha256": donor["sha256"]})
        shutil.copytree(original, frames_dir)
        upscale = LOCAL / "resources" / resref / "02_seedvr_none_x4"
        argv = [sys.executable, "-B", str(ROOT / "pipeline/scripts/upscale_animation_frames.py"),
                str(frames_dir / "rgb"), str(frames_dir / "alpha"), str(upscale),
                "--frame-manifest", str(frames_dir / "manifest.json"), "--scale", "4",
                "--color-correction-method", "none", "--resume"]
        jobs.append({"resref": resref, "argv": argv, "frame_count": 10})
        records.append({"resref": resref, "source_bam_sha256": source["source_sha256"],
                        "frame_manifest": str(frames_dir / "manifest.json"),
                        "frame_manifest_sha256": source["frame_manifest_sha256"],
                        "upscale": str(upscale), "alpha_donors": frame_checks})
    plan = {"schema": "bg2-liquid-local-ar3021-preparation-v1", "status": "prepared-not-rendered",
            "area": "AR3021", "created_utc": datetime.now(timezone.utc).isoformat(),
            "recipe": "new SeedVR7B none x4 straight RGB; accepted native-frame Spline4 alpha; RGB zero only at alpha0; native BAM cycle",
            "vanilla_evidence": vanilla_evidence,
            "alpha_source_pack": str(ALPHA_PACK), "alpha_source_manifest_sha256": ALPHA_MANIFEST_HASH,
            "resources": records, "gpu_jobs": jobs,
            "candidate": str(LOCAL / "candidate/AR3021"),
            "installation": "external AreaTest install_area_pack API; no record_lock call"}
    save_new(PLAN, plan)
    save_new(LOCAL / "gpu-jobs.json", jobs)
    print(json.dumps({"status": "prepared", "gpu_jobs": str(LOCAL / "gpu-jobs.json"),
                      "frames": 30, "gpu_dispatched": False}))


def assemble():
    plan = load(PLAN)
    vanilla_evidence = verify_vanilla_sources()
    donors = check_alpha_source()
    target = LOCAL / "candidate/AR3021"
    require(not target.exists(), "candidate already exists; immutable output requires a new run")
    prepared = []
    provenance = []
    for record in plan["resources"]:
        resref = record["resref"]
        require(resref in RESREFS, "foreign resource")
        upscale = Path(record["upscale"])
        manifest = load(upscale / "manifest.json")
        require(manifest.get("schema") == "bg2-upscale-animation-frames-v1" and
                manifest.get("status") == "completed" and manifest.get("scale") == 4,
                f"SeedVR output incomplete: {resref}")
        require(manifest.get("parameters", {}).get("color_correction_method") == "none" and
                manifest.get("parameters", {}).get("model") == "seedvr2_7b_int8_convrot.safetensors",
                f"unexpected SeedVR recipe: {resref}")
        require(manifest.get("source", {}).get("frame_manifest_sha256") == record["frame_manifest_sha256"],
                f"unexpected SeedVR source: {resref}")
        frame_records = sorted(manifest["frames"], key=lambda f: f["frame"])
        require(len(frame_records) == 10, f"unexpected output frame count: {resref}")
        resource = copy.deepcopy(donors[resref])
        resource["frame_count"] = 10
        resource["frames"] = resource["frames"][:10]
        resource["playback_mode"] = "Native"
        resource["native_fps"] = {"numerator": 0, "denominator": 0}
        resource["target_fps"] = {"numerator": 0, "denominator": 0}
        resource["cycles"] = [{"cycle": 0, "native_frame_indices": list(range(10)),
                                "timeline_frame_indices": []}]
        resource["cycle_count"] = 1
        resource["assets"] = []
        buffers = []
        for index, (frame, raw_frame) in enumerate(zip(resource["frames"], frame_records, strict=True)):
            require(raw_frame["frame"] == index and frame["physical_size_x4"] == raw_frame["physical_size_xn"]
                    and frame["centre_x1"] == raw_frame["centre_x1"], f"SeedVR geometry changed: {resref}/{index}")
            donor_file = ALPHA_PACK / frame["asset"]
            require(digest(donor_file) == frame["sha256"], f"alpha donor changed: {resref}/{index}")
            raw_file = upscale / raw_frame["raw_rgba_xn"]
            require(digest(raw_file) == raw_frame["raw_rgba_xn_sha256"], f"SeedVR RGBA changed: {resref}/{index}")
            width, height = frame["physical_size_x4"]
            donor = np.frombuffer(donor_file.read_bytes(), dtype=np.uint8).reshape(height, width, 4)
            pixels = np.frombuffer(raw_file.read_bytes(), dtype=np.uint8).reshape(height, width, 4).copy()
            alpha = donor[..., 3]
            pixels[..., 3] = alpha
            # ARE 0x1141 has no Blended bit (0x2). Native draw state is preserved
            # by the renderer. Premultiplying soft alpha here would attenuate
            # its RGB again on a standard SRC_ALPHA composition path. The old
            # accepted donor's premultiplied RGB is deliberately not reused.
            pixels[alpha == 0, :3] = 0
            require(np.array_equal(pixels[..., 3], alpha), "alpha graft changed")
            payload = pixels.tobytes()
            frame["sha256"] = hashlib.sha256(payload).hexdigest()
            frame["bytes"] = len(payload)
            frame.pop("generated_by", None)
            resource["assets"].append({"name": frame["asset"], "sha256": frame["sha256"], "bytes": len(payload)})
            buffers.append((frame["asset"], payload))
        runtime.resource_binary_v2(resource, registry_version=3)
        prepared.append((resource, buffers))
        provenance.append({"resref": resref, "upscale_manifest": str(upscale / "manifest.json"),
                           "upscale_manifest_sha256": digest(upscale / "manifest.json")})
    resources = [r for r, _ in prepared]
    require({r["resref"] for r in resources} == set(RESREFS), "incomplete AR3021")
    registry = runtime.registry_v2_from_resources(resources, registry_version=3)
    raw_bytes = sum(a["bytes"] for r in resources for a in r["assets"])
    require(raw_bytes <= runtime.MAX_RAW_BYTES, "runtime budget exceeded")
    target.mkdir(parents=True)
    for _resource, buffers in prepared:
        for name, payload in buffers:
            (target / name).write_bytes(payload)
    (target / runtime.REGISTRY_NAME).write_bytes(registry)
    result = {"schema": runtime.PACK_SCHEMA, "status": "completed", "scale": 4,
              "created_utc": datetime.now(timezone.utc).isoformat(), "area_id": "AR3021",
              "registry_version": 3, "runtime_contract": {"feature": "Native", "clock": "native-engine", "registry_version": 3},
              "registry": runtime.REGISTRY_NAME, "registry_sha256": hashlib.sha256(registry).hexdigest(),
              "registry_bytes": len(registry), "resource_count": 3, "frame_count": 30,
              "timed_resources": [], "raw_bytes": raw_bytes, "runtime_budget_enforced": True,
              "base_assets": [], "new_assets": [], "resources": resources,
              "provenance": {"preparation": str(PLAN), "alpha_source_manifest_sha256": ALPHA_MANIFEST_HASH,
                             "vanilla_evidence": vanilla_evidence, "producer": str(Path(__file__).resolve()),
                             "seedvr_runs": provenance, "rgb_rule": "straight RGB; zero only where alpha==0; alpha donor bytes unchanged",
                             "supersedes_preparation_rgb_recipe": "the original preparation is immutable; assembler owns the final RGB policy"},
              "qa": "pending-user-ingame", "release": "not-requested"}
    save_new(target / "manifest.json", result)
    runtime.validate_v2_pack(target)
    print(json.dumps({"status": "candidate-completed", "path": str(target), "raw_bytes": raw_bytes,
                      "registry_version": 3, "playback": "Native", "installed": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "assemble"))
    parser.add_argument("--output", required=True, type=Path, help="AR3021 local preparation root")
    parser.add_argument("--vanilla-root", type=Path, default=Path("G:/AI/BG2_Vanilla_23534562"))
    args = parser.parse_args()
    LOCAL = args.output.resolve()
    LOCAL.relative_to(ROOT)
    PLAN = LOCAL / "preparation.json"
    VANILLA = args.vanilla_root.resolve()
    prepare() if args.action == "prepare" else assemble()
