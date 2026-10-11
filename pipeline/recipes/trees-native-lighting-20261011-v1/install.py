"""Install renderer plus unlit trees as a coordinated, reversible test."""
import importlib.util
import json
import sys
from pathlib import Path

import build_renderer as b

ROOT, HERE = b.ROOT, b.HERE
sys.path.insert(0,str(ROOT/"pipeline/scripts"))
import run_animation_upscale_30fps_v2 as v2
import area_pack_state as state
sys.path.insert(0,str(ROOT/"engine/InfinityEngine-Enhancer/source-patchee/tools"))
import install_renderer_candidate as renderer


def write(path,value):
    temp = path.with_suffix(path.suffix+".part")
    temp.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
    temp.replace(path)


def main():
    assert not (HERE/"installation.json").exists()
    report = v2.load_json(HERE/"runtime.json")
    prepared = v2.load_json(HERE/"preparation.json")
    game = b.get_path("bg2ee_game_root",required=True)
    areas = game/"iee-assets/areas"
    candidate = (ROOT/report["dll"]).parent
    assert b.sha(game/"InfinityEngine-Enhancer.dll") == report["baseline_dll_sha256"]
    assert b.sha(candidate/"InfinityEngine-Enhancer.dll") == report["dll_sha256"]
    assert b.sha(game/"InfinityEngine-Enhancer.ini") == report["ini_sha256"]
    path = ROOT/"pipeline/area-animation-area-test/area_animation_area_test.py"
    spec = importlib.util.spec_from_file_location("tree_area_install_core",path)
    core = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = core
    spec.loader.exec_module(core)
    core.ensure_game_stopped(core.running_game_processes)
    lock = state.load_lock()
    lock_bytes = state.LOCK_PATH.read_bytes()
    pointer_path = ROOT/"pipeline/water/route2-registry-current.json"
    pointer_bytes = pointer_path.read_bytes()
    pointer = json.loads(pointer_bytes)
    assert pointer["dll_sha256"].lower() == report["baseline_dll_sha256"]
    protected = [game/"InfinityEngine-Enhancer.ini"]
    protected += [p for p in (areas/"AR3000").iterdir() if p.is_file()]
    protected += list((game/"override").glob("A3000*.PVRZ"))
    protected += [game/"override"/"AR3000.WED",game/"override"/"AR3000.TIS"]
    hashes = {str(p.relative_to(game)):b.sha(p) for p in protected if p.is_file()}
    renderer.install_candidate(candidate,game_root=game,verify_only=True)
    for area,p in prepared["leaves"].items():
        leaf = ROOT/p
        assert b.sha(leaf/"manifest.json") == prepared["leaf_manifest_sha256"][area]
        assert state.zone_signatures(areas/area) == prepared["baseline"][area]["signatures"]
        assert b.sha(areas/area/v2.REGISTRY_NAME) == prepared["baseline"][area]["registry_sha256"]
        assert lock["areas"].get(area) == prepared["baseline"][area]["lock_entry"]
        core.install_area_pack(leaf,game_root=game,verify_only=True)
    if "--run" not in sys.argv:
        print("DLL and both area packs verified; no installation performed.")
        return
    dll_result = None
    results = []
    try:
        dll_result = renderer.install_candidate(candidate,game_root=game)
        renderer.verify_transaction(dll_result.receipt_path,game)
        print("Renderer installed and verified",flush=True)
        for area,p in prepared["leaves"].items():
            leaf = ROOT/p
            result = core.install_area_pack(leaf,game_root=game)
            results.append({"area":area,"receipt":result.receipt_path.relative_to(ROOT).as_posix(),"source_pack":p})
            assert result.status == "installed" and not result.dropped
            assert state.zone_signatures(areas/area) == state.leaf_signatures(leaf)
            assert b.sha(areas/area/v2.REGISTRY_NAME) == b.sha(leaf/v2.REGISTRY_NAME)
            print(f"Unlit trees installed and verified: {area}",flush=True)
        assert hashes == {str(p.relative_to(game)):b.sha(p) for p in protected if p.is_file()}
        for area,p in prepared["leaves"].items(): core.record_lock(area,ROOT/p,game)
        updated = state.load_lock()
        assert {a:v for a,v in updated["areas"].items() if a not in prepared["leaves"]} == {
            a:v for a,v in lock["areas"].items() if a not in prepared["leaves"]}
        pointer["dll_sha256"] = report["dll_sha256"].upper()
        pointer["installed_by"] = (HERE/"installation.json").relative_to(ROOT).as_posix()
        pointer["updated"] = "2026-10-11"
        write(pointer_path,pointer)
        write(HERE/"installation.json",dict(schema="bg2-trees-native-lighting-installation-v1",
            status="installed-for-ingame-test",installed_utc=v2.utc_now(),
            dll_sha256=report["dll_sha256"],baseline_dll_sha256=report["baseline_dll_sha256"],
            renderer_receipt=dll_result.receipt_path.relative_to(ROOT).as_posix(),areas=results,
            lighting="Read-only owner-correlated CVidPalette::Realize transfer; cache keyed by lighting",
            baked_lighting_removed=True,alpha_geometry_cycles_preserved=True,
            ini_fountains_ar3000_preserved=True,water_compiled_header_identical=True,
            protected_hashes=hashes,qa_status="pending-user-ingame-test",release=False))
    except Exception:
        for result in reversed(results): core.restore_from_receipt(ROOT/result["receipt"],game_root=game)
        if dll_result: renderer.restore_from_receipt(dll_result.receipt_path,game_root=game)
        state.LOCK_PATH.write_bytes(lock_bytes)
        pointer_path.write_bytes(pointer_bytes)
        raise
    print("Corrective DLL and both unlit tree packs installed; user ingame QA pending.")


if __name__ == "__main__": main()
