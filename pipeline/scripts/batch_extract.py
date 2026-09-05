"""Extract the primary-tile x1 render for every area listed in areas.csv.

Usage (from the project root):
    python pipeline/scripts/batch_extract.py [--night]

--night renders the ARxxxxN night WED instead of the day one, into a
tuiles-principales-nuit/ sibling folder, and is skipped (not a failure) for
any area that has no night WED. Already-rendered areas are skipped, so
re-running this covers only the zones still missing their render.
"""
import csv
import sys
import time
import traceback
from pathlib import Path
from bg2lib import load_key
from area_decode import render_area

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAPS_DIR = PROJECT_ROOT / "maps"
CATALOG = PROJECT_ROOT / "areas.csv"
NIGHT = "--night" in sys.argv
MAPS_DIR.mkdir(parents=True, exist_ok=True)
VARIANT_DIR = "tuiles-principales-nuit" if NIGHT else "tuiles-principales"

with CATALOG.open(encoding="utf-8", newline="") as file:
    areas = [row["area_id"] for row in csv.DictReader(file)]

print(f"Loading chitin.key...")
bif_entries, res_entries = load_key()
wed_names = {name.upper() for name, kind, _locator in res_entries if kind == 0x03E9}
if NIGHT:
    areas = [name for name in areas if f"{name}N" in wed_names]
    print(f"Rendering night variant for {len(areas)}/{len(wed_names)} areas with a night WED...")
else:
    print(f"Rendering {len(areas)} areas...")

failures = []
t_start = time.time()
for i, name in enumerate(areas, 1):
    file_stem = f"{name}N" if NIGHT else name
    out_dir = MAPS_DIR / name / "rendus-x1" / VARIANT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{file_stem}-{VARIANT_DIR.replace('-nuit', '')}-x1.png"
    if out_path.exists():
        print(f"[{i}/{len(areas)}] {name} - already exists, skip")
        continue
    t0 = time.time()
    try:
        img = render_area(bif_entries, res_entries, name, night=NIGHT)
        img.convert("RGB").save(out_path, optimize=True)
        dt = time.time() - t0
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"[{i}/{len(areas)}] {name} -> {img.size} {size_mb:.1f}MB in {dt:.1f}s")
    except Exception as e:
        print(f"[{i}/{len(areas)}] {name} FAILED: {e}")
        traceback.print_exc()
        failures.append((name, str(e)))

total_dt = time.time() - t_start
print(f"\nDone in {total_dt:.1f}s. Failures: {len(failures)}")
for name, err in failures:
    print(f"  {name}: {err}")
