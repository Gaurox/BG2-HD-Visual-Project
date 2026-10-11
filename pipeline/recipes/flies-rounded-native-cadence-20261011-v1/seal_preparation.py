"""Finish pack validation/receipt after preparation; no game or authority writes."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RECIPE = Path(__file__).resolve().parent
sys.path.insert(0, str(RECIPE))
import build


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else "v1"
    assert version.isalnum()
    record_path = RECIPE / f"preparation-{version}.json"
    assert not record_path.exists(), "Preparation receipts are immutable"
    complete = ROOT / "animations/packs-par-zone" / f"{build.RUN_ID}-complete-{version}"
    index = build.v2.load_json(complete / "manifest.json")
    lock_path = ROOT / "animations/index/area-pack-lock.json"
    lock = build.v2.load_json(lock_path)
    game_areas = build.get_path("bg2ee_game_root", required=True) / "iee-assets/areas"
    core_path = ROOT / "pipeline/area-animation-area-test/area_animation_area_test.py"
    spec = importlib.util.spec_from_file_location("flies_pack_validation", core_path)
    core = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = core
    spec.loader.exec_module(core)
    baseline = {}
    assert index["area_count"] == len(index["areas"]) == 21
    for item in index["areas"]:
        area = item["area_id"]
        leaf = complete / item["directory"]
        assert build.v2.sha256_file(leaf / "manifest.json") == item["manifest_sha256"]
        core.validate_area_pack(leaf)
        entry = lock["areas"].get(area)
        expected = {k: v["sig"] for k, v in entry["resources"].items()} if entry else {}
        game_dir = game_areas / area
        actual = {k: v["sig"] for k, v in build.zone_signatures(game_dir).items()} if game_dir.exists() else {}
        assert actual == expected, f"Installed state changed: {area}"
        if entry:
            assert build.recipe_signatures(entry) == expected, area
        else:
            assert not game_dir.exists(), area
        after = build.leaf_signatures(leaf)
        assert {k: v["sig"] for k, v in after.items() if k.split("-v")[0] not in build.TARGETS} == expected
        baseline[area] = {"lock_entry": entry, "installed_resource_signatures": expected,
                          "installed_fingerprint": build.zone_fingerprint(game_dir) if game_dir.exists() else None,
                          "installed_registry_sha256": build.v2.sha256_file(game_dir / build.v2.REGISTRY_NAME) if game_dir.exists() else None}
        print(f"Validated {area}", flush=True)
    assert build.v2.load_json(lock_path) == lock
    for area, snapshot in baseline.items():
        directory = game_areas / area
        assert (build.zone_fingerprint(directory) if directory.exists() else None) == snapshot["installed_fingerprint"], area
    production = build.v2.load_json(build.RUN / "manifest.json")
    assert len(production["occurrences"]) == 216
    record = {
        "schema": "bg2-upscale-flies-preparation-v1", "status": "prepared-not-installed",
        "created_utc": build.v2.utc_now(), "production_run": build.relative(build.RUN),
        "complete_split_root": build.relative(complete),
        "complete_manifest_sha256": build.v2.sha256_file(complete / "manifest.json"),
        "area_count": 21, "occurrence_count": 216, "source_frame_count": 36,
        "native_cadence_preserved": True, "existing_resources_byte_identical": True,
        "area_installer_pack_validation": "passed-for-all-21-leaves",
        "installation": {
            "status": "deferred-by-user",
            "must_wait_for": "User confirms parallel DLL work finished and committed",
            "before_install": "Compare relevant lock entries and installed signatures to baseline; recompose a new version if changed; close game and InfinityLoader; run targeted installer VerifyOnly",
            "installer": "pipeline/scripts/Install-AreaAnimation-AreaTest.ps1",
            "do_not_use": "Install-AreaAnimations-PerArea.ps1: split-root covers only 21 affected zones",
        },
        "qa": "PNG previews accepted; ingame QA pending; native selections unchanged",
        "release": "not-selected", "baseline_lock_sha256": build.v2.sha256_file(lock_path),
        "largest_area_raw_bytes": index["largest_area_raw_bytes"], "total_raw_bytes": index["total_raw_bytes"],
        "areas": baseline,
    }
    build.write(record_path, record)
    print(json.dumps({k: record[k] for k in ("status", "area_count", "occurrence_count", "complete_split_root", "largest_area_raw_bytes")}, indent=2))


if __name__ == "__main__":
    main()
