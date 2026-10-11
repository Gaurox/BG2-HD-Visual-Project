"""Install the two prepared tree packs transactionally; verify exact installed bytes."""
import argparse
import importlib.util
import sys

import finish


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    f = finish
    record = f.HERE / "installation.json"
    assert not record.exists(), "Do not rewrite an installation receipt"
    prepared = f.v2.load_json(f.HERE / "preparation.json")
    game = f.get_path("bg2ee_game_root", required=True)
    areas = game / "iee-assets/areas"
    path = f.ROOT / "pipeline/area-animation-area-test/area_animation_area_test.py"
    spec = importlib.util.spec_from_file_location("trees_install_core", path)
    core = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = core
    spec.loader.exec_module(core)
    core.ensure_game_stopped(core.running_game_processes)
    lock = f.state.load_lock()
    protected = [game/"InfinityEngine-Enhancer.dll", game/"InfinityEngine-Enhancer.ini"]
    if (areas/"AR3000").exists():
        protected += [p for p in (areas/"AR3000").iterdir() if p.is_file()]
    hashes = {str(p.relative_to(game)):f.v2.sha256_file(p) for p in protected}
    for area, leaf_path in prepared["leaves"].items():
        leaf = f.ROOT / leaf_path
        baseline = prepared["baseline"][area]
        actual = f.state.zone_signatures(areas/area) if (areas/area).exists() else {}
        assert actual == baseline["signatures"], f"Recompose: installed {area} changed"
        assert lock["areas"].get(area) == baseline["lock_entry"], f"Recompose: {area} lock changed"
        assert f.v2.sha256_file(leaf/"manifest.json") == prepared["leaf_manifest_sha256"][area]
        result = core.install_area_pack(leaf, game_root=game, verify_only=True)
        assert not result.dropped
        print(f"VerifyOnly passed: {area}", flush=True)
    if not args.run:
        return
    results = []
    for area, leaf_path in prepared["leaves"].items():
        leaf = f.ROOT / leaf_path
        result = core.install_area_pack(leaf, game_root=game)
        assert result.status == "installed" and not result.dropped
        actual = f.state.zone_signatures(areas/area)
        assert actual == f.state.leaf_signatures(leaf)
        assert f.v2.sha256_file(areas/area/f.v2.REGISTRY_NAME) == f.v2.sha256_file(leaf/f.v2.REGISTRY_NAME)
        core.record_lock(area, leaf, game)
        results.append({"area":area, "source_pack":leaf_path,
            "receipt":f.relative(result.receipt_path), "incoming_files":result.incoming_files,
            "incoming_bytes":result.incoming_bytes,"installed_signatures":actual})
        f.write(f.HERE/"installation-progress.json", {"status":"installing","areas":results})
        print(f"Installed and verified: {area}", flush=True)
    assert hashes == {str(p.relative_to(game)):f.v2.sha256_file(p) for p in protected}
    updated = f.state.load_lock()
    assert {a:e for a,e in updated["areas"].items() if a not in prepared["leaves"]} == {
        a:e for a,e in lock["areas"].items() if a not in prepared["leaves"]}
    f.write(record, {"schema":"bg2-upscale-trees-installation-v1",
        "status":"installed-for-ingame-test","installed_utc":f.v2.utc_now(),
        "preparation_sha256":f.v2.sha256_file(f.HERE/"preparation.json"),
        "area_count":2,"tree_resources":5,"tree_occurrences":10,
        "native_geometry_cycles_preserved":True,"fountains_preserved":True,
        "renderer_ini_ar3000_unchanged":True,"protected_hashes":hashes,
        "qa_status":"pending-user-ingame-test","release_status":"not-selected","areas":results})
    f.write(f.HERE/"installation-progress.json", {"status":"completed","receipt":f.relative(record)})


if __name__ == "__main__":
    main()
