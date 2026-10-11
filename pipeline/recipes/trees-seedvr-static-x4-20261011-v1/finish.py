"""Finish the five fresh SeedVR trees; preserve native geometry and installed fountains."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import build_animation_runtime_pack as v1
import run_animation_upscale_30fps_v2 as v2
import build_spatial_spline_alpha as contour
import split_animation_pack_by_area as splitter
import build_area_lightmap_pack as lighting
import merge_area_pack_resources as merger
import area_pack_state as state
from workspace_paths import get_path

RUN = ROOT / "animations/batches/trees-seedvr-static-x4-20261011-v1"
REFS = {f"1400T{i:03}" for i in range(1, 6)}
BASELINE = ROOT / "animations/packs-par-zone/combined-20260904-fpit1s-contour-fondu-J/AR1400"


def relative(path):
    return path.relative_to(ROOT).as_posix()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def protected_alpha(source, band):
    mask = source > 127
    native = mask[::4, ::4]
    distance = ndimage.distance_transform_edt(np.pad(native, 1))[1:-1, 1:-1]
    core = distance > 1.5
    near_core = ndimage.distance_transform_edt(~core) <= 1.5
    thin = native & ~near_core
    protected = ndimage.binary_dilation(thin, iterations=1).repeat(4, 0).repeat(4, 1)
    protected[:2] = protected[-2:] = True
    protected[:, :2] = protected[:, -2:] = True
    alpha, report = contour.potrace_alpha(source, threshold=127, alphamax=.8,
        opttolerance=.1, supersample=8, band=band)
    # Inward antialiasing only: retain every twig, native hole and runtime support.
    alpha = np.where(mask, np.maximum(alpha, 176), 0).astype(np.uint8)
    alpha[protected] = source[protected]
    assert np.array_equal(alpha > 127, mask)
    report.update(support_exact=True, thin_native_pixels=int(thin.sum()),
        changed_pixels=int(np.count_nonzero(alpha != source)), minimum_inside_alpha=176,
        outside_growth_pixels=0, effective_coverage_ratio=float(alpha.sum()/source.sum()))
    return alpha, report


def board(items, path):
    size = 340
    out = Image.new("RGB", (size * 3, (size + 30) * 2), (30, 30, 30))
    draw = ImageDraw.Draw(out)
    for n, (label, rgba) in enumerate(items):
        x, y = (n % 3) * size, (n // 3) * (size + 30)
        yy, xx = np.indices((size, size))
        c = np.where(((xx//20 + yy//20) % 2)[..., None], 75, 95)
        background = Image.fromarray(np.repeat(c, 3, axis=2).astype(np.uint8)).convert("RGBA")
        image = Image.fromarray(rgba).resize((size, size), Image.Resampling.LANCZOS)
        background.alpha_composite(image)
        out.paste(background.convert("RGB"), (x, y+30))
        draw.text((x+8, y+8), label, fill="white")
    out.save(path)


def main():
    assert not (HERE / "preparation.json").exists(), "Do not rewrite a sealed preparation"
    game = get_path("bg2ee_game_root", required=True)
    areas = game / "iee-assets/areas"
    lock = state.load_lock()
    baseline = {}
    for area in ("AR1400", "AR1404"):
        signatures = state.zone_signatures(areas / area) if (areas / area).exists() else {}
        baseline[area] = {"signatures": signatures, "lock_entry": lock["areas"].get(area),
            "registry_sha256": v2.sha256_file(areas/area/v2.REGISTRY_NAME) if signatures else None}
    assert baseline["AR1400"]["signatures"] == state.leaf_signatures(BASELINE)
    assert not baseline["AR1404"]["signatures"], "Recompose existing AR1404 resources"
    primary = RUN / "03_runtime_pack"
    v1.validate_pack_contents(primary)
    overrides, reports, images = [], {}, []
    for ref in sorted(REFS):
        name = f"AAX4-{ref}-frame000.rgba"
        rgba = np.fromfile(primary / name, dtype=np.uint8).reshape(1020, 1020, 4).copy()
        alpha = rgba[..., 3].copy()
        assert np.array_equal(alpha, alpha[::4, ::4].repeat(4,0).repeat(4,1))
        folder = RUN / "04_alpha" / ref
        folder.mkdir(parents=True, exist_ok=False)
        if ref in {"1400T001", "1400T003", "1400T005"}:
            for band in (1, 2):
                candidate, report = protected_alpha(alpha, band)
                Image.fromarray(candidate).save(folder / f"alpha-band{band}.png")
                candidate_rgba = rgba.copy()
                candidate_rgba[...,3] = candidate
                Image.fromarray(candidate_rgba).save(folder / f"rgba-band{band}.png")
                if band == 2:
                    rgba = candidate_rgba
                    reports[ref] = report
        else:
            reports[ref] = {"mode":"native-nearest", "changed_pixels":0, "support_exact":True}
        rgba[rgba[...,3] == 0, :3] = 0
        rgba.tofile(folder / name)
        Image.fromarray(rgba).save(folder / "finished.png")
        images.append((ref, rgba))
        manifest = folder / "manifest.json"
        write(manifest, {"schema":"bg2-upscale-animation-alpha-feather-test-v1",
            "status":"completed", "scale":4, "resref":ref, "alpha":reports[ref],
            "source_pack_sha256":v2.sha256_file(primary/"manifest.json"),
            "frames":[{"frame":0,"runtime_asset":name,
                "runtime_sha256":v2.sha256_file(folder/name),"runtime_bytes":(folder/name).stat().st_size}]})
        overrides.append(manifest)
    board(images, RUN / "04_alpha/preview.png")
    resources, sources, provenance, override_provenance = v1.compose_runtime_packs([primary], overrides)
    finished = RUN / "05_finished_runtime_pack"
    finished.mkdir()
    v1.write_composed_pack(finished, resources, sources, provenance, override_provenance)
    occurrences = ROOT / "animations/index/occurrences.csv"
    split = RUN / "06_split"
    splitter.split(finished, split, occurrences, False)
    relit = RUN / "07_lit_split"
    lighting.build(split, relit, REFS, {"AR1400":"AR1400LM", "AR1404":"AR1404LM"}, occurrences, False)
    leaves = {}
    for area in ("AR1400", "AR1404"):
        specs = [str(relit/area)]
        if area == "AR1400":
            specs.insert(0, str(BASELINE))
        complete = ROOT / f"animations/packs-par-zone/trees-seedvr-static-x4-20261011-v1-{area.lower()}"
        merger.merge(specs, area, complete, False)
        leaf = complete/area
        signatures = state.leaf_signatures(leaf)
        assert {k:v for k,v in signatures.items() if k not in REFS} == baseline[area]["signatures"]
        leaves[area] = relative(leaf)
        manifest = v2.load_json(leaf/"manifest.json")
        preview_items = []
        for resource in manifest["resources"]:
            if resource["resref"] in REFS:
                frame = resource["frames"][0]
                raw = np.fromfile(leaf/frame["asset"],dtype=np.uint8).reshape(1020,1020,4)
                preview_items.append((resource["resref"]+" "+area, raw))
        board(preview_items, RUN / f"preview-{area}.png")
    write(HERE/"preparation.json", {"schema":"bg2-upscale-trees-preparation-v1", "status":"completed",
        "created_utc":v2.utc_now(), "production_run":relative(RUN), "leaves":leaves,
        "leaf_manifest_sha256":{a:v2.sha256_file(ROOT/p/"manifest.json") for a,p in leaves.items()},
        "baseline":baseline,"alpha":reports,"upscaler":"SeedVR2 7B INT8 LAB x4",
        "seed":20261011,"native_geometry_cycles_preserved":True,"rgb_edge_fill":False,
        "lighting":{"AR1400":"AR1400LM day baked","AR1404":"AR1404LM permanent night baked"},
        "limitation":"AR1400 night lighting needs a renderer fix; no dynamic lighting in this test",
        "qa_status":"pending-user-ingame-test","release_status":"not-selected"})
    print("Prepared five trees and two complete area packs; fountains unchanged.")


if __name__ == "__main__":
    main()
