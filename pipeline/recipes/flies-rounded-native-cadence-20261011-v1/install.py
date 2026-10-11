"""Verify or install only the 21 prepared flies area packs, using the transactional installer."""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Install after the user-confirmed DLL commit")
    parser.add_argument("--composition-version", default="v1")
    args = parser.parse_args()
    assert args.composition_version.isalnum()
    record_path = HERE / f"installation-{args.composition_version}.json"
    assert not record_path.exists(), "Do not overwrite an installation receipt"
    prepared = build.v2.load_json(HERE / f"preparation-{args.composition_version}.json")
    complete = ROOT / prepared["complete_split_root"]
    assert build.v2.sha256_file(complete / "manifest.json") == prepared["complete_manifest_sha256"]
    index = build.v2.load_json(complete / "manifest.json")
    assert index["area_count"] == len(index["areas"]) == 21
    lock_path = ROOT / "animations/index/area-pack-lock.json"
    lock = build.v2.load_json(lock_path)
    game = build.get_path("bg2ee_game_root", required=True)
    game_areas = game / "iee-assets/areas"
    core_path = ROOT / "pipeline/area-animation-area-test/area_animation_area_test.py"
    spec = importlib.util.spec_from_file_location("flies_install_core", core_path)
    core = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = core
    spec.loader.exec_module(core)
    core.ensure_game_stopped(core.running_game_processes)
    # Preserve the parallel AR3000 work and the currently installed renderer/INI.
    protected = [game / "InfinityEngine-Enhancer.dll", game / "InfinityEngine-Enhancer.ini"]
    ar3000 = game_areas / "AR3000"
    if ar3000.exists():
        protected += [p for p in ar3000.iterdir() if p.is_file()]
    protected_hashes = {str(p.relative_to(game)): build.v2.sha256_file(p) for p in protected}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    entries = sorted(index["areas"], key=lambda e: e["area_id"])
    for entry in entries:
        area = entry["area_id"]
        baseline = prepared["areas"][area]
        assert lock["areas"].get(area) == baseline["lock_entry"], f"Recompose: lock changed for {area}"
        installed = game_areas / area
        signatures = {k: v["sig"] for k, v in build.zone_signatures(installed).items()} if installed.exists() else {}
        assert signatures == baseline["installed_resource_signatures"], f"Recompose: payload changed for {area}"
        digest = build.v2.sha256_file(installed / build.v2.REGISTRY_NAME) if installed.exists() else None
        assert digest == baseline["installed_registry_sha256"], f"Recompose: registry changed for {area}"
        leaf = complete / entry["directory"]
        assert build.v2.sha256_file(leaf / "manifest.json") == entry["manifest_sha256"]
        verified = core.install_area_pack(leaf, game_root=game, verify_only=True)
        assert not verified.dropped, f"Unexpected drop: {area}"
        print(f"VerifyOnly passed: {area}", flush=True)
    assert build.v2.load_json(lock_path) == lock, "Lock changed during preflight"
    if not args.run:
        print("All 21 packs verified; no installation performed.")
        return
    results = []
    for entry in entries:
        leaf = complete / entry["directory"]
        result = core.install_area_pack(leaf, game_root=game)
        assert result.status == "installed", result
        core.record_lock(result.area_id, leaf, game)
        actual = build.zone_signatures(game_areas / result.area_id)
        assert actual == build.leaf_signatures(leaf), f"Installed frames differ: {result.area_id}"
        assert build.v2.sha256_file(game_areas / result.area_id / build.v2.REGISTRY_NAME) == entry["registry_sha256"]
        updated_lock = build.v2.load_json(lock_path)
        assert updated_lock["areas"][result.area_id]["resources"] == actual, result.area_id
        results.append({"area": result.area_id, "status": result.status,
                        "source_pack": build.relative(leaf), "incoming_files": result.incoming_files,
                        "incoming_bytes": result.incoming_bytes,
                        "receipt": build.relative(result.receipt_path),
                        "installed_registry_sha256": entry["registry_sha256"]})
        build.write(HERE / f"installation-progress-{args.composition_version}.json", {
            "status": "installing", "created_utc": build.v2.utc_now(), "completed_areas": results,
        })
        print(f"Installed and verified: {result.area_id} ({len(results)}/21)", flush=True)
    assert {str(p.relative_to(game)): build.v2.sha256_file(p) for p in protected} == protected_hashes
    assert build.v2.load_json(lock_path)["areas"].get("AR3000") == lock["areas"].get("AR3000")
    build.write(record_path, {
        "schema": "bg2-upscale-flies-installation-v1", "status": "installed-for-ingame-test",
        "installed_utc": build.v2.utc_now(), "repository_commit_at_install": head,
        "preparation": build.relative(HERE / f"preparation-{args.composition_version}.json"),
        "complete_split_root": prepared["complete_split_root"], "area_count": 21,
        "occurrence_count": 216, "source_frame_count": 36, "native_cadence_preserved": True,
        "all_installed_assets_and_registries_verified": True,
        "renderer_ini_ar3000_unchanged": True, "protected_hashes": protected_hashes,
        "qa_status": "pending-user-ingame-test", "release_status": "not-selected", "areas": results,
    })
    build.write(HERE / f"installation-progress-{args.composition_version}.json", {
        "status": "completed", "receipt": build.relative(record_path), "completed_areas": results,
    })
    print(f"Installed 21 areas; receipt: {build.relative(record_path)}")


if __name__ == "__main__":
    main()
