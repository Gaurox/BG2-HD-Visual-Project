#!/usr/bin/env python3
"""CONTOUR-NET : contour net et fin pour une animation de zone rigide à liseré sombre.

Recette (catalogue `animations/ANIMATION_RECIPE_CATALOG.md`, modèle `CONTOUR-NET`) :
alpha x4 = vectorisation Potrace du masque x1 (arêtes droites, angles vifs) ; RGB du liseré
sombre de la source et des pixels gagnés = moyenne gaussienne normalisée de l'intérieur ;
puis Apollo-8 15→30 depuis le pack corrigé, découpe par zone et reconstruction de chaque
zone servie à partir du verrou (`area-pack-lock.json`), la ressource traitée remplacée et les
autres conservées octet pour octet. N'installe rien : affiche les commandes AreaTest.

Exemple validé : AM5000A/AM5000B (AR5000), 2026-09-23.

    python pipeline/scripts/contour_net.py --spatial-run animations/batches/<run-seedvr> --resref AM5000A --resref AM5000B --tag ar5000-am5000ab
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

import animation_paths  # noqa: E402

PACKS_ROOT = PROJECT_ROOT / "animations" / "packs-par-zone"
LOCK_PATH = PROJECT_ROOT / "animations" / "index" / "area-pack-lock.json"
OCCURRENCES_PATH = PROJECT_ROOT / "animations" / "index" / "occurrences.csv"
BLENDED_FLAG = 0x2


def fail(message: str) -> None:
    raise SystemExit(f"CONTOUR-NET : {message}")


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def run_script(name: str, *arguments: str) -> str:
    command = [sys.executable, str(SCRIPT_DIR / name), *arguments]
    print("> " + " ".join(command[1:]), flush=True)
    result = subprocess.run(
        command, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8",
        errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if result.returncode != 0:
        fail(f"{name} a échoué :\n{result.stdout[-2000:]}\n{result.stderr[-4000:]}")
    return result.stdout


def json_from_output(output: str) -> dict:
    start = output.find("{")
    if start < 0:
        fail("sortie JSON attendue absente")
    return json.loads(output[start:])


def blended_resrefs(resrefs: list[str]) -> list[str]:
    found = set()
    with OCCURRENCES_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["resource_resref"].upper() in resrefs and int(row["flags_hex"], 16) & BLENDED_FLAG:
                found.add(row["resource_resref"].upper())
    return sorted(found)


def pack_resources(pack: Path) -> list[dict]:
    manifest = pack / "manifest.json"
    if not manifest.is_file():
        fail(f"manifest de pack absent : {rel(pack)}")
    return json.loads(manifest.read_text(encoding="utf-8-sig"))["resources"]


def zone_sources(area: str, entry: dict, treated: set[str]) -> tuple[list[str], set[str]]:
    """Return the lock's selectors for ``area`` without the treated resrefs."""
    build = entry.get("build") or {}
    selectors = list(build.get("merged_from") or [])
    if "leaf" in build:
        selectors = [build["leaf"]]
    kept: list[str] = []
    replaced: set[str] = set()
    for selector in selectors:
        parts = selector.split("::")
        path = PROJECT_ROOT / parts[0]
        if len(parts) == 1:
            resources = pack_resources(path)
            names = [str(item["resref"]).upper() for item in resources]
            if not treated & set(names):
                kept.append(selector)
                continue
            for item in resources:
                name = str(item["resref"]).upper()
                if item.get("position") is not None or int(item.get("variant_index") or 0) > 0 or names.count(name) > 1:
                    fail(f"{area} : {selector} porte des variantes liées ; fusion manuelle requise")
                if name in treated:
                    replaced.add(name)
                else:
                    kept.append(f"{parts[0]}::{name}")
            continue
        if len(parts) == 2 and "," in parts[1]:
            names = {str(item["resref"]).upper() for item in pack_resources(path)}
            if names & treated:
                fail(f"{area} : {selector} lie une ressource traitée à une position ; fusion manuelle requise")
            kept.append(selector)
            continue
        name = parts[1].upper()
        if name not in treated:
            kept.append(selector)
        elif len(parts) == 3:
            fail(f"{area} : {selector} lie une ressource traitée à une position ; fusion manuelle requise")
        else:
            replaced.add(name)
    return kept, replaced


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spatial-run", required=True, help="run spatial x4 (étage 02_upscale_x4, alpha nearest)")
    parser.add_argument("--resref", action="append", required=True, help="répétable")
    parser.add_argument("--tag", required=True, help="préfixe des runs et packs produits, ex. ar5000-am5000ab")
    parser.add_argument("--alphamax", type=float, default=0.8, help="0.8 garde les angles vifs ; 1.0 arrondit")
    parser.add_argument("--fill-depth-x4", type=float, default=6.0, help="largeur du liseré remplacé")
    parser.add_argument("--fill-sigma-x4", type=float, default=2.5)
    parser.add_argument("--preserve-segmented-holds", action="store_true", help="transmis à Apollo-8")
    parser.add_argument("--collapse-uniform-duplicate-holds", action="store_true", help="transmis à Apollo-8")
    parser.add_argument("--allow-blended", action="store_true", help="recette conçue pour des ressources non Blended")
    parser.add_argument("--skip-zones", action="store_true", help="s'arrêter au pack découpé par zone")
    args = parser.parse_args()

    resrefs = sorted({value.upper() for value in args.resref})
    tag = animation_paths.validate_run_id(args.tag)
    blended = blended_resrefs(resrefs)
    if blended and not args.allow_blended:
        fail(f"ressources Blended ({', '.join(blended)}) : le RGB y est additif, utiliser une recette prémultipliée")
    spatial = animation_paths.resolve_existing_run(args.spatial_run, resrefs)
    if not (spatial / "03_runtime_pack" / "manifest.json").is_file():
        fail(f"pack runtime primaire absent : {rel(spatial)}/03_runtime_pack")

    overrides = []
    for resref in resrefs:
        run_script(
            "build_spatial_spline_alpha.py", "--resref", resref, "--run", str(spatial),
            "--output-run", f"{tag}-contour-net-x4",
            "--potrace-alphamax", str(args.alphamax),
            "--edge-rgb-fill-depth-x4", str(args.fill_depth_x4),
            "--edge-rgb-fill-sigma-x4", str(args.fill_sigma_x4),
        )
        overrides += ["--alpha-override-manifest", str(
            animation_paths.resolve_existing_run(f"{tag}-contour-net-x4", [resref]) / "manifest.json"
        )]

    composed = spatial / f"03_runtime_pack_contour_net_{tag}"
    run_script("build_animation_runtime_pack.py", str(spatial), str(composed), *overrides)

    timed_run = f"{tag}-contour-net-apo8-x4-30fps-v2"
    timing = ["--base-runtime-only", "--base-pack", str(composed), "--transparent-rgb-mode", "nearest-opaque-dilate"]
    for resref in resrefs:
        timing += ["--resref", resref]
    if args.preserve_segmented_holds:
        timing.append("--preserve-segmented-holds")
    if args.collapse_uniform_duplicate_holds:
        timing.append("--collapse-uniform-duplicate-holds")
    plan = json_from_output(run_script("run_animation_upscale_30fps_v2.py", "plan", *timing, "--run", timed_run))
    run_script(
        "run_animation_upscale_30fps_v2.py", "build", *timing, "--run", timed_run,
        "--approve-plan-sha256", plan["plan_sha256"],
    )
    timed = animation_paths.resolve_existing_run(timed_run, resrefs)

    split = PACKS_ROOT / timed_run
    index = json_from_output(run_script(
        "split_animation_pack_by_area.py", "--pack", str(timed / "03_runtime_pack"), "--output", str(split),
    ))
    if index.get("areas_over_budget"):
        fail(f"zones hors budget : {index['areas_over_budget']}")
    print(f"\nPack découpé (témoin finalize --qa-pack) : {rel(split)}")
    print(f"Run final (finalize --final-run)         : {rel(timed)}")
    if args.skip_zones:
        return

    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))["areas"]
    treated = set(resrefs)
    installs: list[str] = []
    for area_dir in sorted(path for path in split.iterdir() if path.is_dir()):
        area = area_dir.name
        present = {str(item["resref"]).upper() for item in pack_resources(area_dir)} & treated
        kept, _ = zone_sources(area, lock[area], treated) if area in lock else ([], set())
        selectors = kept + [f"{rel(area_dir)}::{name}" for name in sorted(present)]
        output = PACKS_ROOT / f"{tag}-contour-net-zone-{area.lower()}"
        merge = ["merge_area_pack_resources.py", "--area", area, "--output", str(output)]
        for selector in selectors:
            merge += ["--pack", selector]
        run_script(*merge)
        expected = set(lock[area]["resources"]) | present if area in lock else present
        built = {str(item["resref"]).upper() for item in pack_resources(output / area)}
        if built != {name.upper() for name in expected}:
            fail(f"{area} : ressources {sorted(built)} au lieu de {sorted(expected)}")
        installs.append(
            f'powershell -File pipeline/scripts/Install-AreaAnimation-AreaTest.ps1 -AreaPack "{rel(output / area)}"'
        )

    print("\nZones reconstruites (jeu et InfinityLoader fermés avant installation) :")
    for command in installs:
        print("  " + command)


if __name__ == "__main__":
    main()
