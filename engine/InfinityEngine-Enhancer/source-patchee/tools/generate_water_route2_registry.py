"""Generate the compile-time water route2 allowlist from its versioned JSON authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = SOURCE_ROOT.parents[2]
DEFAULT_INPUT = SOURCE_ROOT / "assets" / "water-route2" / "registry-v2.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_registry(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    child = json.loads(path.read_text(encoding="utf-8"))
    schema = child.get("schema")
    version = child.get("version")
    if (schema, version) not in {
        ("bg2-water-route2-registry-v2", 2),
        ("bg2-water-route2-registry-v3", 3),
    }:
        raise RuntimeError("unsupported water route2 registry")
    parent_ref = child.get("parent", {})
    parent_path = WORKSPACE_ROOT / str(parent_ref.get("path", ""))
    if not parent_path.is_file() or sha256(parent_path) != parent_ref.get("sha256"):
        raise RuntimeError("water route2 parent registry is absent or divergent")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    if version == 2:
        if parent.get("schema") != "bg2-water-route2-registry-v1" or parent.get("version") != 1:
            raise RuntimeError("unsupported parent water route2 registry")
        overrides = {item["id"]: item for item in child.get("entry_overrides", [])}
        entries = parent.get("entries", [])
        if set(overrides) != {entry.get("id") for entry in entries}:
            raise RuntimeError("v2 overrides must cover every active parent entry exactly")
        resolved = []
        for entry in entries:
            if entry.get("state") != "approved-ingame" or entry.get("qa", {}).get("status") != "validated-ingame":
                raise RuntimeError(f"unapproved entry in active registry: {entry.get('id')}")
            merged = dict(entry)
            merged.update(overrides[entry["id"]])
            resolved.append(merged)
    else:
        if parent.get("schema") != "bg2-water-route2-registry-v2" or parent.get("version") != 2:
            raise RuntimeError("unsupported parent water route2 registry")
        parent_ids = {item.get("id") for item in parent.get("entry_overrides", [])}
        resolved = child.get("entries", [])
        ids = [entry.get("id") for entry in resolved]
        if not ids or len(ids) != len(set(ids)) or not parent_ids.issubset(set(ids)):
            raise RuntimeError("v3 entries must be unique and retain every active parent id")
        for entry in resolved:
            state = entry.get("state")
            qa_status = entry.get("qa", {}).get("status")
            if state == "approved-ingame":
                if qa_status != "validated-ingame":
                    raise RuntimeError(f"approved v3 entry lacks ingame QA: {entry.get('id')}")
            elif state == "candidate-installable-pending-qa":
                if qa_status != "pending-ingame":
                    raise RuntimeError(f"candidate v3 entry has divergent QA state: {entry.get('id')}")
            else:
                raise RuntimeError(f"unsupported v3 entry state: {entry.get('id')}")
    return child, {"entries": resolved}


def cpp_resref(value: str) -> str:
    upper = value.upper()
    if not 0 <= len(upper) <= 8 or any(ord(char) < 33 or ord(char) > 126 for char in upper):
        raise RuntimeError(f"invalid resref: {value!r}")
    return f'resref_array("{upper}")'


def cpp_sha(value: str) -> str:
    if len(value) != 64:
        raise RuntimeError("invalid SHA-256")
    raw = bytes.fromhex(value)
    return "{" + ", ".join(f"std::byte{{0x{byte:02X}}}" for byte in raw) + "}"


def file_records(entry: dict[str, Any]) -> list[dict[str, Any]]:
    records = [{
        "kind": "BaseTis",
        "resref": entry["base_tis"]["resref"],
        "width": 0,
        "height": 0,
        "bytes": entry["base_tis"]["bytes"],
        "sha256": entry["base_tis"]["sha256"],
    }]
    records.extend({"kind": "BasePvrz", **page} for page in entry["base_tis"]["pages"])
    records.append({
        "kind": "OverlayTis",
        "resref": entry["overlay"]["tis_resref"],
        "width": 0,
        "height": 0,
        "bytes": entry["overlay"]["tis_bytes"],
        "sha256": entry["overlay"]["tis_sha256"],
    })
    records.extend({"kind": "OverlayPvrz", **page} for page in entry["overlay"]["pages"])
    return records


def generate(path: Path) -> str:
    child, resolved = load_registry(path)
    entries = resolved["entries"]
    files: list[dict[str, Any]] = []
    entry_lines = []
    art_lines = []
    identities: set[tuple[str, int, str]] = set()
    for entry in entries:
        overlay = entry["overlay"]
        identity = (entry["wed"]["resref"], overlay["slot"], overlay["tis_resref"])
        if identity in identities:
            raise RuntimeError(f"duplicate route2 identity: {identity}")
        identities.add(identity)
        start = len(files)
        current_files = file_records(entry)
        files.extend(current_files)
        slots = entry["wed"]["overlay_slots"]
        if not 2 <= len(slots) <= 5 or overlay["slot"] >= len(slots):
            raise RuntimeError(f"invalid WED layout: {entry['id']}")
        if not 0.0 <= float(entry["approved_strength"]) <= 1.0:
            raise RuntimeError(f"invalid approved strength: {entry['id']}")
        temporal = entry.get("temporal_overlay") or {}
        temporal_values = {
            "frame_count": int(temporal.get("frame_count", 0)),
            "source_fps": float(temporal.get("source_fps", 0.0)),
            "target_fps": float(temporal.get("target_fps", 0.0)),
            "columns": int(temporal.get("atlas_columns", 0)),
            "stride": int(temporal.get("atlas_stride_pixels", 0)),
            "padding": int(temporal.get("atlas_padding_pixels", 0)),
        }
        if temporal:
            pages = overlay["pages"]
            rows = ((temporal_values["frame_count"] + temporal_values["columns"] - 1)
                    // temporal_values["columns"] if temporal_values["columns"] > 0 else 0)
            if (temporal.get("mode") != "atlas-linear" or len(pages) != 1 or
                    temporal_values["frame_count"] != int(overlay["tile_count"]) or
                    temporal_values["frame_count"] < 2 or
                    temporal_values["source_fps"] <= 0.0 or
                    temporal_values["target_fps"] < temporal_values["source_fps"] or
                    temporal_values["columns"] <= 0 or temporal_values["stride"] <= 0 or
                    temporal_values["padding"] < 0 or
                    temporal_values["stride"] !=
                    int(overlay["tile_dimension"]) + 2 * temporal_values["padding"] or
                    temporal_values["columns"] * temporal_values["stride"] >
                    int(pages[0]["width"]) or
                    rows * temporal_values["stride"] > int(pages[0]["height"])):
                raise RuntimeError(f"invalid temporal overlay: {entry['id']}")
        padded_slots = slots + [""] * (5 - len(slots))
        art = entry.get("local_art_opacity")
        art_fields = ["{}", "0", "0"]
        if art is not None:
            ids = art.get("secondary_tile_ids", [])
            source_alpha = art.get("source_draw_alpha")
            target_alpha = art.get("target_draw_alpha")
            if (art.get("mode") != "paired-primary-texture-secondary-draw" or
                    not ids or ids != sorted(set(ids)) or len(ids) > 65535 or
                    any(type(i) is not int or not 0 <= i < min(65535, entry["base_tis"]["tile_count"]) for i in ids) or
                    type(source_alpha) is not int or not 1 <= source_alpha <= 255 or
                    type(target_alpha) is not int or not 1 <= target_alpha <= 255 or
                    art.get("primary_texture_alpha") != target_alpha or
                    entry["allow_stock_wed_when_override_absent"]):
                raise RuntimeError(f"invalid paired art opacity: {entry['id']}")
            symbol = f"kSecondaryArtTiles{len(art_lines)}"
            art_lines.append(f"inline constexpr std::array<std::uint16_t, {len(ids)}> {symbol}{{{{" +
                             ", ".join(str(i) for i in ids) + "}};")
            art_fields = [symbol, str(source_alpha), str(target_alpha)]
        entry_lines.append(
            "  RegistryEntry{" + ", ".join([
                cpp_resref(entry["wed"]["resref"]),
                cpp_resref(entry["base_tis"]["resref"]),
                cpp_resref(overlay["tis_resref"]),
                str(overlay["slot"]),
                str(entry["wed"]["grid"]["width"]),
                str(entry["wed"]["grid"]["height"]),
                str(len(slots)),
                str(entry["base_tis"]["tile_count"]),
                str(overlay["tile_count"]),
                str(overlay["tile_dimension"]),
                str(entry["overlay_coverage_cells"]),
                str(start),
                str(len(current_files)),
                f"{float(entry['approved_strength']):.8f}f",
                str(entry["material_id"]),
                str(temporal_values["frame_count"]),
                f"{temporal_values['source_fps']:.8f}f",
                f"{temporal_values['target_fps']:.8f}f",
                str(temporal_values["columns"]),
                str(temporal_values["stride"]),
                str(temporal_values["padding"]),
                "{" + ", ".join(cpp_resref(slot) for slot in padded_slots) + "}",
                cpp_sha(entry["wed"]["sha256"]),
                "true" if entry["allow_stock_wed_when_override_absent"] else "false",
                *art_fields,
            ]) + "},"
        )
    file_lines = [
        "  RegistryFileEvidence{" + ", ".join([
            f"RegistryFileKind::{record['kind']}",
            cpp_resref(record["resref"]),
            str(record.get("width", 0)),
            str(record.get("height", 0)),
            str(record["bytes"]),
            cpp_sha(record["sha256"]),
        ]) + "},"
        for record in files
    ]
    return "\n".join([
        "#pragma once",
        "",
        "// Generated by tools/generate_water_route2_registry.py; do not edit.",
        "namespace iee::water_route2::generated {",
        f"inline constexpr std::uint32_t kRegistryVersion = {child['version']};",
        f"inline constexpr std::array<RegistryFileEvidence, {len(files)}> kFiles{{{{",
        *file_lines,
        "}};",
        *art_lines,
        f"inline constexpr std::array<RegistryEntry, {len(entries)}> kEntries{{{{",
        *entry_lines,
        "}};",
        "}  // namespace iee::water_route2::generated",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = generate(args.input.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".part")
    temporary.write_text(output, encoding="utf-8", newline="\n")
    temporary.replace(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
