"""Create a new experimental route2 registry revision; plan-only by default."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from build_wtlake_timeline_batch import ROOT, get_path, sha256_file


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def write_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    source = ROOT / request["source_registry"]
    output = ROOT / request["output"]
    require(source.is_file() and sha256_file(source) == request["source_registry_sha256"],
            "source registry absent or divergent")
    registry = json.loads(source.read_text(encoding="utf-8"))
    by_wed = {entry["wed"]["resref"]: entry for entry in registry["entries"]}
    require(len(by_wed) == len(registry["entries"]), "duplicate WED identity")
    live = get_path("bg2ee_game_root") / "override"
    checked = {}
    for entry in registry["entries"]:
        evidence = [(entry["wed"]["resref"] + ".WED", entry["wed"]["sha256"]),
                    (entry["base_tis"]["resref"] + ".TIS", entry["base_tis"]["sha256"]),
                    (entry["overlay"]["tis_resref"] + ".TIS", entry["overlay"]["tis_sha256"])]
        evidence += [(page["resref"] + ".PVRZ", page["sha256"])
                     for page in entry["base_tis"]["pages"] + entry["overlay"]["pages"]]
        for name, expected in evidence:
            if name not in checked:
                require(sha256_file(live / name) == expected, f"live registry evidence diverged: {name}")
                checked[name] = expected
    changed = []
    for change in request["changes"]:
        area = change["wed"]
        require(area in by_wed, f"unknown WED: {area}")
        entry = by_wed[area]
        before = {"strength": entry["approved_strength"], "state": entry["state"],
                  "qa": entry["qa"]}
        if "strength" in change:
            strength = float(change["strength"])
            require(0 <= strength <= 1, "strength outside [0,1]")
            entry["approved_strength"] = strength
        if change.get("validated_ingame"):
            entry["state"] = "approved-ingame"
            entry["qa"] = {"status": "validated-ingame", "reference": change["qa_reference"]}
        else:
            entry["state"] = "candidate-installable-pending-qa"
            entry["qa"] = {"status": "pending-ingame", "reference": change["qa_reference"]}
        changed.append({"wed": area, "before": before,
                        "after": {"strength": entry["approved_strength"], "state": entry["state"],
                                  "qa": entry["qa"]}})
    registry["status"] = "experimental-pending-ingame-qa"
    registry["experiment"] = {"scope": [row["wed"] for row in request["changes"]],
        "previous_registry": request["source_registry"],
        "previous_registry_sha256": request["source_registry_sha256"],
        "untargeted_entries": "unchanged", "tests": "not-run-user-choice"}
    plan = {"schema": "bg2-water-route2-registry-revision-plan-v1", "changes": changed,
            "verified_live_files": len(checked), "output": request["output"],
            "mode": "run" if args.run else "plan"}
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    if not args.run:
        return
    require(ROOT in output.resolve().parents and not output.exists(), "output must be new")
    output.mkdir(parents=True)
    write_json(output / "request.json", request | {"request_sha256": sha256_file(args.request),
               "producer_sha256": sha256_file(Path(__file__))})
    write_json(output / "registry-v3.json", registry)
    write_json(output / "run.json", plan | {"created_at_utc": datetime.now(timezone.utc).isoformat(),
               "registry_sha256": sha256_file(output / "registry-v3.json"),
               "installation": "not-run", "qa": "per-entry", "release": "not-requested"})


if __name__ == "__main__":
    main()
