"""Derive a split-root whose targeted resources carry the area's own lighting.

Why this exists: the x4 area-animation path binds a pre-baked RGBA texture and, as
`src/iee/area_animation_x4_registry.h` states in its own words, "area-animation composition
leaves [the realized palette] null" — unlike creature composition, which consumes the table
`CVidPalette::Realize` produced for that very draw call. The engine's per-area lighting reaches
the vanilla BAM through that palette, so our replacement texture is drawn unlit.

Indoors that is invisible: the light map does not vary. Outdoors it is not. Measured on
`1400T005` (AR1400 / AR1404), the light factor over the resource footprint is:

    day   AR1400LM  ->  [0.842, 0.842, 0.864]   our texture is 1.19x too bright
    night AR1400LN  ->  [0.441, 0.420, 0.558]   our texture is 2.27 / 2.38 / 1.79x too bright

which matches the in-game verdict exactly: accepted in daylight, rejected at night, and rejected
as *warm* rather than merely bright, because the blue channel is the least over-driven one.

The correction re-applies what the engine would have applied:

    rgb_final = rgb_x4 * lightmap(world) / 255      per channel
    alpha     = unchanged, asserted byte for byte

The light map is sampled in world space, bilinearly, from each frame's own BAM anchor
(`position - centre_x1`), so frames of differing size or centre stay registered. The IE light
map covers 16 x 12 world pixels per texel; the ratio is derived from the WED overlay rather than
assumed, and a mismatch is fatal.

Scope and limit: one baked texture carries one lighting state. A zone whose light map never
changes (AR1404 uses AR1404LM == AR1400LN, permanent night) is fully corrected by this. A zone
that cycles day and night (AR1400) can only be correct for the state it was baked for; the other
state is wrong by the ratio between the two light maps. That is a property of the defect, not of
this script, and the real fix belongs to the renderer.

This never touches the game, the DLL, INI, override, the input split-root or any catalogue: it
writes a new split-root beside the old one.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bg2lib  # noqa: E402
import run_animation_upscale_30fps_v2 as v2  # noqa: E402
import split_animation_pack_by_area as splitter  # noqa: E402

BMP_TYPE = 0x0001
WED_TYPE = 0x03E9
SCALE = 4
TILE_PX = 64


def load_bmp_resource(resref: str) -> tuple[np.ndarray, str]:
    """Return one BMP game resource as float RGB plus its SHA-256."""
    bif_entries, resources = bg2lib.load_key()
    matches = [row for row in resources
               if row[0].upper() == resref.upper() and row[1] == BMP_TYPE]
    v2.require(len(matches) >= 1, f"light map absente du KEY : {resref}")
    payload = bg2lib.resolve_resource(bif_entries, matches[0][2])
    data = payload[0] if isinstance(payload, tuple) else payload
    image = np.asarray(Image.open(io.BytesIO(data)).convert("RGB")).astype(np.float32)
    return image, v2.sha256_bytes(data) if hasattr(v2, "sha256_bytes") else _sha(data)


def _sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def area_tile_extent(area_id: str) -> tuple[int, int]:
    """Base overlay size in tiles, read from the area's WED."""
    import struct
    bif_entries, resources = bg2lib.load_key()
    matches = [row for row in resources
               if row[0].upper() == area_id.upper() and row[1] == WED_TYPE]
    v2.require(bool(matches), f"WED absent du KEY : {area_id}")
    payload = bg2lib.resolve_resource(bif_entries, matches[0][2])
    data = payload[0] if isinstance(payload, tuple) else payload
    overlay_offset = struct.unpack_from("<I", data, 16)[0]
    width, height = struct.unpack_from("<HH", data, overlay_offset)
    return int(width), int(height)


def lightmap_ratio(light: np.ndarray, area_id: str) -> tuple[float, float]:
    """World pixels covered by one light-map texel, derived from the WED extent."""
    tiles_x, tiles_y = area_tile_extent(area_id)
    height, width = light.shape[:2]
    v2.require(width > 0 and height > 0, f"light map vide pour {area_id}")
    ratio_x = tiles_x * TILE_PX / width
    ratio_y = tiles_y * TILE_PX / height
    # The engine uses integral ratios; anything else means we mis-identified the resource.
    for value, axis in ((ratio_x, "x"), (ratio_y, "y")):
        v2.require(abs(value - round(value)) < 0.05,
                   f"{area_id}: ratio light map {axis} non entier ({value:.3f})")
    return float(round(ratio_x)), float(round(ratio_y))


def sample_lightmap(light: np.ndarray, world_x: np.ndarray, world_y: np.ndarray,
                    ratio: tuple[float, float]) -> np.ndarray:
    """Bilinear sample of the light map at world coordinates, texel centres at (i+0.5)*ratio."""
    height, width = light.shape[:2]
    fx = world_x / ratio[0] - 0.5
    fy = world_y / ratio[1] - 0.5
    x0 = np.clip(np.floor(fx).astype(np.int64), 0, width - 1)
    y0 = np.clip(np.floor(fy).astype(np.int64), 0, height - 1)
    x1 = np.clip(x0 + 1, 0, width - 1)
    y1 = np.clip(y0 + 1, 0, height - 1)
    tx = np.clip(fx - x0, 0.0, 1.0)[..., None]
    ty = np.clip(fy - y0, 0.0, 1.0)[..., None]
    top = light[y0, x0] * (1.0 - tx) + light[y0, x1] * tx
    bottom = light[y1, x0] * (1.0 - tx) + light[y1, x1] * tx
    return top * (1.0 - ty) + bottom * ty


def relight_asset(path: Path, width: int, height: int, origin: tuple[int, int],
                  light: np.ndarray, ratio: tuple[float, float]) -> tuple[int, list[float]]:
    """Multiply one raw RGBA asset by the light map. Returns changed texels and mean factor."""
    raw = path.read_bytes()
    expected = width * height * 4
    v2.require(len(raw) == expected,
               f"{path.name}: {len(raw)} octets pour {width}x{height}x4 attendus")
    buffer = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4)
    rows, columns = np.mgrid[0:height, 0:width]
    factor = sample_lightmap(light,
                             origin[0] + columns / SCALE,
                             origin[1] + rows / SCALE,
                             ratio) / 255.0
    out = buffer.copy()
    out[..., :3] = np.clip(np.rint(buffer[..., :3].astype(np.float32) * factor), 0, 255)
    v2.require(np.array_equal(out[..., 3], buffer[..., 3]), f"{path.name}: alpha modifié")
    changed = int((out[..., :3] != buffer[..., :3]).any(axis=2).sum())
    path.write_bytes(out.tobytes())
    return changed, [float(value) for value in factor.reshape(-1, 3).mean(axis=0)]


def occurrence_positions(occurrences: Path) -> dict[tuple[str, str], list[tuple[int, int]]]:
    """World positions declared by the canonical occurrence index, per (area, resref)."""
    import csv
    positions: dict[tuple[str, str], list[tuple[int, int]]] = {}
    with occurrences.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if str(row.get("resource_kind", "")).upper() != "BAM":
                continue
            key = (str(row["area_id"]).upper(), v2.normalise_resref(str(row["resource_resref"])))
            positions.setdefault(key, []).append((int(row["x"]), int(row["y"])))
    return positions


def relight_area(area_dir: Path, area_id: str, targets: set[str],
                 light: np.ndarray, light_resref: str, light_sha: str,
                 positions: dict[tuple[str, str], list[tuple[int, int]]]) -> dict[str, Any]:
    """Rewrite one area pack's targeted assets and re-hash its manifest."""
    manifest = v2.load_json(area_dir / "manifest.json")
    ratio = lightmap_ratio(light, area_id)
    frames_changed = 0
    texels_changed = 0
    touched: list[str] = []
    factors: list[list[float]] = []

    for resource in manifest.get("resources") or []:
        resref = v2.normalise_resref(str(resource["resref"]))
        if resref not in targets:
            continue
        touched.append(resref)
        # Registry v3 carries `position` only for occurrence-routed variants; every other
        # resource takes its world anchor from the canonical occurrence index.
        position = resource.get("position")
        if position is None:
            declared = positions.get((area_id.upper(), resref)) or []
            v2.require(bool(declared),
                       f"{area_id}/{resref}: aucune occurrence dans l'index, "
                       "light map non projetable")
            # Several occurrences sit under different light: one baked texture cannot serve them.
            v2.require(len(set(declared)) == 1,
                       f"{area_id}/{resref}: {len(set(declared))} occurrences à des positions "
                       "distinctes ; un ré-éclairage unique serait faux pour au moins l'une "
                       "d'elles, employer le routage par occurrence")
            position = list(declared[0])
        assets_by_name = {str(asset["name"]): asset for asset in resource["assets"]}
        for frame in sorted(resource["frames"], key=lambda item: int(item["frame"])):
            width, height = (int(value) for value in frame["physical_size_x4"])
            centre_x, centre_y = (int(value) for value in frame["centre_x1"])
            origin = (int(position[0]) - centre_x, int(position[1]) - centre_y)
            asset_path = area_dir / str(frame["asset"])
            changed, factor = relight_asset(asset_path, width, height, origin, light, ratio)
            if changed:
                frames_changed += 1
                texels_changed += changed
            factors.append(factor)
            digest = v2.sha256_file(asset_path)
            size = asset_path.stat().st_size
            # frames[] and assets[] carry the same hash for a frame; both are validated.
            frame["sha256"] = digest
            frame["bytes"] = size
            asset = assets_by_name[str(frame["asset"])]
            asset["sha256"] = digest
            asset["bytes"] = size

    if touched:
        mean = np.asarray(factors, dtype=np.float64).mean(axis=0)
        manifest["area_lightmap_relight"] = {
            "lightmap": light_resref,
            "lightmap_sha256": light_sha,
            "lightmap_ratio_world_px": [ratio[0], ratio[1]],
            "rule": "rgb = rgb * lightmap(world)/255 ; alpha unchanged",
            "reason": "the x4 path binds a baked texture and never receives the realized palette",
            "resrefs": sorted(touched),
            "frames_changed": frames_changed,
            "texels_changed": texels_changed,
            "mean_factor_rgb": [round(float(value), 4) for value in mean],
            "applied_utc": v2.utc_now(),
        }
    return {"manifest": manifest, "resrefs": sorted(touched),
            "frames_changed": frames_changed, "texels_changed": texels_changed}


def build(split_root: Path, output: Path, resrefs: set[str],
          area_lightmaps: dict[str, str], occurrences: Path, resume: bool) -> dict[str, Any]:
    import shutil

    split_root = split_root.resolve()
    output = output.resolve()
    index = v2.load_json(split_root / "manifest.json")
    v2.require(index.get("schema") == splitter.INDEX_SCHEMA and index.get("status") == "completed",
               f"index de découpage incompatible : {split_root}")

    # The source must be intact before anything is copied: a defect inherited silently here
    # would be indistinguishable from one this correction introduced.
    for entry in index.get("areas") or []:
        v2.validate_v2_pack(split_root / str(entry["directory"]))

    available = {v2.normalise_resref(str(resref))
                 for entry in index.get("areas") or [] for resref in entry.get("resrefs") or []}
    missing = sorted(resrefs - available)
    v2.require(not missing, f"resref absent du split-root source : {', '.join(missing)}")

    concerned = sorted({str(entry["area_id"]) for entry in index.get("areas") or []
                        if resrefs & {v2.normalise_resref(str(value))
                                      for value in entry.get("resrefs") or []}})
    unmapped = [area for area in concerned if area.upper() not in area_lightmaps]
    v2.require(not unmapped,
               "light map non déclarée pour : " + ", ".join(unmapped)
               + " — une zone jour/nuit doit être choisie explicitement")

    if output.exists():
        v2.require(resume, f"sortie déjà présente sans --resume : {output}")
        existing = v2.load_json(output / "manifest.json")
        for entry in existing.get("areas") or []:
            v2.validate_v2_pack(output / str(entry["directory"]))
        return existing

    # Build into a .partial sibling and rename only once the whole lot validates: a crash
    # mid-run would otherwise leave a directory that looks complete but carries the source
    # index and un-relit assets.
    staging = output.with_name(output.name + ".partial")
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(split_root, staging, ignore=shutil.ignore_patterns("install-backups"))

    positions = occurrence_positions(occurrences.resolve())
    cache: dict[str, tuple[np.ndarray, str]] = {}
    entries = []
    total_frames = 0
    total_texels = 0
    for entry in sorted(index.get("areas") or [], key=lambda item: str(item["area_id"])):
        area_id = str(entry["area_id"])
        area_dir = staging / str(entry["directory"])
        light_resref = area_lightmaps.get(area_id.upper())
        if light_resref is None:
            # Untouched area: leave the copied manifest byte for byte, so the index hash
            # inherited from the source stays true.
            v2.validate_v2_pack(area_dir)
            entries.append(dict(entry))
            continue
        if light_resref not in cache:
            cache[light_resref] = load_bmp_resource(light_resref)
        light, light_sha = cache[light_resref]
        result = relight_area(area_dir, area_id, resrefs, light, light_resref, light_sha,
                              positions)
        v2.write_json(area_dir / "manifest.json", result["manifest"])
        v2.validate_v2_pack(area_dir)
        total_frames += result["frames_changed"]
        total_texels += result["texels_changed"]
        entry = dict(entry)
        entry["manifest_sha256"] = v2.sha256_file(area_dir / "manifest.json")
        entry["relit_resrefs"] = result["resrefs"]
        entries.append(entry)

    new_index = dict(index)
    new_index["created_utc"] = v2.utc_now()
    new_index["areas"] = entries
    new_index["area_lightmap_relight"] = {
        "rule": "rgb = rgb * lightmap(world)/255 ; alpha unchanged",
        "requested_resrefs": sorted(resrefs),
        "area_lightmaps": {key: value for key, value in sorted(area_lightmaps.items())},
        "frames_changed": total_frames,
        "texels_changed": total_texels,
        "source_split_root": split_root.as_posix(),
        "occurrences_index": occurrences.resolve().as_posix(),
        "occurrences_sha256": v2.sha256_file(occurrences.resolve()),
    }
    v2.write_json(staging / "manifest.json", new_index)
    staging.rename(output)
    return new_index


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split-root", type=Path, required=True,
                        help="lot par zone source, jamais modifié")
    parser.add_argument("--output", type=Path, required=True,
                        help="nouveau lot par zone à écrire")
    parser.add_argument("--resref", action="append", required=True, dest="resrefs",
                        help="resref à ré-éclairer ; répétable")
    parser.add_argument("--area-lightmap", action="append", required=True,
                        dest="area_lightmaps", metavar="ZONE=LIGHTMAP",
                        help="light map à appliquer pour une zone, par exemple AR1400=AR1400LN ; "
                             "répétable, obligatoire pour chaque zone portant un resref ciblé")
    parser.add_argument("--occurrences", type=Path, default=splitter.DEFAULT_OCCURRENCES,
                        help="index canonique des occurrences, source des ancres monde")
    parser.add_argument("--resume", action="store_true",
                        help="revalide une sortie existante sans la réécrire")
    args = parser.parse_args(argv)

    mapping: dict[str, str] = {}
    for item in args.area_lightmaps:
        v2.require("=" in item, f"--area-lightmap attend ZONE=LIGHTMAP, reçu : {item}")
        area, _, light = item.partition("=")
        mapping[area.strip().upper()] = light.strip().upper()

    resrefs = {v2.normalise_resref(value) for value in args.resrefs}
    index = build(args.split_root, args.output, resrefs, mapping, args.occurrences, args.resume)
    import json
    print(json.dumps(index.get("area_lightmap_relight", {}), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
