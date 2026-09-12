"""Repair proven false secondary-alpha seams after a central route-1 candidate.

Default: read-only plan. ``--run`` creates a new immutable candidate. RGB and
alpha outside WED-derived safe interface masks remain byte-exact. No install.
"""
from __future__ import annotations

import argparse
import json
import shutil
import struct
import sys
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import binary_erosion

from area_decode import decode_tis_tiles
from bg2lib import load_key, resolve_resource
from build_water_route1_batch import (ROOT, aggregate, load_json, parse_pvr,
                                      parse_standalone_tis, parse_wed, rel,
                                      sha256_bytes, sha256_file, write_json)


DEFAULT_MATRIX = ROOT / ".tmp" / "water-phase23-20260912" / "matrix.json"
DEFAULT_PARENT = (ROOT / "maps" / "water-batches" / "runs" /
                  "voie1-alpha128-x4-20260912-v3" / "repair-report.json")
DEFAULT_RUN = (ROOT / "maps" / "water-batches" / "runs" /
               "voie1-secondary-alpha-seams-x4-20260912-v1")
ALPHA255 = bytes((255, 255, 0, 0, 0, 0, 0, 0))
OPPOSITE = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}


def block_mask(mask: np.ndarray) -> np.ndarray:
    if mask.shape != (264, 264):
        raise RuntimeError("masque de tuile/padding inattendu")
    return mask.reshape(66, 4, 66, 4).any(axis=(1, 3))


def add_band(target: np.ndarray, side: str, valid: np.ndarray) -> None:
    along = np.repeat(valid, 4)
    for distance in range(8):
        if side == "left":
            target[:, distance] |= along
        elif side == "right":
            target[:, 255 - distance] |= along
        elif side == "top":
            target[distance, :] |= along
        else:
            target[255 - distance, :] |= along


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--parent-report", type=Path, default=DEFAULT_PARENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    rows = load_json(args.matrix)
    parent = load_json(args.parent_report)
    parent_by_wed = {row["wed"]: row for row in parent["results"] if row.get("candidate")}
    targets = []
    for row in rows:
        count = int(row["base_diagnostics"]["interface_heuristic"].get("secondary_alpha_drop", 0))
        if not count:
            continue
        candidate = parent_by_wed.get(row["wed"])
        if not candidate:
            raise RuntimeError(f"candidat central absent: {row['wed']}")
        slot = next(item for item in candidate["slots"] if item["slot"] == row["overlay_slot"])
        targets.append({"wed": row["wed"], "slot": row["overlay_slot"],
                        "overlay": row["overlay_resref"], "expected_interfaces": count,
                        "primary_ids": slot["qualified_ids"], "parent": candidate["candidate"]})
    plan = {"schema": "bg2-water-secondary-alpha-seam-plan-v1",
            "matrix_sha256": sha256_file(args.matrix),
            "parent_report_sha256": sha256_file(args.parent_report),
            "targets": targets}
    if not args.run:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0
    output = args.output.resolve()
    if ROOT not in output.parents or output.exists():
        raise RuntimeError(f"sortie hors workspace ou déjà existante: {output}")
    output.mkdir(parents=True)
    write_json(output / "request.json", {**plan, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                                          "producer": rel(Path(__file__)),
                                          "producer_sha256": sha256_file(Path(__file__))})
    bifs, resources = load_key()
    lookup = {(name.upper(), kind): locator for name, kind, locator in resources}
    pvr_lookup = {name.upper(): (name, kind, locator) for name, kind, locator in resources if kind == 0x404}
    results = []
    for target in targets:
        wed = target["wed"]
        wed_data, archive = resolve_resource(bifs, lookup[(wed, 0x3E9)])
        parsed = parse_wed(wed_data)
        layer = parsed["layers"][target["slot"]]
        bit = 1 << target["slot"]
        tis_resref = parsed["layers"][0]["tis"]
        stock_tile, _ = decode_tis_tiles(bifs, pvr_lookup, tis_resref, lookup[(tis_resref, 0x3EB)])
        width, height = parsed["layers"][0]["width"], parsed["layers"][0]["height"]
        by_xy = {(cell["x"], cell["y"]): cell for cell in parsed["cells"]}
        primary_uses = Counter(tile for cell in parsed["cells"] for tile in cell["primary"])
        secondary_uses = Counter(cell["secondary"] for cell in parsed["cells"] if cell["secondary"] != 0xFFFF)
        if max(primary_uses.values()) != 1 or max(secondary_uses.values()) != 1 \
                or set(primary_uses) & set(secondary_uses):
            raise RuntimeError(f"{wed}: réutilisation de slots non prise en charge")
        water = np.zeros((height * 64, width * 64), dtype=bool)
        for cell in parsed["cells"]:
            if not (cell["flags"] & bit) or cell["count"] != 1:
                continue
            primary = np.array(stock_tile(cell["primary"][0]).getchannel("A"))
            if cell["secondary"] == 0xFFFF:
                valid = np.ones((64, 64), dtype=bool) if cell["primary"][0] in target["primary_ids"] else primary == 255
            else:
                secondary = np.array(stock_tile(cell["secondary"]).getchannel("A"))
                valid = (primary == 0) & (secondary == 255)
            top, left = cell["y"] * 64, cell["x"] * 64
            water[top:top + 64, left:left + 64] = valid
        safe = binary_erosion(water, structure=np.ones((3, 3), bool), border_value=0)
        masks: dict[int, np.ndarray] = {}
        tile_cells: dict[int, tuple[int, int]] = {}
        interfaces = []
        for cell in parsed["cells"]:
            if cell["count"] != 1 or cell["primary"][0] not in target["primary_ids"]:
                continue
            own = safe[cell["y"] * 64:(cell["y"] + 1) * 64,
                       cell["x"] * 64:(cell["x"] + 1) * 64]
            for side, dx, dy in (("left", -1, 0), ("right", 1, 0),
                                 ("top", 0, -1), ("bottom", 0, 1)):
                neighbor = by_xy.get((cell["x"] + dx, cell["y"] + dy))
                if not neighbor or not (neighbor["flags"] & bit) or neighbor["secondary"] == 0xFFFF:
                    continue
                other = safe[neighbor["y"] * 64:(neighbor["y"] + 1) * 64,
                             neighbor["x"] * 64:(neighbor["x"] + 1) * 64]
                if side == "left":
                    valid = own[:, :2].all(axis=1) & other[:, -2:].all(axis=1)
                elif side == "right":
                    valid = own[:, -2:].all(axis=1) & other[:, :2].all(axis=1)
                elif side == "top":
                    valid = own[:2, :].all(axis=0) & other[-2:, :].all(axis=0)
                else:
                    valid = own[-2:, :].all(axis=0) & other[:2, :].all(axis=0)
                if not valid.any():
                    continue
                secondary_id = neighbor["secondary"]
                mask = masks.setdefault(secondary_id, np.zeros((256, 256), dtype=bool))
                add_band(mask, OPPOSITE[side], valid)
                tile_cells[secondary_id] = (neighbor["x"], neighbor["y"])
                interfaces.append({"primary": cell["primary"][0], "secondary": secondary_id,
                                   "side": side, "positions": int(valid.sum())})
        if len(interfaces) != target["expected_interfaces"]:
            raise RuntimeError(f"{wed}: interfaces sûres={len(interfaces)}, matrice={target['expected_interfaces']}")
        parent_dir = ROOT / target["parent"]
        candidate = output / "candidates" / wed
        shutil.copytree(parent_dir, candidate)
        tis = parse_standalone_tis((candidate / f"{tis_resref}.TIS").read_bytes())
        by_page: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
        for tile, mask in masks.items():
            page, x, y = tis["entries"][tile]
            by_page[page].append((tile, x, y))
        page_reports = []
        total = 0
        prefix = tis_resref[0] + tis_resref[2:]
        for page, page_tiles in by_page.items():
            path = candidate / f"{prefix}{page:02d}.PVRZ"
            packed = path.read_bytes()
            raw, fmt, page_width, page_height, offset = parse_pvr(packed)
            if fmt != 11:
                raise RuntimeError(f"{path.name}: DXT5 requis")
            before = bytes(raw)
            columns = page_width // 4
            changed: set[int] = set()
            for tile, x, y in page_tiles:
                if (x % 264, y % 264) != (4, 4):
                    raise RuntimeError(f"{wed} secondary {tile}: padding non prouvé")
                selected = block_mask(np.pad(masks[tile], 4, mode="edge"))
                for by, bx in np.argwhere(selected):
                    block = ((y - 4) // 4 + int(by)) * columns + ((x - 4) // 4 + int(bx))
                    start = offset + block * 16
                    raw[start:start + 8] = ALPHA255
                    changed.add(block)
            for block in range((page_width // 4) * (page_height // 4)):
                start = offset + block * 16
                if raw[start + 8:start + 16] != before[start + 8:start + 16]:
                    raise RuntimeError(f"{path.name}: RGB modifié")
                if block not in changed and raw[start:start + 8] != before[start:start + 8]:
                    raise RuntimeError(f"{path.name}: alpha hors masque modifié")
            output_data = struct.pack("<I", len(raw)) + zlib.compress(raw, 9)
            path.write_bytes(output_data)
            total += len(changed)
            page_reports.append({"name": path.name, "secondary_tiles": len(page_tiles),
                                 "alpha_blocks": len(changed),
                                 "source_sha256": sha256_bytes(packed),
                                 "sha256": sha256_bytes(output_data)})
        files = [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
                 for path in candidate.iterdir() if path.is_file()]
        results.append({"wed": wed, "variant": "day-or-unique",
                        "status": "route1-corrected-candidate-pending-family-qa",
                        "candidate": rel(candidate), "source_wed_archive": archive,
                        "target_primary_ids": target["primary_ids"],
                        "secondary_tiles": sorted(masks), "interfaces": interfaces,
                        "modified_alpha_blocks": total, "rgb_blocks_modified": 0,
                        "other_alpha_blocks_modified": 0, "pages": page_reports,
                        "files": sorted(files, key=lambda row: row["name"]),
                        "candidate_set_sha256": aggregate(files),
                        "residual_non_route1_gate": "restore WTSWAM stock overlay before QA"})
        print(f"{wed}: {len(interfaces)} interfaces, {len(masks)} secondaires, {total} blocs alpha", flush=True)
    report = {"schema": "bg2-water-secondary-alpha-seam-result-v1",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "installation": "not-run", "release": "not-requested", "results": results}
    write_json(output / "repair-report.json", report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
