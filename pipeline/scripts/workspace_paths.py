"""Resolve machine-local paths without embedding them in active scripts or new jobs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/workspace-paths.json"
CONFIG_REFERENCE_PREFIX = "config://"


class WorkspacePathError(RuntimeError):
    """Raised when a configured path is absent or does not satisfy its contract."""


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_configuration(
    *,
    root: Path = ROOT,
    environ: Mapping[str, str] | None = None,
) -> tuple[dict, dict, Mapping[str, str]]:
    config_path = root / "config/workspace-paths.json"
    config = _read_json(config_path)
    override_path = root / config["local_override"]
    override = _read_json(override_path) if override_path.is_file() else {}
    return config, override, os.environ if environ is None else environ


def get_path(
    key: str,
    *,
    required: bool = False,
    root: Path = ROOT,
    environ: Mapping[str, str] | None = None,
) -> Path:
    config, override, environment = load_configuration(root=root, environ=environ)
    if key not in config["paths"]:
        raise KeyError(f"unknown workspace path key: {key}")
    definition = config["paths"][key]
    value = environment.get(definition["environment"], "")
    if not value:
        value = next(
            (
                environment[name]
                for name in definition.get("legacy_environments", [])
                if environment.get(name)
            ),
            "",
        )
    value = value or override.get("paths", {}).get(key, "")
    if not value:
        if required:
            raise WorkspacePathError(
                f"{key} is not configured; set {definition['environment']} or copy "
                "config/workspace-paths.example.json to config/workspace-paths.local.json"
            )
        return root / ".unconfigured" / key
    path = Path(value).expanduser()
    if required:
        expected_kind = definition.get("kind")
        if expected_kind == "file" and not path.is_file():
            raise WorkspacePathError(f"configured file does not exist for {key}: {path}")
        if expected_kind == "directory" and not path.is_dir():
            raise WorkspacePathError(f"configured directory does not exist for {key}: {path}")
        for marker in definition.get("markers", []):
            if not (path / marker).exists():
                raise WorkspacePathError(f"configured directory for {key} lacks marker {marker}: {path}")
    return path


def get_service(
    key: str,
    *,
    root: Path = ROOT,
    environ: Mapping[str, str] | None = None,
) -> str:
    config, override, environment = load_configuration(root=root, environ=environ)
    if key not in config["services"]:
        raise KeyError(f"unknown workspace service key: {key}")
    definition = config["services"][key]
    return str(
        environment.get(definition["environment"], "")
        or override.get("services", {}).get(key, "")
        or definition.get("default", "")
    )


def resolve_path_reference(
    value: str | Path,
    *,
    required: bool = False,
    root: Path = ROOT,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve config:// keys, legacy absolute paths and workspace-relative paths."""

    text = str(value)
    if text.startswith(CONFIG_REFERENCE_PREFIX):
        return get_path(
            text[len(CONFIG_REFERENCE_PREFIX) :],
            required=required,
            root=root,
            environ=environ,
        )
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = root / path
    if required and not path.exists():
        raise WorkspacePathError(f"path does not exist: {path}")
    return path


def portable_path_reference(key: str) -> str:
    config, _override, _environment = load_configuration()
    if key not in config["paths"]:
        raise KeyError(f"unknown workspace path key: {key}")
    return f"{CONFIG_REFERENCE_PREFIX}{key}"
