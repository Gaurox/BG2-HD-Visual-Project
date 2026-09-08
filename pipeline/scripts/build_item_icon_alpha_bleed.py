"""Derive an immutable item-icon batch with RGB edge colors under transparent pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt


ROOT = Path(__file__).resolve().parents[2]
SOURCE_RUN_ID = "item-inventory-xbr2x-aa-v1"
OUTPUT_RUN_ID = "item-inventory-xbr2x-aa-alpha-bleed-v1"
SOURCE_RUN = ROOT / "icons" / "batches" / SOURCE_RUN_ID
OUTPUT_RUN = ROOT / "icons" / "batches" / OUTPUT_RUN_ID
SOURCE_SUFFIX = "xbr2x-aa"
OUTPUT_SUFFIX = "xbr2x-aa-alpha-bleed"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def file_evidence(path: Path, role: str) -> dict[str, object]:
    return {
        "role": role,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def bleed_transparent_rgb(rgba: np.ndarray) -> tuple[np.ndarray, int]:
    alpha = rgba[:, :, 3]
    transparent = alpha == 0
    if not transparent.any():
        return rgba.copy(), 0
    output = rgba.copy()
    if (alpha > 0).any():
        nearest = distance_transform_edt(
            transparent, return_distances=False, return_indices=True
        )
        output[transparent, :3] = rgba[nearest[0][transparent], nearest[1][transparent], :3]
    else:
        output[transparent, :3] = 0
    return output, int(np.count_nonzero(np.any(output[:, :, :3] != rgba[:, :, :3], axis=2)))


def build(*, run: bool) -> dict[str, object]:
    source_manifest_path = SOURCE_RUN / "run.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("result", {}).get("status") != "completed" or not source_manifest.get(
        "result", {}
    ).get("sealed"):
        raise RuntimeError("source xBR2x+AA batch is not completed and sealed")
    source_frames = sorted(
        (SOURCE_RUN / "assets").glob(f"*/frames/frame-*-{SOURCE_SUFFIX}.png")
    )
    expected_frames = int(
        json.loads((SOURCE_RUN / "build-evidence.json").read_text(encoding="utf-8"))[
            "frame_count"
        ]
    )
    if len(source_frames) != expected_frames:
        raise RuntimeError(
            f"source frame count differs from sealed evidence: {len(source_frames)} != {expected_frames}"
        )
    summary: dict[str, object] = {
        "source_run": SOURCE_RUN_ID,
        "output_run": OUTPUT_RUN_ID,
        "asset_count": len({path.parents[1].name for path in source_frames}),
        "frame_count": len(source_frames),
        "transform": "nearest-visible RGB dilation under alpha=0; alpha unchanged",
    }
    if not run:
        return summary
    if OUTPUT_RUN.exists():
        raise FileExistsError(f"refusing to rewrite batch run: {OUTPUT_RUN}")

    recipe = {
        "schema": "bg2-upscale-icon-alpha-bleed-recipe-v1",
        "source_run": SOURCE_RUN_ID,
        "source_frame_suffix": SOURCE_SUFFIX,
        "output_frame_suffix": OUTPUT_SUFFIX,
        "transform": {
            "rgb": "nearest pixel with alpha > 0, Euclidean distance",
            "selection": "alpha == 0 only",
            "alpha": "byte-identical",
            "geometry": "byte-identical",
        },
    }
    OUTPUT_RUN.mkdir(parents=True)
    recipe_path = OUTPUT_RUN / "recipe.json"
    recipe_path.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")

    outputs: list[dict[str, object]] = []
    changed_pixels = 0
    alpha_digest_before = hashlib.sha256()
    alpha_digest_after = hashlib.sha256()
    for source in source_frames:
        relative = source.relative_to(SOURCE_RUN / "assets")
        output_name = source.name.replace(f"-{SOURCE_SUFFIX}.png", f"-{OUTPUT_SUFFIX}.png")
        destination = OUTPUT_RUN / "assets" / relative.parent / output_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            rgba = np.asarray(image.convert("RGBA"))
        corrected, frame_changed = bleed_transparent_rgb(rgba)
        alpha_digest_before.update(rgba[:, :, 3].tobytes())
        alpha_digest_after.update(corrected[:, :, 3].tobytes())
        if not np.array_equal(rgba[:, :, 3], corrected[:, :, 3]):
            raise AssertionError(f"alpha changed for {source}")
        Image.fromarray(corrected, "RGBA").save(destination)
        changed_pixels += frame_changed
        outputs.append(file_evidence(destination, "alpha-bleed-frame"))

    evidence = {
        "schema": "bg2-upscale-icon-alpha-bleed-evidence-v1",
        **summary,
        "changed_transparent_rgb_pixels": changed_pixels,
        "alpha_set_sha256_before": alpha_digest_before.hexdigest().upper(),
        "alpha_set_sha256_after": alpha_digest_after.hexdigest().upper(),
        "alpha_identical": alpha_digest_before.digest() == alpha_digest_after.digest(),
    }
    evidence_path = OUTPUT_RUN / "build-evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    outputs.extend(
        [file_evidence(recipe_path, "recipe"), file_evidence(evidence_path, "build-evidence")]
    )
    now = datetime.now(timezone.utc).isoformat()
    run_manifest = {
        "$schema": "docs/workspace-run.schema.json",
        "schema_version": 1,
        "run_id": OUTPUT_RUN_ID,
        "domain": "icons",
        "asset_ids": source_manifest["asset_ids"],
        "pipeline": {
            "id": "item-icon-alpha-bleed",
            "recipe_path": recipe_path.relative_to(ROOT).as_posix(),
            "recipe_sha256": sha256(recipe_path),
        },
        "inputs": [file_evidence(source_manifest_path, "sealed-xbr2x-aa-run")],
        "outputs": outputs,
        "provenance": {
            "created_at_utc": now,
            "generator": "pipeline/scripts/build_item_icon_alpha_bleed.py",
            "command": ["python", "pipeline/scripts/build_item_icon_alpha_bleed.py", "--run"],
        },
        "result": {
            "status": "completed",
            "sealed": True,
            "completed_at_utc": now,
            "notes": "Derived RGB-only alpha-bleed correction; QA, installation, and release remain separate.",
        },
    }
    run_path = OUTPUT_RUN / "run.json"
    run_path.write_text(json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8")
    return {**summary, "changed_transparent_rgb_pixels": changed_pixels, "run": str(run_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="write the immutable corrected batch")
    args = parser.parse_args()
    result = build(run=args.run)
    print(json.dumps(result, indent=2))
    if not args.run:
        print("Plan only; add --run to write the corrected batch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
