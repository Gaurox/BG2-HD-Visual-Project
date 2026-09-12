"""Build immutable alpha128 route-1 candidates from proven live x4 divergences.

Default mode is read-only. ``--run`` writes only below the requested run root.
It never installs, tests, invokes SeedVR, changes release state or edits sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
import zlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bg2lib import load_key, resolve_resource, resolve_tileset_resource
from workspace_paths import get_path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATRIX = ROOT / ".tmp" / "water-phase23-20260912" / "matrix.json"
DEFAULT_FAMILY = ROOT / "pipeline" / "water" / "family-policy-v1.json"
DEFAULT_POLICY = ROOT / "pipeline" / "water" / "route1-policy-v1.json"
DEFAULT_RUN = ROOT / "maps" / "water-batches" / "runs" / "voie1-alpha128-x4-20260912-v3"
ALPHA128 = bytes((128, 128, 0, 0, 0, 0, 0, 0))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def aggregate(files: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for item in sorted(files, key=lambda row: row["name"].upper()):
        digest.update(item["name"].upper().encode("ascii"))
        digest.update(b"\0")
        digest.update(str(item["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(item["sha256"].upper().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest().upper()


def parse_wed(data: bytes) -> dict[str, Any]:
    if data[:4] != b"WED ":
        raise RuntimeError("signature WED invalide")
    layer_count, _, overlay_offset = struct.unpack_from("<III", data, 8)
    layers = []
    for slot in range(layer_count):
        offset = overlay_offset + slot * 24
        width, height = struct.unpack_from("<HH", data, offset)
        tis = data[offset + 4:offset + 12].split(b"\0")[0].decode("ascii").upper()
        tilemap, lookup = struct.unpack_from("<II", data, offset + 16)
        layers.append({"slot": slot, "width": width, "height": height,
                       "tis": tis, "tilemap": tilemap, "lookup": lookup})
    base = layers[0]
    cells = []
    secondary_ids: set[int] = set()
    for index in range(base["width"] * base["height"]):
        start, count, secondary, flags = struct.unpack_from(
            "<HHHB3x", data, base["tilemap"] + index * 10)
        primary = [struct.unpack_from("<H", data, base["lookup"] + (start + frame) * 2)[0]
                   for frame in range(count)]
        if secondary != 0xFFFF:
            secondary_ids.add(secondary)
        cells.append({"primary": primary, "secondary": secondary, "flags": flags,
                      "count": count, "x": index % base["width"],
                      "y": index // base["width"]})
    return {"layers": layers, "cells": cells, "secondary_ids": secondary_ids}


def parse_standalone_tis(data: bytes) -> dict[str, Any]:
    if data[:8] != b"TIS V1  ":
        raise RuntimeError("signature TIS standalone invalide")
    count, entry_size, header_size, dimension = struct.unpack_from("<4I", data, 8)
    if entry_size != 12 or dimension != 256 or len(data) != header_size + count * entry_size:
        raise RuntimeError("seul le layout PVRZ x4 TIS/12/256 est accepté")
    entries = [struct.unpack_from("<3I", data, header_size + index * entry_size)
               for index in range(count)]
    return {"count": count, "dimension": dimension, "entries": entries}


def parse_pvr(data: bytes) -> tuple[bytearray, int, int, int, int]:
    if len(data) < 5:
        raise RuntimeError("PVRZ tronqué")
    expected = struct.unpack_from("<I", data)[0]
    raw = bytearray(zlib.decompress(data[4:]))
    if len(raw) != expected or struct.unpack_from("<I", raw)[0] != 0x03525650:
        raise RuntimeError("PVRZ/PVRv3 invalide")
    pixel_format = struct.unpack_from("<Q", raw, 8)[0]
    height, width = struct.unpack_from("<II", raw, 24)
    if struct.unpack_from("<4I", raw, 32) != (1, 1, 1, 1):
        raise RuntimeError("PVR multi-surface/mip non supporté")
    offset = 52 + struct.unpack_from("<I", raw, 48)[0]
    block_bytes = {7: 8, 11: 16}.get(pixel_format)
    if block_bytes is None or width % 4 or height % 4:
        raise RuntimeError(f"format PVR non supporté: {pixel_format}")
    if len(raw) != offset + (width // 4) * (height // 4) * block_bytes:
        raise RuntimeError("taille de flux DXT invalide")
    return raw, int(pixel_format), width, height, offset


def dxt5_palette(block: bytes | bytearray) -> tuple[list[int], int]:
    a0, a1 = block[0], block[1]
    if a0 > a1:
        palette = [a0, a1] + [((7 - index) * a0 + (index - 1) * a1) // 7
                              for index in range(2, 8)]
    else:
        palette = [a0, a1] + [((5 - index) * a0 + (index - 1) * a1) // 5
                              for index in range(2, 6)] + [0, 255]
    return palette, int.from_bytes(block[2:8], "little")


def block_alpha_constant(block: bytes | bytearray, pixel_format: int, value: int) -> bool:
    if pixel_format == 7:
        # Infinity PVR7 is the opaque RGB/DXT1 source contract. Its fourth channel
        # is supplied by the draw path, not by BC1's optional transparent index.
        return value == 255
    palette, indices = dxt5_palette(block)
    return all(palette[(indices >> (3 * index)) & 7] == value for index in range(16))


def tile_alpha_constant(raw: bytes | bytearray, pixel_format: int, width: int,
                        offset: int, x: int, y: int, dimension: int, value: int) -> bool:
    block_bytes = 8 if pixel_format == 7 else 16
    columns = width // 4
    for py in range(y // 4, (y + dimension) // 4):
        for px in range(x // 4, (x + dimension) // 4):
            start = offset + (py * columns + px) * block_bytes
            if not block_alpha_constant(raw[start:start + block_bytes], pixel_format, value):
                return False
    return True


def source_pages(bifs: list[str], lookup: dict[tuple[str, int], int], tis_resref: str,
                 source_tis: bytes, source_count: int, source_size: int,
                 ids: set[int]) -> tuple[set[int], dict[int, tuple[bytes, int, int, int, int]]]:
    if source_size != 12:
        return set(), {}
    prefix = tis_resref[0] + tis_resref[2:]
    entries = {tile: struct.unpack_from("<3I", source_tis, tile * 12) for tile in ids
               if tile < source_count}
    pages: dict[int, tuple[bytes, int, int, int, int]] = {}
    for page, _, _ in entries.values():
        if page == 0xFFFFFFFF or page in pages:
            continue
        name = f"{prefix}{page:02d}".upper()
        packed, _ = resolve_resource(bifs, lookup[(name, 0x404)])
        pages[page] = parse_pvr(packed)
    qualified = set()
    for tile, (page, x, y) in entries.items():
        if page == 0xFFFFFFFF:
            continue
        raw, fmt, width, height, offset = pages[page]
        if fmt == 7 and x + 64 <= width and y + 64 <= height:
            qualified.add(tile)
    return qualified, pages


def eligible_primary_ids(parsed: dict[str, Any], slot: int) -> set[int]:
    bit = 1 << slot
    uses: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for cell in parsed["cells"]:
        for tile in cell["primary"]:
            uses[tile].append(cell)
    return {tile for tile, rows in uses.items()
            if tile not in parsed["secondary_ids"]
            and all((row["flags"] & bit) and row["secondary"] == 0xFFFF for row in rows)}


def current_alpha0_ids(override: Path, tis_resref: str, tis: dict[str, Any],
                       ids: set[int]) -> set[int]:
    prefix = tis_resref[0] + tis_resref[2:]
    by_page: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for tile in ids:
        if tile >= tis["count"]:
            continue
        page, x, y = tis["entries"][tile]
        if page != 0xFFFFFFFF:
            by_page[page].append((tile, x, y))
    selected = set()
    for page, rows in by_page.items():
        raw, fmt, width, height, offset = parse_pvr((override / f"{prefix}{page:02d}.PVRZ").read_bytes())
        if fmt != 11:
            continue
        for tile, x, y in rows:
            if x + 256 <= width and y + 256 <= height and x % 4 == y % 4 == 0 \
                    and tile_alpha_constant(raw, fmt, width, offset, x, y, 256, 0):
                selected.add(tile)
    return selected


def patch_candidate(source: Path, output: Path, tis_resref: str, tis: dict[str, Any],
                    targets: set[int]) -> tuple[list[dict[str, Any]], int]:
    output.mkdir(parents=True)
    tis_name = f"{tis_resref}.TIS"
    shutil.copy2(source / tis_name, output / tis_name)
    prefix = tis_resref[0] + tis_resref[2:]
    all_pages = sorted({page for page, _, _ in tis["entries"] if page != 0xFFFFFFFF})
    by_page: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for tile in targets:
        page, x, y = tis["entries"][tile]
        by_page[page].append((tile, x, y))
    reports = []
    total_blocks = 0
    for page in all_pages:
        name = f"{prefix}{page:02d}.PVRZ"
        source_path, output_path = source / name, output / name
        packed = source_path.read_bytes()
        if page not in by_page:
            shutil.copy2(source_path, output_path)
            reports.append({"name": name, "tiles": 0, "alpha_blocks": 0,
                            "source_sha256": sha256_bytes(packed),
                            "sha256": sha256_bytes(packed)})
            continue
        raw, fmt, width, height, offset = parse_pvr(packed)
        if fmt != 11:
            raise RuntimeError(f"{name}: cible non DXT5")
        before = bytes(raw)
        all_rectangles = []
        for other_page, x, y in tis["entries"]:
            if other_page == page:
                all_rectangles.append((x - 4, y - 4, x + 260, y + 260))
        selected_rectangles = []
        for tile, x, y in by_page[page]:
            if (x % 264, y % 264) != (4, 4):
                raise RuntimeError(f"{tis_resref} tile {tile}: padding x4 non prouvé")
            rect = (x - 4, y - 4, x + 260, y + 260)
            if rect[0] < 0 or rect[1] < 0 or rect[2] > width or rect[3] > height:
                raise RuntimeError(f"{tis_resref} tile {tile}: padding hors page")
            for other in all_rectangles:
                if other == rect:
                    continue
                if max(rect[0], other[0]) < min(rect[2], other[2]) and max(rect[1], other[1]) < min(rect[3], other[3]):
                    raise RuntimeError(f"{tis_resref} tile {tile}: padding chevauchant")
            selected_rectangles.append(rect)
        columns = width // 4
        changed: set[int] = set()
        for left, top, right, bottom in selected_rectangles:
            for py in range(top // 4, bottom // 4):
                for px in range(left // 4, right // 4):
                    block = py * columns + px
                    start = offset + block * 16
                    raw[start:start + 8] = ALPHA128
                    changed.add(block)
        for block in range((width // 4) * (height // 4)):
            start = offset + block * 16
            if raw[start + 8:start + 16] != before[start + 8:start + 16]:
                raise RuntimeError(f"{name}: RGB modifié")
            if block not in changed and raw[start:start + 8] != before[start:start + 8]:
                raise RuntimeError(f"{name}: alpha hors masque modifié")
        output_data = struct.pack("<I", len(raw)) + zlib.compress(raw, 9)
        output_path.write_bytes(output_data)
        if zlib.decompress(output_path.read_bytes()[4:]) != raw:
            raise RuntimeError(f"{name}: relecture différente")
        blocks = len(changed)
        if blocks != len(by_page[page]) * 66 * 66:
            raise RuntimeError(f"{name}: cardinal de blocs inattendu")
        total_blocks += blocks
        reports.append({"name": name, "tiles": len(by_page[page]), "alpha_blocks": blocks,
                        "source_sha256": sha256_bytes(packed),
                        "sha256": sha256_bytes(output_data)})
    return reports, total_blocks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--family-policy", type=Path, default=DEFAULT_FAMILY)
    parser.add_argument("--route1-policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    rows = load_json(args.matrix)
    family = load_json(args.family_policy)
    policy = load_json(args.route1_policy)
    if family["seedvr"]["new_processing_color_correction_method"] != "none" \
            or policy["seedvr_new_processing_color_correction_method"] != "none":
        raise RuntimeError("SeedVR doit rester none pour tout nouveau traitement eau")
    overlay_family = {overlay: item["id"] for item in family["families"] for overlay in item["overlays"]}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["wed"]].append(row)
    planned = []
    for wed, wed_rows in sorted(grouped.items()):
        actionable = []
        blocked = []
        for row in wed_rows:
            count = int(row["base_diagnostics"].get("alpha0_native_divergence_ids", 0))
            if not count:
                continue
            family_id = overlay_family[row["overlay_resref"]]
            action = policy["families"][family_id]["alpha128"]
            target = {"slot": row["overlay_slot"], "overlay": row["overlay_resref"],
                      "family": family_id, "expected_ids": count, "action": action}
            (blocked if action.startswith("blocked") else actionable).append(target)
        if actionable or blocked:
            planned.append({"wed": wed, "actionable": actionable, "blocked": blocked})
    plan = {"schema": "bg2-water-route1-alpha128-plan-v1", "matrix": rel(args.matrix),
            "matrix_sha256": sha256_file(args.matrix), "seedvr_color_correction_method": "none",
            "wed_count": len(planned), "actionable_weds": sum(bool(row["actionable"]) for row in planned),
            "blocked_weds": sum(bool(row["blocked"]) and not row["actionable"] for row in planned),
            "targets": planned}
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
    game = Path(get_path("bg2ee_game_root"))
    override = game / "override"
    bifs, resources = load_key()
    lookup = {(name.upper(), kind): locator for name, kind, locator in resources}
    results = []
    for target in planned:
        wed = target["wed"]
        if not target["actionable"]:
            results.append({"wed": wed, "status": "blocked", "reasons": target["blocked"]})
            continue
        wed_path = override / f"{wed}.WED"
        if wed_path.is_file():
            wed_data = wed_path.read_bytes()
            wed_source = f"override/{wed}.WED"
        else:
            wed_data, archive = resolve_resource(bifs, lookup[(wed, 0x3E9)])
            wed_source = f"stock:{archive}"
        parsed = parse_wed(wed_data)
        tis_resref = parsed["layers"][0]["tis"]
        tis_path = override / f"{tis_resref}.TIS"
        tis_data = tis_path.read_bytes()
        tis = parse_standalone_tis(tis_data)
        source_tis, source_count, source_size, source_archive = resolve_tileset_resource(
            bifs, lookup[(tis_resref, 0x3EB)])
        slot_results = []
        all_targets: set[int] = set()
        for item in target["actionable"]:
            eligible = eligible_primary_ids(parsed, item["slot"])
            native, _ = source_pages(bifs, lookup, tis_resref, source_tis,
                                     source_count, source_size, eligible)
            alpha0 = current_alpha0_ids(override, tis_resref, tis, eligible)
            qualified = native & alpha0
            if len(qualified) != item["expected_ids"]:
                raise RuntimeError(f"{wed} slot {item['slot']}: {len(qualified)} IDs prouvés, "
                                   f"matrice={item['expected_ids']}")
            if all_targets & qualified:
                raise RuntimeError(f"{wed}: ID partagé par plusieurs overlays")
            all_targets |= qualified
            slot_results.append({**item, "qualified_ids": sorted(qualified)})
        candidate = output / "candidates" / wed
        files, blocks = patch_candidate(override, candidate, tis_resref, tis, all_targets)
        file_rows = [{"name": f"{tis_resref}.TIS", "bytes": tis_path.stat().st_size,
                      "sha256": sha256_file(candidate / f"{tis_resref}.TIS"),
                      "source_sha256": sha256_file(tis_path)},
                     *[{**item, "bytes": (candidate / item["name"]).stat().st_size} for item in files]]
        status = "candidate-installable-pending-map-qa"
        if any(item["action"].endswith("family-qa") for item in slot_results):
            status = "candidate-installable-pending-family-qa"
        residual = []
        matrix_row = next(row for row in grouped[wed])
        if int(matrix_row["base_diagnostics"]["interface_heuristic"].get("secondary_alpha_drop", 0)):
            residual.append("secondary-alpha-interface-seam-requires-bounded-donor-repair")
            status = "blocked-after-central-alpha-candidate"
        results.append({"wed": wed, "variant": matrix_row["variant"], "status": status,
                        "candidate": rel(candidate), "wed_source": wed_source,
                        "wed_sha256": sha256_bytes(wed_data), "base_tis": tis_resref,
                        "source_tis_archive": source_archive, "target_ids": len(all_targets),
                        "modified_alpha_blocks": blocks, "rgb_blocks_modified": 0,
                        "other_alpha_blocks_modified": 0, "slots": slot_results,
                        "residual_blockers": residual, "files": file_rows,
                        "candidate_set_sha256": aggregate(file_rows)})
        print(f"{wed}: {len(all_targets)} IDs, {blocks} blocs alpha, RGB exact, {status}", flush=True)
    report = {"schema": "bg2-water-route1-alpha128-result-v1",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "request": "request.json", "seedvr_invoked": False,
              "seedvr_color_correction_method_if_needed": "none",
              "installation": "not-run", "release": "not-requested",
              "summary": {"results": len(results),
                          "candidates": sum("candidate" in row for row in results),
                          "blocked": sum(row["status"].startswith("blocked") for row in results),
                          "target_ids": sum(int(row.get("target_ids", 0)) for row in results),
                          "modified_alpha_blocks": sum(int(row.get("modified_alpha_blocks", 0)) for row in results)},
              "results": results}
    write_json(output / "repair-report.json", report)
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
