"""Four reversible VVC-only tests; vanilla BAMs and gameplay files stay native."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
sys.path.insert(0, str(ROOT / "engine/InfinityEngine-Enhancer/source-patchee/tools"))
import bg2lib
import install_renderer_candidate as tx

OUT = ROOT / "effects/installations/vanilla-cloud-tests-20261017-v1"
DONORS = ROOT / "effects/installations/lot58-7b-x4-nearest30-20261017-v1/candidate/override"
TESTS = {"BDWOFOGA": "Z580269", "SPCLOUDK": "Z580278",
         "SPCLOUDS": "Z580290", "SPDFOGA": "Z580300"}
BASE_FILES = ("Baldur.exe", "chitin.key", "engine.lua")


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def save(value):
    path = OUT / "installation.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def target_processes(game):
    # The HD copy can stay open: only the target vanilla process owns these
    # files. Unknown process paths fail closed rather than being ignored.
    command = ('Get-CimInstance Win32_Process -Filter '
               '"Name = \'Baldur.exe\' OR Name = \'BaldurReal.exe\' OR Name = \'InfinityLoader.exe\'" '
               '| Select-Object Name,ExecutablePath | ConvertTo-Json -Compress')
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                            check=True, capture_output=True, text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    rows = json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(rows, dict):
        rows = [rows]
    return [row["Name"] for row in rows if not row.get("ExecutablePath") or
            Path(row["ExecutablePath"]).resolve().parent == game]


def prepare(game):
    if OUT.exists():
        raise SystemExit("Existing installation evidence; use install/verify/restore")
    game = tx.validate_game_root(game)
    if (game / "InfinityLoader.exe").exists() or (game / "InfinityEngine-Enhancer.dll").exists():
        raise SystemExit("Expected the separate vanilla installation")
    bg2lib.GAME_DIR = str(game); bg2lib.KEY_PATH = str(game / "chitin.key")
    bifs, resources = bg2lib.load_key()
    index = {(name.upper(), kind): locator for name, kind, locator in resources}
    records = []
    for bam, donor in TESTS.items():
        target = game / "override" / f"{bam}.vvc"
        if target.exists() or (bam, 1019) in index:
            raise SystemExit(f"Existing VVC would be shadowed: {bam}")
        if (game / "override" / f"{bam}.bam").exists():
            raise SystemExit(f"Expected official BAM from BIF: {bam}")
        native, bif = bg2lib.resolve_resource(bifs, index[(bam, 1000)])
        data = zlib.decompress(native[12:]) if native[:8] == b"BAMC V1 " else native
        if data[:8] != b"BAM V1  ":
            raise SystemExit(f"Unexpected native BAM format: {bam}")
        frame_count = struct.unpack_from("<H", data, 8)[0]
        cycle_count = data[10]
        cycle_offset = struct.unpack_from("<I", data, 12)[0] + frame_count * 12
        raw = (DONORS / f"{donor}.vvc").read_bytes()
        assert len(raw) == 0x1EC and raw[:8] == b"VVC V1.0"
        assert raw[8:16].rstrip(b"\0").decode("ascii") == bam
        # These are the normal-alpha controllers already used for these clouds.
        assert struct.unpack_from("<H", raw, 0x18)[0] == 0
        cycle = struct.unpack_from("<I", raw, 0x68)[0] - 1
        assert 0 <= cycle < cycle_count
        slots, first_slot = struct.unpack_from("<HH", data, cycle_offset + cycle * 4)
        lookup_offset = struct.unpack_from("<I", data, 20)[0]
        frames = struct.unpack_from(f"<{slots}H", data, lookup_offset + first_slot * 2)
        assert slots and all(frame < frame_count for frame in frames)
        assert struct.unpack_from("<I", raw, 0x34)[0] == 15
        records.append({"bam": bam, "path": f"override/{bam}.vvc", "donor": donor,
                        "sha256": digest(raw), "bytes": len(raw), "before_present": False,
                        "cycle": cycle, "native_cycle_slots": slots, "native_bif": bif,
                        "native_bam_sha256": digest(native),
                        "hd_clua": f'C:Eval(\'CreateVisualEffectObject("{donor}",Player1)\',0)',
                        "vanilla_clua": f'C:Eval(\'CreateVisualEffectObject("{bam}",Player1)\',0)'})
    OUT.mkdir(parents=True)
    (OUT / "candidate").mkdir()
    for entry in records:
        raw = (DONORS / f'{entry["donor"]}.vvc').read_bytes()
        assert digest(raw) == entry["sha256"]
        (OUT / "candidate" / Path(entry["path"]).name).write_bytes(raw)
    receipt = {"schema": "bg2-vanilla-cloud-vvc-tests-v1", "status": "prepared",
               "game_root": str(game), "created_at_utc": datetime.now(timezone.utc).isoformat(),
               "preserved": {p: asdict(tx.snapshot_file(game / p)) for p in BASE_FILES},
               "files": records, "native_assets_replaced": False, "game_launched": False,
               "visual_qa": "pending-user"}
    save(receipt)
    print(json.dumps(receipt, indent=2))


def apply(mode):
    receipt = json.loads((OUT / "installation.json").read_text(encoding="utf-8"))
    game = tx.validate_game_root(Path(receipt["game_root"]))
    for name, before in receipt["preserved"].items():
        if asdict(tx.snapshot_file(game / name)) != before:
            raise SystemExit(f"Vanilla base file changed: {name}")
    if mode in {"install", "restore"}:
        tx.ensure_game_stopped(lambda: target_processes(game))
    if mode == "install":
        assert receipt["status"] in {"prepared", "installing"}
        receipt["status"] = "installing"; save(receipt)
        for entry in receipt["files"]:
            target = game / entry["path"]
            source = OUT / "candidate" / target.name
            expected = tx.FileSnapshot(entry["bytes"], entry["sha256"])
            if target.exists() and digest(target.read_bytes()) != entry["sha256"]:
                raise SystemExit(f"Refusing to replace another file: {target}")
            target.parent.mkdir(exist_ok=True)
            tx.atomic_copy(source, target, expected)
        receipt["status"] = "installed"
        receipt["installed_at_utc"] = datetime.now(timezone.utc).isoformat()
        receipt["game_and_infinityloader_stopped"] = True
        save(receipt)
    elif mode == "restore":
        for entry in receipt["files"]:
            target = game / entry["path"]
            if target.exists():
                if digest(target.read_bytes()) != entry["sha256"]:
                    raise SystemExit(f"Refusing to remove modified file: {target}")
                target.unlink()
        receipt["status"] = "restored"; save(receipt)
    expected_present = receipt["status"] == "installed"
    assert receipt["status"] in {"installed", "restored"}
    for entry in receipt["files"]:
        target = game / entry["path"]
        assert target.exists() == expected_present
        if expected_present:
            assert len(target.read_bytes()) == entry["bytes"] and digest(target.read_bytes()) == entry["sha256"]
    print(json.dumps({"status": receipt["status"], "verified_files": len(receipt["files"]),
                      "preserved_base_files": len(receipt["preserved"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "install", "verify", "restore"])
    parser.add_argument("--game-root", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        if not args.game_root:
            parser.error("prepare requires --game-root (resolved from the user's shortcut)")
        prepare(args.game_root)
    else:
        apply(args.mode)
