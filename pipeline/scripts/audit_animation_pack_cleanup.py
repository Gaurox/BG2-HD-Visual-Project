"""Capture and verify the targeted P3 cleanup of per-area animation packs.

The generated JSON is a cleanup receipt, not an animation status authority.  It
records the pre-cleanup physical inventory and validates the deliberately small
set of active packs and archived historical slices after cleanup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
PACK_ROOT = ROOT / "animations/packs-par-zone"
ARCHIVE_ROOT = ROOT / "archive/legacy/animation-packs-p3-20260831"
RECEIPT = ROOT / "docs/workspace-animation-packs-p3-manifest.json"
POST_P3_RETENTION = ROOT / "animations/index/post-p3-pack-retention-20260902.json"

KEEP_ACTIVE: dict[str, str] = {
    "ar0700-fire-rgb-neutral-20260827": (
        "canonical alpha-correction output cited by animation_alpha_corrections.csv"
    ),
    "combined-20260827-ar0900-plus-ar0516-sphinct-spline-fit1": (
        "release candidate source for AR0516"
    ),
    "combined-20260827-ar0900-two-manual-masks-v3": (
        "release candidate source for AR0900"
    ),
    "combined-20260827-plus-flame2s-ar0602-radialA": (
        "release candidate source for AR0700 and retained base for AR0602"
    ),
    "combined-20260828-ar0603-portal-spline-feather8": (
        "release candidate source for AR0602 and AR0603"
    ),
    "combined-20260828-plus-ar1400-fountains-only": (
        "latest validated installed per-area lot, including AR1400 fountains"
    ),
    "combined-20260831-ar0307-ar0329-six-bam-x4": (
        "validated x4 spatial baseline retained with its reversible installation evidence"
    ),
    "combined-20260831-ar0307-ar0329-six-bam-30fps-v2": (
        "approved release-candidate source for AR0307 and AR0329"
    ),
}

# These roots were produced after the 2026-08-31 P3 cleanup.  They remain on
# disk as immutable processing/install evidence; the historical P3 receipt is
# deliberately not rewritten to make them look like pre-cleanup inputs.
POST_P3_RETAINED: dict[str, str] = {
    "ar2100-portals-apo8-x4-30fps-v2-split": "AR2100 portal V2 per-area source retained for reversible delivery evidence",
    "ar2100-portals-seedvr7b-lab-x4-split": "AR2100 portal x4 per-area source retained for reversible delivery evidence",
    "butrfly-apo8-x4-30fps-v2": "BUTRFLY V2 per-area pack retained for approved candidate evidence",
    "butrfly-apo8-x4-30fps-v2-merged": "BUTRFLY V2 merge intermediate retained for reproducibility",
    "butrfly-seedvr7b-lab-x4": "BUTRFLY x4 per-area source retained for reproducibility",
    "butrfly-seedvr7b-lab-x4-merged": "BUTRFLY x4 merge intermediate retained for reproducibility",
    "chimsmk-apo8-x4-30fps-v2": "CHIMSMK V2 per-area source retained for reversible delivery evidence",
    "chimsmk-apo8-x4-30fps-v2-rgb-neutral": "CHIMSMK Blended RGB-neutral per-area delivery source",
    "chimsmk-seedvr7b-lab-x4": "CHIMSMK x4 per-area source retained for reproducibility",
    "combined-20260901-ar1100-chimsmk-dstdvl-30fps-v2-rgb-neutral": "validated CHIMSMK and DSTDVL delivery root",
    "combined-20260901-ar1100-chimsmk-dstdvl-x4": "CHIMSMK and DSTDVL x4 delivery baseline",
    "combined-20260901-ar1100-chimsmk-dstdvl-x4-rgb-neutral": "CHIMSMK and DSTDVL Blended RGB-neutral x4 baseline",
    "combined-20260901-ar2100-portals-30fps-v2": "AR2100 portal V2 delivery root",
    "combined-20260901-ar2100-portals-and-butterfly-30fps-v2": "AR2100 portal and BUTRFLY V2 delivery root",
    "combined-20260901-ar2100-portals-and-butterfly-x4": "AR2100 portal and BUTRFLY x4 delivery root",
    "combined-20260901-ar2100-portals-x4": "AR2100 portal x4 delivery root",
    "dstdvl-chimsmk-apo8-x4-30fps-v2-merged": "CHIMSMK and DSTDVL V2 merge intermediate retained for reproducibility",
    "dstdvl-chimsmk-seedvr7b-lab-x4-merged": "CHIMSMK and DSTDVL x4 merge intermediate retained for reproducibility",
    "dstdvl1a-apo8-x4-30fps-v2": "DSTDVL1A V2 per-area source retained for reversible delivery evidence",
    "dstdvl1a-apo8-x4-30fps-v2-rgb-neutral": "DSTDVL1A Blended RGB-neutral per-area delivery source",
    "dstdvl1a-seedvr7b-lab-x4": "DSTDVL1A x4 per-area source retained for reproducibility",
    "dstdvl1b-apo8-x4-30fps-v2": "DSTDVL1B V2 per-area source retained for reversible delivery evidence",
    "dstdvl1b-apo8-x4-30fps-v2-rgb-neutral": "DSTDVL1B Blended RGB-neutral per-area delivery source",
    "dstdvl1b-seedvr7b-lab-x4": "DSTDVL1B x4 per-area source retained for reproducibility",
    "dstdvl1c-apo8-x4-30fps-v2": "DSTDVL1C V2 per-area source retained for reversible delivery evidence",
    "dstdvl1c-apo8-x4-30fps-v2-rgb-neutral": "DSTDVL1C Blended RGB-neutral per-area delivery source",
    "dstdvl1c-seedvr7b-lab-x4": "DSTDVL1C x4 per-area source retained for reproducibility",
}

ARCHIVE_FULL = {
    "ar0517-sphinct-occlusion-masque-perso-20260827",
    "ar0517-sphinct-occlusion-source-20260827",
    "ar0518-sphinct-occlusion-masque-perso-20260827",
    "ar0518-sphinct-occlusion-source-20260827",
    "ar0519-sphinct-occlusion-masque-perso-20260827",
    "ar0519-sphinct-occlusion-source-20260827",
    "ar0520-sphinct-occlusion-masque-perso-20260827",
    "ar0520-sphinct-occlusion-source-20260827",
    "ar0521-sphinct-occlusion-masque-perso-20260827",
    "ar0521-sphinct-occlusion-source-20260827",
    "ar0700-fire-lcut90-ovl-20260827",
    "ar0700-fire-lf40-overlap-merges-20260827",
    "ar0700-fire-lf64-ovl-20260827",
    "ar0700-fire-rgbneutral-ovl-20260827",
    "ar0700-fire4-overlap-merges-20260827",
}

ARCHIVE_SLICES: dict[str, tuple[str, ...]] = {
    "combined-20260823-spline-fit1-alpha": ("AR0604",),
    "combined-20260828-ar0602-portals-30fps-spline-fit1": ("AR0602",),
    "combined-20260828-ar1400-t005-nightlight": ("AR1400", "AR1404"),
}

ALL_PACKS = {
    "am0033ab-apo8-x4-30fps-v2",
    "am0033ab-spline-fit1-30fps-v2",
    "am0033ab-spline-fit1-feather6-30fps-v2",
    "ar0516-sphinct-sphinct2-geometric-sigma3-erode2",
    "ar0516-sphinct-sphinct2-spline-fit1-inner8-20260827",
    "ar0516-sphinct-spline-fit1-alpha-20260827",
    "ar0516-sphinct-spline-fit1-inner8-20260827",
    "ar0517-sphinct-occlusion-masque-perso-20260827",
    "ar0517-sphinct-occlusion-source-20260827",
    "ar0518-sphinct-occlusion-masque-perso-20260827",
    "ar0518-sphinct-occlusion-source-20260827",
    "ar0519-sphinct-occlusion-masque-perso-20260827",
    "ar0519-sphinct-occlusion-source-20260827",
    "ar0520-sphinct-occlusion-masque-perso-20260827",
    "ar0520-sphinct-occlusion-source-20260827",
    "ar0521-sphinct-occlusion-masque-perso-20260827",
    "ar0521-sphinct-occlusion-source-20260827",
    "ar0700-fire-lcut90-ovl-20260827",
    "ar0700-fire-lcut90-split-20260827",
    "ar0700-fire-lf40-overlap-merges-20260827",
    "ar0700-fire-lf64-ovl-20260827",
    "ar0700-fire-lf64-split-20260827",
    "ar0700-fire-rgb-neutral-20260827",
    "ar0700-fire-rgbneutral-ovl-20260827",
    "ar0700-fire4-overlap-merges-20260827",
    "ar0700-fountains30-fire-lf40-20260827",
    "ar0700-fountains30-fire4x4-20260827",
    "ar0700-fountains30-fire4x4-fire1x4-20260827",
    "ar1400-30fps-split-20260828",
    "ar1400-fountains-only-split-20260828",
    "bubbles2-ar0602-feather2-20260827",
    "bubbles2-ar0602-neutral-20260827",
    "bubbles2-ar0602-split-20260827",
    "bubbles2-feather1-20260827",
    "bubbles2-feather2-20260827",
    "bubbles2-feather3-20260827",
    "bubbles2-feather5-20260827",
    "bubbles2-feather8-20260827",
    "bubbles2-rgb-neutral-20260827",
    "bubbles2-split-20260827",
    "combined-20260823-spline-fit1-alpha",
    "combined-20260827-ar0900-plus-ar0516-sphinct-sphinct2-geometric-sigma3-erode2",
    "combined-20260827-ar0900-plus-ar0516-sphinct-sphinct2-geometric-sigma3-erode2-ar0517-occlusion-masque-perso",
    "combined-20260827-ar0900-plus-ar0516-sphinct-sphinct2-geometric-sigma3-erode2-ar0517-to-ar0521-occlusion-masque-perso",
    "combined-20260827-ar0900-plus-ar0516-sphinct-sphinct2-spline-fit1-inner8",
    "combined-20260827-ar0900-plus-ar0516-sphinct-spline-fit1",
    "combined-20260827-ar0900-plus-ar0516-sphinct-spline-fit1-inner8",
    "combined-20260827-ar0900-two-manual-masks-v3",
    "combined-20260827-native-occlusion-bridge-ar0517-mask-only",
    "combined-20260827-plus-am0033ab-spline-fit1",
    "combined-20260827-plus-am0033ab-spline-fit1-feather6",
    "combined-20260827-plus-am0033ab-x4-30fps",
    "combined-20260827-plus-ar0700-fire-lumcut90",
    "combined-20260827-plus-ar0700-fire-lumfeather40",
    "combined-20260827-plus-ar0700-fire-lumfeather64",
    "combined-20260827-plus-ar0700-fire-rgb-neutral",
    "combined-20260827-plus-ar0700-fountains30-fire4x4",
    "combined-20260827-plus-ar0700-fountains30-fire4x4-fire1x4",
    "combined-20260827-plus-bubbles2-ar0602",
    "combined-20260827-plus-bubbles2-ar0602-feather2",
    "combined-20260827-plus-flame2s-ar0602-radialA",
    "combined-20260828-ar0602-portals-30fps-spline-feather8",
    "combined-20260828-ar0602-portals-30fps-spline-fit1",
    "combined-20260828-ar0603-portal-spline-feather8",
    "combined-20260828-ar1400-t005-nightlight",
    "combined-20260828-plus-ar1400-30fps",
    "combined-20260828-plus-ar1400-fountains-only",
    "combined-20260831-ar0307-ar0329-six-bam-x4",
    "combined-20260831-ar0307-ar0329-six-bam-30fps-v2",
    "flame2s-ar0602-radialA-20260827",
    "flame2s-ar0602-split-20260827",
    "flame2s-radialA-premult-20260827",
    "flame2s-split-20260827",
}

CONTROL_PATHS = (
    "animations/index/animation_alpha_corrections.csv",
    "animations/index/animation_upscale_registry.csv",
    "asset-tracking/runs.csv",
    "asset-tracking/runs.json",
    "releases/BG2-HD-Upscale/bg2hd/manifests/animation-release-candidates.json",
    "releases/BG2-HD-Upscale/bg2hd/manifests/content.json",
    "releases/BG2-HD-Upscale/manifests/animation-release-candidates.json",
    "releases/BG2-HD-Upscale/manifests/content.json",
    "releases/BG2-HD-Upscale/manifests/release.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def files_under(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.is_file())
    return sorted(set(files), key=lambda item: item.as_posix().casefold())


def inventory(paths: Iterable[Path], base: Path) -> dict[str, Any]:
    records = []
    for path in files_under(paths):
        records.append(
            {
                "path": path.relative_to(base).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    payload = "".join(
        f"{record['path']}|{record['bytes']}|{record['sha256']}\n" for record in records
    ).encode("utf-8")
    return {
        "file_count": len(records),
        "bytes": sum(record["bytes"] for record in records),
        "aggregate_sha256": hashlib.sha256(payload).hexdigest().upper(),
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def root_manifest(path: Path) -> tuple[Path | None, dict[str, Any] | None]:
    manifest = path / "manifest.json"
    return (manifest, read_json(manifest)) if manifest.is_file() else (None, None)


def area_hashes(path: Path) -> set[str]:
    hashes: set[str] = set()
    for manifest in path.rglob("manifest.json"):
        try:
            data = read_json(manifest)
        except (OSError, json.JSONDecodeError):
            continue
        for area in data.get("areas", []):
            digest = str(area.get("manifest_sha256", "")).upper()
            if digest:
                hashes.add(digest)
    return hashes


def source_pack_evidence(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {"kind": "nested-area-packs", "references": []}
    source = str(data.get("source_pack", ""))
    if source:
        source_path = Path(source.replace("\\", "/"))
        source_manifest = source_path / "manifest.json"
        expected = str(data.get("source_pack_manifest_sha256", "")).upper()
        actual = sha256_file(source_manifest) if source_manifest.is_file() else ""
        return {
            "kind": "split-from-run",
            "references": [source],
            "source_present": source_path.is_dir(),
            "source_manifest_sha256": actual,
            "source_manifest_matches": bool(expected and actual == expected),
        }
    combined = data.get("combined_from", [])
    if combined:
        return {
            "kind": "combined-pack",
            "references": [str(item) for item in combined],
        }
    sliced = str(data.get("source_slice_of", ""))
    return {
        "kind": "historical-slice" if sliced else "standalone-pack",
        "references": [sliced] if sliced else [],
    }


def control_paths() -> list[Path]:
    paths = [ROOT / item for item in CONTROL_PATHS]
    paths.extend(
        sorted(
            (ROOT / "releases/BG2-HD-Upscale/manifests/animation-qa-approvals").rglob(
                "qa-approval.json"
            )
        )
    )
    return paths


def capture() -> dict[str, Any]:
    if RECEIPT.exists():
        raise RuntimeError(f"receipt already exists: {repo_path(RECEIPT)}")
    if ARCHIVE_ROOT.exists():
        raise RuntimeError(f"archive target already exists: {repo_path(ARCHIVE_ROOT)}")
    current = {path.name for path in PACK_ROOT.iterdir() if path.is_dir()}
    if current != ALL_PACKS:
        raise RuntimeError(
            f"unexpected pack roots; missing={sorted(ALL_PACKS-current)}, extra={sorted(current-ALL_PACKS)}"
        )

    active_hashes: set[str] = set()
    for name in KEEP_ACTIVE:
        active_hashes.update(area_hashes(PACK_ROOT / name))
    recoverable_hashes = set(active_hashes)
    for name in ARCHIVE_FULL:
        recoverable_hashes.update(area_hashes(PACK_ROOT / name))
    for name, areas in ARCHIVE_SLICES.items():
        data = read_json(PACK_ROOT / name / "manifest.json")
        recoverable_hashes.update(
            str(area["manifest_sha256"]).upper()
            for area in data.get("areas", [])
            if area.get("area_id") in areas
        )

    cached: dict[str, tuple[dict[str, Any] | None, dict[str, Any]]] = {}
    for name in sorted(ALL_PACKS):
        _manifest_path, data = root_manifest(PACK_ROOT / name)
        evidence = source_pack_evidence(data)
        cached[name] = (data, evidence)
        if evidence.get("source_manifest_matches"):
            recoverable_hashes.update(area_hashes(PACK_ROOT / name))

    entries: list[dict[str, Any]] = []
    total_bytes = 0
    expected_reclaimed = 0
    for name in sorted(ALL_PACKS):
        path = PACK_ROOT / name
        manifest_path, data = root_manifest(path)
        evidence = cached[name][1]
        all_files = files_under([path])
        byte_count = sum(item.stat().st_size for item in all_files)
        total_bytes += byte_count
        areas = list((data or {}).get("areas", []))
        exact_active = sum(
            1
            for area in areas
            if str(area.get("manifest_sha256", "")).upper() in active_hashes
        )
        unique = len(areas) - exact_active

        entry: dict[str, Any] = {
            "name": name,
            "old_path": repo_path(path),
            "file_count": len(all_files),
            "bytes": byte_count,
            "root_manifest_sha256": sha256_file(manifest_path) if manifest_path else "",
            "area_count": len(areas),
            "exact_active_area_count": exact_active,
            "nonactive_area_count": unique,
            "provenance": evidence,
        }
        if name in KEEP_ACTIVE:
            entry.update(
                classification="KEEP_ACTIVE",
                action="keep",
                reason=KEEP_ACTIVE[name],
            )
        elif name in ARCHIVE_FULL:
            preserved = inventory([path], path)
            entry.update(
                classification="ARCHIVE",
                action="move-whole-pack",
                reason="small unique historical/diagnostic pack retained without another copy",
                archive_path=repo_path(ARCHIVE_ROOT / "full" / name),
                preserved=preserved,
            )
        elif name in ARCHIVE_SLICES:
            components = [path / "manifest.json", *(path / area for area in ARCHIVE_SLICES[name])]
            if not all(component.exists() for component in components):
                raise RuntimeError(f"missing archive component for {name}")
            preserved = inventory(components, path)
            expected_reclaimed += byte_count - preserved["bytes"]
            entry.update(
                classification="ARCHIVE",
                action="keep-unique-slices-delete-duplicates",
                reason="historical unique area payload retained; copied combined areas are redundant",
                archive_path=repo_path(ARCHIVE_ROOT / "slices" / name),
                preserved_components=["manifest.json", *ARCHIVE_SLICES[name]],
                preserved=preserved,
            )
        else:
            if not manifest_path:
                raise RuntimeError(f"DELETE_SAFE pack lacks root manifest: {name}")
            missing = [
                str(area.get("area_id", ""))
                for area in areas
                if str(area.get("manifest_sha256", "")).upper() not in recoverable_hashes
            ]
            if missing:
                raise RuntimeError(f"uncovered payloads in {name}: {missing}")
            expected_reclaimed += byte_count - manifest_path.stat().st_size
            entry.update(
                classification="DELETE_SAFE",
                action="archive-descriptor-delete-generated-payload",
                reason=(
                    "deterministic split/combination; every area payload remains active, archived, "
                    "or reproducible from a source run whose manifest hash matches"
                ),
                descriptor_archive_path=repo_path(
                    ARCHIVE_ROOT / "descriptors" / name / "manifest.json"
                ),
            )
        entries.append(entry)

    controls = [
        {
            "path": repo_path(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in control_paths()
    ]
    receipt = {
        "schema": "bg2-upscale-animation-pack-cleanup-p3-v1",
        "captured_on": "2026-08-31",
        "scope": "animations/packs-par-zone only",
        "authority_policy": (
            "Physical lifecycle receipt only; never grants or changes production, QA, installation, "
            "or release status. Domain authorities and sealed artefacts remain unchanged."
        ),
        "archive_root": repo_path(ARCHIVE_ROOT),
        "summary": {
            "pack_count": len(entries),
            "keep_active_count": sum(e["classification"] == "KEEP_ACTIVE" for e in entries),
            "archive_count": sum(e["classification"] == "ARCHIVE" for e in entries),
            "delete_safe_count": sum(e["classification"] == "DELETE_SAFE" for e in entries),
            "uncertain_count": 0,
            "original_file_count": sum(e["file_count"] for e in entries),
            "original_bytes": total_bytes,
            "expected_reclaimed_bytes": expected_reclaimed,
        },
        "control_plane_baseline": controls,
        "packs": entries,
    }
    RECEIPT.write_bytes(json_bytes(receipt))
    return receipt


def check(*, verify_control_plane: bool = True) -> list[str]:
    errors: list[str] = []
    if not RECEIPT.is_file():
        return [f"missing receipt: {repo_path(RECEIPT)}"]
    receipt = read_json(RECEIPT)
    declared_post_p3: dict[str, dict[str, Any]] = {}
    if not POST_P3_RETENTION.is_file():
        errors.append(f"missing post-P3 retention manifest: {repo_path(POST_P3_RETENTION)}")
    else:
        retention = read_json(POST_P3_RETENTION)
        if retention.get("schema") != "bg2-upscale-animation-post-p3-pack-retention-v1":
            errors.append(f"unsupported post-P3 retention manifest: {repo_path(POST_P3_RETENTION)}")
        for entry in retention.get("packs", []):
            name = str(entry.get("name", ""))
            if not name or name in declared_post_p3:
                errors.append(f"invalid or duplicate post-P3 retained pack: {name!r}")
                continue
            declared_post_p3[name] = entry
            manifest = PACK_ROOT / name / "manifest.json"
            expected_hash = str(entry.get("manifest_sha256", "")).upper()
            if not manifest.is_file():
                errors.append(f"missing post-P3 retained pack manifest: {name}")
            elif not expected_hash or sha256_file(manifest) != expected_hash:
                errors.append(f"post-P3 retained pack manifest diverged: {name}")
    current = {path.name for path in PACK_ROOT.iterdir() if path.is_dir()}
    expected_active = set(KEEP_ACTIVE) | set(POST_P3_RETAINED) | set(declared_post_p3)
    if current != expected_active:
        errors.append(
            f"active pack roots differ: missing={sorted(expected_active-current)}, extra={sorted(current-expected_active)}"
        )

    for entry in receipt.get("packs", []):
        source = ROOT / entry["old_path"]
        classification = entry["classification"]
        if classification == "KEEP_ACTIVE":
            if not source.is_dir():
                errors.append(f"missing active pack: {entry['old_path']}")
                continue
            files = files_under([source])
            if len(files) != int(entry["file_count"]):
                errors.append(f"active pack file count changed: {entry['old_path']}")
            if sum(path.stat().st_size for path in files) != int(entry["bytes"]):
                errors.append(f"active pack byte count changed: {entry['old_path']}")
            manifest = source / "manifest.json"
            expected = str(entry.get("root_manifest_sha256", ""))
            if expected and (not manifest.is_file() or sha256_file(manifest) != expected):
                errors.append(f"active pack manifest changed: {entry['old_path']}")
        elif source.exists():
            errors.append(f"legacy pack still active: {entry['old_path']}")

        if classification == "ARCHIVE":
            archive = ROOT / entry["archive_path"]
            if not archive.is_dir():
                errors.append(f"missing archived pack evidence: {entry['archive_path']}")
            else:
                actual = inventory([archive], archive)
                if actual != entry["preserved"]:
                    errors.append(f"archived pack evidence changed: {entry['archive_path']}")
        elif classification == "DELETE_SAFE":
            descriptor = ROOT / entry["descriptor_archive_path"]
            if not descriptor.is_file():
                errors.append(f"missing archived pack descriptor: {entry['descriptor_archive_path']}")
            elif sha256_file(descriptor) != str(entry["root_manifest_sha256"]):
                errors.append(f"archived pack descriptor changed: {entry['descriptor_archive_path']}")

    if verify_control_plane:
        for control in receipt.get("control_plane_baseline", []):
            path = ROOT / control["path"]
            if not path.is_file():
                errors.append(f"missing control-plane file: {control['path']}")
            elif (
                path.stat().st_size != int(control["bytes"])
                or sha256_file(path) != control["sha256"]
            ):
                errors.append(f"control-plane file changed during P3: {control['path']}")

    candidates_path = ROOT / "releases/BG2-HD-Upscale/manifests/animation-release-candidates.json"
    if candidates_path.is_file():
        for candidate in read_json(candidates_path).get("candidates", []):
            pack = ROOT / candidate["source_pack"]
            manifest = pack / candidate["pack_manifest"]
            registry = pack / candidate["registry"]
            if not manifest.is_file() or sha256_file(manifest) != candidate["pack_manifest_sha256"]:
                errors.append(f"candidate pack manifest unavailable/diverged: {candidate['area']}")
            if not registry.is_file() or sha256_file(registry) != candidate["registry_sha256"]:
                errors.append(f"candidate registry unavailable/diverged: {candidate['area']}")
            qa = ROOT / candidate["qa_approval"]
            if not qa.is_file() or sha256_file(qa) != candidate["qa_approval_sha256"]:
                errors.append(f"candidate QA unavailable/diverged: {candidate['area']}")

    migrations_path = ROOT / "animations/index/path-migrations.json"
    if migrations_path.is_file():
        for migration in read_json(migrations_path).get("pack_migrations", []):
            old_path = ROOT / migration["from"]
            target = ROOT / migration["to"]
            evidence = target if target.is_file() else target / "manifest.json"
            if old_path.exists():
                errors.append(f"migrated legacy pack path returned: {migration['from']}")
            if not evidence.is_file():
                errors.append(f"pack migration target unavailable: {migration['to']}")
            elif sha256_file(evidence) != str(migration["manifest_sha256"]).upper():
                errors.append(f"pack migration evidence diverged: {migration['to']}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true", help="Capture the pre-cleanup receipt.")
    mode.add_argument("--check", action="store_true", help="Validate the completed cleanup.")
    parser.add_argument(
        "--verify-p3-baseline",
        action="store_true",
        help="Also require QA/release/run-index hashes to equal the values captured during P3.",
    )
    args = parser.parse_args(argv)
    try:
        if args.capture:
            receipt = capture()
            summary = receipt["summary"]
            print(
                "animation pack P3 captured: "
                f"{summary['pack_count']} packs, {summary['original_bytes']} bytes, "
                f"{summary['expected_reclaimed_bytes']} bytes reclaimable"
            )
            return 0
        errors = check(verify_control_plane=args.verify_p3_baseline)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    receipt = read_json(RECEIPT)
    summary = receipt["summary"]
    print(
        "animation pack P3: OK; "
        f"{summary['keep_active_count']} active, {summary['archive_count']} archived, "
        f"{summary['delete_safe_count']} deleted safely"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
