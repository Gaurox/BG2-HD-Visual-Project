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
RESTORATION_MANIFEST = "docs/workspace-restoration-manifest.json"
VIDEO_SELECTION = "video/index/processing.csv"
ARCHIVE_P2_MANIFEST = "docs/workspace-archive-p2-manifest.json"
ANIMATION_PACK_P3_MANIFEST = "docs/workspace-animation-packs-p3-manifest.json"
LEGACY_P4_MANIFEST = "docs/workspace-legacy-p4-manifest.json"
BACKUPS_P5_MANIFEST = "docs/workspace-backups-p5-manifest.json"
ANIMATION_RUN_REFERENCE_RE = re.compile(
    r"animations/(?:"
    r"ressources/[A-Z0-9_]{1,8}/runs/[A-Za-z0-9][A-Za-z0-9._-]*"
    r"|batches/[A-Za-z0-9][A-Za-z0-9._-]*"
    r"|runs/[A-Za-z0-9][A-Za-z0-9._-]*"
    r")",
    re.IGNORECASE,
)
ANIMATION_RESREF_RE = re.compile(r"^(?=.*[A-Z0-9])[A-Z0-9_]{1,8}$")
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
        # Video derivatives belong in video/<asset>/runs and are audited separately.
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
                        "policy": "ranger dans video/<asset>/runs avec une preuve de rattachement",
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
    """Vérifie l'autorité logique, les vues d'usage et le corpus PPE séparément."""

    audits: list[dict[str, Any]] = []
    stock_rows = read_csv(ROOT / "portraits/inventaire_portraits.csv")
    stock_expected: set[str] = set()
    stock_missing = 0
    stock_mismatch = 0
    logical_ids: set[str] = set()
    source_resource_count = 0
    for row in stock_rows:
        base = row["portrait"].upper()
        asset_id = f"portraits:{base}"
        if base in logical_ids:
            add_issue(
                issues,
                "error",
                "duplicate-portrait-asset",
                "portraits",
                "Une base est répétée dans l'inventaire logique.",
                path="portraits/inventaire_portraits.csv",
                asset_id=asset_id,
            )
            continue
        logical_ids.add(base)
        declared_sizes = row.get("tailles", "").upper()
        actual_sizes = "".join(
            suffix
            for suffix in "LMS"
            if row.get(f"fichier_{suffix.lower()}", "").strip()
        )
        if declared_sizes != actual_sizes or not actual_sizes:
            add_issue(
                issues,
                "error",
                "portrait-member-mismatch",
                "portraits",
                "Les tailles déclarées ne correspondent pas aux fichiers membres.",
                path="portraits/inventaire_portraits.csv",
                asset_id=asset_id,
                details={"declared_sizes": declared_sizes, "actual_sizes": actual_sizes},
            )
        for suffix in actual_sizes:
            normalized = suffix.lower()
            relative_file = row[f"fichier_{normalized}"]
            path = ROOT / "portraits" / relative_file
            stock_expected.add(repo_path(path))
            source_resource_count += 1
            if not path.is_file():
                stock_missing += 1
                add_issue(
                    issues,
                    "error",
                    "portrait-source-missing",
                    "portraits",
                    "Une ressource membre du portrait est absente.",
                    path=(Path("portraits") / relative_file).as_posix(),
                    asset_id=asset_id,
                )
            elif sha256_file(path) != row[f"sha256_{normalized}"].upper():
                stock_mismatch += 1
                add_issue(
                    issues,
                    "error",
                    "portrait-source-hash-mismatch",
                    "portraits",
                    "Une ressource membre ne correspond plus à son SHA-256 canonique.",
                    path=repo_path(path),
                    asset_id=asset_id,
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
            "role": "asset-authority",
            "asset_count": len(logical_ids),
            "occurrence_count": source_resource_count,
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
            "usage-view",
        ),
        (
            "portraits/pnj-rencontres/inventaire.csv",
            "portraits/pnj-rencontres",
            "portraits:encountered",
            "usage-view",
        ),
        (
            "portraits/mod-PPE/inventaire.csv",
            "portraits/mod-PPE",
            "portraits:ppe",
            "external-reference",
        ),
    )
    for authority, root_text, asset_prefix, role in grouped_specs:
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
                "role": role,
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
        "logical_asset_count": len(logical_ids),
        "physical_file_count": len(stock_present),
        "source_resource_count": source_resource_count,
        "usage_view_physical_file_count": sum(
            item["physical_file_count"] for item in audits if item["role"] == "usage-view"
        ),
        "external_reference_physical_file_count": sum(
            item["physical_file_count"]
            for item in audits
            if item["role"] == "external-reference"
        ),
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


def animation_run_locations(root: Path = ROOT) -> list[dict[str, Any]]:
    """Discover physical animation runs in every supported layout.

    ``path`` is the stable identity.  A run id may legitimately be reused by
    two mono-asset directories, so callers must never key new-layout runs by
    their basename alone.
    """

    animations_root = root / "animations"
    locations: list[dict[str, Any]] = []

    for layout, runs_root in (
        ("legacy", animations_root / "runs"),
        ("batch", animations_root / "batches"),
    ):
        if not runs_root.is_dir():
            continue
        for path in runs_root.iterdir():
            if path.is_dir():
                locations.append(
                    {"layout": layout, "owner_resref": "", "path": path}
                )

    resources_root = animations_root / "ressources"
    if resources_root.is_dir():
        for resource_root in resources_root.iterdir():
            runs_root = resource_root / "runs"
            if not resource_root.is_dir() or not runs_root.is_dir():
                continue
            for path in runs_root.iterdir():
                if path.is_dir():
                    locations.append(
                        {
                            "layout": "mono-asset",
                            "owner_resref": resource_root.name.upper(),
                            "path": path,
                        }
                    )

    return sorted(
        locations,
        key=lambda item: item["path"].relative_to(root).as_posix().casefold(),
    )


def animation_run_key(location: Mapping[str, Any]) -> str:
    """Build a collision-free key while retaining legacy run keys."""

    run_dir = Path(location["path"])
    layout = str(location["layout"])
    if layout == "legacy":
        return f"animations:{run_dir.name}"
    if layout == "batch":
        return f"animations:batch:{run_dir.name}"
    return f"animations:{str(location['owner_resref']).upper()}:{run_dir.name}"


def animation_manifest_resrefs(manifest: Mapping[str, Any]) -> set[str]:
    """Extract output resrefs using the run-manifest vocabulary in use."""

    values: set[str] = set()

    def add(value: Any) -> None:
        if isinstance(value, str):
            normalized = value.strip().upper()
            if ANIMATION_RESREF_RE.fullmatch(normalized):
                values.add(normalized)
        elif isinstance(value, Mapping):
            for key in ("asset", "resref", "bam_resref", "resource_resref"):
                if key in value:
                    add(value[key])

    for key in ("asset", "resref", "bam_resref"):
        add(manifest.get(key))
    for key in (
        "resources",
        "timed_resources",
        "resrefs",
        "targets",
        "requested_resrefs",
        "resolved_resrefs",
    ):
        sequence = manifest.get(key)
        if isinstance(sequence, list):
            for item in sequence:
                add(item)
    request = manifest.get("request")
    if isinstance(request, Mapping):
        for key in (
            "resref",
            "resrefs",
            "targets",
            "requested_resrefs",
            "resolved_resrefs",
        ):
            sequence = request.get(key)
            if isinstance(sequence, list):
                for item in sequence:
                    add(item)
            else:
                add(sequence)
    return values


def validate_animation_run_selections(
    issues: list[dict[str, Any]],
    records: Iterable[dict[str, str]],
    manifest_resrefs: set[str],
    *,
    owner_resref: str,
    run_path: str,
    run_id: str,
) -> list[dict[str, str]]:
    """Reject a QA selection not declared by its run or mono-asset owner."""

    valid: list[dict[str, str]] = []
    for record in records:
        resref = record["resref"]
        mismatches: list[str] = []
        if resref not in manifest_resrefs:
            mismatches.append("absent du manifeste final")
        if owner_resref and resref != owner_resref:
            mismatches.append(f"différent du propriétaire mono-asset {owner_resref}")
        if mismatches:
            add_issue(
                issues,
                "error",
                "animation-selection-run-resref-mismatch",
                "animations",
                "La sélection QA en jeu ne correspond pas aux ressources déclarées par le run.",
                path=record["selection"],
                asset_id=record["asset_id"],
                run_id=run_id,
                details={
                    "manifest_resrefs": sorted(manifest_resrefs),
                    "reasons": mismatches,
                    "run_path": run_path,
                },
            )
            continue
        valid.append(record)
    return valid


def animation_run_references(candidate: Mapping[str, Any]) -> list[str]:
    """Return normalized run roots from structured or legacy candidate data."""

    references: list[str] = []
    structured = candidate.get("source_runs")
    if isinstance(structured, list):
        for item in structured:
            if isinstance(item, Mapping) and isinstance(item.get("path"), str):
                reference = str(item["path"]).replace("\\", "/").rstrip("/")
                if ANIMATION_RUN_REFERENCE_RE.fullmatch(reference):
                    references.append(reference)

    source_run = candidate.get("source_run")
    if isinstance(source_run, str):
        references.extend(
            match.group(0).rstrip(".")
            for match in ANIMATION_RUN_REFERENCE_RE.finditer(source_run.replace("\\", "/"))
        )

    unique: dict[str, str] = {}
    for reference in references:
        unique.setdefault(reference.casefold(), reference)
    return list(unique.values())


def referenced_animation_runs(candidates: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Index release references by full path, never by ambiguous run id."""

    result: dict[str, list[str]] = defaultdict(list)
    for candidate in candidates:
        for reference in animation_run_references(candidate):
            result[reference.casefold()].append(candidate["area"].upper())
    return result


def referenced_animation_run_assets(
    candidates: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Index explicit per-run assets from schema-v3 candidate entries."""

    result: dict[str, list[str]] = defaultdict(list)
    for candidate in candidates:
        structured = candidate.get("source_runs")
        if not isinstance(structured, list):
            continue
        for source in structured:
            if not isinstance(source, Mapping):
                continue
            reference = str(source.get("path", "")).replace("\\", "/").rstrip("/")
            if not ANIMATION_RUN_REFERENCE_RE.fullmatch(reference):
                continue
            asset_resrefs = source.get("asset_ids")
            if not isinstance(asset_resrefs, list):
                continue
            for resref in asset_resrefs:
                result[reference.casefold()].append(
                    f"animations:bam:{str(resref).upper()}"
                )
    return result


def animation_ingame_selections(
    issues: list[dict[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    """Load valid current selections backed by explicit in-game QA decisions."""

    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    builder = global_registry.RegistryBuilder(ROOT)
    selections, _declared = global_registry.load_current_animation_qa(builder)
    for anomaly in builder._anomalies:
        add_issue(
            issues,
            str(anomaly["severity"]),
            str(anomaly["code"]),
            str(anomaly["domain"]),
            str(anomaly["message"]),
            path=str(anomaly.get("source", "")),
            asset_id=str(anomaly.get("asset_id", "")),
            details=anomaly.get("details"),
        )

    for resref, selection in selections.items():
        if selection.get("result_kind") != "x4":
            continue
        run_reference = selection["final_run_path"].replace("\\", "/").rstrip("/")
        if not ANIMATION_RUN_REFERENCE_RE.fullmatch(run_reference):
            add_issue(
                issues,
                "error",
                "animation-selection-run-layout-invalid",
                "animations",
                "Le run sélectionné n'appartient à aucun layout animation supporté.",
                path=run_reference,
                asset_id=f"animations:bam:{resref}",
            )
            continue
        result[run_reference.casefold()].append(
            {
                "asset_id": f"animations:bam:{resref}",
                "decision": selection["decision_path"],
                "resref": resref,
                "selection": selection["selection_path"],
            }
        )
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
) -> dict[str, Any]:
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
    run_locations = animation_run_locations(ROOT)
    run_layout_counts = Counter(str(item["layout"]) for item in run_locations)

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
    proto_root = ROOT / "proto"
    present_proto = (
        {path.name for path in proto_root.iterdir() if path.is_dir()}
        if proto_root.is_dir()
        else set()
    )
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
    for location in run_locations:
        for path in Path(location["path"]).rglob("*"):
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
    selected_assets = referenced_animation_run_assets(candidates)
    ingame_selections = animation_ingame_selections(issues)
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

        structured_sources = candidate.get("source_runs")
        if isinstance(structured_sources, list):
            for source in structured_sources:
                source_path = (
                    str(source.get("path", "")).replace("\\", "/").rstrip("/")
                    if isinstance(source, Mapping)
                    else ""
                )
                if not ANIMATION_RUN_REFERENCE_RE.fullmatch(source_path):
                    evidence_valid = False
                    add_issue(
                        issues,
                        "error",
                        "animation-candidate-source-run-path-invalid",
                        "animations",
                        "Un source_runs structuré ne désigne pas une racine de run animation supportée.",
                        path=source_path or repo_path(candidate_path),
                        asset_id=f"animations:pack:{area}",
                    )
                    continue
                manifest_reference = str(source.get("manifest_path", "")).replace("\\", "/")
                expected_manifest_hash = str(source.get("manifest_sha256", "")).upper()
                if not manifest_reference.startswith(source_path + "/"):
                    evidence_valid = False
                    add_issue(
                        issues,
                        "error",
                        "animation-candidate-source-manifest-outside-run",
                        "animations",
                        "Le manifeste d'un source_runs structuré est extérieur à sa racine de run.",
                        path=manifest_reference or source_path,
                        asset_id=f"animations:pack:{area}",
                    )
                else:
                    manifest_source_path = ROOT / manifest_reference
                    if not manifest_source_path.is_file():
                        evidence_valid = False
                        add_issue(
                            issues,
                            "error",
                            "animation-candidate-source-manifest-missing",
                            "animations",
                            "Le manifeste d'un source_runs structuré est absent.",
                            path=manifest_reference,
                            asset_id=f"animations:pack:{area}",
                        )
                    elif (
                        not expected_manifest_hash
                        or sha256_file(manifest_source_path) != expected_manifest_hash
                    ):
                        evidence_valid = False
                        add_issue(
                            issues,
                            "error",
                            "animation-candidate-source-manifest-hash-mismatch",
                            "animations",
                            "Le manifeste d'un source_runs structuré ne correspond pas à son hash.",
                            path=manifest_reference,
                            asset_id=f"animations:pack:{area}",
                        )

        source_run_text = candidate.get("source_run", "")
        legacy_proto_references = (
            re.findall(r"proto/[^\s+;,)]+", source_run_text)
            if isinstance(source_run_text, str)
            else []
        )
        for reference in [
            *animation_run_references(candidate),
            *(item.rstrip(".") for item in legacy_proto_references),
        ]:
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
                            "evidence_source": historical_git_evidence.reference_label(migration),
                        }
                    )
                    continue
                evidence_valid = False
                add_issue(
                    issues,
                    "error",
                    "animation-qa-evidence-unresolved",
                    "animations",
                    "Une preuve citée par la QA scellée ne correspond ni au fichier courant ni à une preuve historique bornée.",
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
    preview_count = 0
    for location in run_locations:
        run_dir = Path(location["path"])
        layout = str(location["layout"])
        owner_resref = str(location["owner_resref"])
        physical += 1
        files = [path for path in run_dir.rglob("*") if path.is_file()]
        manifest_path = run_dir / "manifest.json"
        request_path = run_dir / "request.json"
        qa_path = run_dir / "qa-approval.json"
        manifest = read_json(manifest_path) if manifest_path.is_file() else {}
        request = read_json(request_path) if request_path.is_file() else {}
        qa_present = qa_path.is_file()
        qa: Mapping[str, Any] = {}
        preview_evidence_valid = True
        if qa_present:
            preview_count += 1
            try:
                qa_data = read_json(qa_path)
            except (OSError, json.JSONDecodeError) as error:
                preview_evidence_valid = False
                add_issue(
                    issues,
                    "error",
                    "animation-run-preview-record-invalid",
                    "animations",
                    "Le relevé de revue/preview du run n'est pas un JSON lisible.",
                    path=repo_path(qa_path),
                    run_id=run_dir.name,
                    details={"error": str(error)},
                )
            else:
                if isinstance(qa_data, Mapping):
                    qa = qa_data
                    if not qa.get("schema") or not qa.get("status"):
                        preview_evidence_valid = False
                        add_issue(
                            issues,
                            "error",
                            "animation-run-preview-record-invalid",
                            "animations",
                            "Le relevé de revue/preview du run ne déclare pas schema/status.",
                            path=repo_path(qa_path),
                            run_id=run_dir.name,
                        )
                else:
                    preview_evidence_valid = False
                    add_issue(
                        issues,
                        "error",
                        "animation-run-preview-record-invalid",
                        "animations",
                        "Le relevé de revue/preview du run doit être un objet JSON.",
                        path=repo_path(qa_path),
                        run_id=run_dir.name,
                    )
        asset_ids: list[str] = []
        run_path = repo_path(run_dir)
        migration = migration_by_target.get(run_path, {})
        asset_ids.extend(str(asset_id) for asset_id in migration.get("asset_ids", []))
        asset_ids.extend(selected_assets.get(run_path.casefold(), []))
        for resref in qa.get("accepted_resrefs", []):
            asset_ids.append(f"animations:bam:{str(resref).upper()}")
        manifest_resrefs = (
            animation_manifest_resrefs(manifest) if isinstance(manifest, Mapping) else set()
        )
        request_resrefs = (
            animation_manifest_resrefs(request) if isinstance(request, Mapping) else set()
        )
        asset_ids.extend(
            f"animations:bam:{resref}"
            for resref in sorted(manifest_resrefs | request_resrefs)
        )
        classified_resrefs = {
            asset_id.removeprefix("animations:bam:")
            for asset_id in asset_ids
            if asset_id.startswith("animations:bam:")
        }
        if owner_resref:
            unexpected_resrefs = sorted(classified_resrefs - {owner_resref})
            if unexpected_resrefs:
                add_issue(
                    issues,
                    "error",
                    "animation-mono-run-owner-mismatch",
                    "animations",
                    "Un run mono-asset déclare des ressources différentes de son dossier propriétaire.",
                    path=run_path,
                    asset_id=f"animations:bam:{owner_resref}",
                    run_id=run_dir.name,
                    details={"declared_resrefs": sorted(classified_resrefs)},
                )
            asset_ids.append(f"animations:bam:{owner_resref}")
        elif layout == "batch" and len(classified_resrefs) == 1:
            add_issue(
                issues,
                "warning",
                "animation-single-asset-run-in-batch-layout",
                "animations",
                "Ce run batch ne déclare qu'une ressource; les nouveaux runs mono-asset appartiennent sous ressources/<RESREF>/runs.",
                path=run_path,
                asset_id=f"animations:bam:{next(iter(classified_resrefs))}",
                run_id=run_dir.name,
            )
        ingame_selection_records = validate_animation_run_selections(
            issues,
            ingame_selections.get(run_path.casefold(), []),
            manifest_resrefs,
            owner_resref=owner_resref,
            run_path=run_path,
            run_id=run_dir.name,
        )
        asset_ids.extend(
            record["asset_id"] for record in ingame_selection_records
        )
        selected_areas = selected.get(run_path.casefold(), [])
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
        if qa_present:
            qa_checks = (
                (manifest_path, qa.get("run_manifest_sha256"), "run manifest"),
                (run_dir / "03_runtime_pack/manifest.json", qa.get("pack_manifest_sha256"), "pack manifest"),
                (run_dir / "03_runtime_pack/AreaAnimations-X4.registry", qa.get("registry_sha256"), "registry"),
            )
            for evidence_path, expected_hash, label in qa_checks:
                if not expected_hash:
                    continue
                if not evidence_path.is_file():
                    preview_evidence_valid = False
                    add_issue(
                        issues,
                        "error",
                        "animation-run-preview-evidence-missing",
                        "animations",
                        f"La preuve de revue/preview ({label}) est absente.",
                        path=repo_path(evidence_path),
                        run_id=run_dir.name,
                    )
                elif sha256_file(evidence_path) != str(expected_hash).upper():
                    preview_evidence_valid = False
                    add_issue(
                        issues,
                        "error",
                        "animation-run-preview-evidence-hash-mismatch",
                        "animations",
                        f"La preuve de revue/preview ({label}) ne correspond plus au relevé du run.",
                        path=repo_path(evidence_path),
                        run_id=run_dir.name,
                    )
            for review in qa.get("reviews", []):
                review_path = run_dir / review["file"]
                if not review_path.is_file():
                    preview_evidence_valid = False
                    add_issue(
                        issues,
                        "error",
                        "animation-run-preview-media-missing",
                        "animations",
                        "Un média de revue/preview cité par le run est absent.",
                        path=repo_path(review_path),
                        run_id=run_dir.name,
                    )
                elif sha256_file(review_path) != str(review["sha256"]).upper():
                    preview_evidence_valid = False
                    add_issue(
                        issues,
                        "error",
                        "animation-run-preview-media-hash-mismatch",
                        "animations",
                        "Un média de revue/preview ne correspond plus au relevé du run.",
                        path=repo_path(review_path),
                        run_id=run_dir.name,
                    )
        canonical_prototypes = alpha_by_path.get(run_path, [])
        descriptor = manifest_path if manifest_path.is_file() else request_path
        result = str(manifest.get("status", "empty" if not files else "unknown"))
        qa_state = str(manifest.get("qa_status", "not-assessed"))
        if ingame_selection_records:
            selected_resrefs = {record["resref"] for record in ingame_selection_records}
            qa_state = (
                "ingame-accepted"
                if manifest_resrefs <= selected_resrefs
                else "ingame-partially-accepted"
            )
        elif qa_present:
            qa_state = f"preview-{str(qa.get('status', 'recorded')).casefold()}"
        selection_state = "historical"
        selection_authority = ""
        if ingame_selection_records:
            selection_state = "selected"
            selection_authority = ";".join(
                sorted({record["selection"] for record in ingame_selection_records})
            )
        elif selected_areas:
            selection_state = "release-candidate"
            selection_authority = repo_path(candidate_path)
        elif canonical_prototypes:
            selection_state = "canonical-prototype"
            selection_authority = repo_path(alpha_authority)
        migration_role = str(migration.get("role", ""))
        note_parts = [f"layout={layout}"]
        if selected_areas:
            note_parts.append(f"Candidat(s) de zone: {';'.join(selected_areas)}")
        if ingame_selection_records:
            note_parts.append(
                "QA ingame explicite: "
                + ";".join(
                    sorted(record["decision"] for record in ingame_selection_records)
                )
            )
        if qa_present:
            note_parts.append(
                "qa-approval.json = revue/preview du run; aucune preuve de QA ingame"
            )
        if migration_role:
            note_parts.append(f"Migré depuis proto; rôle historique: {migration_role}")
        add_run(
            runs,
            default_run(
                run_key=animation_run_key(location),
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
                provenance_state=(
                    "verified"
                    if qa_present and preview_evidence_valid
                    else "incomplete"
                    if qa_present
                    else "complete"
                    if manifest and request
                    else "partial"
                ),
                legacy=bool(migration),
                notes="; ".join(note_parts),
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
        "physical_run_count_by_layout": dict(sorted(run_layout_counts.items())),
        "run_preview_record_count": preview_count,
        "ingame_qa_selected_asset_count": sum(
            len(records) for records in ingame_selections.values()
        ),
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
    restoration_path = ROOT / RESTORATION_MANIFEST
    restoration_data = read_json(restoration_path) if restoration_path.is_file() else {}
    restorations = {
        str(entry.get("target", "")): entry
        for entry in restoration_data.get("restorations", [])
    }
    verified = 0
    moved_files = 0
    moved_bytes = 0
    removed_empty = 0
    restored_after_cleanup = 0
    for operation in data.get("operations", []):
        target_text = str(operation.get("target", ""))
        action = operation["action"]
        if action == "remove-empty-directory":
            source = ROOT / operation["source_roots"][0]
            if source.exists():
                source_text = repo_path(source)
                restoration = restorations.get(source_text)
                restored_manifest = source / str((restoration or {}).get("manifest", ""))
                expected_hash = str((restoration or {}).get("manifest_sha256", "")).upper()
                if (
                    restoration
                    and restored_manifest.is_file()
                    and expected_hash
                    and sha256_file(restored_manifest) == expected_hash
                ):
                    verified += 1
                    restored_after_cleanup += 1
                else:
                    add_issue(
                        issues,
                        "error",
                        "cleanup-empty-directory-returned",
                        operation["domain"],
                        "Le chemin nettoyé est réapparu sans preuve de restauration valide.",
                        path=source_text,
                    )
            else:
                verified += 1
                removed_empty += 1
            continue
        if "<movie-source-directory>" in target_text:
            target_texts = [
                target_text.replace(
                    "<movie-source-directory>",
                    Path(row["extracted_path"]).parent.name,
                )
                for row in read_csv(ROOT / "video/index/resources.csv")
                if row["asset_key"].startswith("movie:")
            ]
        else:
            target_texts = [target_text]
        targets = [ROOT / item for item in target_texts]
        missing_targets = [
            item for item, target in zip(target_texts, targets) if not target.is_dir()
        ]
        if missing_targets:
            add_issue(
                issues,
                "error",
                "cleanup-target-missing",
                operation["domain"],
                "Une destination de nettoyage documentée est absente.",
                path=missing_targets[0],
                details={"missing_target_count": len(missing_targets)},
            )
            continue
        files = [
            path
            for target in targets
            for path in target.rglob("*")
            if path.is_file()
        ]
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
        "restored_after_cleanup_count": restored_after_cleanup,
        "restoration_manifest": RESTORATION_MANIFEST,
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


def audit_workspace_backups_p5(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify the conservative P5 backup retention and cleanup receipt."""

    data = read_json(ROOT / BACKUPS_P5_MANIFEST)
    classifications = data.get("classifications", {})
    valid = True

    for classification in ("KEEP_RESTORE", "KEEP_HISTORICAL"):
        for entry in classifications.get(classification, []):
            path_text = str(entry["path"])
            if not (ROOT / path_text).exists():
                valid = False
                add_issue(
                    issues,
                    "error",
                    "backups-p5-retained-path-missing",
                    "workspace",
                    "Un élément conservé pour restauration ou historique en P5 est absent.",
                    path=path_text,
                    details={"classification": classification},
                )
            for required_text in entry.get("required_paths", []):
                if not (ROOT / str(required_text)).exists():
                    valid = False
                    add_issue(
                        issues,
                        "error",
                        "backups-p5-required-child-missing",
                        "workspace",
                        "Un backup explicitement conservé en P5 est absent de son propriétaire.",
                        path=str(required_text),
                        details={"classification": classification},
                    )

    verified_archives = 0
    archived_files = 0
    archived_bytes = 0
    for entry in classifications.get("ARCHIVE", []):
        source_text = str(entry["source"])
        target_text = str(entry["target"])
        entry_valid = True
        if (ROOT / source_text).exists():
            entry_valid = False
            add_issue(
                issues,
                "error",
                "backups-p5-archive-source-returned",
                "workspace",
                "Un élément archivé en P5 est réapparu dans une zone active.",
                path=source_text,
            )
        target = ROOT / target_text
        if not target.exists():
            entry_valid = False
            add_issue(
                issues,
                "error",
                "backups-p5-archive-target-missing",
                "workspace",
                "Une archive P5 est absente.",
                path=target_text,
            )
        else:
            actual_count, actual_bytes, actual_hash = inventory_evidence(target)
            if (
                actual_count != int(entry["file_count"])
                or actual_bytes != int(entry["bytes"])
                or actual_hash != str(entry["aggregate_sha256"]).upper()
            ):
                entry_valid = False
                add_issue(
                    issues,
                    "error",
                    "backups-p5-archive-evidence-mismatch",
                    "workspace",
                    "Une archive P5 ne correspond plus à sa preuve hashée.",
                    path=target_text,
                )
        if entry_valid:
            verified_archives += 1
            archived_files += int(entry["file_count"])
            archived_bytes += int(entry["bytes"])
        valid = valid and entry_valid

    verified_deletions = 0
    deleted_duplicate_files = 0
    reclaimed_bytes = 0
    removed_empty_directories = 0
    for entry in classifications.get("DELETE_SAFE", []):
        source_text = str(entry["source"])
        kind = str(entry["kind"])
        entry_valid = True
        source = ROOT / source_text
        if kind == "empty-directory" and source.exists():
            if not source.is_dir() or any(source.iterdir()):
                entry_valid = False
                add_issue(
                    issues,
                    "error",
                    "backups-p5-empty-directory-not-empty",
                    "workspace",
                    "Un dossier supprimable/recréable vide en P5 contient désormais des éléments.",
                    path=source_text,
                )
        elif kind != "empty-directory" and source.exists():
            entry_valid = False
            add_issue(
                issues,
                "error",
                "backups-p5-delete-safe-source-returned",
                "workspace",
                "Un doublon ou dossier vide supprimé en P5 est réapparu.",
                path=source_text,
            )

        if kind == "empty-directory":
            if entry_valid:
                removed_empty_directories += 1
        elif kind == "exact-duplicate-tree":
            replacement_text = str(entry["replacement"])
            replacement = ROOT / replacement_text
            if not replacement.exists():
                entry_valid = False
                add_issue(
                    issues,
                    "error",
                    "backups-p5-duplicate-replacement-missing",
                    "workspace",
                    "Le remplaçant hashé d'un doublon supprimé en P5 est absent.",
                    path=replacement_text,
                )
            else:
                actual_count, actual_bytes, actual_hash = inventory_evidence(replacement)
                if (
                    actual_count != int(entry["file_count"])
                    or actual_bytes != int(entry["bytes"])
                    or actual_hash != str(entry["aggregate_sha256"]).upper()
                ):
                    entry_valid = False
                    add_issue(
                        issues,
                        "error",
                        "backups-p5-duplicate-replacement-mismatch",
                        "workspace",
                        "Le remplaçant d'un doublon supprimé en P5 a divergé.",
                        path=replacement_text,
                    )
        elif kind == "exact-duplicate-files":
            source_root = source_text.rstrip("/")
            virtual_records: list[tuple[str, int, str]] = []
            for item in entry.get("files", []):
                item_source = str(item["source"])
                canonical_text = str(item["canonical"])
                expected_bytes = int(item["bytes"])
                expected_hash = str(item["sha256"]).upper()
                canonical = ROOT / canonical_text
                if (
                    not canonical.is_file()
                    or canonical.stat().st_size != expected_bytes
                    or sha256_file(canonical) != expected_hash
                ):
                    entry_valid = False
                    add_issue(
                        issues,
                        "error",
                        "backups-p5-canonical-duplicate-missing",
                        "portraits",
                        "Le portrait canonique justifiant une déduplication P5 est absent ou divergent.",
                        path=canonical_text,
                    )
                prefix = source_root + "/"
                relative = item_source[len(prefix) :] if item_source.startswith(prefix) else item_source
                virtual_records.append((relative, expected_bytes, expected_hash))
            virtual_records.sort(key=lambda item: item[0].casefold())
            payload = "".join(
                f"{relative}|{size}|{digest}\n"
                for relative, size, digest in virtual_records
            ).encode("utf-8")
            virtual_hash = hashlib.sha256(payload).hexdigest().upper()
            if (
                len(virtual_records) != int(entry["file_count"])
                or sum(size for _relative, size, _digest in virtual_records)
                != int(entry["bytes"])
                or virtual_hash != str(entry["aggregate_sha256"]).upper()
            ):
                entry_valid = False
                add_issue(
                    issues,
                    "error",
                    "backups-p5-duplicate-manifest-inconsistent",
                    "workspace",
                    "La preuve interne d'une déduplication P5 est incohérente.",
                    path=BACKUPS_P5_MANIFEST,
                    details={"id": entry.get("id", "")},
                )
        else:
            entry_valid = False
            add_issue(
                issues,
                "error",
                "backups-p5-delete-safe-kind-unknown",
                "workspace",
                "Le manifeste P5 contient un type de suppression inconnu.",
                path=BACKUPS_P5_MANIFEST,
                details={"kind": kind},
            )

        if entry_valid:
            verified_deletions += 1
            if kind.startswith("exact-duplicate"):
                deleted_duplicate_files += int(entry["file_count"])
                reclaimed_bytes += int(entry["bytes"])
        valid = valid and entry_valid

    summary = data.get("summary", {})
    actual_counts = {
        "keep_restore_count": len(classifications.get("KEEP_RESTORE", [])),
        "keep_historical_count": len(classifications.get("KEEP_HISTORICAL", [])),
        "archive_count": len(classifications.get("ARCHIVE", [])),
        "delete_safe_count": len(classifications.get("DELETE_SAFE", [])),
        "archived_file_count": sum(
            int(entry["file_count"]) for entry in classifications.get("ARCHIVE", [])
        ),
        "archived_bytes": sum(
            int(entry["bytes"]) for entry in classifications.get("ARCHIVE", [])
        ),
        "deleted_duplicate_file_count": sum(
            int(entry.get("file_count", 0))
            for entry in classifications.get("DELETE_SAFE", [])
            if str(entry.get("kind", "")).startswith("exact-duplicate")
        ),
        "reclaimed_bytes": sum(
            int(entry.get("bytes", 0))
            for entry in classifications.get("DELETE_SAFE", [])
            if str(entry.get("kind", "")).startswith("exact-duplicate")
        ),
        "removed_empty_directory_count": sum(
            1
            for entry in classifications.get("DELETE_SAFE", [])
            if entry.get("kind") == "empty-directory"
        ),
        "uncertain_count": 0,
    }
    if any(int(summary.get(key, -1)) != value for key, value in actual_counts.items()):
        valid = False
        add_issue(
            issues,
            "error",
            "backups-p5-manifest-summary-mismatch",
            "workspace",
            "Le résumé du manifeste P5 est incohérent.",
            path=BACKUPS_P5_MANIFEST,
        )

    return {
        "manifest": BACKUPS_P5_MANIFEST,
        **actual_counts,
        "verified_archive_count": verified_archives,
        "verified_archived_file_count": archived_files,
        "verified_archived_bytes": archived_bytes,
        "verified_delete_safe_count": verified_deletions,
        "verified_deleted_duplicate_file_count": deleted_duplicate_files,
        "verified_reclaimed_bytes": reclaimed_bytes,
        "verified_removed_empty_directory_count": removed_empty_directories,
        "verified": valid,
    }


def audit_video_runs(
    issues: list[dict[str, Any]], runs: dict[str, dict[str, Any]]
) -> dict[str, int]:
    data = read_json(ROOT / CLEANUP_MANIFEST)
    canonical_asset_ids = {
        "videos:" + row["asset_key"].replace(":", "-").lower()
        for row in read_csv(ROOT / "video/index/resources.csv")
    }
    movie_asset_ids = [
        "videos:" + row["asset_key"].replace(":", "-").lower()
        for row in read_csv(ROOT / "video/index/resources.csv")
        if row["asset_key"].startswith("movie:")
    ]
    physical = 0
    descriptors = sorted(
        (ROOT / "video").glob("*/runs/*/run.json"),
        key=lambda path: path.as_posix().casefold(),
    )
    run_directories: dict[str, list[Path]] = defaultdict(list)
    for descriptor in descriptors:
        run_directories[descriptor.parent.name].append(descriptor.parent)

    def resolve_run_path(path_text: str) -> Path:
        candidate = (ROOT / path_text).resolve()
        if candidate.is_file():
            return candidate
        match = re.fullmatch(r"video/runs/([^/]+)/(.*)", path_text.replace("\\", "/"))
        if match and len(run_directories.get(match.group(1), [])) == 1:
            return (run_directories[match.group(1)][0] / match.group(2)).resolve()
        return candidate

    def evidence_state(
        entries: list[dict[str, Any]], *, run_id: str, descriptor_path: str, label: str
    ) -> str:
        if not entries:
            return "none"
        state = "verified"
        for entry in entries:
            path_text = str(entry.get("path", ""))
            expected_hash = str(entry.get("sha256", "")).upper()
            expected_bytes = entry.get("bytes")
            candidate = resolve_run_path(path_text)
            portable = bool(path_text) and candidate.is_relative_to(ROOT.resolve())
            if not portable or not candidate.is_file():
                state = "missing"
                add_issue(
                    issues,
                    "error",
                    "video-run-evidence-missing",
                    "videos",
                    f"Preuve {label} absente dans un run vidéo.",
                    path=path_text or descriptor_path,
                    run_id=run_id,
                )
                continue
            if candidate.stat().st_size != expected_bytes or sha256_file(candidate) != expected_hash:
                state = "drifted"
                add_issue(
                    issues,
                    "error",
                    "video-run-evidence-drift",
                    "videos",
                    f"Preuve {label} différente du manifeste du run vidéo.",
                    path=path_text,
                    run_id=run_id,
                )
        return state

    for run_id, locations in sorted(run_directories.items()):
        if len(locations) > 1:
            add_issue(
                issues,
                "error",
                "video-run-id-duplicate",
                "videos",
                "Un identifiant de run vidéo existe sous plusieurs assets.",
                run_id=run_id,
                details={"paths": [repo_path(path) for path in locations]},
            )
    for descriptor in descriptors:
            physical += 1
            descriptor_path = repo_path(descriptor)
            run_id = descriptor.parent.name
            try:
                current = read_json(descriptor)
            except (OSError, json.JSONDecodeError) as exc:
                add_issue(
                    issues,
                    "error",
                    "video-run-descriptor-invalid",
                    "videos",
                    "Descripteur de run vidéo illisible.",
                    path=descriptor_path,
                    run_id=run_id,
                    details={"error": str(exc)},
                )
                continue
            asset_ids = current.get("asset_ids") or []
            result = current.get("result") or {}
            pipeline = current.get("pipeline") or {}
            valid_header = (
                current.get("$schema") == "docs/workspace-run.schema.json"
                and current.get("schema_version") == 1
                and current.get("domain") == "videos"
                and current.get("run_id") == run_id
                and asset_ids
                and set(asset_ids).issubset(canonical_asset_ids)
            )
            if not valid_header:
                add_issue(
                    issues,
                    "error",
                    "video-run-descriptor-invalid",
                    "videos",
                    "En-tête ou asset_ids invalides dans un run vidéo.",
                    path=descriptor_path,
                    run_id=run_id,
                )
            recipe_path = str(pipeline.get("recipe_path", ""))
            recipe_hash = str(pipeline.get("recipe_sha256", "")).upper()
            recipe = resolve_run_path(recipe_path)
            recipe_valid = bool(
                recipe_path
                and recipe.is_file()
                and recipe_hash
                and sha256_file(recipe) == recipe_hash
            )
            if not recipe_valid:
                add_issue(
                    issues,
                    "error",
                    "video-run-recipe-drift",
                    "videos",
                    "Recette absente ou différente du hash scellé dans le run vidéo.",
                    path=recipe_path or descriptor_path,
                    run_id=run_id,
                )
            inputs_state = evidence_state(
                current.get("inputs") or [],
                run_id=run_id,
                descriptor_path=descriptor_path,
                label="d'entrée",
            )
            outputs_state = evidence_state(
                current.get("outputs") or [],
                run_id=run_id,
                descriptor_path=descriptor_path,
                label="de sortie",
            )
            completed_without_outputs = result.get("status") == "completed" and outputs_state == "none"
            if completed_without_outputs:
                outputs_state = "missing"
                add_issue(
                    issues,
                    "error",
                    "video-run-output-missing",
                    "videos",
                    "Run vidéo terminé sans sortie déclarée.",
                    path=descriptor_path,
                    run_id=run_id,
                )
            provenance = "verified" if (
                valid_header
                and recipe_valid
                and inputs_state == "verified"
                and outputs_state in {"verified", "none"}
                and result.get("sealed") is True
            ) else "partial"
            add_run(
                runs,
                default_run(
                    run_key=f"videos:{run_id}",
                    domain="videos",
                    run_id=run_id,
                    asset_ids=asset_ids,
                    path=repo_path(descriptor.parent),
                    run_kind=str(pipeline.get("id", "video-run")),
                    descriptor_path=descriptor_path,
                    recipe_path=recipe_path,
                    result_state=str(result.get("status", "unknown")),
                    qa_state="not-assessed",
                    selection_state="unselected",
                    selection_authority="",
                    inputs_state=inputs_state,
                    outputs_state=outputs_state,
                    provenance_state=provenance,
                    legacy=False,
                    notes=str(result.get("notes", "")),
                ),
            )

    selected_runs: set[str] = set()
    patch_runs: set[str] = set()
    selection_path = ROOT / VIDEO_SELECTION
    if selection_path.is_file():
        for asset in read_csv(selection_path):
            asset_id = str(asset.get("asset_id", ""))
            if asset_id not in canonical_asset_ids:
                add_issue(
                    issues,
                    "error",
                    "video-selection-asset-invalid",
                    "videos",
                    "Asset inconnu dans la sélection vidéo.",
                    path=VIDEO_SELECTION,
                    details={"asset_id": asset_id},
                )
            for stage_name, run_column, state_column in (
                ("upscale", "upscale_run", "upscale_state"),
                ("interpolation", "interpolation_run", "interpolation_state"),
            ):
                run_id = str(asset.get(run_column, ""))
                state = str(asset.get(state_column, ""))
                if state != "validated" or not run_id:
                    continue
                run_key = f"videos:{run_id}"
                record = runs.get(run_key)
                if (
                    not record
                    or asset_id not in record.get("asset_ids", [])
                    or record.get("result_state") != "completed"
                    or record.get("provenance_state") != "verified"
                ):
                    add_issue(
                        issues,
                        "error",
                        "video-validated-run-invalid",
                        "videos",
                        "Run vidéo validé absent, incohérent ou non vérifié.",
                        path=VIDEO_SELECTION,
                        run_id=run_id,
                    )
                    continue
                record["qa_state"] = str(asset.get("validation_scope", "pipeline-method"))
                record["selection_state"] = f"validated-{stage_name}"
                record["selection_authority"] = VIDEO_SELECTION
                selected_runs.add(run_id)
            patch_run_id = str(asset.get("patch_run", ""))
            if patch_run_id:
                run_id = str(patch_run_id)
                run_key = f"videos:{run_id}"
                record = runs.get(run_key)
                if not record or asset_id not in record.get("asset_ids", []):
                    add_issue(
                        issues,
                        "error",
                        "video-patch-run-invalid",
                        "videos",
                        "Run vidéo sélectionné pour le patch absent ou incohérent.",
                        path=VIDEO_SELECTION,
                        run_id=run_id,
                    )
                else:
                    record["selection_state"] = "patch-selected"
                    record["selection_authority"] = VIDEO_SELECTION
                    patch_runs.add(run_id)

    for operation in data.get("operations", []):
        if operation.get("domain") != "videos" or operation.get("action") != "move":
            continue
        target_template = str(operation["target"])
        if "<movie-source-directory>" in target_template:
            targets = [
                target_template.replace(
                    "<movie-source-directory>",
                    Path(row["extracted_path"]).parent.name,
                )
                for row in read_csv(ROOT / "video/index/resources.csv")
                if row["asset_key"].startswith("movie:")
            ]
        else:
            targets = [target_template]
        physical += len(targets)
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
                outputs_state=(
                    "present"
                    if targets and all((ROOT / target).is_dir() for target in targets)
                    else "missing"
                ),
                provenance_state="verified-move",
                legacy=True,
                notes=str(operation.get("notes", "")),
            ),
        )
    return {
        "physical_run_count": physical,
        "selected_run_count": len(selected_runs | patch_runs),
        "method_validated_run_count": len(selected_runs),
        "patch_selected_run_count": len(patch_runs),
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
    backups_p5 = audit_workspace_backups_p5(issues)
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
        "workspace_backups_p5": backups_p5,
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
