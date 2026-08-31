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


def stages(mode: str, python: str = sys.executable) -> tuple[Stage, ...]:
    if mode not in {"refresh", "check"}:
        raise ValueError(f"unsupported workspace mode: {mode}")
    common = ("--verify-determinism",)
    if mode == "check":
        common += ("--check",)
    return (
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
        Stage(
            "documentation canonique",
            (python, "-m", "unittest", "pipeline.tests.test_repository_docs"),
        ),
    )


def run(mode: str, *, runner=subprocess.run) -> None:
    for stage in stages(mode):
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run(args.mode)
    except subprocess.CalledProcessError as error:
        return error.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
