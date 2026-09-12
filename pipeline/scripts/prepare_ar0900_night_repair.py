"""Freeze AR0900N day-equivalent repair inputs; plan-only without --run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from build_wtlake_timeline_batch import ROOT, get_path, relative, sha256_file
from repair_water_map_batch import require, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repair-output", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    output, repair = args.output.resolve(), args.repair_output.resolve()
    require(all(ROOT in p.parents and not p.exists() for p in (output, repair)), "new workspace outputs required")
    tracking = json.loads((ROOT/"pipeline/water/release-tracking-v1.json").read_text(encoding="utf-8"))
    evidence = {e["id"]: e for e in tracking["evidence"]}
    current = evidence[tracking["runtime"]["registry_evidence_id"]]
    complete = evidence["water-registry-current-v4"]
    for e in (current, complete):
        require(sha256_file(ROOT/e["path"]) == e["sha256"], "registry evidence drift")
    registry = json.loads((ROOT/current["path"]).read_text(encoding="utf-8"))
    previous = json.loads((ROOT/complete["path"]).read_text(encoding="utf-8"))
    ids = {e["id"] for e in registry["entries"]}
    restored = [e for e in previous["entries"] if e["id"] not in ids]
    require(all(e["material_id"] in (4, 5) for e in restored), "unexpected omitted identity")
    registry["entries"].extend(restored)
    registry["experiment"] = {"scope": "preserve installed WTLAKE identities and restore omitted validated sewage/swamp identities",
                               "parents": [current, complete], "restored_ids": [e["id"] for e in restored]}
    game = get_path("bg2ee_game_root")
    snapshots = {}
    for e in registry["entries"]:
        names = [(e["wed"]["resref"]+".WED", e["wed"]["sha256"]),
                 (e["base_tis"]["resref"]+".TIS", e["base_tis"]["sha256"]),
                 (e["overlay"]["tis_resref"]+".TIS", e["overlay"]["tis_sha256"])]
        names += [(p["resref"]+".PVRZ", p["sha256"]) for p in e["base_tis"]["pages"]+e["overlay"]["pages"]]
        for name, sha in names:
            require(name not in snapshots or snapshots[name] == sha, "conflicting shared asset")
            if name not in snapshots:
                require(sha256_file(game/"override"/name) == sha, f"live asset drift: {name}")
                snapshots[name] = sha
    donor = ROOT/"maps/AR0900/runs/seedvr2-7b-int8-lab-grid-2x5-x4-nuit/tuiles-secondaires-nuit/03_assemble/AR0900N-tuiles-secondaires-nuit-x4-seedvr2-7b-int8-lab-overlap.png"
    request = {"output": relative(repair), "registry": relative(output/"registry-before-v3.json"),
               "targets": [{"wed": "AR0900N", "variant": "night", "strength": 0.70,
                            "base": "maps/water-batches/runs/qa-candidates-20260912-v1/batches/lake-wtlake/maps/AR0900N",
                            "donor": relative(donor), "donor_sha256": sha256_file(donor)}]}
    print(json.dumps({"entries": len(registry["entries"]), "restored_ids": [e["id"] for e in restored],
                      "verified_live_assets": len(snapshots), "request": request}, indent=2), flush=True)
    if not args.run:
        return
    output.mkdir(parents=True)
    write_json(output/"registry-before-v3.json", registry)
    request["registry_sha256"] = sha256_file(output/"registry-before-v3.json")
    write_json(output/"request.json", request)
    shutil.copy2(args.screenshot, output/args.screenshot.name)
    log = game/"InfinityEngine-Enhancer.log"
    shutil.copy2(log, output/"runtime-before.log")
    shutil.copy2(Path(__file__), output/Path(__file__).name)
    write_json(output/"diagnosis.json", {
        "asset_ids": ["maps:AR0900:night"], "qa": "user-rejected-night-v3",
        "causes": ["publish_view_state refreshes only when CGameArea changes; night changes m_pResWED in place; route2 reason3 rejects stale day snapshot",
                   "night base has alpha128 but lacks the day recipe RGB seam graft",
                   "previous WTLAKE-only registry omitted five sewage/swamp identities; restored unchanged from recorded authority"],
        "recipe": "existing night SeedVR LAB x4 masters, native alpha128, bounded secondary donor RGB graft, same WTLAKE x4/36 phases/15Hz/render30/material1/q0.70",
        "parents": [current, complete], "live_assets": snapshots,
        "screenshot": {"path": args.screenshot.name, "sha256": sha256_file(output/args.screenshot.name)},
        "log": {"path": "runtime-before.log", "sha256": sha256_file(output/"runtime-before.log"),
                "witness": "15:49:13 AR0900 q0.7 temporal=true; 15:49:21 reason3 after night transition"},
        "producer_sha256": sha256_file(Path(__file__)), "tests": "not-run-user-choice", "release": "not-requested"})


if __name__ == "__main__":
    main()
