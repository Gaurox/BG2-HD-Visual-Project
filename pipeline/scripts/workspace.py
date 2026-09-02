"""Plan workspace projections by default; rebuild only explicit scopes with ``--run``."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fnmatch import fnmatchcase
import json
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import test_changed  # noqa: E402


SCOPE_ORDER = ("graphics", "registry", "integrity")
SCOPE_LABELS = {
    "graphics": "inventaires graphiques complémentaires",
    "registry": "registre global",
    "integrity": "intégrité physique et index des runs",
}
SCOPE_SCRIPTS = {
    "graphics": "build_graphics_inventory.py",
    "registry": "build_global_asset_registry.py",
    "integrity": "audit_workspace_integrity.py",
}


@dataclass(frozen=True)
class Stage:
    scope: str
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class ReconstructionPlan:
    scopes: tuple[str, ...]
    changed_paths: tuple[test_changed.ChangedPath, ...]
    reasons: tuple[str, ...]
    source: str


def _matches(path: str, *patterns: str) -> bool:
    return any(fnmatchcase(path, pattern) for pattern in patterns)


def normalize_scopes(scopes: Iterable[str]) -> tuple[str, ...]:
    requested = tuple(scopes)
    unknown = sorted(set(requested) - {*SCOPE_ORDER, "all"})
    if unknown:
        raise ValueError("unsupported workspace scope: " + ", ".join(unknown))
    if "all" in requested:
        return SCOPE_ORDER
    return tuple(scope for scope in SCOPE_ORDER if scope in requested)


def stages(
    mode: str,
    python: str = sys.executable,
    *,
    scopes: Iterable[str] = ("all",),
    verify_determinism: bool = False,
) -> tuple[Stage, ...]:
    if mode not in {"refresh", "check"}:
        raise ValueError(f"unsupported workspace mode: {mode}")
    selected = normalize_scopes(scopes)
    common: tuple[str, ...] = ()
    if verify_determinism:
        common += ("--verify-determinism",)
    if mode == "check":
        common += ("--check",)
    return tuple(
        Stage(
            scope,
            SCOPE_LABELS[scope],
            (python, str(SCRIPT_DIR / SCOPE_SCRIPTS[scope]), *common),
        )
        for scope in selected
    )


def reconstruction_scopes_for_path(path: str) -> tuple[str, ...]:
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    lowered = path.casefold()
    if lowered.endswith((".md", ".rst")) or path in {"AGENTS.md", "README.md"}:
        return ()

    if path == "pipeline/scripts/build_graphics_inventory.py" or _matches(
        path,
        "config/workspace-paths*.json",
    ):
        return SCOPE_ORDER

    if path in {
        "pipeline/scripts/asset_tracking_contract.py",
        "pipeline/scripts/build_global_asset_registry.py",
        "docs/asset-tracking-record.schema.json",
    }:
        return ("registry", "integrity")

    if path in {
        "pipeline/scripts/audit_workspace_integrity.py",
        "docs/workspace-run.schema.json",
    } or _matches(
        path,
        "docs/workspace-cleanup-manifest*.json",
        "docs/workspace-archive-manifest*.json",
        "docs/workspace-animation-packs-*.json",
        "docs/workspace-legacy-*.json",
        "docs/workspace-backups-*.json",
    ):
        return ("integrity",)

    if path == "areas.csv" or _matches(
        path,
        "animations/index/**",
        "animations/**/qa-approval.json",
        "sprite/index/**",
        "sprite/**/current-generation.json",
        "sprite/**/active-test.json",
        "sprite/**/build-manifest.json",
        "releases/BG2-HD-Upscale/manifests/**",
        "video/index/**",
        "interface/index/**",
        "interface/fonts/index/**",
        "interface/gameplay-hud-bg2ee/index/**",
        "icons/index/**",
        "cursors/index/**",
        "effects/index/**",
        "projectiles/index/**",
        "graphics/index/**",
        "portraits/*.csv",
        "portraits/**/*.csv",
        "portraits-recrutables/*.csv",
        "portraits-recrutables/**/*.csv",
    ):
        return ("registry", "integrity")

    if _matches(
        path,
        "pipeline/scripts/extract_character_portraits.py",
        "pipeline/scripts/extract_encountered_portraits.py",
        "pipeline/scripts/extract_joinable_portraits.py",
        "pipeline/scripts/organize_ppe_portraits.py",
        "pipeline/scripts/survey_creature_portraits.py",
    ):
        return SCOPE_ORDER

    if _matches(path, "asset-tracking/registry.*", "asset-tracking/coverage.json", "asset-tracking/anomalies.json"):
        return ("registry", "integrity")
    if _matches(path, "asset-tracking/workspace-integrity.json", "asset-tracking/runs.*"):
        return ("integrity",)
    return ()


def select_changed(
    changed_paths: Iterable[test_changed.ChangedPath],
) -> ReconstructionPlan:
    changed = tuple(changed_paths)
    selected: set[str] = set()
    reasons: list[str] = []
    for item in changed:
        paths = [item.path]
        if item.previous_path and item.previous_path not in paths:
            paths.append(item.previous_path)
        item_scopes: set[str] = set()
        for path in paths:
            item_scopes.update(reconstruction_scopes_for_path(path))
        selected.update(item_scopes)
        if item_scopes:
            ordered = [scope for scope in SCOPE_ORDER if scope in item_scopes]
            reasons.append(f"{item.path}: {', '.join(ordered)}")
    ordered_scopes = tuple(scope for scope in SCOPE_ORDER if scope in selected)
    if not ordered_scopes:
        reasons.append("aucune projection générée affectée par les fichiers modifiés")
    return ReconstructionPlan(ordered_scopes, changed, tuple(reasons), "changed")


def explicit_plan(scopes: Iterable[str]) -> ReconstructionPlan:
    selected = normalize_scopes(scopes)
    return ReconstructionPlan(
        selected,
        (),
        ("scopes demandés explicitement",),
        "explicit",
    )


def commands_for(
    plan: ReconstructionPlan,
    mode: str,
    *,
    python: str = sys.executable,
    verify_determinism: bool = False,
) -> tuple[Stage, ...]:
    return stages(
        mode,
        python,
        scopes=plan.scopes,
        verify_determinism=verify_determinism,
    )


def _format_command(argv: Sequence[str]) -> str:
    return subprocess.list2cmdline(argv) if sys.platform == "win32" else shlex.join(argv)


def plan_payload(
    plan: ReconstructionPlan,
    mode: str,
    *,
    verify_determinism: bool = False,
) -> dict[str, object]:
    commands = commands_for(plan, mode, verify_determinism=verify_determinism)
    return {
        "mode": mode,
        "source": plan.source,
        "scopes": list(plan.scopes),
        "verify_determinism": verify_determinism,
        "changed_paths": [
            {
                "status": item.status,
                "path": item.path,
                "previous_path": item.previous_path,
            }
            for item in plan.changed_paths
        ],
        "reasons": list(plan.reasons),
        "commands": [
            {"scope": stage.scope, "label": stage.name, "argv": list(stage.command)}
            for stage in commands
        ],
    }


def print_plan(
    plan: ReconstructionPlan,
    mode: str,
    *,
    verify_determinism: bool = False,
    as_json: bool = False,
) -> None:
    if as_json:
        print(
            json.dumps(
                plan_payload(plan, mode, verify_determinism=verify_determinism),
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    print(f"mode: {mode}")
    print(f"source: {plan.source}")
    print("scopes: " + (", ".join(plan.scopes) if plan.scopes else "none"))
    print(f"verify_determinism: {'yes' if verify_determinism else 'no'}")
    for reason in plan.reasons:
        print(f"reason: {reason}")
    print("commands:")
    for stage in commands_for(plan, mode, verify_determinism=verify_determinism):
        print(f"  [{stage.scope}] {stage.name}: {_format_command(stage.command)}")


def run(
    mode: str,
    *,
    scopes: Iterable[str] = ("all",),
    verify_determinism: bool = False,
    keep_going: bool = False,
    runner=subprocess.run,
) -> int:
    failures: list[tuple[Stage, int]] = []
    for stage in stages(
        mode,
        scopes=scopes,
        verify_determinism=verify_determinism,
    ):
        print(f"== {stage.name} ==", flush=True)
        try:
            runner(stage.command, cwd=ROOT, check=True)
        except (OSError, subprocess.CalledProcessError) as error:
            if not keep_going:
                raise
            code = (
                error.returncode or 1
                if isinstance(error, subprocess.CalledProcessError)
                else 1
            )
            failures.append((stage, code))
            print(
                f"FAILED [{stage.scope}] {stage.name}: {error}",
                file=sys.stderr,
                flush=True,
            )
    if failures:
        print("Failures:", file=sys.stderr)
        for stage, code in failures:
            print(f"  - {stage.name}: code {code}", file=sys.stderr)
        return failures[0][1]
    print(f"workspace {mode}: OK")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("refresh", "check"),
        help="refresh régénère; check compare sans écrire",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--changed",
        action="store_true",
        help="propose seulement les scopes affectés par les changements Git",
    )
    selection.add_argument(
        "--scope",
        action="append",
        choices=("all", *SCOPE_ORDER),
        help="scope explicite; répétable",
    )
    parser.add_argument("--base", help="révision Git de base pour la sélection --changed")
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="double chaque reconstruction; réservé au choix explicite ou à la CI",
    )
    parser.add_argument(
        "--after-full-tests",
        action="store_true",
        help="compatibilité suite complète : check mono-passe de tous les scopes",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="exécute; sans ce drapeau la commande affiche seulement le plan",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="continue les scopes indépendants et récapitule tous les échecs",
    )
    parser.add_argument("--json", action="store_true", help="sortie JSON du plan")
    args = parser.parse_args(argv)
    if args.json and args.run:
        parser.error("--json et --run sont incompatibles")
    if args.keep_going and not args.run:
        parser.error("--keep-going exige --run")
    if args.base and not args.changed:
        parser.error("--base exige --changed")
    if args.after_full_tests and args.mode != "check":
        parser.error("--after-full-tests exige le mode check")
    if args.after_full_tests and args.verify_determinism:
        parser.error("--after-full-tests est mono-passe")
    if args.run and not (args.changed or args.scope or args.after_full_tests):
        parser.error("--run exige --changed ou au moins un --scope explicite")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.changed:
        try:
            plan = select_changed(test_changed.collect_changed_paths(args.base))
        except (OSError, subprocess.CalledProcessError) as error:
            plan = ReconstructionPlan(
                (),
                (),
                (f"lecture Git impossible: {error}", "aucune reconstruction automatique"),
                "changed",
            )
    else:
        plan = explicit_plan(args.scope or ("all",))
    print_plan(
        plan,
        args.mode,
        verify_determinism=args.verify_determinism,
        as_json=args.json,
    )
    if not args.run:
        return 0
    if not plan.scopes:
        print("Aucune reconstruction sélectionnée.")
        return 0
    try:
        return run(
            args.mode,
            scopes=plan.scopes,
            verify_determinism=args.verify_determinism,
            keep_going=args.keep_going,
        )
    except subprocess.CalledProcessError as error:
        return error.returncode or 1
    except OSError as error:
        print(f"workspace {args.mode}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
