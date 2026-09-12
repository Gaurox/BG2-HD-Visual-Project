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
    if child.get("schema") != "bg2-water-route2-registry-v2" or child.get("version") != 2:
        raise RuntimeError("unsupported water route2 registry")
    parent_ref = child.get("parent", {})
    parent_path = WORKSPACE_ROOT / str(parent_ref.get("path", ""))
    if not parent_path.is_file() or sha256(parent_path) != parent_ref.get("sha256"):
        raise RuntimeError("water route2 parent registry is absent or divergent")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
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
        padded_slots = slots + [""] * (5 - len(slots))
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
                "{" + ", ".join(cpp_resref(slot) for slot in padded_slots) + "}",
                cpp_sha(entry["wed"]["sha256"]),
                "true" if entry["allow_stock_wed_when_override_absent"] else "false",
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
