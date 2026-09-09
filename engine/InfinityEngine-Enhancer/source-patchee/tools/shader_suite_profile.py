#!/usr/bin/env python3
"""Validate and materialize the tracked shader-suite profile authority."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONTRACT = (
    ROOT
    / "sprite"
    / "catmull-rom"
    / "profiles"
    / "shader-suite-contract-v1.json"
)
TARGET_SHADERS = {
    "fpSprite",
    "fpSELECT",
    "fpDraw",
    "fpTone",
    "fpFONT",
    "fpSEAM",
    "fpYUV",
    "fpYUVGRY",
}


class ContractError(ValueError):
    """Raised when the tracked authority is internally inconsistent."""


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ContractError("contract root must be an object")
    validate_contract(value)
    return value


def _validate_value(name: str, value: Any, definition: dict[str, Any]) -> None:
    value_type = definition.get("type")
    if value_type == "boolean":
        if not isinstance(value, bool):
            raise ContractError(f"{name}: expected boolean")
        return
    if value_type == "enum":
        if value not in definition.get("values", []):
            raise ContractError(f"{name}: unsupported enum value {value!r}")
        return
    if value_type != "number" or isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{name}: expected finite number")
    if not math.isfinite(value):
        raise ContractError(f"{name}: expected finite number")
    if "minimum" in definition and value < definition["minimum"]:
        raise ContractError(f"{name}: {value} is below {definition['minimum']}")
    if "exclusiveMinimum" in definition and value <= definition["exclusiveMinimum"]:
        raise ContractError(f"{name}: {value} is not above {definition['exclusiveMinimum']}")
    if "maximum" in definition and value > definition["maximum"]:
        raise ContractError(f"{name}: {value} is above {definition['maximum']}")


def _neutral_state(contract: dict[str, Any]) -> dict[str, Any]:
    globals_state = {
        name: deepcopy(definition["neutral"])
        for name, definition in contract["global_parameters"].items()
    }
    profiles: dict[str, dict[str, Any]] = {}
    for profile_name, interface in contract["interfaces"].items():
        profiles[profile_name] = {
            parameter: deepcopy(contract["profile_parameters"][parameter]["neutral"])
            for parameter in interface["parameters"]
        }
    return {"global": globals_state, "profiles": profiles}


def _apply_global(contract: dict[str, Any], state: dict[str, Any], values: Any, owner: str) -> None:
    if values is None:
        return
    if not isinstance(values, dict):
        raise ContractError(f"{owner}.global must be an object")
    for name, value in values.items():
        definition = contract["global_parameters"].get(name)
        if definition is None:
            raise ContractError(f"{owner}: unknown global parameter {name}")
        _validate_value(f"{owner}.global.{name}", value, definition)
        state["global"][name] = deepcopy(value)


def _apply_operations(
    contract: dict[str, Any], state: dict[str, Any], operations: Any, owner: str
) -> None:
    if not isinstance(operations, list):
        raise ContractError(f"{owner}.operations must be an array")
    for operation_index, operation in enumerate(operations):
        if not isinstance(operation, dict) or set(operation) != {"profiles", "set"}:
            raise ContractError(f"{owner}.operations[{operation_index}] has invalid keys")
        profile_names = operation["profiles"]
        assignments = operation["set"]
        if not isinstance(profile_names, list) or not profile_names or not isinstance(assignments, dict):
            raise ContractError(f"{owner}.operations[{operation_index}] is malformed")
        for profile_name in profile_names:
            interface = contract["interfaces"].get(profile_name)
            if interface is None:
                raise ContractError(f"{owner}: unknown profile {profile_name}")
            allowed = set(interface["parameters"])
            for parameter, value in assignments.items():
                if parameter not in allowed:
                    raise ContractError(f"{owner}: {parameter} is not valid for {profile_name}")
                definition = contract["profile_parameters"][parameter]
                _validate_value(f"{owner}.{profile_name}.{parameter}", value, definition)
                state["profiles"][profile_name][parameter] = deepcopy(value)


def _resolve_base(contract: dict[str, Any], base_name: str) -> dict[str, Any]:
    recipe = contract["base_recipes"].get(base_name)
    if recipe is None:
        raise ContractError(f"unknown base recipe {base_name}")
    state = _neutral_state(contract)
    _apply_global(contract, state, recipe.get("global", {}), f"base_recipes.{base_name}")
    _apply_operations(
        contract, state, recipe.get("operations", []), f"base_recipes.{base_name}"
    )
    return state


def _apply_component(
    contract: dict[str, Any], state: dict[str, Any], component_id: int | str
) -> dict[str, Any]:
    component_name = str(component_id)
    component = contract["components"].get(component_name)
    if component is None:
        raise ContractError(f"unknown component {component_name}")
    if "reset_base" in component:
        state = _resolve_base(contract, component["reset_base"])
    _apply_global(contract, state, component.get("global", {}), f"components.{component_name}")
    _apply_operations(
        contract, state, component.get("operations", []), f"components.{component_name}"
    )
    return state


def _resolved_document(
    contract: dict[str, Any], profile_name: str, recipe: dict[str, Any], state: dict[str, Any]
) -> dict[str, Any]:
    document = {
        "contract_version": contract["contract_version"],
        "profile": profile_name,
        "recipe": deepcopy(recipe),
        "global": state["global"],
        "profiles": state["profiles"],
    }
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    document["profile_id"] = hashlib.sha256(canonical).hexdigest()
    return document


def resolve_profile(contract: dict[str, Any], profile_name: str) -> dict[str, Any]:
    if profile_name in contract["presets"]:
        recipe = contract["presets"][profile_name]
        components = recipe.get("components")
        if not isinstance(components, list) or not components or components[0] != 1000:
            raise ContractError(f"preset {profile_name} must start with component 1000")
        state = _resolve_base(contract, "suite_disabled")
        for component_id in components:
            state = _apply_component(contract, state, component_id)
        return _resolved_document(contract, profile_name, recipe, state)

    witness = contract["witness_profiles"].get(profile_name)
    if witness is None:
        raise ContractError(f"unknown profile {profile_name}")
    state = _resolve_base(contract, witness["base"])
    _apply_global(contract, state, witness.get("global", {}), f"witness_profiles.{profile_name}")
    _apply_operations(
        contract,
        state,
        witness.get("operations", []),
        f"witness_profiles.{profile_name}",
    )
    return _resolved_document(contract, profile_name, witness, state)


def validate_contract(contract: dict[str, Any]) -> None:
    required = {
        "contract_version",
        "upstream",
        "global_parameters",
        "profile_parameters",
        "interfaces",
        "base_recipes",
        "components",
        "presets",
        "witness_profiles",
    }
    missing = required - set(contract)
    if missing:
        raise ContractError(f"missing contract keys: {sorted(missing)}")
    if contract["contract_version"] != 1:
        raise ContractError("this tool supports contract_version 1 only")
    if set(contract["interfaces"]) != TARGET_SHADERS | {"CreatureHD"}:
        raise ContractError("interfaces must contain CreatureHD and the eight target shaders")
    if len(contract["presets"]) != 10:
        raise ContractError("exactly ten upstream presets are required")
    required_witnesses = {"BaselineNearest", "BaselineLinear", "CatmullOnlyHD", "Custom"}
    if set(contract["witness_profiles"]) != required_witnesses:
        raise ContractError("the four IEE witness profiles are required")

    for name, definition in contract["global_parameters"].items():
        if not isinstance(definition, dict) or "neutral" not in definition:
            raise ContractError(f"global parameter {name} lacks a neutral value")
        _validate_value(f"global_parameters.{name}.neutral", definition["neutral"], definition)
    for name, definition in contract["profile_parameters"].items():
        if not isinstance(definition, dict) or "neutral" not in definition:
            raise ContractError(f"profile parameter {name} lacks a neutral value")
        _validate_value(f"profile_parameters.{name}.neutral", definition["neutral"], definition)

    for interface_name, interface in contract["interfaces"].items():
        parameters = interface.get("parameters")
        if not isinstance(parameters, list) or len(parameters) != len(set(parameters)):
            raise ContractError(f"interface {interface_name} has invalid parameters")
        unknown = set(parameters) - set(contract["profile_parameters"])
        if unknown:
            raise ContractError(f"interface {interface_name} has unknown parameters: {sorted(unknown)}")

    for base_name in contract["base_recipes"]:
        _resolve_base(contract, base_name)
    for component_name, component in contract["components"].items():
        state = _resolve_base(contract, "suite_disabled")
        _apply_component(contract, state, component_name)
        if "delivery" not in component:
            raise ContractError(f"component {component_name} lacks delivery")
    for profile_name in contract["presets"]:
        resolve_profile(contract, profile_name)
    for profile_name in contract["witness_profiles"]:
        resolve_profile(contract, profile_name)


def _serialized(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--profile")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--list", action="store_true", help="list tracked recipes")
    parser.add_argument("--check", action="store_true", help="validate all recipes")
    parser.add_argument("--run", action="store_true", help="write the materialized profile")
    args = parser.parse_args(argv)

    contract = load_contract(args.contract)
    if args.list:
        for name in (*contract["presets"], *contract["witness_profiles"]):
            print(name)
        return 0
    if args.check and not args.profile:
        print(f"OK contract v{contract['contract_version']}: {args.contract}")
        return 0
    if not args.profile:
        parser.error("--profile is required unless --list or --check is used")

    document = resolve_profile(contract, args.profile)
    payload = _serialized(document)
    destination = args.output
    print(f"profile={args.profile}")
    print(f"profile_id={document['profile_id']}")
    print(f"output={destination if destination else '<stdout-only>'}")
    print(f"action={'write-new-file' if args.run else 'plan-only'}")
    if not args.run:
        return 0
    if destination is None:
        parser.error("--run requires --output")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as stream:
            stream.write(payload)
    except FileExistsError as error:
        raise ContractError(f"refusing to overwrite existing output: {destination}") from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
