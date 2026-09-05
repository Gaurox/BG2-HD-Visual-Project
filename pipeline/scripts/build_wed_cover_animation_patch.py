"""Build a narrow, reversible WED override that adds ``Cover animations``.

The source WED is read from the game's KEY/BIF catalogue.  Every requested
polygon must still carry the explicitly supplied original flags; this prevents
silently applying an old diagnosis to another game build or an already-patched
resource.  Only the polygon flag bytes may differ in the generated override.

Example::

    python build_wed_cover_animation_patch.py AR0516 output \
        --polygon 65:0x05
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from bg2lib import load_key, resolve_resource


WED_TYPE = 0x03E9
WED_SIGNATURE = b"WED V1.3"
POLYGON_SIZE = 0x12
POLYGON_FLAG_OFFSET = 0x08
COVER_ANIMATIONS = 0x08
MANIFEST_SCHEMA = "bg2-upscale-area-animation-override-assets-v1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_polygon(value: str) -> tuple[int, int]:
    try:
        index_text, flags_text = value.split(":", 1)
        index = int(index_text, 10)
        expected_flags = int(flags_text, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--polygon doit utiliser la forme INDEX:FLAGS, par exemple 65:0x05"
        ) from exc
    if index < 0:
        raise argparse.ArgumentTypeError("l'index de polygone doit être positif")
    if not 0 <= expected_flags <= 0xFF:
        raise argparse.ArgumentTypeError("les flags doivent tenir dans un octet")
    return index, expected_flags


def polygon_table(data: bytes) -> tuple[int, int]:
    if len(data) < 0x2C or data[:8] != WED_SIGNATURE:
        raise ValueError("signature WED V1.3 invalide")
    secondary_offset = struct.unpack_from("<I", data, 0x14)[0]
    if secondary_offset > len(data) or len(data) - secondary_offset < 0x14:
        raise ValueError("en-tête secondaire WED hors fichier")
    polygon_count, polygon_offset = struct.unpack_from("<II", data, secondary_offset)
    table_size = polygon_count * POLYGON_SIZE
    if polygon_offset > len(data) or table_size > len(data) - polygon_offset:
        raise ValueError("table des polygones WED hors fichier")
    return polygon_count, polygon_offset


def add_cover_animations(
    source: bytes, requested: list[tuple[int, int]]
) -> tuple[bytes, list[dict[str, int | str]]]:
    if not requested:
        raise ValueError("au moins un polygone doit être demandé")
    indexes = [index for index, _expected in requested]
    if len(indexes) != len(set(indexes)):
        raise ValueError("un index de polygone est demandé plusieurs fois")

    polygon_count, polygon_offset = polygon_table(source)
    output = bytearray(source)
    changes: list[dict[str, int | str]] = []
    changed_offsets: set[int] = set()
    for index, expected_flags in requested:
        if index >= polygon_count:
            raise ValueError(
                f"polygone {index} hors table (nombre de polygones : {polygon_count})"
            )
        flag_offset = polygon_offset + index * POLYGON_SIZE + POLYGON_FLAG_OFFSET
        actual_flags = source[flag_offset]
        if actual_flags != expected_flags:
            raise ValueError(
                f"polygone {index}: flags 0x{actual_flags:02X}, "
                f"0x{expected_flags:02X} attendus"
            )
        if actual_flags & COVER_ANIMATIONS:
            raise ValueError(f"polygone {index}: Cover animations est déjà actif")
        new_flags = actual_flags | COVER_ANIMATIONS
        output[flag_offset] = new_flags
        changed_offsets.add(flag_offset)
        changes.append({
            "polygon_index": index,
            "flag_file_offset": f"0x{flag_offset:X}",
            "original_flags": actual_flags,
            "original_flags_hex": f"0x{actual_flags:02X}",
            "patched_flags": new_flags,
            "patched_flags_hex": f"0x{new_flags:02X}",
            "added_flag": COVER_ANIMATIONS,
            "added_flag_hex": f"0x{COVER_ANIMATIONS:02X}",
        })

    actual_differences = {
        offset for offset, (before, after) in enumerate(zip(source, output)) if before != after
    }
    if actual_differences != changed_offsets or len(output) != len(source):
        raise RuntimeError("la génération WED a modifié des octets hors sélection")
    return bytes(output), changes


def load_wed(area: str) -> tuple[bytes, str]:
    bif_entries, resources = load_key()
    matches = [
        (name, locator)
        for name, resource_type, locator in resources
        if name.upper() == area and resource_type == WED_TYPE
    ]
    if len(matches) != 1:
        raise ValueError(f"{area}: ressource WED KEY/BIF unique introuvable")
    resolved = resolve_resource(bif_entries, matches[0][1])
    if resolved is None:
        raise ValueError(f"{area}: ressource WED impossible à résoudre")
    return resolved


def build(
    area: str, output_dir: Path, requested: list[tuple[int, int]]
) -> dict[str, object]:
    area = area.upper()
    if len(area) > 8 or not area.isascii() or not area.isalnum():
        raise ValueError(f"resref de zone invalide : {area!r}")
    source, source_bif = load_wed(area)
    patched, changes = add_cover_animations(source, requested)

    output_dir = output_dir.resolve()
    output_path = output_dir / f"{area}.WED"
    manifest_path = output_dir / "manifest.json"
    if output_path.exists() and output_path.read_bytes() != patched:
        raise RuntimeError(f"destination WED existante différente : {output_path}")

    manifest: dict[str, object] = {
        "schema": MANIFEST_SCHEMA,
        "status": "completed",
        "area": area,
        "purpose": "native-wed-cover-animations-test",
        "qa_status": "pending-ingame",
        "files": {
            output_path.name: {
                "bytes": len(patched),
                "sha256": sha256_bytes(patched),
            }
        },
        "wed_patch": {
            "source": "KEY/BIF",
            "source_bif": source_bif,
            "source_bytes": len(source),
            "source_sha256": sha256_bytes(source),
            "output_sha256": sha256_bytes(patched),
            "byte_difference_count": len(changes),
            "changes": changes,
        },
        "compatibility": {
            "x1_maps": "native WED semantics; unchanged tiles and overlays",
            "x4_maps": "same logical WED coordinates",
            "saves": "no serialized schema change",
            "rollback": "Restore-AreaOverrideAssets.ps1 with the install backup",
        },
    }

    rendered_manifest = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != rendered_manifest:
        raise RuntimeError(f"manifeste existant différent : {manifest_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(patched)
    manifest_path.write_text(rendered_manifest, encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("area", help="resref WED de la zone, par exemple AR0516")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--polygon",
        action="append",
        required=True,
        type=parse_polygon,
        help="index et flags source attendus (répétable), par exemple 65:0x05",
    )
    args = parser.parse_args()
    manifest = build(args.area, args.output_dir, args.polygon)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
