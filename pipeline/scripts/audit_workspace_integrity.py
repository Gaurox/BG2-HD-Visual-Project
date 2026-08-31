"""Audit physical workspace integrity without mutating domain authorities.

The only writable outputs are disposable projections in ``asset-tracking``.
Runs, manifests, extracted sources, payloads and historical artefacts are read
only.  The generated run index is deliberately not an authority.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_global_asset_registry as global_registry  # noqa: E402
import audit_animation_pack_cleanup as animation_pack_cleanup  # noqa: E402
import verify_historical_git_evidence as historical_git_evidence  # noqa: E402
import workspace_paths  # noqa: E402


GENERATOR = "pipeline/scripts/audit_workspace_integrity.py"
INTEGRITY_SCHEMA = "bg2-upscale-workspace-integrity-v1"
RUN_INDEX_SCHEMA = "bg2-upscale-workspace-run-index-v1"
OUTPUT_DIR = ROOT / "asset-tracking"
JSON_OUTPUTS = ("workspace-integrity.json", "runs.json")
RUN_CSV = "runs.csv"
ANIMATION_PATH_MIGRATIONS = "animations/index/path-migrations.json"
CLEANUP_MANIFEST = "docs/workspace-cleanup-manifest.json"
ARCHIVE_P2_MANIFEST = "docs/workspace-archive-p2-manifest.json"
ANIMATION_PACK_P3_MANIFEST = "docs/workspace-animation-packs-p3-manifest.json"
LEGACY_P4_MANIFEST = "docs/workspace-legacy-p4-manifest.json"
ACTIVE_SCRIPT_SUFFIXES = {".bat", ".cmd", ".js", ".ps1", ".py"}
WINDOWS_ABSOLUTE_PATH_LITERAL = re.compile(
    r"(?<![A-Za-z])[A-Za-z]:(?:\\\\|[\\/])"
    r"[^\\/\r\n'\"`]+(?:\\\\|[\\/])",
    re.IGNORECASE,
)
RUN_COLUMNS = (
    "run_key",
    "domain",
    "run_id",
    "asset_count",
    "asset_ids",
    "path",
    "run_kind",
    "descriptor_path",
    "recipe_path",
    "result_state",
    "qa_state",
    "selection_state",
    "selection_authority",
    "inputs_state",
    "outputs_state",
    "provenance_state",
    "legacy",
    "notes",
)


SOURCE_TABLES: tuple[dict[str, Any], ...] = (
    {
        "name": "videos",
        "domain": "videos",
        "csv": "video/index/resources.csv",
        "manifest": "video/index/manifest.json",
        "path_field": "extracted_path",
        "hash_field": "source_sha256",
        "root": "video",
        "canonical_path": "video/index/resources.csv",
    },
    {
        "name": "hud",
        "domain": "ui",
        "csv": "interface/gameplay-hud-bg2ee/index/resources.csv",
        "manifest": "interface/gameplay-hud-bg2ee/index/manifest.json",
        "path_field": "extracted_path",
        "hash_field": "source_sha256",
        "root": "interface/gameplay-hud-bg2ee/source",
        "canonical_path": "interface/gameplay-hud-bg2ee/index/resources.csv",
    },
    {
        "name": "ui-supplemental",
        "domain": "ui",
        "csv": "interface/index/resources.csv",
        "manifest": "interface/index/manifest.json",
        "path_field": "extracted_path",
        "hash_field": "source_sha256",
        "root": "interface/source",
        "canonical_path": "interface/index/resources.csv",
    },
    {
        "name": "icons",
        "domain": "icons",
        "csv": "icons/index/resources.csv",
        "manifest": "icons/index/manifest.json",
        "path_field": "extracted_path",
        "hash_field": "source_sha256",
        "root": "icons/source",
        "canonical_path": "icons/index/resources.csv",
    },
    {
        "name": "cursors",
        "domain": "cursors",
        "csv": "cursors/index/resources.csv",
        "manifest": "cursors/index/manifest.json",
        "path_field": "extracted_path",
        "hash_field": "source_sha256",
        "root": "cursors/source",
        "canonical_path": "cursors/index/resources.csv",
    },
    {
        "name": "effects",
        "domain": "effects",
        "csv": "effects/index/resources.csv",
        "manifest": "effects/index/manifest.json",
        "path_field": "extracted_path",
        "hash_field": "source_sha256",
        "root": "effects/source",
        "canonical_path": "effects/index/resources.csv",
    },
    {
        "name": "projectiles",
        "domain": "projectiles",
        "csv": "projectiles/index/resources.csv",
        "manifest": "projectiles/index/manifest.json",
        "path_field": "extracted_path",
        "hash_field": "source_sha256",
        "root": "projectiles/source",
        "canonical_path": "projectiles/index/resources.csv",
    },
    {
        "name": "graphics-supplemental",
        "domain": "multiple",
        "csv": "graphics/index/supplemental-assets.csv",
        "manifest": "graphics/index/supplemental-manifest.json",
        "path_field": "extracted_path",
        "hash_field": "source_sha256",
        "root": "graphics/source",
        "canonical_path": "graphics/index/supplemental-assets.csv",
    },
)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def inventory_evidence(path: Path) -> tuple[int, int, str]:
    """Return count, bytes and a path-sensitive aggregate hash for one file tree."""

    if path.is_file():
        root = path.parent
        files = [path]
    else:
        root = path
        files = [candidate for candidate in path.rglob("*") if candidate.is_file()]
    records = [
        (
            candidate.relative_to(root).as_posix(),
            candidate.stat().st_size,
            sha256_file(candidate),
        )
        for candidate in files
    ]
    records.sort(key=lambda item: item[0].casefold())
    payload = "".join(
        f"{relative}|{size}|{digest}\n" for relative, size, digest in records
    ).encode("utf-8")
    return len(records), sum(size for _relative, size, _digest in records), hashlib.sha256(
        payload
    ).hexdigest().upper()


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def normalize_repo_reference(value: str) -> str | None:
    """Turn current-root absolute references into repository-relative paths."""

    text = value.strip().replace("\\", "/")
    if not text:
        return None
    root_text = ROOT.resolve().as_posix().rstrip("/")
    if text.casefold().startswith((root_text + "/").casefold()):
        return text[len(root_text) + 1 :]
    if re.match(r"^[A-Za-z]:/", text):
        return None
    return text.lstrip("./")


def resolve_map_reference(value: str) -> tuple[str | None, bool]:
    """Resolve the two documented pre-layout map roots without rewriting history."""

    relative = normalize_repo_reference(value)
    if relative is None:
        return None, False
    if (ROOT / relative).exists():
        return relative, False
    match = re.match(r"^maps/(?:maps-principales|maps-secondaires)/([^/]+)/(.*)$", relative, re.IGNORECASE)
    if match:
        migrated = f"maps/{match.group(1)}/{match.group(2)}"
        if (ROOT / migrated).exists():
            return migrated, True
    return relative, False


def add_issue(
    issues: list[dict[str, Any]],
    severity: str,
    code: str,
    domain: str,
    message: str,
    *,
    path: str = "",
    asset_id: str = "",
    run_id: str = "",
    details: Mapping[str, Any] | None = None,
) -> None:
    issue: dict[str, Any] = {
        "code": code,
        "domain": domain,
        "message": message,
        "severity": severity,
    }
    if path:
        issue["path"] = path
    if asset_id:
        issue["asset_id"] = asset_id
    if run_id:
        issue["run_id"] = run_id
    if details:
        issue["details"] = dict(details)
    issues.append(issue)


def add_run(runs: dict[str, dict[str, Any]], record: dict[str, Any]) -> None:
    record["asset_ids"] = sorted(set(record.get("asset_ids", [])), key=str.casefold)
    record["asset_count"] = len(record["asset_ids"])
    key = record["run_key"]
    if key in runs:
        existing = runs[key]
        existing["asset_ids"] = sorted(
            set(existing["asset_ids"]) | set(record["asset_ids"]), key=str.casefold
        )
        existing["asset_count"] = len(existing["asset_ids"])
        return
    runs[key] = record


def iter_path_records(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if isinstance(value.get("path"), str):
            yield value
        for child in value.values():
            yield from iter_path_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_path_records(child)


def default_run(
    *,
    run_key: str,
    domain: str,
    run_id: str,
    asset_ids: Iterable[str],
    path: str,
    run_kind: str,
    descriptor_path: str = "",
    recipe_path: str = "",
    result_state: str = "unknown",
    qa_state: str = "unknown",
    selection_state: str = "historical",
    selection_authority: str = "",
    inputs_state: str = "unknown",
    outputs_state: str = "unknown",
    provenance_state: str = "partial",
    legacy: bool = False,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "run_key": run_key,
        "domain": domain,
        "run_id": run_id,
        "asset_ids": list(asset_ids),
        "path": path,
        "run_kind": run_kind,
        "descriptor_path": descriptor_path,
        "recipe_path": recipe_path,
        "result_state": result_state,
        "qa_state": qa_state,
        "selection_state": selection_state,
        "selection_authority": selection_authority,
        "inputs_state": inputs_state,
        "outputs_state": outputs_state,
        "provenance_state": provenance_state,
        "legacy": legacy,
        "notes": notes,
    }


def audit_registry(issues: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, int]]:
    projection = global_registry.build_outputs(ROOT)
    registry = projection["registry"]
    records = registry["assets"]
    asset_ids = [record["asset_id"] for record in records]
    if len(asset_ids) != len(set(asset_ids)):
        add_issue(
            issues,
            "error",
            "registry-duplicate-asset-id",
            "global",
            "Le registre global contient des identifiants dupliqués.",
        )

    declared_inputs = {item["path"]: item["sha256"] for item in registry["inputs"]}
    canonical_counts: Counter[str] = Counter()
    for record in records:
        canonical = record["canonical_source"]["path"]
        canonical_counts[canonical] += 1
        path = ROOT / canonical
        if not path.is_file():
            add_issue(
                issues,
                "error",
                "registry-canonical-source-missing",
                record["domain"],
                "La source canonique référencée par le registre est absente.",
                path=canonical,
                asset_id=record["asset_id"],
            )
        if canonical not in declared_inputs:
            add_issue(
                issues,
                "error",
                "registry-canonical-source-not-declared",
                record["domain"],
                "La source canonique n'est pas déclarée dans les inputs du registre.",
                path=canonical,
                asset_id=record["asset_id"],
            )

    for path_text, expected in sorted(declared_inputs.items()):
        path = ROOT / path_text
        if not path.is_file():
            add_issue(
                issues,
                "error",
                "registry-input-missing",
                "global",
                "Un input déclaré du registre est absent.",
                path=path_text,
            )
        elif sha256_file(path) != expected.upper():
            add_issue(
                issues,
                "error",
                "registry-input-hash-mismatch",
                "global",
                "Le hash d'un input ne correspond plus au registre généré.",
                path=path_text,
            )

    return registry, dict(canonical_counts)


def audit_source_tables(
    issues: list[dict[str, Any]], canonical_counts: Mapping[str, int]
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for config in SOURCE_TABLES:
        csv_path = ROOT / config["csv"]
        manifest_path = ROOT / config["manifest"]
        rows = read_csv(csv_path)
        manifest = read_json(manifest_path)
        expected_paths: set[str] = set()
        missing = 0
        mismatched = 0
        for row in rows:
            path_text = row[config["path_field"]]
            expected_paths.add(path_text)
            path = ROOT / path_text
            if not path.is_file():
                missing += 1
                add_issue(
                    issues,
                    "error",
                    "extracted-source-missing",
                    config["domain"],
                    "Une source extraite référencée est absente.",
                    path=path_text,
                    asset_id=row.get("asset_key", ""),
                )
            elif sha256_file(path) != row[config["hash_field"]].upper():
                mismatched += 1
                add_issue(
                    issues,
                    "error",
                    "extracted-source-hash-mismatch",
                    config["domain"],
                    "Une source extraite ne correspond plus à son hash canonique.",
                    path=path_text,
                    asset_id=row.get("asset_key", ""),
                )

        manifest_count = int(manifest["asset_count"])
        if manifest_count != len(rows):
            add_issue(
                issues,
                "error",
                "source-manifest-count-mismatch",
                config["domain"],
                "Le nombre du manifest diffère du CSV canonique.",
                path=config["manifest"],
                details={"manifest": manifest_count, "csv": len(rows)},
            )

        root = ROOT / config["root"]
        present_files = {
            repo_path(path)
            for path in root.rglob("*")
            if path.is_file()
            and not (
                config["name"] == "videos"
                and "runs" in path.relative_to(root).parts
                and path.relative_to(root).parts[0].casefold() == "runs"
            )
        } if root.is_dir() else set()
        expected_folded = {path.casefold() for path in expected_paths}
        extra = sorted(
            (
                path
                for path in present_files
                if path.casefold() not in expected_folded
                and not (
                    config["name"] == "videos"
                    and (path.casefold().startswith("video/index/") or path.casefold() == "video/readme.md")
                )
            ),
            key=str.casefold,
        )
        # Historical video derivatives belong in video/runs and are audited separately.
        if config["name"] == "videos":
            if extra:
                extension_counts = Counter(Path(path).suffix.lower() or "<none>" for path in extra)
                add_issue(
                    issues,
                    "warning",
                    "video-unindexed-work-products",
                    "videos",
                    "Des conversions ou rendus de travail cohabitent encore avec les sources WBM.",
                    path="video/",
                    details={
                        "file_count": len(extra),
                        "extensions": dict(sorted(extension_counts.items())),
                        "policy": "ranger dans video/runs avec une preuve de rattachement",
                    },
                )
        elif extra:
            add_issue(
                issues,
                "warning",
                "source-root-unindexed-files",
                config["domain"],
                "Des fichiers non référencés sont présents dans une racine de sources extraites.",
                path=config["root"],
                details={"file_count": len(extra), "examples": extra[:10]},
            )

        projected = canonical_counts.get(config["canonical_path"], 0)
        if projected != len(rows):
            add_issue(
                issues,
                "error",
                "source-registry-count-mismatch",
                config["domain"],
                "Le nombre d'entrées projetées depuis cette autorité diffère de son CSV.",
                path=config["canonical_path"],
                details={"csv": len(rows), "registry": projected},
            )
        results.append(
            {
                "authority": config["csv"],
                "domain": config["domain"],
                "extra_file_count": len(extra),
                "hash_mismatch_count": mismatched,
                "manifest_asset_count": manifest_count,
                "missing_file_count": missing,
                "referenced_file_count": len(expected_paths),
                "registry_projection_count": projected,
            }
        )

    # Fonts are grouped assets: each member is a separate immutable source file.
    font_rows = read_csv(ROOT / "interface/fonts/index/resources.csv")
    font_expected: set[str] = set()
    for row in font_rows:
        members = json.loads(row["members_json"])
        member_hashes: list[str] = []
        for member in members:
            path_text = member["extracted_path"]
            font_expected.add(path_text)
            path = ROOT / path_text
            if not path.is_file():
                add_issue(
                    issues,
                    "error",
                    "extracted-source-missing",
                    "ui",
                    "Un membre de police extrait est absent.",
                    path=path_text,
                    asset_id=row["asset_key"],
                )
                continue
            actual = sha256_file(path)
            member_hashes.append(actual)
            if actual != member["sha256"].upper():
                add_issue(
                    issues,
                    "error",
                    "extracted-source-hash-mismatch",
                    "ui",
                    "Un membre de police ne correspond plus à son hash canonique.",
                    path=path_text,
                    asset_id=row["asset_key"],
                )
        combined = hashlib.sha256(json_bytes(members)).hexdigest().upper()
        if len(member_hashes) == len(members) and combined != row["source_sha256"].upper():
            add_issue(
                issues,
                "error",
                "font-group-hash-mismatch",
                "ui",
                "L'empreinte groupée d'une police ne correspond plus à ses membres.",
                asset_id=row["asset_key"],
            )
    font_present = {
        repo_path(path)
        for path in (ROOT / "interface/fonts/source").rglob("*")
        if path.is_file()
    }
    font_extra = sorted(font_present - font_expected, key=str.casefold)
    if font_extra:
        add_issue(
            issues,
            "warning",
            "source-root-unindexed-files",
            "ui",
            "Des fichiers non référencés sont présents dans les sources de polices.",
            path="interface/fonts/source",
            details={"file_count": len(font_extra), "examples": font_extra[:10]},
        )
    font_projected = canonical_counts.get("interface/fonts/index/resources.csv", 0)
    if font_projected != len(font_rows):
        add_issue(
            issues,
            "error",
            "source-registry-count-mismatch",
            "ui",
            "Le nombre de polices projetées diffère du CSV canonique.",
            path="interface/fonts/index/resources.csv",
            details={"csv": len(font_rows), "registry": font_projected},
        )
    results.append(
        {
            "authority": "interface/fonts/index/resources.csv",
            "domain": "ui",
            "extra_file_count": len(font_extra),
            "hash_mismatch_count": 0,
            "manifest_asset_count": len(font_rows),
            "missing_file_count": sum(not (ROOT / path).is_file() for path in font_expected),
            "referenced_file_count": len(font_expected),
            "registry_projection_count": font_projected,
        }
    )

    # Area animation BAMs use one directory per logical asset.
    animation_rows = read_csv(ROOT / "animations/index/ressources.csv")
    animation_expected: set[str] = set()
    for row in animation_rows:
        path_text = f"animations/{row['relative_path']}/source.bam"
        animation_expected.add(path_text)
        path = ROOT / path_text
        if not path.is_file():
            add_issue(
                issues,
                "error",
                "extracted-source-missing",
                "animations",
                "Le BAM source d'une animation inventoriée est absent.",
                path=path_text,
                asset_id=f"animations:bam:{row['bam_resref'].upper()}",
            )
        elif sha256_file(path) != row["sha256"].upper():
            add_issue(
                issues,
                "error",
                "extracted-source-hash-mismatch",
                "animations",
                "Le BAM source d'une animation ne correspond plus au catalogue.",
                path=path_text,
                asset_id=f"animations:bam:{row['bam_resref'].upper()}",
            )
    present_animation_sources = {
        repo_path(path)
        for path in (ROOT / "animations/ressources").glob("*/source.bam")
        if path.is_file()
    }
    extra_animation_sources = sorted(
        present_animation_sources - animation_expected, key=str.casefold
    )
    if extra_animation_sources:
        add_issue(
            issues,
            "warning",
            "source-root-unindexed-files",
            "animations",
            "Des BAM source d'animation ne sont pas référencés.",
            path="animations/ressources",
            details={"file_count": len(extra_animation_sources), "examples": extra_animation_sources[:10]},
        )
    results.append(
        {
            "authority": "animations/index/ressources.csv",
            "domain": "animations",
            "extra_file_count": len(extra_animation_sources),
            "hash_mismatch_count": 0,
            "manifest_asset_count": len(animation_rows),
            "missing_file_count": sum(not (ROOT / path).is_file() for path in animation_expected),
            "referenced_file_count": len(animation_expected),
            "registry_projection_count": canonical_counts.get(
                "animations/index/animation_upscale_registry.csv", 0
            ),
        }
    )
    return sorted(results, key=lambda item: (item["domain"], item["authority"]))


def audit_portraits(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify immutable portrait BMPs while preserving occurrence-oriented layouts."""

    audits: list[dict[str, Any]] = []
    stock_rows = read_csv(ROOT / "portraits/inventaire_portraits.csv")
    stock_expected: set[str] = set()
    stock_missing = 0
    stock_mismatch = 0
    for row in stock_rows:
        path = ROOT / "portraits" / row["fichier"]
        stock_expected.add(repo_path(path))
        if not path.is_file():
            stock_missing += 1
            add_issue(
                issues,
                "error",
                "portrait-source-missing",
                "portraits",
                "Un portrait stock inventorié est absent.",
                path=(Path("portraits") / row["fichier"]).as_posix(),
                asset_id=f"portraits:stock:{row['portrait']}-{row['taille']}",
            )
        elif sha256_file(path) != row["sha256"].upper():
            stock_mismatch += 1
            add_issue(
                issues,
                "error",
                "portrait-source-hash-mismatch",
                "portraits",
                "Un portrait stock ne correspond plus à son hash canonique.",
                path=repo_path(path),
                asset_id=f"portraits:stock:{row['portrait']}-{row['taille']}",
            )
    stock_present = {
        repo_path(path)
        for folder in ("grands", "moyens", "petits")
        for path in (ROOT / "portraits" / folder).glob("*.bmp")
    }
    stock_extra = sorted(stock_present - stock_expected, key=str.casefold)
    if stock_extra:
        add_issue(
            issues,
            "warning",
            "portrait-source-unindexed-files",
            "portraits",
            "Des portraits stock BMP ne sont pas inventoriés.",
            path="portraits/",
            details={"file_count": len(stock_extra), "examples": stock_extra[:10]},
        )
    audits.append(
        {
            "authority": "portraits/inventaire_portraits.csv",
            "asset_count": len(stock_rows),
            "occurrence_count": len(stock_rows),
            "physical_file_count": len(stock_present),
            "missing_file_count": stock_missing,
            "hash_mismatch_count": stock_mismatch,
            "extra_file_count": len(stock_extra),
        }
    )

    grouped_specs = (
        (
            "portraits-recrutables/inventaire.csv",
            "portraits-recrutables",
            "portraits:recruitable",
        ),
        (
            "portraits/pnj-rencontres/inventaire.csv",
            "portraits/pnj-rencontres",
            "portraits:encountered",
        ),
        (
            "portraits/mod-PPE/inventaire.csv",
            "portraits/mod-PPE",
            "portraits:ppe",
        ),
    )
    for authority, root_text, asset_prefix in grouped_specs:
        rows = read_csv(ROOT / authority)
        root = ROOT / root_text
        files = sorted(root.rglob("*.bmp"), key=lambda path: repo_path(path).casefold())
        by_resref: dict[str, list[Path]] = defaultdict(list)
        for path in files:
            by_resref[path.stem.upper()].append(path)
        expected_hashes: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            expected_hashes[row["ressource"].upper()].add(row["sha256"].upper())
        missing = 0
        mismatched = 0
        for resref, hashes in sorted(expected_hashes.items()):
            candidates = by_resref.get(resref, [])
            if not candidates:
                missing += 1
                add_issue(
                    issues,
                    "error",
                    "portrait-source-missing",
                    "portraits",
                    "Un portrait inventorié est absent de son arborescence physique.",
                    path=root_text,
                    asset_id=f"{asset_prefix}:{resref}",
                )
                continue
            for candidate in candidates:
                actual = sha256_file(candidate)
                if not any(actual.startswith(expected) for expected in hashes):
                    mismatched += 1
                    add_issue(
                        issues,
                        "error",
                        "portrait-source-hash-mismatch",
                        "portraits",
                        "Une copie physique de portrait ne correspond à aucune empreinte canonique.",
                        path=repo_path(candidate),
                        asset_id=f"{asset_prefix}:{resref}",
                    )
        extras = sorted(
            (path for resref, candidates in by_resref.items() if resref not in expected_hashes for path in candidates),
            key=lambda path: repo_path(path).casefold(),
        )
        if extras:
            add_issue(
                issues,
                "warning",
                "portrait-source-unindexed-files",
                "portraits",
                "Des portraits BMP ne sont pas rattachés à l'inventaire de leur domaine.",
                path=root_text,
                details={"file_count": len(extras), "examples": [repo_path(path) for path in extras[:10]]},
            )
        audits.append(
            {
                "authority": authority,
                "asset_count": len(expected_hashes),
                "occurrence_count": len(rows),
                "physical_file_count": len(files),
                "missing_file_count": missing,
                "hash_mismatch_count": mismatched,
                "extra_file_count": len(extras),
            }
        )
    return {
        "authorities": audits,
        "logical_asset_count": sum(item["asset_count"] for item in audits),
        "physical_file_count": sum(item["physical_file_count"] for item in audits),
    }


def audit_maps(issues: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> dict[str, int]:
    rows = read_csv(ROOT / "areas.csv")
    selected: dict[str, set[str]] = defaultdict(set)
    expected_sources: set[str] = set()
    for row in rows:
        area = row["area_id"].upper()
        expected_sources.update(
            {
                f"maps/{area}/rendus-x1/tuiles-principales/{area}-tuiles-principales-x1.png",
                f"maps/{area}/rendus-x1/tuiles-secondaires/{area}-tuiles-secondaires-x1.png",
            }
        )
        if row["has_night_variant"] == "yes":
            expected_sources.update(
                {
                    f"maps/{area}/rendus-x1/tuiles-principales-nuit/{area}N-tuiles-principales-x1.png",
                    f"maps/{area}/rendus-x1/tuiles-secondaires-nuit/{area}N-tuiles-secondaires-x1.png",
                }
            )
        for field, variant in (("runs", "day"), ("runs_nuit", "night")):
            for run_id in filter(None, (item.strip() for item in row[field].split(";"))):
                selected[f"maps/{area}/runs/{run_id}"].add(f"maps:{area}:{variant}")

    missing_sources = sorted(path for path in expected_sources if not (ROOT / path).is_file())
    if missing_sources:
        add_issue(
            issues,
            "error",
            "map-extracted-source-missing",
            "maps",
            "Des maîtres x1 déclarés comme extraits dans areas.csv sont absents.",
            path="maps/",
            details={"file_count": len(missing_sources), "examples": missing_sources[:10]},
        )
    present_sources = {
        repo_path(path)
        for path in (ROOT / "maps").rglob("*.png")
        if "rendus-x1" in path.parts
    }
    extra_sources = sorted(
        (path for path in present_sources if path.casefold() not in {item.casefold() for item in expected_sources}),
        key=str.casefold,
    )
    if extra_sources:
        add_issue(
            issues,
            "warning",
            "map-source-root-experiment-files",
            "maps",
            "Des essais d'upscale sont mélangés aux maîtres x1 canoniques d'AR0410.",
            path="maps/AR0410/rendus-x1/tuiles-principales",
            details={
                "file_count": len(extra_sources),
                "examples": extra_sources[:10],
                "policy": "conserver; candidat à archivage hors de rendus-x1 après revue",
            },
        )

    physical: set[str] = set()
    descriptor_count = 0
    legacy_count = 0
    migrated_reference_count = 0
    for area_dir in sorted((ROOT / "maps").iterdir(), key=lambda path: path.name):
        if not area_dir.is_dir():
            continue
        run_root = area_dir / "runs"
        if not run_root.is_dir():
            continue
        for run_dir in sorted((path for path in run_root.iterdir() if path.is_dir()), key=lambda path: path.name):
            path_text = repo_path(run_dir)
            physical.add(path_text)
            run_json = run_dir / "run.json"
            legacy = False
            recipe = ""
            result = "unknown"
            inputs = "unknown"
            provenance = "partial"
            descriptor = ""
            notes = ""
            referenced_files_state = "unknown"
            cleanup_legacy = path_text == "maps/AR0410/runs/legacy-upscale-tests-20260818"
            if run_json.is_file():
                descriptor_count += 1
                descriptor = repo_path(run_json)
                data = read_json(run_json)
                result = str(data.get("status", "unknown"))
                workflow = data.get("workflow", {})
                workflow_path = normalize_repo_reference(str(workflow.get("path", "")))
                recipe = workflow_path or str(workflow.get("name", ""))
                if data.get("run_id") != run_dir.name or str(data.get("area_id", "")).upper() != area_dir.name.upper():
                    add_issue(
                        issues,
                        "error",
                        "map-run-identity-mismatch",
                        "maps",
                        "L'identité du run.json ne correspond pas à son chemin.",
                        path=descriptor,
                        run_id=run_dir.name,
                    )
                inputs = "verified" if data.get("jobs") and data.get("preflight") else "partial"
                provenance = "verified" if workflow.get("sha256") and data.get("parameters") else "partial"
                if workflow_path:
                    workflow_file = ROOT / workflow_path
                    if not workflow_file.is_file():
                        add_issue(
                            issues,
                            "error",
                            "map-run-workflow-missing",
                            "maps",
                            "La recette ComfyUI d'un run sélectionné est absente.",
                            path=workflow_path,
                            run_id=run_dir.name,
                        )
                    elif workflow.get("sha256") and sha256_file(workflow_file) != str(workflow["sha256"]).upper():
                        add_issue(
                            issues,
                            "error",
                            "map-run-workflow-hash-mismatch",
                            "maps",
                            "La recette ComfyUI ne correspond plus au hash scellé dans le run.",
                            path=workflow_path,
                            run_id=run_dir.name,
                        )
                missing_references: list[str] = []
                size_mismatches: list[str] = []
                for reference in iter_path_records({"jobs": data.get("jobs", []), "outputs": data.get("outputs", {})}):
                    reference_path, migrated = resolve_map_reference(str(reference["path"]))
                    if migrated:
                        migrated_reference_count += 1
                    if not reference_path:
                        continue
                    physical_path = ROOT / reference_path
                    if not physical_path.is_file():
                        missing_references.append(reference_path)
                    elif reference.get("bytes") is not None and physical_path.stat().st_size != int(reference["bytes"]):
                        size_mismatches.append(reference_path)
                if missing_references:
                    inputs = "partial"
                    referenced_files_state = "partial"
                    add_issue(
                        issues,
                        "warning",
                        "map-run-referenced-files-missing",
                        "maps",
                        "Des inputs/outputs intermédiaires scellés d'un run sélectionné sont absents, mais son build final existe.",
                        path=path_text,
                        run_id=run_dir.name,
                        details={"file_count": len(set(missing_references)), "examples": sorted(set(missing_references))[:10]},
                    )
                if size_mismatches:
                    inputs = "invalid"
                    referenced_files_state = "invalid"
                    add_issue(
                        issues,
                        "error",
                        "map-run-referenced-file-size-mismatch",
                        "maps",
                        "La taille d'inputs/outputs ne correspond plus au run scellé.",
                        path=path_text,
                        run_id=run_dir.name,
                        details={"file_count": len(set(size_mismatches)), "examples": sorted(set(size_mismatches))[:10]},
                    )
                if referenced_files_state == "unknown":
                    referenced_files_state = "present"
            elif (run_dir / "README.md").is_file() and path_text == "maps/AR0413/runs/wtoil-family-definitive":
                legacy = True
                legacy_count += 1
                descriptor = repo_path(run_dir / "README.md")
                result = "completed-legacy"
                inputs = "documented"
                notes = "Run historique antérieur à run.json; conservé et sélectionné par areas.csv."
                add_issue(
                    issues,
                    "info",
                    "map-legacy-run-without-json",
                    "maps",
                    "Ce run historique reste traçable par son README et areas.csv, sans réécriture rétroactive.",
                    path=path_text,
                    run_id=run_dir.name,
                )
            elif cleanup_legacy:
                legacy = True
                legacy_count += 1
                descriptor = CLEANUP_MANIFEST
                result = "historical-experiment"
                inputs = "documented"
                provenance = "verified-move"
                referenced_files_state = "present"
                notes = "Essais AR0410 retirés des maîtres x1; aucune sélection ni QA inférée."
            else:
                add_issue(
                    issues,
                    "error",
                    "map-run-descriptor-missing",
                    "maps",
                    "Un run de map n'a ni run.json ni exception historique documentée.",
                    path=path_text,
                    run_id=run_dir.name,
                )
            build_exists = (run_dir / "05_build").is_dir() or cleanup_legacy
            if path_text in selected and not build_exists:
                add_issue(
                    issues,
                    "error",
                    "selected-map-build-missing",
                    "maps",
                    "Le build du run sélectionné est absent.",
                    path=f"{path_text}/05_build",
                    run_id=run_dir.name,
                )
            selection = "selected" if path_text in selected else (
                "historical-unselected" if cleanup_legacy else "unselected"
            )
            if selection == "unselected":
                add_issue(
                    issues,
                    "warning",
                    "map-run-unselected",
                    "maps",
                    "Un run physique n'est rattaché à aucune sélection de areas.csv.",
                    path=path_text,
                    run_id=run_dir.name,
                )
            add_run(
                runs,
                default_run(
                    run_key=f"maps:{area_dir.name}:{run_dir.name}",
                    domain="maps",
                    run_id=run_dir.name,
                    asset_ids=selected.get(path_text, {f"maps:{area_dir.name}:day"}),
                    path=path_text,
                    run_kind="legacy-map-experiment" if cleanup_legacy else "map-upscale",
                    descriptor_path=descriptor,
                    recipe_path=recipe,
                    result_state=result,
                    qa_state="from-areas-csv" if selection == "selected" else "unknown",
                    selection_state=selection,
                    selection_authority="areas.csv" if selection == "selected" else "",
                    inputs_state=inputs,
                    outputs_state=(
                        "missing"
                        if not build_exists
                        else referenced_files_state
                        if referenced_files_state in {"partial", "invalid"}
                        else "present"
                    ),
                    provenance_state=provenance,
                    legacy=legacy,
                    notes=notes,
                ),
            )

    for path_text, asset_ids in sorted(selected.items()):
        if path_text not in physical:
            add_issue(
                issues,
                "error",
                "selected-map-run-missing",
                "maps",
                "Un run sélectionné par areas.csv est absent du disque.",
                path=path_text,
                asset_id=";".join(sorted(asset_ids)),
                run_id=Path(path_text).name,
            )
    if migrated_reference_count:
        add_issue(
            issues,
            "info",
            "map-historical-paths-adapted",
            "maps",
            "Les chemins pré-layout des runs historiques sont résolus sans modifier leurs manifests scellés.",
            path="maps/",
            details={
                "reference_count": migrated_reference_count,
                "mappings": [
                    "maps/maps-principales/<AREA>/ -> maps/<AREA>/",
                    "maps/maps-secondaires/<AREA>/ -> maps/<AREA>/",
                ],
            },
        )
    return {
        "canonical_asset_rows": len(rows),
        "descriptor_count": descriptor_count,
        "legacy_descriptor_count": legacy_count,
        "migrated_reference_count": migrated_reference_count,
        "extracted_source_count": len(expected_sources) - len(missing_sources),
        "extra_source_file_count": len(extra_sources),
        "physical_run_count": len(physical),
        "selected_run_count": len(selected),
    }


def referenced_animation_runs(candidates: list[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for candidate in candidates:
        for match in re.findall(r"animations/runs/([^\s+;,)]+)", candidate.get("source_run", "")):
            result[match.rstrip(".")].append(candidate["area"].upper())
    return result


def animation_migration_pairs(data: Mapping[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for section in ("migrations", "loose_file_migrations"):
        for item in data.get(section, []):
            source = str(item.get("from", "")).replace("\\", "/").rstrip("/")
            target = str(item.get("to", "")).replace("\\", "/").rstrip("/")
            if source and target:
                pairs.append((source, target))
    return sorted(pairs, key=lambda item: len(item[0]), reverse=True)


def audit_animations(
    issues: list[dict[str, Any]], runs: dict[str, dict[str, Any]]
) -> dict[str, int]:
    migration_path = ROOT / ANIMATION_PATH_MIGRATIONS
    migration_data = read_json(migration_path)
    migrations = migration_data.get("migrations", [])
    loose_file_migrations = migration_data.get("loose_file_migrations", [])
    synthetic_bindings = migration_data.get("synthetic_run_bindings", [])
    migration_by_target = {
        str(item["to"]).replace("\\", "/").rstrip("/"): item for item in migrations
    }
    migration_by_target.update(
        {
            str(item["path"]).replace("\\", "/").rstrip("/"): item
            for item in synthetic_bindings
        }
    )
    path_pairs = animation_migration_pairs(migration_data)

    for item in migrations:
        source = ROOT / str(item["from"])
        target = ROOT / str(item["to"])
        if source.exists():
            add_issue(
                issues,
                "error",
                "animation-migration-source-still-present",
                "animations",
                "Un ancien répertoire d'animation est encore présent dans proto après migration.",
                path=repo_path(source),
            )
        if not target.is_dir():
            add_issue(
                issues,
                "error",
                "animation-migration-target-missing",
                "animations",
                "La destination déclarée d'un ancien prototype d'animation est absente.",
                path=str(item["to"]),
            )
    for item in loose_file_migrations:
        source = ROOT / str(item["from"])
        target = ROOT / str(item["to"])
        if source.exists():
            add_issue(
                issues,
                "error",
                "animation-loose-file-source-still-present",
                "animations",
                "Un fichier d'atelier animation est encore présent à la racine de proto.",
                path=repo_path(source),
            )
        if not target.is_file():
            add_issue(
                issues,
                "error",
                "animation-loose-file-target-missing",
                "animations",
                "La destination déclarée d'un fichier d'atelier animation est absente.",
                path=str(item["to"]),
            )

    migrated_files: set[Path] = set()
    for item in migrations:
        target = ROOT / str(item["to"])
        if target.is_dir():
            migrated_files.update(path for path in target.rglob("*") if path.is_file())
    for item in loose_file_migrations:
        target = ROOT / str(item["to"])
        if target.is_file():
            migrated_files.add(target)
    verification = migration_data.get("migration_verification", {})
    migrated_bytes = sum(path.stat().st_size for path in migrated_files)
    if (
        len(migrated_files) != int(verification.get("file_count", -1))
        or migrated_bytes != int(verification.get("bytes", -1))
    ):
        add_issue(
            issues,
            "error",
            "animation-migration-inventory-changed",
            "animations",
            "Le nombre de fichiers ou d'octets migrés ne correspond plus à la preuve de déplacement.",
            path=ANIMATION_PATH_MIGRATIONS,
            details={
                "actual_bytes": migrated_bytes,
                "actual_file_count": len(migrated_files),
                "expected_bytes": verification.get("bytes"),
                "expected_file_count": verification.get("file_count"),
            },
        )

    retained_proto = set(migration_data.get("retained_proto_directories", []))
    present_proto = {
        path.name for path in (ROOT / "proto").iterdir() if path.is_dir()
    }
    unexpected_proto = sorted(present_proto - retained_proto, key=str.casefold)
    missing_retained_proto = sorted(retained_proto - present_proto, key=str.casefold)
    if unexpected_proto:
        add_issue(
            issues,
            "error",
            "animation-work-remains-in-proto",
            "animations",
            "Des répertoires non autorisés restent dans proto après la migration animation.",
            path="proto/",
            details={"directories": unexpected_proto},
        )
    if missing_retained_proto:
        add_issue(
            issues,
            "warning",
            "retained-proto-directory-missing",
            "global",
            "Un répertoire explicitement laissé hors du domaine animation n'est plus présent.",
            path="proto/",
            details={"directories": missing_retained_proto},
        )

    alpha_authority = ROOT / "animations/index/animation_alpha_corrections.csv"
    alpha_by_path: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(alpha_authority):
        prototype = str(row.get("prototype", ""))
        if not prototype:
            continue
        resolved = resolve_migrated_reference(prototype, path_pairs)
        if resolved is None:
            add_issue(
                issues,
                "error",
                "animation-canonical-prototype-unresolved",
                "animations",
                "Un prototype cité par l'autorité de corrections alpha est introuvable.",
                path=prototype,
                asset_id=f"animations:bam:{row['resref'].upper()}",
            )
            continue
        alpha_by_path[resolved].append(row)

    known_legacy_sources = [source for source, _target in path_pairs]
    known_legacy_sources.extend(
        str(item["from"]).replace("\\", "/").rstrip("/")
        for item in migration_data.get("deprecated_output_roots", [])
    )
    embedded_reference_count = 0
    embedded_reference_files: set[str] = set()
    unmapped_embedded_references: set[str] = set()
    text_suffixes = {".json", ".md", ".ps1", ".py", ".txt"}
    for path in (ROOT / "animations/runs").rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore").replace("\\", "/")
        matched = 0
        for source in known_legacy_sources:
            matched += text.count(source)
        if matched:
            embedded_reference_count += matched
            embedded_reference_files.add(repo_path(path))
        for match in re.findall(r"proto/[A-Za-z0-9_.-]+", text):
            if "..." in match:
                continue
            if not any(
                match.casefold() == source.casefold()
                or match.casefold().startswith((source + "/").casefold())
                or source.casefold().startswith((match + "/").casefold())
                for source in known_legacy_sources
            ):
                unmapped_embedded_references.add(match)
    if unmapped_embedded_references:
        add_issue(
            issues,
            "error",
            "animation-embedded-proto-reference-unmapped",
            "animations",
            "Un artefact animation contient un ancien chemin proto absent de l'adaptateur.",
            path=ANIMATION_PATH_MIGRATIONS,
            details={"references": sorted(unmapped_embedded_references, key=str.casefold)},
        )

    candidate_path = ROOT / "releases/BG2-HD-Upscale/manifests/animation-release-candidates.json"
    candidate_data = read_json(candidate_path)
    candidates = candidate_data["candidates"]
    selected = referenced_animation_runs(candidates)
    indexed_release_packs = 0
    historical_evidence_adapted: list[dict[str, str]] = []

    for candidate in candidates:
        area = candidate["area"].upper()
        pack = ROOT / candidate["source_pack"]
        qa_path = ROOT / candidate["qa_approval"]
        evidence_valid = True
        checks = (
            (pack / candidate["pack_manifest"], candidate["pack_manifest_sha256"], "pack manifest"),
            (pack / candidate["registry"], candidate["registry_sha256"], "registry"),
            (qa_path, candidate["qa_approval_sha256"], "QA approval"),
        )
        for path, expected, label in checks:
            if not path.is_file():
                evidence_valid = False
                add_issue(
                    issues,
                    "error",
                    "animation-candidate-evidence-missing",
                    "animations",
                    f"La preuve {label} du candidat {area} est absente.",
                    path=repo_path(path),
                    asset_id=f"animations:pack:{area}",
                )
            elif sha256_file(path) != expected.upper():
                evidence_valid = False
                add_issue(
                    issues,
                    "error",
                    "animation-candidate-evidence-hash-mismatch",
                    "animations",
                    f"La preuve {label} du candidat {area} ne correspond plus au hash approuvé.",
                    path=repo_path(path),
                    asset_id=f"animations:pack:{area}",
                )

        for reference in re.findall(
            r"(?:proto|animations/runs)/[^\s+;,)]+", candidate.get("source_run", "")
        ):
            reference = reference.rstrip(".")
            if resolve_migrated_reference(reference, path_pairs) is None:
                evidence_valid = False
                add_issue(
                    issues,
                    "error",
                    "animation-candidate-source-run-unresolved",
                    "animations",
                    "Un chemin de run cité par un candidat animation est introuvable.",
                    path=reference,
                    asset_id=f"animations:pack:{area}",
                )

        if qa_path.is_file():
            qa_approval = read_json(qa_path)
            for evidence in qa_approval.get("evidence", []):
                relative_evidence = str(evidence.get("path", "")).replace("\\", "/")
                expected_hash = str(evidence.get("sha256", "")).upper()
                evidence_path = ROOT / relative_evidence
                if evidence_path.is_file() and sha256_file(evidence_path) == expected_hash:
                    continue
                migration = historical_git_evidence.verify_reference(
                    relative_evidence,
                    expected_hash,
                )
                if migration is not None:
                    historical_evidence_adapted.append(
                        {
                            "area": area,
                            "path": relative_evidence,
                            "sha256": expected_hash,
                            "git_commit": migration["git_commit"],
                        }
                    )
                    continue
                evidence_valid = False
                add_issue(
                    issues,
                    "error",
                    "animation-qa-evidence-unresolved",
                    "animations",
                    "Une preuve citée par la QA scellée ne correspond ni au fichier courant ni à un blob Git borné.",
                    path=relative_evidence,
                    asset_id=f"animations:pack:{area}",
                )

        add_run(
            runs,
            default_run(
                run_key=f"animations-pack:{area}",
                domain="animations",
                run_id=f"release-pack-{area.lower()}",
                asset_ids=[f"animations:pack:{area}"],
                path=repo_path(pack),
                run_kind="area-animation-release-pack",
                descriptor_path=repo_path(pack / candidate["pack_manifest"]),
                result_state=str(candidate["approval_status"]),
                qa_state="approved",
                selection_state="release-candidate",
                selection_authority=repo_path(candidate_path),
                inputs_state="documented",
                outputs_state="present" if pack.is_dir() else "missing",
                provenance_state="verified" if evidence_valid else "incomplete",
                notes=(
                    f"registre v{candidate['registry_version']}; "
                    f"QA: {candidate['qa_approval']}"
                ),
            ),
        )
        indexed_release_packs += 1

    if historical_evidence_adapted:
        add_issue(
            issues,
            "info",
            "animation-historical-qa-evidence-adapted",
            "animations",
            "Les anciennes versions de catalogues citées par les QA scellées sont vérifiées contre leurs blobs Git exacts.",
            path="animations/index/qa-evidence-migrations.json",
            details={
                "evidence_reference_count": len(historical_evidence_adapted),
                "migrations": historical_evidence_adapted,
            },
        )

    physical = 0
    empty = 0
    qa_count = 0
    for run_dir in sorted((ROOT / "animations/runs").iterdir(), key=lambda path: path.name):
        if not run_dir.is_dir():
            continue
        physical += 1
        files = [path for path in run_dir.rglob("*") if path.is_file()]
        manifest_path = run_dir / "manifest.json"
        request_path = run_dir / "request.json"
        qa_path = run_dir / "qa-approval.json"
        manifest = read_json(manifest_path) if manifest_path.is_file() else {}
        request = read_json(request_path) if request_path.is_file() else {}
        qa = read_json(qa_path) if qa_path.is_file() else {}
        if qa:
            qa_count += 1
        asset_ids: list[str] = []
        run_path = repo_path(run_dir)
        migration = migration_by_target.get(run_path, {})
        asset_ids.extend(str(asset_id) for asset_id in migration.get("asset_ids", []))
        for resref in qa.get("accepted_resrefs", []):
            asset_ids.append(f"animations:bam:{str(resref).upper()}")
        for resref in manifest.get("timed_resources", []):
            asset_ids.append(f"animations:bam:{str(resref).upper()}")
        manifest_request = manifest.get("request", {})
        if isinstance(manifest_request, Mapping):
            for resref in manifest_request.get("resolved_resrefs", []):
                asset_ids.append(f"animations:bam:{str(resref).upper()}")
        for resource in manifest.get("resources", []):
            if isinstance(resource, Mapping) and resource.get("resref"):
                asset_ids.append(f"animations:bam:{str(resource['resref']).upper()}")
        targets = request.get("targets", [])
        if isinstance(targets, list):
            for target in targets:
                if isinstance(target, str):
                    asset_ids.append(f"animations:bam:{target.upper()}")
                elif isinstance(target, Mapping) and target.get("resref"):
                    asset_ids.append(f"animations:bam:{str(target['resref']).upper()}")
        selected_areas = selected.get(run_dir.name, [])
        if selected_areas:
            asset_ids.extend(f"animations:pack:{area}" for area in selected_areas)
        if not files:
            empty += 1
            add_issue(
                issues,
                "warning",
                "animation-empty-run-skeleton",
                "animations",
                "Ce squelette de run est vide et n'est référencé par aucune autorité.",
                path=repo_path(run_dir),
                run_id=run_dir.name,
                details={"policy": "conserver; candidat à suppression après confirmation"},
            )
        if qa:
            qa_checks = (
                (manifest_path, qa.get("run_manifest_sha256"), "run manifest"),
                (run_dir / "03_runtime_pack/manifest.json", qa.get("pack_manifest_sha256"), "pack manifest"),
                (run_dir / "03_runtime_pack/AreaAnimations-X4.registry", qa.get("registry_sha256"), "registry"),
            )
            for evidence_path, expected_hash, label in qa_checks:
                if not expected_hash:
                    continue
                if not evidence_path.is_file():
                    add_issue(
                        issues,
                        "error",
                        "animation-qa-evidence-missing",
                        "animations",
                        f"La preuve QA ({label}) est absente.",
                        path=repo_path(evidence_path),
                        run_id=run_dir.name,
                    )
                elif sha256_file(evidence_path) != str(expected_hash).upper():
                    add_issue(
                        issues,
                        "error",
                        "animation-qa-evidence-hash-mismatch",
                        "animations",
                        f"La preuve QA ({label}) ne correspond plus à l'approbation.",
                        path=repo_path(evidence_path),
                        run_id=run_dir.name,
                    )
            for review in qa.get("reviews", []):
                review_path = run_dir / review["file"]
                if not review_path.is_file():
                    add_issue(
                        issues,
                        "error",
                        "animation-qa-review-missing",
                        "animations",
                        "Un média de revue cité par la QA est absent.",
                        path=repo_path(review_path),
                        run_id=run_dir.name,
                    )
                elif sha256_file(review_path) != str(review["sha256"]).upper():
                    add_issue(
                        issues,
                        "error",
                        "animation-qa-review-hash-mismatch",
                        "animations",
                        "Un média de revue ne correspond plus à la preuve QA.",
                        path=repo_path(review_path),
                        run_id=run_dir.name,
                    )
        canonical_prototypes = alpha_by_path.get(run_path, [])
        descriptor = manifest_path if manifest_path.is_file() else request_path
        result = str(manifest.get("status", "empty" if not files else "unknown"))
        qa_state = str(qa.get("status", manifest.get("qa_status", "not-assessed")))
        if canonical_prototypes and not qa:
            qa_state = "validated"
        selection_state = "historical"
        selection_authority = ""
        if selected_areas:
            selection_state = "release-candidate"
            selection_authority = repo_path(candidate_path)
        elif qa:
            selection_state = "qa-approved"
            selection_authority = repo_path(qa_path)
        elif canonical_prototypes:
            selection_state = "canonical-prototype"
            selection_authority = repo_path(alpha_authority)
        migration_role = str(migration.get("role", ""))
        notes = f"Candidat(s) de zone: {';'.join(selected_areas)}" if selected_areas else ""
        if migration_role:
            migration_note = f"Migré depuis proto; rôle historique: {migration_role}"
            notes = f"{notes}; {migration_note}" if notes else migration_note
        add_run(
            runs,
            default_run(
                run_key=f"animations:{run_dir.name}",
                domain="animations",
                run_id=run_dir.name,
                asset_ids=asset_ids,
                path=run_path,
                run_kind="animation-prototype" if migration else "area-animation",
                descriptor_path=repo_path(descriptor) if descriptor.is_file() else "",
                recipe_path="request.json" if request_path.is_file() else "",
                result_state=result,
                qa_state=qa_state,
                selection_state=selection_state,
                selection_authority=selection_authority,
                inputs_state="documented" if request or manifest else "unknown",
                outputs_state="present" if files else "missing",
                provenance_state="verified" if qa else ("complete" if manifest and request else "partial"),
                legacy=bool(migration),
                notes=notes,
            ),
        )
    return {
        "approved_candidate_count": len(candidates),
        "empty_run_count": empty,
        "legacy_proto_directory_migration_count": len(migrations),
        "legacy_proto_embedded_reference_count": embedded_reference_count,
        "legacy_proto_embedded_reference_file_count": len(embedded_reference_files),
        "legacy_proto_loose_file_migration_count": len(loose_file_migrations),
        "legacy_proto_migrated_bytes": migrated_bytes,
        "legacy_proto_migrated_file_count": len(migrated_files),
        "legacy_proto_run_count": len(migration_by_target),
        "remaining_proto_directory_count": len(present_proto),
        "remaining_animation_proto_directory_count": len(unexpected_proto),
        "physical_run_count": physical,
        "qa_attested_run_count": qa_count,
        "historical_qa_evidence_adapted_count": len(historical_evidence_adapted),
        "release_pack_indexed_count": indexed_release_packs,
        "release_referenced_run_count": len(selected),
    }


def migration_pairs() -> list[tuple[str, str]]:
    data = read_json(ROOT / "sprite/index/path-migrations.json")
    pairs: list[tuple[str, str]] = []
    for item in data["migrations"]:
        source = str(item.get("from", item.get("legacy_job", ""))).replace("\\", "/").rstrip("/")
        target = str(item.get("to", item.get("location", ""))).replace("\\", "/").rstrip("/")
        if source and target:
            pairs.append((source, target))
    return sorted(pairs, key=lambda item: len(item[0]), reverse=True)


def resolve_migrated_reference(value: str, pairs: list[tuple[str, str]]) -> str | None:
    relative = normalize_repo_reference(value)
    if relative is None:
        return None
    if (ROOT / relative).exists():
        return relative
    folded = relative.casefold()
    for source, target in pairs:
        if folded == source.casefold() or folded.startswith((source + "/").casefold()):
            migrated = target + relative[len(source) :]
            if (ROOT / migrated).exists():
                return migrated
    return None


def sprite_family_lookup() -> dict[tuple[str, str], list[str]]:
    lookup: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in read_csv(ROOT / "sprite/index/sprite_families.csv"):
        key = (row["animation_id"].upper(), row["bam_prefix"].upper())
        lookup[key].append(f"sprites:family:{row['family_id']}")
    return lookup


def audit_sprites(
    issues: list[dict[str, Any]], runs: dict[str, dict[str, Any]]
) -> dict[str, int]:
    pairs = migration_pairs()
    layout = read_json(ROOT / "sprite/index/sprite-layout.json")
    for workspace in layout["workspaces"]:
        location = workspace["location"]
        if not (ROOT / location).is_dir():
            add_issue(
                issues,
                "error",
                "sprite-layout-location-missing",
                "sprites",
                "Une destination déclarée par l'index de layout est absente.",
                path=location,
            )

    pointer_path = ROOT / "sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/runs/catalog-xbr2x-x2/current-generation.json"
    pointer = read_json(pointer_path)
    current_generation = pointer["generation_dir"].replace("\\", "/").rstrip("/")
    current_job_path = ROOT / "sprite/catalogs/creature-x2-nearest/jobs/qa-refresh-current-catalog-v1.json"
    if not current_job_path.is_file() or sha256_file(current_job_path) != pointer["job_sha256"].upper():
        add_issue(
            issues,
            "error",
            "sprite-current-generation-job-mismatch",
            "sprites",
            "La recette historique de la génération active ne correspond plus au pointeur courant.",
            path=repo_path(current_job_path),
        )
    for relative_field, hash_field in (
        ("build_manifest", "build_manifest_sha256"),
        ("runtime_manifest", "runtime_manifest_sha256"),
    ):
        target = ROOT / current_generation / pointer[relative_field]
        if not target.is_file():
            add_issue(
                issues,
                "error",
                "sprite-current-generation-evidence-missing",
                "sprites",
                "Une preuve de la génération sprite courante est absente.",
                path=repo_path(target),
            )
        elif sha256_file(target) != pointer[hash_field].upper():
            add_issue(
                issues,
                "error",
                "sprite-current-generation-hash-mismatch",
                "sprites",
                "Une preuve de la génération sprite courante ne correspond plus à son pointeur.",
                path=repo_path(target),
            )

    lookup = sprite_family_lookup()
    build_files = sorted((ROOT / "sprite").rglob("build-manifest.json"), key=lambda path: repo_path(path))
    selected_builds = 0
    migrated_recipe_count = 0
    immutable_snapshot_count = 0
    for manifest_path in build_files:
        data = read_json(manifest_path)
        run_dir = manifest_path.parent.parent if manifest_path.parent.name == "build" else manifest_path.parent
        run_path = repo_path(run_dir)
        animation_ids = data.get("animation_ids", [])
        if not animation_ids and data.get("animation_id"):
            animation_ids = [data["animation_id"]]
        prefixes: list[str] = []
        if data.get("bam_prefix"):
            prefixes.append(str(data["bam_prefix"]))
        asset_ids: list[str] = []
        for animation_id in animation_ids:
            if prefixes:
                for prefix in prefixes:
                    asset_ids.extend(lookup.get((str(animation_id).upper(), prefix.upper()), []))
            else:
                for (candidate_animation, _), ids in lookup.items():
                    if candidate_animation == str(animation_id).upper():
                        asset_ids.extend(ids)
        selected_run = run_path.casefold() == current_generation.casefold()
        if selected_run:
            selected_builds += 1
        recipe_path = str(data.get("job_file", data.get("source_manifest", "")))
        resolved_recipe = resolve_migrated_reference(recipe_path, pairs) if recipe_path else None
        if recipe_path and resolved_recipe and resolved_recipe.casefold() != normalize_repo_reference(recipe_path).casefold():
            migrated_recipe_count += 1
        if recipe_path and not resolved_recipe:
            add_issue(
                issues,
                "warning",
                "sprite-build-recipe-unresolved",
                "sprites",
                "La recette/source d'un build historique ne peut pas être résolue.",
                path=repo_path(manifest_path),
                run_id=str(data.get("generation_id", data.get("job_id", run_dir.name))),
                details={"reference": recipe_path},
            )
        if data.get("source_manifest") and data.get("source_manifest_sha256") and resolved_recipe:
            if sha256_file(ROOT / resolved_recipe) != str(data["source_manifest_sha256"]).upper():
                add_issue(
                    issues,
                    "error",
                    "sprite-source-manifest-hash-mismatch",
                    "sprites",
                    "Le manifest source d'un build ne correspond plus à son empreinte.",
                    path=resolved_recipe,
                    run_id=str(data.get("generation_id", data.get("job_id", run_dir.name))),
                )
        if data.get("job_file") and data.get("job_sha256") and resolved_recipe:
            live_job_matches = sha256_file(ROOT / resolved_recipe) == str(data["job_sha256"]).upper()
            snapshot_relative = data.get("job_snapshot")
            snapshot_hash = data.get("job_snapshot_sha256")
            snapshot_matches = False
            if snapshot_relative or snapshot_hash:
                snapshot_path = manifest_path.parent / str(snapshot_relative or "")
                snapshot_matches = bool(
                    snapshot_relative
                    and snapshot_hash
                    and snapshot_path.is_file()
                    and sha256_file(snapshot_path) == str(snapshot_hash).upper() == str(data["job_sha256"]).upper()
                )
                if snapshot_matches:
                    immutable_snapshot_count += 1
                else:
                    add_issue(
                        issues,
                        "error",
                        "sprite-job-snapshot-invalid",
                        "sprites",
                        "Le snapshot immuable déclaré d'une recette sprite est invalide.",
                        path=repo_path(manifest_path),
                        run_id=str(data.get("generation_id", data.get("job_id", run_dir.name))),
                    )
            if not live_job_matches and not snapshot_matches:
                add_issue(
                    issues,
                    "warning",
                    "sprite-historical-live-job-diverged",
                    "sprites",
                    "Le job mutable a divergé du build historique, sans snapshot prévu par cet ancien contrat.",
                    path=resolved_recipe,
                    run_id=str(data.get("generation_id", data.get("job_id", run_dir.name))),
                    details={"policy": "ne pas réécrire le build historique; les nouveaux builds scellent un snapshot"},
                )
        add_run(
            runs,
            default_run(
                run_key=f"sprites:{run_path}",
                domain="sprites",
                run_id=str(data.get("generation_id", data.get("job_id", run_dir.name))),
                asset_ids=asset_ids,
                path=run_path,
                run_kind="sprite-build",
                descriptor_path=repo_path(manifest_path),
                recipe_path=resolved_recipe or recipe_path,
                result_state=str(data.get("status", "unknown")),
                qa_state="pending" if "pending" in str(data.get("status", "")) else "unknown",
                selection_state="current-generation" if selected_run else "historical",
                selection_authority=repo_path(pointer_path) if selected_run else "",
                inputs_state="verified" if data.get("source_manifest_sha256") or data.get("job_sha256") else "documented",
                outputs_state="present",
                provenance_state="verified" if data.get("job_sha256") or data.get("source_manifest_sha256") else "partial",
                notes="Agrégat catalogue" if not prefixes and len(animation_ids) > 1 else "",
            ),
        )

    active_tests = sorted((ROOT / "sprite").rglob("active-test.json"), key=lambda path: repo_path(path))
    canonical_active = current_generation.rsplit("/generations/", 1)[0] + "/ingame-installation/active-test.json"
    canonical_active_path = ROOT / canonical_active
    if not canonical_active_path.is_file():
        add_issue(
            issues,
            "error",
            "sprite-current-installation-pointer-missing",
            "sprites",
            "Le pointeur d'installation du catalogue courant est absent.",
            path=canonical_active,
        )
    else:
        active_state = read_json(canonical_active_path)
        if str(active_state.get("generation_id", "")).upper() != str(pointer["generation_id"]).upper():
            add_issue(
                issues,
                "error",
                "sprite-current-installation-generation-mismatch",
                "sprites",
                "Le pointeur d'installation et current-generation.json désignent des générations différentes.",
                path=canonical_active,
            )
        backup_root = normalize_repo_reference(str(active_state.get("backup_root", "")))
        if not backup_root or not (ROOT / backup_root).is_dir():
            add_issue(
                issues,
                "error",
                "sprite-current-installation-backup-missing",
                "sprites",
                "La chaîne de restauration de l'installation sprite courante est absente.",
                path=str(active_state.get("backup_root", "")),
            )
    migrated_historic = 0
    unresolved_historic = 0
    noncanonical_installed = 0
    for active_path in active_tests:
        path_text = repo_path(active_path)
        data = read_json(active_path)
        if path_text.casefold() == canonical_active.casefold():
            continue
        if str(data.get("status", "")).startswith("installed"):
            noncanonical_installed += 1
        references = [str(data.get(key, "")) for key in ("job_file", "backup_root") if data.get(key)]
        unresolved = [value for value in references if resolve_migrated_reference(value, pairs) is None]
        if unresolved:
            unresolved_historic += 1
            add_issue(
                issues,
                "warning",
                "sprite-historical-pointer-unresolved",
                "sprites",
                "Un pointeur d'installation historique ne peut pas être résolu par path-migrations.json.",
                path=path_text,
                details={"unresolved_references": unresolved},
            )
        else:
            migrated_historic += 1

    if migrated_historic:
        add_issue(
            issues,
            "info",
            "sprite-historical-pointers-migrated",
            "sprites",
            "Les pointeurs historiques restent en place et sont résolus par l'adaptateur de migration.",
            path="sprite/index/path-migrations.json",
            details={
                "pointer_count": migrated_historic,
                "noncanonical_installed_status_count": noncanonical_installed,
                "policy": "seul le pointeur catalogue courant décrit l'installation active",
            },
        )
    return {
        "build_manifest_count": len(build_files),
        "canonical_active_test_count": 1,
        "current_generation_count": selected_builds,
        "historical_active_test_count": len(active_tests) - 1,
        "historical_pointer_resolved_count": migrated_historic,
        "historical_pointer_unresolved_count": unresolved_historic,
        "immutable_job_snapshot_count": immutable_snapshot_count,
        "migrated_build_recipe_count": migrated_recipe_count,
    }


def audit_workspace_cleanup(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify Phase 6 destinations without treating the evidence as domain authority."""

    manifest_path = ROOT / CLEANUP_MANIFEST
    data = read_json(manifest_path)
    verified = 0
    moved_files = 0
    moved_bytes = 0
    removed_empty = 0
    for operation in data.get("operations", []):
        target_text = str(operation.get("target", ""))
        action = operation["action"]
        if action == "remove-empty-directory":
            source = ROOT / operation["source_roots"][0]
            if source.exists():
                add_issue(
                    issues,
                    "error",
                    "cleanup-empty-directory-returned",
                    operation["domain"],
                    "Le squelette de run prouvé vide est réapparu.",
                    path=repo_path(source),
                )
            else:
                verified += 1
                removed_empty += 1
            continue
        target = ROOT / target_text
        if not target.is_dir():
            add_issue(
                issues,
                "error",
                "cleanup-target-missing",
                operation["domain"],
                "Une destination de nettoyage documentée est absente.",
                path=target_text,
            )
            continue
        files = [path for path in target.rglob("*") if path.is_file()]
        actual_bytes = sum(path.stat().st_size for path in files)
        expected_count = int(operation["file_count"])
        expected_bytes = int(operation["bytes"])
        if len(files) != expected_count or actual_bytes != expected_bytes:
            add_issue(
                issues,
                "error",
                "cleanup-target-inventory-changed",
                operation["domain"],
                "Le contenu d'une destination de nettoyage ne correspond plus à la preuve de migration.",
                path=target_text,
                details={
                    "actual_bytes": actual_bytes,
                    "actual_file_count": len(files),
                    "expected_bytes": expected_bytes,
                    "expected_file_count": expected_count,
                },
            )
            continue
        verified += 1
        moved_files += len(files)
        moved_bytes += actual_bytes

    return {
        "manifest": CLEANUP_MANIFEST,
        "operation_count": len(data.get("operations", [])),
        "verified_operation_count": verified,
        "preserved_file_count": moved_files,
        "preserved_bytes": moved_bytes,
        "removed_empty_directory_count": removed_empty,
        "deferred_regeneration_count": len(data.get("deferred", [])),
    }


def audit_workspace_archive_p2(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify the targeted P2 archive and exact duplicate removals."""

    data = read_json(ROOT / ARCHIVE_P2_MANIFEST)
    verified_operations = 0
    archived_files = 0
    archived_bytes = 0
    for operation in data.get("operations", []):
        source_text = str(operation["source"])
        target_text = str(operation["target"])
        source = ROOT / source_text
        target = ROOT / target_text
        valid = True
        if source.exists():
            valid = False
            add_issue(
                issues,
                "error",
                "archive-p2-source-returned",
                str(operation["domain"]),
                "Un élément archivé en P2 est réapparu dans une zone active.",
                path=source_text,
            )
        if not target.exists():
            valid = False
            add_issue(
                issues,
                "error",
                "archive-p2-target-missing",
                str(operation["domain"]),
                "Une destination d'archive P2 est absente.",
                path=target_text,
            )
        else:
            actual_count, actual_bytes, actual_hash = inventory_evidence(target)
            expected_count = int(operation["file_count"])
            expected_bytes = int(operation["bytes"])
            expected_hash = str(operation["aggregate_sha256"]).upper()
            if (
                actual_count != expected_count
                or actual_bytes != expected_bytes
                or actual_hash != expected_hash
            ):
                valid = False
                add_issue(
                    issues,
                    "error",
                    "archive-p2-target-evidence-mismatch",
                    str(operation["domain"]),
                    "Une archive P2 ne correspond plus à son inventaire hashé.",
                    path=target_text,
                    details={
                        "actual_file_count": actual_count,
                        "actual_bytes": actual_bytes,
                        "actual_aggregate_sha256": actual_hash,
                        "expected_file_count": expected_count,
                        "expected_bytes": expected_bytes,
                        "expected_aggregate_sha256": expected_hash,
                    },
                )
        if valid:
            verified_operations += 1
            archived_files += int(operation["file_count"])
            archived_bytes += int(operation["bytes"])

    verified_duplicate_groups = 0
    duplicate_files = 0
    duplicate_bytes = 0
    for group in data.get("exact_duplicate_removals", []):
        valid = True
        source_root = str(group["source_root"]).rstrip("/")
        virtual_records: list[tuple[str, int, str]] = []
        for item in group.get("files", []):
            source_text = str(item["source"])
            canonical_text = str(item["canonical"])
            expected_bytes = int(item["bytes"])
            expected_hash = str(item["sha256"]).upper()
            if (ROOT / source_text).exists():
                valid = False
                add_issue(
                    issues,
                    "error",
                    "archive-p2-exact-duplicate-returned",
                    "animations",
                    "Une copie AR0602 supprimée après preuve d'identité est réapparue.",
                    path=source_text,
                )
            canonical = ROOT / canonical_text
            if (
                not canonical.is_file()
                or canonical.stat().st_size != expected_bytes
                or sha256_file(canonical) != expected_hash
            ):
                valid = False
                add_issue(
                    issues,
                    "error",
                    "archive-p2-canonical-duplicate-evidence-missing",
                    "animations",
                    "La copie canonique justifiant une déduplication AR0602 est absente ou divergente.",
                    path=canonical_text,
                )
            prefix = source_root + "/"
            if not source_text.startswith(prefix):
                valid = False
                relative = source_text
            else:
                relative = source_text[len(prefix) :]
            virtual_records.append((relative, expected_bytes, expected_hash))

        virtual_records.sort(key=lambda item: item[0].casefold())
        payload = "".join(
            f"{relative}|{size}|{digest}\n"
            for relative, size, digest in virtual_records
        ).encode("utf-8")
        actual_group_hash = hashlib.sha256(payload).hexdigest().upper()
        if (
            len(virtual_records) != int(group["file_count"])
            or sum(size for _relative, size, _digest in virtual_records)
            != int(group["bytes"])
            or actual_group_hash != str(group["aggregate_sha256"]).upper()
        ):
            valid = False
            add_issue(
                issues,
                "error",
                "archive-p2-duplicate-manifest-inconsistent",
                "animations",
                "La preuve de déduplication P2 est incohérente avec sa propre liste de fichiers.",
                path=ARCHIVE_P2_MANIFEST,
                details={"group": group.get("id", "")},
            )
        if valid:
            verified_duplicate_groups += 1
            duplicate_files += int(group["file_count"])
            duplicate_bytes += int(group["bytes"])

    return {
        "manifest": ARCHIVE_P2_MANIFEST,
        "operation_count": len(data.get("operations", [])),
        "verified_operation_count": verified_operations,
        "archived_file_count": archived_files,
        "archived_bytes": archived_bytes,
        "exact_duplicate_group_count": len(data.get("exact_duplicate_removals", [])),
        "verified_exact_duplicate_group_count": verified_duplicate_groups,
        "exact_duplicate_removed_file_count": duplicate_files,
        "exact_duplicate_removed_bytes": duplicate_bytes,
        "left_in_place_count": len(data.get("left_in_place", [])),
    }


def audit_animation_pack_archive_p3(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate the P3 pack lifecycle without freezing future control-plane updates."""

    manifest_path = ROOT / ANIMATION_PACK_P3_MANIFEST
    if not manifest_path.is_file():
        add_issue(
            issues,
            "error",
            "animation-pack-p3-manifest-missing",
            "animations",
            "Le reçu de cycle de vie P3 des packs d'animations est absent.",
            path=ANIMATION_PACK_P3_MANIFEST,
        )
        return {
            "manifest": ANIMATION_PACK_P3_MANIFEST,
            "pack_count": 0,
            "keep_active_count": 0,
            "archive_count": 0,
            "delete_safe_count": 0,
            "uncertain_count": 0,
            "verified": False,
        }

    data = read_json(manifest_path)
    errors = animation_pack_cleanup.check(verify_control_plane=False)
    for message in errors:
        add_issue(
            issues,
            "error",
            "animation-pack-p3-drift",
            "animations",
            "Le rangement P3 des packs d'animations a dérivé.",
            path="animations/packs-par-zone",
            details={"error": message},
        )
    summary = data["summary"]
    return {
        "manifest": ANIMATION_PACK_P3_MANIFEST,
        "pack_count": int(summary["pack_count"]),
        "keep_active_count": int(summary["keep_active_count"]),
        "archive_count": int(summary["archive_count"]),
        "delete_safe_count": int(summary["delete_safe_count"]),
        "uncertain_count": int(summary["uncertain_count"]),
        "original_file_count": int(summary["original_file_count"]),
        "original_bytes": int(summary["original_bytes"]),
        "reclaimed_bytes": int(summary["expected_reclaimed_bytes"]),
        "verified": not errors,
    }


def audit_workspace_legacy_p4(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify P4 technical classifications and archived script bytes."""

    data = read_json(ROOT / LEGACY_P4_MANIFEST)
    classifications = data.get("classifications", {})
    valid = True
    for classification in ("KEEP_ACTIVE", "KEEP_COMPAT"):
        for entry in classifications.get(classification, []):
            path_text = str(entry["path"])
            if not (ROOT / path_text).is_file():
                valid = False
                add_issue(
                    issues,
                    "error",
                    "legacy-p4-required-tool-missing",
                    "workspace",
                    "Un outil actif ou de compatibilité conservé en P4 est absent.",
                    path=path_text,
                    details={"classification": classification},
                )

    archived_bytes = 0
    verified_archives = 0
    for entry in classifications.get("ARCHIVE", []):
        source_text = str(entry["source"])
        target_text = str(entry["target"])
        source = ROOT / source_text
        target = ROOT / target_text
        entry_valid = True
        if source.exists():
            entry_valid = False
            add_issue(
                issues,
                "error",
                "legacy-p4-source-returned",
                "workspace",
                "Un outil technique archivé en P4 est réapparu dans la zone active.",
                path=source_text,
            )
        expected_bytes = int(entry["bytes"])
        expected_hash = str(entry["sha256"]).upper()
        if (
            not target.is_file()
            or target.stat().st_size != expected_bytes
            or sha256_file(target) != expected_hash
        ):
            entry_valid = False
            add_issue(
                issues,
                "error",
                "legacy-p4-archive-evidence-mismatch",
                "workspace",
                "Un outil technique archivé en P4 est absent ou divergent.",
                path=target_text,
            )
        if entry_valid:
            verified_archives += 1
            archived_bytes += expected_bytes
        valid = valid and entry_valid

    summary = data.get("summary", {})
    actual_counts = {
        "keep_active_count": len(classifications.get("KEEP_ACTIVE", [])),
        "keep_compat_count": len(classifications.get("KEEP_COMPAT", [])),
        "archive_count": len(classifications.get("ARCHIVE", [])),
        "delete_safe_count": len(classifications.get("DELETE_SAFE", [])),
        "archived_bytes": sum(
            int(entry["bytes"]) for entry in classifications.get("ARCHIVE", [])
        ),
    }
    if any(int(summary.get(key, -1)) != value for key, value in actual_counts.items()):
        valid = False
        add_issue(
            issues,
            "error",
            "legacy-p4-manifest-summary-mismatch",
            "workspace",
            "Le résumé du manifeste de legacy technique P4 est incohérent.",
            path=LEGACY_P4_MANIFEST,
        )

    return {
        "manifest": LEGACY_P4_MANIFEST,
        **actual_counts,
        "verified_archive_count": verified_archives,
        "verified_archived_bytes": archived_bytes,
        "verified": valid,
    }


def audit_video_runs(
    issues: list[dict[str, Any]], runs: dict[str, dict[str, Any]]
) -> dict[str, int]:
    data = read_json(ROOT / CLEANUP_MANIFEST)
    movie_asset_ids = [
        "videos:" + row["asset_key"].replace(":", "-").lower()
        for row in read_csv(ROOT / "video/index/resources.csv")
        if row["asset_key"].startswith("movie:")
    ]
    physical = 0
    for operation in data.get("operations", []):
        if operation.get("domain") != "videos" or operation.get("action") != "move":
            continue
        physical += 1
        path_text = str(operation["target"])
        asset_ids = operation.get("asset_ids") or movie_asset_ids
        add_run(
            runs,
            default_run(
                run_key=f"videos:{operation['id']}",
                domain="videos",
                run_id=str(operation["id"]),
                asset_ids=asset_ids,
                path=path_text,
                run_kind="historical-video-work-products",
                descriptor_path=CLEANUP_MANIFEST,
                result_state=str(operation["status"]),
                qa_state="not-assessed",
                selection_state="historical-unselected",
                selection_authority="",
                inputs_state="documented",
                outputs_state="present" if (ROOT / path_text).is_dir() else "missing",
                provenance_state="verified-move",
                legacy=True,
                notes=str(operation.get("notes", "")),
            ),
        )
    return {
        "physical_run_count": physical,
        "selected_run_count": 0,
        "canonical_source_count": len(read_csv(ROOT / "video/index/resources.csv")),
    }


def audit_path_portability(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Check active code and grandfathered descriptors without rewriting history."""

    config = read_json(ROOT / "config/workspace-paths.json")
    configured = 0
    missing = 0
    unconfigured = 0
    path_states: dict[str, str] = {}
    for key in sorted(config["paths"]):
        path = workspace_paths.get_path(key)
        if ".unconfigured" in path.parts:
            unconfigured += 1
            path_states[key] = "unconfigured"
            add_issue(
                issues,
                "warning",
                "active-path-unconfigured",
                "global",
                "Un chemin machine actif n'est configuré ni localement ni par variable d'environnement.",
                path=f"config://{key}",
                details={"environment": config["paths"][key]["environment"]},
            )
        elif not path.exists():
            missing += 1
            path_states[key] = "missing"
            add_issue(
                issues,
                "error",
                "active-path-missing",
                "global",
                "Un chemin machine actif configuré n'existe pas.",
                path=f"config://{key}",
                details={"resolved_path": str(path)},
            )
        else:
            configured += 1
            path_states[key] = "available"
            for marker in config["paths"][key].get("markers", []):
                if not (path / marker).exists():
                    add_issue(
                        issues,
                        "error",
                        "active-path-marker-missing",
                        "global",
                        "Un répertoire machine configuré ne contient pas son marqueur attendu.",
                        path=f"config://{key}",
                        details={"marker": marker, "resolved_path": str(path)},
                    )

    active_roots = (
        ROOT / "pipeline/scripts",
        ROOT / "engine/InfinityEngine-Enhancer/source-patchee/tools",
        ROOT / "interface",
        ROOT / "maps/technical-overlays",
        ROOT / "releases/BG2-HD-Upscale/tools",
        ROOT / "releases/BG2-HD-Upscale/tests",
    )
    historical_script_exceptions: set[str] = set()
    active_violations: list[str] = []
    retained_script_exceptions: list[str] = []
    scanned_active_script_count = 0
    active_script_paths: set[Path] = {
        path
        for path in ROOT.iterdir()
        if path.is_file() and path.suffix.casefold() in ACTIVE_SCRIPT_SUFFIXES
    }
    for root in active_roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.casefold() not in ACTIVE_SCRIPT_SUFFIXES:
                continue
            active_script_paths.add(path)
    for path in sorted(active_script_paths, key=lambda item: repo_path(item).casefold()):
        relative_parts = {part.casefold() for part in path.relative_to(ROOT).parts}
        if "archive" in relative_parts or "runs" in relative_parts:
            continue
        scanned_active_script_count += 1
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if not WINDOWS_ABSOLUTE_PATH_LITERAL.search(text):
            continue
        path_text = repo_path(path)
        if path_text in historical_script_exceptions:
            retained_script_exceptions.append(path_text)
        else:
            active_violations.append(path_text)
    if active_violations:
        add_issue(
            issues,
            "error",
            "active-script-absolute-path",
            "global",
            "Un script actif contient un nouveau chemin machine absolu interdit.",
            path="config/workspace-paths.json",
            details={"files": sorted(set(active_violations), key=str.casefold)},
        )

    baseline_path = ROOT / "config/historical-absolute-paths.json"
    baseline = set(read_json(baseline_path)["historical_files"])
    current_historical: set[str] = set()
    for path in (ROOT / "sprite").rglob("*.json"):
        path_text = repo_path(path)
        if "jobs" not in {part.casefold() for part in path.parts} and path_text not in baseline:
            continue
        if WINDOWS_ABSOLUTE_PATH_LITERAL.search(
            path.read_text(encoding="utf-8-sig", errors="ignore")
        ):
            current_historical.add(path_text)
    new_historical = sorted(current_historical - baseline, key=str.casefold)
    if new_historical:
        add_issue(
            issues,
            "error",
            "new-descriptor-absolute-path",
            "sprites",
            "Un nouveau descripteur contient un chemin machine absolu au lieu d'une référence config://.",
            path="sprite/",
            details={"files": new_historical},
        )
    if current_historical or retained_script_exceptions:
        add_issue(
            issues,
            "info",
            "historical-absolute-paths-adapted",
            "global",
            "Les chemins absolus historiques restent inchangés et sont explicitement bornés.",
            path="config/historical-absolute-paths.json",
            details={
                "descriptor_file_count": len(current_historical),
                "script_exceptions": sorted(retained_script_exceptions, key=str.casefold),
                "policy": "les runners résolvent config://; les artefacts historiques ne sont pas réécrits",
            },
        )
    return {
        "configured_path_count": configured,
        "missing_path_count": missing,
        "unconfigured_path_count": unconfigured,
        "path_states": path_states,
        "active_script_file_count": scanned_active_script_count,
        "active_absolute_path_violation_count": len(set(active_violations)),
        "historical_descriptor_file_count": len(current_historical),
        "historical_script_exception_count": len(retained_script_exceptions),
        "new_historical_absolute_path_file_count": len(new_historical),
    }


def workspace_hygiene(issues: list[dict[str, Any]]) -> dict[str, int]:
    temp_root = ROOT / "temp"
    temp_files = [path for path in temp_root.rglob("*") if path.is_file()] if temp_root.is_dir() else []
    if temp_files:
        add_issue(
            issues,
            "info",
            "workspace-temporary-files",
            "global",
            "Des temporaires restent hors des zones canoniques et ne sont pas utilisés comme autorité.",
            path="temp/",
            details={
                "file_count": len(temp_files),
                "policy": "candidat à revue puis suppression; aucune suppression automatique",
            },
        )
    empty_map_animations = [
        path
        for path in (ROOT / "maps").glob("*/animations")
        if path.is_dir() and not any(path.iterdir())
    ]
    empty_map_runs = [
        path
        for path in (ROOT / "maps").glob("*/runs")
        if path.is_dir() and not any(path.iterdir())
    ]
    empty_temp_directories = (
        [
            path
            for path in temp_root.rglob("*")
            if path.is_dir() and not any(path.iterdir())
        ]
        if temp_root.is_dir()
        else []
    )
    personal_shortcuts = list(ROOT.glob("*.lnk")) + list((ROOT / "maps").rglob("*.lnk"))
    stale_alpha5 = (
        ROOT
        / "releases/BG2-HD-Upscale/release-inputs/renderer/iee-0.1.0-alpha.5"
    ).is_dir()
    retired_scan_script = (ROOT / "pipeline/scripts/scan_mos_versions.py").is_file()
    obsolete_count = (
        len(empty_map_animations)
        + len(empty_map_runs)
        + len(empty_temp_directories)
        + len(personal_shortcuts)
        + int(stale_alpha5)
        + int(retired_scan_script)
    )
    if obsolete_count:
        add_issue(
            issues,
            "warning",
            "workspace-safe-cleanup-targets-present",
            "global",
            "Des cibles P1 vides, personnelles ou remplacées sont revenues dans le workspace.",
            path=".",
            details={
                "empty_map_animation_directories": len(empty_map_animations),
                "empty_map_run_directories": len(empty_map_runs),
                "empty_temp_directories": len(empty_temp_directories),
                "personal_shortcuts": sorted(repo_path(path) for path in personal_shortcuts),
                "retired_scan_script_present": retired_scan_script,
                "stale_alpha5_worktree_present": stale_alpha5,
            },
        )
    return {
        "temporary_file_count": len(temp_files),
        "empty_map_animation_directory_count": len(empty_map_animations),
        "empty_map_run_directory_count": len(empty_map_runs),
        "empty_temp_directory_count": len(empty_temp_directories),
        "personal_shortcut_count": len(personal_shortcuts),
        "obsolete_p1_target_count": obsolete_count,
        "retired_scan_script_present": int(retired_scan_script),
        "stale_alpha5_worktree_present": int(stale_alpha5),
    }


def runs_csv_bytes(records: Iterable[Mapping[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=RUN_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    for record in records:
        row = dict(record)
        row["asset_ids"] = " | ".join(record["asset_ids"])
        row["legacy"] = "yes" if record["legacy"] else "no"
        writer.writerow({column: row[column] for column in RUN_COLUMNS})
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


def build_outputs(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise ValueError("This audit currently targets the repository containing the script.")
    issues: list[dict[str, Any]] = []
    runs: dict[str, dict[str, Any]] = {}
    registry, canonical_counts = audit_registry(issues)
    sources = audit_source_tables(issues, canonical_counts)
    cleanup = audit_workspace_cleanup(issues)
    archive_p2 = audit_workspace_archive_p2(issues)
    animation_packs_p3 = audit_animation_pack_archive_p3(issues)
    legacy_p4 = audit_workspace_legacy_p4(issues)
    portability = audit_path_portability(issues)
    domain_audits = {
        "maps": audit_maps(issues, runs),
        "animations": audit_animations(issues, runs),
        "portraits": audit_portraits(issues),
        "sprites": audit_sprites(issues, runs),
        "videos": audit_video_runs(issues, runs),
        "workspace_cleanup": cleanup,
        "workspace_archive_p2": archive_p2,
        "animation_pack_archive_p3": animation_packs_p3,
        "workspace_legacy_p4": legacy_p4,
        "path_portability": portability,
    }
    hygiene = workspace_hygiene(issues)
    domain_audits["workspace_hygiene"] = hygiene

    sorted_runs = sorted(runs.values(), key=lambda item: item["run_key"].casefold())
    sorted_issues = sorted(
        issues,
        key=lambda item: (
            {"error": 0, "warning": 1, "info": 2}[item["severity"]],
            item["domain"],
            item["code"],
            item.get("path", ""),
        ),
    )
    severity_counts = Counter(issue["severity"] for issue in sorted_issues)
    code_counts = Counter(issue["code"] for issue in sorted_issues)
    run_domain_counts = Counter(record["domain"] for record in sorted_runs)
    selection_counts = Counter(record["selection_state"] for record in sorted_runs)
    input_fingerprint = hashlib.sha256(json_bytes(registry["inputs"])).hexdigest().upper()
    run_records_hash = hashlib.sha256(json_bytes(sorted_runs)).hexdigest().upper()

    run_index = {
        "schema": RUN_INDEX_SCHEMA,
        "generated_by": GENERATOR,
        "authority_policy": "generated read-only projection; never edit or consume as a domain authority",
        "selection_policy": "selection remains in external canonical manifests or pointers",
        "source_fingerprint_sha256": input_fingerprint,
        "run_count": len(sorted_runs),
        "run_records_sha256": run_records_hash,
        "summary": {
            "by_domain": dict(sorted(run_domain_counts.items())),
            "by_selection_state": dict(sorted(selection_counts.items())),
        },
        "runs": sorted_runs,
    }
    integrity = {
        "schema": INTEGRITY_SCHEMA,
        "generated_by": GENERATOR,
        "mode": "read-only audit; only this generated report and the generated run index are writable",
        "registry_asset_count": registry["asset_count"],
        "registry_asset_records_sha256": registry["asset_records_sha256"],
        "source_fingerprint_sha256": input_fingerprint,
        "run_count": len(sorted_runs),
        "run_records_sha256": run_records_hash,
        "summary": {
            "by_issue_code": dict(sorted(code_counts.items())),
            "by_severity": {severity: severity_counts.get(severity, 0) for severity in ("error", "warning", "info")},
            "candidate_cleanup": {
                "animation_empty_run_skeletons": code_counts.get("animation-empty-run-skeleton", 0),
                "map_incomplete_intermediate_runs": code_counts.get("map-run-referenced-files-missing", 0),
                "map_source_experiment_files": domain_audits["maps"]["extra_source_file_count"],
                "sprite_historical_diverged_jobs": code_counts.get("sprite-historical-live-job-diverged", 0),
                "temporary_files": hygiene["temporary_file_count"],
                "video_unindexed_work_products": next(
                    (item["extra_file_count"] for item in sources if item["authority"] == "video/index/resources.csv"),
                    0,
                ),
            },
        },
        "domain_audits": domain_audits,
        "source_audits": sources,
        "issues": sorted_issues,
    }
    return {"workspace-integrity.json": integrity, "runs.json": run_index, RUN_CSV: sorted_runs}


def rendered_outputs(outputs: Mapping[str, Any]) -> dict[str, bytes]:
    return {
        "workspace-integrity.json": json_bytes(outputs["workspace-integrity.json"]),
        "runs.json": json_bytes(outputs["runs.json"]),
        RUN_CSV: runs_csv_bytes(outputs[RUN_CSV]),
    }


def write_outputs(outputs: Mapping[str, Any], output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in rendered_outputs(outputs).items():
        (output_dir / name).write_bytes(content)


def check_outputs(outputs: Mapping[str, Any], output_dir: Path = OUTPUT_DIR) -> list[str]:
    errors: list[str] = []
    for name, expected in rendered_outputs(outputs).items():
        path = output_dir / name
        if not path.is_file():
            errors.append(f"missing generated output: {repo_path(path)}")
        elif path.read_bytes() != expected:
            errors.append(f"stale generated output: {repo_path(path)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check generated outputs without writing.")
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="Build twice in memory and require byte-identical outputs before writing.",
    )
    args = parser.parse_args()
    outputs = build_outputs(ROOT)
    if args.verify_determinism:
        second = build_outputs(ROOT)
        if rendered_outputs(outputs) != rendered_outputs(second):
            print("ERROR: non-deterministic workspace integrity projection", file=sys.stderr)
            return 1
    if args.check:
        errors = check_outputs(outputs)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
    else:
        write_outputs(outputs)
    report = outputs["workspace-integrity.json"]
    counts = report["summary"]["by_severity"]
    print(
        f"workspace integrity: {report['registry_asset_count']} assets, "
        f"{report['run_count']} runs, {counts['error']} errors, "
        f"{counts['warning']} warnings, {counts['info']} infos"
    )
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
