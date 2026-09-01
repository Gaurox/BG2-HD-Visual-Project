"""Common read-only asset tracking contract helpers.

This module validates disposable projections. It never reads or writes domain
manifests itself and is deliberately not an asset registry.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath
import re
from typing import Any, Mapping


SCHEMA_VERSION = 1

DOMAINS = (
    "maps",
    "animations",
    "sprites",
    "ui",
    "portraits",
    "videos",
    "icons",
    "cursors",
    "effects",
    "projectiles",
    "other",
)

STATE_VALUES = {
    "source": (
        "unknown",
        "unavailable",
        "available",
        "extracted",
        "verified",
        "not-applicable",
    ),
    "production": (
        "unknown",
        "not-started",
        "ready",
        "in-progress",
        "produced",
        "verified",
        "rejected",
        "blocked",
        "not-applicable",
    ),
    "qa": (
        "not-assessed",
        "pending",
        "passed",
        "failed",
        "blocked",
        "not-applicable",
    ),
    "installation": (
        "unknown",
        "not-installed",
        "staged",
        "installed",
        "drifted",
        "restored",
        "not-applicable",
    ),
    "release": (
        "not-evaluated",
        "ineligible",
        "eligible",
        "approved",
        "integrated",
        "published",
        "blocked",
        "not-applicable",
    ),
}

PROVENANCE_VALUES = ("missing", "partial", "complete", "verified", "not-applicable")
SELECTION_ROLES = (
    "run",
    "candidate",
    "generation",
    "build",
    "variant",
    "correction",
    "release-entry",
)

# Transitional, exact mappings only. Missing axes must be filled from their own
# authority; no mapping is allowed to infer a release from production or install.
LEGACY_STATUS_MAPPINGS: dict[str, dict[str, dict[str, str]]] = {
    "maps.areas.status.v1": {
        "source-pending": {"source": "available", "production": "not-started"},
        "source-only": {"source": "extracted", "production": "not-started"},
        "installed-pending-qa": {
            "production": "produced",
            "qa": "pending",
            "installation": "installed",
        },
        "validated-installed": {
            "production": "verified",
            "qa": "passed",
            "installation": "installed",
        },
    },
    "animations.index.upscale-status.v1": {
        "non-traité": {"production": "not-started"},
        "à-compléter": {"production": "in-progress"},
        "à-corriger": {"production": "blocked", "release": "ineligible"},
        "écarté": {"production": "rejected", "release": "ineligible"},
        "validé-x4": {"production": "verified"},
        "validé-natif": {"production": "verified"},
    },
    "animations.index.alpha-status.v1": {
        "validated-prototype-installed": {
            "production": "verified",
            "qa": "passed",
            "installation": "installed",
            "release": "ineligible",
        },
    },
    "animations.qa-approval.status.v1": {
        "accepted": {"qa": "passed"},
    },
    "sprites.index.manifest-status.v1": {
        "generated-verified-read-only-source": {"source": "verified"},
    },
    "sprites.index.pipeline-ready.v1": {
        "yes": {"production": "ready"},
        "no": {"production": "blocked"},
    },
    "sprites.build.status.v1": {
        "built-pending-ingame-qa": {"production": "verified", "qa": "pending"},
        "built-tested": {"production": "verified"},
    },
    "sprites.installation.status.v1": {
        "installed-pending-qa": {"qa": "pending", "installation": "installed"},
        "corrected-reinstalled-pending-qa": {
            "qa": "pending",
            "installation": "installed",
        },
        "validated-installed": {"qa": "passed", "installation": "installed"},
        "restored": {"installation": "restored"},
        "rolled-back-after-install-error": {"installation": "restored"},
    },
    "release.animation.approval-status.v1": {
        "validated-awaiting-manifest-approval": {"release": "eligible"},
        "approved-for-release": {"release": "approved"},
    },
}


_ASSET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
_ASSET_TYPE_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_ADAPTER_RE = re.compile(r"^[a-z][a-z0-9.-]*[.]v[0-9]+$")
_SHA256_RE = re.compile(r"^[A-F0-9]{64}$")


class ContractError(ValueError):
    """Raised when a projected asset record violates the common contract."""


def map_legacy_status(mapping: str, raw_status: str) -> dict[str, str]:
    """Return an independent-axis fragment for one exact legacy status.

    Unknown mappings and values fail closed so an adapter cannot silently
    reinterpret a new domain status.
    """

    try:
        fragment = LEGACY_STATUS_MAPPINGS[mapping][raw_status]
    except KeyError as exc:
        raise ContractError(
            f"legacy status not mapped exactly: mapping={mapping!r}, status={raw_status!r}"
        ) from exc
    return dict(fragment)


def _is_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _validate_repo_path(value: Any, label: str, errors: list[str]) -> None:
    if not _is_string(value):
        errors.append(f"{label} must be a non-empty string")
        return
    if "\\" in value or re.match(r"^[A-Za-z]:", value):
        errors.append(f"{label} must be a repository-relative POSIX path")
        return
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} must stay inside the repository")


def _validate_reference(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, Mapping):
        errors.append(f"{label} must be an object")
        return
    allowed = {"path", "locator", "sha256"}
    extra = set(value) - allowed
    missing = {"path", "locator"} - set(value)
    if extra:
        errors.append(f"{label} has unsupported fields: {sorted(extra)}")
    if missing:
        errors.append(f"{label} is missing fields: {sorted(missing)}")
    _validate_repo_path(value.get("path"), f"{label}.path", errors)
    if not _is_string(value.get("locator")):
        errors.append(f"{label}.locator must be a non-empty string")
    sha256 = value.get("sha256")
    if sha256 is not None and (not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256)):
        errors.append(f"{label}.sha256 must be 64 uppercase hexadecimal characters")


def validate_record(record: Any) -> list[str]:
    """Return every contract violation found in a projected record."""

    errors: list[str] = []
    if not isinstance(record, Mapping):
        return ["record must be an object"]

    required = {
        "schema_version",
        "asset_id",
        "domain",
        "asset_type",
        "canonical_source",
        "states",
        "provenance",
        "adapter",
        "observed_at_utc",
    }
    allowed = required | {"$schema", "selections", "legacy"}
    extra = set(record) - allowed
    missing = required - set(record)
    if extra:
        errors.append(f"record has unsupported fields: {sorted(extra)}")
    if missing:
        errors.append(f"record is missing fields: {sorted(missing)}")

    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    asset_id = record.get("asset_id")
    if not isinstance(asset_id, str) or not _ASSET_ID_RE.fullmatch(asset_id):
        errors.append("asset_id must be stable and contain only identity characters")
    if record.get("domain") not in DOMAINS:
        errors.append(f"domain must be one of {DOMAINS}")
    asset_type = record.get("asset_type")
    if not isinstance(asset_type, str) or not _ASSET_TYPE_RE.fullmatch(asset_type):
        errors.append("asset_type must be lower-case kebab-case")
    _validate_reference(record.get("canonical_source"), "canonical_source", errors)

    states = record.get("states")
    if not isinstance(states, Mapping):
        errors.append("states must be an object")
        states = {}
    else:
        missing_states = set(STATE_VALUES) - set(states)
        extra_states = set(states) - set(STATE_VALUES)
        if missing_states:
            errors.append(f"states is missing axes: {sorted(missing_states)}")
        if extra_states:
            errors.append(f"states has unsupported axes: {sorted(extra_states)}")
        for axis, accepted in STATE_VALUES.items():
            if states.get(axis) not in accepted:
                errors.append(f"states.{axis} must be one of {accepted}")

    selections = record.get("selections", [])
    if not isinstance(selections, list):
        errors.append("selections must be an array")
        selections = []
    else:
        seen_selections: set[tuple[Any, Any]] = set()
        for index, selection in enumerate(selections):
            label = f"selections[{index}]"
            if not isinstance(selection, Mapping):
                errors.append(f"{label} must be an object")
                continue
            if set(selection) != {"role", "id", "source"}:
                errors.append(f"{label} must contain exactly role, id and source")
            if selection.get("role") not in SELECTION_ROLES:
                errors.append(f"{label}.role must be one of {SELECTION_ROLES}")
            if not _is_string(selection.get("id")):
                errors.append(f"{label}.id must be a non-empty string")
            _validate_reference(selection.get("source"), f"{label}.source", errors)
            key = (selection.get("role"), selection.get("id"))
            if key in seen_selections:
                errors.append(f"{label} duplicates selection {key!r}")
            seen_selections.add(key)

    provenance = record.get("provenance")
    provenance_state = None
    evidence: list[Any] = []
    if not isinstance(provenance, Mapping):
        errors.append("provenance must be an object")
    else:
        if set(provenance) != {"state", "evidence"}:
            errors.append("provenance must contain exactly state and evidence")
        provenance_state = provenance.get("state")
        if provenance_state not in PROVENANCE_VALUES:
            errors.append(f"provenance.state must be one of {PROVENANCE_VALUES}")
        raw_evidence = provenance.get("evidence")
        if not isinstance(raw_evidence, list):
            errors.append("provenance.evidence must be an array")
        else:
            evidence = raw_evidence
            for index, reference in enumerate(evidence):
                _validate_reference(reference, f"provenance.evidence[{index}]", errors)
        if provenance_state in {"missing", "not-applicable"} and evidence:
            errors.append(f"provenance {provenance_state} cannot contain evidence")
        if provenance_state in {"complete", "verified"} and not evidence:
            errors.append(f"provenance {provenance_state} requires evidence")
        if provenance_state == "verified" and any(
            not isinstance(item, Mapping) or "sha256" not in item for item in evidence
        ):
            errors.append("verified provenance requires a sha256 on every evidence reference")
        if provenance_state == "not-applicable" and selections:
            errors.append("not-applicable provenance cannot contain selections")

    legacy = record.get("legacy", [])
    if not isinstance(legacy, list):
        errors.append("legacy must be an array")
    else:
        for index, item in enumerate(legacy):
            label = f"legacy[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{label} must be an object")
                continue
            if not {"field", "value"}.issubset(item) or set(item) - {
                "field",
                "value",
                "mapping",
            }:
                errors.append(f"{label} must contain field, value and optional mapping")
            if not _is_string(item.get("field")) or not _is_string(item.get("value")):
                errors.append(f"{label}.field and value must be non-empty strings")
            mapping = item.get("mapping")
            if mapping is not None and (
                not isinstance(mapping, str) or not _ADAPTER_RE.fullmatch(mapping)
            ):
                errors.append(f"{label}.mapping must be a versioned mapping identifier")

    adapter = record.get("adapter")
    if not isinstance(adapter, str) or not _ADAPTER_RE.fullmatch(adapter):
        errors.append("adapter must be a versioned identifier ending in .vN")
    observed = record.get("observed_at_utc")
    if not isinstance(observed, str) or not observed.endswith("Z"):
        errors.append("observed_at_utc must be an ISO-8601 UTC timestamp ending in Z")
    else:
        try:
            parsed = datetime.fromisoformat(observed[:-1] + "+00:00")
            if parsed.tzinfo != timezone.utc:
                raise ValueError
        except ValueError:
            errors.append("observed_at_utc must be a valid ISO-8601 UTC timestamp")

    release_state = states.get("release")
    if release_state in {"eligible", "approved", "integrated", "published"}:
        if states.get("qa") != "passed":
            errors.append(f"release {release_state} requires qa passed")
        if provenance_state not in {"complete", "verified"}:
            errors.append(f"release {release_state} requires complete provenance")
        if not selections:
            errors.append(f"release {release_state} requires an explicit selection")

    return errors


def assert_valid_record(record: Any) -> None:
    """Raise :class:`ContractError` if a projected record is invalid."""

    errors = validate_record(record)
    if errors:
        raise ContractError("invalid asset tracking record:\n- " + "\n- ".join(errors))
