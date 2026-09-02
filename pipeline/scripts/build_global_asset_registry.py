"""Build the disposable global asset registry from existing authorities.

The generated files are projections only. This script never writes domain
catalogues, manifests, runs, payloads or game files.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from asset_tracking_contract import (
    ContractError,
    PROVENANCE_VALUES,
    STATE_VALUES,
    map_legacy_status,
    validate_record,
)
from animation_workflow import check_workspace as check_animation_workspace


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / "asset-tracking"
REGISTRY_SCHEMA = "bg2-upscale-global-asset-registry-v1"
COVERAGE_SCHEMA = "bg2-upscale-global-asset-coverage-v1"
ANOMALY_SCHEMA = "bg2-upscale-global-asset-anomalies-v1"
GENERATOR = "pipeline/scripts/build_global_asset_registry.py"
CONTRACT_SCHEMA = "docs/asset-tracking-record.schema.json"

JSON_OUTPUT_NAMES = {
    "registry": "registry.json",
    "coverage": "coverage.json",
    "anomalies": "anomalies.json",
}
REGISTRY_CSV_NAME = "registry.csv"
REGISTRY_CSV_COLUMNS = (
    "asset_id",
    "domain",
    "asset_type",
    "source_state",
    "production_state",
    "qa_state",
    "installation_state",
    "release_state",
    "provenance_state",
    "selection",
    "canonical_source_path",
    "canonical_source_locator",
    "evidence_count",
    "adapter",
    "observed_at_utc",
)

RELEASE_PROGRESS = {"eligible", "approved", "integrated", "published"}
SOURCE_AVAILABLE = {"available", "extracted", "verified"}
PRODUCED = {"produced", "verified"}
RELEASE_ELIGIBLE = {"eligible", "approved", "integrated", "published"}
PROVENANCE_AVAILABLE = {"partial", "complete", "verified"}
ANIMATION_SELECTIONS_ROOT = "animations/index/selections"
ANIMATION_DECISIONS_ROOT = "animations/index/qa-decisions"
ANIMATION_RESOURCES_PATH = "animations/index/ressources.csv"
ANIMATION_CANDIDATES_PATH = (
    "releases/BG2-HD-Upscale/manifests/animation-release-candidates.json"
)
ANIMATION_RESREF_RE = re.compile(r"^(?=.*[A-Z0-9])[A-Z0-9_]{1,8}$")
SHA256_RE = re.compile(r"^[A-F0-9]{64}$")


def canonical_row_sha256(row: Mapping[str, str]) -> str:
    payload = json.dumps(
        dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()

UNRESOLVED_STATES = {
    "source": {"unknown"},
    "production": {"unknown"},
    "qa": {"not-assessed"},
    "installation": {"unknown"},
    "release": {"not-evaluated"},
    "provenance": {"missing"},
}

DOMAIN_SCOPE = {
    "maps": {
        "coverage_status": "projected",
        "authority": "areas.csv",
        "note": "Une entrée par variante jour ou nuit connue.",
    },
    "animations": {
        "coverage_status": "projected",
        "authority": "animations/index/ et candidats release",
        "note": (
            "BAM inventoriés et packs release séparés ; QA courante issue de "
            "selections/<RESREF>.json et de sa décision ingame hashée."
        ),
    },
    "sprites": {
        "coverage_status": "projected",
        "authority": "sprite/index/ et état du catalogue cumulatif",
        "note": "Une entrée par famille ; état actif propagé par appartenance structurée.",
    },
    "ui": {
        "coverage_status": "projected",
        "authority": "manifests UI existants, interface/index/, gameplay-hud et fonts/index/",
        "note": "Compositions UI/HUD et polices projetées ; les pages PVRZ restent des dépendances.",
    },
    "portraits": {
        "coverage_status": "projected",
        "authority": "portraits/inventaire_portraits.csv",
        "note": (
            "Une entrée par base déclarée dans BGEE.lua ou référencée par un CRE ; "
            "les tailles L/M/S sont des dépendances."
        ),
    },
    "videos": {
        "coverage_status": "projected",
        "authority": "video/index/",
        "note": "Une entrée par cinématique ou tutoriel WBM ; processing.csv porte production, QA et sélections.",
    },
    "icons": {
        "coverage_status": "projected",
        "authority": "icons/index/",
        "note": "Une entrée par jeu BAM référencé par ITM/SPL ; les usages restent des relations.",
    },
    "cursors": {
        "coverage_status": "projected",
        "authority": "cursors/index/",
        "note": "CURSORS.BAM est suivi comme un jeu moteur unique.",
    },
    "effects": {
        "coverage_status": "projected",
        "authority": "effects/index/",
        "note": "Une entrée par contrôleur VVC/VEF ; animations et palettes sont des dépendances.",
    },
    "projectiles": {
        "coverage_status": "projected",
        "authority": "projectiles/index/",
        "note": "Une entrée par contrôleur PRO ; animations, effets et palettes sont des dépendances.",
    },
}


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def registry_csv_row(record: Mapping[str, Any]) -> dict[str, str | int]:
    states = record["states"]
    canonical_source = record["canonical_source"]
    selections = sorted(
        (
            f"{selection['role']}:{selection['id']}"
            for selection in record.get("selections", [])
        ),
        key=str.casefold,
    )
    return {
        "asset_id": str(record["asset_id"]),
        "domain": str(record["domain"]),
        "asset_type": str(record["asset_type"]),
        "source_state": str(states["source"]),
        "production_state": str(states["production"]),
        "qa_state": str(states["qa"]),
        "installation_state": str(states["installation"]),
        "release_state": str(states["release"]),
        "provenance_state": str(record["provenance"]["state"]),
        "selection": " | ".join(selections),
        "canonical_source_path": str(canonical_source["path"]),
        "canonical_source_locator": str(canonical_source["locator"]),
        "evidence_count": len(record["provenance"].get("evidence", [])),
        "adapter": str(record["adapter"]),
        "observed_at_utc": str(record["observed_at_utc"]),
    }


def registry_csv_bytes(records: Iterable[Mapping[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=REGISTRY_CSV_COLUMNS,
        extrasaction="raise",
        lineterminator="\r\n",
    )
    writer.writeheader()
    for record in sorted(records, key=lambda item: str(item["asset_id"])):
        writer.writerow(registry_csv_row(record))
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def repo_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def stable_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._/-]+", "-", value.strip())
    return token.strip("-") or "unknown"


def canonical_relative_path(value: str) -> bool:
    return bool(value) and not (
        value.startswith("/")
        or re.match(r"^[A-Za-z]:", value)
        or "\\" in value
        or ".." in value.split("/")
    )


def utc_text(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    if normalized.microsecond:
        return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return normalized.isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime | None:
    candidate = value.strip()
    if not re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T", candidate):
        return None
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def iter_timestamps(value: Any, key: str = "") -> Iterable[datetime]:
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            yield from iter_timestamps(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from iter_timestamps(child, key)
    elif isinstance(value, str) and (
        key.endswith("_utc")
        or key.endswith("_at_utc")
        or key in {"created_utc", "recorded_at_utc", "generated_at_utc"}
    ):
        parsed = parse_timestamp(value)
        if parsed is not None:
            yield parsed


class InputCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._json_cache: dict[str, Any] = {}
        self._csv_cache: dict[str, list[dict[str, str]]] = {}
        self._inputs: dict[str, dict[str, str]] = {}
        self._timestamps: list[datetime] = []

    def absolute(self, path: str) -> Path:
        target = (self.root / path).resolve()
        target.relative_to(self.root)
        return target

    def exists(self, path: str) -> bool:
        return self.absolute(path).is_file()

    def register(self, path: str, role: str = "canonical-source") -> str:
        target = self.absolute(path)
        if not target.is_file():
            raise FileNotFoundError(path)
        normalized = target.relative_to(self.root).as_posix()
        digest = sha256_file(target)
        previous = self._inputs.get(normalized)
        if previous is None or previous["role"] != "canonical-source":
            self._inputs[normalized] = {
                "path": normalized,
                "role": role,
                "sha256": digest,
            }
        return digest

    def read_json(self, path: str, role: str = "canonical-source") -> Any:
        if path not in self._json_cache:
            self.register(path, role)
            value = json.loads(self.absolute(path).read_text(encoding="utf-8-sig"))
            self._json_cache[path] = value
            self._timestamps.extend(iter_timestamps(value))
        return self._json_cache[path]

    def read_csv(self, path: str) -> list[dict[str, str]]:
        if path not in self._csv_cache:
            self.register(path)
            with self.absolute(path).open(encoding="utf-8-sig", newline="") as stream:
                self._csv_cache[path] = list(csv.DictReader(stream))
        return self._csv_cache[path]

    def digest(self, path: str, role: str = "canonical-source") -> str:
        if path not in self._inputs:
            self.register(path, role)
        return self._inputs[path]["sha256"]

    @property
    def snapshot_at_utc(self) -> str:
        if not self._timestamps:
            return "1970-01-01T00:00:00Z"
        return utc_text(max(self._timestamps))

    @property
    def inputs(self) -> list[dict[str, str]]:
        return [self._inputs[path] for path in sorted(self._inputs)]

    @property
    def fingerprint(self) -> str:
        material = "".join(
            f"{entry['role']}\0{entry['path']}\0{entry['sha256']}\n"
            for entry in self.inputs
        ).encode("utf-8")
        return sha256_bytes(material)


def source_ref(path: str, locator: str) -> dict[str, str]:
    return {"path": path, "locator": locator}


def evidence_ref(inputs: InputCatalog, path: str, locator: str) -> dict[str, str]:
    return {
        "path": path,
        "locator": locator,
        "sha256": inputs.digest(path),
    }


def unique_references(references: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    found: dict[tuple[str, str, str], dict[str, str]] = {}
    for reference in references:
        key = (
            reference["path"],
            reference["locator"],
            reference.get("sha256", ""),
        )
        found[key] = reference
    return [found[key] for key in sorted(found)]


def base_record(
    *,
    asset_id: str,
    domain: str,
    asset_type: str,
    canonical_path: str,
    locator: str,
    states: dict[str, str],
    provenance_state: str = "not-applicable",
    evidence: Iterable[dict[str, str]] = (),
    selections: Iterable[dict[str, Any]] = (),
    legacy: Iterable[dict[str, str]] = (),
    adapter: str,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "$schema": CONTRACT_SCHEMA,
        "schema_version": 1,
        "asset_id": asset_id,
        "domain": domain,
        "asset_type": asset_type,
        "canonical_source": source_ref(canonical_path, locator),
        "states": states,
        "provenance": {
            "state": provenance_state,
            "evidence": unique_references(evidence),
        },
        "adapter": adapter,
    }
    selections_list = list(selections)
    if selections_list:
        record["selections"] = selections_list
    legacy_list = list(legacy)
    if legacy_list:
        record["legacy"] = legacy_list
    return record


class RegistryBuilder:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.inputs = InputCatalog(self.root)
        self._records: dict[str, dict[str, Any]] = {}
        self._anomalies: list[dict[str, Any]] = []
        self.uninventoried_scopes: list[dict[str, Any]] = []

    def anomaly(
        self,
        code: str,
        severity: str,
        domain: str,
        message: str,
        *,
        asset_id: str | None = None,
        source: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        anomaly: dict[str, Any] = {
            "code": code,
            "severity": severity,
            "domain": domain,
            "message": message,
        }
        if asset_id:
            anomaly["asset_id"] = asset_id
        if source:
            anomaly["source"] = source
        if details:
            anomaly["details"] = dict(details)
        self._anomalies.append(anomaly)

    def add(self, record: dict[str, Any]) -> None:
        asset_id = record.get("asset_id", "")
        previous = self._records.get(asset_id)
        if previous is not None:
            identical = json_bytes(previous) == json_bytes(record)
            self.anomaly(
                "duplicate-asset-id" if identical else "conflicting-asset-id",
                "warning" if identical else "error",
                str(record.get("domain", "other")),
                "identifiant d'asset projeté plusieurs fois"
                if identical
                else "projections divergentes pour le même identifiant",
                asset_id=asset_id or None,
            )
            return
        self._records[asset_id] = record

    def map_status(
        self,
        mapping: str,
        status: str,
        *,
        domain: str,
        asset_id: str,
        source: str,
    ) -> dict[str, str] | None:
        try:
            return map_legacy_status(mapping, status)
        except ContractError:
            self.anomaly(
                "unknown-status",
                "error",
                domain,
                f"valeur historique inconnue pour {mapping}: {status!r}",
                asset_id=asset_id,
                source=source,
            )
            return None

    def finalize(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        self.inputs.register(CONTRACT_SCHEMA, "contract")
        self.inputs.register("pipeline/scripts/asset_tracking_contract.py", "contract")
        self.inputs.register(GENERATOR, "adapter")

        observed_at = self.inputs.snapshot_at_utc
        valid_records: list[dict[str, Any]] = []
        for asset_id in sorted(self._records):
            record = self._records[asset_id]
            record["observed_at_utc"] = observed_at
            errors = validate_record(record)
            if errors:
                self.anomaly(
                    "invalid-projection",
                    "error",
                    str(record.get("domain", "other")),
                    "projection rejetée par le contrat Phase 2",
                    asset_id=asset_id,
                    details={"errors": errors},
                )
                continue
            valid_records.append(record)

        records_sha256 = sha256_bytes(json_bytes(valid_records))
        registry = {
            "schema": REGISTRY_SCHEMA,
            "contract": CONTRACT_SCHEMA,
            "generated_by": GENERATOR,
            "source_snapshot_at_utc": observed_at,
            "source_fingerprint_sha256": self.inputs.fingerprint,
            "asset_records_sha256": records_sha256,
            "asset_count": len(valid_records),
            "inputs": self.inputs.inputs,
            "assets": valid_records,
        }
        coverage = build_coverage(
            valid_records,
            observed_at,
            self.inputs.fingerprint,
            records_sha256,
            self.uninventoried_scopes,
        )
        anomalies = self._build_anomaly_report(
            observed_at,
            self.inputs.fingerprint,
            records_sha256,
        )
        return registry, coverage, anomalies

    def _build_anomaly_report(
        self,
        observed_at: str,
        fingerprint: str,
        records_sha256: str,
    ) -> dict[str, Any]:
        ordered = sorted(
            self._anomalies,
            key=lambda item: (
                item["severity"],
                item["domain"],
                item["code"],
                item.get("asset_id", ""),
                item.get("source", ""),
                item["message"],
                json.dumps(item.get("details", {}), ensure_ascii=False, sort_keys=True),
            ),
        )
        rendered = []
        for index, anomaly in enumerate(ordered, 1):
            rendered.append({"anomaly_id": f"ANOM-{index:04d}", **anomaly})
        severity_counts = {
            severity: sum(item["severity"] == severity for item in rendered)
            for severity in ("error", "warning", "info")
        }
        code_counts: dict[str, int] = {}
        for item in rendered:
            code_counts[item["code"]] = code_counts.get(item["code"], 0) + 1
        return {
            "schema": ANOMALY_SCHEMA,
            "generated_by": GENERATOR,
            "source_snapshot_at_utc": observed_at,
            "source_fingerprint_sha256": fingerprint,
            "asset_records_sha256": records_sha256,
            "summary": {
                "total": len(rendered),
                "by_severity": severity_counts,
                "by_code": dict(sorted(code_counts.items())),
            },
            "anomalies": rendered,
        }


def default_states() -> dict[str, str]:
    return {
        "source": "unknown",
        "production": "unknown",
        "qa": "not-assessed",
        "installation": "unknown",
        "release": "not-evaluated",
    }


def apply_fragment(
    builder: RegistryBuilder,
    states: dict[str, str],
    fragment: Mapping[str, str],
    *,
    domain: str,
    asset_id: str,
    source: str,
    keep_axes: set[str] | None = None,
) -> None:
    for axis, value in fragment.items():
        if keep_axes and axis in keep_axes and states.get(axis) != value:
            builder.anomaly(
                "state-conflict",
                "error",
                domain,
                f"preuves divergentes pour l'axe {axis}: {states.get(axis)!r} / {value!r}",
                asset_id=asset_id,
                source=source,
            )
            continue
        states[axis] = value


def load_content_groups(inputs: InputCatalog) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    path = "releases/BG2-HD-Upscale/manifests/content.json"
    content = inputs.read_json(path)
    map_groups: dict[str, list[dict[str, Any]]] = {}
    animation_groups: dict[str, list[dict[str, Any]]] = {}
    ui_groups: dict[str, list[dict[str, Any]]] = {}
    for entry in content.get("entries", []):
        kind = entry.get("kind")
        if kind == "map":
            map_groups.setdefault(str(entry.get("area", "")), []).append(entry)
        elif kind == "area-animation":
            animation_groups.setdefault(str(entry.get("area", "")), []).append(entry)
        elif kind == "ui":
            ui_groups.setdefault(str(entry.get("component_label", "")), []).append(entry)
    return map_groups, animation_groups, ui_groups


def load_auxiliary_map_release_contracts(inputs: InputCatalog) -> dict[str, list[dict[str, Any]]]:
    """Read approved animation contracts that deliberately add map payloads."""
    path = "releases/BG2-HD-Upscale/manifests/animation-release-candidates.json"
    candidates = inputs.read_json(path).get("candidates", [])
    contracts: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        if candidate.get("approval_status") != "approved-for-release":
            continue
        contract = candidate.get("occlusion_contract")
        if not isinstance(contract, dict):
            continue
        area = str(candidate.get("area", "")).strip().upper()
        source = str(contract.get("source", "")).strip()
        if not area or "/" not in source:
            continue
        contracts.setdefault(area, []).append(
            {
                "source": source,
                "source_run": source.rsplit("/", 1)[0],
                "destination": str(contract.get("destination", "")).strip(),
                "bytes": contract.get("bytes"),
                "sha256": str(contract.get("sha256", "")).strip(),
                "component_id": contract.get("map_component_id"),
                "component_label": str(contract.get("map_component_label", "")).strip(),
                "payload_group": str(contract.get("map_payload_group", "")).strip(),
            }
        )
    return contracts


def entry_matches_auxiliary_map_contract(
    entry: Mapping[str, Any], contracts: Iterable[Mapping[str, Any]]
) -> bool:
    """Require every release entry field declared by the occlusion contract."""
    return any(
        entry.get("kind") == "map"
        and entry.get("qa_status") == "validated"
        and entry.get("source") == contract["source"]
        and entry.get("source_run") == contract["source_run"]
        and entry.get("destination") == contract["destination"]
        and entry.get("bytes") == contract["bytes"]
        and entry.get("sha256") == contract["sha256"]
        and entry.get("component_id") == contract["component_id"]
        and entry.get("component_label") == contract["component_label"]
        and entry.get("payload_group") == contract["payload_group"]
        for contract in contracts
    )


def adapt_maps(
    builder: RegistryBuilder,
    map_groups: Mapping[str, list[dict[str, Any]]],
    auxiliary_contracts: Mapping[str, list[dict[str, Any]]],
) -> None:
    path = "areas.csv"
    content_path = "releases/BG2-HD-Upscale/manifests/content.json"
    rows = builder.inputs.read_csv(path)
    seen_areas: set[str] = set()
    stale_source_statuses: list[str] = []
    for row_index, row in enumerate(rows, 2):
        area = row.get("area_id", "").strip().upper()
        if not area:
            builder.anomaly(
                "missing-identity",
                "error",
                "maps",
                "ligne areas.csv sans area_id",
                source=f"{path}:{row_index}",
            )
            continue
        if area in seen_areas:
            builder.anomaly(
                "duplicate-source-row",
                "error",
                "maps",
                "area_id dupliqué dans areas.csv",
                asset_id=f"maps:{area}:day",
                source=path,
            )
        seen_areas.add(area)

        variants = [
            {
                "name": "day",
                "content_area": area,
                "source_field": "x1_tuiles_principales",
                "run_field": "runs",
                "build_field": "build",
                "status_field": "status",
            }
        ]
        if row.get("has_night_variant") == "yes":
            variants.append(
                {
                    "name": "night",
                    "content_area": f"{area}N",
                    "source_field": "x1_tuiles_principales_nuit",
                    "run_field": "runs_nuit",
                    "build_field": "build_nuit",
                    "status_field": "status_nuit",
                }
            )

        for variant in variants:
            name = variant["name"]
            asset_id = f"maps:{area}:{name}"
            locator = f"csv:area_id={area};variant={name}"
            source_extracted = row.get(variant["source_field"]) == "yes"
            states = default_states()
            states.update(
                {
                    "source": "extracted" if source_extracted else "available",
                    "production": "not-started",
                    "installation": "not-installed",
                }
            )
            status = row.get(variant["status_field"], "").strip()
            legacy: list[dict[str, str]] = []
            if status:
                fragment = builder.map_status(
                    "maps.areas.status.v1",
                    status,
                    domain="maps",
                    asset_id=asset_id,
                    source=path,
                )
                if fragment is None:
                    states.update(
                        {
                            "production": "unknown",
                            "qa": "not-assessed",
                            "installation": "unknown",
                        }
                    )
                else:
                    mapped_source = fragment.get("source")
                    if mapped_source is not None and mapped_source != states["source"]:
                        stale_source_statuses.append(asset_id)
                    fragment = {
                        axis: value for axis, value in fragment.items() if axis != "source"
                    }
                    apply_fragment(
                        builder,
                        states,
                        fragment,
                        domain="maps",
                        asset_id=asset_id,
                        source=path,
                    )
                legacy.append(
                    {
                        "field": variant["status_field"],
                        "value": status,
                        "mapping": "maps.areas.status.v1",
                    }
                )

            selected_run_text = row.get(variant["run_field"], "").strip()
            selected_runs = [value.strip() for value in selected_run_text.split(";") if value.strip()]
            build_value = row.get(variant["build_field"], "").strip()
            selections: list[dict[str, Any]] = []
            for selected_run in selected_runs:
                selections.append(
                    {
                        "role": "run",
                        "id": selected_run,
                        "source": source_ref(path, f"{locator};field={variant['run_field']}"),
                    }
                )

            evidence: list[dict[str, str]] = []
            provenance_state = "not-applicable"
            if selected_runs:
                evidence.append(evidence_ref(builder.inputs, path, locator))
                provenance_state = "complete" if build_value else "partial"
            elif states["production"] in PRODUCED or states["installation"] == "installed":
                provenance_state = "missing"
                builder.anomaly(
                    "missing-selected-run",
                    "error",
                    "maps",
                    "asset produit ou installé sans run sélectionné structuré",
                    asset_id=asset_id,
                    source=path,
                )

            content_entries = list(map_groups.get(variant["content_area"], []))
            if content_entries:
                content_runs = sorted(
                    {str(entry.get("source_run", "")) for entry in content_entries}
                )
                content_valid = all(
                    entry.get("qa_status") == "validated" for entry in content_entries
                )
                area_contracts = auxiliary_contracts.get(variant["content_area"], [])
                run_matches = bool(selected_runs) and all(
                    any(
                        f"/runs/{selected_run}/" in f"/{str(entry.get('source_run', '')).strip('/')}"
                        for selected_run in selected_runs
                    )
                    or entry_matches_auxiliary_map_contract(entry, area_contracts)
                    for entry in content_entries
                )
                if states["qa"] != "passed" or not content_valid or not run_matches:
                    states["release"] = "blocked"
                    builder.anomaly(
                        "release-selection-mismatch",
                        "error",
                        "maps",
                        "contenu release présent mais statut QA ou run canonique divergent",
                        asset_id=asset_id,
                        source=content_path,
                        details={
                            "selected_runs": selected_runs,
                            "content_runs": content_runs,
                            "content_qa_validated": content_valid,
                        },
                    )
                else:
                    states["release"] = "integrated"
                    evidence.append(
                        evidence_ref(
                            builder.inputs,
                            content_path,
                            f"json:entries[kind=map;area={variant['content_area']}]",
                        )
                    )
                    provenance_state = "verified"

            builder.add(
                base_record(
                    asset_id=asset_id,
                    domain="maps",
                    asset_type="area-map",
                    canonical_path=path,
                    locator=locator,
                    states=states,
                    provenance_state=provenance_state,
                    evidence=evidence,
                    selections=selections,
                    legacy=legacy,
                    adapter="maps.areas.v1",
                )
            )

    if stale_source_statuses:
        builder.anomaly(
            "map-source-status-stale",
            "warning",
            "maps",
            "des libellés source-pending historiques contredisent les colonnes x1 extraites ; les colonnes dédiées prévalent",
            source=path,
            details={
                "affected_count": len(stale_source_statuses),
                "examples": sorted(stale_source_statuses)[:20],
            },
        )


def _current_animation_selection(
    builder: RegistryBuilder,
    selection_path: str,
    expected_resref: str,
) -> tuple[dict[str, str] | None, list[str]]:
    """Resolve and verify one mutable selection and its immutable QA decision."""

    errors: list[str] = []
    try:
        selection = builder.inputs.read_json(selection_path)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as error:
        return None, [f"sélection illisible: {error}"]
    if not isinstance(selection, Mapping):
        return None, ["objet JSON de sélection attendu"]

    resref = str(selection.get("resref", "")).upper()
    if resref != expected_resref:
        errors.append("resref incohérent avec le nom du fichier")
    if selection.get("schema_version") != 1:
        errors.append("schema_version de sélection invalide")
    if selection.get("asset_id") != f"animations:bam:{expected_resref}":
        errors.append("asset_id de sélection incohérent")
    if parse_timestamp(str(selection.get("updated_at_utc", ""))) is None:
        errors.append("updated_at_utc de sélection invalide")

    decision_ref = selection.get("qa_decision")
    if not isinstance(decision_ref, Mapping):
        errors.append("référence qa_decision absente ou invalide")
        return None, errors
    decision_path = str(decision_ref.get("path", ""))
    decision_hash = str(decision_ref.get("sha256", ""))
    expected_prefix = f"{ANIMATION_DECISIONS_ROOT}/{expected_resref}/"
    if (
        not canonical_relative_path(decision_path)
        or not decision_path.startswith(expected_prefix)
        or not decision_path.endswith(".json")
    ):
        errors.append("chemin de décision hors autorité canonique")
    if decision_ref.get("status") != "accepted":
        errors.append("statut de décision sélectionnée non accepté")
    if not SHA256_RE.fullmatch(decision_hash):
        errors.append("hash de décision invalide")

    decision: Mapping[str, Any] | None = None
    actual_decision_hash = ""
    if decision_path and not errors:
        try:
            decision_value = builder.inputs.read_json(decision_path)
            actual_decision_hash = builder.inputs.digest(decision_path)
            if isinstance(decision_value, Mapping):
                decision = decision_value
            else:
                errors.append("objet JSON de décision attendu")
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"décision illisible: {error}")
    if actual_decision_hash and actual_decision_hash != decision_hash:
        errors.append("hash de décision différent de la sélection")
    if decision is None:
        return None, errors

    if decision.get("schema_version") != 1:
        errors.append("schema_version de décision invalide")
    decision_id = str(decision.get("decision_id", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", decision_id):
        errors.append("decision_id invalide")
    if str(decision.get("resref", "")).upper() != expected_resref:
        errors.append("resref de décision incohérent")
    if decision.get("asset_id") != f"animations:bam:{expected_resref}":
        errors.append("asset_id de décision incohérent")
    if decision.get("status") != "accepted":
        errors.append("décision QA non acceptée")
    if decision.get("decision_origin") != "explicit-user-ingame-qa":
        errors.append("origine de décision QA non explicite")
    if not str(decision.get("decision", "")).strip():
        errors.append("texte de décision QA absent")
    if parse_timestamp(str(decision.get("recorded_at_utc", ""))) is None:
        errors.append("recorded_at_utc de décision invalide")
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", str(decision.get("decision_date", ""))
    ):
        errors.append("decision_date invalide")
    if decision_ref.get("decision_date") != decision.get("decision_date"):
        errors.append("date de décision incohérente")
    result_kind = str(decision.get("result_kind", ""))
    if result_kind not in {"x4", "native"}:
        errors.append("result_kind de décision invalide")
    if selection.get("result_kind") != result_kind:
        errors.append("result_kind diffère entre sélection et décision")
    for key in ("tested_areas",):
        if selection.get(key) != decision.get(key):
            errors.append(f"{key} diffère entre sélection et décision")
    tested_areas = decision.get("tested_areas")
    if not isinstance(tested_areas, list) or not tested_areas or any(
        not re.fullmatch(r"(?:AR|OH)[0-9]{4}", str(area)) for area in tested_areas
    ):
        errors.append("tested_areas invalide")

    resolved: dict[str, str] = {
        "selection_path": selection_path,
        "selection_sha256": builder.inputs.digest(selection_path),
        "decision_path": decision_path,
        "decision_sha256": actual_decision_hash,
        "decision_id": decision_id,
        "decision_date": str(decision.get("decision_date", "")),
        "result_kind": result_kind,
    }
    if result_kind == "x4":
        for key in ("lineage", "source_pack"):
            if selection.get(key) != decision.get(key):
                errors.append(f"{key} diffère entre sélection et décision")
        if selection.get("selected_run") != decision.get("final_run"):
            errors.append("selected_run diffère du run final de la décision")
        if "native_source" in selection or "native_source" in decision:
            errors.append("native_source interdit pour un résultat x4")
        final_run = decision.get("final_run")
        if not isinstance(final_run, Mapping):
            errors.append("run final absent de la décision")
            return None, errors
        final_run_path = str(final_run.get("path", ""))
        final_manifest_path = str(final_run.get("manifest_path", ""))
        final_manifest_hash = str(final_run.get("manifest_sha256", ""))
        if not canonical_relative_path(final_run_path) or not canonical_relative_path(
            final_manifest_path
        ):
            errors.append("chemin du run final non canonique")
        if not SHA256_RE.fullmatch(final_manifest_hash):
            errors.append("hash de manifeste du run final invalide")
        try:
            run_directory = builder.inputs.absolute(final_run_path)
            manifest_file = builder.inputs.absolute(final_manifest_path)
            if not run_directory.is_dir():
                errors.append("répertoire du run final absent")
            if manifest_file != run_directory / "manifest.json":
                errors.append("manifeste du run final hors de son emplacement canonique")
            if not manifest_file.is_file():
                errors.append("manifeste du run final absent")
            else:
                final_manifest = builder.inputs.read_json(final_manifest_path)
                actual_manifest_hash = builder.inputs.digest(final_manifest_path)
                if actual_manifest_hash != final_manifest_hash:
                    errors.append("hash du manifeste du run final incohérent")
                if not isinstance(final_manifest, Mapping):
                    errors.append("objet JSON attendu pour le manifeste du run final")
                elif (
                    final_manifest.get("schema") != final_run.get("schema")
                    or final_manifest.get("status") != final_run.get("status")
                ):
                    errors.append("identité du manifeste du run final incohérente")
        except (FileNotFoundError, ValueError) as error:
            errors.append(f"chemin du run final invalide: {error}")
        resolved.update(
            {
                "selected_artifact_path": final_manifest_path,
                "selected_artifact_sha256": final_manifest_hash,
                "selection_id": final_run_path,
                "final_run_path": final_run_path,
                "final_manifest_path": final_manifest_path,
                "final_manifest_sha256": final_manifest_hash,
            }
        )
    elif result_kind == "native":
        forbidden = {"selected_run", "lineage", "source_pack"}
        if forbidden & set(selection) or {"final_run", "lineage", "source_pack"} & set(decision):
            errors.append("champs x4 interdits pour un résultat natif")
        native_source = decision.get("native_source")
        if selection.get("native_source") != native_source or not isinstance(native_source, Mapping):
            errors.append("native_source absent ou différent entre sélection et décision")
        else:
            native_path = str(native_source.get("path", ""))
            native_hash = str(native_source.get("sha256", ""))
            expected_path = f"animations/ressources/{expected_resref}/source.bam"
            if native_path != expected_path or not SHA256_RE.fullmatch(native_hash):
                errors.append("chemin/hash de source native invalide")
            try:
                source_file = builder.inputs.absolute(native_path)
                if not source_file.is_file():
                    errors.append("source BAM native absente")
                elif builder.inputs.digest(native_path) != native_hash:
                    errors.append("hash de source BAM native incohérent")
                if source_file.is_file() and source_file.stat().st_size != int(native_source.get("bytes", -1)):
                    errors.append("taille de source BAM native incohérente")
                inventory_rows = builder.inputs.read_csv(ANIMATION_RESOURCES_PATH)
                matching_rows = [
                    row
                    for row in inventory_rows
                    if str(row.get("bam_resref", "")).upper() == expected_resref
                ]
                if len(matching_rows) != 1:
                    errors.append("ligne native unique absente de ressources.csv")
                else:
                    inventory_row = matching_rows[0]
                    if canonical_row_sha256(inventory_row) != native_source.get("inventory_row_sha256"):
                        errors.append("empreinte de ligne native incohérente")
                    if str(inventory_row.get("sha256", "")).upper() != native_hash:
                        errors.append("hash natif différent de ressources.csv")
            except (FileNotFoundError, ValueError, TypeError) as error:
                errors.append(f"source native invalide: {error}")
            resolved.update(
                {
                    "selected_artifact_path": native_path,
                    "selected_artifact_sha256": native_hash,
                    "selection_id": native_path,
                    "native_source_path": native_path,
                    "native_source_sha256": native_hash,
                }
            )

    if not errors:
        try:
            workflow_result = check_animation_workspace(builder.root, expected_resref)
        except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
            errors.append(f"validation workflow impossible: {error}")
        else:
            if not workflow_result.get("ok"):
                errors.extend(
                    f"workflow: {message}"
                    for message in workflow_result.get("errors", ["erreur non détaillée"])
                )
    if errors:
        return None, errors
    return resolved, []


def load_current_animation_qa(
    builder: RegistryBuilder,
) -> tuple[dict[str, dict[str, str]], set[str]]:
    """Return valid current QA chains and every resref declaring a selection."""

    selected: dict[str, dict[str, str]] = {}
    declared: set[str] = set()
    root = builder.root / ANIMATION_SELECTIONS_ROOT
    if not root.is_dir():
        return selected, declared
    for path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
        expected_resref = path.stem.upper()
        relative = repo_path(builder.root, path)
        if path.stem != expected_resref or not ANIMATION_RESREF_RE.fullmatch(expected_resref):
            builder.anomaly(
                "invalid-animation-selection",
                "error",
                "animations",
                "nom de fichier de sélection animation invalide",
                source=relative,
            )
            continue
        declared.add(expected_resref)
        resolved, errors = _current_animation_selection(builder, relative, expected_resref)
        if errors:
            builder.anomaly(
                "invalid-animation-selection",
                "error",
                "animations",
                "la sélection animation courante ne forme pas une chaîne QA vérifiable",
                asset_id=f"animations:bam:{expected_resref}",
                source=relative,
                details={"errors": errors},
            )
            continue
        if resolved is not None:
            selected[expected_resref] = resolved
    return selected, declared


def load_legacy_release_animation_qa(
    builder: RegistryBuilder,
) -> dict[str, list[dict[str, str]]]:
    """Keep only pre-contract QA pinned by the canonical release candidate register."""

    approvals: dict[str, list[dict[str, str]]] = {}
    document = builder.inputs.read_json(ANIMATION_CANDIDATES_PATH)
    for candidate in document.get("candidates", []):
        if candidate.get("approval_status") not in {
            "approved-for-release",
            "validated-awaiting-manifest-approval",
        }:
            continue
        area = str(candidate.get("area", "")).upper()
        required_resrefs = {
            str(value).upper() for value in candidate.get("required_resrefs", [])
        }
        qa_path = str(candidate.get("qa_approval", ""))
        declared_hash = str(candidate.get("qa_approval_sha256", ""))
        if (
            not required_resrefs
            or not qa_path.startswith(
                "releases/BG2-HD-Upscale/manifests/animation-qa-approvals/"
            )
            or not SHA256_RE.fullmatch(declared_hash)
            or not builder.inputs.exists(qa_path)
        ):
            continue
        approval = builder.inputs.read_json(qa_path)
        actual_hash = builder.inputs.digest(qa_path)
        approval_resrefs = {
            str(value).upper() for value in approval.get("required_resrefs", [])
        }
        if not (
            approval.get("status") == "accepted"
            and approval.get("decision_origin") == "preserved-existing-user-qa"
            and str(approval.get("area", "")).upper() == area
            and approval_resrefs == required_resrefs
            and actual_hash == declared_hash
        ):
            continue
        locator = f"json:candidates[area={area}]"
        for resref in required_resrefs:
            if not ANIMATION_RESREF_RE.fullmatch(resref):
                continue
            approvals.setdefault(resref, []).extend(
                (
                    {
                        "path": ANIMATION_CANDIDATES_PATH,
                        "locator": locator,
                        "sha256": builder.inputs.digest(ANIMATION_CANDIDATES_PATH),
                    },
                    {
                        "path": qa_path,
                        "locator": f"json:required_resrefs[{resref}]",
                        "sha256": actual_hash,
                    },
                )
            )
    return approvals


def adapt_animation_bams(builder: RegistryBuilder) -> set[str]:
    registry_path = "animations/index/animation_upscale_registry.csv"
    resources_path = "animations/index/ressources.csv"
    alpha_path = "animations/index/animation_alpha_corrections.csv"
    manifest_path = "animations/index/manifest.json"
    registry_rows = builder.inputs.read_csv(registry_path)
    resource_rows = builder.inputs.read_csv(resources_path)
    alpha_rows = builder.inputs.read_csv(alpha_path)
    manifest = builder.inputs.read_json(manifest_path)
    current_qa_by_resref, declared_selections = load_current_animation_qa(builder)
    legacy_qa_by_resref = load_legacy_release_animation_qa(builder)

    resources: dict[str, dict[str, str]] = {}
    for row in resource_rows:
        resref = row.get("bam_resref", "").upper()
        if resref in resources:
            builder.anomaly(
                "duplicate-source-row",
                "error",
                "animations",
                "bam_resref dupliqué dans ressources.csv",
                asset_id=f"animations:bam:{resref}",
                source=resources_path,
            )
        resources.setdefault(resref, row)

    corrections: dict[str, list[dict[str, str]]] = {}
    for row in alpha_rows:
        corrections.setdefault(row.get("resref", "").upper(), []).append(row)

    registry_resrefs: set[str] = set()
    for row_index, row in enumerate(registry_rows, 2):
        resref = row.get("resref", "").upper()
        asset_id = f"animations:bam:{resref}"
        if not resref:
            builder.anomaly(
                "missing-identity",
                "error",
                "animations",
                "ligne de registre sans resref",
                source=f"{registry_path}:{row_index}",
            )
            continue
        if resref in registry_resrefs:
            builder.anomaly(
                "duplicate-source-row",
                "error",
                "animations",
                "resref dupliqué dans le registre spatial",
                asset_id=asset_id,
                source=registry_path,
            )
            continue
        registry_resrefs.add(resref)
        resource = resources.get(resref)
        source_hash = str(resource.get("sha256", "")) if resource else ""
        source_verified = bool(re.fullmatch(r"[a-fA-F0-9]{64}", source_hash))
        states = default_states()
        states.update(
            {
                "source": "verified" if source_verified else "unavailable",
                "production": "unknown",
                "installation": "unknown",
            }
        )
        status = row.get("status", "").strip()
        fragment = builder.map_status(
            "animations.index.upscale-status.v1",
            status,
            domain="animations",
            asset_id=asset_id,
            source=registry_path,
        )
        legacy: list[dict[str, str]] = []
        if fragment is not None:
            apply_fragment(
                builder,
                states,
                fragment,
                domain="animations",
                asset_id=asset_id,
                source=registry_path,
            )
            legacy.append(
                {
                    "field": "status",
                    "value": status,
                    "mapping": "animations.index.upscale-status.v1",
                }
            )

        selections: list[dict[str, Any]] = []
        evidence: list[dict[str, str]] = []
        correction_rows = corrections.get(resref, [])
        for correction_index, correction in enumerate(correction_rows):
            correction_status = correction.get("status", "").strip()
            correction_fragment = builder.map_status(
                "animations.index.alpha-status.v1",
                correction_status,
                domain="animations",
                asset_id=asset_id,
                source=alpha_path,
            )
            if correction_fragment is not None:
                # Historical correction statuses still describe production and
                # installation, but current in-game QA only comes from the
                # selected decision chain resolved below.
                correction_fragment = {
                    axis: value
                    for axis, value in correction_fragment.items()
                    if axis != "qa"
                }
                apply_fragment(
                    builder,
                    states,
                    correction_fragment,
                    domain="animations",
                    asset_id=asset_id,
                    source=alpha_path,
                )
                legacy.append(
                    {
                        "field": f"alpha_status[{correction_index}]",
                        "value": correction_status,
                        "mapping": "animations.index.alpha-status.v1",
                    }
                )
            correction_id = correction.get("correction_id", "").strip()
            if correction_id:
                selections.append(
                    {
                        "role": "correction",
                        "id": correction_id,
                        "source": source_ref(
                            alpha_path,
                            f"csv:resref={resref};correction_id={correction_id}",
                        ),
                    }
                )
        if len(correction_rows) > 1:
            builder.anomaly(
                "multiple-scoped-corrections",
                "warning",
                "animations",
                "plusieurs corrections canoniques existent pour des portées de zones distinctes",
                asset_id=asset_id,
                source=alpha_path,
                details={
                    "correction_ids": sorted(
                        row.get("correction_id", "") for row in correction_rows
                    )
                },
            )

        registry_correction = row.get("correction_id", "").strip()
        selected_ids = {selection["id"] for selection in selections}
        if registry_correction and registry_correction not in selected_ids:
            selections.append(
                {
                    "role": "correction",
                    "id": registry_correction,
                    "source": source_ref(
                        registry_path,
                        f"csv:resref={resref};field=correction_id",
                    ),
                }
            )

        states["qa"] = "not-assessed"
        current_qa = current_qa_by_resref.get(resref)
        if current_qa:
            expected_current = {
                "status": (
                    "validé-x4"
                    if current_qa["result_kind"] == "x4"
                    else "validé-natif"
                ),
                "selected_run": current_qa.get("final_run_path", ""),
                "qa_decision": current_qa["decision_path"],
                "qa_date": current_qa["decision_date"],
            }
            mismatches = {
                field: {"expected": expected, "actual": row.get(field, "")}
                for field, expected in expected_current.items()
                if row.get(field, "") != expected
            }
            if mismatches:
                builder.anomaly(
                    "animation-selection-registry-mismatch",
                    "error",
                    "animations",
                    "le registre CSV ne reflète pas la sélection animation courante",
                    asset_id=asset_id,
                    source=registry_path,
                    details={"fields": mismatches},
                )
                current_qa = None
        legacy_approvals = (
            [] if resref in declared_selections else legacy_qa_by_resref.get(resref, [])
        )
        if current_qa:
            states["qa"] = "passed"
            evidence.extend(
                (
                    {
                        "path": current_qa["selection_path"],
                        "locator": "json:root",
                        "sha256": current_qa["selection_sha256"],
                    },
                    {
                        "path": current_qa["decision_path"],
                        "locator": "json:root",
                        "sha256": current_qa["decision_sha256"],
                    },
                    {
                        "path": current_qa["selected_artifact_path"],
                        "locator": "json:root" if current_qa["result_kind"] == "x4" else "file:sha256",
                        "sha256": current_qa["selected_artifact_sha256"],
                    },
                )
            )
            selections.append(
                {
                    "role": "run" if current_qa["result_kind"] == "x4" else "native-source",
                    "id": current_qa["selection_id"],
                    "source": source_ref(
                        current_qa["selection_path"],
                        "json:selected_run"
                        if current_qa["result_kind"] == "x4"
                        else "json:native_source",
                    ),
                }
            )
        elif resref in declared_selections:
            states["qa"] = "blocked"
        elif legacy_approvals:
            states["qa"] = "passed"
            evidence.extend(legacy_approvals)

        if resource is None:
            builder.anomaly(
                "missing-resource-row",
                "error",
                "animations",
                "resref du registre absent de ressources.csv",
                asset_id=asset_id,
                source=resources_path,
            )
        if states["production"] in {"verified", "in-progress", "blocked"}:
            evidence.extend(
                [
                    evidence_ref(builder.inputs, registry_path, f"csv:resref={resref}"),
                    evidence_ref(builder.inputs, resources_path, f"csv:bam_resref={resref}"),
                ]
            )
        if correction_rows:
            evidence.append(
                evidence_ref(builder.inputs, alpha_path, f"csv:resref={resref}")
            )

        if selections:
            provenance_state = "complete"
        elif states["production"] == "verified":
            provenance_state = "partial"
        else:
            provenance_state = "not-applicable"
        if current_qa:
            provenance_state = "verified"
        elif legacy_approvals and selections:
            provenance_state = "verified"
        elif legacy_approvals and provenance_state == "not-applicable":
            provenance_state = "partial"

        builder.add(
            base_record(
                asset_id=asset_id,
                domain="animations",
                asset_type="area-animation-bam",
                canonical_path=registry_path,
                locator=f"csv:resref={resref}",
                states=states,
                provenance_state=provenance_state,
                evidence=evidence,
                selections=selections,
                legacy=legacy,
                adapter="animations.index.v2",
            )
        )

    extra_resources = sorted(set(resources) - registry_resrefs)
    if extra_resources:
        builder.anomaly(
            "untracked-animation-resources",
            "error",
            "animations",
            "ressources BAM extraites absentes du registre spatial",
            source=resources_path,
            details={"count": len(extra_resources), "examples": extra_resources[:20]},
        )
    if manifest.get("missing_bams") or manifest.get("failures"):
        builder.anomaly(
            "animation-inventory-failures",
            "error",
            "animations",
            "le manifeste d'inventaire signale des BAM manquants ou des échecs",
            source=manifest_path,
            details={
                "missing_bams": manifest.get("missing_bams", []),
                "failures": manifest.get("failures", []),
            },
        )
    return registry_resrefs


def adapt_animation_candidates(
    builder: RegistryBuilder,
    registry_resrefs: set[str],
    animation_groups: Mapping[str, list[dict[str, Any]]],
) -> None:
    candidate_path = ANIMATION_CANDIDATES_PATH
    content_path = "releases/BG2-HD-Upscale/manifests/content.json"
    document = builder.inputs.read_json(candidate_path)
    seen_areas: set[str] = set()
    for index, candidate in enumerate(document.get("candidates", [])):
        area = str(candidate.get("area", "")).upper()
        asset_id = f"animations:pack:{area}"
        locator = f"json:candidates[area={area}]"
        if area in seen_areas:
            builder.anomaly(
                "duplicate-release-candidate",
                "error",
                "animations",
                "plusieurs candidats release pour la même zone",
                asset_id=asset_id,
                source=candidate_path,
            )
            continue
        seen_areas.add(area)

        required_resrefs = [str(value).upper() for value in candidate.get("required_resrefs", [])]
        missing_resrefs = sorted(set(required_resrefs) - registry_resrefs)
        qa_path = str(candidate.get("qa_approval", ""))
        qa_valid = False
        qa_actual_hash = ""
        qa_document: dict[str, Any] = {}
        if qa_path and builder.inputs.exists(qa_path):
            qa_document = builder.inputs.read_json(qa_path)
            qa_actual_hash = builder.inputs.digest(qa_path)
            qa_valid = (
                qa_document.get("status") == "accepted"
                and str(qa_document.get("area", "")).upper() == area
                and set(str(value).upper() for value in qa_document.get("required_resrefs", []))
                == set(required_resrefs)
                and qa_actual_hash == str(candidate.get("qa_approval_sha256", "")).upper()
            )
        else:
            builder.anomaly(
                "missing-pinned-qa-approval",
                "error",
                "animations",
                "attestation QA épinglée absente",
                asset_id=asset_id,
                source=qa_path or candidate_path,
            )

        if missing_resrefs:
            builder.anomaly(
                "candidate-member-missing",
                "error",
                "animations",
                "le candidat référence des resrefs absents de l'inventaire canonique",
                asset_id=asset_id,
                source=candidate_path,
                details={"missing_resrefs": missing_resrefs},
            )
        if qa_path and not qa_valid:
            builder.anomaly(
                "pinned-qa-mismatch",
                "error",
                "animations",
                "attestation QA absente, divergente ou hashée différemment",
                asset_id=asset_id,
                source=qa_path,
                details={
                    "declared_sha256": candidate.get("qa_approval_sha256", ""),
                    "actual_sha256": qa_actual_hash,
                },
            )

        states = default_states()
        states.update(
            {
                "source": "verified" if not missing_resrefs else "available",
                "production": "verified" if not missing_resrefs else "blocked",
                "qa": "passed" if qa_valid else "blocked",
                "installation": "unknown",
            }
        )
        approval_status = str(candidate.get("approval_status", ""))
        approval_fragment = builder.map_status(
            "release.animation.approval-status.v1",
            approval_status,
            domain="animations",
            asset_id=asset_id,
            source=candidate_path,
        )
        if approval_fragment and qa_valid and not missing_resrefs:
            apply_fragment(
                builder,
                states,
                approval_fragment,
                domain="animations",
                asset_id=asset_id,
                source=candidate_path,
            )
        else:
            states["release"] = "blocked"

        content_entries = list(animation_groups.get(area, []))
        content_valid = bool(content_entries) and all(
            entry.get("qa_status") == "validated"
            and entry.get("payload_group") == candidate.get("payload_group")
            and str(entry.get("source", "")).startswith(str(candidate.get("source_pack", "")) + "/")
            for entry in content_entries
        )
        if content_entries and not content_valid:
            builder.anomaly(
                "release-content-mismatch",
                "error",
                "animations",
                "content.json ne correspond pas exactement au candidat de zone",
                asset_id=asset_id,
                source=content_path,
            )
            states["release"] = "blocked"
        elif content_valid and states["release"] in {"eligible", "approved"}:
            states["release"] = "integrated"

        evidence = [
            evidence_ref(builder.inputs, candidate_path, locator),
        ]
        if qa_valid:
            evidence.append(evidence_ref(builder.inputs, qa_path, "json:root"))
        if content_valid:
            evidence.append(
                evidence_ref(
                    builder.inputs,
                    content_path,
                    f"json:entries[kind=area-animation;area={area}]",
                )
            )
        provenance_state = "verified" if qa_valid and not missing_resrefs else "partial"
        if states["release"] in RELEASE_PROGRESS and provenance_state != "verified":
            states["release"] = "blocked"

        selection_id = str(candidate.get("source_pack", "")) or f"candidate-{index}"
        builder.add(
            base_record(
                asset_id=asset_id,
                domain="animations",
                asset_type="area-animation-pack",
                canonical_path=candidate_path,
                locator=locator,
                states=states,
                provenance_state=provenance_state,
                evidence=evidence,
                selections=[
                    {
                        "role": "candidate",
                        "id": selection_id,
                        "source": source_ref(candidate_path, locator),
                    }
                ],
                legacy=[
                    {
                        "field": "approval_status",
                        "value": approval_status,
                        "mapping": "release.animation.approval-status.v1",
                    }
                ],
                adapter="animations.release-candidates.v1",
            )
        )


def adapt_sprites(builder: RegistryBuilder) -> None:
    family_path = "sprite/index/sprite_families.csv"
    manifest_path = "sprite/index/manifest.json"
    current_path = (
        "sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/"
        "runs/catalog-xbr2x-x2/current-generation.json"
    )
    active_path = (
        "sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/"
        "runs/catalog-xbr2x-x2/ingame-installation/active-test.json"
    )
    families = builder.inputs.read_csv(family_path)
    inventory = builder.inputs.read_json(manifest_path)
    inventory_status = str(inventory.get("status", ""))
    inventory_fragment = builder.map_status(
        "sprites.index.manifest-status.v1",
        inventory_status,
        domain="sprites",
        asset_id="sprites:index",
        source=manifest_path,
    )
    inventory_verified = bool(inventory_fragment and inventory_fragment.get("source") == "verified")

    active_members: set[tuple[str, str]] = set()
    active_integrity = True
    current: dict[str, Any] = {}
    active: dict[str, Any] = {}
    build: dict[str, Any] = {}
    build_path = ""
    build_fragment: dict[str, str] | None = None
    active_fragment: dict[str, str] | None = None
    if builder.inputs.exists(current_path) and builder.inputs.exists(active_path):
        current = builder.inputs.read_json(current_path)
        active = builder.inputs.read_json(active_path)
        generation_dir = str(current.get("generation_dir", ""))
        build_path = f"{generation_dir.rstrip('/')}/{current.get('build_manifest', '')}"
        if not builder.inputs.exists(build_path):
            active_integrity = False
            builder.anomaly(
                "sprite-build-manifest-missing",
                "error",
                "sprites",
                "build manifest de la génération courante absent",
                source=build_path,
            )
        else:
            build = builder.inputs.read_json(build_path)
            actual_build_hash = builder.inputs.digest(build_path)
            if actual_build_hash != str(current.get("build_manifest_sha256", "")).upper():
                active_integrity = False
                builder.anomaly(
                    "sprite-build-hash-mismatch",
                    "error",
                    "sprites",
                    "hash du build manifest différent de current-generation.json",
                    source=build_path,
                    details={
                        "declared": current.get("build_manifest_sha256", ""),
                        "actual": actual_build_hash,
                    },
                )
            build_fragment = builder.map_status(
                "sprites.build.status.v1",
                str(build.get("status", "")),
                domain="sprites",
                asset_id="sprites:catalog:current",
                source=build_path,
            )
            for member in build.get("source_members", []):
                animation_id = str(member.get("animation_id", ""))
                raw_prefixes = member.get("bam_prefixes", [])
                prefixes = raw_prefixes if isinstance(raw_prefixes, list) else str(raw_prefixes).split()
                for prefix in prefixes:
                    active_members.add((animation_id, prefix))
        if active.get("generation_id") != current.get("generation_id"):
            active_integrity = False
            builder.anomaly(
                "sprite-active-generation-mismatch",
                "error",
                "sprites",
                "active-test.json ne référence pas la génération courante",
                source=active_path,
            )
        active_fragment = builder.map_status(
            "sprites.installation.status.v1",
            str(active.get("status", "")),
            domain="sprites",
            asset_id="sprites:catalog:current",
            source=active_path,
        )
    else:
        active_integrity = False
        builder.anomaly(
            "sprite-active-state-unavailable",
            "warning",
            "sprites",
            "état courant du catalogue ou installation active absent",
            source=current_path,
        )

    seen_families: set[str] = set()
    matched_active = 0
    for row_index, row in enumerate(families, 2):
        family_id = row.get("family_id", "").strip()
        asset_id = f"sprites:family:{family_id}"
        if not family_id:
            builder.anomaly(
                "missing-identity",
                "error",
                "sprites",
                "famille sans family_id",
                source=f"{family_path}:{row_index}",
            )
            continue
        if family_id in seen_families:
            builder.anomaly(
                "duplicate-source-row",
                "error",
                "sprites",
                "family_id dupliqué",
                asset_id=asset_id,
                source=family_path,
            )
            continue
        seen_families.add(family_id)
        try:
            resource_count = int(row.get("resource_count", "0") or 0)
        except ValueError:
            resource_count = 0
            builder.anomaly(
                "invalid-resource-count",
                "error",
                "sprites",
                "resource_count non numérique",
                asset_id=asset_id,
                source=family_path,
            )
        states = default_states()
        states.update(
            {
                "source": "verified" if inventory_verified and resource_count > 0 else "unavailable",
                "production": "unknown",
                "installation": "not-installed" if active_integrity else "unknown",
            }
        )
        readiness = row.get("pipeline_ready", "").strip()
        readiness_fragment = builder.map_status(
            "sprites.index.pipeline-ready.v1",
            readiness,
            domain="sprites",
            asset_id=asset_id,
            source=family_path,
        )
        if readiness_fragment:
            apply_fragment(
                builder,
                states,
                readiness_fragment,
                domain="sprites",
                asset_id=asset_id,
                source=family_path,
            )
        legacy = [
            {
                "field": "pipeline_ready",
                "value": readiness,
                "mapping": "sprites.index.pipeline-ready.v1",
            }
        ]
        pair = (row.get("animation_id", ""), row.get("bam_prefix", ""))
        is_active = pair in active_members
        selections: list[dict[str, Any]] = []
        evidence: list[dict[str, str]] = []
        provenance_state = "not-applicable"
        if is_active:
            matched_active += 1
            if build_fragment:
                apply_fragment(
                    builder,
                    states,
                    build_fragment,
                    domain="sprites",
                    asset_id=asset_id,
                    source=build_path,
                )
            if active_fragment:
                apply_fragment(
                    builder,
                    states,
                    active_fragment,
                    domain="sprites",
                    asset_id=asset_id,
                    source=active_path,
                )
                legacy.append(
                    {
                        "field": "active-test.status",
                        "value": str(active.get("status", "")),
                        "mapping": "sprites.installation.status.v1",
                    }
                )
            generation_id = str(current.get("generation_id", ""))
            selections.append(
                {
                    "role": "generation",
                    "id": generation_id,
                    "source": source_ref(current_path, "json:generation_id"),
                }
            )
            evidence.extend(
                [
                    evidence_ref(builder.inputs, manifest_path, "json:root"),
                    evidence_ref(builder.inputs, current_path, "json:root"),
                    evidence_ref(builder.inputs, build_path, "json:root"),
                    evidence_ref(builder.inputs, active_path, "json:root"),
                ]
            )
            provenance_state = "verified" if active_integrity else "partial"
            if readiness != "yes" or resource_count <= 0:
                builder.anomaly(
                    "active-sprite-not-ready",
                    "error",
                    "sprites",
                    "famille active mais inventaire courant non prêt",
                    asset_id=asset_id,
                    source=family_path,
                )

        builder.add(
            base_record(
                asset_id=asset_id,
                domain="sprites",
                asset_type="sprite-family",
                canonical_path=family_path,
                locator=f"csv:family_id={family_id}",
                states=states,
                provenance_state=provenance_state,
                evidence=evidence,
                selections=selections,
                legacy=legacy,
                adapter="sprites.families.v1",
            )
        )

    if active_members and matched_active != len(active_members):
        builder.anomaly(
            "sprite-active-membership-gap",
            "error",
            "sprites",
            "certains membres du catalogue actif ne correspondent à aucune famille",
            source=build_path,
            details={"declared": len(active_members), "matched": matched_active},
        )
    unavailable_count = sum(
        int(row.get("resource_count", "0") or 0) == 0 for row in families
    )
    if unavailable_count:
        builder.anomaly(
            "sprite-families-without-resources",
            "info",
            "sprites",
            "familles connues sans ressource BAM dans l'inventaire courant",
            source=family_path,
            details={"affected_count": unavailable_count},
        )


def adapt_ui(
    builder: RegistryBuilder,
    ui_groups: Mapping[str, list[dict[str, Any]]],
) -> None:
    extraction_path = "interface/menus-options-bg2ee/reference/extraction-manifest.json"
    sprite_path = (
        "interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50/sprite-manifest.json"
    )
    selector_path = (
        "interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50/"
        "selection-des-trois-jeux/assets/asset-manifest.json"
    )
    content_path = "releases/BG2-HD-Upscale/manifests/content.json"
    hud_path = "interface/gameplay-hud-bg2ee/index/resources.csv"
    hud_claimed = {
        (row.get("resref", "").upper(), row.get("format", "").upper())
        for row in builder.inputs.read_csv(hud_path)
    }
    extraction = builder.inputs.read_json(extraction_path)
    seen_resources: set[str] = set()
    content_hash_groups: dict[str, list[str]] = {}
    dependency_rows_skipped = 0
    hud_rows_skipped = 0
    for index, resource in enumerate(extraction.get("resources", [])):
        name = str(resource.get("resource", "")).upper()
        if not name:
            builder.anomaly(
                "missing-identity",
                "error",
                "ui",
                "ressource UI extraite sans identité",
                source=f"{extraction_path}:resources[{index}]",
            )
            continue
        asset_id = f"ui:source:{stable_token(name)}"
        if name in seen_resources:
            builder.anomaly(
                "duplicate-source-row",
                "error",
                "ui",
                "ressource dupliquée dans le manifeste d'extraction",
                asset_id=asset_id,
                source=extraction_path,
            )
            continue
        seen_resources.add(name)
        kind_raw = str(resource.get("kind", "resource")).upper()
        resref = Path(name).stem.upper()
        if kind_raw == "PVRZ":
            dependency_rows_skipped += 1
            continue
        if (resref, kind_raw) in hud_claimed:
            hud_rows_skipped += 1
            continue
        declared_hash = str(resource.get("sha256", ""))
        source_verified = bool(re.fullmatch(r"[a-fA-F0-9]{64}", declared_hash))
        if source_verified:
            content_hash_groups.setdefault(declared_hash.lower(), []).append(asset_id)
        kind = stable_token(kind_raw.lower())
        states = default_states()
        states.update(
            {
                "source": "verified" if source_verified else "extracted",
                "production": "unknown",
                "installation": "not-applicable",
            }
        )
        builder.add(
            base_record(
                asset_id=asset_id,
                domain="ui",
                asset_type=f"ui-{kind}",
                canonical_path=extraction_path,
                locator=f"json:resources[resource={name}]",
                states=states,
                adapter="ui.extraction.v1",
            )
        )

    duplicate_hashes = [
        asset_ids for asset_ids in content_hash_groups.values() if len(asset_ids) > 1
    ]
    if duplicate_hashes:
        builder.anomaly(
            "duplicate-source-content",
            "info",
            "ui",
            "plusieurs identités UI partagent les mêmes octets source",
            source=extraction_path,
            details={"groups": [sorted(group) for group in sorted(duplicate_hashes)]},
        )
    if extraction.get("failures"):
        builder.anomaly(
            "ui-extraction-failures",
            "error",
            "ui",
            "le manifeste d'extraction UI signale des échecs",
            source=extraction_path,
            details={"failures": extraction.get("failures")},
        )
    source_game = str(extraction.get("source_game", ""))
    if re.match(r"^[A-Za-z]:[\\/]", source_game):
        builder.anomaly(
            "hardcoded-source-path",
            "warning",
            "ui",
            "le manifeste UI conserve un chemin absolu de jeu non portable",
            source=extraction_path,
            details={"source_game": source_game},
        )
    if dependency_rows_skipped or hud_rows_skipped:
        builder.anomaly(
            "ui-source-rows-reclassified",
            "info",
            "ui",
            "ressources brutes exclues de la projection historique car elles sont désormais des dépendances PVRZ ou des assets HUD canoniques",
            source=extraction_path,
            details={
                "pvrz_dependency_rows": dependency_rows_skipped,
                "hud_rows": hud_rows_skipped,
            },
        )

    components = (
        {
            "asset_id": "ui:component:main-menu-x4",
            "asset_type": "ui-atlas-set",
            "canonical_path": sprite_path,
            "locator": "json:root",
            "content_label": "ui-mainmenu-x4",
            "selection_id": "x4-topaz-recovery-v2-d50-main-menu",
            "expected_assets": None,
        },
        {
            "asset_id": "ui:component:selector-x4",
            "asset_type": "ui-atlas-set",
            "canonical_path": selector_path,
            "locator": "json:root",
            "content_label": "ui-selector-x4",
            "selection_id": "x4-topaz-recovery-v2-d50-selector",
            "expected_assets": {
                str(item.get("asset", ""))
                for item in builder.inputs.read_json(selector_path)
            },
        },
    )
    builder.inputs.read_json(sprite_path)
    for component in components:
        asset_id = component["asset_id"]
        content_entries = list(ui_groups.get(component["content_label"], []))
        content_assets = {Path(str(entry.get("source", ""))).name for entry in content_entries}
        expected_assets = component["expected_assets"]
        content_valid = bool(content_entries) and all(
            entry.get("qa_status") == "validated" for entry in content_entries
        )
        if expected_assets is not None and content_assets != expected_assets:
            content_valid = False
            builder.anomaly(
                "ui-content-membership-mismatch",
                "error",
                "ui",
                "les assets du sélecteur divergent entre son manifeste et content.json",
                asset_id=asset_id,
                source=content_path,
                details={
                    "expected": sorted(expected_assets),
                    "content": sorted(content_assets),
                },
            )
        if not content_entries:
            builder.anomaly(
                "ui-release-component-missing",
                "warning",
                "ui",
                "composant UI manifesté absent du contenu release généré",
                asset_id=asset_id,
                source=content_path,
            )
        states = default_states()
        states.update(
            {
                "source": "verified" if content_valid else "available",
                "production": "verified" if content_valid else "unknown",
                "qa": "passed" if content_valid else "not-assessed",
                "installation": "unknown",
                "release": "integrated" if content_valid else "not-evaluated",
            }
        )
        evidence = [
            evidence_ref(
                builder.inputs,
                component["canonical_path"],
                component["locator"],
            )
        ]
        if content_valid:
            evidence.append(
                evidence_ref(
                    builder.inputs,
                    content_path,
                    f"json:entries[component_label={component['content_label']}]",
                )
            )
        builder.add(
            base_record(
                asset_id=asset_id,
                domain="ui",
                asset_type=component["asset_type"],
                canonical_path=component["canonical_path"],
                locator=component["locator"],
                states=states,
                provenance_state="verified" if content_valid else "partial",
                evidence=evidence,
                selections=[
                    {
                        "role": "variant",
                        "id": component["selection_id"],
                        "source": source_ref(
                            component["canonical_path"], component["locator"]
                        ),
                    }
                ],
                adapter="ui.menu-components.v1",
            )
        )

    builder.anomaly(
        "ui-mainmenu-output-manifest-missing",
        "warning",
        "ui",
        "les huit atlas principaux n'ont pas de manifeste d'outputs métier dédié ; projection limitée à la recette et au content généré",
        asset_id="ui:component:main-menu-x4",
        source=sprite_path,
    )


def adapt_animation_wbms(builder: RegistryBuilder) -> None:
    path = "animations/index/occurrences.csv"
    rows = builder.inputs.read_csv(path)
    resrefs = sorted(
        {
            row.get("resource_resref", "").upper()
            for row in rows
            if row.get("resource_kind", "").upper() == "WBM"
            and row.get("resource_resref", "")
        }
    )
    for resref in resrefs:
        asset_id = f"animations:wbm:{stable_token(resref.lower())}"
        states = default_states()
        states.update(
            {
                "source": "available",
                "production": "not-started",
                "installation": "not-applicable",
            }
        )
        builder.add(
            base_record(
                asset_id=asset_id,
                domain="animations",
                asset_type="area-animation-wbm",
                canonical_path=path,
                locator=f"csv:resource_kind=WBM,resource_resref={resref}",
                states=states,
                adapter="animations.wbm-occurrences.v1",
            )
        )


PHASE4_INVENTORIES = (
    {
        "domain": "videos",
        "manifest": "video/index/manifest.json",
        "resources": "video/index/resources.csv",
        "id_prefix": "videos",
        "asset_type": lambda row: f"video-{stable_token(row.get('role', 'resource').lower())}",
        "adapter": "videos.inventory.v1",
        "auxiliary": (),
    },
    {
        "domain": "ui",
        "manifest": "interface/gameplay-hud-bg2ee/index/manifest.json",
        "resources": "interface/gameplay-hud-bg2ee/index/resources.csv",
        "id_prefix": "ui-hud",
        "asset_type": lambda row: "ui-hud-resource",
        "adapter": "ui.hud-inventory.v1",
        "auxiliary": ("interface/gameplay-hud-bg2ee/index/dependencies.csv",),
    },
    {
        "domain": "ui",
        "manifest": "interface/index/manifest.json",
        "resources": "interface/index/resources.csv",
        "id_prefix": "ui-resource",
        "asset_type": lambda row: f"ui-{stable_token(row.get('format', 'resource').lower())}",
        "adapter": "ui.supplement-inventory.v1",
        "auxiliary": ("interface/index/dependencies.csv",),
    },
    {
        "domain": "ui",
        "manifest": "interface/fonts/index/manifest.json",
        "resources": "interface/fonts/index/resources.csv",
        "id_prefix": "ui-font",
        "asset_type": lambda row: "ui-font",
        "adapter": "ui.font-inventory.v1",
        "auxiliary": (),
    },
    {
        "domain": "icons",
        "manifest": "icons/index/manifest.json",
        "resources": "icons/index/resources.csv",
        "id_prefix": "icons",
        "asset_type": lambda row: "icon-bam-set",
        "adapter": "icons.inventory.v1",
        "auxiliary": ("icons/index/usages.csv",),
    },
    {
        "domain": "cursors",
        "manifest": "cursors/index/manifest.json",
        "resources": "cursors/index/resources.csv",
        "id_prefix": "cursors",
        "asset_type": lambda row: "cursor-set",
        "adapter": "cursors.inventory.v1",
        "auxiliary": (),
    },
    {
        "domain": "effects",
        "manifest": "effects/index/manifest.json",
        "resources": "effects/index/resources.csv",
        "id_prefix": "effects",
        "asset_type": lambda row: f"effect-controller-{stable_token(row.get('format', 'resource').lower())}",
        "adapter": "effects.inventory.v1",
        "auxiliary": ("effects/index/dependencies.csv",),
    },
    {
        "domain": "projectiles",
        "manifest": "projectiles/index/manifest.json",
        "resources": "projectiles/index/resources.csv",
        "id_prefix": "projectiles",
        "asset_type": lambda row: "projectile-controller",
        "adapter": "projectiles.inventory.v1",
        "auxiliary": ("projectiles/index/dependencies.csv",),
    },
)


def adapt_phase4_inventories(builder: RegistryBuilder) -> None:
    video_processing_path = "video/index/processing.csv"
    video_processing: dict[str, dict[str, str]] = {}
    if builder.inputs.exists(video_processing_path):
        for row in builder.inputs.read_csv(video_processing_path):
            asset_key = row.get("asset_key", "")
            if not asset_key:
                builder.anomaly(
                    "missing-identity",
                    "error",
                    "videos",
                    "ligne de suivi vidéo sans asset_key",
                    source=video_processing_path,
                )
            elif asset_key in video_processing:
                builder.anomaly(
                    "duplicate-source-row",
                    "error",
                    "videos",
                    "asset_key dupliqué dans le suivi vidéo",
                    source=video_processing_path,
                    details={"asset_key": asset_key},
                )
            else:
                video_processing[asset_key] = row

    for config in PHASE4_INVENTORIES:
        domain = str(config["domain"])
        manifest_path = str(config["manifest"])
        resources_path = str(config["resources"])
        manifest = builder.inputs.read_json(manifest_path)
        rows = builder.inputs.read_csv(resources_path)
        for auxiliary_path in config["auxiliary"]:
            auxiliary_rows = builder.inputs.read_csv(str(auxiliary_path))
            missing = [row for row in auxiliary_rows if row.get("present") == "no"]
            if missing:
                builder.anomaly(
                    "missing-resource-dependencies",
                    "warning",
                    domain,
                    "des dépendances référencées par l'inventaire sont absentes du jeu stock",
                    source=str(auxiliary_path),
                    details={"affected_count": len(missing)},
                )
        expected_count = manifest.get("asset_count")
        if expected_count != len(rows):
            builder.anomaly(
                "inventory-count-mismatch",
                "error",
                domain,
                "le nombre de lignes diverge du manifeste canonique",
                source=manifest_path,
                details={"manifest": expected_count, "rows": len(rows)},
            )
        missing_icons = manifest.get("missing_icon_resrefs", [])
        if missing_icons:
            builder.anomaly(
                "referenced-icon-sources-missing",
                "warning",
                domain,
                "des resrefs d'icônes référencés par ITM/SPL sont absents du jeu stock",
                source=manifest_path,
                details={"affected_count": len(missing_icons)},
            )
        seen_keys: set[str] = set()
        for row in rows:
            asset_key = row.get("asset_key", "")
            if not asset_key:
                builder.anomaly(
                    "missing-identity",
                    "error",
                    domain,
                    "ligne d'inventaire sans asset_key",
                    source=resources_path,
                )
                continue
            if asset_key in seen_keys:
                builder.anomaly(
                    "duplicate-source-row",
                    "error",
                    domain,
                    "asset_key dupliqué dans l'inventaire canonique",
                    source=resources_path,
                    details={"asset_key": asset_key},
                )
                continue
            seen_keys.add(asset_key)
            asset_id = (
                f"{config['id_prefix']}:{stable_token(asset_key.lower())}"
            )
            source_hash = row.get("source_sha256", "").upper()
            verified = bool(re.fullmatch(r"[A-F0-9]{64}", source_hash))
            if not verified:
                builder.anomaly(
                    "source-hash-missing-or-invalid",
                    "error",
                    domain,
                    "empreinte source absente ou invalide dans l'inventaire",
                    asset_id=asset_id,
                    source=resources_path,
                )
            states = default_states()
            states.update(
                {
                    "source": "verified" if verified else "available",
                    "production": "not-started",
                    "installation": "not-applicable",
                }
            )
            locator = f"csv:asset_key={asset_key}"
            provenance_state = "not-applicable"
            evidence: list[dict[str, str]] = []
            selections: list[dict[str, Any]] = []
            adapter = str(config["adapter"])
            if domain == "videos" and asset_key in video_processing:
                processing = video_processing[asset_key]
                expected_directory = Path(row.get("extracted_path", "")).parent.as_posix()
                invalid_fields = {
                    "asset_id": (processing.get("asset_id", ""), asset_id),
                    "asset_directory": (
                        processing.get("asset_directory", ""),
                        expected_directory,
                    ),
                }
                differences = {
                    field: {"actual": actual, "expected": expected}
                    for field, (actual, expected) in invalid_fields.items()
                    if actual != expected
                }
                if differences:
                    builder.anomaly(
                        "video-processing-identity-mismatch",
                        "error",
                        "videos",
                        "le suivi vidéo ne correspond pas à l'identité de l'inventaire",
                        asset_id=asset_id,
                        source=video_processing_path,
                        details=differences,
                    )
                upscale_state = processing.get("upscale_state", "")
                interpolation_state = processing.get("interpolation_state", "")
                if upscale_state not in {"", "validated"} or interpolation_state not in {
                    "",
                    "validated",
                }:
                    builder.anomaly(
                        "unknown-status",
                        "error",
                        "videos",
                        "état de traitement vidéo inconnu",
                        asset_id=asset_id,
                        source=video_processing_path,
                    )
                if interpolation_state == "validated" and upscale_state != "validated":
                    builder.anomaly(
                        "video-processing-stage-order-invalid",
                        "error",
                        "videos",
                        "une interpolation validée exige un upscale validé",
                        asset_id=asset_id,
                        source=video_processing_path,
                    )
                for stage, state_field, run_field in (
                    ("upscale", "upscale_state", "upscale_run"),
                    ("interpolation", "interpolation_state", "interpolation_run"),
                ):
                    state = processing.get(state_field, "")
                    run_id = processing.get(run_field, "")
                    if state == "validated" and not run_id:
                        builder.anomaly(
                            "video-processing-run-missing",
                            "error",
                            "videos",
                            f"run {stage} absent pour une étape validée",
                            asset_id=asset_id,
                            source=video_processing_path,
                        )
                    elif state == "validated":
                        selections.append(
                            {
                                "role": "run",
                                "id": run_id,
                                "source": source_ref(video_processing_path, locator),
                            }
                        )
                patch_state = processing.get("patch_state", "")
                patch_run = processing.get("patch_run", "")
                if patch_state not in {"not-integrated", "staged", "integrated"}:
                    builder.anomaly(
                        "unknown-status",
                        "error",
                        "videos",
                        "état patch vidéo inconnu",
                        asset_id=asset_id,
                        source=video_processing_path,
                    )
                if patch_state == "not-integrated" and patch_run:
                    builder.anomaly(
                        "video-patch-selection-inconsistent",
                        "error",
                        "videos",
                        "un run patch est renseigné alors que l'intégration est absente",
                        asset_id=asset_id,
                        source=video_processing_path,
                    )
                if patch_state in {"staged", "integrated"} and not patch_run:
                    builder.anomaly(
                        "video-patch-run-missing",
                        "error",
                        "videos",
                        "un état patch actif exige un run patch",
                        asset_id=asset_id,
                        source=video_processing_path,
                    )
                if patch_run:
                    selections.append(
                        {
                            "role": "run",
                            "id": patch_run,
                            "source": source_ref(video_processing_path, locator),
                        }
                    )
                states["production"] = (
                    "verified" if upscale_state == "validated" else "not-started"
                )
                states["qa"] = (
                    "passed"
                    if upscale_state == interpolation_state == "validated"
                    else "not-assessed"
                )
                states["installation"] = {
                    "not-integrated": "not-installed",
                    "staged": "staged",
                    "integrated": "installed",
                }.get(patch_state, "unknown")
                provenance_state = "complete"
                evidence = [
                    evidence_ref(builder.inputs, video_processing_path, locator)
                ]
                adapter = "videos.processing.v1"
            builder.add(
                base_record(
                    asset_id=asset_id,
                    domain=domain,
                    asset_type=config["asset_type"](row),
                    canonical_path=resources_path,
                    locator=locator,
                    states=states,
                    provenance_state=provenance_state,
                    evidence=evidence,
                    selections=selections,
                    adapter=adapter,
                )
            )

    supplemental_manifest_path = "graphics/index/supplemental-manifest.json"
    supplemental_path = "graphics/index/supplemental-assets.csv"
    supplemental_manifest = builder.inputs.read_json(supplemental_manifest_path)
    supplemental_rows = builder.inputs.read_csv(supplemental_path)
    if supplemental_manifest.get("asset_count") != len(supplemental_rows):
        builder.anomaly(
            "inventory-count-mismatch",
            "error",
            "other",
            "le nombre de compléments graphiques diverge de leur manifeste",
            source=supplemental_manifest_path,
        )
    supplemental_keys: set[str] = set()
    for row in supplemental_rows:
        asset_key = row.get("asset_key", "")
        domain = row.get("domain", "other")
        asset_type = row.get("asset_type", "graphical-resource")
        resref = row.get("resref", "")
        asset_id = (
            f"{domain}:supplemental:{stable_token(asset_type)}:{stable_token(resref.lower())}"
        )
        if asset_key in supplemental_keys:
            builder.anomaly(
                "duplicate-source-row",
                "error",
                domain,
                "asset_key dupliqué dans les compléments graphiques",
                asset_id=asset_id,
                source=supplemental_path,
            )
            continue
        supplemental_keys.add(asset_key)
        source_hash = row.get("source_sha256", "").upper()
        verified = bool(re.fullmatch(r"[A-F0-9]{64}", source_hash))
        states = default_states()
        states.update(
            {
                "source": "verified" if verified else "available",
                "production": "not-started",
                "installation": "not-applicable",
            }
        )
        builder.add(
            base_record(
                asset_id=asset_id,
                domain=domain,
                asset_type=asset_type,
                canonical_path=supplemental_path,
                locator=f"csv:asset_key={asset_key}",
                states=states,
                adapter="graphics.supplemental-inventory.v1",
            )
        )

    graphics_path = "graphics/index/coverage.json"
    graphics = builder.inputs.read_json(graphics_path)
    unclassified_count = int(graphics.get("unclassified_resource_count", 0))
    if unclassified_count:
        builder.uninventoried_scopes.append(
            {
                "scope": "unclassified-graphical-resources",
                "domain": "other",
                "asset_count": None,
                "resource_count": unclassified_count,
                "coverage_status": "insufficient",
                "reason": (
                    "ressources BAM présentes mais propriétaire logique non démontré ; "
                    "elles ne sont pas inventées comme assets autonomes"
                ),
                "format_counts": graphics.get("unclassified_format_counts", {}),
                "source": "graphics/index/unclassified-resources.csv",
            }
        )
        builder.inputs.register(
            "graphics/index/unclassified-resources.csv", "coverage-gap"
        )
        builder.anomaly(
            "unclassified-graphical-resources",
            "warning",
            "other",
            "des ressources graphiques brutes ne peuvent pas encore être rattachées à un asset logique",
            source=graphics_path,
            details={"resource_count": unclassified_count},
        )
    overlap_count = int(graphics.get("raw_cross_domain_overlap_count", 0))
    if overlap_count:
        builder.anomaly(
            "shared-raw-dependencies",
            "info",
            "other",
            "des ressources brutes sont partagées entre plusieurs domaines sans créer de doublon logique",
            source=graphics_path,
            details={"resource_count": overlap_count},
        )


def adapt_portraits(builder: RegistryBuilder) -> None:
    path = "portraits/inventaire_portraits.csv"
    if not builder.inputs.exists(path):
        builder.anomaly(
            "portrait-inventory-missing",
            "error",
            "portraits",
            "inventaire logique des portraits absent",
            source=path,
        )
        return

    rows = builder.inputs.read_csv(path)
    seen: set[str] = set()
    for row_index, row in enumerate(rows, 2):
        base = stable_token(row.get("portrait", "").upper())
        asset_id = f"portraits:{base}"
        if base == "unknown":
            builder.anomaly(
                "missing-identity",
                "error",
                "portraits",
                "ligne d'inventaire portrait sans base exploitable",
                source=f"{path}:{row_index}",
            )
            continue
        if base in seen:
            builder.anomaly(
                "duplicate-portrait-rows",
                "error",
                "portraits",
                "base de portrait répétée dans l'inventaire logique",
                asset_id=asset_id,
                source=f"{path}:{row_index}",
            )
            continue
        seen.add(base)

        declared_sizes = row.get("tailles", "").strip().upper()
        actual_sizes = "".join(
            suffix for suffix in "LMS" if row.get(f"ressource_{suffix.lower()}", "").strip()
        )
        if not actual_sizes or declared_sizes != actual_sizes:
            builder.anomaly(
                "portrait-member-mismatch",
                "error",
                "portraits",
                "les tailles déclarées ne correspondent pas aux ressources membres",
                asset_id=asset_id,
                source=f"{path}:{row_index}",
                details={"declared_sizes": declared_sizes, "actual_sizes": actual_sizes},
            )

        evidence: list[dict[str, str]] = []
        hashes_complete = True
        for suffix in actual_sizes:
            normalized = suffix.lower()
            relative_file = row.get(f"fichier_{normalized}", "").strip()
            declared_hash = row.get(f"sha256_{normalized}", "").strip().upper()
            if not relative_file or not re.fullmatch(r"[A-F0-9]{64}", declared_hash):
                hashes_complete = False
                continue
            evidence.append(
                {
                    "path": f"portraits/{relative_file}",
                    "locator": f"portrait={base};taille={suffix}",
                    "sha256": declared_hash,
                }
            )
        if not hashes_complete:
            builder.anomaly(
                "incomplete-portrait-provenance",
                "error",
                "portraits",
                "une ressource membre n'a pas de chemin ou SHA-256 complet",
                asset_id=asset_id,
                source=f"{path}:{row_index}",
            )

        usage = [
            field
            for field in ("selectable", "recrutable", "rencontre")
            if row.get(field, "").strip().lower() == "yes"
        ]
        if not usage:
            builder.anomaly(
                "portrait-without-runtime-usage",
                "error",
                "portraits",
                "portrait sans déclaration BGEE.lua ni porteur CRE",
                asset_id=asset_id,
                source=f"{path}:{row_index}",
            )

        states = default_states()
        states.update(
            {
                "source": "verified" if hashes_complete else "extracted",
                "production": "not-applicable",
                "qa": "not-applicable",
                "installation": "not-applicable",
                "release": "not-applicable",
            }
        )
        builder.add(
            base_record(
                asset_id=asset_id,
                domain="portraits",
                asset_type="portrait-set",
                canonical_path=path,
                locator=f"csv:portrait={base}",
                states=states,
                provenance_state="verified" if hashes_complete else "partial",
                evidence=evidence,
                legacy=[
                    {"field": "usage", "value": ",".join(usage), "mapping": "portraits.logical.v2"},
                    {"field": "tailles", "value": actual_sizes, "mapping": "portraits.logical.v2"},
                ],
                adapter="portraits.logical.v2",
            )
        )


def axis_coverage(records: list[dict[str, Any]], axis: str) -> dict[str, Any]:
    if axis == "provenance":
        values = [record["provenance"]["state"] for record in records]
        order = PROVENANCE_VALUES
    else:
        values = [record["states"][axis] for record in records]
        order = STATE_VALUES[axis]
    state_counts = {value: values.count(value) for value in order if values.count(value)}
    not_applicable = values.count("not-applicable")
    applicable_count = len(values) - not_applicable
    unresolved_count = sum(values.count(value) for value in UNRESOLVED_STATES[axis])
    covered_count = applicable_count - unresolved_count
    percent = round(100.0 * covered_count / applicable_count, 2) if applicable_count else None
    return {
        "applicable_count": applicable_count,
        "covered_count": covered_count,
        "unresolved_count": unresolved_count,
        "not_applicable_count": not_applicable,
        "coverage_percent": percent,
        "state_counts": state_counts,
    }


def build_coverage(
    records: list[dict[str, Any]],
    observed_at: str,
    fingerprint: str,
    records_sha256: str,
    uninventoried_scopes: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    domain_rows = []
    for domain in sorted(DOMAIN_SCOPE):
        domain_records = [record for record in records if record["domain"] == domain]
        asset_types: dict[str, int] = {}
        for record in domain_records:
            asset_type = record["asset_type"]
            asset_types[asset_type] = asset_types.get(asset_type, 0) + 1
        domain_rows.append(
            {
                "domain": domain,
                **DOMAIN_SCOPE[domain],
                "asset_count": len(domain_records),
                "asset_types": dict(sorted(asset_types.items())),
                "axes": {
                    axis: axis_coverage(domain_records, axis)
                    for axis in (*STATE_VALUES.keys(), "provenance")
                },
            }
        )

    metrics = {
        "known_assets": len(records),
        "known_unprocessed": sum(
            record["states"]["production"] in {"not-started", "ready"}
            for record in records
        ),
        "known_blocked_or_rejected": sum(
            record["states"]["production"] in {"blocked", "rejected"}
            for record in records
        ),
        "source_available": sum(
            record["states"]["source"] in SOURCE_AVAILABLE for record in records
        ),
        "produced": sum(record["states"]["production"] in PRODUCED for record in records),
        "qa_passed": sum(record["states"]["qa"] == "passed" for record in records),
        "installed": sum(
            record["states"]["installation"] == "installed" for record in records
        ),
        "release_eligible_or_beyond": sum(
            record["states"]["release"] in RELEASE_ELIGIBLE for record in records
        ),
        "release_integrated_or_published": sum(
            record["states"]["release"] in {"integrated", "published"}
            for record in records
        ),
        "provenance_available": sum(
            record["provenance"]["state"] in PROVENANCE_AVAILABLE for record in records
        ),
    }
    return {
        "schema": COVERAGE_SCHEMA,
        "generated_by": GENERATOR,
        "source_snapshot_at_utc": observed_at,
        "source_fingerprint_sha256": fingerprint,
        "asset_records_sha256": records_sha256,
        "metrics": metrics,
        "global_axes": {
            axis: axis_coverage(records, axis)
            for axis in (*STATE_VALUES.keys(), "provenance")
        },
        "domains": domain_rows,
        "uninventoried_scopes": sorted(
            (dict(scope) for scope in uninventoried_scopes),
            key=lambda scope: (str(scope.get("domain", "")), str(scope.get("scope", ""))),
        ),
    }


def build_outputs(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    builder = RegistryBuilder(root)
    map_groups, animation_groups, ui_groups = load_content_groups(builder.inputs)
    auxiliary_contracts = load_auxiliary_map_release_contracts(builder.inputs)
    adapt_maps(builder, map_groups, auxiliary_contracts)
    animation_resrefs = adapt_animation_bams(builder)
    adapt_animation_wbms(builder)
    adapt_animation_candidates(builder, animation_resrefs, animation_groups)
    adapt_sprites(builder)
    adapt_ui(builder, ui_groups)
    adapt_phase4_inventories(builder)
    adapt_portraits(builder)
    registry, coverage, anomalies = builder.finalize()
    return {
        "registry": registry,
        "coverage": coverage,
        "anomalies": anomalies,
    }


def rendered_outputs(outputs: Mapping[str, Any]) -> dict[str, bytes]:
    return {
        JSON_OUTPUT_NAMES["registry"]: json_bytes(outputs["registry"]),
        REGISTRY_CSV_NAME: registry_csv_bytes(outputs["registry"]["assets"]),
        JSON_OUTPUT_NAMES["coverage"]: json_bytes(outputs["coverage"]),
        JSON_OUTPUT_NAMES["anomalies"]: json_bytes(outputs["anomalies"]),
    }


def write_outputs(outputs: Mapping[str, Any], output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in rendered_outputs(outputs).items():
        (output_dir / name).write_bytes(content)


def check_outputs(outputs: Mapping[str, Any], output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[str]:
    stale = []
    for name, expected in rendered_outputs(outputs).items():
        path = output_dir / name
        if not path.is_file() or path.read_bytes() != expected:
            stale.append(name)
    return stale


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="dossier des quatre sorties générées",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="vérifie les sorties existantes sans écrire",
    )
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="construit deux fois en mémoire et compare les octets",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    first = build_outputs(ROOT)
    if args.verify_determinism:
        second = build_outputs(ROOT)
        if rendered_outputs(first) != rendered_outputs(second):
            raise ContractError("la seconde génération diffère de la première")
    if args.check:
        stale = check_outputs(first, args.output_dir)
        if stale:
            print("sorties absentes ou périmées : " + ", ".join(stale))
            return 1
        print("registre global et rapports à jour")
        return 0
    write_outputs(first, args.output_dir)
    metrics = first["coverage"]["metrics"]
    anomaly_summary = first["anomalies"]["summary"]
    print(
        f"registre généré : {metrics['known_assets']} assets ; "
        f"{anomaly_summary['total']} anomalie(s) structurée(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
