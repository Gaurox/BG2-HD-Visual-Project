"""Initialize the effect BAM processing authority from its generated inventory.

The command never rewrites an existing selection or state. It only creates the
initial CSV or appends newly inventoried BAM assets. Use ``--run`` to write.
"""

from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path
from typing import Iterable, Mapping


ROOT = Path(__file__).resolve().parents[2]
BAM_ASSETS = ROOT / "effects/index/bam-assets.csv"
PROCESSING = ROOT / "effects/index/processing.csv"
FIELDS = (
    "asset_key",
    "asset_directory",
    "spatial_run",
    "spatial_state",
    "interpolation_run",
    "interpolation_state",
    "selected_run",
    "qa_state",
    "qa_evidence",
    "installation_state",
    "installation_receipt",
    "release_state",
    "release_candidate",
    "notes",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError(
                f"schéma inattendu: {path.relative_to(ROOT)}; attendu: {','.join(FIELDS)}"
            )
        return list(reader)


def read_bam_assets() -> list[dict[str, str]]:
    with BAM_ASSETS.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {"asset_key", "resref", "source_state", "extracted_path"}
    if not rows or not expected.issubset(rows[0]):
        raise ValueError("bam-assets.csv absent ou incomplet; régénérer l'inventaire graphique")
    keys = [row["asset_key"] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("asset_key dupliqué dans effects/index/bam-assets.csv")
    return rows


def default_row(asset: Mapping[str, str]) -> dict[str, str]:
    resref = asset["resref"].upper()
    source_missing = asset["source_state"] == "missing"
    return {
        "asset_key": asset["asset_key"],
        "asset_directory": f"effects/ressources/{resref}",
        "spatial_run": "",
        "spatial_state": "blocked" if source_missing else "not-started",
        "interpolation_run": "",
        "interpolation_state": "not-applicable" if source_missing else "not-started",
        "selected_run": "",
        "qa_state": "not-assessed",
        "qa_evidence": "",
        "installation_state": "not-installed",
        "installation_receipt": "",
        "release_state": "not-evaluated",
        "release_candidate": "",
        "notes": "source BAM stock absent" if source_missing else "",
    }


def build_rows() -> tuple[list[dict[str, str]], int]:
    assets = read_bam_assets()
    existing_rows = read_csv(PROCESSING) if PROCESSING.is_file() else []
    existing = {row["asset_key"]: row for row in existing_rows}
    if len(existing) != len(existing_rows):
        raise ValueError("asset_key dupliqué dans effects/index/processing.csv")

    asset_keys = {row["asset_key"] for row in assets}
    stale = sorted(set(existing) - asset_keys, key=str.casefold)
    if stale:
        raise ValueError(
            "processing contient des assets absents de bam-assets.csv: " + ", ".join(stale)
        )

    rows: list[dict[str, str]] = []
    additions = 0
    for asset in assets:
        key = asset["asset_key"]
        expected_directory = f"effects/ressources/{asset['resref'].upper()}"
        current = existing.get(key)
        if current is None:
            rows.append(default_row(asset))
            additions += 1
            continue
        if current["asset_directory"] != expected_directory:
            raise ValueError(
                f"asset_directory invalide pour {key}: {current['asset_directory']!r}"
            )
        rows.append({field: current.get(field, "") for field in FIELDS})
    return rows, additions


def csv_bytes(rows: Iterable[Mapping[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="écrit effects/index/processing.csv")
    args = parser.parse_args()
    rows, additions = build_rows()
    payload = csv_bytes(rows)
    unchanged = PROCESSING.is_file() and PROCESSING.read_bytes() == payload
    print(
        f"assets: {len(rows)}; additions: {additions}; "
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
