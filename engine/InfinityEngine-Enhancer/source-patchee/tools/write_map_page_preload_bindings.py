"""Write B1.3 tile bindings from an existing B1 private cache; never overwrite it."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


def write_bindings(cache: Path, output: Path) -> int:
    manifest = json.loads((cache / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or manifest.get("area") != "AR0900":
        raise ValueError("Only B1 AR0900 manifests are supported")
    pages = manifest["pages"]
    if not 0 < len(pages) <= 96:
        raise ValueError("Page count outside native reserve")
    expected_index = ["IEE_PRIVATE_PVRZ_V1", f"AREA AR0900 {len(manifest['overlays'])}",
                      "OVERLAYS " + " ".join(manifest["overlays"])]
    rows = ["IEE_PRELOAD_BINDINGS_V1 AR0900"]
    for name, page in pages.items():
        tis, number, tile = page["tis"], page["page"], page["first_tile"]
        if (not re.fullmatch(r"[A-Z0-9_]{2,8}", tis)
                or tis not in manifest["overlays"]
                or type(number) is not int or number < 0
                or type(tile) is not int or not 0 <= tile < 1048576
                or not re.fullmatch(r"[A-Z0-9_]{1,8}", name)
                or name != tis[0] + tis[2:] + f"{number:02d}"):
            raise ValueError(f"Invalid binding: {name}")
        expected_index.append(f"PAGE {name} {page['bytes']} {page['decoded_bytes']} {page['crc32']}")
        rows.append(f"PAGE {name} {tis} {number} {tile}")
    if (cache / "pages.index").read_text(encoding="ascii").splitlines() != expected_index:
        raise ValueError("Manifest and native B1 index disagree")
    # Exclusive creation: installed / historical binding files remain immutable.
    with output.open("x", encoding="ascii", newline="\n") as stream:
        stream.write("\n".join(rows) + "\n")
    return len(pages)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(f"bindings={write_bindings(args.cache, args.output)} output={args.output}")
