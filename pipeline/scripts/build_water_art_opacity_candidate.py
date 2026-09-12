"""Build the reviewed AR0300N paired-alpha experiment. Plan-only without --run."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess

from bg2lib import load_key, resolve_resource, resolve_tileset_resource
from build_water_route1_batch import (
    ROOT, eligible_primary_ids, parse_wed, sha256_file, source_pages, write_json,
)
from build_wtlake_timeline_batch import tis_metadata
from repair_wtswam_pilot import correct_central_alpha
from workspace_paths import get_path

ENGINE = ROOT / "engine/InfinityEngine-Enhancer/source-patchee"
SOURCE_FILES = [
    ENGINE / "src/iee/water_route2_registry.h",
    ENGINE / "src/iee/water_route2_registry.cpp",
    ENGINE / "src/iee/area_state.h",
    ENGINE / "src/iee/area_state.cpp",
    ENGINE / "src/iee/features/tile_render.cpp",
    ENGINE / "tools/generate_water_route2_registry.py",
    ENGINE / "tests/iee_tests.cpp",
    ROOT / "pipeline/scripts/install_water_repair_candidate.py",
    ROOT / "pipeline/scripts/repair_wtswam_pilot.py",
    Path(__file__).resolve(),
]


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def record(path):
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path),
            "bytes": path.stat().st_size}


def secondary_ids(wed):
    parsed = parse_wed(wed)
    water = {c["secondary"] for c in parsed["cells"]
             if c["flags"] & 2 and c["secondary"] != 65535}
    other = {c["secondary"] for c in parsed["cells"]
             if not c["flags"] & 2 and c["secondary"] != 65535}
    primaries = {i for c in parsed["cells"] for i in c["primary"]}
    require(not water & (other | primaries), "ambiguous secondary roles")
    return sorted(water)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    request_path = args.request.resolve()
    request = json.loads(request_path.read_text(encoding="utf-8"))
    require([t["wed"] for t in request["targets"]] == ["AR0300N"] and
            (request["source_alpha"], request["target_alpha"]) == (128, 160),
            "only the reviewed AR0300N 128-to-160 experiment is supported")
    registry_path = ROOT / request["registry"]
    require(sha256_file(registry_path) == request["registry_sha256"], "parent drift")
    parent = json.loads(registry_path.read_text(encoding="utf-8"))
    registry = copy.deepcopy(parent)
    target = next(e for e in registry["entries"] if e["wed"]["resref"] == "AR0300N")
    require(not target.get("local_art_opacity"), "parent already overrides native art opacity")
    source = ROOT / request["source"]
    require(tis_metadata("AR0300N", source)[0] == target["base_tis"], "source TIS/PVRZ drift")
    require(sha256_file(source / "AR0300N.WED") == target["wed"]["sha256"], "source WED drift")
    game = get_path("bg2ee_game_root")
    live = game / "override"
    before = {}
    for entry in parent["entries"]:
        files = [(entry["wed"]["resref"] + ".WED", entry["wed"]["sha256"]),
                 (entry["base_tis"]["resref"] + ".TIS", entry["base_tis"]["sha256"]),
                 (entry["overlay"]["tis_resref"] + ".TIS", entry["overlay"]["tis_sha256"])]
        files += [(p["resref"] + ".PVRZ", p["sha256"])
                  for p in entry["base_tis"]["pages"] + entry["overlay"]["pages"]]
        for name, digest in files:
            if name not in before:
                require(sha256_file(live / name) == digest, "live drift: " + name)
                before[name] = digest
            require(before[name] == digest, "registry alias hash conflict")
    bifs, resources = load_key()
    lookup = {(n.upper(), k): loc for n, k, loc in resources}
    stock_wed, archive = resolve_resource(bifs, lookup["AR0300N", 0x3E9])
    stock_tis, count, size, _ = resolve_tileset_resource(bifs, lookup["AR0300N", 0x3EB])
    are_path = live / "AR0300.ARE"
    are = are_path.read_bytes() if are_path.exists() else resolve_resource(bifs, lookup["AR0300", 0x3F2])[0]
    require(are[:8] == b"AREAV1.0" and (are[0x52] or 128) == 128, "native ARE alpha drift")
    primaries = eligible_primary_ids(parse_wed(stock_wed), 1)
    qualified, _ = source_pages(bifs, lookup, "AR0300N", stock_tis, count, size, primaries)
    secondaries = secondary_ids(stock_wed)
    current_wed = (source / "AR0300N.WED").read_bytes()
    require(qualified == primaries and len(primaries) == 892 and len(secondaries) == 374,
            "native role population drift")
    require(eligible_primary_ids(parse_wed(current_wed), 1) == primaries and
            secondary_ids(current_wed) == secondaries, "stock/x4 role divergence")
    executable = game / "BaldurReal.exe"
    require(sha256_file(executable) == "B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57",
            "native alpha ABI evidence requires requalification")
    output = ROOT / request["output"]
    require(ROOT in output.resolve().parents and not output.exists(), "output must be new within workspace")
    print(json.dumps({"mode": "run" if args.run else "plan", "primaries": len(primaries),
                      "secondaries": len(secondaries), "live_files": len(before), "target_alpha": 160}), flush=True)
    if not args.run:
        return
    output.mkdir(parents=True)
    destination = output / "maps/AR0300N"
    shutil.copytree(source, destination)
    alpha_report = correct_central_alpha("AR0300N", stock_wed, source, destination, 160)
    # The reused helper names this field 'native'; this candidate is explicitly artistic.
    alpha_report["candidate_primary_texture_alpha"] = alpha_report.pop("effective_native_alpha")
    target["base_tis"] = tis_metadata("AR0300N", destination)[0]
    target["local_art_opacity"] = {
        "mode": "paired-primary-texture-secondary-draw", "source_draw_alpha": 128,
        "target_draw_alpha": 160, "primary_texture_alpha": 160,
        "secondary_tile_ids": secondaries,
        "scope": "exact AR0300N WED/TIS and exclusive water secondary roles; preserve RGB and other alpha",
    }
    target["state"] = "candidate-installable-pending-qa"
    target["qa"] = {"status": "pending-ingame", "reference": (output / "repair-report.json").relative_to(ROOT).as_posix()}
    registry["experiment"] = {"scope": ["AR0300N"], "parent": record(registry_path),
                              "reason": request["user_direction"], "qa": "pending-ingame"}
    write_json(output / "registry-v3.json", registry)
    write_json(output / "request.json", request | {"producer": record(Path(__file__).resolve()),
                                                    "input_request": record(request_path)})
    write_json(output / "live-before.json", before)
    candidate = output / "override-candidate"
    candidate.mkdir()
    plan = {}
    for path in sorted(destination.iterdir()):
        digest = sha256_file(path)
        if digest == before[path.name]:
            continue
        require(path.suffix == ".PVRZ", "change outside base pages")
        plan[path.name] = record(path) | {"source": path.relative_to(ROOT).as_posix(),
                                         "before_sha256": before[path.name]}
        shutil.copy2(path, candidate / path.name)
    require(len(plan) == 20, "changed page population drift")
    write_json(output / "install-plan.json", plan)
    write_json(candidate / "manifest.json", {
        "schema": "bg2-upscale-area-animation-override-assets-v1", "status": "completed",
        "area": "AR0300N", "qa_status": "pending-ingame",
        "files": {name: {k: row[k] for k in ("sha256", "bytes")} for name, row in plan.items()},
    })
    snapshots = []
    for path in SOURCE_FILES:
        copied = output / "source-snapshot" / path.relative_to(ROOT)
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, copied)
        snapshots.append(record(copied))
    report = {
        "wed": "AR0300N", "family": "lake-wtlake", "native_are_alpha": 128,
        "primary": alpha_report, "eligible_primary_ids": sorted(primaries),
        "secondary_draw_alpha": {"from": 128, "to": 160, "tile_ids": secondaries},
        "source_wed_archive": archive, "rgb_secondary_shore_masks_wed_tis": "byte-identical",
        "route2": "unchanged q0.70; WTLAKE x4; 36 frames; source15Hz/render30FPS",
        "native_abi": {"executable_sha256": sha256_file(executable),
                       "draw_color_rva": "0x413200", "draw_alpha_rva": "0x413090",
                       "opengl_color_state_rva": "0x756E08",
                       "evidence": "DrawColor/DrawAlpha share packed color state; alpha is high byte; DrawColor returns previous ARGB; RGB swap in GL retains alpha"},
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ENGINE, text=True).strip(),
        "source_snapshot": snapshots, "unchanged_registry_entries": len(parent["entries"]) - 1,
        "limits": ["experimental artistic opacity, not native repair", "install pages and matching DLL together",
                   "unexpected native alpha/fades remain unchanged", "not visually validated"],
        "tests": "not-run-user-choice", "qa": "pending-ingame", "release": "not-requested",
    }
    write_json(output / "repair-report.json", report)
    write_json(output / "run.json", {
        "schema": "bg2-water-paired-art-opacity-run-v1", "asset_ids": request["asset_ids"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "request": record(output / "request.json"), "report": record(output / "repair-report.json"),
        "registry": record(output / "registry-v3.json"), "candidate": record(candidate / "manifest.json"),
        "changed_assets": len(plan), "verified_live_files": len(before),
        "installation": "not-run", "tests": "not-run-user-choice", "qa": "pending-ingame", "release": "not-requested",
    })
    print(json.dumps(record(output / "run.json")), flush=True)


if __name__ == "__main__":
    main()
