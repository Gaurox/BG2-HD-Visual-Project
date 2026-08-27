"""Integrate one zone's build into <game>\\override, per pipeline/README.md step 6.

- backs up any currently-active override files with the same names before touching them
  (backups/maps/<RESREF>-<timestamp>/), even if that means an empty backup dir (nothing active yet)
- copies only *.TIS and *.PVRZ from the build dir (never the QA thumbnail)
- never touches anything not produced by this build (so shared overlays like WTLAKE.TIS
  are structurally never at risk: build_upscaled_area.py only ever emits <RESREF>.TIS +
  its own <prefix>NN.PVRZ pages)
- verifies SHA-256 build <-> override after copy, 0 divergence required

Usage:
    python pipeline/scripts/inject_build.py AR2015 maps/AR2015/runs/<run>/05_build
    python pipeline/scripts/inject_build.py AR2000N maps/AR2000/runs/<run>/05_build
"""
from __future__ import annotations

import hashlib
import shutil
import sys
import time
from pathlib import Path

GAME_DIR = Path(r"G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition")
OVERRIDE = GAME_DIR / "override"
PROJECT = Path(__file__).resolve().parent.parent.parent
BACKUP_ROOT = PROJECT / "backups" / "maps"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: inject_build.py RESREF BUILD_DIR")
    resref = sys.argv[1].upper()
    build_dir = Path(sys.argv[2])
    if not build_dir.is_dir():
        raise SystemExit(f"build dir introuvable: {build_dir}")

    build_files = sorted(
        p for p in build_dir.iterdir()
        if p.is_file() and p.suffix.upper() in (".TIS", ".PVRZ")
    )
    if not build_files:
        raise SystemExit(f"aucun .TIS/.PVRZ dans {build_dir}")

    ts = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUP_ROOT / f"{resref}-{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backed_up = []
    for src in build_files:
        dest = OVERRIDE / src.name
        if dest.exists():
            shutil.copy2(dest, backup_dir / src.name)
            backed_up.append(src.name)

    for src in build_files:
        shutil.copy2(src, OVERRIDE / src.name)

    mismatches = []
    for src in build_files:
        dest = OVERRIDE / src.name
        if sha256(src) != sha256(dest):
            mismatches.append(src.name)

    print(f"RESREF: {resref}")
    print(f"build_dir: {build_dir}")
    print(f"fichiers copies: {len(build_files)}")
    print(f"actifs sauvegardes avant ecrasement: {len(backed_up)} -> {backup_dir}")
    if backed_up:
        for n in backed_up:
            print(f"  - {n}")
    print(f"divergence SHA-256 build<->override: {len(mismatches)}")
    if mismatches:
        print("MISMATCHES:", mismatches)
        raise SystemExit(1)
    print("OK")


if __name__ == "__main__":
    main()
