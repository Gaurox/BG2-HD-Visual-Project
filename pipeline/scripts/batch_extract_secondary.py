"""Extract the secondary-tile x1 render for every area listed in areas.csv.

Each output is written to:
    maps/<AREA>/rendus-x1/tuiles-secondaires/<AREA>-tuiles-secondaires-x1.png

Usage (from the project root):
    python pipeline/scripts/batch_extract_secondary.py [--night]

--night renders the ARxxxxN night WED instead of the day one, into a
tuiles-secondaires-nuit/ sibling folder, and is skipped (not a failure) for
any area that has no night WED. Already-rendered areas are skipped, so
re-running this covers only the zones still missing their render.
"""
import csv
import subprocess
import sys
from pathlib import Path

from bg2lib import load_key

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG = PROJECT_ROOT / "areas.csv"
RENDER_SECONDARY = Path(__file__).with_name("render_secondary.py")
NIGHT = "--night" in sys.argv


def main():
    with CATALOG.open(encoding="utf-8", newline="") as file:
        area_ids = [row["area_id"] for row in csv.DictReader(file)]

    if NIGHT:
        _bif, res = load_key()
        wed_names = {name.upper() for name, kind, _locator in res if kind == 0x03E9}
        area_ids = [area_id for area_id in area_ids if f"{area_id}N" in wed_names]
        print(f"{len(area_ids)} areas have a night WED.")

    variant_dir = "tuiles-secondaires-nuit" if NIGHT else "tuiles-secondaires"
    failures = []
    for index, area_id in enumerate(area_ids, 1):
        file_stem = f"{area_id}N" if NIGHT else area_id
        output = (
            PROJECT_ROOT / "maps" / area_id / "rendus-x1" / variant_dir
            / f"{file_stem}-tuiles-secondaires-x1.png"
        )
        if output.exists():
            print(f"[{index}/{len(area_ids)}] {area_id}: already exists, skip")
            continue
        cmd = [sys.executable, str(RENDER_SECONDARY), area_id, str(output)]
        if NIGHT:
            cmd.append("--night")
        result = subprocess.run(cmd)
        if result.returncode:
            failures.append(area_id)
            print(f"[{index}/{len(area_ids)}] {area_id}: FAILED")

    print(f"Done. Failures: {len(failures)}")
    if failures:
        print(" ".join(failures))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
