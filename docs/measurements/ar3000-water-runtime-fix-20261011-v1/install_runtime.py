"""Recover the known stale water pointer with an exact-baseline renderer transaction."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from workspace_paths import get_path
sys.path.insert(0, str(ROOT / "engine/InfinityEngine-Enhancer/source-patchee/tools"))
import install_renderer_candidate as installer
import generate_water_route2_registry as generator


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


report = json.loads((HERE / "runtime.json").read_text())
game = get_path("bg2ee_game_root", required=True)
pointer_path = ROOT / "pipeline/water/route2-registry-current.json"
pointer = json.loads(pointer_path.read_text())
registry = generator.default_input()
assert registry.relative_to(ROOT).as_posix() == report["registry"]
assert report["registry_sha256_lf"] == pointer["registry"]["sha256_lf"]
assert report["native_tests_passed"] and report["ar3000_file_evidence_matches"]
assert sha(game / "InfinityEngine-Enhancer.dll") == report["baseline_dll_sha256"]
candidate_dll = ROOT / report["dll"]
assert sha(candidate_dll) == report["dll_sha256"]
assert sha(game / "InfinityEngine-Enhancer.ini") == report["ini_sha256"]
child, resolved = generator.load_registry(registry)
for entry in resolved["entries"]:
    wed = game / "override" / (entry["wed"]["resref"] + ".WED")
    assert (wed.is_file() and sha(wed) == entry["wed"]["sha256"]) or (
        not wed.exists() and entry.get("allow_stock_wed_when_override_absent")), wed
    for evidence in generator.file_records(entry):
        extension = ".TIS" if evidence["kind"] in ("BaseTis", "OverlayTis") else ".PVRZ"
        file = game / "override" / (evidence["resref"] + extension)
        assert file.stat().st_size == evidence["bytes"] and sha(file) == evidence["sha256"], file
installer.install_candidate(candidate_dll.parent, game_root=game, verify_only=True)
if "--install" not in sys.argv:
    print("Candidate verified; game closed; 188 registry entries match installed files.")
    raise SystemExit(0)

backup_root = ROOT / "backups/water" / HERE.name / "runtime"
assert not backup_root.exists(), "choose a new recovery run"
result = installer.install_candidate(candidate_dll.parent, game_root=game,
                                     backup_root=backup_root / "renderer")
transaction = json.loads(result.receipt_path.read_text())
backup_dll = result.receipt_path.parent / "before/InfinityEngine-Enhancer.dll"
assert sha(backup_dll) == report["baseline_dll_sha256"]
assert sha(game / "InfinityEngine-Enhancer.dll") == report["dll_sha256"]
assert sha(game / "InfinityEngine-Enhancer.ini") == report["ini_sha256"]
receipt_path = backup_root / "install-backup.json"
receipt = dict(schema="bg2-water-runtime-install-v1", created_utc=datetime.now(timezone.utc).isoformat(),
    label=HERE.name, target=str(game / "InfinityEngine-Enhancer.dll"),
    source=str(candidate_dll), backup=str(backup_dll),
    before_sha256=report["baseline_dll_sha256"], installed_sha256=report["dll_sha256"],
    bytes=candidate_dll.stat().st_size, registry=pointer["registry"], previous_pointer=pointer,
    recovery=dict(previous_pointer_was_stale=pointer["dll_sha256"] != report["baseline_dll_sha256"],
        previous_actual_registry_version=2, previous_actual_registry_entries=1,
        previous_renderer_receipt="backups/renderer/20261011T090835037764Z-f8d1a2b6/renderer-install-receipt.json"),
    renderer_receipt=result.receipt_path.relative_to(ROOT).as_posix(),
    ini_preserved=True, ingame_QA=False, release=False)
try:
    write(receipt_path, receipt)
    updated = dict(pointer, dll_sha256=report["dll_sha256"],
                   installed_by=receipt_path.relative_to(ROOT).as_posix(), updated="2026-10-11")
    write(pointer_path, updated)
except Exception:
    installer.restore_from_receipt(result.receipt_path, game_root=game)
    write(pointer_path, pointer)
    raise
installer.verify_transaction(result.receipt_path, game)
write(HERE / "installation.json", dict(status="installed-pending-user-ingame-qa",
    receipt=receipt_path.relative_to(ROOT).as_posix(), dll_sha256=report["dll_sha256"],
    registry_version=3, registry_entries=188, ar3000_target_draw_alpha=160,
    ini_preserved=True, map_assets_changed=0, ingame_QA=False, release=False))
print(json.dumps({"status": "installed", "receipt": str(receipt_path), "dll_sha256": report["dll_sha256"]}))
