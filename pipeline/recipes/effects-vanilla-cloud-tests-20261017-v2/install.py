"""Install the six exact Z58 cloud commands on the separate vanilla copy."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "vanilla_cloud_tests_v1",
    ROOT / "pipeline/recipes/effects-vanilla-cloud-tests-20261017-v1/install.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.OUT = ROOT / "effects/installations/vanilla-cloud-tests-20261017-v2"
TESTS = {"Z580269": ("BDWOFOGA", 4, 0), "Z580278": ("SPCLOUDK", 2, 0),
         "Z580290": ("SPCLOUDS", 2, 0), "Z580300": ("SPDFOGA", 1, 0),
         "Z580310": ("SPHORWIA", 2, 8), "Z580315": ("SPHORWIL", 0, 8)}


def prepare(game):
    if base.OUT.exists():
        raise SystemExit("Existing evidence; use install/verify/restore")
    game = base.tx.validate_game_root(game)
    if (game / "InfinityLoader.exe").exists() or (game / "InfinityEngine-Enhancer.dll").exists():
        raise SystemExit("Expected the separate vanilla installation")
    old = json.loads((ROOT / "effects/installations/vanilla-cloud-tests-20261017-v1/installation.json")
                     .read_text(encoding="utf-8"))
    assert old["status"] == "installed" and Path(old["game_root"]).resolve() == game
    preserved = {p: asdict(base.tx.snapshot_file(game / p)) for p in base.BASE_FILES}
    for entry in old["files"]:
        assert base.digest((game / entry["path"]).read_bytes()) == entry["sha256"]
        preserved[entry["path"]] = asdict(base.tx.snapshot_file(game / entry["path"]))
    base.bg2lib.GAME_DIR = str(game); base.bg2lib.KEY_PATH = str(game / "chitin.key")
    bifs, entries = base.bg2lib.load_key()
    index = {(name.upper(), kind): locator for name, kind, locator in entries}
    records, payloads = [], {}
    for vvc, (bam, cycle, display) in TESTS.items():
        path = f"override/{vvc}.vvc"
        assert not (game / path).exists() and (vvc, 1019) not in index
        assert not (game / "override" / f"{bam}.bam").exists()
        native, bif = base.bg2lib.resolve_resource(bifs, index[(bam, 1000)])
        data = zlib.decompress(native[12:]) if native[:8] == b"BAMC V1 " else native
        assert data[:8] == b"BAM V1  " and cycle < data[10]
        frame_count = struct.unpack_from("<H", data, 8)[0]
        cycle_offset = struct.unpack_from("<I", data, 12)[0] + frame_count * 12
        slots, start = struct.unpack_from("<HH", data, cycle_offset + cycle * 4)
        lookup = struct.unpack_from("<I", data, 20)[0]
        assert slots and all(f < frame_count for f in struct.unpack_from(f"<{slots}H", data, lookup + start * 2))
        raw = (base.DONORS / f"{vvc}.vvc").read_bytes()
        assert len(raw) == 0x1EC and raw[:8] == b"VVC V1.0"
        assert raw[8:16].rstrip(b"\0").decode("ascii") == bam
        assert struct.unpack_from("<H", raw, 0x18)[0] == display
        assert struct.unpack_from("<I", raw, 0x68)[0] == cycle + 1
        assert struct.unpack_from("<I", raw, 0x34)[0] == 15
        loop = bool(struct.unpack_from("<I", raw, 0x20)[0] & 1)
        assert loop == (vvc in {"Z580269", "Z580315"})
        assert struct.unpack_from("<I", raw, 0x6C)[0] == (cycle + 1 if loop else 0)
        records.append({"bam": bam, "path": path, "donor": vvc, "cycle": cycle,
                        "native_cycle_slots": slots, "loop": loop, "display_flags": display,
                        "sha256": base.digest(raw), "bytes": len(raw), "before_present": False,
                        "native_bif": bif, "native_bam_sha256": base.digest(native),
                        "clua": f'C:Eval(\'CreateVisualEffectObject("{vvc}",Player1)\',0)'})
        payloads[vvc] = raw
    (base.OUT / "candidate").mkdir(parents=True)
    for name, raw in payloads.items():
        (base.OUT / "candidate" / f"{name}.vvc").write_bytes(raw)
    receipt = {"schema": "bg2-vanilla-cloud-z58-tests-v2", "status": "prepared",
               "game_root": str(game), "created_at_utc": datetime.now(timezone.utc).isoformat(),
               "preserved": preserved, "files": records, "native_assets_replaced": False,
               "game_launched": False, "visual_qa": "pending-user"}
    base.save(receipt)
    print(json.dumps({"status": "prepared", "validated_native_profiles": len(records),
                      "preserved_files": len(preserved)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "install", "verify", "restore"])
    parser.add_argument("--game-root", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        if not args.game_root:
            parser.error("prepare requires --game-root from the vanilla shortcut")
        prepare(args.game_root)
    else:
        base.apply(args.mode)
