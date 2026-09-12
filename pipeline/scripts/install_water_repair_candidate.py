"""Install a prepared water repair and its matching DLL; plan-only without --run."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

from build_wtlake_timeline_batch import ROOT, get_path, sha256_file, relative
from water_wed import validate_polygons

TOOLS = ROOT / "engine/InfinityEngine-Enhancer/source-patchee/tools"
sys.path.insert(0, str(TOOLS))
import install_renderer_candidate as renderer


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, obj):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--dll", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    require(ROOT in candidate.parents, "candidate outside workspace")
    game = get_path("bg2ee_game_root")
    override = game/"override"
    request = read(candidate/"request.json")
    before = read(candidate/"live-before.json")
    plan = read(candidate/"install-plan.json")
    old_registry = read(ROOT/request["registry"])
    new_registry = read(candidate/"registry-v3.json")
    targets = {t["wed"] for t in request["targets"]}
    require(targets in ({"AR0204", "AR1600"}, {"AR0900N"}), "installer limited to reviewed repair scopes")
    old_entries = {e["id"]: e for e in old_registry["entries"]}
    require({e["id"] for e in new_registry["entries"]} == set(old_entries), "registry identity set changed")
    for e in new_registry["entries"]:
        if e["wed"]["resref"] not in targets:
            require(e == old_entries[e["id"]], "unrelated registry entry changed")
    for name, sha in before.items():
        require(sha256_file(override/name) == sha, f"live drift: {name}")
    for name, row in plan.items():
        require(Path(name).name == name and name in before, "unexpected installation target")
        require(any(name == area+".WED" or name.startswith(area[0]+area[2:]) and name.endswith(".PVRZ") for area in targets), "target outside reviewed maps")
        require(row["before_sha256"] == before[name], "before snapshot divergence")
        require(sha256_file(candidate/"override-candidate"/name) == row["sha256"], "candidate drift")
        if name.endswith(".WED"):
            validate_polygons((candidate/"override-candidate"/name).read_bytes())
    require(args.dll.is_file(), "built DLL absent")
    print(json.dumps({"assets": len(plan), "maps": sorted(targets), "dll": str(args.dll),
                      "dll_sha256": sha256_file(args.dll), "untouched_registry_entries": len(old_entries)-len(targets),
                      "tests": "none-user-choice", "mode": "install" if args.run else "plan"}), flush=True)
    if not args.run:
        return
    renderer.ensure_game_stopped(renderer.running_game_processes)
    transaction = ROOT/"backups/water-map-repair"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    transaction.mkdir(parents=True)
    renderer_candidate = transaction/"renderer-candidate"
    renderer_candidate.mkdir()
    shutil.copy2(args.dll, renderer_candidate/"InfinityEngine-Enhancer.dll")
    shutil.copy2(game/"InfinityEngine-Enhancer.ini", renderer_candidate/"InfinityEngine-Enhancer.ini")
    runtime_before = {name: sha256_file(game/name) for name in ["InfinityEngine-Enhancer.dll", "InfinityEngine-Enhancer.ini"]}
    protected = {"fpSEAM.glsl": sha256_file(override/"fpSEAM.glsl")}
    write(transaction/"request.json", {"candidate": relative(candidate), "registry_sha256": sha256_file(candidate/"registry-v3.json"),
          "renderer_before": runtime_before, "protected_shaders": protected, "assets": plan,
          "producer_sha256": sha256_file(Path(__file__))})
    shell = shutil.which("pwsh") or shutil.which("powershell.exe")
    require(shell is not None, "PowerShell runtime absent")
    ps = [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
          str(ROOT/"pipeline/scripts/Install-AreaOverrideAssets.ps1"), "-SourceRoot", str(candidate/"override-candidate"),
          "-GameRoot", str(game), "-BackupRoot", str(transaction/"assets")]
    subprocess.run(ps+["-VerifyOnly"], check=True)
    renderer.install_candidate(renderer_candidate, game_root=game, verify_only=True)
    # Check again immediately before the first write.
    for name, sha in before.items():
        require(sha256_file(override/name) == sha, f"live drift before install: {name}")
    for name, sha in runtime_before.items():
        require(sha256_file(game/name) == sha, "runtime drift before install")
    result = None
    try:
        subprocess.run(ps, check=True)
        result = renderer.install_candidate(renderer_candidate, game_root=game)
        renderer.verify_transaction(result.receipt_path, game)
        for name, old_sha in before.items():
            expected = plan[name]["sha256"] if name in plan else old_sha
            require(sha256_file(override/name) == expected, f"installed asset mismatch: {name}")
        for name, sha in protected.items():
            require(sha256_file(override/name) == sha, "protected shader drift")
        require(sha256_file(game/"InfinityEngine-Enhancer.ini") == runtime_before["InfinityEngine-Enhancer.ini"], "INI drift")
    except Exception as error:
        renderer.ensure_game_stopped(renderer.running_game_processes)
        if result and result.receipt_path:
            renderer.restore_from_receipt(result.receipt_path, game_root=game)
        # Restore only known before/after hashes; never overwrite third-party drift.
        receipts = list((transaction/"assets").glob("*/install-backup.json"))
        if receipts:
            require(len(receipts) == 1, "ambiguous asset backup")
            receipt = receipts[0]
            records = read(receipt)["Files"]
            for r in records:
                name = r["Name"]
                require(r["PresentBefore"], "unexpected previously absent asset")
                require(sha256_file(override/name) in {before[name], plan[name]["sha256"]}, "third-party drift blocks rollback")
                require(sha256_file(receipt.parent/name) == before[name], "backup drift")
            for r in records:
                shutil.copy2(receipt.parent/r["Name"], override/r["Name"])
                require(sha256_file(override/r["Name"]) == before[r["Name"]], "rollback verification failed")
        write(transaction/"failure.json", {"error": str(error), "status": "rolled-back"})
        raise
    receipt = next((transaction/"assets").glob("*/install-backup.json"))
    final = {"status": "installed-pending-ingame-qa", "asset_receipt": relative(receipt),
             "renderer_receipt": relative(result.receipt_path), "registry": relative(candidate/"registry-v3.json"),
             "registry_sha256": sha256_file(candidate/"registry-v3.json"), "verified_registry_assets": len(before),
             "changed_assets": len(plan), "dll_sha256": sha256_file(game/"InfinityEngine-Enhancer.dll"),
             "ini_sha256": sha256_file(game/"InfinityEngine-Enhancer.ini"), "tests": "not-run-user-choice", "release": "not-requested"}
    write(transaction/"installation.json", final)
    print(json.dumps(final, indent=2), flush=True)
    print("Receipt: "+relative(transaction/"installation.json"), flush=True)


if __name__ == "__main__":
    main()
