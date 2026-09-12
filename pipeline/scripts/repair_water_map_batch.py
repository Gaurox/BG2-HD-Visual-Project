"""Audit/repair bounded WTLAKE interfaces and WED timelines; plan-only by default.

Reuses the AR0900 donor recipe. No inference, tests, installation or release.
Every input must match the prior installed registry; output must be new.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import io
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zlib

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion

from area_decode import decode_tis_tiles, _pvrz_page_cache
from bg2lib import load_key, resolve_resource, resolve_tileset_resource
from build_water_route1_batch import (parse_standalone_tis, parse_wed, parse_pvr,
                                     eligible_primary_ids, source_pages, patch_candidate)
from build_wtlake_timeline_batch import ROOT, get_path, sha256_file, relative, tis_metadata, patch_wed
from mos_decode import decode_pvrz_page
from water_wed import validate_polygons

Image.MAX_IMAGE_PIXELS = None


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def write_json(path, data):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def masks_for(wed, stock_tile):
    parsed = parse_wed(wed)
    cells = {(c["x"], c["y"]): c for c in parsed["cells"]}
    primaries = Counter(t for c in cells.values() for t in c["primary"])
    secondaries = Counter(c["secondary"] for c in cells.values() if c["secondary"] != 65535)
    require(max(primaries.values()) == 1 and max(secondaries.values(), default=1) == 1
            and not (primaries.keys() & secondaries.keys()), "shared tile usages unsupported")
    width, height = parsed["layers"][0]["width"], parsed["layers"][0]["height"]
    water = np.zeros((height * 64, width * 64), bool)
    full = {}
    for (x, y), c in cells.items():
        if not c["flags"] & 2:
            continue
        require(c["count"] == 1, "animated base tile unsupported")
        primary = np.asarray(stock_tile(c["primary"][0]))[:, :, 3]
        if c["secondary"] == 65535:
            require(np.all(primary == 255), "full water must be stock opaque")
            full[x, y] = c["primary"][0]
            valid = np.ones((64, 64), bool)
        else:
            secondary = np.asarray(stock_tile(c["secondary"]))[:, :, 3]
            valid = (primary == 0) & (secondary == 255)
        water[y*64:(y+1)*64, x*64:(x+1)*64] = valid
    safe = binary_erosion(water, structure=np.ones((3, 3), bool), border_value=0)
    rgb, alpha, coords, seams = {}, {}, {}, []
    opposite = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
    def add(store, tile, x, y, side, valid, feather):
        m = store.setdefault(tile, np.zeros((256, 256), np.float32))
        along = np.repeat(valid, 4)
        for d, weight in enumerate([1, 1, 1, 1, .75, .5, .25, 0] if feather else [1]*8):
            v = along * weight
            if side == "left": m[:, d] = np.maximum(m[:, d], v)
            elif side == "right": m[:, 255-d] = np.maximum(m[:, 255-d], v)
            elif side == "top": m[d] = np.maximum(m[d], v)
            else: m[255-d] = np.maximum(m[255-d], v)
        coords[tile] = (x, y)
    for (x, y), p in full.items():
        own = safe[y*64:(y+1)*64, x*64:(x+1)*64]
        for side, dx, dy in [("left", -1, 0), ("right", 1, 0), ("top", 0, -1), ("bottom", 0, 1)]:
            nx, ny = x+dx, y+dy
            n = cells.get((nx, ny))
            if not n or not n["flags"] & 2 or n["secondary"] == 65535:
                continue
            other = safe[ny*64:(ny+1)*64, nx*64:(nx+1)*64]
            if side == "left": valid = own[:, :2].all(1) & other[:, -2:].all(1)
            elif side == "right": valid = own[:, -2:].all(1) & other[:, :2].all(1)
            elif side == "top": valid = own[:2].all(0) & other[-2:].all(0)
            else: valid = own[-2:].all(0) & other[:2].all(0)
            if not valid.any():
                continue
            add(rgb, p, x, y, side, valid, True)
            add(alpha, n["secondary"], nx, ny, opposite[side], valid, False)
            seams.append({"primary": p, "secondary": n["secondary"], "side": side,
                          "cell": [x, y], "neighbor": [nx, ny],
                          "positions_x1": np.flatnonzero(valid).tolist()})
    for store in (rgb, alpha):
        for tile, m in store.items():
            x, y = coords[tile]
            selected = (m > 0).reshape(64, 4, 64, 4).any((1, 3))
            require(not (selected & ~safe[y*64:(y+1)*64, x*64:(x+1)*64]).any(), "repair touches true shoreline")
    return rgb, alpha, coords, seams, (width, height)


def block_mask(mask):
    return np.pad(mask, 4, mode="edge").reshape(66, 4, 66, 4).any((1, 3))


def inspect_or_patch(area, wed, base, donor_path, bifs, lookup, pvr, output=None):
    stock_tile, _ = decode_tis_tiles(bifs, pvr, area, lookup[area, 0x3eb])
    rgb, alpha, coords, seams, grid = masks_for(wed, stock_tile)
    tis = parse_standalone_tis((base / f"{area}.TIS").read_bytes())
    entries = tis["entries"]
    real_entries = [e for e in entries if e[0] != 0xffffffff]
    require(len(set(real_entries)) == len(real_entries), "aliased atlas slots unsupported")
    require(all((x % 264, y % 264) == (4, 4) for _, x, y in real_entries),
            "cannot prove non-overlapping padded atlas slots")
    require(not (rgb.keys() & alpha.keys()), "overlapping primary/secondary masks")
    by_page = defaultdict(list)
    for tile in rgb.keys() | alpha.keys():
        page, x, y = entries[tile]
        require(page != 0xffffffff and (x % 264, y % 264) == (4, 4), "unproven atlas padding")
        by_page[page].append(tile)
    report = {"wed": area, "grid": grid, "interfaces": len(seams),
              "rgb_tiles": len(rgb), "secondary_alpha_tiles": len(alpha),
              "donor": relative(donor_path), "donor_sha256": sha256_file(donor_path),
              "primary_alpha": 128, "band_x4": 8, "padding_x4": 4,
              "true_bank_guard_x1": 1, "seams": seams, "tiles": [], "pages": []}
    if output:
        shutil.copytree(base, output)
    with Image.open(donor_path) as donor:
        require(donor.size == (grid[0]*256, grid[1]*256), "donor dimensions diverge")
        donor.load()
        for page, tiles in sorted(by_page.items()):
            name = f"{area[0]+area[2:]}{page:02d}.PVRZ"
            packed = (base / name).read_bytes()
            raw, fmt, width, height, offset = parse_pvr(packed)
            require(fmt == 11, "DXT5 required")
            original = np.frombuffer(bytes(raw), np.uint8, offset=offset).reshape(height//4, width//4, 16)
            blocks = np.frombuffer(raw, np.uint8, offset=offset).reshape(height//4, width//4, 16)
            allowed_rgb = np.zeros((height//4, width//4), bool)
            allowed_alpha = np.zeros_like(allowed_rgb)
            decoded = decode_pvrz_page(packed)
            for tile in sorted(tiles):
                _, x, y = entries[tile]
                require(x+260 <= width and y+260 <= height, "tile padding out of bounds")
                core = np.array(decoded.crop((x, y, x+256, y+256)))
                bx, by = (x-4)//4, (y-4)//4
                view = blocks[by:by+66, bx:bx+66]
                cx, cy = coords[tile]
                if tile in rgb:
                    require(np.all(core[:, :, 3] == 128), "primary alpha128 prerequisite missing")
                    replacement = np.array(donor.crop((cx*256, cy*256, (cx+1)*256, (cy+1)*256)).convert("RGB"))
                    weight = rgb[tile][:, :, None]
                    selected_pixels = weight[:, :, 0] == 1
                    report["tiles"].append({"tile": tile, "kind": "primary",
                        "edge_rgb_before": float(core[:, :, :3][selected_pixels].mean()),
                        "edge_rgb_donor": float(replacement[selected_pixels].mean())})
                    if output:
                        core[:, :, :3] = np.rint(core[:, :, :3]*(1-weight) + replacement*weight).clip(0, 255).astype(np.uint8)
                        stream = io.BytesIO()
                        Image.fromarray(np.pad(core, ((4, 4), (4, 4), (0, 0)), mode="edge")).save(stream, format="DDS", pixel_format="DXT5")
                        encoded = stream.getvalue()
                        require(encoded[84:88] == b"DXT5" and len(encoded) == 128+66*66*16, "unexpected DDS encoder layout")
                        coded = np.frombuffer(encoded, np.uint8, offset=128).reshape(66, 66, 16)
                        mask = block_mask(weight[:, :, 0] > 0)
                        view[mask, 8:] = coded[mask, 8:]
                        allowed_rgb[by:by+66, bx:bx+66] |= mask
                else:
                    selected_pixels = alpha[tile] > 0
                    report["tiles"].append({"tile": tile, "kind": "secondary",
                        "edge_alpha_before": float(core[:, :, 3][selected_pixels].mean()),
                        "pixels_below255": int((core[:, :, 3][selected_pixels] < 255).sum())})
                    if output:
                        mask = block_mask(selected_pixels)
                        view[mask, :8] = np.array([255, 255, 0, 0, 0, 0, 0, 0], np.uint8)
                        allowed_alpha[by:by+66, bx:bx+66] |= mask
            if output:
                require(np.array_equal(blocks[~allowed_rgb, 8:], original[~allowed_rgb, 8:]), "RGB outside repair mask changed")
                require(np.array_equal(blocks[~allowed_alpha, :8], original[~allowed_alpha, :8]), "alpha outside repair mask changed")
                rgb_count = int(np.any(blocks[:, :, 8:] != original[:, :, 8:], axis=2).sum())
                alpha_count = int(np.any(blocks[:, :, :8] != original[:, :, :8], axis=2).sum())
                if rgb_count or alpha_count:
                    payload = struct.pack("<I", len(raw)) + zlib.compress(raw, 9)
                    (output / name).write_bytes(payload)
                    require(zlib.decompress((output/name).read_bytes()[4:]) == bytes(raw), "PVRZ serialization mismatch")
                report["pages"].append({"name": name, "rgb_blocks_changed": rgb_count,
                                        "alpha_blocks_changed": alpha_count,
                                        "source_sha256": sha256_file(base/name),
                                        "sha256": sha256_file(output/name)})
    _pvrz_page_cache.clear()
    return report


def summary(report):
    primary = [r for r in report["tiles"] if r["kind"] == "primary"]
    secondary = [r for r in report["tiles"] if r["kind"] == "secondary"]
    return {k: report[k] for k in ("wed", "interfaces", "rgb_tiles", "secondary_alpha_tiles")} | {
        "darkest_primary_witnesses": sorted(primary, key=lambda r: r["edge_rgb_before"]-r["edge_rgb_donor"])[:6],
        "secondary_alpha_pixels_below255": sum(r["pixels_below255"] for r in secondary),
        "rgb_blocks_changed": sum(r["rgb_blocks_changed"] for r in report["pages"]),
        "alpha_blocks_changed": sum(r["alpha_blocks_changed"] for r in report["pages"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    output = ROOT / request["output"]
    require(ROOT in output.resolve().parents and not output.exists(), "output must be new and inside workspace")
    registry_path = ROOT / request["registry"]
    require(sha256_file(registry_path) == request["registry_sha256"], "parent registry diverged")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    game = get_path("bg2ee_game_root")
    live = game / "override"
    bifs, resources = load_key()
    lookup = {(n.upper(), k): l for n, k, l in resources}
    pvr = {n.upper(): (n, k, l) for n, k, l in resources if k == 0x404}
    # Snapshot every old registry identity, including the unaffected AR0900 witness.
    snapshots = {}
    for entry in registry["entries"]:
        names = [(entry["wed"]["resref"]+".WED", entry["wed"]["sha256"]),
                 (entry["base_tis"]["resref"]+".TIS", entry["base_tis"]["sha256"]),
                 (entry["overlay"]["tis_resref"]+".TIS", entry["overlay"]["tis_sha256"])]
        names += [(p["resref"]+".PVRZ", p["sha256"]) for p in entry["base_tis"]["pages"]+entry["overlay"]["pages"]]
        for name, sha in names:
            if name not in snapshots:
                require(sha256_file(live/name) == sha, f"installed identity diverged: {name}")
                snapshots[name] = sha
    if args.run:
        output.mkdir(parents=True)
        write_json(output/"request.json", request | {"producer_sha256": sha256_file(Path(__file__)), "input_request_sha256": sha256_file(args.request)})
        write_json(output/"live-before.json", snapshots)
    reports, install = [], {}
    for target in request["targets"]:
        area = target["wed"]
        entry = next(e for e in registry["entries"] if e["wed"]["resref"] == area)
        source = ROOT / target["base"]
        base, files = tis_metadata(area, source)
        require(base == entry["base_tis"], f"source build differs from installed registry: {area}")
        donor = ROOT / target["donor"]
        require(sha256_file(donor) == target["donor_sha256"], f"donor diverged: {area}")
        wed, archive = resolve_resource(bifs, lookup[area, 0x3e9])
        corrected_wed = patch_wed(wed, area)
        alpha_report = None
        if target.get("restore_native_alpha"):
            are_name = area.removesuffix("N")
            are_path = live / f"{are_name}.ARE"
            are = are_path.read_bytes() if are_path.is_file() else resolve_resource(bifs, lookup[are_name, 0x3f2])[0]
            require(len(are) > 0x52 and are[:8] == b"AREAV1.0" and are[0x52] in (0, 128), "native alpha128 contract not proven")
            ids = eligible_primary_ids(parse_wed(wed), 1)
            stock_tis, count, size, _ = resolve_tileset_resource(bifs, lookup[area, 0x3eb])
            qualified, _ = source_pages(bifs, lookup, area, stock_tis, count, size, ids)
            require(ids and qualified == ids, "full-water primary source must be DXT1")
            alpha_report = {"eligible_primary_ids": sorted(ids), "native_alpha": 128,
                            "are_sha256": hashlib.sha256(are).hexdigest().upper(),
                            "recipe": "DXT5 alpha128 core+padding; RGB unchanged"}
            print(json.dumps({"wed": area, "native_alpha128_primary_tiles": len(ids)}), flush=True)
            if not args.run:
                continue
            alpha_source = output/"alpha128"/area
            alpha_report["pages"], alpha_report["selected_blocks"] = patch_candidate(
                source, alpha_source, area, parse_standalone_tis((source/f"{area}.TIS").read_bytes()), ids)
            write_json(output/f"{area}-alpha128-report.json", alpha_report)
            source = alpha_source
        report = inspect_or_patch(area, wed, source, donor, bifs, lookup, pvr,
                                 output/"maps"/area if args.run else None)
        report["stock_wed_archive"] = archive
        report["corrected_wed_geometry"] = validate_polygons(corrected_wed)
        report["strength_before"] = entry["approved_strength"]
        report["strength_candidate"] = target["strength"]
        print(json.dumps(summary(report), ensure_ascii=False), flush=True)
        if args.run:
            newbase = output/"maps"/area
            write_json(output/f"{area}-repair-report.json", report)
            (newbase/f"{area}.WED").write_bytes(corrected_wed)
            entry["wed"]["sha256"] = sha256_file(newbase/f"{area}.WED")
            entry["base_tis"] = tis_metadata(area, newbase)[0]
            entry["approved_strength"] = target["strength"]
            entry["qa"] = {"status": "pending-ingame", "reference": relative(output/f"{area}-repair-report.json")}
            entry["state"] = "candidate-installable-pending-qa"
            for f in newbase.iterdir():
                sha = sha256_file(f)
                if sha != snapshots[f.name]:
                    install[f.name] = {"source": relative(f), "sha256": sha,
                                       "bytes": f.stat().st_size, "before_sha256": snapshots[f.name]}
        reports.append(summary(report))
    if args.run:
        registry["experiment"] = {"scope": [t["wed"] for t in request["targets"]],
            "previous_registry": request["registry"], "previous_registry_sha256": request["registry_sha256"],
            "untargeted_entries": "byte-equivalent JSON objects", "qa": "pending-ingame"}
        write_json(output/"registry-v3.json", registry)
        write_json(output/"install-plan.json", install)
        assets = output/"override-candidate"
        assets.mkdir()
        for name, record in install.items():
            shutil.copy2(ROOT/record["source"], assets/name)
        write_json(assets/"manifest.json", {"schema": "bg2-upscale-area-animation-override-assets-v1",
            "status": "completed", "area": "+".join(t["wed"] for t in request["targets"]),
            "files": {n: {"bytes": v["bytes"], "sha256": v["sha256"]} for n, v in install.items()}})
        write_json(output/"run.json", {"schema": "bg2-water-map-repair-run-v1", "asset_ids": ["maps:"+t["wed"].removesuffix("N")+(":night" if t["wed"].endswith("N") else ":day") for t in request["targets"]],
            "created_at_utc": datetime.now(timezone.utc).isoformat(), "reports": reports,
            "installation": "not-run", "tests": "not-run-user-choice", "qa": "pending-ingame", "release": "not-requested"})


if __name__ == "__main__":
    main()
