"""Static validation for the BG2 HD alpha payload.

This intentionally reads only the source files declared by content.json.  It
does not use the development override and it does not decode image pixels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

PVR_MAGIC = 0x03525650
BLACK_PAGE = 0xFFFFFFFF


def fail(message: str) -> None:
    raise ValueError(message)


def power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def pvrz_info(path: Path) -> dict[str, int]:
    raw = path.read_bytes()
    if len(raw) < 5:
        fail(f"{path}: PVRZ trop court")
    try:
        pvr = zlib.decompress(raw[4:])
    except zlib.error as exc:
        fail(f"{path}: compression PVRZ invalide ({exc})")
    if len(pvr) < 52:
        fail(f"{path}: entete PVR v3 tronque")
    magic, _flags, fmt, _fmt_hi, _colorspace, _channel_type, height, width, depth, surfaces, faces, mips, metadata = struct.unpack_from("<13I", pvr)
    if magic != PVR_MAGIC:
        fail(f"{path}: magic PVR invalide")
    if fmt not in (7, 11):
        fail(f"{path}: format PVR {fmt} non autorise (DXT1/DXT5 requis)")
    if not (power_of_two(width) and power_of_two(height) and width >= 256 and height >= 256):
        fail(f"{path}: dimensions PVR invalides {width}x{height}")
    if (depth, surfaces, faces, mips) != (1, 1, 1, 1):
        fail(f"{path}: PVR doit etre une seule surface 2D sans mipmaps")
    block_bytes = 8 if fmt == 7 else 16
    expected_size = 52 + metadata + ((width + 3) // 4) * ((height + 3) // 4) * block_bytes
    if len(pvr) != expected_size:
        fail(f"{path}: taille PVR incoherente ({len(pvr)} != {expected_size})")
    return {"format": fmt, "width": width, "height": height}


def pvrz_prefix(resref: str) -> str:
    if len(resref) < 2:
        fail(f"resref TIS invalide : {resref}")
    return resref[0] + resref[2:]


def validate_tis(path: Path, declared_pvrz: dict[str, Path]) -> Counter[int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"TIS V1  ":
        fail(f"{path}: signature TIS moderne invalide")
    tile_count, entry_size, header_size, tile_dim = struct.unpack_from("<4I", data, 8)
    if entry_size != 12 or header_size != 24:
        fail(f"{path}: TIS PVRZ attendu (entree=12, entete=24)")
    if tile_dim != 256:
        fail(f"{path}: dimension de tuile {tile_dim}; x4 attend 256")
    if len(data) != header_size + tile_count * entry_size:
        fail(f"{path}: taille TIS incoherente")
    pages: dict[int, dict[str, int]] = {}
    references: Counter[int] = Counter()
    prefix = pvrz_prefix(path.stem.upper())
    for index in range(tile_count):
        page, x, y = struct.unpack_from("<3I", data, header_size + index * entry_size)
        if page == BLACK_PAGE:
            continue
        expected_name = f"{prefix}{page:02d}.PVRZ"
        pvrz = declared_pvrz.get(expected_name)
        if not pvrz:
            fail(f"{path}: page referencee absente du manifeste : {expected_name}")
        if page not in pages:
            pages[page] = pvrz_info(pvrz)
        info = pages[page]
        if x + tile_dim > info["width"] or y + tile_dim > info["height"]:
            fail(f"{path}: tuile {index} hors page {expected_name} ({x},{y})")
        references[page] += 1
    actual_pages = {int(name[len(prefix):-5]) for name in declared_pvrz if name.startswith(prefix) and name.endswith('.PVRZ') and name[len(prefix):-5].isdigit()}
    if actual_pages != set(references):
        fail(f"{path}: pages PVRZ declarees/referencees differentes ({sorted(actual_pages)} != {sorted(references)})")
    return Counter(info["format"] for info in pages.values())


def validate_ui(entries: list[dict], root: Path) -> Counter[int]:
    dimensions = Counter()
    for entry in entries:
        path = root / entry["source"]
        if path.suffix.lower() != ".dxt5":
            fail(f"{path}: extension DXT5 attendue")
        size = path.stat().st_size
        side = math.isqrt(size)
        if side * side != size or side not in (2048, 4096):
            fail(f"{path}: taille DXT5 x4 inattendue ({size} octets)")
        dimensions[side] += 1
    return dimensions


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_area_animations(entries: list[dict], root: Path) -> dict[str, int]:
    by_component: dict[int, list[dict]] = {}
    for entry in entries:
        by_component.setdefault(entry["component_id"], []).append(entry)

    total_frames = 0
    for component_id, group in by_component.items():
        areas = {entry["area"] for entry in group}
        if len(areas) != 1:
            fail(f"Composant animation {component_id}: zone unique attendue")
        area = next(iter(areas))
        payload_groups = {entry["payload_group"] for entry in group}
        labels = {entry["component_label"] for entry in group}
        if len(payload_groups) != 1 or len(labels) != 1:
            fail(f"Composant animation {component_id}: identite de composant incoherente")
        prefix = f"iee-assets/areas/{area}/"
        if any(not entry["destination"].startswith(prefix) for entry in group):
            fail(f"Composant animation {component_id}: destination hors zone {area}")

        manifests = [entry for entry in group if Path(entry["source"]).name == "manifest.json"]
        registries = [entry for entry in group if Path(entry["source"]).name == "AreaAnimations-X4.registry"]
        if len(manifests) != 1 or len(registries) != 1:
            fail(f"Composant animation {component_id}: manifeste ou registre absent/duplique")
        manifest_path = root / manifests[0]["source"]
        pack = json.loads(manifest_path.read_text(encoding="utf-8"))
        registry_version = pack.get("registry_version")
        if (
            pack.get("schema") != "bg2-upscale-area-animation-runtime-pack-v2"
            or pack.get("status") != "completed"
            or pack.get("area_id") != area
            or pack.get("scale") != 4
            or registry_version not in (2, 3)
        ):
            fail(f"Composant animation {component_id}: manifeste de pack invalide")

        registry_path = root / registries[0]["source"]
        registry = registry_path.read_bytes()
        if len(registry) < 24 or registry[:8] != b"IEEAAX4\0":
            fail(f"Composant animation {component_id}: registre binaire invalide")
        version, scale, resource_count, reserved = struct.unpack_from("<4I", registry, 8)
        if (version, scale, resource_count, reserved) != (registry_version, 4, pack["resource_count"], 0):
            fail(f"Composant animation {component_id}: entete de registre incoherent")
        if sha256(registry_path) != pack["registry_sha256"].upper() or len(registry) != pack["registry_bytes"]:
            fail(f"Composant animation {component_id}: hash ou taille du registre incoherent")

        expected: dict[str, dict] = {"manifest.json": manifests[0], "AreaAnimations-X4.registry": registries[0]}
        for resource in pack["resources"]:
            frames = resource["frames"]
            if len(frames) != resource["frame_count"]:
                fail(f"Composant animation {component_id}: nombre de frames incoherent pour {resource['resref']}")
            variant_index = int(resource.get("variant_index", 0))
            variant_suffix = f"-v{variant_index}" if variant_index else ""
            for frame in frames:
                name = frame["asset"]
                expected_name = f"AAX4-{resource['resref']}{variant_suffix}-frame{frame['frame']:03d}.rgba"
                if name != expected_name:
                    fail(f"Composant animation {component_id}: nom de frame invalide {name}")
                expected[name] = frame
                total_frames += 1
        actual = {Path(entry["source"]).name: entry for entry in group}
        if set(actual) != set(expected):
            fail(f"Composant animation {component_id}: inventaire de fichiers different du manifeste")
        if len(pack["resources"]) != pack["resource_count"]:
            fail(f"Composant animation {component_id}: inventaire de ressources incoherent")

        for name, frame in expected.items():
            entry = actual[name]
            path = root / entry["source"]
            actual_size = path.stat().st_size
            actual_sha256 = sha256(path)
            if actual_size != entry["bytes"] or actual_sha256 != entry["sha256"].upper():
                fail(f"Composant animation {component_id}: hash ou taille contenu invalide {name}")
            if name.startswith("AAX4-"):
                width, height = frame["physical_size_x4"]
                if actual_size != width * height * 4:
                    fail(f"Composant animation {component_id}: taille RGBA invalide {name}")
                if actual_sha256 != frame["sha256"].upper() or actual_size != frame["bytes"]:
                    fail(f"Composant animation {component_id}: hash de frame invalide {name}")
    return {"components": len(by_component), "frames": total_frames, "files": len(entries)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--content", required=True, type=Path)
    parser.add_argument(
        "--area-animation-only",
        action="store_true",
        help="validate only a temporary manifest containing area-animation entries",
    )
    args = parser.parse_args()
    root = args.workspace.resolve()
    entries = json.loads(args.content.read_text(encoding="utf-8"))["entries"]
    maps = [entry for entry in entries if entry["kind"] == "map"]
    ui = [entry for entry in entries if entry["kind"] == "ui"]
    animations = [entry for entry in entries if entry["kind"] == "area-animation"]
    if args.area_animation_only:
        if maps or ui or len(animations) != len(entries) or not animations:
            fail("Le manifeste delta doit contenir uniquement des area-animation")
        animation_summary = validate_area_animations(animations, root)
        print(json.dumps({"area_animations": animation_summary}, sort_keys=True))
        return 0
    map_tis = [entry for entry in maps if entry["source"].upper().endswith(".TIS")]
    expected_tis = len({entry["area"] for entry in maps})
    if len(map_tis) != expected_tis:
        fail(
            "Chaque variante de carte doit declarer exactement un TIS "
            f"({len(map_tis)} TIS pour {expected_tis} variantes)"
        )
    if len(ui) != 15:
        fail("Le lot alpha doit contenir exactement 15 entrees UI")
    by_directory: dict[Path, list[dict]] = {}
    for entry in maps:
        by_directory.setdefault((root / entry["source"]).parent, []).append(entry)
    formats: Counter[int] = Counter()
    for directory, group in by_directory.items():
        pvrz = {Path(entry["source"]).name.upper(): root / entry["source"] for entry in group if entry["source"].upper().endswith(".PVRZ")}
        for entry in (entry for entry in group if entry["source"].upper().endswith(".TIS")):
            formats.update(validate_tis(root / entry["source"], pvrz))
    ui_dimensions = validate_ui(ui, root)
    animation_summary = validate_area_animations(animations, root)
    print(json.dumps({"tis": len(map_tis), "pvrz": len(maps) - len(map_tis), "pvr_formats": {str(key): value for key, value in sorted(formats.items())}, "ui": len(ui), "ui_dimensions": {str(key): value for key, value in sorted(ui_dimensions.items())}, "area_animations": animation_summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, struct.error) as exc:
        print(f"BG2 HD asset validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
