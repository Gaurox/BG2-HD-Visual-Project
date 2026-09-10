"""Initialize or extend the sprite-family lifecycle authority without promotion.

Existing rows are preserved. New inventory families receive conservative states.
Membership in the exact active catalog seeds only facts already proven by its
hashed build manifest and installation receipt. Use ``--run`` to write.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Iterable, Mapping

from sprite_layout import GroupRule, family_directory, load_group_rules, project_relative


ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ROOT / "sprite/index/sprite_families.csv"
ANIMATIONS = ROOT / "sprite/index/sprite_animations.csv"
PROCESSING = ROOT / "sprite/index/processing.csv"
GROUPS = ROOT / "sprite/index/family-groups.csv"
CURRENT = ROOT / (
    "sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/"
    "runs/catalog-xbr2x-x2/current-generation.json"
)
ACTIVE = ROOT / (
    "sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/"
    "runs/catalog-xbr2x-x2/ingame-installation/active-test.json"
)
VARIANT_ID = "x2-nearest"
FIELDS = (
    "asset_key",
    "asset_id",
    "family_id",
    "variant_id",
    "asset_directory",
    "source_set_sha256",
    "production_run",
    "production_run_sha256",
    "production_state",
    "selected_run",
    "selected_run_sha256",
    "qa_state",
    "qa_evidence",
    "installation_state",
    "installation_receipt",
    "catalog_generation",
    "release_state",
    "release_candidate",
    "notes",
)


def read_csv(path: Path, expected_fields: tuple[str, ...] | None = None) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if expected_fields is not None and tuple(reader.fieldnames or ()) != expected_fields:
            raise ValueError(
                f"schéma inattendu: {path.relative_to(ROOT)}; attendu: {','.join(expected_fields)}"
            )
        return list(reader)


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"racine JSON invalide: {path.relative_to(ROOT)}")
    return value


def _safe_project_path(value: object) -> Path:
    text = str(value or "").replace("\\", "/")
    relative = Path(text)
    if not text or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"chemin catalogue non canonique: {text!r}")
    resolved = (ROOT / relative).resolve()
    if ROOT.resolve() not in resolved.parents:
        raise ValueError(f"chemin catalogue hors workspace: {text!r}")
    return resolved


def active_members() -> dict[tuple[str, str], dict[str, str]]:
    if not CURRENT.is_file() or not ACTIVE.is_file():
        return {}
    current = read_json(CURRENT)
    active = read_json(ACTIVE)
    if active.get("generation_id") != current.get("generation_id"):
        raise ValueError("active-test.json ne référence pas current-generation.json")
    build_path = _safe_project_path(
        f"{str(current.get('generation_dir', '')).rstrip('/')}/"
        f"{current.get('build_manifest', '')}"
    )
    build = read_json(build_path)
    if build.get("generation_id") != current.get("generation_id"):
        raise ValueError("build catalogue et current-generation.json divergent")
    status = str(active.get("status", ""))
    qa_state = {
        "installed-pending-qa": "pending",
        "validated-installed": "passed",
        "qa-failed": "failed",
    }.get(status, "not-assessed")
    installation_state = (
        "installed"
        if status in {"installed-pending-qa", "validated-installed", "qa-failed"}
        else "unknown"
    )
    receipt = ACTIVE.resolve().relative_to(ROOT.resolve()).as_posix()
    result: dict[tuple[str, str], dict[str, str]] = {}
    source_members = build.get("source_members", [])
    if not isinstance(source_members, list):
        raise ValueError("source_members absent du build catalogue")
    for member in source_members:
        if not isinstance(member, dict):
            raise ValueError("source_member catalogue invalide")
        animation_id = str(member.get("animation_id", "")).upper()
        run = str(member.get("build_manifest", ""))
        run_sha256 = str(member.get("build_manifest_sha256", "")).upper()
        prefixes = member.get("bam_prefixes", [])
        if not isinstance(prefixes, list):
            raise ValueError("bam_prefixes catalogue invalide")
        for prefix in prefixes:
            key = (animation_id, str(prefix).upper())
            if key in result:
                raise ValueError(f"membre catalogue dupliqué: {key}")
            result[key] = {
                "production_run": run,
                "production_run_sha256": run_sha256,
                "production_state": "verified",
                "selected_run": run,
                "selected_run_sha256": run_sha256,
                "qa_state": qa_state,
                "qa_evidence": receipt if qa_state in {"passed", "failed"} else "",
                "installation_state": installation_state,
                "installation_receipt": receipt,
                "catalog_generation": str(current.get("generation_id", "")),
            }
    return result


def default_row(
    family: Mapping[str, str],
    animation: Mapping[str, str],
    active: Mapping[tuple[str, str], Mapping[str, str]],
    rules: Mapping[str, GroupRule],
) -> dict[str, str]:
    family_id = family["family_id"]
    asset_id = f"sprites:family:{family_id}"
    pair = (family.get("animation_id", "").upper(), family.get("bam_prefix", "").upper())
    proven = active.get(pair, {})
    return {
        "asset_key": f"{asset_id}:{VARIANT_ID}",
        "asset_id": asset_id,
        "family_id": family_id,
        "variant_id": VARIANT_ID,
        "asset_directory": project_relative(
            family_directory(family, animation, rules=rules, project_root=ROOT),
            ROOT,
        ),
        "source_set_sha256": "",
        "production_run": proven.get("production_run", ""),
        "production_run_sha256": proven.get("production_run_sha256", ""),
        "production_state": proven.get(
            "production_state",
            "ready" if family.get("pipeline_ready", "").lower() == "yes" else "blocked",
        ),
        "selected_run": proven.get("selected_run", ""),
        "selected_run_sha256": proven.get("selected_run_sha256", ""),
        "qa_state": proven.get("qa_state", "not-assessed"),
        "qa_evidence": proven.get("qa_evidence", ""),
        "installation_state": proven.get("installation_state", "not-installed"),
        "installation_receipt": proven.get("installation_receipt", ""),
        "catalog_generation": proven.get("catalog_generation", ""),
        "release_state": "not-evaluated",
        "release_candidate": "",
        "notes": "",
    }


def build_rows() -> tuple[list[dict[str, str]], int, int]:
    families = read_csv(FAMILIES)
    animations = read_csv(ANIMATIONS)
    if not families or "family_id" not in families[0]:
        raise ValueError("sprite_families.csv absent ou incomplet")
    animation_by_id = {row["animation_id"].upper(): row for row in animations}
    if len(animation_by_id) != len(animations):
        raise ValueError("animation_id dupliqué dans sprite_animations.csv")
    existing_rows = read_csv(PROCESSING, FIELDS) if PROCESSING.is_file() else []
    rules = load_group_rules(GROUPS)
    existing = {row["asset_key"]: row for row in existing_rows}
    if len(existing) != len(existing_rows):
        raise ValueError("asset_key dupliqué dans processing.csv")
    inventory_ids = {row["family_id"] for row in families}
    stale = sorted(
        row["family_id"] for row in existing_rows if row["family_id"] not in inventory_ids
    )
    if stale:
        raise ValueError("processing référence des familles absentes: " + ", ".join(stale))
    active = active_members()
    rows: list[dict[str, str]] = []
    additions = 0
    seeded = 0
    for family in families:
        animation_id = family.get("animation_id", "").upper()
        animation = animation_by_id.get(animation_id)
        if animation is None:
            raise ValueError(f"animation absente pour {family['family_id']}")
        proposed = default_row(family, animation, active, rules)
        current = existing.get(proposed["asset_key"])
        if current is None:
            rows.append(proposed)
            additions += 1
            seeded += int(bool(proposed["catalog_generation"]))
            continue
        for field in ("asset_id", "family_id", "variant_id", "asset_directory"):
            if current[field] != proposed[field]:
                raise ValueError(
                    f"{field} invalide pour {proposed['asset_key']}: {current[field]!r}"
                )
        rows.append({field: current.get(field, "") for field in FIELDS})
    return rows, additions, seeded


def csv_bytes(rows: Iterable[Mapping[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="écrit sprite/index/processing.csv")
    args = parser.parse_args()
    rows, additions, seeded = build_rows()
    payload = csv_bytes(rows)
    unchanged = PROCESSING.is_file() and PROCESSING.read_bytes() == payload
    print(
        f"families: {len(rows)}; additions: {additions}; active-seeded: {seeded}; "
        f"write: {'yes' if args.run and not unchanged else 'no'}"
    )
    if args.run and not unchanged:
        PROCESSING.parent.mkdir(parents=True, exist_ok=True)
        temporary = PROCESSING.with_suffix(".csv.partial")
        temporary.write_bytes(payload)
        temporary.replace(PROCESSING)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
