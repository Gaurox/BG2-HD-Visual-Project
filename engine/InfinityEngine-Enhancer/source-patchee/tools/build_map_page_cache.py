"""Build a new private AR0900 PVRZ cache, never modify installed resources.

Override-only candidate: unknown/missing dependencies fail closed. All TIS
entries are inventoried (including door/animation alternatives); table order
is deterministic, not spatial prioritization. Run with game/loader closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import zlib

from install_renderer_candidate import ensure_game_stopped, running_game_processes

RESREF = re.compile(r"[A-Z0-9_]{1,8}\Z")
MAX_FILE = 32 * 1024 * 1024
MAX_DECODED = 20 * 1024 * 1024
MAX_DISK = 512 * 1024 * 1024


def resref(value: bytes) -> str:
    result = value.split(b"\0", 1)[0].decode("ascii").upper()
    if not RESREF.fullmatch(result):
        raise ValueError(f"Invalid resref: {result!r}")
    return result


def build(override: Path, output: Path, validator: Path) -> dict:
    ensure_game_stopped(running_game_processes)
    if output.exists():
        raise ValueError("Output must be a new directory; old candidates are immutable")
    if output.resolve().is_relative_to(override.resolve()):
        raise ValueError("Private cache must be outside override")
    files: dict[str, dict] = {}

    def read(name: str, maximum: int = MAX_FILE) -> bytes:
        path = override / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
            raise ValueError(f"Unsupported or missing override resource: {name}")
        data = path.read_bytes()
        files[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        return data

    wed = read("AR0900.WED")
    if wed[:8] != b"WED V1.3" or len(wed) < 32:
        raise ValueError("Expected WED V1.3")
    count, = struct.unpack_from("<I", wed, 8)
    offset, = struct.unpack_from("<I", wed, 16)
    if not 1 <= count <= 5 or offset < 32 or offset + 24 * count > len(wed):
        raise ValueError("Invalid overlay table")
    overlays = []
    pages = {}
    for index in range(count):
        width, height, raw_tis = struct.unpack_from("<HH8s", wed, offset + index * 24)
        tis_name = resref(raw_tis) if width and height else "-"
        overlays.append(tis_name)
        if tis_name == "-":
            continue
        tis = read(tis_name + ".TIS")
        if tis[:8] != b"TIS V1  " or len(tis) < 24:
            raise ValueError(f"Expected TIS V1: {tis_name}")
        tiles, size, start, dimension = struct.unpack_from("<4I", tis, 8)
        if size != 12 or start < 24 or dimension not in (64, 128, 256) or not 0 < tiles <= 1048576 or start + tiles * size > len(tis):
            raise ValueError(f"Unsupported PVRZ TIS: {tis_name}")
        for tile in range(tiles):
            page, = struct.unpack_from("<i", tis, start + 12 * tile)
            if page < 0:
                continue
            page_name = tis_name[0] + tis_name[2:] + f"{page:02d}"
            if not RESREF.fullmatch(page_name):
                raise ValueError(f"Invalid page: {page_name}")
            pages.setdefault(page_name, {"tis": tis_name, "page": page, "first_tile": tile})
    if not 0 < len(pages) <= 96:
        raise ValueError("Page count outside candidate bound")
    output.mkdir(parents=True)
    rows = ["IEE_PRIVATE_PVRZ_V1", f"AREA AR0900 {len(overlays)}", "OVERLAYS " + " ".join(overlays)]
    total = 0
    for name, entry in pages.items():
        ensure_game_stopped(running_game_processes)
        data = read(name + ".PVRZ")
        total += len(data)
        if total > MAX_DISK or len(data) < 6:
            raise ValueError("Cache disk bound or envelope rejected")
        decoded, = struct.unpack_from("<I", data)
        if not 52 <= decoded <= MAX_DECODED:
            raise ValueError(f"Decoded bound rejected: {name}")
        target = output / (name + ".b1pvrz")
        # write_bytes creates independent bytes, never a link to override.
        target.write_bytes(data)
        checked = subprocess.run([str(validator), str(target)], capture_output=True, text=True, check=True)
        entry.update(files[name + ".PVRZ"], decoded_bytes=decoded,
                     crc32=zlib.crc32(data[4:]), validation=checked.stdout.strip())
        rows.append(f"PAGE {name} {len(data)} {decoded} {entry['crc32']}")
    manifest = {"schema": 1, "area": "AR0900", "overlays": overlays,
                "source": str(override.resolve()), "dependencies": files,
                "pages": pages, "private_bytes": total,
                "ordering": "overlay then first TIS occurrence; all entries"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # Runtime commit marker last. Partial builds never have a loadable index.
    (output / "pages.index").write_text("\n".join(rows) + "\n", encoding="ascii")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--override", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validator", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.override, args.output, args.validator)
    print(json.dumps({"area": result["area"], "pages": len(result["pages"]),
                      "private_bytes": result["private_bytes"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
