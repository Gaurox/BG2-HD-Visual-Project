"""Install T002/T003/T005 night correction; leave all area assets and active area lock exact."""
import json
import sys
from pathlib import Path
import build_renderer as b

ROOT, HERE = b.ROOT, b.HERE
sys.path.insert(0, str(ROOT/"engine/InfinityEngine-Enhancer/source-patchee/tools"))
import install_renderer_candidate as renderer


def write(path, value):
    temp = path.with_suffix(path.suffix+".part")
    temp.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
    temp.replace(path)


def main():
    assert not (HERE/"installation.json").exists()
    report = json.loads((HERE/"runtime.json").read_text(encoding="utf-8"))
    game = b.get_path("bg2ee_game_root",required=True)
    candidate = (ROOT/report["dll"]).parent
    assert b.sha(game/"InfinityEngine-Enhancer.dll") == report["baseline_dll_sha256"]
    assert b.sha(candidate/"InfinityEngine-Enhancer.dll") == report["dll_sha256"]
    assert b.sha(game/"InfinityEngine-Enhancer.ini") == report["ini_sha256"]
    renderer.ensure_game_stopped(renderer.running_game_processes)
    lock_path = ROOT/"animations/index/area-pack-lock.json"
    lock_bytes = lock_path.read_bytes()
    pointer_path = ROOT/"pipeline/water/route2-registry-current.json"
    pointer_bytes = pointer_path.read_bytes()
    pointer = json.loads(pointer_bytes)
    assert pointer["dll_sha256"].lower() == report["baseline_dll_sha256"]
    protected = [game/"InfinityEngine-Enhancer.ini"]
    for area in ("AR1400", "AR1404", "AR3000"):
        protected += [p for p in (game/"iee-assets/areas"/area).rglob("*") if p.is_file()]
    protected += list((game/"override").glob("A3000*.PVRZ"))
    protected += [game/"override"/"AR3000.WED", game/"override"/"AR3000.TIS"]
    hashes = {str(p.relative_to(game)):b.sha(p) for p in protected if p.is_file()}
    renderer.install_candidate(candidate,game_root=game,verify_only=True)
    if "--run" not in sys.argv:
        print("Candidate verified; no installation performed.")
        return
    result = None
    try:
        result = renderer.install_candidate(candidate,game_root=game)
        assert result.status == "installed"
        renderer.verify_transaction(result.receipt_path,game)
        assert b.sha(game/"InfinityEngine-Enhancer.dll") == report["dll_sha256"]
        assert hashes == {str(p.relative_to(game)):b.sha(p) for p in protected if p.is_file()}
        assert lock_bytes == lock_path.read_bytes()
        pointer["dll_sha256"] = report["dll_sha256"].upper()
        pointer["installed_by"] = (HERE/"installation.json").relative_to(ROOT).as_posix()
        pointer["updated"] = "2026-10-11"
        write(pointer_path,pointer)
        write(HERE/"installation.json",dict(schema="bg2-trees-night-color-installation-v2",
            status="installed-for-ingame-test",installed_utc=renderer.utc_now(),
            dll_sha256=report["dll_sha256"],baseline_dll_sha256=report["baseline_dll_sha256"],
            renderer_receipt=result.receipt_path.relative_to(ROOT).as_posix(),
            resrefs=report["resrefs"],rgb_gains=report["rgb_gains"],night_gate=report["night_gate"],
            area_assets_ini_ar3000_unchanged=True,area_pack_lock_unchanged=True,
            water_compiled_header_identical=True,protected_hashes=hashes,
            qa_status="pending-user-ingame-test",release=False))
    except Exception:
        if result:
            renderer.restore_from_receipt(result.receipt_path,game_root=game)
        pointer_path.write_bytes(pointer_bytes)
        raise
    print("T002/T003/T005 night-only DLL installed and verified; area assets and INI unchanged.")


if __name__ == "__main__":
    main()
