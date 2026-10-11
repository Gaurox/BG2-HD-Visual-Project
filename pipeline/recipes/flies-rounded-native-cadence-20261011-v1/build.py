"""Prepare FLIESL/FLIESS packs only; never install or change QA/release authorities."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[3]
RECIPE = Path(__file__).resolve().parent
SCRIPTS = ROOT / "pipeline/scripts"
sys.path.insert(0, str(SCRIPTS))

import build_animation_runtime_pack as v1
import run_animation_upscale_30fps_v2 as v2
import split_animation_pack_by_area as split
from area_pack_state import leaf_signatures, recipe_signatures, zone_fingerprint, zone_signatures
from export_bam_frames import cycle_metadata, read_bam
from bam_export import decode_bam
from merge_area_pack_resources import merge
from workspace_paths import get_path

RUN_ID = "flies-rounded-native-cadence-20261011-v1"
RUN = ROOT / "animations/batches" / RUN_ID
TARGETS = {"FLIESL", "FLIESS"}


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    v2.write_json(path, payload)


def ellipse_alpha(mask: np.ndarray) -> Image.Image:
    """Same algorithm as the accentuated preview: area-matched component ellipses."""
    labels, count = ndi.label(mask, structure=np.ones((3, 3)))
    h, w = mask.shape
    ss, factor = 16, 64
    high = np.zeros((h * factor, w * factor), np.uint8)
    for component in range(1, count + 1):
        ys, xs = np.nonzero(labels == component)
        centre = np.array([xs.mean() + 0.5, ys.mean() + 0.5]) * 4
        points = np.stack([xs + 0.5, ys + 0.5], 1)
        centred = points - points.mean(0)
        covariance = centred.T @ centred / len(xs) + np.eye(2) / 12
        vals, vecs = np.linalg.eigh(covariance)
        aspect = min(1.6, float(np.sqrt(vals[1] / vals[0])))
        area = len(xs) * 16
        a, b = np.sqrt(area * aspect / np.pi), np.sqrt(area / aspect / np.pi)
        major, minor = vecs[:, 1], vecs[:, 0]
        bound = int(np.ceil(a * ss)) + 2
        mx, my = centre * ss
        x0, x1 = max(0, int(mx) - bound), min(w * factor, int(mx) + bound + 1)
        y0, y1 = max(0, int(my) - bound), min(h * factor, int(my) + bound + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx, dy = (xx + 0.5) / ss - centre[0], (yy + 0.5) / ss - centre[1]
        along, across = dx * major[0] + dy * major[1], dx * minor[0] + dy * minor[1]
        inside = (along / a) ** 2 + (across / b) ** 2 <= 1
        high[y0:y1, x0:x1] = np.maximum(high[y0:y1, x0:x1], inside.astype(np.uint8) * 255)
    return Image.fromarray(high, "L").resize((w * 4, h * 4), Image.Resampling.BOX)


def smooth_alpha(mask: np.ndarray) -> Image.Image:
    """Same opening/antialiasing as the initial FLIESS preview."""
    radius = 10  # 1.25 pixels x4, sampled at x8.
    yy, xx = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    disk = xx * xx + yy * yy <= radius * radius
    high = np.repeat(np.repeat(mask, 32, 0), 32, 1)
    rounded = ndi.binary_opening(high, structure=disk)
    h, w = mask.shape
    return Image.fromarray(rounded.astype(np.uint8) * 255, "L").resize(
        (w * 4, h * 4), Image.Resampling.LANCZOS
    )


def rounded_frame(indices: np.ndarray, palette: np.ndarray, transparent: int,
                  resref: str) -> np.ndarray:
    # Pad only while processing; crop back to the exact original BAM frame geometry.
    mask = np.pad(indices != transparent, 2)
    colours = np.pad(palette[indices], ((2, 2), (2, 2), (0, 0)))
    if mask.any():
        nearest = ndi.distance_transform_edt(~mask, return_distances=False, return_indices=True)
        colours = colours[tuple(nearest)]
    alpha = ellipse_alpha(mask) if resref == "FLIESL" else smooth_alpha(mask)
    image = Image.fromarray(colours, "RGB").resize(alpha.size, Image.Resampling.NEAREST).convert("RGBA")
    image.putalpha(alpha)
    w, h = indices.shape[1] * 4, indices.shape[0] * 4
    return np.asarray(image)[8:8 + h, 8:8 + w].copy()


def build_assets(occurrences: list[dict]) -> None:
    if RUN.exists():
        raise RuntimeError(f"Immutable output already exists: {relative(RUN)}")
    RUN.mkdir(parents=True)
    inventory = {r["bam_resref"]: r for r in csv.DictReader(
        (ROOT / "animations/index/ressources.csv").open(encoding="utf-8")
    )}
    records, checks = [], []
    for resref in sorted(TARGETS):
        resource = RUN / "resources" / resref
        source = ROOT / "animations/ressources" / resref / "source.bam"
        assert v2.sha256_file(source).lower() == inventory[resref]["sha256"].lower()
        resource.mkdir(parents=True)
        shutil.copyfile(source, resource / "source.bam")
        exported = resource / "01_frames_x1"
        subprocess.run([sys.executable, str(SCRIPTS / "export_bam_frames.py"),
                        str(resource / "source.bam"), str(exported)], check=True, cwd=ROOT)
        fm = v2.load_json(exported / "manifest.json")
        data = read_bam(source)
        frames, palette, transparent = decode_bam(data)
        stage = resource / "02_rounded_x4"
        for sub in ("rgba", "rgb", "alpha", "raw_rgba"):
            (stage / sub).mkdir(parents=True)
        outputs = []
        for index, (indices, cx, cy, frame_transparent) in enumerate(frames):
            rgba = rounded_frame(indices, palette, frame_transparent, resref)
            h, w = indices.shape
            assert rgba.shape == (h * 4, w * 4, 4)
            name = f"frame_{index:03d}.png"
            Image.fromarray(rgba, "RGBA").save(stage / "rgba" / name)
            Image.fromarray(rgba[:, :, :3], "RGB").save(stage / "rgb" / name)
            Image.fromarray(rgba[:, :, 3], "L").save(stage / "alpha" / name)
            raw = stage / "raw_rgba" / f"frame_{index:03d}.rgba"
            raw.write_bytes(rgba.tobytes())
            outputs.append({"frame": index, "logical_size_x1": [w, h],
                            "physical_size_xn": [w * 4, h * 4], "centre_x1": [cx, cy],
                            "rgba_xn": f"rgba/{name}", "alpha_xn": f"alpha/{name}",
                            "rgb_xn": f"rgb/{name}", "raw_rgba_xn": f"raw_rgba/{raw.name}",
                            "raw_rgba_xn_sha256": v2.sha256_file(raw)})
            before = int((indices != frame_transparent).sum()) * 16 * 255
            checks.append({"resref": resref, "frame": index, "size_x1": [w, h],
                           "centre_x1": [cx, cy], "opaque_area_change_percent":
                           round(100 * (int(rgba[:, :, 3].sum()) / before - 1), 4)})
            if index in (0, 9):
                # Reference previews use a common centre-aligned canvas with a two-pixel margin.
                selected = [frames[i] for i in (0, 9)]
                left = min(-f[1] for f in selected) - 2
                top = min(-f[2] for f in selected) - 2
                reference = Image.open(RECIPE / "reference-previews" / f"{resref}-{index:03d}.png")
                ox, oy = (-cx - left) * 4, (-cy - top) * 4
                expected = np.asarray(reference.crop((ox, oy, ox + w * 4, oy + h * 4)))
                assert np.array_equal(rgba, expected), f"Preview mismatch: {resref}/{index}"
        write(stage / "manifest.json", {
            "schema": v1.UPSCALE_SCHEMA, "status": "completed", "scale": 4,
            "created_utc": v2.utc_now(), "source_frame_manifest_sha256": v2.sha256_file(exported / "manifest.json"),
            "recipe": "area-matched-component-ellipses" if resref == "FLIESL" else "rounded-opening-radius1p25-x4",
            "geometry_mode": fm["geometry_mode"], "raw_rgba_layout": "RGBA8 tightly packed top-to-bottom",
            "rgb_policy": "straight source palette; nearest opaque colour under antialiased edges",
            "parameters": {"scale": 4, "native_cadence": True,
                           "supersampling": 16 if resref == "FLIESL" else 8,
                           "max_ellipse_aspect": 1.6 if resref == "FLIESL" else None,
                           "corner_radius_x4": 1.25 if resref == "FLIESS" else None},
            "frames": outputs,
        })
        assert fm["cycles"] == cycle_metadata(data, len(frames))
        records.append({"resref": resref, "status": "completed", "source_sha256": v2.sha256_file(source),
                        "canonical_source": relative(source), "source_bam": relative(resource / "source.bam"),
                        "frames_x1": exported.relative_to(RUN).as_posix(),
                        "upscale": stage.relative_to(RUN).as_posix(), "frame_count": len(frames),
                        "frame_manifest_sha256": v2.sha256_file(exported / "manifest.json"),
                        "upscale_manifest_sha256": v2.sha256_file(stage / "manifest.json")})
    write(RUN / "manifest.json", {
        "schema": v1.RUN_SCHEMA, "status": "completed", "run": RUN_ID,
        "created_utc": v2.utc_now(), "request": {"scale": 4, "resrefs": sorted(TARGETS), "native_cadence": True},
        "recipe_script": relative(Path(__file__)), "recipe_sha256": v2.sha256_file(Path(__file__)),
        "qa_status": "png-preview-accepted-ingame-pending", "installation_status": "deferred-by-user",
        "release_status": "not-selected", "occurrences": occurrences, "resources": records,
    })
    write(RUN / "local-checks.json", {"source_geometry_cycles_preserved": True,
                                      "four_preview_crops_byte_identical": True, "frames": checks})
    subprocess.run([sys.executable, str(SCRIPTS / "build_animation_runtime_pack.py"), str(RUN)],
                   check=True, cwd=ROOT)


def prepare(occurrences: list[dict], composition_version: str) -> None:
    # Recomposition after other work must create a new immutable version, never overwrite v1.
    assert composition_version.isalnum(), "Use an alphanumeric version such as v1 or v2"
    split_root = ROOT / "animations/packs-par-zone" / RUN_ID
    if not split_root.exists():
        split.split(RUN / "03_runtime_pack", split_root, ROOT / "animations/index/occurrences.csv", False)
    complete = ROOT / "animations/packs-par-zone" / f"{RUN_ID}-complete-{composition_version}"
    if complete.exists():
        raise RuntimeError(f"Immutable composition already exists: {relative(complete)}")
    areas = sorted({r["area_id"] for r in occurrences})
    lock_path = ROOT / "animations/index/area-pack-lock.json"
    lock = v2.load_json(lock_path)
    game_areas = get_path("bg2ee_game_root", required=True) / "iee-assets/areas"
    baseline, entries = {}, []
    for area in areas:
        entry = lock["areas"].get(area)
        game_dir = game_areas / area
        if entry:
            expected = {k: v["sig"] for k, v in entry["resources"].items()}
            assert recipe_signatures(entry) == expected, f"Lock recipe diverged: {area}"
            assert game_dir.is_dir(), f"Locked zone missing in game: {area}"
            assert {k: v["sig"] for k, v in zone_signatures(game_dir).items()} == expected, area
            specs = [entry["build"]["leaf"]] if "leaf" in entry["build"] else list(entry["build"]["merged_from"])
            assert not any(k.split("-v")[0] in TARGETS for k in expected), area
        else:
            assert not game_dir.exists(), f"Untracked installed zone: {area}"
            expected, specs = {}, []
        baseline[area] = {"lock_entry": entry, "installed_resource_signatures": expected,
                          "installed_fingerprint": zone_fingerprint(game_dir) if game_dir.exists() else None,
                          "installed_registry_sha256": v2.sha256_file(game_dir / v2.REGISTRY_NAME) if game_dir.exists() else None}
        index = merge([*specs, relative(split_root / area)], area, complete / area.lower(), False)
        leaf = complete / area.lower() / area
        after = leaf_signatures(leaf)
        preserved = {k: v["sig"] for k, v in after.items() if k.split("-v")[0] not in TARGETS}
        assert preserved == expected, f"Existing animations changed: {area}"
        new_refs = {r["resource_resref"] for r in occurrences if r["area_id"] == area}
        assert {k.split("-v")[0] for k in after} == {k.split("-v")[0] for k in expected} | new_refs
        result_entry = index["areas"][0]
        result_entry["directory"] = f"{area.lower()}/{area}"
        entries.append(result_entry)
        print(f"Prepared {area}: preserved {len(expected)} resources + {','.join(sorted(new_refs))}", flush=True)
    for area, snapshot in baseline.items():
        directory = game_areas / area
        assert (zone_fingerprint(directory) if directory.exists() else None) == snapshot["installed_fingerprint"], area
    assert v2.load_json(lock_path) == lock, "Installation lock changed during preparation"
    total = sum(e["raw_bytes"] for e in entries)
    largest = max(e["raw_bytes"] for e in entries)
    write(complete / "manifest.json", {
        "schema": split.INDEX_SCHEMA, "status": "completed", "created_utc": v2.utc_now(),
        "area_count": len(entries), "areas": entries, "total_raw_bytes": total,
        "largest_area_raw_bytes": largest, "runtime_budget_bytes": v2.MAX_RAW_BYTES,
        "areas_over_budget": [], "resrefs_without_area": [], "usage": "targeted-area-installer-only",
    })
    assert largest <= v2.MAX_RAW_BYTES
    core_path = ROOT / "pipeline/area-animation-area-test/area_animation_area_test.py"
    spec = importlib.util.spec_from_file_location("flies_area_test_validation", core_path)
    core = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = core
    spec.loader.exec_module(core)
    for entry in entries:
        core.validate_area_pack(complete / entry["directory"])
    record = {
        "schema": "bg2-upscale-flies-preparation-v1", "status": "prepared-not-installed",
        "created_utc": v2.utc_now(), "production_run": relative(RUN),
        "complete_split_root": relative(complete), "complete_manifest_sha256": v2.sha256_file(complete / "manifest.json"),
        "area_count": len(areas), "occurrence_count": len(occurrences), "source_frame_count": 36,
        "native_cadence_preserved": True, "existing_resources_byte_identical": True,
        "area_installer_pack_validation": "passed-for-all-21-leaves",
        "installation": {"status": "deferred-by-user", "must_wait_for": "User confirms parallel DLL work finished and committed",
                         "before_install": "Compare relevant lock entries and installed signatures to this baseline; recompose a new version if changed; close game and InfinityLoader; run targeted installer VerifyOnly",
                         "installer": "pipeline/scripts/Install-AreaAnimation-AreaTest.ps1",
                         "do_not_use": "Install-AreaAnimations-PerArea.ps1: split-root covers only 21 affected zones"},
        "qa": "PNG previews accepted; ingame QA pending; native selections unchanged",
        "release": "not-selected", "baseline_lock_sha256": v2.sha256_file(lock_path),
        "largest_area_raw_bytes": largest, "total_raw_bytes": total, "areas": baseline,
    }
    write(RECIPE / f"preparation-{composition_version}.json", record)
    print(json.dumps({k: record[k] for k in ("status", "area_count", "occurrence_count", "complete_split_root", "largest_area_raw_bytes")}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-only", action="store_true")
    parser.add_argument("--composition-version", default="v1")
    args = parser.parse_args()
    occurrences = [r for r in csv.DictReader((ROOT / "animations/index/occurrences.csv").open(encoding="utf-8"))
                   if r["resource_resref"] in TARGETS]
    assert len(occurrences) == 216
    assert all(r["resource_kind"] == "BAM" and r["palette_mode"] == "embedded"
               and not (int(r["flags_hex"], 16) & 2) for r in occurrences), "Unexpected Blended/external-palette use"
    if not args.compose_only:
        build_assets(occurrences)
    prepare(occurrences, args.composition_version)


if __name__ == "__main__":
    main()
