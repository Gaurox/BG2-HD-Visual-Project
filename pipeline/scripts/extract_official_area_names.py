"""Read official bilingual area names directly from BG2EE world-map resources.

Only areas listed in WORLDMAP or WORLDM25 are emitted.  Interior maps and
sub-areas without a direct world-map entry are deliberately omitted: their
names need separate verification before they are added to areas.csv.

Usage:
    python extract_official_area_names.py
    python extract_official_area_names.py --verify-csv <areas.csv>
"""
import argparse
import csv
import struct
from pathlib import Path

from bg2lib import GAME_DIR, load_key, resolve_resource

WORLD_MAP_TYPE = 0x03F7
WORLD_MAP_ENTRY_SIZE = 184
AREA_ENTRY_SIZE = 240


def read_tlk(language: str):
    data = Path(GAME_DIR, "lang", language, "dialog.tlk").read_bytes()
    if data[:8] != b"TLK V1  ":
        raise ValueError(f"dialog.tlk {language}: signature invalide")
    count = struct.unpack_from("<I", data, 10)[0]
    text_offset = struct.unpack_from("<I", data, 14)[0]

    def string(strref: int) -> str:
        if strref == 0xFFFFFFFF or strref >= count:
            return ""
        entry = 18 + strref * 26
        offset, length = struct.unpack_from("<II", data, entry + 18)
        return data[text_offset + offset:text_offset + offset + length].decode(
            "utf-8", errors="replace"
        )

    return string


def official_names():
    bif_entries, resources = load_key()
    tlk_fr = read_tlk("fr_FR")
    tlk_en = read_tlk("en_US")
    rows = {}

    for name, resource_type, locator in resources:
        if resource_type != WORLD_MAP_TYPE or name.upper() not in {"WORLDMAP", "WORLDM25"}:
            continue
        data, _ = resolve_resource(bif_entries, locator)
        map_count, maps_offset = struct.unpack_from("<II", data, 8)
        for map_index in range(map_count):
            world_map = maps_offset + map_index * WORLD_MAP_ENTRY_SIZE
            area_count, areas_offset = struct.unpack_from("<II", data, world_map + 32)
            for area_index in range(area_count):
                area = areas_offset + area_index * AREA_ENTRY_SIZE
                area_id = data[area:area + 8].split(b"\0")[0].decode("ascii").upper()
                strref = struct.unpack_from("<I", data, area + 64)[0]
                rows[area_id] = {
                    "name_fr": tlk_fr(strref),
                    "name_en": tlk_en(strref),
                    "name_source": name.upper(),
                    "name_strref": str(strref),
                    "name_confidence": "official",
                }
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-csv", type=Path)
    args = parser.parse_args()
    names = official_names()

    if args.verify_csv is None:
        print("area_id,name_fr,name_en,name_source,name_strref,name_confidence")
        for area_id in sorted(names):
            row = names[area_id]
            print(",".join([area_id] + [row[key] for key in (
                "name_fr", "name_en", "name_source", "name_strref", "name_confidence"
            )]))
        return

    with args.verify_csv.open(encoding="utf-8", newline="") as file:
        catalog = {row["area_id"]: row for row in csv.DictReader(file)}

    errors = []
    for area_id, expected in names.items():
        if area_id not in catalog:
            continue
        for column, value in expected.items():
            actual = catalog[area_id].get(column, "")
            if actual != value:
                errors.append(f"{area_id} {column}: {actual!r} != {value!r}")

    listed = [area_id for area_id in catalog if catalog[area_id].get("name_confidence") == "official"]
    print(f"Noms officiels du jeu : {len(names)}")
    print(f"Noms officiels répertoriés dans le catalogue : {len(listed)}")
    if errors:
        print("ERREURS:")
        print("\n".join(errors))
        raise SystemExit(1)
    print("Validation réussie.")


if __name__ == "__main__":
    main()
