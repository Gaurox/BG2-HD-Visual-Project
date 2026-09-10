"""Extract deduplicated native sprite BAMs into the shared resource store.

The default is a read-only plan. At least one explicit selector is required.
``--run`` writes only native/canonical BAM bytes, per-source manifests and the
generated ``sprite/index/extractions.csv`` projection. It never decodes PNG
frames, runs an upscale, builds a registry, installs files or changes QA.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from run_creature_sprite_x2 import BAM_TYPE, KeyIndex, canonical_bam
from sprite_layout import load_group_rules
from workspace_paths import get_path


ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ROOT / "sprite/index/sprite_families.csv"
RESOURCES = ROOT / "sprite/index/sprite_resources.csv"
INVENTORY_MANIFEST = ROOT / "sprite/index/manifest.json"
GROUPS = ROOT / "sprite/index/family-groups.csv"
RESOURCE_STORE = ROOT / "sprite/ressources"
EXTRACTIONS = ROOT / "sprite/index/extractions.csv"
SHA256_RE = re.compile(r"[0-9A-F]{64}")
RESREF_RE = re.compile(r"[A-Z0-9_]{1,8}")
EXTRACTION_FIELDS = (
    "bam_resref",
    "source_sha256",
    "canonical_sha256",
    "source_bif",
    "locator",
    "source_file",
    "canonical_file",
    "source_manifest",
    "extraction_state",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def split_values(value: str) -> set[str]:
    return {part.strip() for part in value.split(";") if part.strip()}


def normalize_animation_id(value: str) -> str:
    if not re.fullmatch(r"0x[0-9A-Fa-f]{4}", value):
        raise ValueError(f"animation_id invalide: {value!r}")
    return f"0x{int(value, 16):04X}"


def select_inventory(
    *,
    family_ids: Iterable[str] = (),
    animation_ids: Iterable[str] = (),
    engine_sections: Iterable[str] = (),
    macro_groups: Iterable[str] = (),
    resrefs: Iterable[str] = (),
    all_ready: bool = False,
    include_blocked: bool = False,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    requested_families = set(family_ids)
    requested_animations = {normalize_animation_id(value) for value in animation_ids}
    requested_sections = {value.strip() for value in engine_sections}
    requested_macros = {value.strip() for value in macro_groups}
    requested_resrefs = {value.upper() for value in resrefs}
    if any(not RESREF_RE.fullmatch(value) for value in requested_resrefs):
        raise ValueError("--resref exige 1..8 caractères BAM ASCII")
    if not (
        requested_families
        or requested_animations
        or requested_sections
        or requested_macros
        or requested_resrefs
        or all_ready
    ):
        raise ValueError("sélecteur requis; utiliser une portée explicite ou --all-ready")
    rules = load_group_rules(GROUPS)
    known_macros = {rule.macro_group for rule in rules.values()}
    unknown_macros = requested_macros - known_macros
    if unknown_macros:
        raise ValueError("macro_group inconnu: " + ", ".join(sorted(unknown_macros)))
    unknown_sections = requested_sections - set(rules)
    if unknown_sections:
        raise ValueError("engine_section inconnu: " + ", ".join(sorted(unknown_sections)))

    families = read_csv(FAMILIES)
    resources = read_csv(RESOURCES)
    known_family_ids = {row.get("family_id", "") for row in families}
    unknown_families = requested_families - known_family_ids
    if unknown_families:
        raise ValueError("family_id inconnu: " + ", ".join(sorted(unknown_families)))
    known_resrefs = {row.get("bam_resref", "").upper() for row in resources}
    unknown_resrefs = requested_resrefs - known_resrefs
    if unknown_resrefs:
        raise ValueError("resref inconnu: " + ", ".join(sorted(unknown_resrefs)))

    use_family_filters = bool(
        requested_families
        or requested_animations
        or requested_sections
        or requested_macros
        or all_ready
    )
    selected_families: list[dict[str, str]] = []
    if use_family_filters:
        for row in families:
            section = row.get("engine_section", "")
            rule = rules.get(section)
            if requested_families and row.get("family_id", "") not in requested_families:
                continue
            if requested_animations and normalize_animation_id(
                row.get("animation_id", "")
            ) not in requested_animations:
                continue
            if requested_sections and section not in requested_sections:
                continue
            if requested_macros and (rule is None or rule.macro_group not in requested_macros):
                continue
            if all_ready and row.get("pipeline_ready", "").lower() != "yes":
                continue
            if not include_blocked and row.get("pipeline_ready", "").lower() != "yes":
                continue
            selected_families.append(row)
    selected_family_ids = {row["family_id"] for row in selected_families}
    selected_resources = []
    for row in resources:
        resref = row.get("bam_resref", "").upper()
        by_resref = resref in requested_resrefs
        by_family = bool(selected_family_ids & split_values(row.get("family_ids", "")))
        if not (by_resref or by_family):
            continue
        if not include_blocked and row.get("blocker", ""):
            continue
        selected_resources.append(row)
    return selected_families, selected_resources


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"chemin hors workspace: {path}") from error


def json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def manifest_payload_path(destination: Path, manifest: Mapping[str, object], field: str) -> Path:
    value = str(manifest.get(field, "")).replace("\\", "/")
    relative_path = Path(value)
    if not value or relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"chemin {field} non canonique: {value!r}")
    resolved = (ROOT / relative_path).resolve()
    if resolved.parent != destination.resolve():
        raise ValueError(f"chemin {field} hors source: {value!r}")
    return resolved


def verify_existing_source(destination: Path, expected: Mapping[str, str]) -> None:
    manifest_path = destination / "source.json"
    if not manifest_path.is_file():
        raise ValueError(f"source partielle sans manifeste: {relative(destination)}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for field in ("bam_resref", "source_sha256", "canonical_sha256"):
        if str(manifest.get(field, "")).upper() != expected[field].upper():
            raise ValueError(f"source existante divergente: {relative(destination)} ({field})")
    for field in ("source_file", "canonical_file"):
        path = manifest_payload_path(destination, manifest, field)
        if not path.is_file():
            raise ValueError(f"payload source absent: {relative(path)}")
    source_path = manifest_payload_path(destination, manifest, "source_file")
    canonical_path = manifest_payload_path(destination, manifest, "canonical_file")
    if sha256_bytes(source_path.read_bytes()) != expected["source_sha256"].upper():
        raise ValueError(f"hash source divergent: {relative(destination)}")
    if sha256_bytes(canonical_path.read_bytes()) != expected["canonical_sha256"].upper():
        raise ValueError(f"hash canonique divergent: {relative(destination)}")
    if not SHA256_RE.fullmatch(
        str(manifest.get("inventory_manifest_sha256", "")).upper()
    ):
        raise ValueError(f"hash du snapshot inventaire invalide: {relative(destination)}")


def extract_one(
    row: Mapping[str, str], index: KeyIndex, bam_map: Mapping[str, tuple[str, int, int]]
) -> bool:
    resref = row["bam_resref"].upper()
    source_sha256 = row["source_sha256"].upper()
    canonical_sha256 = row["canonical_sha256"].upper()
    if not SHA256_RE.fullmatch(source_sha256) or not SHA256_RE.fullmatch(canonical_sha256):
        raise ValueError(f"hash inventaire invalide pour {resref}")
    destination = RESOURCE_STORE / resref / "sources" / source_sha256.lower()
    expected = {
        "bam_resref": resref,
        "source_sha256": source_sha256,
        "canonical_sha256": canonical_sha256,
    }
    if destination.exists():
        verify_existing_source(destination, expected)
        return False
    entry = bam_map.get(resref)
    if entry is None:
        raise ValueError(f"BAM absent du chitin.key courant: {resref}")
    raw, bif_name = index.resolve(entry)
    canonical, packed = canonical_bam(raw)
    if sha256_bytes(raw) != source_sha256:
        raise ValueError(f"source installée différente de l'inventaire: {resref}")
    if sha256_bytes(canonical) != canonical_sha256:
        raise ValueError(f"BAM canonique différent de l'inventaire: {resref}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{source_sha256.lower()}-", dir=destination.parent))
    try:
        source_name = "source.bamc" if packed else "source.bam"
        (temporary / source_name).write_bytes(raw)
        if packed:
            (temporary / "source.bam").write_bytes(canonical)
        manifest = {
            "schema": "bg2-upscale-sprite-native-source-v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "bam_resref": resref,
            "source_bif": bif_name.replace("\\", "/"),
            "locator": row["locator"],
            "source_sha256": source_sha256,
            "canonical_sha256": canonical_sha256,
            "source_file": relative(destination / source_name),
            "canonical_file": relative(destination / "source.bam"),
            "inventory_manifest": relative(INVENTORY_MANIFEST),
            "inventory_manifest_sha256": sha256_bytes(INVENTORY_MANIFEST.read_bytes()),
        }
        (temporary / "source.json").write_bytes(json_bytes(manifest))
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    verify_existing_source(destination, expected)
    return True


def extraction_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not RESOURCE_STORE.is_dir():
        return rows
    for path in RESOURCE_STORE.glob("*/sources/*/source.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "bam_resref": str(value["bam_resref"]),
                "source_sha256": str(value["source_sha256"]),
                "canonical_sha256": str(value["canonical_sha256"]),
                "source_bif": str(value["source_bif"]),
                "locator": str(value["locator"]),
                "source_file": str(value["source_file"]),
                "canonical_file": str(value["canonical_file"]),
                "source_manifest": relative(path),
                "extraction_state": "verified",
            }
        )
    return sorted(rows, key=lambda row: (row["bam_resref"], row["source_sha256"]))


def csv_bytes(rows: Iterable[Mapping[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=EXTRACTION_FIELDS, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


def write_extractions_projection() -> None:
    payload = csv_bytes(extraction_rows())
    temporary = EXTRACTIONS.with_suffix(".csv.partial")
    temporary.write_bytes(payload)
    temporary.replace(EXTRACTIONS)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-id", action="append", default=[])
    parser.add_argument("--animation-id", action="append", default=[])
    parser.add_argument("--engine-section", action="append", default=[])
    parser.add_argument("--macro-group", action="append", default=[])
    parser.add_argument("--resref", action="append", default=[])
    parser.add_argument("--all-ready", action="store_true")
    parser.add_argument("--include-blocked", action="store_true")
    parser.add_argument("--list", action="store_true", help="inclut les resrefs dans le plan")
    parser.add_argument("--run", action="store_true", help="exécute l'extraction native")
    return parser


def main() -> int:
    args = make_parser().parse_args()
    families, resources = select_inventory(
        family_ids=args.family_id,
        animation_ids=args.animation_id,
        engine_sections=args.engine_section,
        macro_groups=args.macro_group,
        resrefs=args.resref,
        all_ready=args.all_ready,
        include_blocked=args.include_blocked,
    )
    result: dict[str, object] = {
        "status": "planned" if not args.run else "completed",
        "family_count": len(families),
        "resource_count": len(resources),
        "already_extracted": 0,
        "written": 0,
    }
    if args.list:
        result["resrefs"] = [row["bam_resref"] for row in resources]
    if args.run:
        game_root = get_path("bg2ee_game_root")
        index = KeyIndex(game_root)
        bam_map = index.resource_map(BAM_TYPE)
        for row in resources:
            if extract_one(row, index, bam_map):
                result["written"] = int(result["written"]) + 1
            else:
                result["already_extracted"] = int(result["already_extracted"]) + 1
        write_extractions_projection()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
