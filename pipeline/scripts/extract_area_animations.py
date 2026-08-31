"""Inventory every ARE animation resource and extract its BAM sources.

The occurrence index distinguishes BAM, WBM and direct PVRZ resources from the
ARE flags.  BAM sources keep one canonical export, while WBM/PVRZ occurrences
remain inventoried without being misreported as missing BAM files.  External
ARE palettes are recorded per occurrence and summarised per BAM.

Usage:
    python extract_area_animations.py [output_dir] [--dry-run|--index-only]

The default output directory is the workspace-relative ``animations`` directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import struct
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bam_export import decode_bam, export, load_bam
from bg2lib import load_key, resolve_resource


AREA_TYPE = 0x03F2
BAM_TYPE = 0x03E8
DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "animations"
ARE_ANIMATION_SIZE = 76
FLAG_EXTERNAL_PALETTE = 1 << 10
FLAG_WBM_RESREF = 1 << 13
FLAG_PVRZ_RESREF = 1 << 15
RESOURCE_KINDS = ("BAM", "WBM", "PVRZ")
OCCURRENCE_FIELDS = [
    "area_id", "occurrence_index", "instance_name", "resource_resref", "resource_kind",
    "x", "y", "cell_x", "cell_y", "sequence", "initial_frame", "flags_hex",
    "palette_mode", "palette_resref",
]


def decode_resref(data: bytes, offset: int) -> str:
    return data[offset:offset + 8].split(b"\0")[0].decode("ascii", "replace").upper()


def resource_kind_from_flags(flags: int) -> str:
    use_wbm = bool(flags & FLAG_WBM_RESREF)
    use_pvrz = bool(flags & FLAG_PVRZ_RESREF)
    if use_wbm and use_pvrz:
        raise ValueError("flags ARE ambigus : WBM et PVRZ actifs simultanément")
    if use_wbm:
        return "WBM"
    if use_pvrz:
        return "PVRZ"
    return "BAM"


def parse_area(area_id: str, data: bytes) -> list[dict[str, object]]:
    """Return every typed animation placement declared by one V1 ARE resource."""
    if data[:4] != b"AREA":
        raise ValueError(f"{area_id}: signature ARE inattendue: {data[:8]!r}")

    count = struct.unpack_from("<I", data, 0xAC)[0]
    offset = struct.unpack_from("<I", data, 0xB0)[0]
    end = offset + count * ARE_ANIMATION_SIZE
    if end > len(data):
        raise ValueError(f"{area_id}: table d'animations hors du fichier")

    rows = []
    for index in range(count):
        pos = offset + index * ARE_ANIMATION_SIZE
        name = data[pos:pos + 32].split(b"\0")[0].decode("cp1252", "replace")
        x, y = struct.unpack_from("<hh", data, pos + 0x20)
        resref = decode_resref(data, pos + 0x28)
        sequence, initial_frame = struct.unpack_from("<HH", data, pos + 0x30)
        flags = struct.unpack_from("<I", data, pos + 0x34)[0]
        if not resref:
            continue
        resource_kind = resource_kind_from_flags(flags)
        palette_mode = "external" if flags & FLAG_EXTERNAL_PALETTE else "embedded"
        palette_resref = decode_resref(data, pos + 0x40) if palette_mode == "external" else ""
        if palette_mode == "external" and not palette_resref:
            raise ValueError(
                f"{area_id} occurrence {index}: palette externe active mais resref vide"
            )
        rows.append({
            "area_id": area_id,
            "occurrence_index": index,
            "instance_name": name,
            "resource_resref": resref,
            "resource_kind": resource_kind,
            "x": x,
            "y": y,
            "cell_x": x // 64,
            "cell_y": y // 64,
            "sequence": sequence,
            "initial_frame": initial_frame,
            "flags_hex": f"0x{flags:08X}",
            "palette_mode": palette_mode,
            "palette_resref": palette_resref,
        })
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true", help="indexe sans ecrire les BAM/images")
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="régénère seulement les CSV/manifest canoniques, sans réécrire les médias extraits",
    )
    parser.add_argument("--keep-going", action="store_true", help="signale les ressources invalides au lieu d'arreter")
    args = parser.parse_args()
    if args.dry_run and args.index_only:
        parser.error("--dry-run et --index-only sont incompatibles")

    bif_entries, resources = load_key()
    area_entries = sorted((name.upper(), locator) for name, rtype, locator in resources if rtype == AREA_TYPE)
    bam_entries = {name.upper(): (name, rtype, locator) for name, rtype, locator in resources if rtype == BAM_TYPE}

    occurrences: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    for area_id, locator in area_entries:
        try:
            resolved = resolve_resource(bif_entries, locator)
            if resolved is None:
                raise ValueError("ressource ARE introuvable dans le BIF")
            data, _ = resolved
            occurrences.extend(parse_area(area_id, data))
        except Exception as exc:  # a malformed optional area should not hide the rest of the catalog
            failures.append({"kind": "area", "name": area_id, "error": str(exc)})
            if not args.keep_going:
                raise

    occurrences.sort(key=lambda row: (
        str(row["resource_kind"]), str(row["resource_resref"]),
        str(row["area_id"]), int(row["occurrence_index"]),
    ))
    used_resources = sorted({str(row["resource_resref"]) for row in occurrences})
    used_bams = sorted({
        str(row["resource_resref"])
        for row in occurrences
        if row["resource_kind"] == "BAM"
    })
    missing_bams = [name for name in used_bams if name not in bam_entries]

    area_counts = Counter(str(row["area_id"]) for row in occurrences)
    area_resources: dict[str, set[str]] = defaultdict(set)
    area_kind_resources: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    area_kind_occurrences: dict[str, Counter[str]] = defaultdict(Counter)
    bam_occurrences = Counter(
        str(row["resource_resref"])
        for row in occurrences
        if row["resource_kind"] == "BAM"
    )
    bam_areas: dict[str, set[str]] = defaultdict(set)
    bam_external_palettes: dict[str, set[str]] = defaultdict(set)
    bam_external_palette_occurrences = Counter()
    for row in occurrences:
        area_id = str(row["area_id"])
        resref = str(row["resource_resref"])
        kind = str(row["resource_kind"])
        area_resources[area_id].add(resref)
        area_kind_resources[area_id][kind].add(resref)
        area_kind_occurrences[area_id][kind] += 1
        if kind == "BAM":
            bam_areas[resref].add(area_id)
            if row["palette_mode"] == "external":
                bam_external_palette_occurrences[resref] += 1
                bam_external_palettes[resref].add(str(row["palette_resref"]))

    print(f"ARE analysees : {len(area_entries)}")
    print(f"Occurrences  : {len(occurrences)}")
    for kind in RESOURCE_KINDS:
        kind_rows = [row for row in occurrences if row["resource_kind"] == kind]
        kind_resrefs = {str(row["resource_resref"]) for row in kind_rows}
        print(f"{kind} : {len(kind_rows)} occurrence(s), {len(kind_resrefs)} resref(s)")
    print(f"BAM manquants: {len(missing_bams)}")
    if args.dry_run:
        return 0

    output = args.output_dir.resolve()
    resources_dir = output / "ressources"
    index_dir = output / "index"
    resources_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)

    resource_rows: list[dict[str, object]] = []
    for number, resref in enumerate(used_bams, start=1):
        entry = bam_entries.get(resref)
        if entry is None:
            failures.append({"kind": "bam", "name": resref, "error": "absent du chitin.key"})
            continue
        try:
            raw = load_bam(bif_entries, entry)
            frames, rgb, transparent = decode_bam(raw)
            frame_count = len(frames)
            maxw = max(frame.shape[1] for frame, _, _, _ in frames)
            maxh = max(frame.shape[0] for frame, _, _, _ in frames)
            if not args.index_only:
                resource_dir = resources_dir / resref
                resource_dir.mkdir(exist_ok=True)
                (resource_dir / "source.bam").write_bytes(raw)
                maxw, maxh, frame_count = export(
                    resref, frames, rgb, transparent, str(resource_dir)
                )
            resource_rows.append({
                "bam_resref": resref,
                "format": raw[:8].decode("ascii", "replace").strip(),
                "frames": frame_count,
                "max_frame_width": maxw,
                "max_frame_height": maxh,
                "occurrences": bam_occurrences[resref],
                "areas": len(bam_areas[resref]),
                "area_ids": ";".join(sorted(bam_areas[resref])),
                "external_palette_occurrences": bam_external_palette_occurrences[resref],
                "external_palette_resrefs": ";".join(sorted(bam_external_palettes[resref])),
                "relative_path": (Path("ressources") / resref).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
            print(f"[{number}/{len(used_bams)}] {resref}: {frame_count} frames")
        except Exception as exc:
            failures.append({"kind": "bam", "name": resref, "error": str(exc)})
            if not args.keep_going:
                raise

    resource_rows.sort(key=lambda row: str(row["bam_resref"]))
    areas_rows = []
    for area_id in sorted(area_counts):
        row: dict[str, object] = {
            "area_id": area_id,
            "animation_occurrences": area_counts[area_id],
            "distinct_animation_resources": len(area_resources[area_id]),
            "animation_resrefs": ";".join(sorted(area_resources[area_id])),
        }
        for kind in RESOURCE_KINDS:
            prefix = kind.lower()
            row[f"{prefix}_occurrences"] = area_kind_occurrences[area_id][kind]
            row[f"distinct_{prefix}s"] = len(area_kind_resources[area_id][kind])
            row[f"{prefix}_resrefs"] = ";".join(sorted(area_kind_resources[area_id][kind]))
        palette_rows = [
            item for item in occurrences
            if item["area_id"] == area_id and item["palette_mode"] == "external"
        ]
        row["external_palette_occurrences"] = len(palette_rows)
        row["palette_resrefs"] = ";".join(sorted({
            str(item["palette_resref"]) for item in palette_rows
        }))
        areas_rows.append(row)
    write_csv(index_dir / "ressources.csv", list(resource_rows[0]) if resource_rows else ["bam_resref"], resource_rows)
    write_csv(index_dir / "occurrences.csv", OCCURRENCE_FIELDS, occurrences)
    write_csv(index_dir / "zones.csv", list(areas_rows[0]) if areas_rows else ["area_id"], areas_rows)
    write_csv(index_dir / "erreurs.csv", ["kind", "name", "error"], failures)

    kind_summary = {}
    for kind in RESOURCE_KINDS:
        kind_rows = [row for row in occurrences if row["resource_kind"] == kind]
        kind_summary[kind] = {
            "occurrences": len(kind_rows),
            "distinct_resrefs": len({str(row["resource_resref"]) for row in kind_rows}),
        }
    external_palette_rows = [
        row for row in occurrences if row["palette_mode"] == "external"
    ]
    manifest = {
        "schema": "bg2-upscale-area-animation-inventory-v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "area_resources_scanned": len(area_entries),
        "animation_occurrences": len(occurrences),
        "distinct_animation_resources_referenced": len(used_resources),
        "distinct_bams_referenced": len(used_bams),
        "exported_bams": len(resource_rows),
        "resource_kinds": kind_summary,
        "external_palette_occurrences": len(external_palette_rows),
        "external_palette_resrefs": sorted({
            str(row["palette_resref"]) for row in external_palette_rows
        }),
        "missing_bams": missing_bams,
        "failures": failures,
    }
    (index_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not args.index_only:
        readme = output / "README.md"
        readme.write_text(
            "# Bibliotheque d'animations de zones\n\n"
            "Pipeline d'upscale et integration runtime x1 logique / xN physique :\n"
            "[`UPSCALE_ANIMATIONS_ZONE.md`](UPSCALE_ANIMATIONS_ZONE.md).\n\n"
            "Automatisation de la preparation des assets :\n"
            "[`../pipeline/ANIMATION_UPSCALE_PIPELINE.md`](../pipeline/ANIMATION_UPSCALE_PIPELINE.md).\n\n"
            "- `ressources/<BAM>/source.bam` : source BAM V1 extraite.\n"
            "- `ressources/<BAM>/<BAM>_sheet.png` : planche RGB PNG sans perte.\n"
            "- `ressources/<BAM>/<BAM>_alpha.png` : masque alpha PNG associe.\n"
            "- `ressources/<BAM>/<BAM>.gif` : apercu anime.\n"
            "- `index/occurrences.csv` : chaque pose d'animation dans une zone, avec type de ressource et palette.\n"
            "- `index/ressources.csv` : une ligne par BAM et les zones qui l'utilisent.\n"
            "- `index/zones.csv` : synthese par zone.\n",
            encoding="utf-8",
        )
    action = "indexes, sans reecriture des medias" if args.index_only else "BAM exportes"
    print(f"\nTermine: {len(resource_rows)} {action} dans {output}")
    if failures:
        print(f"Avertissements: {len(failures)} (voir index/erreurs.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
