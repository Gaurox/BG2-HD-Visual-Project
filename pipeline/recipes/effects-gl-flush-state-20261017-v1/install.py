"""DLL-only installation for the effect native-flush GL-state repair."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "engine/InfinityEngine-Enhancer/source-patchee/tools"
sys.path.insert(0, str(TOOLS))
import install_renderer_candidate as tx

OUTPUT = ROOT / "engine/InfinityEngine-Enhancer/installations/effects-gl-flush-state-20261017-v1"
BUILD = ROOT / "build/iee-effects-gl-flush-state-20261017-v1"
GAME = tx.get_path("bg2ee_game_root", required=True)
PRESERVE = (
    "InfinityEngine-Enhancer.ini", "BaldurReal.exe",
    "override/fpDraw.glsl", "override/fpSprite.glsl", "override/fpSELECT.glsl",
    "iee-assets/creature-sprites/CreatureSprites-XN.catalog",
    "iee-assets/effects/manifest.json", "iee-assets/effects/EffectAnimations-X4.registry",
)


def snapshot(path):
    value = tx.snapshot_file(path)
    return {"bytes": value.bytes, "sha256": value.sha256.upper()}


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def main(mode):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    baseline_path = OUTPUT / "before.json"
    if mode == "prepare":
        write_new(baseline_path, {
            "utc": datetime.now(timezone.utc).isoformat(), "game_root": str(GAME),
            "files": {p: snapshot(GAME / p) for p in ("InfinityEngine-Enhancer.dll", *PRESERVE)},
        })
        print(baseline_path)
        return
    if mode != "install":
        raise SystemExit("Use prepare or install")
    if (OUTPUT / "installation.json").exists():
        raise SystemExit("Installation already recorded; use the transaction receipt for verification/restore")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    for name, old in baseline["files"].items():
        if snapshot(GAME / name) != old:
            raise SystemExit(f"Active file changed since preparation: {name}")
    checks = ["regression-before-fix", "build-fix-v1", "regression-after-fix",
              "registry-tests", "active-catalogue-check"]
    for name in checks:
        result = json.loads((OUTPUT / f"{name}.json").read_text(encoding="utf-8"))
        if not result["expected_result"]:
            raise SystemExit(f"Unsuccessful check: {name}")
        if name != "regression-before-fix":
            for path, digest in result["source_sha256"].items():
                if snapshot(ROOT / path)["sha256"] != digest:
                    raise SystemExit(f"Source changed after check {name}: {path}")
    tx.ensure_game_stopped(tx.running_game_processes)
    candidate = OUTPUT / "candidate"
    candidate.mkdir()
    shutil.copy2(BUILD / "Release/InfinityEngine-Enhancer.dll", candidate / "InfinityEngine-Enhancer.dll")
    shutil.copy2(GAME / "InfinityEngine-Enhancer.ini", candidate / "InfinityEngine-Enhancer.ini")
    result = tx.install_candidate(candidate, game_root=GAME, backup_root=OUTPUT / "backups")
    receipt = tx.verify_transaction(result.receipt_path, game_root=GAME)
    after = {p: snapshot(GAME / p) for p in PRESERVE}
    for name, value in after.items():
        if value != baseline["files"][name]:
            raise RuntimeError(f"Preserved file changed: {name}; receipt: {result.receipt_path}")
    if snapshot(GAME / "InfinityEngine-Enhancer.dll") != snapshot(candidate / "InfinityEngine-Enhancer.dll"):
        raise RuntimeError("Installed DLL differs from candidate")
    record = {
        "schema": "bg2-effects-gl-flush-state-install-v1", "status": "installed-offline-verified",
        "utc": datetime.now(timezone.utc).isoformat(),
        "receipt": result.receipt_path.relative_to(ROOT).as_posix(),
        "transaction_status": receipt["status"], "managed_files": list(result.files),
        "dll": snapshot(GAME / "InfinityEngine-Enhancer.dll"),
        "previous_dll": baseline["files"]["InfinityEngine-Enhancer.dll"],
        "preserved": after, "checks": checks, "game_launched": False,
        "game_and_infinityloader_stopped": True,
        "visual_qa": "pending-user", "release_changed": False,
        "effect_assets_changed": False,
    }
    write_new(OUTPUT / "installation.json", record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
