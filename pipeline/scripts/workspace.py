"""Single entry point for generated workspace projections and their checks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Stage:
    name: str
    command: tuple[str, ...]


def stages(
    mode: str,
    python: str = sys.executable,
    *,
    verify_determinism: bool = True,
    include_documentation: bool = True,
) -> tuple[Stage, ...]:
    if mode not in {"refresh", "check"}:
        raise ValueError(f"unsupported workspace mode: {mode}")
    common: tuple[str, ...] = ()
    if verify_determinism:
        common += ("--verify-determinism",)
    if mode == "check":
        common += ("--check",)
    stages = [
        Stage(
            "inventaires graphiques complémentaires",
            (python, str(SCRIPT_DIR / "build_graphics_inventory.py"), *common),
        ),
        Stage(
            "registre global",
            (python, str(SCRIPT_DIR / "build_global_asset_registry.py"), *common),
        ),
        Stage(
            "intégrité physique et index des runs",
            (python, str(SCRIPT_DIR / "audit_workspace_integrity.py"), *common),
        ),
    ]
    if include_documentation:
        stages.append(
            Stage(
                "documentation canonique",
                (python, "-m", "unittest", "pipeline.tests.test_repository_docs"),
            )
        )
    return tuple(stages)


def run(
    mode: str,
    *,
    verify_determinism: bool = True,
    include_documentation: bool = True,
    runner=subprocess.run,
) -> None:
    for stage in stages(
        mode,
        verify_determinism=verify_determinism,
        include_documentation=include_documentation,
    ):
        print(f"== {stage.name} ==", flush=True)
        runner(stage.command, cwd=ROOT, check=True)
    print(f"workspace {mode}: OK")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("refresh", "check"),
        help="refresh régénère les projections; check ne modifie aucune source métier",
    )
    parser.add_argument(
        "--after-full-tests",
        action="store_true",
        help="contrôle mono-passe des sorties; réservé au sélecteur après les tests complets",
    )
    args = parser.parse_args(argv)
    if args.after_full_tests and args.mode != "check":
        parser.error("--after-full-tests exige le mode check")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run(
            args.mode,
            verify_determinism=not args.after_full_tests,
            include_documentation=not args.after_full_tests,
        )
    except subprocess.CalledProcessError as error:
        return error.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
