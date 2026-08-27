"""Extract every BAM used by map-area animations and build reusable indexes.

The output keeps one canonical export per BAM resource and records every map
placement separately.  This matters because a resource can be reused across
many areas (and many times inside one area).

Usage:
    python extract_area_animations.py [output_dir] [--dry-run]

The default output directory is ``G:\\AI\\BG2_Upscale\\animations``.
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


def parse_area(area_id: str, data: bytes) -> list[dict[str, object]]:
    """Return the animation placements declared by one V1 ARE resource."""
    if data[:4] != b"AREA":
        raise ValueError(f"{area_id}: signature ARE inattendue: {data[:8]!r}")

    count = struct.unpack_from("<I", data, 0xAC)[0]
    offset = struct.unpack_from("<I", data, 0xB0)[0]
    end = offset + count * 76
    if end > len(data):
        raise ValueError(f"{area_id}: table d'animations hors du fichier")

    rows = []
    for index in range(count):
        pos = offset + index * 76
        name = data[pos:pos + 32].split(b"\0")[0].decode("cp1252", "replace")
        x, y = struct.unpack_from("<hh", data, pos + 0x20)
        bam = data[pos + 0x28:pos + 0x30].split(b"\0")[0].decode("ascii", "replace").upper()
        sequence, initial_frame = struct.unpack_from("<HH", data, pos + 0x30)
        flags = struct.unpack_from("<I", data, pos + 0x34)[0]
        if not bam:
            continue
        rows.append({
            "area_id": area_id,
            "occurrence_index": index,
            "instance_name": name,
            "bam_resref": bam,
            "x": x,
            "y": y,
            "cell_x": x // 64,
            "cell_y": y // 64,
            "sequence": sequence,
            "initial_frame": initial_frame,
            "flags_hex": f"0x{flags:08X}",
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
    parser.add_argument("--keep-going", action="store_true", help="signale les ressources invalides au lieu d'arreter")
    args = parser.parse_args()

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

    occurrences.sort(key=lambda row: (str(row["bam_resref"]), str(row["area_id"]), int(row["occurrence_index"])))
    used_bams = sorted({str(row["bam_resref"]) for row in occurrences})
    missing_bams = [name for name in used_bams if name not in bam_entries]

    area_counts = Counter(str(row["area_id"]) for row in occurrences)
    area_resources: dict[str, set[str]] = defaultdict(set)
    bam_occurrences = Counter(str(row["bam_resref"]) for row in occurrences)
    bam_areas: dict[str, set[str]] = defaultdict(set)
    for row in occurrences:
        area_resources[str(row["area_id"])].add(str(row["bam_resref"]))
        bam_areas[str(row["bam_resref"])].add(str(row["area_id"]))

    print(f"ARE analysees : {len(area_entries)}")
    print(f"Occurrences  : {len(occurrences)}")
    print(f"BAM distincts: {len(used_bams)}")
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
            resource_dir = resources_dir / resref
            resource_dir.mkdir(exist_ok=True)
            (resource_dir / "source.bam").write_bytes(raw)
            maxw, maxh, frame_count = export(resref, frames, rgb, transparent, str(resource_dir))
            resource_rows.append({
                "bam_resref": resref,
                "format": raw[:8].decode("ascii", "replace").strip(),
                "frames": frame_count,
                "max_frame_width": maxw,
                "max_frame_height": maxh,
                "occurrences": bam_occurrences[resref],
                "areas": len(bam_areas[resref]),
                "area_ids": ";".join(sorted(bam_areas[resref])),
                "relative_path": (Path("ressources") / resref).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
            print(f"[{number}/{len(used_bams)}] {resref}: {frame_count} frames")
        except Exception as exc:
            failures.append({"kind": "bam", "name": resref, "error": str(exc)})
            if not args.keep_going:
                raise

    resource_rows.sort(key=lambda row: str(row["bam_resref"]))
    areas_rows = [{
        "area_id": area_id,
        "occurrences": area_counts[area_id],
        "distinct_bams": len(area_resources[area_id]),
        "bam_resrefs": ";".join(sorted(area_resources[area_id])),
    } for area_id in sorted(area_counts)]
    write_csv(index_dir / "ressources.csv", list(resource_rows[0]) if resource_rows else ["bam_resref"], resource_rows)
    write_csv(index_dir / "occurrences.csv", [
        "area_id", "occurrence_index", "instance_name", "bam_resref", "x", "y", "cell_x", "cell_y",
        "sequence", "initial_frame", "flags_hex",
    ], occurrences)
    write_csv(index_dir / "zones.csv", ["area_id", "occurrences", "distinct_bams", "bam_resrefs"], areas_rows)
    write_csv(index_dir / "erreurs.csv", ["kind", "name", "error"], failures)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "area_resources_scanned": len(area_entries),
        "animation_occurrences": len(occurrences),
        "distinct_bams_referenced": len(used_bams),
        "exported_bams": len(resource_rows),
        "missing_bams": missing_bams,
        "failures": failures,
    }
    (index_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
        "- `index/occurrences.csv` : chaque pose d'animation dans une zone.\n"
        "- `index/ressources.csv` : une ligne par BAM et les zones qui l'utilisent.\n"
        "- `index/zones.csv` : synthese par zone.\n",
        encoding="utf-8",
    )
    print(f"\nTermine: {len(resource_rows)} BAM exportes dans {output}")
    if failures:
        print(f"Avertissements: {len(failures)} (voir index/erreurs.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
