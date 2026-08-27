"""Refresh areas.csv from the BG2EE resources and the current map folders.

Only zones with an injectable PVRZ tileset are catalogued. Existing bilingual
names and manual notes are preserved.
"""
import csv
import struct
from pathlib import Path

from bg2lib import load_key, resolve_resource, resolve_tileset_resource

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAPS_ROOT = PROJECT_ROOT / "maps"
CATALOG = PROJECT_ROOT / "areas.csv"
FIELDS = [
    "area_id", "campaign", "name_fr", "name_en", "name_source", "name_strref",
    "name_confidence", "location_group", "accessible_from", "resolution_x1", "resolution_x1_mpx",
    "split_seedvr", "map_variants_count", "workload_mpx", "workload_done_mpx",
    "x1_tuiles_principales", "x1_tuiles_secondaires", "runs",
    "build", "status", "has_night_variant", "x1_tuiles_principales_nuit",
    "x1_tuiles_secondaires_nuit", "runs_nuit", "build_nuit", "status_nuit",
    "spline_fit_1_0", "notes",
]
COMPLETED_STATUSES = {"installed-pending-qa", "validated-installed"}


def derive_workload_done_mpx(row: dict) -> str:
    """Return the Mpx covered by completed day/night variants.

    ``workload_mpx`` already includes every required variant.  A night variant
    therefore represents half of the workload: the day and night statuses each
    contribute their half only when the variant is installed or validated.
    """
    workload_text = row.get("workload_mpx", "").strip()
    if not workload_text:
        return "0.00"
    try:
        workload = float(workload_text)
    except ValueError as exc:
        raise ValueError(
            f"{row.get('area_id', '<unknown>')}: workload_mpx invalide: {workload_text!r}"
        ) from exc

    day_done = row.get("status") in COMPLETED_STATUSES
    if row.get("has_night_variant") != "yes":
        return f"{workload if day_done else 0:.2f}"

    night_done = row.get("status_nuit") in COMPLETED_STATUSES
    return f"{workload * 0.5 * (day_done + night_done):.2f}"


def injectable_areas():
    bif_entries, resources = load_key()
    are_entries = [entry for entry in resources if entry[1] == 0x03F2]
    wed_by_name = {entry[0].upper(): entry for entry in resources if entry[1] == 0x03E9}
    tis_by_name = {entry[0].upper(): entry for entry in resources if entry[1] == 0x03EB}
    result = []

    for area_id, _resource_type, locator in are_entries:
        try:
            area, _ = resolve_resource(bif_entries, locator)
            if area[:4] != b"AREA":
                continue
            wed, _ = resolve_resource(bif_entries, wed_by_name[area_id.upper()][2])
            if wed[:4] != b"WED ":
                continue
            overlay_offset = struct.unpack_from("<III", wed, 8)[2]
            tileset = wed[overlay_offset + 4:overlay_offset + 12].split(b"\0")[0].decode("ascii").upper()
            _data, _count, entry_size, _bif = resolve_tileset_resource(
                bif_entries, tis_by_name[tileset][2]
            )
            if entry_size == 12:  # PVRZ tileset, supported by the injection pipeline
                result.append(area_id.upper())
        except (KeyError, ValueError, struct.error, TypeError):
            continue
    return sorted(set(result)), wed_by_name


def existing_rows():
    """Read areas.csv, tolerating legacy rows whose ``notes`` field has an
    unquoted comma: earlier writes let it spill into the blank trailing
    columns of the on-disk header instead of quoting the field. Rejoining
    everything from the ``notes`` position onward with a comma reverses an
    unquoted split exactly; ``csv.DictWriter`` will quote it properly this
    time, so the file self-heals on the next refresh.
    """
    # ``areas.csv`` may be saved by Excel with a UTF-8 BOM; ``utf-8-sig``
    # accepts both forms and keeps ``area_id`` usable as the first header.
    with CATALOG.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        header = next(reader, [])
        notes_pos = header.index("notes") if "notes" in header else len(header)
        rows: dict[str, dict] = {}
        for values in reader:
            if not values or not values[0]:
                continue
            row = {field: (values[i] if i < len(values) else "") for i, field in enumerate(header[:notes_pos])}
            row["notes"] = ",".join(values[notes_pos:]).rstrip(",")
            rows[row["area_id"]] = row
    return rows


def main():
    old = existing_rows()
    injectable, wed_by_name = injectable_areas()
    rows = []

    for area_id in injectable:
        old_row = old.get(area_id, {})
        area_root = MAPS_ROOT / area_id / "rendus-x1"
        primary = area_root / "tuiles-principales" / f"{area_id}-tuiles-principales-x1.png"
        secondary = area_root / "tuiles-secondaires" / f"{area_id}-tuiles-secondaires-x1.png"
        has_night = f"{area_id}N" in wed_by_name
        primary_nuit = area_root / "tuiles-principales-nuit" / f"{area_id}N-tuiles-principales-x1.png"
        secondary_nuit = area_root / "tuiles-secondaires-nuit" / f"{area_id}N-tuiles-secondaires-x1.png"
        row = {field: old_row.get(field, "") for field in FIELDS}
        row["area_id"] = area_id
        row["x1_tuiles_principales"] = "yes" if primary.is_file() else "no"
        row["x1_tuiles_secondaires"] = "yes" if secondary.is_file() else "no"
        row["has_night_variant"] = "yes" if has_night else "no"
        row["x1_tuiles_principales_nuit"] = ("yes" if primary_nuit.is_file() else "no") if has_night else ""
        row["x1_tuiles_secondaires_nuit"] = ("yes" if secondary_nuit.is_file() else "no") if has_night else ""
        if not row["status"]:
            row["status"] = "source-only" if primary.is_file() else "source-pending"
        row["workload_done_mpx"] = derive_workload_done_mpx(row)
        rows.append(row)

    with CATALOG.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Zones injectables : {len(rows)}")
    print(f"Rendus principaux x1 : {sum(row['x1_tuiles_principales'] == 'yes' for row in rows)}")
    print(f"Rendus secondaires x1 : {sum(row['x1_tuiles_secondaires'] == 'yes' for row in rows)}")
    print(f"Zones avec variante nuit : {sum(row['has_night_variant'] == 'yes' for row in rows)}")
    print(f"Rendus principaux nuit extraits : {sum(row['x1_tuiles_principales_nuit'] == 'yes' for row in rows)}")
    print(f"Rendus secondaires nuit extraits : {sum(row['x1_tuiles_secondaires_nuit'] == 'yes' for row in rows)}")


if __name__ == "__main__":
    main()
